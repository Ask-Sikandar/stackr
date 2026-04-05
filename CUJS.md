# Critical User Journeys (CUJs)

Product: Memox AI Sales Assistant
Date: 2026-04-05
Purpose: Define the user journeys we will design for before implementing a production UI.

## Scope

These CUJs cover:
- user onboarding and project setup
- document upload and ingestion
- first and repeat chat usage
- lead review and follow-up
- the new requirement: user-customizable intro chat message during project creation or document ingestion

## Primary Personas

1. Workspace Admin
Owns setup, creates organizations/projects, ingests documents, sets assistant behavior.

2. Sales Rep
Uses chat in live conversations with prospects and needs fast, accurate responses.

3. Sales Manager
Monitors lead scores and intent patterns to prioritize follow-up.

4. Operations/Knowledge Maintainer
Keeps product docs current and re-ingests when content changes.

## CUJ Priority Map

| ID | Journey | Persona | Priority |
|---|---|---|---|
| CUJ-01 | Sign up and access workspace | Workspace Admin | P0 |
| CUJ-02 | Create organization and project | Workspace Admin | P0 |
| CUJ-03 | Set intro chat message at setup | Workspace Admin | P0 |
| CUJ-04 | Upload and ingest documents | Workspace Admin / Ops | P0 |
| CUJ-05 | Update intro chat message during ingestion flow | Workspace Admin / Ops | P0 |
| CUJ-06 | Start first chat with prerequisites | Sales Rep | P0 |
| CUJ-07 | Handle active chat and response states | Sales Rep | P1 |
| CUJ-08 | Review lead intelligence and intent timeline | Sales Manager | P1 |
| CUJ-09 | Maintain knowledge base (re-ingest and validate) | Ops | P1 |

---

## CUJ-01: Sign Up And Access Workspace

Goal:
A new user can register, authenticate, and reach the portal without confusion.

Trigger:
User lands on sign-up or login page.

Preconditions:
- User has no active session.

Main flow:
1. User enters identity details and submits.
2. System creates account and returns tokens.
3. User lands on portal with session saved.

Edge/error flow:
- Duplicate email, weak password, or API error shows inline validation.

Success criteria:
- Time to portal under 60 seconds for first-time user.
- Authentication errors are understandable and recoverable.

---

## CUJ-02: Create Organization And Project

Goal:
Admin can create/select organization and create/select project quickly.

Trigger:
User opens portal after auth.

Preconditions:
- Valid session token.

Main flow:
1. User creates org (if none exists).
2. User creates project.
3. Project becomes active workspace context.

Edge/error flow:
- Missing org context disables project creation with clear guidance.

Success criteria:
- User can reach a selected project in under 2 minutes.

---

## CUJ-03: Set Intro Chat Message At Setup (New Requirement)

Goal:
Admin defines the first assistant message users see when chat opens.

Trigger:
During project creation/edit.

Preconditions:
- Organization selected.

Main flow:
1. User opens project create/edit form.
2. User sets:
   - assistant display name
   - intro message (multi-line)
   - optional starter prompts (up to 3)
3. User previews chat header and first message.
4. User saves settings.

Edge/error flow:
- Empty intro message falls back to system default only if user never configured one.
- Over max length shows validation with remaining characters.

Success criteria:
- 100% of newly created projects can define a custom intro.
- Preview and saved result match exactly.

Required behavior:
- Intro message is project-scoped (tenant isolation).
- Intro is loaded from backend config, never hardcoded in UI.

---

## CUJ-04: Upload And Ingest Documents

Goal:
Admin/Ops can add knowledge documents and start ingestion reliably.

Trigger:
User opens Documents page.

Preconditions:
- Active project selected.

Main flow:
1. User enters title/content and uploads.
2. Document appears in list as pending.
3. User starts ingestion.
4. UI shows queued/running/succeeded or failed status.

Edge/error flow:
- Upload without project is blocked with direct path back to project selection.
- Ingestion queue failures show retry action.

Success criteria:
- Ingestion status updates live until terminal state.
- Users can continue working while ingestion progresses.

---

## CUJ-05: Update Intro Chat Message During Ingestion Flow (New Requirement)

Goal:
User can set or refine intro message while managing documents.

Trigger:
User uploads or re-ingests docs and wants assistant intro to match new knowledge set.

Preconditions:
- Active project selected.

Main flow:
1. User opens a "Chat Experience" panel on Documents page.
2. User edits intro message and optional starter prompts.
3. User saves before or after ingestion.
4. Next chat session uses latest saved intro.

Edge/error flow:
- Save conflict (stale data) prompts user to refresh or overwrite.
- If save fails, previous intro remains active and user sees non-destructive error.

Success criteria:
- Intro update can be completed in under 30 seconds.
- Next chat load reflects updated intro without app refresh hacks.

Required behavior:
- Both project creation flow and document ingestion flow can update the same project-level intro config.
- No duplicate conflicting settings models.

---

## CUJ-06: Start First Chat With Prerequisites

Goal:
Sales rep can open chat only when workspace is valid and has at least one ingested doc.

Trigger:
User clicks Open Chat.

Preconditions:
- User authenticated.
- Project selected.
- At least one document in project has processed=true.

Main flow:
1. System validates prerequisites.
2. If valid, opens chat page and connects websocket.
3. Assistant renders configured intro message.

Edge/error flow:
- Missing ingested docs routes user back to Documents with actionable message.
- WS connection issue shows reconnect state and preserves typed input.

Success criteria:
- First chat launch success > 95% in normal network conditions.

---

## CUJ-07: Handle Active Chat And Response States

Goal:
Rep can ask questions and understand assistant response confidence and provenance.

Trigger:
Conversation is active.

Main flow:
1. User sends message.
2. UI shows pending state/typing.
3. Streamed or final response arrives.
4. Sources/components appear when available.

Edge/error flow:
- Backend error shows inline and allows resend.
- Temporary disconnect does not erase message history in session.

Success criteria:
- Perceived latency is clearly communicated.
- User can distinguish system state: connecting, sending, receiving, failed.

---

## CUJ-08: Review Lead Intelligence And Intent Timeline

Goal:
Manager can prioritize high-intent leads from scored activity.

Trigger:
User opens Leads page.

Main flow:
1. System loads lead rows for active project.
2. User sees score, message count, intent trail, last seen.
3. User identifies highest-priority leads for follow-up.

Edge/error flow:
- Partial event-load failures do not blank the table; show row-level fallbacks.

Success criteria:
- User can identify top 3 leads in under 20 seconds.

---

## CUJ-09: Maintain Knowledge Base (Re-Ingest And Validate)

Goal:
Ops can keep assistant answers current as docs change.

Trigger:
Product/pricing policy updates.

Main flow:
1. User uploads updated doc revision.
2. User re-ingests affected docs.
3. User validates behavior in chat using known test prompts.
4. User confirms lead/chat flows still operate.

Edge/error flow:
- Failed ingestion provides reason and retry path.

Success criteria:
- Knowledge update to available-in-chat in under 15 minutes for standard doc set.

---

## Production UI Acceptance Criteria (For Next Phase)

These are the quality gates for the implementation phase.

1. Information architecture
- Clear navigation between Portal, Documents, Chat, Leads.
- Persistent active organization/project context in header.

2. Form UX
- Inline validation, helper text, and autosave where appropriate.
- Dedicated editor UI for intro message with preview.

3. State handling
- Explicit empty, loading, success, and error states on every major screen.
- Retry affordances without requiring full page reload.

4. Chat experience
- Intro message, assistant name, and starter prompts come from saved project config.
- No hardcoded brand strings in chat widget.

5. Accessibility
- Keyboard-first interaction, visible focus states, semantic headings, color contrast >= WCAG AA.

6. Responsiveness
- Works cleanly on 360px mobile through wide desktop.

7. Trust and safety UX
- Clear source display and failure transparency.
- Prevent accidental destructive actions with confirmations.

8. Observability
- Track conversion funnel events: signup, project create, intro configured, doc ingested, first chat message, lead score threshold reached.

## Functional Requirements Derived From CUJs (Intro Message)

1. Add project-level chat configuration fields (minimum)
- assistant_display_name
- intro_message
- starter_prompts (array of strings, optional)

2. Expose config in APIs used by portal/documents/chat screens.

3. Load intro message from backend config in chat initialization.

4. If no project custom intro exists, use a single platform default stored server-side (not frontend hardcoded).

5. Support editing intro config in both:
- project setup flow
- documents/ingestion flow

6. Preserve tenant isolation for all intro settings and reads.

## Implementation Order Recommendation

1. Backend config model + serializer updates for project chat configuration.
2. Project create/edit UI with intro editor and preview.
3. Documents page chat-experience panel (same config endpoint).
4. Chat widget initialization from config endpoint.
5. Production visual redesign using these journeys and acceptance criteria.
