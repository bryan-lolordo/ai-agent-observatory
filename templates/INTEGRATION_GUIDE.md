# Observatory Integration Guide

## Overview

Observatory tracks LLM calls with a 139-field schema, detects optimization opportunities, and applies optimizations in a two-phase system.

**Key Concept**: Use `@observe` decorator for simple tracking, review opportunities in dashboard, add optimizations to your config.

---

## Quick Start (5 Minutes)

### Step 1: Copy the Config Template

```bash
cp templates/observatory_config_template.py your-project/observatory_config.py
```

### Step 2: Add @observe to Your LLM Calls

```python
from observatory_config import observe

@observe(operation="chat", agent_name="ChatBot")
async def chat(prompt: str, conversation_id: str = None, turn_number: int = None):
    return await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
```

**That's it.** All metrics tracked, all opportunities detected.

---

## How It Works

### Phase 1: Baseline (Detection)

```bash
export OBSERVATORY_PHASE=baseline  # This is the default
```

In baseline mode, `@observe`:
- Tracks all metrics (tokens, latency, cost, content)
- Runs all detectors passively
- Identifies optimization opportunities
- **Does NOT change your app's behavior**

### Phase 2: Optimized (Apply Fixes)

After reviewing opportunities in the dashboard:

1. Add optimizations to your `observatory_config.py`:

```python
OPTIMIZATIONS = {
    "chat": {
        "cache": {"enabled": True, "ttl": 1800},
    },
    "score_resume": {
        "cache": {"enabled": True, "ttl": 3600},
        "route_to": "gpt-4o-mini",
    },
}
```

2. Switch to optimized mode:

```bash
export OBSERVATORY_PHASE=optimized
```

Now `@observe` will:
- Check cache before calling LLM
- Route to specified models
- Apply all enabled optimizations
- Track baseline vs optimized comparisons

---

## @observe Decorator Reference

```python
@observe(
    # Required
    operation="your_operation",     # Name for tracking/grouping

    # Optional - recommended
    agent_name="YourAgent",         # Component/plugin name
    agent_role="analyst",           # Role: analyst, coordinator, writer, etc.

    # Optional - conversation tracking
    # These can be passed as function params instead
    conversation_id=None,           # Links related calls
    turn_number=None,               # Which turn in conversation
    user_id=None,                   # User identifier

    # Optional - control
    cache_key=None,                 # Dict for cache key generation
    skip_cache=False,               # Skip cache check
    skip_quality_eval=False,        # Skip LLM-as-judge
    complexity=0.5,                 # For model routing (0.0-1.0)
    metadata=None,                  # Additional tracking data
)
async def your_function(...):
    ...
```

---

## Conversation Tracking

For multi-turn conversations, pass `conversation_id` and `turn_number`:

```python
@observe(operation="chat", agent_name="ChatBot")
async def chat(
    prompt: str,
    conversation_id: str = None,  # @observe extracts this automatically
    turn_number: int = None,      # @observe extracts this automatically
):
    return await client.chat.completions.create(...)

# Usage
response = await chat(
    prompt="Hello",
    conversation_id=session_id,
    turn_number=1,
)
```

---

## Supported Response Formats

`@observe` auto-detects and extracts from:

| Format | Example |
|--------|---------|
| OpenAI/Azure | `response.choices[0].message.content` |
| Anthropic | `response.content[0].text` |
| Semantic Kernel | `response.content` with `response.metadata['usage']` |
| Dictionary | `{"content": "...", "usage": {...}}` |
| Tuple | `(response_text, {"prompt_tokens": 100, ...})` |
| String | Plain text response |

---

## Available Optimizations

Add these to your `OPTIMIZATIONS` dict:

| Optimization | Config | Description |
|--------------|--------|-------------|
| Exact cache | `"cache": {"enabled": True, "ttl": 3600}` | Hash-based caching |
| Semantic cache | `"semantic_cache": {"enabled": True, "threshold": 0.92}` | Similarity-based caching |
| Model routing | `"route_to": "gpt-4o-mini"` | Use specific model |
| Streaming | `"streaming": {"enabled": True}` | Enable streaming |
| Prefix cache | `"prefix_cache": {"enabled": True}` | Azure/Anthropic prefix caching |

### Example Configuration

```python
OPTIMIZATIONS = {
    # Simple operation - just cache it
    "get_job_details": {
        "cache": {"enabled": True, "ttl": 3600},
    },

    # Chat - cache + cheaper model
    "chat_response": {
        "cache": {"enabled": True, "ttl": 1800},
        "route_to": "gpt-4o-mini",
    },

    # Analysis - semantic cache + streaming
    "deep_analyze": {
        "semantic_cache": {"enabled": True, "threshold": 0.90},
        "streaming": {"enabled": True},
    },
}
```

---

## Before/After Comparison

### Before: Manual 450-Line Pattern

```python
async def chat_with_kernel(message: str) -> tuple[str, str]:
    memory.turn_number += 1
    memory.conversation_id = obs_session.id
    start_time = time.time()

    try:
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

        # STEP 9: Cache response (~10 lines)
        cache.set(...)

        # STEP 10: Track with Observatory (~90 lines!)
        track_llm_call(
            model_name=routed_model,
            prompt_tokens=prompt_tokens,
            # ... 40+ more parameters
        )

        return response_text, plugin_used

    except Exception as e:
        track_llm_call(success=False, error=str(e), ...)
        raise
```

### After: With @observe (~25 Lines)

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

---

## Minimum Viable Integration

If you just want basic tracking with no optimizations:

```python
from observatory_config import observe

@observe(operation="my_operation")
async def my_llm_call(prompt: str):
    return await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
```

All features are optional and can be added incrementally.

---

## Session Management (Optional)

For grouping multiple calls together:

```python
from observatory_config import observe, start_session, end_session

async def chat_session(user_id: str):
    session = start_session("chat", user_id=user_id)

    try:
        while True:
            user_input = get_user_input()
            if user_input == "exit":
                break

            response = await chat(
                prompt=user_input,
                conversation_id=session.id,
                turn_number=turn,
            )
            display(response)
            turn += 1

        end_session(session, success=True)
    except Exception as e:
        end_session(session, success=False, error=str(e))
        raise
```

---

## Workflow Summary

```
┌─────────────────────────────────────────────────────────────┐
│  1. ADD @observe TO YOUR LLM CALLS                          │
│                                                             │
│     @observe(operation="chat")                              │
│     async def chat(prompt):                                 │
│         return await client.chat.completions.create(...)    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  2. RUN IN BASELINE MODE (default)                          │
│                                                             │
│     export OBSERVATORY_PHASE=baseline                       │
│     python your_app.py                                      │
│                                                             │
│     → All metrics tracked                                   │
│     → Opportunities detected                                │
│     → No behavior changes                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  3. REVIEW OPPORTUNITIES IN DASHBOARD                       │
│                                                             │
│     Dashboard shows:                                        │
│     - Cache opportunities: "47 duplicate calls detected"    │
│     - Routing opportunities: "Use gpt-4o-mini for simple"   │
│     - Code to copy/paste into your config                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  4. ADD OPTIMIZATIONS TO CONFIG                             │
│                                                             │
│     # In observatory_config.py                              │
│     OPTIMIZATIONS = {                                       │
│         "chat": {"cache": {"enabled": True, "ttl": 1800}},  │
│     }                                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  5. SWITCH TO OPTIMIZED MODE                                │
│                                                             │
│     export OBSERVATORY_PHASE=optimized                      │
│     python your_app.py                                      │
│                                                             │
│     → Optimizations applied                                 │
│     → Compare baseline vs optimized in dashboard            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```
