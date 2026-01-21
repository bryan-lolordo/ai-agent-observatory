# Universal SDK Plan - Observatory Integration

## Overview

A simple, universal pattern for integrating Observatory into any AI application with minimal code changes. The framework has two modes:

- **Baseline Mode**: Track all metrics, detect optimization opportunities, show engineers what to fix
- **Optimized Mode**: Execute engineer-written optimization code

**Philosophy**: Observatory detects problems and shows how to fix them. Engineers implement the fixes in a structured shell. No magic auto-optimization.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR AI APPLICATION                       │
│                                                                 │
│   @observe(operation="score_resume")                            │
│   async def score_resume(prompt):                               │
│       return await client.chat.completions.create(...)          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BASELINE MODE                               │
│                                                                 │
│  @observe decorator:                                            │
│  ├── Auto-capture metrics (tokens, latency, cost, content)      │
│  ├── Run ALL detectors passively                                │
│  │   ├── Cache opportunity detector                             │
│  │   ├── Semantic cache opportunity detector                    │
│  │   ├── Batch opportunity detector                             │
│  │   ├── Parallel opportunity detector                          │
│  │   ├── Routing opportunity detector                           │
│  │   ├── Streaming candidate detector                           │
│  │   ├── Prefix cache opportunity detector                      │
│  │   ├── Context growth detector                                │
│  │   └── Token efficiency detector                              │
│  ├── Track conversation context (if provided)                   │
│  └── Record everything to database (~100 fields)                │
│                                                                 │
│  NO behavior changes - just observation and detection           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      OBSERVATORY DASHBOARD                       │
│                                                                 │
│  Shows detected opportunities with:                             │
│  ├── Impact estimate (cost savings, latency reduction)          │
│  ├── Code example for how to implement                          │
│  └── Which operations are affected                              │
│                                                                 │
│  Example:                                                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ OPPORTUNITY: Cache repeated calls                          │ │
│  │ Operation: get_job_details                                 │ │
│  │ Impact: 47 duplicate calls detected, ~$2.30 savings        │ │
│  │                                                            │ │
│  │ Add to your optimizations.py:                              │ │
│  │ ┌────────────────────────────────────────────────────────┐ │ │
│  │ │ OPTIMIZATIONS = {                                      │ │ │
│  │ │     "get_job_details": {                               │ │ │
│  │ │         "cache": {"enabled": True, "ttl": 3600},       │ │ │
│  │ │     }                                                  │ │ │
│  │ │ }                                                      │ │ │
│  │ └────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 ENGINEER IMPLEMENTS OPTIMIZATIONS                │
│                                                                 │
│  # optimizations.py (or in observatory_config.py)               │
│                                                                 │
│  OPTIMIZATIONS = {                                              │
│      "score_resume": {                                          │
│          "batch": {"enabled": True, "size": 5},                 │
│          "cache": {"enabled": True, "ttl": 3600},               │
│      },                                                         │
│      "get_job_details": {                                       │
│          "cache": {"enabled": True, "ttl": 7200},               │
│          "route_to": "gpt-4o-mini",                             │
│      },                                                         │
│      "deep_analyze": {                                          │
│          "prefix_cache": {"enabled": True},                     │
│          "streaming": {"enabled": True},                        │
│      },                                                         │
│  }                                                              │
│                                                                 │
│  # Optional: Custom implementations for complex optimizations   │
│  @optimization("score_resume", "batch")                         │
│  async def score_resume_batched(items):                         │
│      # Custom batching logic                                    │
│      ...                                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      OPTIMIZED MODE                              │
│                                                                 │
│  Same @observe decorator now:                                   │
│  ├── Checks OPTIMIZATIONS config for this operation             │
│  ├── Executes enabled optimizations:                            │
│  │   ├── cache.enabled? → Check cache first, return if hit      │
│  │   ├── batch.enabled? → Collect calls, execute in batches     │
│  │   ├── route_to? → Use specified model                        │
│  │   ├── streaming.enabled? → Use streaming response            │
│  │   └── etc.                                                   │
│  ├── Falls back to custom implementation if defined             │
│  ├── Still tracks everything (now with optimization metadata)   │
│  └── Records baseline vs optimized comparison data              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Capture Summary

### Auto-Captured by @observe (~100 fields)

| Category | Fields | How |
|----------|--------|-----|
| Core metrics | `prompt_tokens`, `completion_tokens`, `total_cost`, `latency_ms` | Extracted from LLM response |
| Content | `system_prompt`, `user_message`, `response_text`, `messages` | Extracted from function args |
| Token breakdown | `system_prompt_tokens`, `user_message_tokens`, `chat_history_tokens` | Calculated from content |
| Cache detection | `cache_opportunity`, `would_be_hit`, `potential_savings` | Cache detector |
| Routing detection | `routing_opportunity`, `suggested_model`, `cost_savings` | Router detector |
| Batch detection | `batch_opportunity`, `sequential_calls_count`, `batch_savings` | Batch detector |
| Parallel detection | `parallel_opportunity`, `independent_calls` | Parallel detector |
| Streaming detection | `streaming_candidate`, `estimated_ttft_improvement` | Streaming detector |
| Prefix cache | `prefix_reuse_count`, `prefix_cache_savings` | Prefix detector |
| Context growth | `history_percentage`, `growth_rate` | Context detector |
| Model config | `temperature`, `max_tokens`, `top_p` | Extracted from call |
| Error details | `error_type`, `error_code`, `retry_count` | Captured on failure |
| Phase tagging | `phase`, `optimizations_applied` | Auto-tagged |

### Requires Engineer Input (~39 fields)

| Category | Fields | How to Provide |
|----------|--------|----------------|
| Conversation | `conversation_id`, `turn_number`, `user_id` | See Conversation Tracking section |
| Agent context | `agent_name`, `agent_role` | Decorator parameter |
| Tool calls | `tool_calls_made`, `tool_call_count` | Pass in metadata |
| Experiment | `experiment_id`, `control_group` | Decorator parameter |
| Custom | `metadata` | Decorator parameter |

---

## Conversation Tracking

Based on the Career Copilot implementation:

### How conversation_id is generated/passed:
```python
# At app startup - create a session
obs_session = start_session("streamlit_app_session", metadata={...})

# In each call - use session ID as conversation_id
memory.conversation_id = obs_session.id
```

### How turn_number is tracked:
```python
# Increment on each message
memory.turn_number += 1

# Generate unique request ID
memory.request_id = f"{memory.conversation_id}_turn{memory.turn_number}"
```

### Integration with @observe decorator:
```python
from observatory_config import observe, start_session

# At app startup
obs_session = start_session("my_app_session")

# Pass conversation context to decorator
@observe(
    operation="chat",
    agent_name="ChatAgent",
    conversation_id=memory.conversation_id,  # Links calls together
    turn_number=memory.turn_number,          # Which turn
    user_id=user_id,                         # Optional
)
async def chat_with_kernel(message: str):
    ...
```

### Alternative: Session context manager
```python
from observatory_config import observe, observatory_session

async def chat_session(user_id: str):
    async with observatory_session(user_id=user_id) as session:
        # conversation_id and turn_number auto-managed
        while True:
            response = await chat(message)  # turn auto-incremented
```

---

## Before/After Example (Career Copilot)

### BEFORE: Manual 11-Step Pattern (~450 lines)

```python
async def chat_with_kernel(message: str) -> tuple[str, str]:
    memory.turn_number += 1
    memory.conversation_id = obs_session.id
    start_time = time.time()

    try:
        history.add_user_message(message)

        # STEP 1: Check exact cache (~30 lines)
        cached_response, cache_meta = cache.get(...)
        if cached_response:
            track_llm_call(...)  # 20+ parameters
            return cached_response, None

        # STEP 2: Check semantic cache (~30 lines)
        if semantic_cache:
            result = await semantic_cache.get(...)
            if result.hit:
                track_llm_call(...)
                return result.response, None

        # STEP 3: Get optimized prompt (~10 lines)
        _, max_tokens_limit, prompt_meta = prompt_optimizer.get_optimized_prompt(...)

        # STEP 4: Get routed model (~10 lines)
        routed_model, routing_meta = router.select(...)

        # STEP 5: Track prefix (~5 lines)
        prefix_cache.track_call(...)

        # STEP 6: Make LLM call (~40 lines with error handling)
        response = await chat_completion.get_chat_message_content(...)

        # STEP 7: Extract tokens (~30 lines)
        prompt_tokens = response.metadata.get('usage').prompt_tokens
        ...

        # STEP 8: Detect streaming candidates (~10 lines)
        streaming_detector.check_call(...)

        # STEP 8.5: Context growth detection (~20 lines)
        context_growth_detector.check_call(...)
        token_efficiency_detector.check_call(...)

        # STEP 9: Cache response (~10 lines)
        cache.set(...)
        semantic_cache.set(...)

        # STEP 10: Track with Observatory (~90 lines!)
        track_llm_call(
            model_name=routed_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            # ... 40+ more parameters
        )

        # STEP 11: Batch detection (~10 lines)
        batch_detector.track_call(...)
        sequential_detector.track_call(...)

        return response_text, plugin_used

    except Exception as e:
        # Error tracking (~50 lines)
        track_llm_call(success=False, error=str(e), ...)
        raise
```

### AFTER: With @observe (~25 lines)

```python
from observatory_config import observe

@observe(
    operation="streamlit_chat",
    agent_name="ChatAgent",
    agent_role="orchestrator",
)
async def chat_with_kernel(
    message: str,
    conversation_id: str = None,
    turn_number: int = None,
) -> tuple[str, str]:
    """Send a message to the chatbot and get a reply."""

    history.add_user_message(message)

    response = await chat_completion.get_chat_message_content(
        chat_history=history,
        settings=execution_settings,
        kernel=kernel,
    )

    response_text = str(response)
    history.add_message(response)
    plugin_used = detect_plugin_used(response)

    return response_text, plugin_used
```

**@observe automatically handles:**
- Timing (start/end)
- Cache check (exact + semantic)
- Prompt optimization detection
- Model routing detection
- Prefix cache tracking
- Token extraction from response
- All detector checks (streaming, batch, context growth, etc.)
- Cache storage
- Quality evaluation (fire-and-forget)
- Full track_llm_call() with ~100 fields
- Error handling and tracking

---

## Simplified Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PUBLIC API                               │
│                                                                 │
│   from observatory_config import observe                        │
│                                                                 │
│   @observe(operation="chat", agent_name="Bot")                  │
│   async def my_llm_call(...):                                   │
│       return await client.chat(...)                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     INTERNAL (observe.py)                        │
│                                                                 │
│   @observe decorator:                                           │
│   ├── Wraps function                                            │
│   ├── Times execution                                           │
│   ├── Runs all detectors (from existing files)                  │
│   ├── Extracts data from response                               │
│   └── Calls track_llm_call() (from __init__.py)                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                    Uses existing components:
                    ├── cache.py (CacheManager)
                    ├── execution.py (detectors)
                    ├── router.py (ModelRouter)
                    ├── judge.py (LLMJudge)
                    └── collector.py (track_llm_call)
```

### What Gets Removed

| Component | Status |
|-----------|--------|
| `TrackedLLMCall` class | **Remove** - replaced by @observe |
| `tracked_call()` factory | **Remove** - replaced by @observe |
| `create_tracked_call()` | **Remove** - replaced by @observe |
| `track_llm_call()` | **Keep** - internal, called by @observe |
| All detectors | **Keep** - used internally by @observe |
| All optimization components | **Keep** - used internally by @observe |

---

## Files to Create/Update

### New Files

| File | Purpose |
|------|---------|
| `observatory/observe.py` | The `@observe` decorator - THE public interface |

### Files to Update

| File | Changes |
|------|---------|
| `observatory/__init__.py` | Export `observe`, remove TrackedLLMCall exports |
| `observatory/tracked_call.py` | **Delete** or mark as deprecated |
| `observatory_config_template.py` | Add OPTIMIZATIONS section, export `observe` |
| `templates/INTEGRATION_GUIDE.md` | Rewrite to focus on simple `@observe` pattern |

### Dashboard Updates (Frontend)

| File/Component | Changes |
|----------------|---------|
| Opportunities page | Show detected opportunities with code examples |
| Fix suggestions | Generate copy-paste code for OPTIMIZATIONS config |
| Comparison view | Baseline vs Optimized metrics side-by-side |

---

## Implementation Status

### ✅ Phase 1: Core @observe Decorator (COMPLETED)
- [x] Create `observatory/observe.py`
- [x] Basic decorator that wraps async/sync functions
- [x] Auto-extract tokens, latency, cost from response (detect OpenAI/Anthropic/Azure/SemanticKernel format)
- [x] Auto-extract content from function arguments (messages, prompt, system_prompt)
- [x] Accept optional params: operation, agent_name, conversation_id, turn_number, etc.
- [x] Call `track_llm_call()` with all extracted + passed data

### ✅ Phase 2: Integrate Detectors (COMPLETED)
- [x] Run all existing detectors inside @observe:
  - [x] cache.get() / cache.set()
  - [x] semantic_cache.get() / semantic_cache.set()
  - [x] router.select()
  - [x] prefix_cache.track_call()
  - [x] streaming_detector.check_call()
  - [x] batch_detector.track_call()
  - [x] context_growth_detector.check_call()
  - [x] token_efficiency_detector.check_call()
  - [x] judge.maybe_evaluate() (fire-and-forget)
- [x] Baseline mode: detect only, log opportunities
- [x] Optimized mode: apply optimizations (return cached, use routed model, etc.)

### ✅ Phase 3: Cleanup & Export (COMPLETED)
- [x] Export `observe` from `observatory/__init__.py`
- [x] Export `observe` from `observatory_config_template.py`
- [x] Mark `TrackedLLMCall`, `tracked_call()`, `create_tracked_call()` as legacy
- [x] Update `INTEGRATION_GUIDE.md` with new simple pattern

### ✅ Phase 4: Optimization Shell (COMPLETED)
- [x] Add OPTIMIZATIONS config section to template
- [ ] Create `@optimization` decorator for custom implementations (future enhancement)
- [x] Wire optimized mode to check OPTIMIZATIONS config first

### 🔲 Phase 5: Dashboard Updates (TODO)
- [ ] Show detected opportunities with code examples
- [ ] Generate copy-paste OPTIMIZATIONS config
- [ ] Baseline vs Optimized comparison view

---

## Usage Examples

### Basic Integration (Baseline)

```python
# Step 1: Copy observatory_config.py to your project
# Step 2: Add @observe to your LLM calls

from observatory_config import observe

@observe(operation="chat", agent_name="ChatBot")
async def chat(messages: list, model: str = "gpt-4o-mini"):
    return await client.chat.completions.create(
        model=model,
        messages=messages
    )

# That's it. All metrics tracked, all opportunities detected.
```

### With Conversation Tracking

```python
from observatory_config import observe, observatory_session

# Option A: Pass explicitly
@observe(operation="chat")
async def chat(messages, conversation_id=None, turn_number=None):
    return await client.chat.completions.create(messages=messages)

# Option B: Use session context
async def chat_session(user_id: str):
    async with observatory_session(user_id=user_id) as session:
        while True:
            response = await chat(messages)  # turn auto-tracked
            # ...
```

### Adding Optimizations (After Reviewing Dashboard)

```python
# In observatory_config.py or optimizations.py

OPTIMIZATIONS = {
    "chat": {
        "cache": {"enabled": True, "ttl": 1800},
    },
    "score_resume": {
        "batch": {"enabled": True, "size": 5},
        "route_to": "gpt-4o-mini",
    },
    "deep_analyze": {
        "cache": {"enabled": True, "ttl": 7200},
        "prefix_cache": {"enabled": True},
        "streaming": {"enabled": True},
    },
}

# Switch to optimized mode
# export OBSERVATORY_PHASE=optimized
```

### Custom Optimization Implementation

```python
from observatory_config import optimization

# For complex optimizations that need custom logic
@optimization("score_resume", "batch")
async def score_resume_batched(items: list):
    """Custom batching implementation for resume scoring."""
    # Combine multiple resumes into one prompt
    combined_prompt = "\n---\n".join([item["resume"] for item in items])

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": BATCH_SCORING_PROMPT},
            {"role": "user", "content": combined_prompt}
        ]
    )

    # Parse and return individual scores
    return parse_batch_scores(response, items)
```

---

## Resolved Questions

1. **Detector storage**: Detection results stored in `llm_calls` table metadata field. Separate `opportunities` table for dashboard aggregation (future).

2. **Optimization config location**: ✅ OPTIMIZATIONS lives in `observatory_config.py` - one file to manage.

3. **Custom implementation discovery**: Deferred to future enhancement (`@optimization` decorator).

4. **Batch execution**: Deferred to future enhancement. Current focus is on simpler optimizations (cache, routing).

---

## Files Created/Modified

| File | Status | Description |
|------|--------|-------------|
| `observatory/observe.py` | ✅ Created | Core `@observe` decorator (~750 lines) |
| `observatory/__init__.py` | ✅ Updated | Exports `observe`, `extract_response`, `ExtractedResponse` |
| `templates/observatory_config_template.py` | ✅ Updated | Added OPTIMIZATIONS section, `observe` export |
| `templates/INTEGRATION_GUIDE.md` | ✅ Updated | Rewritten for simple `@observe` pattern |
| `UNIVERSAL_SDK_PLAN.md` | ✅ Updated | This file - marked phases complete |

---

## Config File Structure

```python
# observatory_config.py

# =============================================================================
# SECTION 1: OPTIMIZATIONS (engineer fills after dashboard review)
# =============================================================================
OPTIMIZATIONS = {
    "chat": {"cache": {"enabled": True, "ttl": 1800}},
    "score_resume": {"route_to": "gpt-4o-mini"},
}

# =============================================================================
# SECTION 2: PROJECT CONFIG (engineer fills once)
# =============================================================================
PROJECT_NAME = "my-app"
DEFAULT_MODEL = "gpt-4o-mini"

# =============================================================================
# SECTION 3: SDK INTERNALS (don't edit below)
# =============================================================================
# ... all Observatory component setup ...
# ... observe = partial(_sdk_observe, obs=obs, cache=cache, ...) ...
```

---

## Next Steps

1. [x] Create `observatory/observe.py` with @observe decorator
2. [x] Update exports in `__init__.py`
3. [x] Add OPTIMIZATIONS section to config template
4. [x] Update integration guide
5. [ ] Dashboard: Show opportunities with copy-paste code
6. [ ] Dashboard: Baseline vs Optimized comparison view
