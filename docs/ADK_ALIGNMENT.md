# ADK Library Alignment

This document explains how the workbench backend aligns with the Google Agent Development Kit (ADK) internals — and why this matters for prompt engineering fidelity.

## Why This Matters

The workbench is a **simulation environment** for agents that run in production via the ADK. If the simulation doesn't match the ADK's internal behavior, a prompt that works in the workbench might fail in production — or vice versa. The goal is to make the workbench behaviorally identical to the ADK runtime so that prompt engineering results transfer directly.

---

## Key ADK Behaviors Replicated

### 1. Manual Function Calling Loop (`automatic_function_calling=False`)

**ADK behavior:** The ADK disables Gemini's automatic function calling and manages the call-response loop manually. This gives the ADK full control over when and how tools are executed, how errors are handled, and how many iterations to allow.

**Workbench implementation** (`gemini_client.py:111`):
```python
config = types.GenerateContentConfig(
    system_instruction=system_prompt,
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
)
```

If `automatic_function_calling` were left enabled, the SDK would silently execute tools on the Gemini server side (or attempt to call Python callables you register), bypassing the workbench's mock tool layer entirely. Disabling it is critical for the mock tool system to function.

---

### 2. Grouping Multiple Function Calls Into One Content Object

**ADK behavior:** When Gemini returns multiple function calls in a single response (e.g., two tools called in parallel), the ADK groups them into a single `Content(role="model", parts=[fc1, fc2, ...])` object when building the next request.

**Workbench implementation** (`agent_runtime.py:202–212`):
```python
# --- ADK-style: group all function calls into one Content(role="model") ---
fc_parts = []
for fc in result["function_calls"]:
    fc_parts.append(types.Part.from_function_call(
        name=fc["name"],
        args=fc["args"],
    ))
    all_tool_calls.append(fc)

contents.append(types.Content(role="model", parts=fc_parts))
```

And in `gemini_client.build_contents()` (`gemini_client.py:63–72`), when reconstructing history from stored turns:
```python
elif role == "tool_call":
    # Collect all consecutive tool_call turns into one Content(role="model")
    fc_parts = []
    while i < len(turns) and turns[i]["role"] == "tool_call":
        fc = turns[i].get("tool_call", {})
        fc_parts.append(types.Part.from_function_call(...))
        i += 1
    contents.append(types.Content(role="model", parts=fc_parts))
```

**Why this matters:** Gemini's API validates that function responses correspond to function calls in the immediately preceding model turn. If function calls are split across multiple `Content` objects, or function responses don't align with their corresponding calls in the same batch, Gemini returns an error. This grouping is mandatory, not optional.

---

### 3. Grouping All Function Responses Into One Content Object

**ADK behavior:** All function responses for a given batch of tool calls are grouped into a single `Content(role="user", parts=[fr1, fr2, ...])`.

**Workbench implementation** (`agent_runtime.py:226–238`):
```python
# --- ADK-style: group all function responses into one Content(role="user") ---
fr_parts = []
for fc, tool_result in zip(result["function_calls"], tool_results):
    all_tool_responses.append({"name": fc["name"], "response": tool_result})

    resp = tool_result if isinstance(tool_result, dict) else {"result": tool_result}
    fr_parts.append(types.Part.from_function_response(
        name=fc["name"],
        response=resp,
    ))

contents.append(types.Content(role="user", parts=fr_parts))
```

And in `build_contents()` (`gemini_client.py:74–85`):
```python
elif role == "tool_response":
    # Collect all consecutive tool_response turns into one Content(role="user")
    fr_parts = []
    while i < len(turns) and turns[i]["role"] == "tool_response":
        fr = turns[i].get("tool_response", {})
        fr_parts.append(types.Part.from_function_response(...))
        i += 1
    contents.append(types.Content(role="user", parts=fr_parts))
```

**Why this matters:** Sending tool responses one-by-one (each in their own `Content`) or mixing them with user text breaks Gemini's content structure validation. The ADK's batching ensures the model sees all results together, which also enables the model to reason about multiple tool outputs jointly.

---

### 4. Parallel Tool Execution

**ADK behavior:** The ADK executes all tool calls from a single model turn in parallel (using `asyncio.gather` in its async implementation).

**Workbench implementation** (`agent_runtime.py:215–224`):
```python
# --- ADK-style: execute all tools in parallel ---
loop = asyncio.get_event_loop()
tasks = [
    loop.run_in_executor(
        None,
        _execute_tool_call,
        fc["name"], fc["args"], state, tool_response_overrides,
    )
    for fc in result["function_calls"]
]
tool_results = await asyncio.gather(*tasks)
```

Note: `run_in_executor` is used here because the mock tool functions are synchronous (not async). This offloads them to the default thread pool while keeping the event loop unblocked — the same pattern the ADK uses for sync tool functions.

**Why this matters:** Parallel execution means the ordering of tool responses in the conversation must be deterministic (matched to the order of tool calls). The `zip(function_calls, tool_results)` pattern preserves this ordering.

---

### 5. Async Gemini API Calls

**ADK behavior:** The ADK uses the async Gemini client (`client.aio.*`) throughout to avoid blocking the event loop.

**Workbench implementation** (`gemini_client.py:124`):
```python
response = await client.aio.models.generate_content(
    model=model,
    contents=contents,
    config=config,
)
```

Using the sync `client.models.generate_content()` would block the event loop during the Gemini API call, preventing other requests from being handled concurrently. The ADK always uses the async variant.

---

### 6. System Instruction Placement

**ADK behavior:** The ADK passes the system prompt as `system_instruction` in `GenerateContentConfig`, not as a `Content` object in the conversation history.

**Workbench implementation** (`gemini_client.py:109`):
```python
config = types.GenerateContentConfig(
    system_instruction=system_prompt,
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
)
```

**Why this matters:** Including the system prompt as the first user or model turn (as some simple wrappers do) changes how Gemini processes it. The `system_instruction` field is handled distinctly by the model — it applies across all turns and does not count as a conversation participant. The workbench respects this distinction.

---

### 7. Conversation History Reconstruction

**ADK behavior:** The ADK maintains a list of `Content` objects representing the full conversation. When restarting or loading a session, it reconstructs this list from stored turn data.

**Workbench implementation** — `build_contents()` is the key function. It accepts the workbench's internal format (list of dicts with `role`, `content`, `tool_call`, `tool_response` fields) and produces the correct `Content` object sequence for Gemini. The reconstruction handles:

- `role="user"` → `Content(role="user", parts=[Part.from_text(...)])`
- `role="agent"` → `Content(role="model", parts=[Part.from_text(...)])`
- Consecutive `role="tool_call"` → single `Content(role="model", parts=[Part.from_function_call(...), ...])`
- Consecutive `role="tool_response"` → single `Content(role="user", parts=[Part.from_function_response(...), ...])`

This is used both for new turns (building from `conversation_history`) and for reruns (rebuilding from DB).

---

## Where the Workbench Diverges From ADK

### 1. Simulated Streaming vs. True Streaming

The ADK can use `generate_content_stream()` for genuine token-by-token streaming. The workbench currently calls `generate_content()` (non-streaming) and then simulates streaming by splitting the response into 3-word chunks. This means time-to-first-token in the workbench is the full Gemini latency, not progressive.

### 2. Tool Execution Layer

The ADK connects tools to real service implementations. The workbench uses mock tools backed by in-memory fixture data. This is intentional — the point is to test the prompt, not the tools.

### 3. Max Iterations

The ADK has its own iteration limits and safety mechanisms. The workbench uses `max_iterations=10` as a simple safeguard. Production ADK behavior may differ.

### 4. Error Handling

The ADK has structured error handling and retry logic for Gemini API failures. The workbench surfaces errors directly as WebSocket `error` events without retry.

### 5. Session State Persistence

The ADK runtime is typically stateless between requests (state lives in the client application). The workbench persists full conversation history to SQLite, including raw Gemini requests/responses, which the ADK does not do by default.

---

## Content Structure: Correct vs. Incorrect

To make the alignment concrete, here is an example of a conversation with two tool calls:

### Correct (ADK-style, what this workbench produces):

```
Content(role="user", parts=[Part.from_text("What did I spend on food?")])
Content(role="model", parts=[
    Part.from_function_call("getTransactionHistory", {"category": "food"}),
    Part.from_function_call("getUserProfile", {}),          # same turn, batched
])
Content(role="user", parts=[
    Part.from_function_response("getTransactionHistory", {"transactions": [...]}),
    Part.from_function_response("getUserProfile", {"name": "Jane", ...}),  # same turn, batched
])
Content(role="model", parts=[Part.from_text("You spent $234 on food.")])
```

### Incorrect (naive approach):

```
Content(role="user", parts=[Part.from_text("What did I spend on food?")])
Content(role="model", parts=[Part.from_function_call("getTransactionHistory", ...)])
Content(role="model", parts=[Part.from_function_call("getUserProfile", ...)])  # WRONG: separate turns
Content(role="user", parts=[Part.from_function_response("getTransactionHistory", ...)])
Content(role="user", parts=[Part.from_function_response("getUserProfile", ...)])  # WRONG: separate turns
Content(role="model", parts=[Part.from_text("You spent $234 on food.")])
```

The incorrect version causes Gemini API validation errors or unpredictable behavior. The workbench prevents this by collecting all function calls from one model response into a single `Content` and all function responses into a single `Content`.
