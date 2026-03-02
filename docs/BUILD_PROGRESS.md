# Build Progress

## Phase 1: Backend Core - COMPLETE
- database.py: All 13 tables, auto-creates on startup
- config.py: Settings from .env
- schemas/: Pydantic models for all 6 domains
- services/gemini_client.py: google-genai wrapper with manual function calling
- routers/: CRUD for agents, fixtures, sessions, transcripts, autoraters, classification, generation, settings
- main.py: FastAPI with CORS, lifespan, all routers

## Phase 2: Agent Runtime - COMPLETE
- mock_tools.py: fetch_transactions (filter + group_by), get_user_profile, execute_code
- code_sandbox.py: subprocess-based Python execution with timeout
- agent_runtime.py: core agent loop with Gemini function calling, tool overrides, rerun
- chat.py: WebSocket handler for all message types

## Phase 3: Batch Evaluation - COMPLETE
- batch_runner.py: async batch runner with semaphore-based concurrency
- metrics.py: precision/recall/F1, confusion matrix, classification metrics
- matchers.py: MatchStrategy interface with ExactCategoryMatch
- POST /api/eval/run, POST /api/classification/run, POST /api/generate/transcripts

## Phase 4: Frontend Shell - COMPLETE
- Tailwind CSS, Vite proxy, React Router with 7 routes
- Layout with top nav, shared components (DataTable, JsonEditor, PromptEditor, MetricsCard, StatusBadge, DiffViewer)
- API client, TypeScript types, WebSocket client, Zustand store
- Settings page functional

## Phase 5: Frontend Playground - COMPLETE
- Three-column layout: agent config, chat, debug inspector
- Full WebSocket chat with markdown, streaming, tool call cards
- Debug inspector with 5 tabs + rerun support
- Fixture swap, tool overrides, prompt version save

## Phase 6: Frontend Eval - COMPLETE
- Autorater page: Transcripts tab, Autoraters tab, Eval Runs tab
- Generator page: reference selector + prompt + results review
- Classification page: Golden Sets tab, Prompts tab, Eval Runs tab

## Phase 7: Integration & Polish - COMPLETE
- Seed data: sample agent, 2 fixtures, 3 transcripts (auto-loaded if DB empty)
- Vite proxy configured for /api and /ws
- Full end-to-end verified

## Phase 8: File-Based Agents + UI Polish - COMPLETE
- freemarker.py: FreeMarker template subset renderer (interpolation, list, if/elseif/else, built-ins)
- agent_loader.py: Loads agent.yaml + prompt.ftl from disk; resolves static/programmatic/template variables
- sherlock-finance agent: Full agent definition in backend/agents/sherlock-finance/
- agents router: New endpoints for folder listing, import, agent-versions CRUD, active version, template
- agent_versions table: Full snapshot versioning with source (file/ui), is_base flag
- Agents page (/agents): Agent management, file import, template inspector, version management
- UserProfiles page (/profiles): Fixture management with simulation date picker
- ChatPanel widget rendering: PieChart, LineChart, Table, PromptSuggestionChips
- Comprehensive test coverage: all backend services and API endpoints
- Architecture docs: BACKEND_COMPONENTS.md, FRONTEND_COMPONENTS.md, SYSTEM_OVERVIEW.md

## Phase 9: Playground Rerun & Debug Improvements - COMPLETE
- **Rerun message cleanup:** `handleRerun` now removes old tool_call/tool_response/agent messages before rerunning, so the chat shows only the fresh results
- **Auto-select new turn:** `turn_complete` handler auto-selects the new turn in the DebugPanel, so the debug inspector immediately shows fresh raw request/response data
- **Lock responses toggle:** New "Lock responses" checkbox in DebugPanel edit mode. When enabled, the original (or edited) tool responses are injected directly into conversation history and Gemini is called without tool declarations — it can only produce text, no new tool calls. This allows testing how Gemini interprets specific tool data without re-executing tools.
- **Simulation date in Playground:** Date picker in the AgentConfigPanel Fixtures section that reads/writes `currentDate` from the user_profile fixture. Syncs to the agent runtime's system prompt injection.

## Current Status
All 9 phases complete. The system is fully functional.

## Test Coverage
- Backend: Full coverage of all routers and services via pytest
- Frontend: Components (DataTable, DiffViewer, MetricsCard, StatusBadge, TranscriptPicker) and API layer tested

## Known Gaps / Future Work
See docs/EVAL_FUTURE_WORK.md for planned evaluation improvements.

Frontend page-level tests (Agents, UserProfiles, Playground pages) are not yet written — these
require more complex mocking of the API layer and WebSocket.
