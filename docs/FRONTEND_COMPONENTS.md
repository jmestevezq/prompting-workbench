# Frontend Components

## Technology Stack

| Package | Version | Role |
|---|---|---|
| React | 19.2 | UI framework |
| TypeScript | 5.9 | Type safety |
| Vite | 7.3 | Dev server + bundler |
| Tailwind CSS | 4.2 | Utility-first styling |
| React Router DOM | 7.13 | Client-side routing |
| Zustand | 5.0 | Global state management |
| @monaco-editor/react | 4.7 | Code/JSON/prompt editors |
| react-markdown | 10.1 | Markdown rendering in chat |
| Vitest | 4.0 | Unit testing |
| @testing-library/react | 16.3 | Component testing utilities |

---

## Entry Points

### `src/main.tsx`

Mounts the React application into the DOM. Wraps `<App>` with no additional providers — Zustand stores are accessed directly.

### `src/App.tsx`

Defines the router tree with React Router v7. All pages are children of the `<Layout>` route, which provides the persistent navigation shell:

```
/ → redirect to /playground
/playground     → Playground
/agents         → Agents (agent management + file import)
/profiles       → UserProfiles (fixture management)
/autorater      → Autorater
/generator      → Generator
/classification → Classification
/settings       → Settings
```

---

## API Layer

### `src/api/types.ts` — TypeScript Types

All types mirror the backend Pydantic schemas. Organized into groups:

- **Agent types:** `Agent`, `AgentCreate`, `AgentUpdate`, `ToolDefinition`, `PromptVersion`
- **Fixture types:** `Fixture`, `FixtureCreate`
- **Session types:** `Session`, `SessionCreate`, `Turn`, `ToolCall`, `ToolResponse`, `TokenUsage`
- **Transcript types:** `Transcript`, `TranscriptCreate`
- **Autorater types:** `Autorater`, `AutoraterCreate`, `EvalRun`, `EvalMetrics`, `EvalResult`
- **Classification types:** `GoldenTransaction`, `ClassificationPrompt`, `ClassificationRun`, `ClassificationMetrics`, `ClassificationResult`
- **Settings types:** `SettingsData`, `SettingsUpdate`
- **WebSocket types:** `WsClientMessage` (union of 5 message types), `WsServerMessage` (union of 8 event types)

### `src/api/client.ts` — REST Client

A thin wrapper around the browser's native `fetch`. All requests include `Content-Type: application/json`. Non-OK responses throw an `Error` with the status code and body. 204 responses return `undefined`.

The exported `api` object provides named methods grouped by domain:

```typescript
// Agents
api.listAgents()
api.createAgent(data)
api.getAgent(id)
api.updateAgent(id, data)
api.deleteAgent(id)
// File-based import
api.listAgentFolders()
api.importAgent(folderName)
// Prompt versions (legacy)
api.listVersions(agentId)
api.createVersion(agentId, label?)
// Agent versions (new)
api.listAgentVersions(agentId)
api.createAgentVersion(agentId, data)
api.setActiveVersion(agentId, versionId)
api.getAgentTemplate(agentId)
// Fixtures
api.listFixtures()
api.createFixture(data)
api.updateFixture(id, data)
api.deleteFixture(id)
// Eval / classification / generation
api.startEvalRun(autorater_id, transcript_ids, eval_tags?)
api.generateTranscripts(data)
// ...etc
```

All methods are typed with the corresponding request/response TypeScript types.

### `src/api/websocket.ts` — WebSocket Client

`ChatWebSocket` class wrapping a native `WebSocket`:

- `connect()` — opens the connection, resolves when open. URL is derived from `window.location` (ws:// or wss:// depending on protocol).
- `send(message)` — serializes `WsClientMessage` to JSON and sends if connection is open
- `onMessage(handler)` — registers a handler function, returns an unsubscribe function
- `disconnect()` — closes the connection, disables auto-reconnect

**Auto-reconnect:** On close, waits `reconnectDelay × attempt` milliseconds and reconnects, up to `maxReconnectAttempts = 5` times. Reconnect is disabled on intentional `disconnect()` call.

---

## Global State

### `src/store/index.ts` — Zustand Store

Minimal global state for cross-page communication:

```typescript
interface AppState {
  activeAgent: Agent | null     // currently selected agent
  activeSession: Session | null // active chat session
  agents: Agent[]               // loaded agent list
  fixtures: Fixture[]           // loaded fixture list
}
```

Used by `Playground` (reads/writes all fields) and potentially other pages. Actions are simple setters.

---

## Layout

### `src/components/Layout.tsx`

Outer shell rendered for all pages. Contains:
- A top navigation bar with links to all five pages
- The active nav item is highlighted (blue background)
- An `<Outlet>` that renders the active page
- Full-height layout (`h-screen`, `flex flex-col`)

---

## Shared Components

### `src/components/DataTable.tsx`

A generic table component with:
- Column definitions with optional sort and render functions
- Row click handler
- Header-based sorting (toggling asc/desc)
- No external dependencies (pure Tailwind)

### `src/components/JsonEditor.tsx`

A Monaco Editor instance configured for JSON mode. Props:
- `value` — current JSON string
- `onChange` — called on every keystroke
- `readOnly` — optional, disables editing
- `height` — default `200px`

Uses `@monaco-editor/react` which lazy-loads Monaco from CDN.

### `src/components/PromptEditor.tsx`

Similar to `JsonEditor` but configured for plain text / markdown editing. Used for system prompts and autorater prompt templates.

### `src/components/MetricsCard.tsx`

Displays evaluation metrics in a card layout:
- Overall accuracy or match rate (large number)
- Per-label or per-category precision/recall/F1 in a table
- Color-coded (green ≥0.8, yellow ≥0.6, red <0.6)

### `src/components/StatusBadge.tsx`

A small inline badge component for status values. Maps status strings to colors:
- `completed` / `pass` → green
- `failed` / `fail` → red
- `running` → yellow/blue animated
- `pending` → gray

### `src/components/DiffViewer.tsx`

Side-by-side comparison of two text values. Highlights differences. Used for comparing eval run results.

### `src/components/TranscriptPicker.tsx`

A multi-select list of transcripts with:
- Search/filter input
- Checkbox per transcript
- Shows transcript name, source badge, and label summary
- Returns selected IDs to parent

---

## Pages

### `src/pages/Playground.tsx` — Agent Playground

The most complex page. Orchestrates:
- Loading agents and fixtures on mount
- Agent selection → creating a session → connecting WebSocket
- Message routing from WebSocket to UI state
- Streaming message assembly (chunks accumulate into the last streaming message)
- Fixture selection and live fixture swapping
- Tool override management
- Agent update (system prompt, model) and version saving

**State:**
- `agents` — all available agents
- `session` — current session object
- `selectedFixtureIds` — fixture IDs active in this session
- `messages` — `ChatMessage[]` array (role, content, streaming flag, turn debug data)
- `selectedTurn` — turn loaded in the debug inspector
- `toolOverrides` — current session overrides
- `wsRef` — ref holding the `ChatWebSocket` instance
- `isStreaming` — true while an agent turn is in progress

**WebSocket message routing (`handleWsMessage`):**
- `agent_chunk` → appends to last streaming message, or creates new one
- `tool_call` → adds a `tool_call` message
- `tool_response` → adds a `tool_response` message
- `turn_complete` → marks the streaming message as complete, attaches turn debug data
- `error` → adds a system error message

**Layout:** Three-column grid (280px | 1fr | 340px)

### `src/pages/Autorater.tsx` — Autorater Workbench

Three-tab page:

**Tab 1: Transcripts**
- Loads all transcripts from `api.listTranscripts()`
- Filterable by source (dropdown) and tag (text input)
- Click a row to expand it: shows full content, editable labels and tags
- Bulk import via JSON paste

**Tab 2: Autoraters**
- Lists autoraters; click to select
- Editor pane: name, prompt (with `{{transcript}}` placeholder), model, output schema
- Save updates via `api.updateAutorater()`

**Tab 3: Eval Runs**
- Run launcher: select autorater + transcripts (via `TranscriptPicker`) + optional eval tags
- Run history table: date, status, transcript count, pass rate, per-tag F1
- Click a run to see per-transcript results table with predicted vs ground-truth labels

### `src/pages/Generator.tsx` — Transcript Generator

- Left pane: select reference transcripts (`TranscriptPicker`), text area for generation prompt, count selector, model dropdown
- Right pane: generated results with transcript content, tags
- "Generate" button calls `api.generateTranscripts()`, displays results
- Results can be saved by accepting them (already auto-saved by backend) or edited

### `src/pages/Classification.tsx` — Classification Evaluation

Three-tab page (same structure as Autorater):

**Tab 1: Golden Sets**
- Table of golden set entries grouped by `set_name`
- Expand to see JSON of input_transactions, reference_transactions, expected_output

**Tab 2: Prompts**
- List + editor for classification prompt templates
- Placeholder reference shown in UI

**Tab 3: Eval Runs**
- Run launcher: select prompt + golden set name
- Run history with `exact_match_rate`, per-category precision/recall/F1
- Per-entry results with match details (per-transaction category comparison)

### `src/pages/Agents.tsx` — Agent Management

Three-tab page for managing file-based and manually created agents:

**Tab 1: Overview**
- Lists all agents with name, model, folder, and source badge (file/ui)
- Detail pane: shows agent metadata, "Re-import from Files" button (for file-based agents), Delete button
- Import section: dropdown of available agent folders → "Import" triggers `POST /api/agents/import/{folder}`

**Tab 2: Template & Variables**
- Loads the active version's raw `.ftl` template and variable definitions via `GET /api/agents/{id}/template`
- Displays raw template in read-only Monaco editor
- Variable table: name, type (static/programmatic/template), resolved value preview
- Rendered system prompt in read-only Monaco editor
- Tool and widget detail cards

**Tab 3: Versions**
- Lists all `agent_versions` records with label, source, created date, active status
- Set any version as active via `PUT /api/agents/{id}/active-version`
- Re-import from files (updates base version)
- Create new UI version: label + system prompt form → `POST /api/agents/{id}/agent-versions`
- Version detail pane: system prompt, tool details, widget details

### `src/pages/UserProfiles.tsx` — User Profiles

Two-panel page for managing user profile and transaction fixtures:

- Left panel: list of all `user_profile` type fixtures
- Right panel: edit/create form with:
  - Name field
  - **Simulation date** picker (`currentDate` field injected into profile JSON)
  - Profile data JSON editor (Monaco)
  - Transactions JSON editor (linked `transactions` fixture)
- Create: saves both the user profile fixture and updates/creates a linked transactions fixture
- Delete: removes the profile fixture

### `src/pages/Settings.tsx` — Settings

- Shows current settings from `api.getSettings()`
- Form with API key input (write-only), model dropdown, concurrency input, timeout input
- `PUT /api/settings` on save

---

## Playground Sub-components

### `src/components/playground/AgentConfigPanel.tsx`

Left column of the Playground. Contains:
- Agent selector dropdown (shows all agents)
- System prompt editor (Monaco, editable)
- Model selector
- Tool definitions viewer (read-only JSON)
- Fixture selector (multi-select checkboxes)
- Fixture data editor (expandable JSON editor per fixture)
- Fixture swap button
- Tool override panel (set/clear override per tool)
- "Save Version" button with label input

### `src/components/playground/ChatPanel.tsx`

Center column. Contains:
- Scrolling message list
  - User messages (right-aligned)
  - Agent messages (left-aligned, markdown-rendered + widget blocks)
  - Tool call cards (expandable, shows tool name + args)
  - Tool response cards (expandable, shows result)
  - System messages (error/info banners)
- "Generating..." indicator while agent is responding
- Message input bar (text input + send button, disabled while streaming)
- Click on agent message → calls `onSelectTurn` to load debug data

**UI Widget Rendering**

Agent message content is parsed for embedded widget JSON blocks. The `tryParseRenderableBlocks()` function handles:
- Pure JSON messages (entire content is a JSON object with a widget key)
- Mixed content: fenced ` ```json ``` ` blocks or bare JSON objects interspersed with markdown text

Supported widget block types and their JSON keys:

| Widget | JSON Key | Render Component |
|---|---|---|
| Prompt suggestion chips | `promptSuggestionsBlock.suggestions` | `PromptSuggestionChips` — clickable chip buttons that send the suggestion as a message |
| Pie chart | `pieChartBlock.slices` | `PieChartWidget` — SVG pie chart with legend |
| Line chart | `lineChartBlock.dataPoints` | `LineChartWidget` — SVG line chart with area fill and axis ticks |
| Table | `tableBlock.{title,headers,rows}` | `TableWidget` — HTML table with optional title |

Non-widget text portions surrounding widget JSON are rendered as markdown alongside the widgets.

### `src/components/playground/DebugPanel.tsx`

Right column. Displays data for the selected turn in tabs:

- **Prompt** — full system prompt sent to Gemini
- **Tool Calls** — list of tool invocations with arguments and responses
- **Raw Request** — JSON editor (read-only) of the serialized Gemini request
- **Raw Response** — JSON editor (read-only) of the full Gemini response
- **Tokens** — token usage (prompt, completion, total)

When a turn is selected, shows an "Edit & Rerun" section where the user can:
- Modify the system prompt override
- Modify individual tool response overrides
- Click "Rerun" → sends `rerun_turn` WebSocket message
