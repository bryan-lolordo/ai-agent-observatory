# Observatory Optimization Roadmap

## Current Status

### Working Automatically (via OPTIMIZATIONS config)
- [x] **Exact Cache** - Returns cached response for identical prompts
- [x] **Semantic Cache** - Returns cached response for similar prompts
- [x] **Model Routing** - Routes to cheaper/better models based on complexity
- [x] **Detection** - Identifies batch/parallel/streaming opportunities in dashboard

### Requires Code Changes
- [ ] **Parallel Execution** - Run multiple LLM calls concurrently
- [ ] **Batching** - Combine multiple items into single LLM call

---

## Discussion Items

### 1. Parallel Execution for `quick_score_job`

**Current code (sequential):**
```python
for job in jobs:
    scored = await self._quick_score_job_match(resume_text, job)
    scored_jobs.append(scored)
    await asyncio.sleep(0.5)
```

**Proposed change:**
```python
import asyncio

semaphore = asyncio.Semaphore(5)  # Max 5 concurrent

async def score_one(job):
    async with semaphore:
        return await self._quick_score_job_match(resume_text, job)

scored_jobs = await asyncio.gather(*[score_one(job) for job in jobs])
```

**Impact:** ~5x faster (parallel), same number of LLM calls, same cost

**Location:** `ResumeMatchingPlugin.py` lines 254-260

---

### 2. True Batching for `quick_score_job`

Combine 3 jobs into 1 LLM call with a batch-aware prompt.

**Requires:**
1. New method `_quick_score_jobs_batch(resume_text, jobs: list[dict])`
2. Modified prompt that scores multiple jobs and returns JSON array
3. Loop change to process in batches of 3

**Impact:** 3x fewer LLM calls, ~66% cost reduction for scoring

**Complexity:** Medium - requires new prompt engineering and result parsing

---

### 3. OPTIMIZATIONS Config Structure

**Current (simple):**
```python
OPTIMIZATIONS = {
    "quick_score_job": {
        "cache": {"enabled": True, "ttl": 86400},
        "route_to": "gpt-4o-mini",
    },
}
```

**Question:** Do we want batching/parallel to be config-driven or code-driven?

**Config-driven (more magic):**
```python
OPTIMIZATIONS = {
    "quick_score_job": {
        "cache": {"enabled": True, "ttl": 86400},
        "batch": {"enabled": True, "size": 3},      # Requires batch prompt
        "parallel": {"enabled": True, "max": 5},    # Requires code wrapper
    },
}
```

**Code-driven (explicit):**
```python
# In your code, you call helpers explicitly
from observatory import parallel_execute
scores = await parallel_execute(quick_score_job, jobs, max_concurrent=5)
```

**Recommendation:** Code-driven for batch/parallel (they change call patterns), config-driven for cache/routing (transparent).

---

### 4. Operations to Optimize

| Operation | Cache | Parallel | Batch | Route |
|-----------|-------|----------|-------|-------|
| `quick_score_job` | Yes (24h) | Yes (5 concurrent) | Maybe (3 per call) | gpt-4o-mini |
| `deep_analyze_job` | Yes (24h) | Yes (3 concurrent) | No | gpt-4o |
| `generate_sql` | Yes (1h) | No | No | gpt-4o-mini |
| `improve_bullet` | Yes (2h) | No | No | gpt-4o |
| `streamlit_chat` | No | No | No | Default |
| `scenario_chat` | No | No | No | Default |

---

### 5. Bugs Fixed This Session

1. **Router tuple unpacking** - `observe.py:745` was storing tuple instead of unpacking `(model, decision)`
2. **Token extraction for Semantic Kernel** - `observe.py:166-220` now correctly extracts from `CompletionUsage` object in metadata
3. **Semantic cache causing hangs in baseline** - `observe.py:702-710, 881-894` was calling ChromaDB embedding queries even in baseline mode, which is slow. Fixed to only query/store in optimized mode when explicitly enabled.
4. **system_prompt/user_message not saved** - `storage.py:403-404` was only checking `prompt_breakdown` dict, not direct `llm_call` fields. Fixed to check `llm_call.system_prompt` first.
5. **phase not tracked** - `observe.py:964` wasn't including `current_phase` in metadata. Added `"phase": current_phase` to the metadata dict.
6. **conversation_id/turn_number low population** - Plugin LLM calls didn't receive these from parent calls. Implemented ContextVar propagation so nested @observe calls automatically inherit conversation context.
7. **judge_score not populated** - `judge.py` required `llm_client` parameter but `observe.py` didn't pass one. Fixed by making LLMJudge self-contained with its own OpenAI client (uses `OPENAI_API_KEY` env var). Renamed `maybe_evaluate()` → `evaluate_async()` for clarity.

---

### 6. Files Modified This Session

| File | Changes |
|------|---------|
| `observatory/observe.py` | Fixed router tuple bug, SK token extraction, semantic cache baseline hang, added ContextVar for conversation propagation, updated judge call to use `evaluate_async()` |
| `observatory/judge.py` | Added self-contained OpenAI client, renamed `maybe_evaluate()` → `evaluate_async()`, added `api_key`/`api_base` init params |
| `observatory/storage.py` | Fixed system_prompt/user_message extraction |
| `observatory/__init__.py` | Exported set_conversation_context, get_conversation_context |
| `README.md` | Polished for job interviews, added video/screenshot |
| `docs/media/` | Created folder for demo assets |
| `UNIVERSAL_SDK_PLAN.md` | Moved to `docs/` |

---

## Next Steps

1. **Add OPTIMIZATIONS to config** for caching (immediate win)
2. **Implement parallel execution** in ResumeMatchingPlugin (easy, big impact)
3. **Decide on batching** - worth the prompt engineering effort?
4. **Run baseline scenarios** with token fix to verify tracking works
5. **Compare baseline vs optimized** in dashboard

---

## Questions to Resolve

- [ ] What TTL makes sense for job/resume caching? (Jobs don't change often)
- [ ] Max concurrency for parallel scoring? (Azure rate limits)
- [ ] Is batching worth it for quick_score_job? (Prompt complexity vs cost savings)
- [ ] Should deep_analyze_job also be parallelized?
