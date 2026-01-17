# AI Agent Observatory

**Production-ready observability platform for AI agents and LLM applications**

<!-- TODO: Replace with your video link -->
<p align="center">
  <a href="YOUR_VIDEO_LINK_HERE">
    <img src="https://img.shields.io/badge/Watch%20Demo-Video-red?style=for-the-badge&logo=youtube" alt="Watch Demo Video">
  </a>
</p>

<!-- TODO: Add dashboard screenshot
<p align="center">
  <img src="docs/images/dashboard-screenshot.png" alt="Observatory Dashboard" width="800">
</p>
-->

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
| **139 Metrics** | Tokens, cost, latency, quality, cache, routing per call |
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

## Demo Walkthrough

### Dashboard Overview

The main dashboard shows KPIs at a glance with quick access to all 7 analytics stories.

<!-- TODO: Add screenshot
<p align="center">
  <img src="docs/images/01-dashboard.png" alt="Dashboard Overview" width="800">
</p>
-->

### 3-Layer Drill-Down

Every story follows the same pattern: **KPIs → Operations → Individual Calls**

**Layer 1: Story KPIs** - High-level metrics and the operations table

<!-- TODO: Add screenshot
<p align="center">
  <img src="docs/images/02-layer1-kpis.png" alt="Layer 1 - Story KPIs" width="800">
</p>
-->

**Layer 2: Operation Detail** - Click any operation to see detailed breakdown

<!-- TODO: Add screenshot
<p align="center">
  <img src="docs/images/03-layer2-operation.png" alt="Layer 2 - Operation Detail" width="800">
</p>
-->

**Layer 3: Call Detail** - Click any call to see the full 139-field record

<!-- TODO: Add screenshot
<p align="center">
  <img src="docs/images/04-layer3-call.png" alt="Layer 3 - Call Detail" width="800">
</p>
-->

### Optimization Queue

Prioritized list of optimization opportunities across all stories, ranked by impact.

<!-- TODO: Add screenshot
<p align="center">
  <img src="docs/images/05-optimization-queue.png" alt="Optimization Queue" width="800">
</p>
-->

### Optimization Impact

Track before/after metrics to measure the effectiveness of your optimizations.

<!-- TODO: Add screenshot
<p align="center">
  <img src="docs/images/06-optimization-impact.png" alt="Optimization Impact" width="800">
</p>
-->

---

## 7 Analytics Stories

| Story | What It Shows |
|-------|---------------|
| **Cost** | Spending by model, agent, operation with cost breakdowns |
| **Latency** | Bottlenecks, slow calls, performance patterns |
| **Tokens** | Usage analysis, ratios, optimization opportunities |
| **Quality** | Judge scores, hallucination detection, error tracking |
| **Prompts** | System prompt analysis, chat history breakdown, token distribution |
| **Cache** | Cacheable patterns (exact, prefix, semantic) with ROI estimates |
| **Routing** | Model upgrade/downgrade recommendations with savings projections |

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

## Getting Started

### 1. Clone & Install

```bash
git clone https://github.com/bryan-lolordo/ai-agent-observatory.git
cd ai-agent-observatory
pip install -e .                    # Core SDK
pip install -e ".[ai]"              # + OpenAI/Anthropic for LLM Judge
pip install -e ".[full]"            # + Everything including SemanticCache
```

### 2. Run the Dashboard

```bash
# Terminal 1: Start API
uvicorn api.main:app --port 8000

# Terminal 2: Start Frontend
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` to view the dashboard.

### 3. Add Tracking to Your Project

```python
from observatory import Observatory, track_llm_call

# Point to the Observatory database
obs = Observatory(
    project_name="Your Project",
    db_path="/path/to/ai-agent-observatory/observatory.db"
)

# After each LLM call, track it
track_llm_call(
    observatory=obs,
    model_name="gpt-4",
    prompt_tokens=100,
    completion_tokens=50,
    latency_ms=1200,
    agent_name="MyAgent",
    operation="analyze"
)
```

### 4. Configure (Optional)

Copy `.env.example` to `.env` and add your keys:

```bash
cp .env.example .env
```

Required for LLM Judge and Semantic Cache features:
- `OPENAI_API_KEY` - For quality evaluation
- `AZURE_OPENAI_*` - Alternative to OpenAI

---

## Integration Templates

The [`templates/`](templates/) folder contains ready-to-use configuration files for adding Observatory tracking to your LLM applications:

| Template | Purpose |
|----------|---------|
| [`observatory_config_template.py`](templates/observatory_config_template.py) | One-time setup: SDK initialization, routing rules, judge criteria |
| [`llm_call_template.py`](templates/llm_call_template.py) | Code patterns to copy into files that make LLM calls |

**Quick start:**
1. Copy `observatory_config_template.py` → your project as `observatory_config.py`
2. Customize operations, prompts, and routing rules for your app
3. Use patterns from `llm_call_template.py` in your LLM-calling code

→ [Full integration guide](templates/README.md)

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **SDK** | Python 3.10+, Pydantic v2 |
| **Backend** | FastAPI, SQLAlchemy (async), SQLite/PostgreSQL |
| **Frontend** | React 18, Vite, Tailwind CSS, Recharts |

---

## Tracked Metrics

Observatory captures 139 fields per LLM call across 12 categories:

| Category | Fields |
|----------|--------|
| **Core** | ID, timestamp, provider, model, success/error |
| **Tokens** | prompt, completion, system, history, tools, cached |
| **Cost** | prompt cost, completion cost, total, savings |
| **Latency** | total, TTFT, tool execution time |
| **Context** | agent, operation, conversation, user |
| **Model Config** | temperature, max_tokens, top_p, seed |
| **Cache** | hit/miss, key, cluster, similarity score |
| **Routing** | chosen model, alternatives, complexity, savings |
| **Quality** | judge score, hallucination, confidence |
| **Errors** | type, code, retry count, strategy |
| **Streaming** | chunks, interrupted, TTFT |
| **Experiments** | A/B test ID, variant, control group |

→ [Full metrics reference](docs/METRICS.md)

---

## License

MIT License - free for personal and commercial use.
