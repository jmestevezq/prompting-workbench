# Architecture Assessment and Improvement Recommendations

## What Works Well

### 1. Clear Module Boundaries

The four application domains (Playground, Autorater, Generator, Classification) are well-separated — both in the backend (one router per domain) and in the frontend (one page per domain). Adding a fifth module would not require touching existing code.

### 2. ADK-Aligned Agent Loop

The agent runtime in `agent_runtime.py` and `gemini_client.py` deliberately mirrors the Google ADK's internal behavior: grouping multiple function calls into one `Content(role="model")`, executing tools in parallel, grouping responses into one `Content(role="user")`. This means behaviors observed in the workbench translate directly to the production ADK environment. See `docs/ADK_ALIGNMENT.md`.

### 3. Extensible Matching Layer

The `MatchStrategy` interface in `matchers.py` is a clean extension point. Adding fuzzy matching, synonym maps, or semantic similarity matching does not require touching the eval pipeline.

### 4. Rerun and Debugging Capability

The turn-level rerun system (marking old turns `is_active=0`, storing `parent_turn_id`, allowing prompt/tool overrides) is the workbench's highest-value feature. It enables rapid iteration without restarting conversations.

### 5. Background Task Isolation

Batch evaluation runs (autorater and classification) execute in FastAPI `BackgroundTasks`, so the HTTP response returns immediately and the client can poll for completion. This prevents request timeouts on large eval sets.

### 6. Streaming Architecture

The WebSocket streaming via `AsyncGenerator` in `run_agent_turn` is well-designed. Events are yielded granularly (`tool_call`, `tool_response`, `agent_chunk`, `turn_complete`), giving the UI enough information to build a rich real-time experience.

---

## Issues and Risks

### 1. No Connection Pooling — DB Opens Per Request

**Current:** Every API handler calls `get_db()`, which opens a new SQLite connection, executes the query, then closes the connection. Under concurrent load this is acceptable for SQLite (WAL mode handles concurrent readers/writers), but it introduces per-request overhead.

**Recommendation:** Use a connection pool (e.g. `aiosqlite` with a context manager that reuses connections per request, or switch to `SQLAlchemy` async with a pool). At minimum, inject the DB connection as a FastAPI dependency so it can be reused across function calls within the same request.

### 2. In-Process Session State Is Not Safe Under Multiple Workers

**Current:** `active_sessions: dict[str, SessionState]` in `chat.py` is a module-level dict. This works fine with a single uvicorn worker. If the server is ever started with `--workers 2+`, sessions would be isolated per worker and a WebSocket reconnect could land on a different worker with no session state.

**Recommendation:** For the current single-developer use case this is fine. If multi-worker deployment is ever needed, session state should be moved to Redis or re-loaded from DB on each connection.

### 3. Settings Mutation Is In-Process Only

**Current:** `PUT /api/settings` mutates the `Settings` singleton in memory. Changes are lost on server restart.

**Recommendation:** Persist settings to the `.env` file or a separate settings table in SQLite. This is low priority for a dev-only tool but is surprising behavior when users set an API key in the UI and then restart the server.

### 4. Code Sandbox Has No Security Boundaries

**Current:** Agent-generated Python code runs in a subprocess with no filesystem, network, or resource restrictions. It has access to the full system Python environment.

**Recommendation:** This is acceptable for a local developer tool. If this is ever deployed as a shared service, add: subprocess resource limits (`ulimit`), a restricted Python namespace, or use a true sandbox (gVisor, Firecracker). Document the current behavior clearly.

### 5. Tag Filtering Is Post-Fetch

**Current:** The transcript list endpoint fetches all transcripts from the DB, then filters by tag in Python because tags are stored as JSON arrays.

```python
results = [r for r in results if tag in r["tags"]]
```

**Recommendation:** Use SQLite's JSON functions to filter at the database level:
```sql
WHERE json_each.value = ? FROM transcripts, json_each(tags)
```
This matters at scale (thousands of transcripts). For current usage it's fine.

### 6. Streaming Simulation Is Not Real Streaming

**Current:** Text streaming in `agent_runtime.py` is simulated by splitting the final response into 3-word chunks:

```python
words = final_text.split(" ")
for i in range(0, len(words), 3):
    chunk = " ".join(words[i:i+3])
    yield {"type": "agent_chunk", "content": chunk}
```

Gemini's `generate_content` doesn't return a true streaming response in this code — it waits for the full response, then simulates streaming.

**Recommendation:** Use `client.aio.models.generate_content_stream()` (Gemini's streaming API) to yield chunks as they arrive. This would provide real time-to-first-token and a smoother UX. The `generate()` function signature would need to change to return an async generator.

### 7. Duplicate Code in Row-to-Dict Helpers

**Current:** Every router module has private `_row_to_X()` helper functions that manually extract and deserialize JSON fields. This pattern is repeated ~10 times across the codebase with slight variations.

**Recommendation:** Consolidate into a generic DB helper or use ORM-style dataclass mapping. The risk is that a JSON field gets missed in one helper — as happened during the `eval_tags` column migration.

### 8. Classification Metrics Use Count-Based Approximation

**Current:** `_compute_per_category_metrics()` uses `min(pred_count, true_count)` as TP, which is not the standard per-instance precision/recall calculation. It's an approximation that works for balanced data but can be misleading.

**Recommendation:** Track per-transaction match status explicitly, then compute TP/FP/FN based on actual per-instance outcomes. The position-aligned matching in `match_transaction_lists` already provides this data.

### 9. No Auth or Rate Limiting

**Current:** The API has no authentication, no rate limiting, and no request size limits. Any process with network access can read or delete all data.

**Recommendation:** For local development this is intentional (no-auth is a design goal). Document it clearly. If ever deployed as a shared service, add API key-based auth or OAuth.

### 10. Frontend Has No Error Boundaries

**Current:** React rendering errors will crash the entire application with a blank screen. There are no `ErrorBoundary` components.

**Recommendation:** Add an `ErrorBoundary` at the page level so errors in one page don't break navigation.

---

## Improvement Opportunities

### Short-Term (Low Effort, High Value)

1. **Real Gemini streaming** — switch to `generate_content_stream()` for genuine latency reduction
2. **DB dependency injection** — use FastAPI's `Depends()` to manage DB connections per request
3. **Settings persistence** — write settings to SQLite instead of only mutating in memory
4. **Error boundaries in React** — wrap each page in an error boundary

### Medium-Term

5. **Per-instance classification metrics** — fix the approximation in `_compute_per_category_metrics`
6. **Tag filtering in SQL** — use JSON functions instead of post-fetch Python filter
7. **Transcript search** — full-text search on transcript content (SQLite FTS5)
8. **Eval run cancellation** — support cancelling a running background eval task
9. **Tool definition schema validation** — validate tool definitions against Gemini's schema format on create/update

### Longer-Term (V2)

10. **A/B prompt comparison** — run two prompt versions on the same input side-by-side
11. **Automated user agent** — let Gemini simulate a user for fully automated conversation generation
12. **CI regression detection** — auto-run eval suite on prompt save, block if regressions exceed threshold
13. **Cost tracking** — compute token cost estimates per session and eval run
14. **Conversation tree visualization** — show forked conversation branches as a tree
15. **Export to production format** — one-click export of agent config in the production ADK format
16. **Multi-worker safety** — move session state to Redis for horizontal scaling

---

## Code Quality Notes

- **Good:** The service layer is well-separated from the router layer. Business logic is in `services/`, not scattered in route handlers.
- **Good:** Pydantic schemas provide clear contracts at API boundaries.
- **Good:** The `MatchStrategy` pattern correctly anticipates future extension needs.
- **OK:** Error handling in background tasks is consistent (always updates status to `failed`).
- **OK:** The `_serialize_*` functions in `gemini_client.py` are verbose but necessary due to SDK object complexity. A utility approach would help.
- **Weak:** No structured logging. Errors surface to the client as HTTP 500 or as `{"type": "error"}` WebSocket messages, but nothing is logged to stdout for the developer running the server.
- **Weak:** No input validation on tool definitions or fixture data schemas. Malformed data can cause subtle runtime errors deep in the agent loop.
