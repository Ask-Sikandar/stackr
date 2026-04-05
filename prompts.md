# AI Prompts Log — Memox Sales Assistant

Representative prompts used while building this project. Grouped by phase.
Each entry notes what the AI produced, what I kept, and where I overrode it.

---

## Phase 1 — Architecture & Stack Decisions

**Prompt**
> I'm building a RAG-based AI sales assistant for a shipping container company using Django + DRF, Next.js, and WebSockets. The system needs to ingest markdown product docs, chunk and embed them, retrieve relevant chunks at query time, and stream LLM responses to a browser chat widget. What vector store and embedding approach would you recommend, and why?

**What AI suggested:** Separate ChromaDB service for the vector store, OpenAI embeddings.

**What I kept:** The overall RAG architecture and the rationale for embedding-based retrieval.

**What I changed:** Switched to pgvector (one less service, same Postgres transaction) and `all-MiniLM-L6-v2` (no API key, offline-capable). Documented the reasoning in DECISIONS.md.

---

**Prompt**
> Design a SOLID service layer for a RAG pipeline in Django. The embedding model, vector retriever, LLM client, chunker, and intent classifier should all be swappable — I need to inject mocks in tests without loading real models or making HTTP calls.

**What AI suggested:** Abstract base classes with a simple registry dict in settings, factory functions with `@lru_cache`.

**What I kept:** The ABC interfaces, `SERVICE_CLASSES` settings registry, and `lru_cache` singletons. This became the backbone of the test strategy.

**What I changed:** Added `reset_cache()` to the factory after discovering that `@lru_cache` singletons persisted between test cases and caused mock/real class bleed-through.

---

## Phase 2 — Document Ingestion

**Prompt**
> Build a semantic chunker for markdown documents that splits on paragraph boundaries first, keeps table rows atomic (never splits mid-row), and treats bullet lists as single chunks. Fall back to sentence-boundary splitting when a paragraph exceeds 500 characters. Add 50-char overlap between adjacent chunks and store section_title metadata from the nearest heading above each chunk.

**What AI produced:** A working chunker with paragraph and sentence splitting, but it used a simple line-by-line scan that missed multi-line table cells.

**What I kept:** The overall structure and the overlap logic.

**What I changed:** Rewrote the table detection to buffer consecutive `|...|` lines into a single block before emitting, after manually inspecting what the AI version produced on `pricing_sheet.md`.

---

**Prompt**
> Implement `ingest_document(document_id)` — it should chunk the document content, generate embeddings in a single batch pass (not a loop), bulk-create Chunk rows in an atomic transaction, and delete any stale chunks first so re-ingestion is idempotent.

**What AI produced:** Correct batch embedding and `bulk_create`, but it marked `document.processed = True` outside the transaction.

**What I kept:** Batch embedding, bulk create, stale chunk deletion.

**What I changed:** Moved `document.processed = True` inside the `transaction.atomic()` block so a failed embedding run never marks a document as processed.

---

**Prompt**
> Add async ingestion with Celery. The ingest endpoint should create an `IngestionJob` record, enqueue the task, and return the job ID immediately. The job should track `queued → running → succeeded/failed` status with timestamps and a retry limit. The frontend should poll the job status endpoint until the job completes.

**What AI produced:** A working Celery task with status tracking and the polling endpoint.

**What I kept:** The job lifecycle model, the Celery task structure, and the polling endpoint.

**What I changed:** Added a `warm_ingestion_worker` pre-task that runs a no-op to keep the worker hot and avoid cold-start latency on the first real ingest after idle — the AI hadn't considered this.

---

## Phase 3 — Retrieval & Agent

**Prompt**
> Implement `retrieve_context(query, top_k=3)` using pgvector's cosine distance. The query should be embedded with the same model used during ingestion, and results should include document title, chunk index, relevance score (converted from distance to similarity), and chunk metadata for source citation. Add optional project_id filtering so retrieval is tenant-scoped.

**What AI produced:** Correct pgvector `CosineDistance` annotation with `order_by`. Missing the project_id filter.

**What I kept:** The ORM pattern, the distance-to-similarity conversion.

**What I added:** `filter(document__project_id=project_id)` when project context is present, and a `select_related("document")` to avoid N+1 on the title field.

---

**Prompt**
> Build a sales-oriented prompt template that instructs the LLM to: only answer from the provided XML-tagged context blocks, cite sources using [Source: title], answer like a knowledgeable sales rep, and guide prospects toward conversion. Add a `custom_instructions` slot so each project can inject their own persona or tone rules.

**What AI produced:** A good system prompt with the XML context format and citation instructions.

**What I kept:** The `<source title="...">` block format and the five-rule system prompt structure.

**What I changed:** Rewrote the conversion-nudge rule — the AI version was too pushy ("always ask for the sale"), which would have felt aggressive. I softened it to "when appropriate, guide toward the next step."

---

**Prompt**
> Implement `classify_intent(message)` that categorises a message as `pricing | availability | general | conversion`. I want keyword matching (not LLM zero-shot) so it's sub-millisecond and fully testable. Conversion should be checked before pricing in priority order, since it has the highest business value.

**What AI produced:** A flat keyword list with no priority ordering.

**What I kept:** The keyword lists and the basic structure.

**What I changed:** Restructured as an ordered list of `(Intent, keywords[])` tuples so CONVERSION is checked first. Added `I want to buy`, `ready to order` variants the AI missed.

---

## Phase 4 — WebSocket & Streaming

**Prompt**
> Implement a Django Channels `AsyncWebsocketConsumer` that streams Ollama tokens to the browser in real time. The LLM generator is synchronous — run it in a thread pool executor, bridge tokens back to the async event loop via `asyncio.Queue`, and send each token as `{"type": "stream", "token": "..."}`. Send a final `{"type": "message"}` with the complete structured response (sources, components, lead score) after streaming finishes.

**What AI produced:** A consumer using `asyncio.get_event_loop()` inside the thread, which fails in a `ThreadPoolExecutor` because threads don't have a running event loop.

**What I kept:** The queue-based bridging idea.

**What I changed:** Switched to `asyncio.get_running_loop()` captured in the async context before the thread starts, then passed via closure to `asyncio.run_coroutine_threadsafe()`. Added `.result()` on each future so the thread blocks until the queue put succeeds rather than fire-and-forget.

---

**Prompt**
> Build a `useWebSocket` React hook that auto-reconnects, keeps the callback refs fresh without re-triggering the connection effect, and handles React Strict Mode's double-mount/unmount. The hook should expose `send`, `isConnected`, and `isConnecting`.

**What AI produced:** A clean hook with reconnect timer and `useRef` for callbacks.

**What I kept:** The overall structure and `unmountedRef` pattern to suppress reconnects after unmount.

**What I changed:** Added `useEffect(() => { if (isConnected) setError(null); }, [isConnected])` in the ChatWidget to clear stale error banners — the hook fires `onError` when Strict Mode kills the first WS before it connects, and without the effect the error persists even after the second WS connects cleanly.

---

## Phase 5 — Frontend Components

**Prompt**
> Build a `ChatWidget` React component that accepts `leadId`, `apiUrl`, `wsUrl` as props. It should render a scrollable message history, show animated typing dots while the LLM is responding, render streaming tokens in-place inside the current bubble (with a blinking cursor), and replace the streamed text with the final structured message when complete. Show source citation cards (collapsible) and product comparison tables below assistant messages.

**What AI produced:** A complete widget with streaming state management.

**What I kept:** The message state shape (`isStreaming`, `streamBuffer`), the inline token-append logic, and the component hierarchy.

**What I changed:** The AI rendered source cards inside the streaming bubble — I moved them to appear only on the final `type: "message"` event so they don't flicker during streaming.

---

**Prompt**
> Add a Lead Intelligence Dashboard admin page that shows each lead's score, total message count, and intent progression as a colour-coded timeline of pills (general=grey, availability=purple, pricing=blue, conversion=orange). Order leads by score descending. Score thresholds for colour coding: ≥30 orange, ≥15 blue, otherwise grey.

**What AI produced:** A working table with colour-coded scores.

**What I kept:** The table structure and intent pill colours.

**What I changed:** Added tooltip titles on each intent pill showing the message preview and score delta — the AI version had no way to inspect what triggered each event without navigating away.

---

## Phase 6 — Multi-tenancy & Auth

**Prompt**
> Add organisation and project tenancy to the system. Documents, chunks, leads, and conversations should be scoped to a project. Retrieval should filter by project_id. The chat API and WebSocket should accept a project_id, resolve it through the user's membership, and reject requests where the user is not a member. Use JWT auth via djangorestframework-simplejwt.

**What AI produced:** Organisation and Project models with a Membership join table, project-scoped querysets on all views.

**What I kept:** The model structure, the `get_project_for_user()` access helper, and the membership-filtered querysets.

**What I changed:** Added `is_active` on the Membership model so suspended members are blocked without deletion, and added `allow_platform_fallback` and `use_private_llm_credentials` flags on Organisation after the AI's first version had no way to mix private and platform-level LLM keys.

---

**Prompt**
> Add provider routing so each project can configure a primary and backup LLM provider (ollama, openai, gemini). If the organisation has private API keys, use those; if not (or if they fail), fall back to platform-level keys. Implement `FallbackLLMClient` that tries providers in order, emits structured events on failure and fallback, and raises only when all providers are exhausted.

**What AI produced:** A working `FallbackLLMClient` with try/except over each provider.

**What I kept:** The fallback loop and the provider chain construction.

**What I changed:** The AI emitted a single failure event at the end. I changed it to emit `llm.provider_failed` per provider and `llm.fallback_used` when the first provider fails but a subsequent one succeeds — this gives ops the signal they need to know a key has gone stale before it causes an outage.
