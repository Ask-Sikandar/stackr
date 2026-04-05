# DECISIONS.md — Memox AI Sales Assistant

Key architectural decisions, trade-offs, AI-assisted choices, and where I overrode the AI.

## Reviewer Quick Scan (10 bullets)

- Kept embeddings local with `all-MiniLM-L6-v2` (384-dim) for speed, cost control, and offline development.
- Chose pgvector over a separate vector DB to keep vectors + metadata transactional in one Postgres stack.
- Implemented semantic chunking (paragraph/table/list aware) with bounded overlap for better retrieval recall at boundaries.
- Used Ollama `llama3.2:3b` as default runtime, but built provider routing (OpenAI/Gemini supported) for production flexibility.
- Kept intent classification deterministic (keyword-based) for sub-ms latency and fully testable behavior.
- Added weighted lead scoring (`general=1`, `availability=5`, `pricing=10`, `conversion=25`) to prioritize sales follow-up.
- Enforced interface-driven service architecture (`SERVICE_CLASSES` + factory) to keep the pipeline swappable and test-friendly.
- Added async ingestion jobs with lifecycle status, retries, and worker warmup to remove upload-time blocking.
- Added WebSocket token streaming + typing indicators to improve perceived responsiveness.
- Added evaluation tooling and UX upgrades (lead dashboard, CTA card, guided auth/prerequisite flow, LLM-generated welcome message).

## Representative AI Prompts Used

These are representative prompts/tasks I used while iterating with AI during implementation and refinements.

- "Build a semantic chunker for markdown docs that keeps tables atomic and avoids splitting rows."
- "Implement a retrieval pipeline with pgvector cosine search and source-attributed results."
- "Create a structured AgentHandler response with sources, components, lead score delta, and conversion handoff."
- "Add WebSocket streaming with typing indicators and a resilient frontend message state."
- "Enforce tenant isolation across organizations/projects in documents, retrieval, chat, and lead history."
- "Add async ingestion jobs with queue/running/succeeded/failed status and polling from the admin page."
- "If no auth token exists, redirect users to login and block access to protected pages."
- "Generate the chat welcome message from uploaded docs with strict length limits and safe fallback behavior."

---

## 1. Embedding Model: all-MiniLM-L6-v2

**Chosen:** `sentence-transformers/all-MiniLM-L6-v2` (384 dims, local)

**Rejected:** OpenAI `text-embedding-3-small`, TF-IDF

**Why:** Runs fully offline — no API key, no per-request cost, no external dependency. At 384 dimensions it's fast enough for a demo (< 100ms per query on CPU). Benchmark scores (~63% on SBERT STS) are adequate for domain-specific FAQ retrieval where vocabulary overlap is high.

**AI helped with:** Suggesting the model name. I verified the benchmark vs. the larger `all-mpnet-base-v2` (768 dims) and confirmed the speed/quality trade-off favours MiniLM for this demo scale.

**Where I'd change it in production:** Switch to `text-embedding-3-small` (OpenAI) or `voyage-3` for better cross-lingual and semantic recall on longer documents.

---

## 2. Vector Store: pgvector over ChromaDB

**Chosen:** pgvector (PostgreSQL extension via `pgvector` Python library)

**Rejected:** ChromaDB, FAISS, Qdrant

**Why:** Django already requires PostgreSQL. Adding pgvector is one `CREATE EXTENSION` SQL statement — no extra Docker service, no extra connection pool, no data synchronisation between two stores. Chunk records and their embeddings live in the same ACID transaction (no partial-failure risk). SQL filters + vector similarity in one query (`WHERE document_id = X ORDER BY embedding <=> query_vec`).

**AI helped with:** Initial suggestion to use ChromaDB (simpler). I overrode this — ChromaDB is a second database service with no benefit at POC scale, and pgvector is production-grade to millions of vectors.

---

## 3. Chunking Strategy: Paragraph-first with bounded overlap

**Chosen:** Paragraph-aware chunking (split on `\n\n`, then sentence boundaries, tables/lists atomic) with 50-char forward overlap between adjacent chunks.

**Rejected:** Fixed 500-char-only splitting, sentence-only splitting, and large overlapping windows.

**Why:** Container spec documents are table-heavy and section-structured. A fixed character split cuts mid-table-row ("40ft | $3,85" on one chunk, "0" on the next), which destroys meaning for both retrieval and the LLM. Splitting by paragraph boundaries first preserves semantic units — each paragraph is a coherent thought. Tables are kept as a single atomic chunk so pricing comparisons stay intact.

**Chunk size rationale:** 500 chars ≈ 80–100 tokens, fits well within the MiniLM model's 256-token window while providing enough context per chunk.

**Where I overrode AI:** Claude suggested a simpler fixed-size splitter. I rewrote the chunker with table and list detection after manually inspecting what fixed splits produced on the pricing_sheet.md document, then added a small overlap after measuring better boundary recall.

---

## 4. LLM Runtime: Ollama default + provider fallback routing

**Chosen:** Ollama with `llama3.2:3b` as the default runtime, plus a provider-routed architecture that supports OpenAI and Gemini with fallback.

**Rejected:** Hard-coding the platform to one provider with no fallback path.

**Why:** Ollama keeps local development fully offline and no-key, while provider routing keeps the codebase production-ready. Projects can prefer providers per client context, organizations can use private provider keys, and platform fallback avoids hard downtime when a provider fails.

**In production I'd use:** Keep provider routing as implemented, and tune per client for cost/quality/SLA (for example GPT-4o-mini or Claude haiku-class models for stronger instruction following and citation reliability).

---

## 5. Intent Classification: Keyword matching over LLM zero-shot

**Chosen:** Keyword pattern matching with priority ordering (conversion checked first)

**Rejected:** LLM zero-shot classification, fine-tuned classifier, embedding-based classification

**Why:** For 4 well-defined sales categories, keyword matching is sub-millisecond and fully testable without any model. LLM zero-shot would add 1–2s latency before every response. The categories have clear vocabulary boundaries: "how much / price / cost" → pricing, "deliver / ship / Texas" → availability, "I want to buy / place an order" → conversion.

**Limitation I documented:** "Is the 40ft available in Texas?" would classify as availability (correct) but misses a pricing sub-question. A multi-label classifier would handle this. I noted this as a "what I'd do with more time" item.

**Where I overrode AI:** Claude suggested an LLM-based classifier. I changed it to keyword matching and documented the reasoning — speed and testability matter more than marginal accuracy gains for 4 categories.

---

## 6. WebSocket Streaming

**Chosen:** Ollama streaming API (`stream: true`) forwarded token-by-token over Django Channels WebSocket

**Rejected:** REST polling, Server-Sent Events, batch response

**Why:** Users perceive LLM responses as ~3× faster with streaming even when total latency is identical. The spec required WebSocket for the typing indicator anyway — streaming tokens adds no additional infrastructure. Ollama's streaming API returns NDJSON that we iterate line-by-line.

**Implementation challenge:** Django Channels consumers are async but `agent.stream_message()` is a sync generator (because `httpx.stream()` is sync). I use `sync_to_async` + `asyncio.run_coroutine_threadsafe` to bridge the gap. This is slightly complex but keeps the service layer sync (easier to test).

---

## 7. Lead Scoring: Weighted Intent Events

**Chosen:** Additive score: general=1, availability=5, pricing=10, conversion=25

**Rejected:** Equal weights, ML-based propensity score, time-decayed score

**Why:** This wasn't in the spec — I added it as the "obviously better" feature. A real sales assistant needs to know who's hot. The weights reflect sales reality: someone who asks about pricing is 10× more valuable than someone who asks a general question. Someone who says "I want to order" is worth 25× a general query. The weights are transparent and adjustable.

**AI helped with:** Suggesting equal weights (1:1:1:1). I changed the weights after thinking about conversion funnels.

---

## 8. SOLID Architecture

The service layer uses abstract base classes (`IEmbedder`, `IRetriever`, `ILLMClient`, `IChunker`, `IIntentClassifier`) registered in `settings.SERVICE_CLASSES`. The factory resolves concrete classes at runtime via `import_string`.

This means:
- Tests inject mocks by changing `SERVICE_CLASSES` in `settings/test.py` — no model loading, no HTTP calls
- Swapping from Ollama to OpenAI is one settings change, no code change
- The `AgentHandler` depends on interfaces, not concrete classes — fully testable in isolation

**AI helped with:** The general pattern. I added the `reset_cache()` function after discovering that `@lru_cache` singletons persisted between test cases and caused mock/real class bleed-through.

---

## 9. What I Added That Wasn't Asked For

- **Lead Intelligence Dashboard** (`/admin/leads`) — shows lead scores, intent timelines, and message counts. Sales teams need to know who to call next. This is "obviously better" without being asked.
- **Inline quote request form** (CTACard) — when a prospect says "I want to buy", the chat widget renders an inline form to capture name + email. No page redirect, no friction.
- **Answer quality eval script** (`eval/eval_quality.py`) — 10 golden Q&A pairs, semantic similarity scoring, intent accuracy. Tests answer quality, not just HTTP 200.
- **Business-ready production architecture plan** — implemented a clear path from demo to SaaS: organization/project tenancy boundaries, project-scoped retrieval isolation, project/org provider routing with private keys and platform fallback, and usage metering events for governance and billing.
- **Client-safe workspace separation** — data and behavior are scoped per project so multiple clients can share one platform without cross-project leakage in retrieval, chat behavior, or reporting.
- **Easy document ingestion flow** — implemented asynchronous ingestion jobs with lifecycle status (`queued/running/succeeded/failed`), retries, warm-worker optimization, and UI status polling so users can upload documents and keep working while indexing completes.
- **Guided chat readiness UX** — added prerequisite checks and auth guards so users are guided into the right flow (select project -> ingest docs -> open chat) instead of encountering runtime failures.
- **LLM-generated onboarding copy** — added a welcome-message generation endpoint based on uploaded documents, with strict length caps and fallback normalization so each project gets sensible, domain-aware first-contact messaging.

---

## 10. What I'd Do With More Time

- **Re-ranking:** Add a cross-encoder (e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2`) on top of vector retrieval to improve chunk selection quality.
- **Ingestion throughput scaling:** Add queue prioritization and autoscaled worker pools (for example separate queues for small vs large documents) to improve ingest latency at higher tenant volumes.
- **Lead authentication:** Currently `lead_id` is a UUID passed from the client — trivially spoofable. Production needs a proper session + HMAC verification.
- **HyDE (Hypothetical Document Embeddings):** Generate a hypothetical answer, embed it, then retrieve — often outperforms query embedding for complex questions.
- **Webhook on conversion:** Fire a webhook to a CRM (HubSpot, Salesforce) when `handoff_triggered=True` so the sales team gets a real-time notification.
