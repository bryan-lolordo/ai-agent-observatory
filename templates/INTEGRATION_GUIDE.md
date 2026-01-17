# Observatory Integration Guide

## Overview

This guide explains how to integrate Observatory tracking into any AI application. Observatory tracks LLM calls with a 139-field schema, detects optimization opportunities, and applies optimizations in a two-phase system.

---

## Step 1: Copy the Config Template

Copy `observatory_config_template.py` to your project root and rename it:

```
your-project/
├── observatory_config.py   ← Copy template here
├── your_app.py
└── ...
```

---

## Step 2: Configure for Your Project

Edit `observatory_config.py` and update the `[PROJECT-SPECIFIC]` sections:

1. **Project name**: Set `PROJECT_NAME` via environment variable or directly
2. **Model provider**: Set `MODEL_PROVIDER` (azure, openai, anthropic)
3. **Operations**: Update cache, router, and judge with your operation names
4. **Quality criteria**: Customize judge criteria for your domain

---

## Step 3: Import What You Need

```python
from observatory_config import (
    # Main tracking
    track_llm_call,

    # Optimization components (use what you need)
    cache,
    semantic_cache,
    router,
    prefix_cache,
    prompt_optimizer,
    judge,

    # Detectors
    batch_detector,
    streaming_detector,
    context_growth_detector,

    # Helpers
    estimate_tokens,
    classify_error,
    fire_and_forget_judge,

    # Session management
    start_session,
    end_session,

    # Config constants
    CURRENT_PHASE,
    DEFAULT_MODEL,
)
```

---

## Step 4: Wrap Your LLM Calls

### Option A: Full 10-Step Pattern (Recommended)

For maximum optimization detection and tracking:

```python
import time

async def your_chat_function(user_input: str):
    operation = "chat_response"

    # Step 1: Check exact cache
    cached_response, cache_meta = cache.get(
        operation=operation,
        key_data={"user_message": user_input}
    )
    if cached_response:
        return cached_response

    # Step 2: Check semantic cache (if available)
    if semantic_cache:
        result = await semantic_cache.get(operation=operation, prompt=user_input)
        if result.hit:
            return result.response

    # Step 3: Get optimized prompt
    optimized_prompt, max_tokens, prompt_meta = prompt_optimizer.get_optimized_prompt(
        operation=operation,
        default_prompt=YOUR_SYSTEM_PROMPT
    )

    # Step 4: Get routed model
    routed_model, routing_meta = router.select(
        operation=operation,
        prompt=optimized_prompt,
        estimated_tokens=estimate_tokens(optimized_prompt),
        complexity=0.5
    )

    # Step 5: Track prefix for caching detection
    prefix_cache.track_call(
        operation=operation,
        system_prompt=optimized_prompt,
        system_prompt_tokens=estimate_tokens(optimized_prompt),
    )

    # Step 6: Make LLM call
    start_time = time.time()
    try:
        response = await your_llm_client.chat(
            model=routed_model,
            messages=[
                {"role": "system", "content": optimized_prompt},
                {"role": "user", "content": user_input}
            ],
            max_tokens=max_tokens
        )
        latency_ms = (time.time() - start_time) * 1000
        success = True
        error = None
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        success = False
        error = str(e)

    # Step 7: Extract token usage
    prompt_tokens = response.usage.prompt_tokens
    completion_tokens = response.usage.completion_tokens
    response_text = response.content

    # Step 8: Detect streaming candidates
    streaming_detector.check_call(
        operation=operation,
        latency_ms=latency_ms,
        completion_tokens=completion_tokens,
    )

    # Step 9: Cache the response
    if success:
        cache.set(
            operation=operation,
            key_data={"user_message": user_input},
            value=response_text
        )

    # Step 10: Track with Observatory
    track_llm_call(
        model_name=routed_model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        operation=operation,
        success=success,
        error=error,
        user_message=user_input,
        system_prompt=optimized_prompt,
        response_text=response_text,
        routing_decision=routing_meta,
        cache_metadata=cache_meta,
    )

    return response_text
```

### Option B: Simple Direct Tracking

For quick integration without full optimization:

```python
import time

def your_llm_call(prompt: str):
    start = time.time()

    response = your_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    latency = (time.time() - start) * 1000

    track_llm_call(
        model_name="gpt-4o-mini",
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        latency_ms=latency,
        operation="your_operation",
        user_message=prompt,
        response_text=response.choices[0].message.content,
    )

    return response.choices[0].message.content
```

### Option C: Using `tracked_call()` Context Manager

For a cleaner abstraction that handles the 10-step pattern:

```python
from observatory_config import tracked_call

async def your_analysis_function(data: dict):
    async with tracked_call(
        operation="analyze_data",
        agent_name="DataAnalyzer",
        complexity=0.6,
        cache_key={"data_id": data["id"]},
    ) as ctx:
        result = await ctx.call(
            llm_func=your_llm_callable,
            prompt=f"Analyze this: {data}",
            system_prompt="You are a data analyst.",
        )
    return result
```

---

## Step 5: Set Your Phase

Observatory operates in two phases:

| Phase | Behavior |
|-------|----------|
| `baseline` | Track metrics, detect opportunities, **no changes** to app behavior |
| `optimized` | Apply optimizations (caching, routing, compression) |

Set via environment variable:

```bash
# Start with baseline to collect data
export OBSERVATORY_PHASE=baseline

# Switch to optimized after reviewing opportunities
export OBSERVATORY_PHASE=optimized
```

Or in `.env`:

```
OBSERVATORY_PHASE=baseline
```

---

## Step 6: Use Sessions for Multi-Turn Conversations

```python
from observatory_config import start_session, end_session

async def chat_session(user_id: str):
    session = start_session("chat", user_id=user_id)

    try:
        while True:
            user_input = get_user_input()
            if user_input == "exit":
                break

            response = await your_chat_function(user_input)
            display(response)

        end_session(session, success=True)
    except Exception as e:
        end_session(session, success=False, error=str(e))
        raise
```

---

## Quick Reference: What Each Component Does

| Component | Purpose | Baseline Mode | Optimized Mode |
|-----------|---------|---------------|----------------|
| `cache` | Exact hash caching | Detect hits | Return cached |
| `semantic_cache` | Similarity-based caching | Detect similar | Return similar |
| `router` | Model selection | Log opportunities | Route to model |
| `prompt_optimizer` | Prompt compression | Calculate savings | Apply compression |
| `prefix_cache` | Azure/Anthropic prefix caching | Track prefix reuse | Ready for API |
| `judge` | Quality evaluation | Evaluate all | Evaluate all |
| `batch_detector` | Batch opportunities | Detect patterns | Ready to batch |
| `streaming_detector` | Streaming candidates | Flag candidates | Ready to stream |

---

## Minimum Viable Integration

If you just want basic tracking:

```python
from observatory_config import track_llm_call
import time

start = time.time()
response = your_llm_call(prompt)
latency = (time.time() - start) * 1000

track_llm_call(
    operation="my_operation",
    prompt_tokens=response.usage.prompt_tokens,
    completion_tokens=response.usage.completion_tokens,
    latency_ms=latency,
)
```

That's it. All other features are optional and can be added incrementally.
