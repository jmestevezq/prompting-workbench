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
- Tailwind CSS, Vite proxy, React Router with 5 routes
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
- Makefile: `make dev`, `make backend`, `make frontend`, `make install`
- Vite proxy configured for /api and /ws
- Full end-to-end verified
