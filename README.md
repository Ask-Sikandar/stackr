# Memox AI Sales Assistant — Pacific Container Co. POC

A RAG-based AI sales assistant that answers prospect questions about shipping containers using company documentation. Built with Django + DRF, Next.js, WebSockets, pgvector, Celery, Redis, and Ollama.

## Deployment Modes

Choose one of these modes based on what you are trying to do.

| Mode | What runs in Docker | What runs locally | Best for |
|------|----------------------|-------------------|----------|
| Full Docker | DB, Redis, Ollama, backend, worker, frontend | Nothing required | Fastest onboarding and demo setup |
| Hybrid Dev | DB, Redis, Ollama | Backend (Daphne), Celery worker, frontend dev server | Daily development with hot reload |
| Fully Local | Nothing | Everything (including DB/Redis/Ollama) | Advanced local ops and custom setups |

## Option A: Full Stack in Docker (Detailed)

### 1. Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- At least 8 GB RAM recommended (Ollama model + app stack)

### 2. Start the full stack

From the repository root (`asses_proj/`):

```bash
docker compose up --build
```

This starts:

- `db` (PostgreSQL 16 + pgvector)
- `redis` (channel layer + Celery broker/result backend)
- `ollama` (LLM inference)
- `backend` (Daphne ASGI app; migrations auto-run on startup)
- `ingestion-worker` (Celery worker)
- `frontend` (Next.js production server)

### 3. Verify service health

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f ingestion-worker
```

### 4. First-run Ollama model pull

On first startup, the `ollama` container pulls `llama3.2:3b` (about 2 GB). Initial boot may take a few minutes.

Check model/server readiness:

```bash
docker compose logs -f ollama
```

### 5. Ingest sample documents (one-time)

Open a Django shell in the backend container:

```bash
docker compose exec backend uv run python manage.py shell
```

Then run:

```python
from pathlib import Path
from apps.documents.models import Document, IngestionJob
from apps.documents.tasks import run_ingestion_job

docs_dir = Path("sample_docs")
for f in docs_dir.glob("*.md"):
    doc = Document.objects.create(
        title=f.stem.replace("_", " ").title(),
        content=f.read_text(),
        source_type="markdown",
    )
    job = IngestionJob.objects.create(document=doc)
    run_ingestion_job.delay(str(job.job_id))
    print(f"Queued ingestion for {doc.title} ({job.job_id})")
```

### 6. Access URLs

- Frontend app: http://localhost:3000
- Frontend document admin page: http://localhost:3000/admin/documents
- Frontend lead dashboard: http://localhost:3000/admin/leads
- Django admin: http://localhost:8000/admin/
- API root (example endpoint): http://localhost:8000/api/ai/chat/

### 7. Stop and clean up

```bash
# stop containers (preserve volumes)
docker compose down

# optional: remove volumes too (wipes Postgres + Ollama persisted data)
docker compose down -v
```

## Option B: Hybrid Dev Mode (Infra in Docker, App in Dev Mode)

This mode runs only stateful infrastructure in Docker (`db`, `redis`, `ollama`) while you run backend/worker/frontend directly for faster iteration.

### 1. Start infrastructure only

From `asses_proj/`:

```bash
docker compose up -d db redis ollama
docker compose ps
```

### 2. Configure backend environment

Create local environment file once:

```bash
# macOS/Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

Minimum env values for hybrid mode (already aligned with `.env.example` defaults):

```env
DJANGO_SETTINGS_MODULE=config.settings.development
DB_HOST=localhost
DB_PORT=5432
DB_NAME=memox
DB_USER=memox
DB_PASSWORD=memox
REDIS_HOST=localhost
REDIS_PORT=6379
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

### 3. Run backend in dev mode

Terminal 1 (from `asses_proj/`):

```bash
uv sync --extra dev
uv run python manage.py migrate
uv run daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

### 4. Run Celery worker in dev mode

Terminal 2 (from `asses_proj/`):

```bash
# macOS/Linux
uv run celery -A config worker --loglevel=INFO

# Windows PowerShell (Celery prefork is unstable on Windows)
uv run celery -A config worker --loglevel=INFO --pool=solo --concurrency=1
```

### 5. Run frontend in dev mode

Terminal 3:

```bash
cd frontend
npm install

# macOS/Linux
NEXT_PUBLIC_API_URL=http://localhost:8000 NEXT_PUBLIC_WS_URL=ws://localhost:8000 npm run dev

# Windows PowerShell
$env:NEXT_PUBLIC_API_URL="http://localhost:8000"
$env:NEXT_PUBLIC_WS_URL="ws://localhost:8000"
npm run dev
```

Frontend dev server is available at http://localhost:3000.

### 6. Recommended hybrid health checks

```bash
# infra containers
docker compose logs -f db
docker compose logs -f redis
docker compose logs -f ollama

# optional warmup endpoint (requires auth)
# POST /api/documents/ingestion/warm/
```

### 7. Stop hybrid mode

Stop local processes with Ctrl+C, then:

```bash
docker compose stop db redis ollama
```

## Option C: Fully Local Development (without Docker)

### Prerequisites

- Python 3.12+ with `uv`
- PostgreSQL 16 with pgvector extension enabled
- Redis 7
- Ollama running locally (`ollama pull llama3.2:3b`)
- Node.js 20+

### Backend

```bash
# macOS/Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env

uv sync --extra dev
createdb memox
psql -d memox -c "CREATE EXTENSION IF NOT EXISTS vector;"
uv run python manage.py migrate
uv run daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

### Worker

```bash
# macOS/Linux
uv run celery -A config worker --loglevel=INFO

# Windows PowerShell
uv run celery -A config worker --loglevel=INFO --pool=solo --concurrency=1
```

### Frontend

```bash
cd frontend
npm install

# macOS/Linux
NEXT_PUBLIC_API_URL=http://localhost:8000 NEXT_PUBLIC_WS_URL=ws://localhost:8000 npm run dev

# Windows PowerShell
$env:NEXT_PUBLIC_API_URL="http://localhost:8000"
$env:NEXT_PUBLIC_WS_URL="ws://localhost:8000"
npm run dev
```

## Detailed Architecture Specification

### 1. Runtime Topology

```text
Browser (Next.js)
      ├─ HTTP/JSON ───────────────▶ Django REST API (DRF)
      └─ WebSocket /ws/chat/<id>/ ▶ Django Channels Consumer

Django ASGI (Daphne)
      ├─ AgentHandler orchestration
      │   ├─ IntentClassifier (keyword-based)
      │   ├─ PgVectorRetriever (PostgreSQL + pgvector)
      │   ├─ PromptBuilder
      │   └─ LLMClient (Ollama/OpenAI/Gemini + fallback router)
      ├─ PostgreSQL (documents, chunks, leads, conversations, tenancy)
      └─ Redis (Channels layer + Celery broker/result backend)

Celery Worker
      └─ Ingestion pipeline (chunk -> embed -> bulk store chunks)

Ollama
      └─ Local model inference (streaming tokens)
```

### 2. Component Specifications

| Layer | Component | Responsibility | Key Technology |
|------|-----------|----------------|----------------|
| UI | Next.js frontend | Chat widget, admin documents page, lead dashboard | Next.js 14, React |
| Transport | ASGI app | Serves HTTP + WebSocket in one process | Daphne + Channels |
| API | DRF views | Authenticated CRUD and chat endpoints | Django REST Framework |
| Realtime | ChatConsumer | Streaming token relay + final structured message | Channels AsyncWebsocketConsumer |
| Orchestration | AgentHandler | classify -> retrieve -> prompt -> generate -> structure | services/agent.py |
| Retrieval | PgVectorRetriever | Top-k semantic retrieval with cosine distance | pgvector `<=>` via ORM |
| Generation | LLM clients | Provider abstraction + fallback chain | Ollama/OpenAI/Gemini clients |
| Ingestion | Celery tasks | Async job lifecycle + retries + warmup | Celery |
| Persistence | Postgres schema | Multi-tenant domain + vectors + chat history | PostgreSQL 16 + pgvector |
| Eventing | Usage metering | Billing-ready event hooks | accounts_usageevent |

### 3. Backend Architectural Contracts (SOLID)

The service layer depends on interfaces, not concrete classes:

- `IEmbedder`
- `IChunker`
- `IRetriever`
- `ILLMClient`
- `IIntentClassifier`
- `IPromptBuilder`

Concrete classes are selected via `settings.SERVICE_CLASSES` and instantiated through `services.factory` with process-level caching (`@lru_cache`). This allows tests to inject mocks without changing production code or infrastructure.

### 4. Chat Request Lifecycle

#### REST flow (`POST /api/ai/chat/`)

1. JWT-authenticated user sends `lead_id`, `project_id`, and `message`.
2. Access check resolves project via organization membership (`get_project_for_user`).
3. Agent pipeline executes intent classification, project-scoped vector retrieval, merged instruction prompt assembly, and provider-routed LLM completion.
4. User and assistant turns are persisted in `Message`.
5. Lead score and intent timeline (`IntentEvent`) are updated.
6. Usage event `chat.response` is emitted.
7. Structured response is returned with `sources`, `components`, and `lead_score`.

#### WebSocket streaming flow (`/ws/chat/<lead_id>/`)

1. Client sends chat frame containing `message`, and for tenant mode `project_id` + `access_token`.
2. Consumer validates project authorization from JWT.
3. Consumer emits typing status.
4. `agent.stream_message()` runs in a thread executor.
5. Tokens stream incrementally to client (`type: stream`).
6. Final structured response is persisted and emitted (`type: message`).
7. Typing indicator turns off.

### 5. Ingestion Architecture

#### Document ingestion flow

1. User uploads document (`POST /api/documents/`) for a project.
2. Optional worker warm task is queued (`warm_ingestion_worker`).
3. Ingestion is queued (`POST /api/documents/<id>/ingest/`) as `IngestionJob`.
4. Celery worker runs `run_ingestion_job(job_id)`, marks status `running`, executes `ingest_document(document_id)`, retries failures with bounded retry policy, and finishes in `succeeded` or `failed`.
5. Pipeline internals: chunk content semantically, batch-embed chunk texts, bulk-create `Chunk` rows with 384-dim vectors, and mark document `processed=true`.
6. Usage events emitted: `ingestion.queued`, `ingestion.succeeded`, `ingestion.failed`.

### 6. Data Model and Tenancy Boundaries

#### Core entities

- Identity and tenant model: `Organization`, `Membership`, `Project`
- AI credentials/routing: `OrganizationLLMKey`
- Knowledge base: `Document`, `Chunk`, `IngestionJob`
- Conversation model: `Lead`, `Conversation`, `Message`, `IntentEvent`
- Metering: `UsageEvent`

#### Isolation model

- API access is scoped through active organization membership.
- Documents and leads are tied to `Project`.
- Retrieval filters chunks by `document__project_id` when project context is supplied.
- Chat APIs and WS tenant mode enforce project ownership before inference.

#### Simplified relation map

```text
User --< Membership >-- Organization --< Project
Project --< Document --< Chunk
Project --< Lead --< Conversation --< Message
Lead --< IntentEvent
Organization --< OrganizationLLMKey
Organization/Project --< UsageEvent
Document --< IngestionJob
```

### 7. LLM Routing and Fallback

Routing is project-aware:

1. Evaluate project provider preferences (`llm_primary_provider`, `llm_backup_provider`).
2. If organization private-key mode is enabled, use active encrypted org keys first.
3. If permitted, fall back to platform-level providers from settings.
4. `FallbackLLMClient` attempts providers in order.
5. Provider events are emitted: `llm.provider_used`, `llm.provider_failed`, `llm.fallback_used`, `llm.all_failed`.

### 8. Operational Notes

- ASGI app and WebSocket transport share one deployment unit (`config.asgi`).
- Channels uses Redis as broker for cross-process message delivery.
- Celery worker is separated from API process to isolate ingestion workload.
- Embedding model (`all-MiniLM-L6-v2`) is warmed in Docker image build and can also be worker-warmed at runtime.
- Usage events are best-effort and do not block user-facing request paths.

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


