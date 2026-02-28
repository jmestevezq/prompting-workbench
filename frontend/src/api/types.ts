// --- Agents ---
export interface Agent {
  id: string
  name: string
  system_prompt: string
  model: string
  tool_definitions: ToolDefinition[]
  created_at: string
  updated_at: string
}

export interface AgentCreate {
  name: string
  system_prompt: string
  model?: string
  tool_definitions?: ToolDefinition[]
}

export interface AgentUpdate {
  name?: string
  system_prompt?: string
  model?: string
  tool_definitions?: ToolDefinition[]
}

export interface ToolDefinition {
  name: string
  description: string
  parameters?: Record<string, unknown>
}

export interface PromptVersion {
  id: string
  agent_id: string
  system_prompt: string
  tool_definitions?: ToolDefinition[]
  version_hash: string
  label?: string
  created_at: string
}

// --- Fixtures ---
export interface Fixture {
  id: string
  name: string
  type: string
  data: unknown
  created_at: string
}

export interface FixtureCreate {
  name: string
  type: string
  data: unknown
}

// --- Sessions ---
export interface Session {
  id: string
  agent_id: string
  fixture_ids?: string[]
  prompt_version_id?: string
  created_at: string
}

export interface SessionCreate {
  agent_id: string
  fixture_ids?: string[]
  prompt_version_id?: string
}

export interface Turn {
  id: string
  session_id: string
  turn_index: number
  role: string
  content: string
  raw_request?: unknown
  raw_response?: unknown
  tool_calls?: ToolCall[]
  tool_responses?: ToolResponse[]
  token_usage?: TokenUsage
  parent_turn_id?: string
  is_active: number
  created_at: string
}

export interface ToolCall {
  name: string
  args: Record<string, unknown>
}

export interface ToolResponse {
  name: string
  response: unknown
}

export interface TokenUsage {
  prompt_tokens: number
  completion_tokens: number
  total: number
}

// --- Transcripts ---
export interface Transcript {
  id: string
  name?: string
  content: string
  parsed_turns?: unknown
  labels: Record<string, string>
  source: string
  tags?: string[]
  created_at: string
}

export interface TranscriptCreate {
  name?: string
  content: string
  parsed_turns?: unknown
  labels: Record<string, string>
  source?: string
  tags?: string[]
}

// --- Autoraters ---
export interface Autorater {
  id: string
  name: string
  prompt: string
  model: string
  output_schema?: unknown
  created_at: string
}

export interface AutoraterCreate {
  name: string
  prompt: string
  model?: string
  output_schema?: unknown
}

export interface EvalRun {
  id: string
  autorater_id: string
  prompt_version_hash?: string
  transcript_ids: string[]
  status: string
  metrics?: EvalMetrics
  created_at: string
  completed_at?: string
}

export interface EvalMetrics {
  accuracy: number
  total: number
  correct: number
  per_label?: Record<string, LabelMetrics>
  confusion_matrix?: Record<string, Record<string, number>>
}

export interface LabelMetrics {
  precision: number
  recall: number
  f1: number
  tp: number
  fp: number
  fn: number
  tn: number
}

export interface EvalResult {
  id: string
  run_id: string
  transcript_id: string
  predicted_labels: Record<string, string>
  ground_truth_labels: Record<string, string>
  match?: boolean
  raw_response?: unknown
  token_usage?: TokenUsage
}

// --- Classification ---
export interface GoldenTransaction {
  id: string
  set_name: string
  input_transactions: unknown
  reference_transactions?: unknown
  expected_output: unknown
  tags?: string[]
  created_at: string
}

export interface GoldenTransactionCreate {
  set_name: string
  input_transactions: unknown
  reference_transactions?: unknown
  expected_output: unknown
  tags?: string[]
}

export interface ClassificationPrompt {
  id: string
  name: string
  prompt_template: string
  model: string
  created_at: string
}

export interface ClassificationPromptCreate {
  name: string
  prompt_template: string
  model?: string
}

export interface ClassificationRun {
  id: string
  prompt_id: string
  prompt_version_hash?: string
  golden_set_name?: string
  status: string
  metrics?: ClassificationMetrics
  created_at: string
  completed_at?: string
}

export interface ClassificationMetrics {
  exact_match_rate: number
  total: number
  exact_matches: number
  per_category?: Record<string, CategoryMetrics>
}

export interface CategoryMetrics {
  precision: number
  recall: number
  f1: number
  count: number
}

export interface ClassificationResult {
  id: string
  run_id: string
  golden_id: string
  predicted_output: unknown
  match_details?: unknown
  raw_response?: unknown
  token_usage?: TokenUsage
}

// --- Settings ---
export interface SettingsData {
  has_api_key: boolean
  default_model: string
  batch_concurrency: number
  code_execution_timeout: number
}

export interface SettingsUpdate {
  gemini_api_key?: string
  default_model?: string
  batch_concurrency?: number
  code_execution_timeout?: number
}

// --- WebSocket Messages ---
export interface WsUserMessage {
  type: 'user_message'
  content: string
}

export interface WsRerunTurn {
  type: 'rerun_turn'
  turn_id: string
  overrides?: {
    system_prompt?: string
    tool_responses?: Record<string, unknown>
    modified_history?: unknown[]
  }
}

export interface WsSwapFixture {
  type: 'swap_fixture'
  fixture_ids: string[]
}

export interface WsSetToolOverride {
  type: 'set_tool_override'
  overrides: Record<string, { data: unknown; active: boolean }>
}

export interface WsClearToolOverrides {
  type: 'clear_tool_overrides'
}

export type WsClientMessage =
  | WsUserMessage
  | WsRerunTurn
  | WsSwapFixture
  | WsSetToolOverride
  | WsClearToolOverrides

export interface WsAgentChunk {
  type: 'agent_chunk'
  content: string
}

export interface WsToolCall {
  type: 'tool_call'
  tool_name: string
  arguments: Record<string, unknown>
}

export interface WsToolResponse {
  type: 'tool_response'
  tool_name: string
  result: unknown
}

export interface WsTurnComplete {
  type: 'turn_complete'
  turn: Turn
}

export interface WsError {
  type: 'error'
  message: string
}

export type WsServerMessage =
  | WsAgentChunk
  | WsToolCall
  | WsToolResponse
  | WsTurnComplete
  | WsError
  | { type: 'fixture_swapped'; fixture_ids: string[] }
  | { type: 'tool_overrides_updated'; overrides: unknown }
  | { type: 'tool_overrides_cleared' }
