# Memox Technical Test Submission

Hi Memox team,

Thanks for reviewing this submission. I built this project as a realistic white-label sales assistant foundation, not just a one-off coding exercise. The goal was to satisfy the spec fully, then push into product-level quality and production-ready architecture.

---

## 1) Submission Checklist

- GitHub repo with iterative commit history: **26 commits** (not squashed)
- Full setup and run guide (Docker + hybrid + local): `README.md`
- Decision log with trade-offs, overrides, and AI usage: `DECISIONS.md`
- This file (`readme_submission.md`) maps each requirement to implementation details

---

## 2) Requirement-by-Requirement Coverage

## 2.1 Document Ingestion Pipeline (25 pts)

### Models
Implemented in `apps/documents/models.py`:
- `Document`: `title`, `content`, `source_type`, `file_url`, `uploaded_at`, `processed`
- `Chunk`: `document`, `content`, `embedding`, `chunk_index`, `metadata`

### Sample documents (required: 5-10 realistic docs)
Created **10 realistic shipping-container documents** under `sample_docs/` (pricing, delivery, FAQ, specs, customization, warranty, ordering, and regional coverage).

### Ingestion Service
Implemented in `services/ingestion.py`:
- `ingest_document(document_id)`
  - loads document
  - chunks content
  - batch embeds chunk text
  - stores chunks with metadata
  - marks `document.processed = True`

### Chunking strategy (~500 chars + overlap)
Implemented in `services/chunking.py` and documented in code/comments + `DECISIONS.md`.
- Paragraph-first segmentation
- Sentence fallback for long paragraphs
- Table/list atomic chunking to preserve meaning
- 50-char bounded overlap
- Metadata includes `section_title`, `chunk_type`, `char_start`

### Detailed justification for this chunking strategy
This project's documents are not plain prose; they are mostly operational sales docs (pricing sheets, delivery policies, FAQ blocks, and comparison tables). A naive fixed-size splitter is fast, but it degrades retrieval quality in exactly these formats.

Why paragraph-first:
- A paragraph usually maps to a single semantic unit (for example, "Texas delivery windows" or "bulk discount tiers").
- Preserving that unit improves embedding coherence, which improves nearest-neighbor retrieval quality for user questions.
- It reduces context pollution where unrelated sentences are merged into one vector.

Why sentence fallback for oversized paragraphs:
- Some markdown sections are long enough to exceed target chunk size.
- Sentence-boundary fallback avoids cutting mid-thought, which is common with strict character slicing.
- This keeps chunks readable for both retrieval and downstream prompt assembly.

Why tables/lists are atomic:
- Pricing/spec tables are high-value sales data and are structurally fragile.
- Splitting a row across chunks can separate a product from its price or dimensions, causing incorrect or vague answers.
- Keeping tables/lists intact preserves row-level meaning and improves factual grounding.

Why ~500 chars:
- It is a practical balance between precision and context density for this domain.
- Smaller chunks improve retrieval specificity but can lose supporting details.
- Larger chunks add noise and increase the risk that top-k retrieval returns partially relevant context.
- Around 500 chars gave enough local context for pricing/policy questions while keeping chunk vectors focused.

Why 50-char overlap:
- Questions often target information at boundaries between adjacent chunks.
- A small overlap improves recall for boundary cases without creating heavy duplication.
- 50 chars is deliberately conservative: enough continuity for retrieval, low enough to avoid repeated context dominating top-k matches.

Why metadata (`section_title`, `chunk_type`, `char_start`):
- `section_title` improves explainability and source citation quality.
- `chunk_type` allows future retrieval filtering (for example, preferring table chunks for pricing intents).
- `char_start` supports deterministic traceability and easier debugging during eval.

Net effect:
- Better factual consistency on sales-critical queries (pricing, availability, comparisons).
- Higher trustworthiness of source citations.
- A chunking pipeline that is still simple to reason about, test, and operate in production.

### Async ingestion UX (beyond base requirement)
Implemented in:
- `apps/documents/views.py`
- `apps/documents/tasks.py`
- `apps/documents/models.py` (`IngestionJob`)

Behavior:
- queue ingestion jobs (`queued/running/succeeded/failed`)
- retries + error persistence
- warm worker task to reduce first-ingest latency

---

## 2.2 Retrieval + LLM Response (25 pts)

### Context retrieval
Implemented in `services/retrieval.py`:
- `PgVectorRetriever.retrieve(query, top_k=3, project_id=None)`
- query embedding + cosine-distance search via pgvector
- returns source-rich `RetrievedChunk` objects
- project filter enforces tenant/project isolation

### Prompt construction
Implemented in `services/prompt_builder.py`:
- `SalesPromptBuilder.build(query, context, custom_instructions=None)`
- includes system guidance to:
  - cite sources
  - avoid hallucinations
  - answer like a sales rep
  - nudge conversion when appropriate

### Chat endpoint
Implemented in `apps/ai/views.py`:
- `POST /api/ai/chat/`
- validates input, resolves project, retrieves context, builds prompt, calls LLM, persists conversation
- returns **structured** response (not plain string):
  - `content`
  - `intent`
  - `sources`
  - `components`
  - `lead_score_delta`
  - `handoff_triggered`
  - `lead_score`

### Structured response assembly
Implemented in `services/agent.py` (`AgentResponse` + `AgentHandler`).

---

## 2.3 API + Real-time (20 pts)

### REST endpoints (all required)
Implemented in:
- `apps/documents/urls.py`
- `apps/ai/urls.py`

Provided:
- `GET/POST /api/documents/`
- `POST /api/documents/<id>/ingest/`
- `GET /api/documents/<id>/chunks/`
- `POST /api/ai/chat/`
- `GET /api/ai/chat/history/<lead_id>/`

### WebSocket
Implemented in:
- `apps/ai/routing.py`
- `apps/ai/consumers.py`

Provided:
- `/ws/chat/<lead_id>/`
- bidirectional messaging
- typing indicators
- token streaming
- final structured response event

---

## 2.4 Frontend (20 pts)

### Chat widget (TypeScript)
Implemented in `frontend/src/components/chat/ChatWidget.tsx`:
- prop-driven widget (`leadId`, `apiUrl`, `wsUrl`)
- scrollable history
- connection-aware input
- typing indicators
- streaming message assembly
- structured component rendering pipeline via chat message metadata

### Admin page
Implemented in `frontend/src/app/admin/documents/page.tsx`:
- document listing with status
- ingestion trigger button
- ingest job progress polling
- robust loading/error/success states

---

## 2.5 Bonus: Agent Behavior (10 pts)

### Intent classification
Implemented in `services/intent.py`:
- `pricing | availability | general | conversion`
- conversion-first priority ordering

### Message handling and routing
Implemented in `services/agent.py`:
- pricing intent returns comparison card data
- conversion intent returns CTA + handoff signal
- lead scoring delta computed by intent class

---

## 3) Tests and Validation

### Required-style tests
- Ingestion/chunk/embedding tests: `tests/test_ingestion.py`
- Intent/agent behavior tests: `tests/test_agent.py`

### Additional coverage
Also included API, websocket, routing, fallback, metering, and isolation tests under `tests/`.

### Quality eval beyond standard unit tests
Implemented in `eval/eval_quality.py`:
- golden Q&A set
- semantic similarity scoring
- intent check reporting

---

## 4) "Going Beyond" (Product and Engineering)

I intentionally built this with product instincts and production direction in mind.

### 4.1 Structured AI responses (not plain text)
The assistant returns citations + UI components (`product_comparison`, `cta`) to support real sales workflows.

### 4.2 Real-time token streaming UX
WebSocket streaming with typing states improves perceived speed and trust.

### 4.3 Smarter chunking than fixed-size splitting
Paragraph/table/list-aware chunking improves retrieval quality on realistic sales documents.

### 4.4 Better-than-minimum frontend UX
- clear loading/error states
- ingestion progress visibility
- guarded chat prerequisites to prevent broken user flows

### 4.5 Lead intelligence and conversion workflow
- lead dashboard (`/admin/leads`)
- weighted scoring by intent
- CTA handoff signal for conversion messages

### 4.6 Multi-tenant architecture for white-label use
Added organization/project boundaries and project-scoped retrieval/chat so multiple clients can safely share one platform without data leakage.

### 4.7 Production-minded LLM architecture
Kept local-first default (Ollama) but implemented provider routing and fallback architecture for real deployment flexibility.

### 4.8 Easy ingestion flow for non-technical users
Asynchronous ingestion jobs with queue/running/success/failure status and polling so users can continue working while indexing runs.

---

## 5) AI-Assisted Workflow (What I Used AI For)

I used AI as a coding accelerator and design reviewer, then validated and overrode where needed.

Representative prompt/task themes I used:
- build semantic chunking that preserves tables and list structure
- wire pgvector retrieval with source attribution
- create structured agent responses and conversion-aware components
- add websocket token streaming and typing flow
- enforce tenant-safe project isolation in retrieval/chat
- add auth guards and prerequisite checks for chat readiness
- generate doc-grounded welcome message with strict length and fallback safety

Where I overrode AI suggestions:
- chose pgvector over separate vector DB service for transactional simplicity
- kept deterministic intent classification over LLM zero-shot for speed + testability
- rewrote chunking to avoid fixed-size row breaks in pricing tables
- adjusted lead scoring to reflect business value differences between intents

---

## 6) Commit History (Proof of Iterative Work)

Current commit count: **26**

Recent commits include:
- `dc02f73` updated decisions and UI improvements
- `243e82d` frontend progress indication for ingestion
- `41a604b` frontend pages for multi-tenant architecture
- `e05c77b` usage events API + billing telemetry hooks
- `e4c00f7` provider policy and key storage in tenant domain
- `9928fa1` tenant organizations/projects models
- `07c677e` AgentHandler with streaming + DI factory
- `8b5fa43` semantic chunker implementation

This reflects iterative product and architecture development rather than one-pass generation.

---

## 7) DECISIONS.md Coverage

`DECISIONS.md` includes:
- what was chosen
- what was rejected
- what AI helped with
- where AI was overridden
- concise reviewer summary bullets
- representative AI prompt log
- production-readiness additions and future roadmap

---

## 8) Business-Ready Strengths (Why This Is More Than a Test App)

- **Client project isolation**: tenant-safe boundaries for white-label operation
- **Composable architecture**: interface-driven services + runtime class registry
- **Operational clarity**: ingestion lifecycle tracking and error visibility
- **LLM resilience**: provider routing/fallback design, not single-provider lock-in
- **Sales alignment**: intent-aware cards, CTA handoff, lead scoring intelligence
- **Measurable quality**: answer-quality evaluation script beyond HTTP status checks

---

## 9) What I Would Improve Next in Production

- lead identity hardening for websocket/session integrity
- queue prioritization and autoscaled ingestion workers
- retrieval reranking for long, noisy documents
- CRM webhooks for immediate sales-team activation

---

## 10) Final Note

I approached this as if I were building the first real version of a client-facing B2B sales assistant, not just trying to check boxes. I focused on correctness, product UX, operational reliability, and architecture decisions that can survive real usage.

