# AI Agent Observatory - Data Stories Implementation Plan

## 📋 Document Overview

This document outlines the complete implementation plan for transforming the AI Agent Observatory dashboard into a **story-driven optimization experience**. The goal is to make data insights actionable by guiding developers from high-level stories down to specific code changes.

**Last Updated:** December 2024  
**Migration Status:** Streamlit → React + FastAPI ✅ COMPLETE

---

## 🏗️ Project Architecture (Updated)

```
ai-agent-observatory/
│
├── observatory/                    # Core tracking library (unchanged)
│   ├── __init__.py                 # Main exports
│   ├── cache.py                    # Caching logic
│   ├── collector.py                # Tracks sessions & LLM calls
│   ├── judge.py                    # LLM-as-judge logic
│   ├── models.py                   # Data models (Pydantic)
│   ├── prompts.py                  # Prompt utilities
│   ├── router.py                   # Model routing logic
│   └── storage.py                  # Database layer (SQLAlchemy)
│
├── api/                            # FastAPI Backend (NEW)
│   ├── __init__.py
│   ├── main.py                     # FastAPI server & endpoints
│   ├── config/
│   │   ├── __init__.py
│   │   ├── plugin_map.py           # Agent → file → method mapping
│   │   └── story_definitions.py    # Story metadata & thresholds
│   └── utils/
│       ├── __init__.py
│       ├── aggregators.py          # Data aggregation functions
│       ├── data_fetcher.py         # Database queries (no Streamlit)
│       ├── formatters.py           # Display formatting utilities
│       └── story_analyzer.py       # Story analysis functions
│
├── frontend/                       # React Frontend (NEW)
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx                # Entry point
│       ├── index.css               # Tailwind styles
│       ├── App.jsx                 # Main app router
│       └── components/
│           └── ObservatoryStories.jsx  # Stories dashboard
│
├── tests/                          # Test suite
│   ├── __init__.py
│   └── diagnose_db.py
│
├── observatory.db                  # Centralized metrics database
├── pyproject.toml
├── requirements.txt
├── README.md
└── .env
```

### ❌ DELETED (Former Streamlit Dashboard)
```
dashboard/                          # DELETED - Migrated to React
├── app.py
├── optimizer_state.py
├── templates/
├── pages/
├── components/
├── utils/
└── .streamlit/
```

---

## ✅ Migration Status

### Phase 1: Foundation ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| FastAPI backend setup | ✅ | `api/main.py` |
| Remove Streamlit dependencies | ✅ | No `@st.cache_*` decorators |
| Migrate `data_fetcher.py` | ✅ | Singleton pattern for Storage |
| Migrate `story_analyzer.py` | ✅ | Updated imports |
| Migrate `aggregators.py` | ✅ | No changes needed |
| Migrate `formatters.py` | ✅ | No changes needed |
| Create `api/config/` | ✅ | plugin_map.py, story_definitions.py |
| Update all import paths | ✅ | `dashboard.utils` → `api.utils` |

### Phase 2: API Endpoints ✅ COMPLETE

| Endpoint | Method | Status |
|----------|--------|--------|
| `/api/health` | GET | ✅ |
| `/api/projects` | GET | ✅ |
| `/api/models` | GET | ✅ |
| `/api/agents` | GET | ✅ |
| `/api/operations` | GET | ✅ |
| `/api/calls` | GET | ✅ |
| `/api/stories` | GET | ✅ |
| `/api/stories/{story_id}` | GET | ✅ |
| `/api/code-location` | GET | ✅ |

### Phase 3: React Stories Dashboard ✅ COMPLETE

| Component | Status | Notes |
|-----------|--------|-------|
| `ObservatoryStories.jsx` | ✅ | Full stories dashboard |
| API integration | ✅ | Configurable `API_BASE_URL` |
| Story navigation (7 stories) | ✅ | Clickable story cards |
| Health summary metrics | ✅ | Issues, passed, total, score |
| Project/time filters | ✅ | Dropdown selectors |
| Charts (Recharts) | ✅ | Per-story visualizations |
| Detail tables | ✅ | Expandable data tables |
| Top offender display | ✅ | Highlighted problem areas |
| Action recommendations | ✅ | Yellow callout boxes |

---

## 🎯 The Vision

The AI Agent Observatory tells **stories** about your AI application's performance, not just displays metrics. Each story represents a specific optimization opportunity, and clicking into a story walks the developer through:

1. **What's happening** (the data)
2. **Why it matters** (the impact)
3. **Where to fix it** (the code location)
4. **How to fix it** (the code change)
5. **Did it work?** (measure the impact)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     📊 DATA STORIES (React Dashboard)               │
│                                                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ 🐌 Story 1  │ │ 💾 Story 2  │ │ 🔀 Story 3  │ │ ❌ Story 4  │   │
│  │ Latency     │ │ Zero Cache  │ │ Model       │ │ Quality     │   │
│  │ Monster     │ │ Hits        │ │ Routing     │ │ Issues      │   │
│  │             │ │             │ │             │ │             │   │
│  │ 16s avg     │ │ 110 misses  │ │ 5 misroutes │ │ 2% errors   │   │
│  │ [View →]    │ │ [View →]    │ │ [View →]    │ │ [View →]    │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
│                                                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                   │
│  │ ⚖️ Story 5  │ │ 📝 Story 6  │ │ 💰 Story 7  │                   │
│  │ Token       │ │ System      │ │ Cost        │                   │
│  │ Imbalance   │ │ Prompt Waste│ │ Deep Dive   │                   │
│  └─────────────┘ └─────────────┘ └─────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Remaining Implementation To-Do List

### Phase 4: Additional React Pages 🔲 NOT STARTED

#### 4.1 Cache Analyzer Page
- [ ] Create `frontend/src/components/CacheAnalyzer.jsx`
- [ ] Add `/api/cache-analysis` endpoint
- [ ] Show duplicate prompt groups
- [ ] Show cache key suggestions
- [ ] Show code change guidance

#### 4.2 Model Router Page
- [ ] Create `frontend/src/components/ModelRouter.jsx`
- [ ] Add `/api/routing-analysis` endpoint
- [ ] Show complexity vs model mapping
- [ ] Show latency by operation
- [ ] Show routing recommendations

#### 4.3 Prompt Optimizer Page
- [ ] Create `frontend/src/components/PromptOptimizer.jsx`
- [ ] Add `/api/prompt-analysis` endpoint
- [ ] Show token breakdown by component
- [ ] Show compression opportunities
- [ ] Show before/after examples

#### 4.4 Cost Estimator Page
- [ ] Create `frontend/src/components/CostEstimator.jsx`
- [ ] Add `/api/cost-analysis` endpoint
- [ ] Show cost breakdown by operation/model
- [ ] Show cost projections
- [ ] Show savings opportunities

#### 4.5 LLM Judge Page
- [ ] Create `frontend/src/components/LLMJudge.jsx`
- [ ] Add `/api/quality-analysis` endpoint
- [ ] Show quality scores distribution
- [ ] Show error patterns
- [ ] Show hallucination flags

#### 4.6 Optimization Impact Page
- [ ] Create `frontend/src/components/OptimizationImpact.jsx`
- [ ] Add `/api/optimization-comparison` endpoint
- [ ] Show baseline vs optimized metrics
- [ ] Show before/after comparisons
- [ ] Show ROI calculations

### Phase 5: Navigation & Routing 🔲 NOT STARTED

- [ ] Add React Router to `App.jsx`
- [ ] Create navigation sidebar/header
- [ ] Implement story → page drill-down navigation
- [ ] Add breadcrumb component
- [ ] Add "Back to Stories" navigation

### Phase 6: Code Location & Change Guidance 🔲 NOT STARTED

- [ ] Create `CodeLocation.jsx` component
- [ ] Create `CodeDiff.jsx` component (before/after)
- [ ] Populate `api/config/plugin_map.py` with actual mappings
- [ ] Add code snippets to story detail views

### Phase 7: Testing & Polish 🔲 NOT STARTED

- [ ] Test all 7 story flows end-to-end
- [ ] Test with real observatory.db data
- [ ] Add loading states and error handling
- [ ] Add responsive design for mobile
- [ ] Performance optimization

---

## 🚀 Running the Application

### Development Mode

```bash
# Terminal 1: Start FastAPI backend
cd ai-agent-observatory
python -m api.main
# → http://localhost:8000

# Terminal 2: Start React frontend
cd ai-agent-observatory/frontend
npm run dev
# → http://localhost:5173
```

### API Testing

```bash
# Health check
curl http://localhost:8000/api/health

# Get all stories
curl http://localhost:8000/api/stories

# Get specific story detail
curl http://localhost:8000/api/stories/latency

# Get projects
curl http://localhost:8000/api/projects
```

### Environment Configuration

```bash
# frontend/.env (optional)
VITE_API_URL=http://localhost:8000

# Root .env
DATABASE_URL=sqlite:///observatory.db
```

---

## 📊 Story Definitions Reference

| # | Story | Key Metric | Target Page | Red Flag Threshold |
|---|-------|------------|-------------|-------------------|
| 1 | 🐌 Latency Monster | Avg latency (s) | Model Router | > 5s avg |
| 2 | 💾 Zero Cache Hits | Cache miss count | Cache Analyzer | > 50% redundancy |
| 3 | 🔀 Model Routing | Complexity mismatch | Model Router | High complexity + cheap model |
| 4 | ❌ Quality Issues | Error/hallucination rate | LLM Judge | > 3% rate |
| 5 | ⚖️ Token Imbalance | Prompt:Completion ratio | Prompt Optimizer | > 10:1 ratio |
| 6 | 📝 System Prompt Waste | Redundant tokens | Prompt Optimizer | > 30% system tokens |
| 7 | 💰 Cost Deep Dive | Cost concentration | Cost Estimator | Top 3 ops > 70% |

---

## 📁 File Reference

### API Files (Backend)

| File | Purpose | Status |
|------|---------|--------|
| `api/main.py` | FastAPI endpoints | ✅ Complete |
| `api/utils/data_fetcher.py` | Database queries | ✅ Complete |
| `api/utils/story_analyzer.py` | Story analysis | ✅ Complete |
| `api/utils/aggregators.py` | Data aggregation | ✅ Complete |
| `api/utils/formatters.py` | Display formatting | ✅ Complete |
| `api/config/plugin_map.py` | Code location mapping | ✅ Placeholder |
| `api/config/story_definitions.py` | Story metadata | ✅ Complete |

### Frontend Files (React)

| File | Purpose | Status |
|------|---------|--------|
| `frontend/src/App.jsx` | Main app | ✅ Basic |
| `frontend/src/components/ObservatoryStories.jsx` | Stories dashboard | ✅ Complete |
| `frontend/src/components/CacheAnalyzer.jsx` | Cache analysis | 🔲 Not started |
| `frontend/src/components/ModelRouter.jsx` | Routing analysis | 🔲 Not started |
| `frontend/src/components/PromptOptimizer.jsx` | Prompt analysis | 🔲 Not started |
| `frontend/src/components/CostEstimator.jsx` | Cost analysis | 🔲 Not started |
| `frontend/src/components/LLMJudge.jsx` | Quality analysis | 🔲 Not started |
| `frontend/src/components/OptimizationImpact.jsx` | Impact tracking | 🔲 Not started |

---

## ⏱️ Estimated Remaining Effort

| Phase | Effort | Priority |
|-------|--------|----------|
| Phase 4: Additional Pages | 8-12 hours | 🟡 High value |
| Phase 5: Navigation | 2-3 hours | 🟡 High value |
| Phase 6: Code Guidance | 3-4 hours | 🟢 Nice to have |
| Phase 7: Testing & Polish | 3-4 hours | 🔴 Must have |

**Remaining: ~16-23 hours**

---

## ✅ Success Criteria

The implementation is complete when:

1. ✅ **Stories Dashboard** - All 7 stories visible with metrics and red flags
2. 🔲 **Drill-Down Pages** - Each story links to detailed analysis page
3. 🔲 **Code Guidance** - Each page shows file path, method, and code examples
4. 🔲 **Measure Impact** - Optimization Impact page shows before/after comparison
5. ✅ **No Streamlit** - Fully migrated to React + FastAPI

---

*Document created: December 2024*  
*Last updated: December 2024*  
*Project: AI Agent Observatory - Career Copilot*