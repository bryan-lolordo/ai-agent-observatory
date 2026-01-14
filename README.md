# AI Agent Observatory

**Production-ready observability platform for AI agents and LLM applications**

<!-- TODO: Replace with your video link -->
<p align="center">
  <a href="YOUR_VIDEO_LINK_HERE">
    <img src="https://img.shields.io/badge/Watch%20Demo-Video-red?style=for-the-badge&logo=youtube" alt="Watch Demo Video">
  </a>
</p>

<!-- TODO: Add dashboard screenshot -->
<p align="center">
  <img src="docs/images/dashboard-screenshot.png" alt="Observatory Dashboard" width="800">
</p>

---

## Why Observatory?

Building AI agents is easy. **Understanding why they cost so much is hard.**

Most teams discover their LLM costs are 10x higher than expected, but have no visibility into *why*. Which prompts are bloated? Which calls could be cached? Which operations use GPT-4 when GPT-4o-mini would suffice?

**Observatory answers these questions** by passively tracking every LLM call and surfacing actionable insights:

- **"Your system prompts consume 80% of tokens"** → with specific prompts to compress
- **"38% of calls are exact duplicates"** → with caching recommendations
- **"Simple operations use expensive models"** → with routing suggestions

> Observatory is a **passive observer** - it tracks and visualizes, but never modifies your LLM calls. You stay in control.

---

## Highlights

| | |
|---|---|
| **70+ Metrics** | Tokens, cost, latency, quality, cache, routing per call |
| **7 Analytics Stories** | Cost, Latency, Tokens, Quality, Prompts, Cache, Routing |
| **3-Layer Drill-Down** | KPIs → Operations → Individual Calls |
| **6 SDK Components** | Observatory, LLMJudge, CacheManager, SemanticCache, ModelRouter, PromptManager |
| **Framework Agnostic** | LangGraph, AutoGen, Semantic Kernel, or any LLM |
| **Full Stack** | Python SDK + FastAPI Backend + React Dashboard |

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![React](https://img.shields.io/badge/React-18+-61DAFB.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## Dashboard

### 7 Analytics Stories

Each story provides deep-dive analysis with 3-layer drill-down (KPIs → Operations → Individual Calls):

| Story | What It Shows |
|-------|---------------|
| **Cost** | Spending by model, agent, operation with cost breakdowns |
| **Latency** | Bottlenecks, slow calls, performance patterns |
| **Tokens** | Usage analysis, ratios, optimization opportunities |
| **Quality** | Judge scores, hallucination detection, error tracking |
| **Prompts** | System prompt analysis, chat history breakdown, token distribution |
| **Cache** | Cacheable patterns (exact, prefix, semantic) with ROI estimates |
| **Routing** | Model upgrade/downgrade recommendations with savings projections |

### Additional Pages

- **Dashboard** - Overview KPIs with trends and quick access to all stories
- **Optimization Impact** - Before/after comparisons to measure effectiveness
- **Optimization Queue** - Prioritized optimization opportunities across all stories

---

## Quick Start

```python
from observatory import Observatory, track_llm_call
import time

# Initialize
obs = Observatory(project_name="My AI App")

# Make your LLM call
start = time.time()
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)

# Track it
track_llm_call(
    observatory=obs,
    model_name="gpt-4",
    prompt_tokens=response.usage.prompt_tokens,
    completion_tokens=response.usage.completion_tokens,
    latency_ms=(time.time() - start) * 1000,
    agent_name="Chatbot",
    operation="greeting"
)
```

See [full SDK documentation](docs/METRICS.md) for all 70+ tracked fields.

---

## Architecture

```
ai-agent-observatory/
├── observatory/          # Python SDK (6 components)
│   ├── collector.py      # Main Observatory class
│   ├── cache.py          # CacheManager + PrefixCacheDetector
│   ├── semantic_cache.py # SemanticCache (vector similarity)
│   ├── judge.py          # LLMJudge (quality evaluation)
│   ├── router.py         # ModelRouter (cost/quality routing)
│   └── prompts.py        # PromptManager (versioning, A/B tests)
│
├── api/                  # FastAPI backend
│   ├── routers/stories/  # 7 analytics story endpoints
│   └── services/         # Business logic layer
│
├── frontend/             # React + Vite + Tailwind
│   └── src/pages/        # Dashboard, Stories, Queue
│
└── tests/                # Unit + integration tests
```

---

## Installation

```bash
# Clone and install SDK
git clone https://github.com/yourusername/ai-agent-observatory.git
cd ai-agent-observatory
pip install -e .

# Run dashboard
pip install -e ".[dashboard]"
uvicorn api.main:app --port 8000 &
cd frontend && npm install && npm run dev
```

Dashboard: `http://localhost:5173` | API: `http://localhost:8000`

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **SDK** | Python 3.10+, Pydantic v2 |
| **Backend** | FastAPI, SQLAlchemy (async), SQLite/PostgreSQL |
| **Frontend** | React 18, Vite, Tailwind CSS, Recharts |

---

## Tracked Metrics

Observatory captures 70+ fields per LLM call across 12 categories:

**Core** · ID, timestamp, provider, model, success/error
**Tokens** · prompt, completion, system, history, tools, cached
**Cost** · prompt cost, completion cost, total, savings
**Latency** · total, TTFT, tool execution time
**Context** · agent, operation, conversation, user
**Model Config** · temperature, max_tokens, top_p, seed
**Cache** · hit/miss, key, cluster, similarity score
**Routing** · chosen model, alternatives, complexity, savings
**Quality** · judge score, hallucination, confidence
**Errors** · type, code, retry count, strategy
**Streaming** · chunks, interrupted, TTFT
**Experiments** · A/B test ID, variant, control group

→ [Full metrics reference](docs/METRICS.md)

---

## Roadmap

### Completed
- [x] Core SDK with 70+ metrics
- [x] 7 analytics stories with 3-layer drill-down
- [x] FastAPI backend + React dashboard
- [x] Semantic caching, LLM judge, model routing
- [x] Optimization queue with prioritization

### Planned
- [ ] Real-time WebSocket updates
- [ ] Alert system (email/Slack)
- [ ] Distributed tracing support

---

## License

MIT License - free for personal and commercial use.
