# AI Agent Observatory - Project Instructions for Claude

## Overview

The AI Agent Observatory is a comprehensive metrics tracking and optimization system for AI applications. It tracks LLM calls across applications, enabling data-driven optimization through measurement of cost, latency, tokens, quality, and performance.

**Two Components:**
1. **Observatory SDK** (`observatory/`) - Shared library with models, storage, judge, router, cache
2. **observatory_config.py** - Per-project configuration file that configures the SDK

**Current Integration:** Career Copilot - a job search assistant with multiple plugins

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  APPLICATION CODE (Plugins/Services)                    │
│  - Imports from observatory_config                      │
│  - Calls track_llm_call() after each LLM operation      │
├─────────────────────────────────────────────────────────┤
│  OBSERVATORY_CONFIG.PY (per project)                    │
│  - Project settings (name, model, database path)        │
│  - Configures judge criteria, cache rules, routing      │
│  - Wrapper functions with project defaults              │
├─────────────────────────────────────────────────────────┤
│  OBSERVATORY SDK (shared library)                       │
│  - models.py: Data models (LLMCall, QualityEvaluation)  │
│  - storage.py: SQLite persistence                       │
│  - collector.py: Main Observatory class                 │
│  - judge.py: LLM-as-a-judge quality evaluation          │
│  - router.py: Model routing logic                       │
│  - cache.py: Semantic caching                           │
│  - prompts.py: Prompt management                        │
└─────────────────────────────────────────────────────────┘
```

---

## Tracking Tiers

### Tier 1 - Core Metrics (Always tracked)
- `model_name`, `prompt_tokens`, `completion_tokens`, `total_tokens`
- `prompt_cost`, `completion_cost`, `total_cost`
- `latency_ms`
- `agent_name`, `agent_role`, `operation`
- `success`, `error`

### Tier 2 - Prompt Analysis
- `prompt`, `response_text`, `system_prompt`, `user_message`
- `prompt_metadata` - Version tracking (template_id, version, optimization_flags)
- `prompt_breakdown` - Token breakdown by component
- `quality_evaluation` - LLM Judge scores (see below)

### Tier 3 - Optimization
- `routing_decision` - Model routing info (chosen_model, alternatives, complexity_score)
- `cache_metadata` - Cache info (cache_hit, cache_key, cache_cluster_id)
- `prompt_variant_id`, `test_dataset_id` - A/B testing

---

## Key SDK Files

| File | Purpose |
|------|---------|
| `observatory/__init__.py` | Exports all public APIs |
| `observatory/models.py` | Pydantic models for all data structures |
| `observatory/storage.py` | SQLite database operations |
| `observatory/collector.py` | Main Observatory class, record_call() |
| `observatory/judge.py` | LLMJudge for quality evaluation |
| `observatory/router.py` | ModelRouter for intelligent routing |
| `observatory/cache.py` | CacheManager for semantic caching |
| `observatory/prompts.py` | PromptManager for versioning |

---

## Tracking Pattern

**Standard imports for plugins:**
```python
from observatory_config import (
    track_llm_call,
    create_prompt_metadata,
    create_prompt_breakdown,
    create_routing_decision,
    create_cache_metadata,
    judge,
    DEFAULT_MODEL,
    PromptMetadata,
)
```

**Basic tracking:**
```python
start_time = time.time()
result = await self.kernel.invoke_prompt(prompt)
latency_ms = (time.time() - start_time) * 1000

track_llm_call(
    model_name=DEFAULT_MODEL,
    prompt_tokens=len(prompt) // 4,
    completion_tokens=len(str(result)) // 4,
    latency_ms=latency_ms,
    agent_name="MyPlugin",
    agent_role="analyst",
    operation="my_operation",
    success=True,
    prompt=prompt,
    response_text=str(result),
    metadata={"custom_field": "value"}
)
```

**Full tracking with all tiers:**
```python
# After LLM call...

prompt_breakdown = create_prompt_breakdown(
    system_prompt=system_prompt,
    system_prompt_tokens=len(system_prompt) // 4,
    user_message=user_message,
    user_message_tokens=len(user_message) // 4,
)

quality_eval = await judge.maybe_evaluate(
    operation="my_operation",
    prompt=prompt[:5000],
    response=result_str[:5000],
    llm_client=self.kernel,
)

routing_decision = create_routing_decision(
    chosen_model=DEFAULT_MODEL,
    alternative_models=["gpt-4o", "gpt-4o-mini"],
    reasoning="Standard complexity task",
    complexity_score=0.5,
)

cache_metadata = create_cache_metadata(
    cache_hit=False,
    cache_key="my_cache_key",
    cache_cluster_id="my_cluster",
)

track_llm_call(
    # Tier 1
    model_name=DEFAULT_MODEL,
    prompt_tokens=prompt_tokens,
    completion_tokens=completion_tokens,
    latency_ms=latency_ms,
    agent_name="MyPlugin",
    agent_role="analyst",
    operation="my_operation",
    success=True,
    
    # Tier 2
    prompt=prompt,
    response_text=result_str,
    system_prompt=system_prompt,
    user_message=user_message,
    prompt_metadata=MY_OPERATION_META,
    prompt_breakdown=prompt_breakdown,
    quality_evaluation=quality_eval,
    
    # Tier 3
    routing_decision=routing_decision,
    cache_metadata=cache_metadata,
    
    metadata={"judged": quality_eval is not None}
)
```

---

## Agent Roles

| Role | Use For |
|------|---------|
| `analyst` | Analysis, scoring, evaluation |
| `reviewer` | Quality review, critique |
| `writer` | Content generation, creative |
| `retriever` | Data fetching, search, DB queries |
| `planner` | Planning, strategy |
| `formatter` | Formatting, transformation |
| `fixer` | Error correction, improvement |
| `orchestrator` | Coordination, routing |
| `custom` | Anything else |

---

## Complexity Scores (for routing)

| Score | Task Type |
|-------|-----------|
| 0.1-0.3 | Simple: DB lookups, formatting, list retrieval |
| 0.4-0.6 | Medium: SQL generation, summarization, basic analysis |
| 0.7-0.9 | Complex: Deep analysis, creative writing, multi-step reasoning |

---

## Career Copilot Plugins

| Plugin | Operations | Agent Role |
|--------|------------|------------|
| **JobPlugin** | `find_jobs`, `get_saved_jobs` | retriever |
| **QueryDatabasePlugin** | `generate_sql`, `query_database_with_ai` | analyst |
| **ResumeMatchingPlugin** | `quick_score_job`, `deep_analyze_job`, `list_resumes` | analyst/retriever |
| **ResumeTailoringPlugin** | `improve_resume_bullet` | writer |
| **SelfImprovingMatchPlugin** | `critique_match`, `deep_analyze_with_guidance` | analyst/reviewer |

---

## Database Schema

**LLM Calls Table:** Stores all tracked calls with full metrics
**Sessions Table:** Groups related calls with aggregate stats

**Export:** Dashboard can export to Excel with LLM Calls and Sessions sheets

---

