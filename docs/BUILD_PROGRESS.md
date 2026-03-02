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

## Phase 10: UI Overhaul - COMPLETE
Premium developer-tool aesthetic (Linear/Vercel light mode style):

**Design System Foundation:**
- Inter Variable + JetBrains Mono Variable fonts
- Indigo/violet primary accent (#6366f1), slate neutrals
- CSS custom properties for fonts and shadows
- Custom Monaco light theme (`workbench-light`)

**Navigation Architecture:**
- IconRail: 56px vertical icon sidebar with Lucide icons (replaced horizontal nav)
- TopBar: 48px route-based breadcrumb bar with action slot
- SubNav: 180px vertical sub-nav for tabbed pages (Agents, Autorater, Classification)
- Layout rewritten to `[IconRail] | [TopBar + Content]` pattern

**Shared Component Upgrades:**
- DataTable: slate-50 headers, indigo-50 hover/selected, shadow-xs container
- StatusBadge: rounded-full pill, emerald/rose/amber/indigo palette
- MetricsCard: white card with shadow-xs, slate-500 labels
- PromptEditor/JsonEditor: light Monaco theme, rounded container, optional label
- DiffViewer: rose/emerald diff colors, rounded container
- TranscriptPicker: Lucide chevron icons, indigo tag chips
- New Skeleton component for loading states

**Page Updates (all pages):**
- Color palette migration: gray→slate, blue→indigo, green→emerald, red→rose
- Agents/Autorater/Classification: horizontal tabs replaced with SubNav
- Settings: card wrapper with refined form styling
- ChatPanel: indigo-600 user bubbles, slate-100 agent bubbles, rounded-2xl
- All playground sub-components updated to new palette

**Build Fix:**
- Excluded test files from tsconfig.app.json to fix pre-existing production build error

## Phase 11: Navigation Refinements - COMPLETE

**IconRail — collapsible/expandable:**
- Collapsed (default, w-14): icons only with hover tooltips
- Expanded (w-[200px]): icons + text labels, "PW Workbench" brand
- Toggle button (ChevronsRight/ChevronsLeft) at bottom
- State persisted to localStorage, smooth width transition

**TabBar component (new):**
- Horizontal tab bar with bottom-border active indicator
- Same prop interface as SubNav (items, active, onChange)
- Used by Agents and Autorater pages

**Agents page restructured:**
- Permanent left sidebar (w-80) with agent list + import controls
- Horizontal TabBar for Overview/Template/Versions tabs in right content area
- Overview tab is now agent detail only (no agent list)

**Autorater page restructured:**
- Replaced vertical SubNav with horizontal TabBar at top
- Full-width content below tabs

**Unchanged pages:** Classification (still uses SubNav), UserProfiles, Playground

## Phase 12: Global Toast System & UX Polish - COMPLETE

**Toast infrastructure:**
- `ToastProvider.tsx`: React context provider holding a `Toast[]` array. Global `useToast()` hook exposes `addToast(message, type, duration?)`. Renders a stacked container (fixed bottom-right, z-50, max 4 toasts, oldest evicted on overflow). Auto-dismisses after 3s (success/info) or 5s (error/warning).
- `Toast.tsx` upgraded: added `info` (sky-600) and `warning` (amber-600) types; icon prefix per type (✓ ✗ ℹ ⚠); no longer positioned itself (positioning delegated to `ToastProvider`).
- `App.tsx`: wrapped with `<ToastProvider>`.

**StatusBadge spinner:**
- Animated SVG spinner renders inline before the label text when `status === 'running'`. Visible feedback during active eval polling.

**Playground toasts:**
- `handleAgentUpdate`: success/error toast on agent save.
- `handleSaveVersion`: success/error toast on version save.
- `handleSwapFixture`: info toast "Fixtures updated".
- WS disconnect/reconnect: warning toast on disconnect, info toast on reconnect.

**Autorater dirty state + toasts:**
- `AutoratersTab`: `isDirty` computed via `useMemo`. Save button disabled when `!isDirty || saving`. Amber "• Unsaved changes" indicator. Replaced inline `saveError` with `addToast`.
- `EvalRunsTab`: success toast with pass rate on completion; error toast on run failure.

**Classification dirty state + polling + toasts:**
- `PromptsTab`: same `isDirty` pattern as AutoratersTab, amber indicator, success/error toasts.
- `ClassificationRunsTab`: added full polling (`pollingRef` + `pollRun`) matching Autorater's pattern — was entirely missing before. Success/error toasts on completion/failure.

**Generator + Agents:**
- Generator: success toast after each transcript save.
- Agents: replaced inline `importMsg` state/display with `addToast` calls.

## Phase 13: AI-Powered Fixture Generation - COMPLETE

**Backend:**
- `fixture_generator.py`: New service with `validate_profile()`, `validate_transactions()`, `generate_profile()`, `generate_transactions()` — uses Gemini with structured JSON output and validation
- `POST /api/fixtures/generate-profile`: Generates random Indian user profile via Gemini (temperature 1.2 for variety)
- `POST /api/fixtures/generate-transactions`: Generates transactions from user prompt + date range + optional profile context
- New schemas: `GenerateTransactionsRequest`, `GenerateProfileResponse`, `GenerateTransactionsResponse`
- Comprehensive validation: profile schema checks (required fields, nested objects, types), transaction schema checks (date format, P2M/P2P types, DEBIT/CREDIT directions, merchantCategory requirement)

**Frontend:**
- "New Profile" auto-generates a random user profile on click (calls Gemini, populates form)
- Loading spinner + "Generating random user profile with Gemini..." indicator during profile generation
- "Generate Transactions" panel alongside transaction editor when creating new profiles
- Pre-filled prompt with sensible defaults (3-month date range, 20+ tx/week, varied categories, salary/rent/P2P, INR)
- Generate button with spinner + "This may take 15-30 seconds..." message
- Error handling with user-visible error messages on generation failure
- Disabled buttons during generation to prevent double-clicks

**Tests:**
- Backend: 22 tests (5 profile validation, 8 transaction validation, 2 generate_profile mocked, 3 generate_transactions mocked, 4 endpoint tests)
- Frontend: 6 tests for UserProfiles page (render, generation indicator, form population, error handling, transaction panel, button state)

## Phase 14: Developer Log Console - COMPLETE

Terminal-style real-time log viewer (`/devlogs`) with backend SSE stream and frontend event capture.

**Backend:**
- `log_service.py`: Singleton with ring buffer (max 1000), subscriber queues for SSE, `dev_log()` convenience function
- `routers/devlogs.py`: `GET /api/devlogs/stream` SSE endpoint — replays buffer history then streams live entries
- `main.py`: HTTP logging middleware (REQ/RES for all endpoints, skips devlogs stream to avoid recursion), devlogs router
- Instrumentation added: gemini_client.py (GEMINI calls), agent_runtime.py (turn start, tool calls/responses, errors), chat.py (WS connect/disconnect/messages)

**Frontend:**
- `lib/devlog.ts`: Module-level buffer (max 500), listener pattern, `devLog()` / `onDevLog()` / `getDevLogHistory()`
- `store/devLogStore.ts`: Zustand store with entries, filters (source/level/category/search), isPaused, isConnected; `selectFilteredEntries()` selector
- `hooks/useBackendLogs.ts`: EventSource hook consuming SSE stream, feeds into devLogStore with `source: 'backend'`
- `components/Layout.tsx`: DevLogBridge component mounts useBackendLogs + subscribes frontend devlog events to store
- `api/client.ts`: devLog calls for API_OUT/API_IN/API_ERR on every request
- `api/websocket.ts`: devLog calls for WS_OUT/WS_IN/WS_ERR on connect/send/receive/close
- `pages/DevLogs.tsx`: Terminal-style UI (dark bg-slate-900), filter bar, auto-scroll, status bar with SSE connection status
- `components/LogEntry.tsx`: Memoized log line with timestamp, colored category badge, expandable JSON details
- Navigation: Terminal icon in IconRail bottomItems, 'Developer Console' in TopBar, `/devlogs` route in App.tsx

**Category colors:** indigo (API_OUT/REQ), emerald (API_IN/RES), rose (API_ERR/ERR/WS_ERR), violet (WS_OUT/GEMINI/WS), teal (WS_IN), cyan (TOOL), amber (DB/STATE)

**Tests:**
- Backend: 16 new tests (9 log_service unit tests, 7 devlogs_api tests)
- Frontend: 39 new tests (9 devlog.ts, 13 devLogStore, 6 LogEntry, 11 DevLogs page)

## Current Status
All 14 phases complete. The system includes a real-time Developer Log Console for debugging prompt iterations.

## Test Coverage
- Backend: ~450 tests via pytest (all routers and services; eval run tests require Gemini API key)
- Frontend: 210 tests via vitest (components, pages, lib modules, stores)

## Known Gaps / Future Work
See docs/EVAL_FUTURE_WORK.md for planned evaluation improvements.

Frontend page-level tests (Agents, Playground pages) are not yet written — these
require more complex mocking of the API layer and WebSocket. UserProfiles and DevLogs pages have tests.
