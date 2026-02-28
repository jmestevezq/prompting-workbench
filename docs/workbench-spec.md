---
title: "Prompt Engineering Workbench — Design Spec"
type: spec
status: draft
created: 2026-02-28
tags: [prompt-engineering, eval, gemini, agent, sherlock, enigma]
---

# Prompt Engineering Workbench

## Problem

Iterating on agent prompts, autoraters, and transaction classification prompts takes 10–40 min per cycle in the current stack. Tool overrides are limited. No way to generate synthetic conversations. No regression detection. This kills velocity.

## Solution

A local-first web application (Python backend + TypeScript frontend) that replicates the agent runtime with mock tools, enables prompt inspection/editing/rerun at turn level, and provides batch evaluation for autoraters and classification prompts.

**Non-goals:** Production deployment of the agent, real tool integrations, multi-user auth, real-time collaboration.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Frontend (React/TS)            │
│  ┌───────────┐ ┌──────────┐ ┌─────────────────┐ │
│  │  Agent     │ │ Autorater│ │  Classification │ │
│  │  Playground│ │ Eval     │ │  Eval           │ │
│  └─────┬─────┘ └────┬─────┘ └───────┬─────────┘ │
│        │             │               │           │
│        └─────────────┼───────────────┘           │
│                      │ REST + WebSocket          │
└──────────────────────┼───────────────────────────┘
                       │
┌──────────────────────┼───────────────────────────┐
│              Backend (FastAPI/Python)             │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │  Agent   │ │  Batch   │ │  Data/Fixture    │  │
│  │  Runtime │ │  Runner  │ │  Manager         │  │
│  └────┬─────┘ └────┬─────┘ └────────┬─────────┘  │
│       │             │                │            │
│  ┌────┴─────────────┴────────────────┴─────────┐  │
│  │           Gemini API Client                  │  │
│  └──────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │           SQLite (DuckDB optional)            │  │
│  └──────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Backend | FastAPI + uvicorn | Async, WebSocket support, fast to build |
| Frontend | React + TypeScript + Vite | Fast dev loop, good for complex UI |
| UI Library | shadcn/ui + Tailwind | Fast to build, clean, no heavy deps |
| DB | SQLite via `aiosqlite` | Zero-config, file-based, good enough |
| Gemini | `google-genai` Python SDK | Official SDK, function calling support |
| Code Execution | `RestrictedPython` or subprocess sandbox | For agent code tool |
| Monorepo | Single repo, `backend/` + `frontend/` | Simple, one `make run` to start both |

### Deployment

Single container for Cloud Run (nice-to-have). FastAPI serves the built frontend as static files + API. SQLite file persisted via Cloud Run volume mount or GCS.

---

## Data Model (SQLite)

```sql
-- Agent configurations
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'gemini-2.5-pro',
    tool_definitions JSON NOT NULL,  -- static, defined once per agent
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Prompt versions (auto-saved on every change)
CREATE TABLE prompt_versions (
    id TEXT PRIMARY KEY,
    agent_id TEXT REFERENCES agents(id),
    system_prompt TEXT NOT NULL,
    tool_definitions JSON,
    version_hash TEXT NOT NULL,  -- sha256 of prompt + tools
    label TEXT,                  -- optional human label like "v3-fixed-math"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Data fixtures (user profiles, transactions, etc)
CREATE TABLE fixtures (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,  -- 'user_profile', 'transactions', 'reference_transactions'
    data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat sessions (agent playground)
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    agent_id TEXT REFERENCES agents(id),
    fixture_ids JSON,  -- array of fixture IDs active in this session
    prompt_version_id TEXT REFERENCES prompt_versions(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Individual turns within a session
CREATE TABLE turns (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    turn_index INTEGER NOT NULL,
    role TEXT NOT NULL,  -- 'user', 'agent', 'tool_call', 'tool_response', 'thought'
    content TEXT NOT NULL,
    -- Debug data: what actually went to Gemini
    raw_request JSON,    -- full request sent to Gemini API
    raw_response JSON,   -- full response from Gemini API
    tool_calls JSON,     -- extracted function calls
    tool_responses JSON, -- mock tool responses
    token_usage JSON,    -- {prompt_tokens, completion_tokens, total}
    -- Forking support
    parent_turn_id TEXT, -- if this is a rerun/fork, points to original
    is_active INTEGER DEFAULT 1,  -- 0 = replaced by a rerun
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transcripts (for autorater eval)
CREATE TABLE transcripts (
    id TEXT PRIMARY KEY,
    name TEXT,
    content TEXT NOT NULL,        -- raw transcript text
    parsed_turns JSON,            -- structured [{role, content, tool_call?, ...}]
    labels JSON NOT NULL,         -- {"safety": "pass", "tool_usage": "fail", ...}
    source TEXT DEFAULT 'manual', -- 'manual', 'generated', 'imported'
    tags JSON,                    -- ["safety-issue", "math-error", ...]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Autorater configurations
CREATE TABLE autoraters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    prompt TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'gemini-2.5-pro',
    output_schema JSON,  -- expected output structure
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Autorater evaluation runs
CREATE TABLE eval_runs (
    id TEXT PRIMARY KEY,
    autorater_id TEXT REFERENCES autoraters(id),
    prompt_version_hash TEXT,     -- snapshot of the autorater prompt
    transcript_ids JSON NOT NULL, -- which transcripts were evaluated
    status TEXT DEFAULT 'pending', -- pending, running, completed, failed
    metrics JSON,                 -- {precision, recall, f1, confusion_matrix, ...}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Individual autorater results per transcript
CREATE TABLE eval_results (
    id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES eval_runs(id),
    transcript_id TEXT REFERENCES transcripts(id),
    predicted_labels JSON NOT NULL,
    ground_truth_labels JSON NOT NULL,
    match BOOLEAN,
    raw_response JSON,  -- full Gemini response
    token_usage JSON
);

-- Transaction classification golden set
CREATE TABLE golden_transactions (
    id TEXT PRIMARY KEY,
    set_name TEXT NOT NULL,       -- group golden sets
    input_transactions JSON NOT NULL,
    reference_transactions JSON,  -- 3 reference lists for dedup context (structure TBD)
    expected_output JSON NOT NULL, -- labeled, deduped transactions
    tags JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Classification prompt configs
CREATE TABLE classification_prompts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    prompt_template TEXT NOT NULL, -- with {{placeholders}} for tx data
    model TEXT NOT NULL DEFAULT 'gemini-2.5-pro',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Classification eval runs
CREATE TABLE classification_runs (
    id TEXT PRIMARY KEY,
    prompt_id TEXT REFERENCES classification_prompts(id),
    prompt_version_hash TEXT,
    golden_set_name TEXT,
    status TEXT DEFAULT 'pending',
    metrics JSON,  -- {exact_match, precision, recall, f1_per_category, ...}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE classification_results (
    id TEXT PRIMARY KEY,
    run_id TEXT REFERENCES classification_runs(id),
    golden_id TEXT REFERENCES golden_transactions(id),
    predicted_output JSON NOT NULL,
    match_details JSON,  -- per-transaction match breakdown
    raw_response JSON,
    token_usage JSON
);
```

---

## Module 1: Agent Playground

### 1.1 Agent Configuration

The user defines an agent as:
- **System prompt** — editable text area, supports template variables
- **Model** — dropdown (gemini-2.5-pro, etc.)
- **Tool definitions** — static JSON array of Gemini function declarations, defined once per agent. Not expected to change frequently. All tools are always available.
- **Active fixtures** — selected user profile + transaction data sets

Transactions have the following core fields: `merchant_name`, `amount`, `category`. The tools include a `fetch_transactions` that supports grouping by columns (e.g., group by category, group by merchant).

Tool definitions follow the Gemini function calling schema:
```json
[
  {
    "name": "fetch_transactions",
    "description": "Fetch user transactions with optional filters and grouping",
    "parameters": {
      "type": "OBJECT",
      "properties": {
        "category": {"type": "STRING", "description": "Filter by category"},
        "merchant_name": {"type": "STRING", "description": "Filter by merchant name"},
        "date_from": {"type": "STRING", "description": "Start date YYYY-MM-DD"},
        "date_to": {"type": "STRING", "description": "End date YYYY-MM-DD"},
        "min_amount": {"type": "NUMBER"},
        "max_amount": {"type": "NUMBER"},
        "group_by": {"type": "STRING", "description": "Group results by column: category, merchant_name, etc."}
      }
    }
  },
  {
    "name": "get_user_profile",
    "description": "Get the current user's profile information",
    "parameters": {"type": "OBJECT", "properties": {}}
  },
  {
    "name": "execute_code",
    "description": "Execute Python code for calculations and data analysis",
    "parameters": {
      "type": "OBJECT",
      "properties": {
        "code": {"type": "STRING", "description": "Python code to execute"}
      },
      "required": ["code"]
    }
  }
]
```

### 1.2 Mock Tool Execution

Tools are backed by in-memory data from fixtures. The backend implements mock handlers:

- **`fetch_transactions`** — reads from the active transaction fixture, applies filters (category, merchant_name, date range, amount range) and group_by aggregation in Python. Returns filtered/grouped JSON array.
- **`get_user_profile`** — returns the active user profile fixture as-is.
- **`execute_code`** — runs the agent-generated Python code in a sandboxed subprocess with a timeout. Injects available data (fetched transactions) as variables. Returns stdout + result.

**Tester-driven tool override (two modes):**

**Mode A: Fixture-backed (default).** Tools read from the session's active fixtures and execute real filtering/grouping logic. Good for natural conversation testing.

**Mode B: Manual override.** The tester provides explicit tool responses that will be returned verbatim instead of executing the mock tool logic. This is stored in the session state (not visible to the agent). When a tool call is made, the backend checks if there's a manual override for that tool — if yes, returns the override; if no, falls back to Mode A.

The override is set via:
- The debug inspector (edit tool response before rerun)
- A `set_tool_override` WebSocket message:
```json
{
  "type": "set_tool_override",
  "overrides": {
    "fetch_transactions": {"data": [...], "active": true},
    "get_user_profile": {"data": {...}, "active": false}
  }
}
```
Overrides persist for the session until cleared. The agent never sees the override config — it only sees the tool response.

**Mid-conversation data swap:** The frontend can send a `SWAP_FIXTURE` WebSocket message with new fixture IDs. Backend updates the session's active fixtures. Next tool call uses the new data. No notification to the agent — it's a silent swap.

### 1.3 Chat Interface

**Left panel:** Chat conversation (user messages + agent responses). Agent responses render markdown. Widget markup (tables, charts) rendered inline if feasible, or shown as raw markup with syntax highlighting.

**Right panel (Debug Inspector):** For the selected turn, shows:
- Full prompt sent to Gemini (system prompt + conversation history + tool definitions)
- Tool calls made and their responses
- Raw Gemini API request/response JSON
- Token usage
- Latency

### 1.4 Turn-Level Rerun

User selects any agent turn → the debug inspector becomes editable:
- Can edit the system prompt for that turn
- Can edit tool responses (mock different data)
- Can edit prior user messages in the history
- Clicks "Rerun" → backend sends modified request to Gemini → new response replaces the selected turn
- Original turn preserved as `is_active=0`, new turn links via `parent_turn_id`
- Conversation after the rerun point is invalidated (greyed out), user can continue from the new response

### 1.5 Conversation Forking (v1.5)

From any turn, user can fork into a new session branch. Both branches preserved. UI shows a tree/timeline view of branches.

### 1.6 Prompt Versioning

Prompt versions are saved **only when the user explicitly requests it** (e.g., a "Save Version" button):
- Saves to `prompt_versions` with a content hash
- User provides a label ("v3-fixed-math", "added-guardrail")
- Prompt history view shows all versions with diffs
- No auto-save on every edit or rerun

---

## Module 2: Autorater Evaluation

### 2.1 Transcript Management

**Labeled set:** Manually curated transcripts with ground-truth labels. Each transcript has:
- Raw content — supports two formats:
  - **Text format:** `[AGENT]`, `[USER]`, `[TOOL_CALL]`, `[TOOL_RESPONSE]`, `[THOUGHT]` prefixed turns
  - **JSON format:** Array of `{role, content, tool_call?, tool_response?}` objects
- Parsed structured turns (auto-parsed from raw text, or used directly from JSON format)
- Labels: key-value pairs like `{"safety": "pass", "tool_usage": "correct", "math_accuracy": "fail"}`
- Tags for filtering: `["safety-issue", "math-error", "hallucination"]`

**Import:** Bulk import transcripts from JSON/JSONL files. UI for manual annotation/labeling.

**Unlabeled analysis:** Import arbitrary transcript lists for exploratory autorater runs (no metrics, just outputs).

### 2.2 Autorater Configuration

An autorater is:
- **Name** — descriptive identifier
- **Prompt** — the evaluation prompt template. Uses `{{transcript}}` placeholder for the input transcript.
- **Model** — which Gemini model to use
- **Output schema** — expected JSON structure. Each autorater returns an assessment and detailed explanations, e.g.:
  ```json
  {
    "assessment": "pass|fail",
    "explanation": "Detailed reasoning for the assessment..."
  }
  ```
  There is one autorater per evaluation dimension (safety, tool_usage, math_accuracy, etc.).

### 2.3 Batch Evaluation

User selects:
- An autorater
- A set of transcripts (by tag filter, manual selection, or "all labeled")
- Clicks "Run Evaluation"

Backend:
1. Creates an `eval_run` record
2. For each transcript, sends the autorater prompt (with transcript injected) to Gemini
3. Parses the response against the output schema
4. Compares predicted labels vs ground truth
5. Computes metrics: precision, recall, F1 per label, overall accuracy, confusion matrix
6. Saves all results

**Concurrency:** Run N transcripts in parallel (configurable, default 5) to speed up batch runs.

### 2.4 Results Dashboard

- **Run list:** All past evaluation runs with summary metrics, sortable by date/metric
- **Run detail:** Per-transcript results table with pass/fail indicators, expandable to see full autorater response
- **Diff view:** Compare two runs side-by-side (e.g., autorater prompt v1 vs v2)
- **Failure analysis:** Filter to only mismatches, group by error type
- **Regression detection:** When running a new eval, auto-compare to the most recent previous run. Highlight regressions 🔴 and improvements 🟢.

---

## Module 3: Transcript Generator

### 3.1 Generation Configuration

User provides:
- **Reference transcripts** — 3–10 real transcripts to use as style/format reference
- **Generation prompt** — what kind of transcripts to generate, e.g.:
  - "Generate 5 transcripts where the agent gives wrong math calculations"
  - "Generate 3 transcripts where the agent references religious content"
  - "Generate 5 transcripts with incorrect category classification"
- **Count** — how many to generate
- **Model** — which Gemini model

### 3.2 Generation Flow

Backend constructs a meta-prompt:
```
You are generating synthetic conversation transcripts for testing.

Here are reference transcripts showing the format and style:
{{reference_transcripts}}

Generate {{count}} transcripts with the following characteristics:
{{user_prompt}}

Output each transcript in this format:
[TRANSCRIPT_START]
[USER] ...
[AGENT] ...
[TOOL_CALL] ...
[TOOL_RESPONSE] ...
[AGENT] ...
[TRANSCRIPT_END]
```

Results are parsed, stored as transcripts with `source='generated'`, and auto-tagged based on the generation prompt.

### 3.3 Review & Edit

After generation, user reviews each transcript in the UI. Can:
- Edit content
- Add/modify labels
- Accept or reject into the labeled set
- Re-generate individual transcripts

---

## Module 4: Transaction Classification Eval

### 4.1 Golden Set Management

Each golden set entry contains:
- **Input transactions** — the transaction list to classify (JSON array)
- **Reference transactions** — additional user transactions for dedup context (3 lists)
- **Expected output** — the correctly labeled, deduplicated output
- **Set name** — group entries into named sets (e.g., "dedup-edge-cases", "category-ambiguous")

UI: Table view with inline JSON preview, bulk import from JSON files, manual editor.

### 4.2 Classification Prompt Configuration

- **Prompt template** — uses placeholders:
  - `{{input_transactions}}` — the transactions to classify
  - `{{reference_list_1}}`, `{{reference_list_2}}`, `{{reference_list_3}}` — reference transaction lists
- **Model** — Gemini model selection

### 4.3 Evaluation Run

User selects a prompt config + golden set → "Run Evaluation":
1. For each golden set entry, render the prompt template with the transaction data
2. Send to Gemini
3. Parse the output (expected: JSON array of labeled transactions)
4. Compare to expected output

**Matching logic (start with exact, structured for easy extension):**
- **v1: Exact category match** — for each transaction, check if the predicted `category` label exactly matches the expected `category`. This is the only field measured initially.
- The matching function is isolated in `app/services/matchers.py` with a `MatchStrategy` interface so new strategies (fuzzy match, synonym maps, multi-field) can be added without refactoring the eval pipeline.

```python
# app/services/matchers.py
class MatchStrategy:
    def match(self, predicted: dict, expected: dict) -> dict:
        """Returns {"match": bool, "details": {...}}"""
        raise NotImplementedError

class ExactCategoryMatch(MatchStrategy):
    def match(self, predicted, expected):
        match = predicted.get("category") == expected.get("category")
        return {
            "match": match,
            "predicted_category": predicted.get("category"),
            "expected_category": expected.get("category")
        }
```

**Metrics:**
- Overall exact match rate (category)
- Per-category precision / recall / F1
- Deduplication accuracy (correct merges vs incorrect merges)
- Per-entry detailed comparison view

### 4.4 Results Dashboard

Same pattern as autorater dashboard:
- Run history with metrics
- Per-entry drill-down
- Side-by-side prompt comparison
- Regression detection

---

## API Design

### REST Endpoints

```
# Agents
GET    /api/agents
POST   /api/agents
PUT    /api/agents/{id}
DELETE /api/agents/{id}

# Fixtures
GET    /api/fixtures
POST   /api/fixtures
PUT    /api/fixtures/{id}
DELETE /api/fixtures/{id}

# Sessions
GET    /api/sessions
POST   /api/sessions
GET    /api/sessions/{id}

# Turns (read-only via REST, writes via WebSocket)
GET    /api/sessions/{id}/turns

# Prompt versions
GET    /api/agents/{id}/versions
POST   /api/agents/{id}/versions/{vid}/label

# Transcripts
GET    /api/transcripts
POST   /api/transcripts
PUT    /api/transcripts/{id}
DELETE /api/transcripts/{id}
POST   /api/transcripts/import     # bulk import

# Autoraters
GET    /api/autoraters
POST   /api/autoraters
PUT    /api/autoraters/{id}

# Eval runs
POST   /api/eval/run               # start a new eval run
GET    /api/eval/runs
GET    /api/eval/runs/{id}
GET    /api/eval/runs/{id}/results
GET    /api/eval/runs/{id}/diff/{other_id}  # compare two runs

# Transcript generation
POST   /api/generate/transcripts

# Golden sets
GET    /api/golden-sets
POST   /api/golden-sets
PUT    /api/golden-sets/{id}
POST   /api/golden-sets/import

# Classification prompts
GET    /api/classification/prompts
POST   /api/classification/prompts
PUT    /api/classification/prompts/{id}

# Classification runs
POST   /api/classification/run
GET    /api/classification/runs
GET    /api/classification/runs/{id}
GET    /api/classification/runs/{id}/results
```

### WebSocket: Agent Chat

```
WS /ws/chat/{session_id}

Client → Server messages:
{
  "type": "user_message",
  "content": "How much did I spend on food last month?"
}

{
  "type": "rerun_turn",
  "turn_id": "turn-123",
  "overrides": {
    "system_prompt": "...",        // optional
    "tool_responses": {"fetch_transactions": [...]},  // optional
    "modified_history": [...]      // optional
  }
}

{
  "type": "swap_fixture",
  "fixture_ids": ["fixture-abc", "fixture-def"]
}

{
  "type": "set_tool_override",
  "overrides": {
    "fetch_transactions": {"data": [...], "active": true},
    "get_user_profile": {"data": {...}, "active": false}
  }
}

{
  "type": "clear_tool_overrides"
}

Server → Client messages:
{
  "type": "agent_chunk",          // streaming response
  "content": "Based on your..."
}

{
  "type": "tool_call",
  "tool_name": "fetch_transactions",
  "arguments": {"category": "food", "date_from": "2026-01-01"}
}

{
  "type": "tool_response",
  "tool_name": "fetch_transactions",
  "result": [...]
}

{
  "type": "turn_complete",
  "turn": {/* full turn object with debug data */}
}

{
  "type": "error",
  "message": "..."
}
```

---

## Frontend Pages

### Page 1: Agent Playground
- **Layout:** Three-column — left (agent config + fixture selector), center (chat), right (debug inspector)
- **Chat area:** Standard chat UI with markdown rendering. Each agent message clickable to load debug data in right panel.
- **Debug inspector:** Tabbed view — Prompt | Tool Calls | Raw Request | Raw Response | Tokens
- **Prompt editor:** Full-height code editor (Monaco or CodeMirror) with syntax highlighting
- **Fixture panel:** Dropdown selectors + inline JSON preview + "swap" button

### Page 2: Autorater Workbench
- **Sub-tabs:** Transcripts | Autoraters | Eval Runs
- **Transcripts tab:** Filterable table, click to expand/edit, bulk import button
- **Autoraters tab:** List + editor (split pane: config left, preview right)
- **Eval Runs tab:** Run history table → drill down to per-transcript results

### Page 3: Transcript Generator
- **Layout:** Left (reference transcript selector + generation prompt), Right (generated results with accept/reject/edit)

### Page 4: Classification Eval
- **Sub-tabs:** Golden Sets | Prompts | Eval Runs
- **Same pattern as autorater workbench** adapted for transaction data

### Global
- **Top nav:** Playground | Autorater | Generator | Classification
- **Settings page:** Gemini API key config, default model, concurrency settings

---

## Claude Code Build Plan

This section defines how to break the build into parallel workstreams for Claude Code agents. Each agent gets a clear scope, interface contracts, and can work independently.

### Agent Breakdown

| Agent | Scope | Est. Effort |
|-------|-------|-------------|
| **Agent-Backend-Core** | FastAPI app skeleton, DB schema, Gemini client, CRUD APIs | High |
| **Agent-Backend-Chat** | WebSocket chat handler, agent runtime loop, mock tools, code sandbox | High |
| **Agent-Backend-Eval** | Batch runner, metrics computation, autorater + classification eval | Medium |
| **Agent-Frontend-Shell** | React app, routing, layout, shared components, settings | Medium |
| **Agent-Frontend-Playground** | Chat UI, debug inspector, fixture panel, rerun flow | High |
| **Agent-Frontend-Eval** | Autorater workbench, transcript manager, classification eval, results dashboards | High |
| **Agent-Integration** | Wire frontend to backend, E2E testing, fix integration issues | Medium |

### Dependency Order

```
Phase 1 (parallel):
  Agent-Backend-Core  ──┐
  Agent-Frontend-Shell ──┤
                         │
Phase 2 (parallel, after Phase 1):
  Agent-Backend-Chat ────┤  (needs Core)
  Agent-Backend-Eval ────┤  (needs Core)
  Agent-Frontend-Playground ─┤  (needs Shell)
  Agent-Frontend-Eval ───┤  (needs Shell)
                         │
Phase 3:
  Agent-Integration ─────┘  (needs all above)
```

**NOTE:** If running with a single Claude Code instance sequentially, recommended order:
1. Backend-Core (DB + API skeleton)
2. Backend-Chat (agent runtime)
3. Frontend-Shell (app scaffold)
4. Frontend-Playground (chat UI)
5. Backend-Eval (batch runner)
6. Frontend-Eval (dashboards)
7. Integration pass

### Agent-Backend-Core — Detailed Instructions

**Goal:** Create the FastAPI application with database, models, and CRUD endpoints.

**Directory structure:**
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, CORS, lifespan
│   ├── config.py            # Settings (API keys, DB path, etc)
│   ├── database.py          # SQLite setup with aiosqlite
│   ├── models/
│   │   ├── __init__.py
│   │   ├── agent.py         # Agent, PromptVersion
│   │   ├── fixture.py       # Fixture
│   │   ├── session.py       # Session, Turn
│   │   ├── transcript.py    # Transcript
│   │   ├── autorater.py     # Autorater, EvalRun, EvalResult
│   │   ├── classification.py # GoldenTransaction, ClassificationPrompt, etc
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── agents.py
│   │   ├── fixtures.py
│   │   ├── sessions.py
│   │   ├── transcripts.py
│   │   ├── autoraters.py
│   │   ├── classification.py
│   │   ├── generation.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini_client.py  # Wrapper around google-genai SDK
│   │   ├── db_service.py     # DB operations
│   ├── schemas/              # Pydantic models for API
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── fixture.py
│   │   ├── ...
├── requirements.txt
├── seed_data/               # Example fixtures, transcripts for dev
│   ├── sample_agent.json
│   ├── sample_fixtures.json
│   ├── sample_transcripts.json
```

**Key decisions:**
- Use `aiosqlite` for async SQLite access
- All IDs are UUIDs generated server-side
- JSON fields stored as TEXT, serialized/deserialized in Python
- Gemini client: use `google-genai` SDK with manual function calling (disable auto-calling) so we control the loop
- API key passed via environment variable `GEMINI_API_KEY`
- CORS: allow `http://localhost:5173` (Vite dev server)

**requirements.txt:**
```
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
aiosqlite>=0.20.0
google-genai>=1.0.0
pydantic>=2.0
python-multipart>=0.0.9
```

### Agent-Backend-Chat — Detailed Instructions

**Goal:** Implement the WebSocket chat handler and agent runtime loop.

**Key file: `app/services/agent_runtime.py`**

The agent runtime loop:
1. Receive user message via WebSocket
2. Build the full prompt: system prompt + conversation history + tool definitions
3. Send to Gemini with `automatic_function_calling=False`
4. If response contains `function_call` parts:
   a. Execute mock tool handler
   b. Send tool response back to Gemini
   c. Repeat until Gemini returns a text response
5. Stream text chunks back via WebSocket
6. Save the complete turn with all debug data

**Key file: `app/services/mock_tools.py`**

Mock tool implementations:
- `fetch_transactions(args, fixtures)` — filter in-memory transaction list
- `get_user_profile(args, fixtures)` — return user profile fixture
- `execute_code(args, context)` — run code in subprocess with 10s timeout, inject `transactions` variable

**Key file: `app/services/code_sandbox.py`**

Simple code execution:
```python
import subprocess, json, tempfile

def execute_agent_code(code: str, context: dict, timeout: int = 10) -> dict:
    """Run agent-generated Python code in a subprocess."""
    wrapper = f"""
import json
context = json.loads('''{json.dumps(context)}''')
transactions = context.get('transactions', [])
{code}
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(wrapper)
        f.flush()
        result = subprocess.run(
            ['python3', f.name],
            capture_output=True, text=True, timeout=timeout
        )
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
```

**Rerun logic:** When receiving a `rerun_turn` message:
1. Load the original turn and its context (conversation up to that point)
2. Apply overrides (modified prompt, tool responses, history)
3. Re-execute the agent loop
4. Mark original turn as `is_active=0`
5. Save new turn with `parent_turn_id` pointing to original

### Agent-Backend-Eval — Detailed Instructions

**Goal:** Batch evaluation engine for autoraters and classification prompts.

**Key file: `app/services/batch_runner.py`**

Generic batch runner:
```python
async def run_batch(items, prompt_template, model, concurrency=5):
    semaphore = asyncio.Semaphore(concurrency)
    async def process_one(item):
        async with semaphore:
            prompt = render_template(prompt_template, item)
            response = await gemini_client.generate(prompt, model)
            return parse_response(response)
    return await asyncio.gather(*[process_one(item) for item in items])
```

**Autorater eval flow:**
1. Load autorater config + selected transcripts
2. For each transcript, inject into autorater prompt template
3. Send to Gemini, parse response as JSON
4. Compare predicted labels vs ground truth labels
5. Compute metrics per label category

**Classification eval flow:**
1. Load classification prompt + golden set entries
2. For each entry, render prompt with transaction data
3. Send to Gemini, parse response as transaction JSON array
4. Compare predicted vs expected using configurable match logic
5. Compute per-category and overall metrics

**Key file: `app/services/metrics.py`**

```python
def compute_classification_metrics(predicted, expected, match_mode='exact'):
    """Compute precision, recall, F1 per category."""
    # exact: full JSON match
    # per_transaction: compare each tx independently
    # fuzzy: apply category synonym mappings
    ...
    return {
        "overall_accuracy": ...,
        "per_category": {"food": {"precision": ..., "recall": ..., "f1": ...}, ...},
        "confusion_matrix": ...,
        "exact_match_rate": ...
    }
```

### Agent-Frontend-Shell — Detailed Instructions

**Goal:** React app scaffold with routing, layout, and shared components.

**Directory structure:**
```
frontend/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── api/
│   │   ├── client.ts          # Axios/fetch wrapper
│   │   ├── websocket.ts       # WebSocket client
│   │   ├── types.ts           # TypeScript types matching backend schemas
│   ├── components/
│   │   ├── Layout.tsx          # Top nav + page container
│   │   ├── JsonEditor.tsx      # JSON editor component (Monaco)
│   │   ├── PromptEditor.tsx    # Text editor with syntax highlighting
│   │   ├── DataTable.tsx       # Reusable sortable/filterable table
│   │   ├── MetricsCard.tsx     # Display precision/recall/F1
│   │   ├── DiffViewer.tsx      # Side-by-side text diff
│   │   ├── StatusBadge.tsx     # 🔴🟡🟢✅ status indicators
│   │   ├── ConfusionMatrix.tsx # Heatmap confusion matrix
│   ├── pages/
│   │   ├── Playground.tsx
│   │   ├── Autorater.tsx
│   │   ├── Generator.tsx
│   │   ├── Classification.tsx
│   │   ├── Settings.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   ├── useAgent.ts
│   │   ├── useFixtures.ts
│   ├── store/              # Zustand or React context
│   │   ├── index.ts
├── package.json
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
```

**Key setup:**
- Vite + React + TypeScript
- Tailwind CSS + shadcn/ui components
- Monaco Editor for JSON/prompt editing (via `@monaco-editor/react`)
- React Router for page navigation
- Proxy API requests to `http://localhost:8000` in Vite dev config

### Agent-Frontend-Playground — Detailed Instructions

**Goal:** The agent chat interface with debug inspector and fixture management.

**Layout (three columns):**

```
┌──────────────┬────────────────────┬──────────────────┐
│ Agent Config │    Chat Area       │ Debug Inspector  │
│              │                    │                  │
│ [Prompt ▾]   │ ┌────────────────┐ │ [Prompt] [Tools] │
│ [Model  ▾]   │ │ User: How much │ │ [Request][Resp]  │
│ [Fixtures ▾] │ │ Agent: Based...│ │                  │
│              │ │ ...            │ │ Full prompt sent │
│ Fixture      │ │                │ │ to Gemini:       │
│ preview:     │ │                │ │ ┌──────────────┐ │
│ {...}        │ │                │ │ │ System: You  │ │
│              │ │                │ │ │ are a...     │ │
│ [Swap Data]  │ ├────────────────┤ │ └──────────────┘ │
│              │ │ [Type message] │ │                  │
│              │ │            [⏎] │ │ [Edit & Rerun]   │
└──────────────┴────────────────────┴──────────────────┘
```

**Chat behavior:**
- Messages stream in via WebSocket (word by word)
- Markdown rendered with a markdown renderer (react-markdown)
- Agent messages have a subtle "inspect" icon — click to load debug data in right panel
- Tool calls shown as collapsible cards in the chat flow
- Rerun button appears in debug inspector when viewing a turn

**Fixture panel:**
- Dropdown to select active fixtures (user profile, transactions)
- Inline JSON preview (collapsed by default)
- "Swap" button sends `swap_fixture` WebSocket message
- Visual indicator when fixtures differ from session start

### Agent-Frontend-Eval — Detailed Instructions

**Goal:** Autorater workbench, transcript management, classification eval, and results dashboards.

**Autorater page — three tabs:**

**Tab 1: Transcripts**
- Table: name, source (manual/generated/imported), labels summary, tags, date
- Click row → expand to see full transcript + edit labels
- Bulk actions: import, delete, tag, export
- Filter by tag, source, label values

**Tab 2: Autoraters**
- Split pane: list on left, editor on right
- Editor: name, prompt (with `{{transcript}}` placeholder), model, output schema
- "Test on single transcript" button for quick iteration

**Tab 3: Eval Runs**
- Run launcher: select autorater + transcript filter → "Run"
- Run history table: date, autorater, transcript count, overall accuracy, P/R/F1
- Click run → drill-down view:
  - Summary metrics cards
  - Per-transcript results table (pass/fail per label, expandable)
  - Confusion matrix visualization
  - "Compare with..." dropdown to diff against another run → DiffViewer
  - Regressions highlighted in red, improvements in green

**Classification page — same three-tab pattern:**
- Golden Sets (instead of Transcripts)
- Prompts (instead of Autoraters)
- Eval Runs (classification-specific metrics)

---

## Configuration & Environment

```bash
# .env file
GEMINI_API_KEY=your-api-key-here
DB_PATH=./workbench.db
DEFAULT_MODEL=gemini-2.5-pro
BATCH_CONCURRENCY=5
CODE_EXECUTION_TIMEOUT=10
```

---

## V2 Features (Post-MVP)

- **A/B Prompt Comparison** — send same input to two prompt versions, show side-by-side
- **Conversation Forking** — branch tree visualization, fork from any turn
- **Automated User Agent** — define a persona prompt, let Gemini impersonate a user chatting with the agent. Auto-generate multi-turn conversations.
- **Regression CI** — on prompt save, auto-run full eval suite, block if regressions detected
- **Cost tracking** — per-session and per-run token cost estimates
- **Export to prod format** — one-click export prompt + tool defs in the format the real Sherlock stack expects
- **Shareable links** — share a session or eval run with a colleague (when deployed)
- **Prompt templates library** — save and reuse common prompt patterns

---

## Open Questions

1. ~~Widget rendering fidelity~~ → v1: markdown + inline JSON/HTML. Simple renderers.
2. ~~Transcript format~~ → Support both text (`[AGENT]`/`[USER]`) and JSON formats.
3. ~~Classification match semantics~~ → Category-only exact match for v1. `MatchStrategy` interface for extension.
4. ~~Gemini model~~ → `gemini-2.5-pro` via `google-genai` SDK.
5. **Reference transaction lists** — always 3 lists. Structure TBD. Stored as flexible JSON field for now.
6. **Exact tool definitions** — placeholder definitions in spec. Real schemas to be provided later.
7. **Autorater dimensions** — how many autoraters are there? What are the exact evaluation dimensions beyond safety and tool_usage?
