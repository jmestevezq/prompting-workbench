# Backend Components

## `app/main.py` — Application Entry Point

FastAPI application factory. Configures CORS (only `http://localhost:5173` is allowed — the Vite dev server), registers all routers, and runs `init_db()` on startup via the `lifespan` context manager.

Registered routers: `agents`, `fixtures`, `sessions`, `transcripts`, `autoraters`, `classification`, `generation`, `settings`, `chat`.

---

## `app/config.py` — Configuration

A single `Settings` class that reads environment variables on import. Loaded from a `.env` file two directories up from the module (project root). Can be mutated at runtime by the settings router (in-process only, not persisted to disk).

| Setting | Env Var | Default |
|---|---|---|
| Gemini API key | `GEMINI_API_KEY` | `""` |
| SQLite DB path | `DB_PATH` | `./workbench.db` |
| Default model | `DEFAULT_MODEL` | `gemini-2.5-pro` |
| Batch concurrency | `BATCH_CONCURRENCY` | `5` |
| Code execution timeout | `CODE_EXECUTION_TIMEOUT` | `10` |

A module-level `settings` singleton is exported and used throughout the application.

---

## `app/database.py` — Database Layer

### Schema

Defines 13 tables inline in `SCHEMA_SQL`. All IDs are `TEXT PRIMARY KEY` (UUID4 strings). JSON-valued fields are stored as `TEXT` and serialized/deserialized in Python. Foreign keys are enabled.

On startup, the schema is applied (idempotently, all `CREATE TABLE IF NOT EXISTS`). A migration check adds the `eval_tags` column to `eval_runs` if it is missing.

If the `agents` table is empty, seed data is automatically loaded from `backend/seed_data/seed.json`.

### `get_db()`

Opens a new aiosqlite connection, configures `WAL` journal mode and `foreign_keys=ON`, and returns the connection. The caller is responsible for closing it (always done in a `finally` block). Each request opens and closes its own connection — there is no connection pool.

### `init_db()`

Called once at server start. Runs schema DDL, applies migrations, seeds initial data.

---

## Routers

### `app/routers/agents.py` — Agent CRUD + File Import

Prefix: `/api/agents`

**Core CRUD:**

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | List all agents, ordered by creation time |
| `POST` | `/` | Create a new agent |
| `GET` | `/{agent_id}` | Get a single agent |
| `PUT` | `/{agent_id}` | Partial update (name, system_prompt, model, tool_definitions) |
| `DELETE` | `/{agent_id}` | Delete agent + all child versions, sessions, turns |

**File-based agent import:**

| Method | Path | Description |
|---|---|---|
| `GET` | `/folders/available` | List agent folder names under `AGENTS_DIR` |
| `POST` | `/import/{folder_name}` | Import (or re-import) an agent from a folder |

On import, the agent's `agent.yaml` + `prompt.ftl` are loaded via `agent_loader.py`, rendered, and stored in the DB. A base `agent_versions` record is created (or updated on re-import). The `agent_folder` column links the DB record back to the source directory.

**Prompt versioning (legacy):**

| Method | Path | Description |
|---|---|---|
| `GET` | `/{agent_id}/versions` | List prompt versions (legacy hash-based snapshots) |
| `POST` | `/{agent_id}/versions` | Snapshot current agent prompt as a new version |
| `POST` | `/{agent_id}/versions/{version_id}/label` | Update a human label on a version |

**Agent versions (new, full snapshots):**

| Method | Path | Description |
|---|---|---|
| `GET` | `/{agent_id}/agent-versions` | List all versions (base first, then UI versions by date) |
| `POST` | `/{agent_id}/agent-versions` | Create a version from UI edits |
| `PUT` | `/{agent_id}/active-version?version_id=` | Switch the active version |
| `GET` | `/{agent_id}/template` | Get raw template + resolved variables for the active version |

Each `agent_versions` record stores the full `raw_template`, `variables`, `variable_definitions`, `system_prompt`, `tool_details`, `widget_details`, and `tools` list. The `source` field is `"file"` for imported versions or `"ui"` for manually created ones. `is_base=1` marks the canonical version imported from disk.

### `app/routers/fixtures.py` — Fixture CRUD

Prefix: `/api/fixtures`

Standard CRUD for data fixtures (user profiles, transaction lists). The `data` field is an arbitrary JSON object stored as TEXT.

### `app/routers/sessions.py` — Session Management

Prefix: `/api/sessions`

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | List all sessions |
| `POST` | `/` | Create a session (agent_id + optional fixture_ids) |
| `GET` | `/{session_id}` | Get a single session |
| `GET` | `/{session_id}/turns` | List turns (`active_only=true` by default) |

Sessions are the link between an agent configuration and a specific conversation. Turns are write-only via the WebSocket; this router provides read access.

### `app/routers/transcripts.py` — Transcript Management

Prefix: `/api/transcripts`

Full CRUD plus bulk import (`POST /import`). Supports filtering by `source` (query param, handled in SQL) and `tag` (query param, filtered in Python after fetch — since tags are stored as JSON). Each transcript has a `labels` dict (ground-truth evaluation labels) and a `tags` list (for filtering and search).

### `app/routers/autoraters.py` — Autorater Evaluation

Prefixed without a common prefix (routes are `/api/autoraters` and `/api/eval/*`).

**Autorater CRUD:** Standard list/create/get/update.

**Eval Run:**
- `POST /api/eval/run` creates an `eval_run` record and starts a background task (`_execute_eval_run`).
- The background task loads transcripts, sends each through the autorater prompt via Gemini (concurrently), parses the JSON response, computes per-tag precision/recall/F1 (when `eval_tags` are specified), and updates the `eval_run` record.
- `GET /api/eval/runs/{run_id}/diff/{other_id}` compares two eval runs by aligning results on `transcript_id` and reporting which transcripts changed.

**Ground truth matching:** For each transcript, labels are like `{"safety": "P", "tool_usage": "N"}` where `P`=positive example (autorater should say "pass") and `N`=negative. The autorater output is parsed for an `assessment` field (`pass`/`fail`). Precision/recall/F1 are computed per tag.

### `app/routers/classification.py` — Classification Evaluation

Routes: `/api/golden-sets`, `/api/classification/prompts`, `/api/classification/runs`, `/api/classification/run`.

**Golden Sets:** CRUD + bulk import. Each entry has `input_transactions`, `reference_transactions` (for dedup context), and `expected_output` (correctly categorized list).

**Classification Prompts:** CRUD. Prompt templates support `{{input_transactions}}`, `{{reference_list_1/2/3}}` placeholders.

**Classification Run:** Background task renders the prompt for each golden entry, calls Gemini, parses the JSON array response, compares with `matchers.match_transaction_lists()`, and computes `metrics.compute_classification_metrics()`.

### `app/routers/generation.py` — Transcript Generation

Prefix: `/api/generate`

`POST /api/generate/transcripts` — Takes reference transcript IDs, a generation instruction, count, and model. Constructs a meta-prompt embedding the reference transcripts and the instruction, calls Gemini, then parses the output using `[TRANSCRIPT_START]...[TRANSCRIPT_END]` delimiters (with fallbacks). Generated transcripts are saved with `source='generated'` and auto-tagged.

### `app/routers/settings.py` — Runtime Settings

Prefix: `/api/settings`

`GET` returns current settings (with `has_api_key` flag instead of exposing the key). `PUT` mutates the in-process `Settings` singleton — changes are lost when the server restarts.

### `app/routers/chat.py` — WebSocket Chat

`WS /ws/chat/{session_id}`

Manages a dictionary of active `SessionState` objects keyed by session ID. On first connection, loads the session from DB. On subsequent connections to the same session ID, reuses the in-memory state.

Dispatches incoming messages:

| Type | Handler |
|---|---|
| `user_message` | Calls `agent_runtime.run_agent_turn()`, streams events |
| `rerun_turn` | Calls `agent_runtime.rerun_turn()`, streams events |
| `swap_fixture` | Calls `state.swap_fixtures()`, sends confirmation |
| `set_tool_override` | Updates `state.tool_overrides` dict |
| `clear_tool_overrides` | Clears `state.tool_overrides` |

On `WebSocketDisconnect`, the session is removed from memory.

---

## Services

### `app/services/agent_loader.py` — File-based Agent Loading

Loads a complete agent definition from a folder on disk. Used by the import endpoint.

**`AgentSnapshot` dataclass**

Fully resolved agent definition with all fields: `name`, `version`, `model`, `description`, `system_prompt` (rendered), `raw_template` (original .ftl), `variables` (resolved values), `variable_definitions` (original YAML defs), `tools`, `widgets`, `tool_details`, `widget_details`, `tool_definitions`.

**`load_agent_from_folder(folder_path)`**

Resolution pipeline:
1. Parse `agent.yaml` — extracts name, version, model, description, tool list, widget list, variable definitions, Gemini function declarations
2. Resolve variables in three passes:
   - Pass 1: `static` variables → direct value from YAML
   - Pass 2: `programmatic` variables → `exec()` a Python snippet that sets `result`; `agent` dict is available in scope
   - Pass 3: `template` variables → render a sub-`.ftl` file with resolved vars so far
3. Build template model dict
4. Load and render `prompt.ftl` via `FreemarkerRenderer`
5. Return `AgentSnapshot`

**`list_agent_folders(agents_dir)`**

Returns a sorted list of folder names that contain an `agent.yaml` file.

---

### `app/services/freemarker.py` — FreeMarker Template Renderer

A pure-Python recursive descent parser implementing a subset of the FreeMarker template language.

**Supported syntax:**
- Interpolation: `${expr}`, `${a.b.c}`, `${a.b?size}`, `${a.b?string}`
- List directive: `<#list expr as var>...</#list>` with nested lists
- Conditionals: `<#if expr>...<#elseif expr>...<#else>...</#if>`
- Loop built-ins on the loop variable: `?index`, `?counter`, `?has_next`, `?is_first`, `?is_last`
- Array indexing: `items[0]`
- Comparison operators: `==`, `!=`, `>`, `<`, `>=`, `<=`, `gt`, `lt`, `gte`, `lte`
- Logical operators: `&&`, `||`, `!`
- Comments: `<#-- ... -->`
- String, numeric, and boolean literals

**`FreemarkerRenderer.render(template, model)`**

Tokenizes the template with `_tokenize()` then renders with `_Parser`. Raises `FreemarkerError` on unresolved variables or malformed directives.

---

### `app/services/gemini_client.py` — Gemini API Wrapper

Wraps the `google-genai` SDK with project-specific conventions.

**`build_tool_declarations(tool_definitions)`**
Converts a list of raw dicts (from DB) into a `types.Tool` with `FunctionDeclaration` objects.

**`build_contents(history, user_message=None)`**
Converts the workbench's internal conversation history format into the Gemini `Content` objects. This is the ADK-alignment method — see `docs/ADK_ALIGNMENT.md` for detail. Groups consecutive `tool_call` turns into one `Content(role="model")` and consecutive `tool_response` turns into one `Content(role="user")`.

**`generate(system_prompt, model, contents, tools=None)`**
Calls `client.aio.models.generate_content()` (async, non-blocking). Returns:
- `text` — concatenated text parts
- `function_calls` — list of `{name, args}` dicts
- `raw_request` — serialized request for debugging
- `raw_response` — serialized response for debugging
- `token_usage` — `{prompt_tokens, completion_tokens, total}`

`automatic_function_calling` is explicitly disabled so the loop is controlled manually.

Serialization helpers (`_serialize_contents`, `_serialize_tool`, `_serialize_response`, `_serialize_schema`) handle the SDK's complex object graph.

---

### `app/services/agent_runtime.py` — Agent Loop

**`SessionState`**

In-memory state for one active chat session:
- `agent_config` — loaded from DB (name, system_prompt, model, tool_definitions)
- `fixtures` — dict keyed by fixture type (e.g. `{"transactions": [...], "user_profile": {...}}`)
- `fixture_ids` — list of active fixture IDs
- `tool_overrides` — session-level override dict
- `conversation_history` — list of turn dicts

`load()` reads all data from DB. `swap_fixtures(new_ids)` updates DB and reloads fixture data into memory.

**`run_agent_turn(state, user_message=None, ...)`** — `AsyncGenerator`

The main agent loop, yielding events for streaming:

1. Optionally saves the user turn to DB
2. Builds `contents` from conversation history via `gemini_client.build_contents()`
3. Loops up to `max_iterations=10`:
   - Calls `gemini_client.generate()`
   - If response contains `function_calls`: executes all tools in parallel via `asyncio.gather()` (one executor task per tool), groups them into ADK-style batched Content objects, continues loop
   - If response contains text: simulates streaming by yielding 3-word chunks
4. Saves the agent turn to DB with all debug data
5. Yields `turn_complete` with the full turn object

Tool calls are executed via `_execute_tool_call()`, which checks overrides first (per-call override → session-level override → mock tool execution).

**`rerun_turn(state, turn_id, overrides)`** — `AsyncGenerator`

Loads the turn at `turn_id`, marks it and all subsequent turns as `is_active=0`, rebuilds history up to that point, then delegates to `run_agent_turn()` with the provided overrides (system_prompt, tool_responses, modified_history).

---

### `app/services/mock_tools.py` — Tool Handlers

Implements the mock tool layer that backs the agent's tool calls.

**`execute_tool(tool_name, args, fixtures, context=None)`**

Dispatches to a handler by name. Supports both camelCase tool names (production-style) and snake_case (legacy/backward compat):
- `getTransactionHistory` / `fetch_transactions` → `_fetch_transactions`
- `getTransactionHistoryAggregations` → `_fetch_transactions_aggregations`
- `getUserProfile` / `get_user_profile` → `_get_user_profile`
- `codeExecution` / `execute_code` → `_execute_code`

Returns `{"error": "Unknown tool: ..."}` for unregistered tools.

**`_fetch_transactions(args, fixtures)`**

Reads `fixtures["transactions"]`, applies filters via `_apply_filters()` (category, merchant_name, date range, amount range), then either groups results by a field (`group_by` arg) or sorts and paginates (by `responseLimit`).

**`_fetch_transactions_aggregations(args, fixtures)`**

Same filtering as above, then computes `sum/count/average/min/max` of amounts — optionally grouped by a field.

**`_get_user_profile(args, fixtures)`**

Returns `fixtures["user_profile"]` as-is.

**`_execute_code(args, fixtures, context)`**

Delegates to `code_sandbox.execute_agent_code()` with transaction and profile data injected.

---

### `app/services/code_sandbox.py` — Code Execution Sandbox

Runs agent-generated Python code in an isolated subprocess with a configurable timeout.

**`execute_agent_code(code, context, timeout=10)`**

1. Serializes the `context` dict to JSON
2. Wraps the user code in a preamble that imports JSON and exposes `transactions` and `user_profile` variables
3. Writes the wrapper to a temp file, runs it with `python3`, captures stdout/stderr
4. Cleans up the temp file in all cases
5. Returns `{stdout, stderr, returncode}` — on timeout, returns error dict with returncode -1

Security considerations: no filesystem or network restrictions on the subprocess. This is a developer-only tool, not a production sandbox.

---

### `app/services/batch_runner.py` — Concurrent Batch Processing

**`run_batch(items, process_fn, concurrency=None)`**

Generic async batch executor. Creates a `Semaphore(concurrency)` and runs `process_fn` on each item concurrently, bounded by the semaphore. Uses `asyncio.gather()` so all results are returned in the same order as `items`. The `concurrency` param defaults to `settings.BATCH_CONCURRENCY`.

Used by both autorater eval and classification eval.

---

### `app/services/matchers.py` — Match Strategies

**`MatchStrategy` (abstract)**

Interface with one method: `match(predicted: dict, expected: dict) -> dict` returning `{match: bool, ...details}`.

**`ExactCategoryMatch`**

Compares only the `category` field of two transaction dicts. Case-sensitive exact match.

**`match_transaction_lists(predicted, expected, strategy="exact_category")`**

Aligns two lists by position (index-based, not by transaction ID). Returns:
- `total` — number of pairs compared (max of both list lengths)
- `matches` — number of matching pairs
- `match_rate` — fraction correct
- `details` — per-pair match result

---

### `app/services/metrics.py` — Evaluation Metrics

**`compute_binary_metrics(results)`**

For autorater eval. Computes from a list of result dicts:
- `accuracy` — fraction of correct predictions
- `per_label` — per label key: precision, recall, F1, TP/FP/FN/TN
- `confusion_matrix` — per label key: counts of `"ground_truth → predicted"` pairs

**`compute_classification_metrics(results)`**

For classification eval. Computes from a list of result dicts (each with `predicted_output` and `expected_output` lists):
- `exact_match_rate` — fraction where all transactions match
- `per_category` — per category: precision, recall, F1, count

Per-category metrics use a count-based approximation (min of predicted/true counts as TP, surplus as FP/FN).

---

## `backend/agents/` — Agent Folder Structure

Agent definitions live under `backend/agents/<folder-name>/`. Each folder contains:

- `agent.yaml` — Agent metadata, variable definitions, tool/widget lists, Gemini function declarations
- `prompt.ftl` — Main system prompt template (FreeMarker syntax)
- Optional sub-templates referenced by `template` type variables

**`agent.yaml` structure:**

```yaml
name: My Agent
version: "1.0"
model: gemini-2.5-pro
description: "..."

variables:
  myStaticVar:
    type: static
    value: "hello"
  myProgrammaticVar:
    type: programmatic
    code: |
      result = some_computation()
  myTemplateVar:
    type: template
    path: sub-template.ftl

tools:
  - TOOL_NAME_1

widgets:
  - WIDGET_NAME_1

tool_definitions:
  - name: TOOL_NAME_1
    description: "..."
    parameters:
      type: OBJECT
      properties:
        myParam:
          type: STRING
```

The bundled `sherlock-finance` agent demonstrates all variable types, multi-tool declarations, and UI widget definitions.

---

## Schemas (`app/schemas/`)

Pydantic v2 models for request validation and response serialization:

- `agent.py` — `AgentCreate`, `AgentUpdate`, `AgentResponse`, `PromptVersionCreate`, `PromptVersionResponse`, `PromptVersionLabelUpdate`, `AgentVersionCreate`, `AgentVersionResponse`, `AgentImportResponse`, `AgentTemplateResponse`
- `fixture.py` — `FixtureCreate`, `FixtureUpdate`, `FixtureResponse`
- `session.py` — `SessionCreate`, `SessionResponse`, `TurnResponse`
- `transcript.py` — `TranscriptCreate`, `TranscriptUpdate`, `TranscriptResponse`, `TranscriptImport`
- `autorater.py` — `AutoraterCreate`, `AutoraterUpdate`, `AutoraterResponse`, `EvalRunCreate`, `EvalRunResponse`, `EvalResultResponse`
- `classification.py` — `GoldenTransactionCreate/Update/Response/Import`, `ClassificationPromptCreate/Update/Response`, `ClassificationRunCreate/Response`, `ClassificationResultResponse`
