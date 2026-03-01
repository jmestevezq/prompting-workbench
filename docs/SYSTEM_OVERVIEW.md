# Prompt Engineering Workbench — System Overview

## Purpose

The Prompt Engineering Workbench is a local-first developer tool for rapidly iterating on LLM agent prompts, autoraters, and transaction classification prompts. It replicates the agent runtime in a controlled sandbox, enabling prompt inspection, turn-level rerun, batch evaluation, and synthetic transcript generation — without touching production infrastructure.

**The core problem it solves:** The iteration cycle for prompt engineering (edit → test → evaluate → refine) is slow when done against production systems. This workbench compresses that cycle to seconds.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Browser (React / TypeScript)                  │
│                                                                  │
│  ┌───────────────┐  ┌─────────────┐  ┌──────────────────────┐   │
│  │   Playground  │  │  Autorater  │  │  Classification Eval │   │
│  │  (chat UI +   │  │  Workbench  │  │  (golden sets,       │   │
│  │   debug panel)│  │  (eval runs)│  │   classification)    │   │
│  └──────┬────────┘  └──────┬──────┘  └──────────┬───────────┘   │
│         │ WebSocket        │ REST                │ REST           │
│         └──────────────────┼─────────────────────┘               │
│                            │                                      │
└────────────────────────────┼──────────────────────────────────────┘
                             │
┌────────────────────────────┼──────────────────────────────────────┐
│                  FastAPI Backend (Python / async)                 │
│                            │                                      │
│  ┌─────────────────────────▼──────────────────────────────────┐  │
│  │                    REST + WebSocket Routers                 │  │
│  │  /api/agents  /api/fixtures  /api/sessions  /api/transcripts│  │
│  │  /api/autoraters  /api/eval  /api/classification            │  │
│  │  /api/generate  /api/settings  /ws/chat/{session_id}        │  │
│  └──────┬──────────────────┬──────────────────┬───────────────┘  │
│         │                  │                  │                   │
│  ┌──────▼──────┐  ┌────────▼──────┐  ┌───────▼──────────────┐   │
│  │   Agent     │  │  Batch Runner  │  │  Gemini Client        │   │
│  │   Runtime   │  │  (semaphore   │  │  (google-genai SDK,   │   │
│  │   (ADK-     │  │   concurrency)│  │   manual fn calling)  │   │
│  │   aligned)  │  └───────────────┘  └───────────────────────┘   │
│  │             │                                                  │
│  │  ┌────────┐ │  ┌───────────────┐  ┌───────────────────────┐   │
│  │  │ Mock   │ │  │   Matchers    │  │   Metrics             │   │
│  │  │ Tools  │ │  │  (MatchStrat) │  │   (P/R/F1, confusion) │   │
│  │  └────────┘ │  └───────────────┘  └───────────────────────┘   │
│  └─────────────┘                                                  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                  SQLite (aiosqlite, WAL mode)               │  │
│  │  agents · prompt_versions · fixtures · sessions · turns    │  │
│  │  transcripts · autoraters · eval_runs · eval_results       │  │
│  │  golden_transactions · classification_prompts/runs/results │  │
│  └────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

---

## Modules

### Module 1 — Agent Playground

An interactive chat environment where a developer can:

- Select a pre-configured agent (system prompt + tool definitions + model)
- Attach data fixtures (user profile, transaction history)
- Chat with the agent live via WebSocket
- Inspect every Gemini API call (raw request, raw response, token usage)
- Override tool responses to test edge cases without modifying fixture data
- Rerun any agent turn with a modified prompt, tool response, or conversation history
- Save prompt snapshots as named versions

**Data flow:** Browser → WebSocket → `chat.py` router → `agent_runtime.py` (session loop) → `gemini_client.py` → Gemini API → `mock_tools.py` (tool execution) → streaming events back to browser.

### Module 2 — Autorater Evaluation

Batch evaluation of conversation transcripts against an LLM-as-judge (autorater):

- Manage a labeled transcript library with ground-truth labels and tags
- Define autoraters (evaluation prompt + model + expected output schema)
- Run batch evaluations with configurable concurrency
- Compute precision/recall/F1 per label, overall accuracy, and confusion matrix
- Diff two runs to detect regressions or improvements
- Import/export transcripts in bulk

**Data flow:** Browser → REST → `autoraters.py` router → `batch_runner.py` (parallel) → `gemini_client.py` → parse JSON response → `metrics.py` → save to DB.

### Module 3 — Transcript Generator

Synthetic data generation for building evaluation sets:

- Select reference transcripts as style examples
- Provide a natural language generation prompt ("generate 5 transcripts where the agent gives wrong math")
- Gemini generates N transcripts matching the specification
- Results are parsed, auto-tagged, and saved for review

**Data flow:** Browser → REST → `generation.py` router → `gemini_client.py` → parse transcript markers → save to DB.

### Module 4 — Classification Evaluation

Evaluation of transaction classification prompts against a golden dataset:

- Manage golden sets (input transactions + reference lists + expected categorized output)
- Define classification prompt templates with `{{input_transactions}}` placeholders
- Run batch evaluations comparing predicted vs expected category labels
- Per-category precision/recall/F1, exact match rate
- Extensible matching via `MatchStrategy` interface

**Data flow:** Browser → REST → `classification.py` router → `batch_runner.py` → `gemini_client.py` → `matchers.py` → `metrics.py` → save to DB.

---

## Data Model Summary

| Table | Purpose | Key Fields |
|---|---|---|
| `agents` | Agent configurations | name, system_prompt, model, tool_definitions |
| `prompt_versions` | Snapshot history of agent prompts | agent_id, version_hash, label |
| `fixtures` | Test data (user profiles, transactions) | type, data (JSON) |
| `sessions` | Chat sessions linking agent + fixtures | agent_id, fixture_ids |
| `turns` | Individual conversation turns | role, content, raw_request, raw_response, tool_calls, is_active |
| `transcripts` | Labeled conversation transcripts | content, labels, source, tags |
| `autoraters` | LLM-as-judge configurations | prompt, model, output_schema |
| `eval_runs` | Batch evaluation execution records | autorater_id, transcript_ids, status, metrics |
| `eval_results` | Per-transcript evaluation results | predicted_labels, ground_truth_labels, match |
| `golden_transactions` | Ground-truth classification examples | input_transactions, expected_output, set_name |
| `classification_prompts` | Classification prompt templates | prompt_template, model |
| `classification_runs` | Batch classification eval records | prompt_id, golden_set_name, status, metrics |
| `classification_results` | Per-entry classification results | predicted_output, match_details |

---

## Communication Protocols

### REST (HTTP/JSON)

All CRUD operations on agents, fixtures, sessions, transcripts, autoraters, golden sets, classification prompts, and settings. All endpoints are under `/api/`.

### WebSocket (`/ws/chat/{session_id}`)

Real-time bidirectional channel for the agent playground. Client sends:

| Message | Purpose |
|---|---|
| `user_message` | Send a chat message to the agent |
| `rerun_turn` | Rerun a past turn with overrides |
| `swap_fixture` | Replace active data fixtures |
| `set_tool_override` | Inject a specific tool response |
| `clear_tool_overrides` | Remove all tool overrides |

Server streams back:

| Event | Purpose |
|---|---|
| `agent_chunk` | Streaming text fragment |
| `tool_call` | Tool invocation visible in UI |
| `tool_response` | Tool result visible in UI |
| `turn_complete` | Full turn object with debug data |
| `error` | Error condition |

---

## Configuration

All runtime configuration comes from environment variables, loaded from `.env`:

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | _(required)_ | Gemini API authentication |
| `DB_PATH` | `./workbench.db` | SQLite database file location |
| `DEFAULT_MODEL` | `gemini-2.5-pro` | Default Gemini model |
| `BATCH_CONCURRENCY` | `5` | Parallel eval tasks |
| `CODE_EXECUTION_TIMEOUT` | `10` | Subprocess sandbox timeout (seconds) |

Settings can also be updated at runtime via `PUT /api/settings`.

---

## Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| Backend framework | FastAPI + uvicorn | Async-native, WebSocket support, fast startup |
| Async DB | aiosqlite | Zero-config file-based storage, async-compatible |
| LLM SDK | google-genai | Official Gemini SDK with function calling |
| Code sandbox | subprocess (tempfile) | Safe isolation without RestrictedPython complexity |
| Frontend framework | React + TypeScript + Vite | Type safety, fast dev loop |
| UI styling | Tailwind CSS | Utility-first, no component library lock-in |
| Code editors | Monaco Editor | VS Code-quality editing in the browser |
| State management | Zustand | Minimal, composable, no boilerplate |
| Routing | React Router | Standard SPA routing |
| Monorepo tooling | pnpm + Nx | Workspace management, task orchestration |
