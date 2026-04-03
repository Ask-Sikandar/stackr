# Memox AI Sales Assistant — Pacific Container Co. POC

A RAG-based AI sales assistant that answers prospect questions about shipping containers using company documentation. Built with Django + DRF, Next.js, WebSockets, pgvector, and Ollama.

## Architecture

```
Browser ──WebSocket──▶ Django Channels (Daphne ASGI)
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
              AgentHandler         REST API (DRF)
                    │
         ┌──────────┼──────────┐
         ▼          ▼          ▼
   IntentClassifier Retriever  LLMClient
   (keywords)   (pgvector)  (Ollama stream)
                    │
              EmbeddingService
             (sentence-transformers)
```

All AI services implement abstract interfaces (`IEmbedder`, `IRetriever`, etc.) — concrete classes are injected via `settings.SERVICE_CLASSES`. Tests swap in mocks with zero infrastructure.

## Quick Start (Docker)

```bash
# 1. Clone and start all services
docker-compose up --build

# 2. The backend auto-runs migrations on startup.
# 3. Ingestion worker runs as a separate container (Celery).
# 4. Ingest sample documents (one-time):
docker-compose exec backend uv run python manage.py shell -c "
from pathlib import Path
from apps.documents.models import Document
from apps.documents.tasks import run_ingestion_job
from apps.documents.models import IngestionJob

docs_dir = Path('sample_docs')
for f in docs_dir.glob('*.md'):
    doc = Document.objects.create(title=f.stem.replace('_', ' ').title(), content=f.read_text(), source_type='markdown')
    job = IngestionJob.objects.create(document=doc)
    run_ingestion_job.delay(str(job.job_id))
    print(f'Queued ingestion for {doc.title} ({job.job_id})')
"

# 5. Open http://localhost:3000 — chat widget ready
# 6. Admin panel: http://localhost:3000/admin/documents
# 7. Lead dashboard: http://localhost:3000/admin/leads
```

> **Note:** Ollama pulls `llama3.2:3b` (~2GB) on first start. This takes a few minutes.

## Local Development (without Docker)

### Prerequisites
- Python 3.12+ with uv
- PostgreSQL 16 with pgvector extension
- Redis 7
- Ollama running locally (`ollama pull llama3.2:3b`)
- Node.js 20+

### Backend

```bash
cp .env.example .env
uv sync --extra dev
createdb memox
uv run python manage.py migrate
uv run daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

### Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 NEXT_PUBLIC_WS_URL=ws://localhost:8000 npm run dev
```

## Running Tests

```bash
# Unit tests (no DB required)
uv run pytest tests/ -v

# All tests including integration (PostgreSQL required for DB tests)
uv run pytest tests/ -v
# DB tests auto-skip if PostgreSQL is not reachable

# With coverage
uv run pytest tests/ --cov=. --cov-report=term-missing
```

## Eval Script

```bash
# With real DB + ingested documents
uv run python eval/eval_quality.py --verbose

# Mock mode (no DB required)
uv run python eval/eval_quality.py --mock
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/accounts/register/` | Create account and optional organization |
| POST | `/api/accounts/token/` | Obtain JWT access/refresh tokens |
| POST | `/api/accounts/token/refresh/` | Refresh JWT access token |
| GET/POST | `/api/accounts/organizations/` | List/create organizations for current user |
| PATCH | `/api/accounts/organizations/<id>/` | Update organization routing flags |
| GET/POST | `/api/accounts/organizations/<id>/llm-keys/` | List/upsert organization LLM API keys |
| POST | `/api/accounts/organizations/<id>/llm-keys/<provider>/rotate/` | Rotate provider key and reactivate it |
| POST | `/api/accounts/organizations/<id>/llm-keys/<provider>/revoke/` | Revoke (disable) provider key |
| GET | `/api/accounts/organizations/<id>/usage-events/` | List and aggregate usage events (supports filters) |
| GET/POST | `/api/accounts/projects/` | List/create projects for current user |
| PATCH | `/api/accounts/projects/<id>/` | Update project provider preferences |
| GET/POST | `/api/documents/` | List / upload documents |
| POST | `/api/documents/ingestion/warm/` | Queue ingestion worker warm-up |
| POST | `/api/documents/<id>/ingest/` | Queue ingestion job (returns 202) |
| GET | `/api/documents/ingest-jobs/<job_id>/` | Ingestion job status |
| GET | `/api/documents/<id>/chunks/` | List chunks |
| POST | `/api/ai/chat/` | Single-turn chat (REST, requires `project_id`) |
| GET | `/api/ai/chat/history/<lead_id>/` | Conversation history |
| GET | `/api/leads/` | Lead list (dashboard) |
| WS | `/ws/chat/<lead_id>/` | Bidirectional chat with streaming |

### Chat request/response

```json
POST /api/ai/chat/
{ "lead_id": "uuid", "project_id": 7, "message": "How much is a 40ft container?" }

{
  "message_id": "uuid",
  "content": "A 40ft standard container is $3,850 [Source: Pricing Sheet]...",
  "intent": "pricing",
  "sources": [{"title": "Pricing Sheet", "excerpt": "...", "score": 0.94}],
  "components": [{"type": "product_comparison", "data": {"products": [...]}}],
  "lead_score": 10,
  "handoff_triggered": false
}
```

### WebSocket tenant-scoped payload

When using tenant-scoped chat over WebSocket, include both `project_id` and `access_token` in the chat frame:

```json
{ "type": "chat", "lead_id": "uuid", "message": "Need pricing", "project_id": 7, "access_token": "<jwt>" }
```

## Key Design Decisions

See [DECISIONS.md](DECISIONS.md) for full reasoning.

- **pgvector** — same Postgres instance, one less service, atomic transactions
- **Paragraph-first chunking** — preserves semantic units; tables kept atomic
- **Keyword intent classification** — sub-ms, fully testable, accurate for 4 categories
- **SOLID service layer** — ABCs + `SERVICE_CLASSES` registry; tests inject mocks
- **Lead scoring dashboard** — added beyond spec: conversion=25pts, pricing=10pts

## Billing-Ready Hooks

- Usage events are recorded in `accounts_usageevent` with organization/project attribution.
- Current emitted event types include `chat.response`, `ingestion.queued`, `ingestion.succeeded`, `ingestion.failed`, `llm.provider_used`, `llm.provider_failed`, `llm.fallback_used`, and `llm.all_failed`.
- These are hooks only (no payment integration yet) and are intentionally best-effort/non-blocking.

