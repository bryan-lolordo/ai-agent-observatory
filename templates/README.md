# Observatory Integration Templates

These templates help you add Observatory tracking to your AI applications.

## Quick Start

### 1. Install the SDK

```bash
# From local clone
pip install -e /path/to/ai-agent-observatory

# Or from GitHub
pip install git+https://github.com/bryan-lolordo/ai-agent-observatory.git

# Optional: for semantic caching
pip install chromadb
```

### 2. Copy the Config Template

```bash
cp templates/observatory_config_template.py your-project/observatory_config.py
```

Edit `observatory_config.py` and customize:
- `PROJECT_NAME` - Your project name
- `operations` in judge, cache, router - Your operations
- `PROMPT_VARIANTS` and `OPERATION_COMPLEXITY` - Your prompts

### 3. Add Tracking to Your Code

Use the `TrackedLLMCall` context manager for the cleanest integration:

```python
from observatory import create_tracked_call

with create_tracked_call(
    observatory=obs,
    operation="chat",
    model_name="gpt-4o-mini",
    prompt=user_message,
    # Optional optimization components
    cache=cache,
    semantic_cache=semantic_cache,
    router=router,
    judge=judge,
) as tracked:
    # Make your LLM call
    response = client.chat.completions.create(...)
    tracked.set_response(response)

# Result available after context exits
final_response = tracked.result.response_text
```

## File Overview

| File | Purpose |
|------|---------|
| `observatory_config_template.py` | One-time setup - creates all Observatory components |

## The 10-Step Optimization Pattern

Every LLM call should follow these steps:

1. **Check exact cache** - Skip LLM if we have cached response
2. **Check semantic cache** - Skip if similar prompt was answered
3. **Get optimized prompt** - Compress if in optimized phase
4. **Get routed model** - Select best model for operation
5. **Track prefix cache** - Detect prefix caching opportunities
6. **Make LLM call** - The actual API call
7. **Extract tokens** - Get usage from response
8. **Cache response** - Store for future hits
9. **Evaluate quality** - LLM Judge scoring
10. **Track with Observatory** - Record everything

## Phases

Set via environment variable:

```bash
# Baseline: Track metrics only, no behavior changes (default)
export OBSERVATORY_PHASE=baseline

# Optimized: Apply caching, routing, compression
export OBSERVATORY_PHASE=optimized
```

Start with `baseline` to collect data, then switch to `optimized` to see savings.

---

## Production Hardening (v0.4.0)

Observatory includes production-ready features for enterprise deployments.

### Circuit Breaker

Prevents cascading failures when external services are unhealthy:

```python
from observatory import create_circuit_breaker, CircuitOpenError

# Create circuit breaker
cb = create_circuit_breaker(
    name="llm_provider",
    failure_threshold=5,      # Open after 5 failures
    recovery_timeout=30.0,    # Try recovery after 30s
    success_threshold=2,      # Close after 2 successes
)

# Use as decorator
@cb.protect
def call_llm(prompt):
    return client.chat.completions.create(...)

# Or as context manager
with cb.call() as allowed:
    if allowed:
        response = call_llm(prompt)
    else:
        response = fallback_response
```

**Environment Variables:**
```bash
CB_ENABLED=true
CB_FAILURE_THRESHOLD=5
CB_RECOVERY_TIMEOUT=30
CB_SUCCESS_THRESHOLD=2
```

### Async Write Queue

Non-blocking database writes with background processing:

```python
from observatory import AsyncWriteQueue

# Create and start async writer
async_writer = AsyncWriteQueue(
    storage=obs.storage,
    batch_size=10,           # Items per batch
    flush_interval=1.0,      # Seconds between flushes
    max_queue_size=1000,     # Max pending items
)
async_writer.start()

# Writes are now non-blocking
# On shutdown:
async_writer.shutdown(wait=True)
```

**Environment Variables:**
```bash
ASYNC_WRITER_ENABLED=true
ASYNC_WRITER_BATCH_SIZE=10
ASYNC_WRITER_FLUSH_INTERVAL=1.0
ASYNC_WRITER_MAX_QUEUE_SIZE=1000
```

### Graceful Degradation

Observatory will never crash your application:

```python
from observatory import SafeObservatoryWrapper, safe_call

# Wrap entire Observatory
safe_obs = SafeObservatoryWrapper(obs)
safe_obs.record_call(...)  # Never raises exceptions

# Or wrap individual calls
result = safe_call(
    storage.save_llm_call,
    llm_call,
    default=None,
    operation_name="save_llm_call"
)
```

### Health Checks

Monitor system status for Kubernetes probes and dashboards:

```python
from observatory import observatory_health_check, HealthStatus

# Comprehensive health check
health = observatory_health_check(
    storage=storage,
    cache=cache,
    semantic_cache=semantic_cache,
    judge=judge,
    async_writer=async_writer,
)

# Returns:
# {
#     "status": "healthy",      # or "degraded", "unhealthy"
#     "healthy": True,
#     "timestamp": 1234567890,
#     "components": {
#         "storage": {"status": "healthy", "latency_ms": 5.2},
#         "cache": {"status": "healthy", "entries": 150, "hit_rate": 0.85},
#         ...
#     }
# }

# Use in FastAPI/Flask
@app.get("/health")
def health():
    return observatory_health_check(storage=storage, cache=cache)

@app.get("/health/live")
def liveness():
    result = observatory_health_check(storage=storage, include_details=False)
    return {"status": "ok"} if result["healthy"] else {"status": "fail"}
```

### Lazy Loading & Connection Pooling

Database connections are optimized for production:

```python
from observatory import Storage

# Lazy loading (default) - defers initialization until first use
storage = Storage(lazy=True)

# Or eager initialization
storage = Storage(lazy=False)
```

**Connection Pool Environment Variables:**
```bash
OBSERVATORY_DB_POOL_SIZE=5
OBSERVATORY_DB_MAX_OVERFLOW=10
OBSERVATORY_DB_POOL_TIMEOUT=30
OBSERVATORY_DB_POOL_RECYCLE=3600
OBSERVATORY_DB_POOL_PRE_PING=true
```

---

## Complete Production Setup

Here's a complete setup with all production features:

```python
import os
from observatory import (
    Observatory,
    Storage,
    CacheManager,
    SemanticCache,
    LLMJudge,
    ModelRouter,
    AsyncWriteQueue,
    create_circuit_breaker,
    observatory_health_check,
)

# Initialize with lazy loading
storage = Storage(lazy=True)
obs = Observatory(project_name="my_app", storage=storage)

# SDK components
cache = CacheManager(observatory=obs, operations={"chat": {"ttl": 3600}})
judge = LLMJudge(observatory=obs, operations={"chat"}, sample_rate=0.1)
router = ModelRouter(observatory=obs, default_model="gpt-4o-mini")

# Production hardening
async_writer = AsyncWriteQueue(storage=storage)
async_writer.start()

storage_cb = create_circuit_breaker(name="storage")
llm_cb = create_circuit_breaker(name="llm_provider")

# Health endpoint
def get_health():
    return observatory_health_check(
        storage=storage,
        cache=cache,
        judge=judge,
        async_writer=async_writer,
        circuit_breakers={"storage": storage_cb, "llm": llm_cb},
    )

# Shutdown handler
import atexit
atexit.register(lambda: async_writer.shutdown(wait=True))
```

---

## Version History

| Version | Features |
|---------|----------|
| 0.4.0 | Production hardening: circuit breaker, async writes, health checks, lazy loading |
| 0.3.0 | Optimization tracking, baseline/optimized phases |
| 0.2.0 | Semantic caching, prompt management |
| 0.1.0 | Core tracking, caching, routing, quality evaluation |
