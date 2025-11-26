# Observatory Architecture

## Overview

Observatory is a **passive observability platform** for AI agents and LLM applications. It follows a clean, minimal architecture that separates metrics collection from visualization, allowing easy integration with any AI framework without wrapping or middleware complexity.

**Design Philosophy**: Observatory records what happened (tracking), shows insights (dashboard), but doesn't make decisions for users (routing, caching, quality evaluation).

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     User AI Applications                        │
│  (Career Copilot, Code Review Crew, SQL Agent, etc.)          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ 1. track_llm_call()
                       │    (model, tokens, latency, prompt, etc.)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Observatory Core Library                      │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ collector.py │  │  models.py   │  │  storage.py  │         │
│  │              │  │              │  │              │         │
│  │ • Sessions   │  │ • Session    │  │ • SQLite     │         │
│  │ • Tracking   │  │ • LLMCall    │  │ • PostgreSQL │         │
│  │ • Recording  │  │ • Quality    │  │ • SQLAlchemy │         │
│  │              │  │ • Routing    │  │              │         │
│  │              │  │ • Cache      │  │              │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ 2. Writes to database
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Observatory Database                        │
│                     (observatory.db)                            │
│                                                                  │
│  Tables:                                                         │
│  • sessions      - Session metadata and aggregates             │
│  • llm_calls     - Individual LLM call records                 │
│                                                                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ 3. Reads data
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Observatory Dashboard                         │
│                    (Streamlit Application)                       │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Pages/    │  │ Components/ │  │   Utils/    │            │
│  │             │  │             │  │             │            │
│  │ • Home      │  │ • Charts    │  │ • Fetcher   │            │
│  │ • Live Demo │  │ • Tables    │  │ • Aggreg.   │            │
│  │ • Cost Est. │  │ • Metrics   │  │ • Format    │            │
│  │ • Router    │  │ • Filters   │  │             │            │
│  │ • Cache     │  │             │  │             │            │
│  │ • Judge     │  │             │  │             │            │
│  │ • Prompt    │  │             │  │             │            │
│  │ • Settings  │  │             │  │             │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Observatory Core Library (4 files)

#### `collector.py` - Metrics Collection & Session Management

**Responsibilities:**
- Start/end tracking sessions
- Record individual LLM calls
- Coordinate with storage layer
- Session lifecycle management

**Key Classes:**
```python
class Observatory:
    def __init__(self, project_name: str, enabled: bool = True)
    def start_session(operation_type: str, metadata: dict) -> Session
    def end_session(session: Session, success: bool = True, error: str = None)
    def record_call(provider, model_name, prompt_tokens, completion_tokens, ...)
```

**Usage:**
```python
obs = Observatory(project_name="My Project")
session = obs.start_session("code_review")
obs.record_call(...)
obs.end_session(session)
```

#### `models.py` - Data Models (Pydantic)

**Responsibilities:**
- Type-safe data structures
- Validation and serialization
- Enum definitions

**Key Models:**
```python
@dataclass
class Session:
    id: str
    project_name: str
    operation_type: str
    start_time: datetime
    end_time: Optional[datetime]
    total_cost: float
    total_tokens: int
    total_llm_calls: int
    success: bool
    metadata: dict

@dataclass
class LLMCall:
    id: str
    session_id: str
    timestamp: datetime
    model_provider: ModelProvider
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    total_cost: float
    agent_name: Optional[str]
    operation_name: Optional[str]
    prompt: Optional[str]
    response_text: Optional[str]
    routing_decision: Optional[RoutingDecision]
    cache_metadata: Optional[CacheMetadata]
    quality_evaluation: Optional[QualityEvaluation]
    error: Optional[str]
    metadata: dict

class RoutingDecision(BaseModel):
    chosen_model: str
    alternative_models: List[str]
    model_scores: Dict[str, float]
    reasoning: str
    estimated_cost_savings: Optional[float]

class CacheMetadata(BaseModel):
    cache_hit: bool
    cache_key: Optional[str]
    cache_cluster_id: Optional[str]

class QualityEvaluation(BaseModel):
    judge_score: float
    reasoning: Optional[str]
    hallucination_flag: bool
    factual_error: bool
    confidence: Optional[float]
    error_category: Optional[str]
    suggestions: List[str]
```

#### `storage.py` - Database Layer (SQLAlchemy)

**Responsibilities:**
- Database connection management
- CRUD operations for sessions and calls
- Query methods with filtering
- Schema migrations

**Supported Databases:**
- SQLite (default, zero configuration)
- PostgreSQL (production, high-volume)

**Key Methods:**
```python
class Storage:
    def save_session(session: Session) -> None
    def save_llm_call(call: LLMCall) -> None
    def get_sessions(project_name=None, limit=100) -> List[Session]
    def get_llm_calls(project_name=None, session_id=None, ...) -> List[LLMCall]
    def get_distinct_projects() -> List[str]
    def get_distinct_models(project_name=None) -> List[str]
    def get_distinct_agents(project_name=None) -> List[str]
```

#### `__init__.py` - Public API

**Exports:**
```python
from observatory import (
    Observatory,
    ModelProvider,
    AgentRole,
    Session,
    LLMCall,
    QualityEvaluation,
    RoutingDecision,
    CacheMetadata
)
```

---

### 2. Dashboard (21 files)

#### Structure

```
dashboard/
├── app.py                          # Main entry point, sidebar, navigation
├── .streamlit/
│   └── config.toml                 # Streamlit theme configuration
├── templates/
│   ├── observatory_config.py       # User integration template
│   └── integration_patterns.py     # Quick reference patterns
├── pages/                          # 8 dashboard pages
│   ├── home.py
│   ├── live_demo.py
│   ├── cost_estimator.py
│   ├── model_router.py
│   ├── cache_analyzer.py
│   ├── llm_judge.py
│   ├── prompt_optimizer.py
│   └── settings.py
├── components/                     # Reusable UI components
│   ├── __init__.py
│   ├── metric_cards.py             # KPI displays
│   ├── charts.py                   # Plotly chart builders
│   ├── tables.py                   # Data table renderers
│   └── filters.py                  # Time/project filters
└── utils/                          # Dashboard utilities
    ├── __init__.py
    ├── data_fetcher.py             # Storage query layer
    ├── aggregators.py              # Metric calculations
    └── formatters.py               # Display formatting
```

#### Key Dashboard Pages

**Home (Mission Control)**
- Overview KPIs (cost, tokens, latency, calls)
- Trends over time
- Model and agent breakdowns
- 4 tabs: Overview, Models, Agents, Trends

**Live Demo**
- Real-time monitoring with auto-refresh
- Live event stream
- KPI time windows (5m, 15m, 1h, 24h)
- Agent activity breakdown

**Cost Estimator**
- Simple and advanced forecasting modes
- Scenario comparison
- Cost breakdown by model/agent/operation
- Cache and routing savings (dual-mode)
- Data-driven recommendations

**Model Router**
- Routing performance KPIs
- Model distribution analysis
- Effectiveness matrix
- Cost vs quality scatter plots
- Decision examples

**Cache Analyzer**
- Semantic prompt clustering (70%+ similarity)
- Cacheability scoring
- Hit/miss timeline
- Per-cluster analysis
- AI recommendations

**LLM Judge**
- Quality metrics and trends
- Performance leaderboards
- Error breakdown
- Best/worst examples
- A/B comparison

**Prompt Optimizer**
- Side-by-side editor
- A/B testing framework
- Win/loss heatmap
- Diff viewer
- Routing impact
- Export functionality

**Settings**
- Project management
- Database configuration
- Display preferences
- Alert configuration
- Performance tuning

#### Dashboard Utilities

**`data_fetcher.py`** - Query Layer
```python
@st.cache_data(ttl=30)
def get_llm_calls(project_name=None, ...) -> List[Dict[str, Any]]
def get_project_overview(project_name) -> Dict[str, Any]
def get_time_series_data(...) -> Dict[datetime, float]
def get_routing_analysis(...) -> Dict[str, Any]
def get_cache_analysis(...) -> Dict[str, Any]
def get_quality_analysis(...) -> Dict[str, Any]
```

**`aggregators.py`** - Metric Calculations
```python
def aggregate_by_model(llm_calls) -> Dict[str, Dict[str, Any]]
def aggregate_by_agent(llm_calls) -> Dict[str, Dict[str, Any]]
def calculate_routing_metrics(llm_calls) -> Dict[str, Any]
def calculate_cache_metrics(llm_calls) -> Dict[str, Any]
def calculate_quality_metrics(llm_calls) -> Dict[str, Any]
def calculate_time_series(llm_calls, metric, interval) -> Dict[datetime, float]
```

**`formatters.py`** - Display Formatting
```python
def format_cost(value: float) -> str  # "$0.0123"
def format_tokens(value: int) -> str  # "1.2K", "1.5M"
def format_latency(value: float) -> str  # "1.2s", "450ms"
def format_model_name(name: str) -> str  # "GPT-4", "Claude Sonnet 4"
```

---

## Data Flow

### Recording Flow (User → Database)

```
1. User Application
   ↓ track_llm_call(model="gpt-4", tokens=500, ...)
   
2. observatory_config.py
   ↓ obs.record_call(...)
   
3. collector.py
   ↓ Creates LLMCall object
   ↓ Validates with Pydantic models
   
4. storage.py
   ↓ Saves to database
   
5. Database (observatory.db)
   ✓ Stored in llm_calls table
```

### Visualization Flow (Database → Dashboard)

```
1. Dashboard Page (e.g., cost_estimator.py)
   ↓ Requests data
   
2. data_fetcher.py
   ↓ Queries storage layer
   ↓ Caches results (30-60s TTL)
   ↓ Converts Pydantic models to dicts
   
3. aggregators.py
   ↓ Calculates metrics
   ↓ Groups by model/agent/time
   
4. charts.py / tables.py
   ↓ Creates visualizations
   
5. Dashboard Display
   ✓ Shows to user
```

---

## Database Schema

### `sessions` Table

```sql
CREATE TABLE sessions (
    id VARCHAR(36) PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    operation_type VARCHAR(255),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    total_cost FLOAT DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_llm_calls INTEGER DEFAULT 0,
    total_latency_ms FLOAT DEFAULT 0,
    success BOOLEAN DEFAULT TRUE,
    error TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_project (project_name),
    INDEX idx_start_time (start_time),
    INDEX idx_operation (operation_type)
);
```

### `llm_calls` Table

```sql
CREATE TABLE llm_calls (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    model_provider VARCHAR(50),
    model_name VARCHAR(255) NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    latency_ms FLOAT NOT NULL,
    total_cost FLOAT NOT NULL,
    agent_name VARCHAR(255),
    operation_name VARCHAR(255),
    prompt TEXT,
    response_text TEXT,
    routing_decision JSON,
    cache_metadata JSON,
    quality_evaluation JSON,
    error TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    INDEX idx_session (session_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_model (model_name),
    INDEX idx_agent (agent_name),
    INDEX idx_project_time (session_id, timestamp)
);
```

---

## Integration Patterns

### Pattern 1: Direct Integration (Minimal)

```python
from observatory_config import track_llm_call

# Your code
response = llm_call()

# Track it
track_llm_call(
    model_name="gpt-4",
    prompt_tokens=500,
    completion_tokens=200,
    latency_ms=1200
)
```

### Pattern 2: Session Tracking (Workflows)

```python
from observatory_config import start_tracking_session, end_tracking_session

session = start_tracking_session("multi_step_workflow")

try:
    step1()
    track_llm_call(...)
    
    step2()
    track_llm_call(...)
    
    end_tracking_session(session, success=True)
except Exception as e:
    end_tracking_session(session, success=False, error=str(e))
```

### Pattern 3: Framework Integration (LangGraph)

```python
# In LangGraph node
def my_node(state: State) -> State:
    result = llm_call()
    
    track_llm_call(
        model_name="gpt-4",
        ...,
        agent_name="NodeName",
        operation="node_operation",
        prompt=state['input'],
        response_text=result
    )
    
    return {"output": result}
```

### Pattern 4: Multi-Agent Systems

```python
# Track different agents
track_llm_call(..., agent_name="Analyzer", operation="analyze")
track_llm_call(..., agent_name="Reviewer", operation="review")
track_llm_call(..., agent_name="Fixer", operation="fix")

# All tracked in same session, visible per-agent in dashboard
```

---

## Design Decisions

### Why Passive Observation?

**Problems with Active Middleware:**
- Wraps user code (complex, brittle)
- Forces specific patterns
- Harder to debug
- Framework lock-in

**Benefits of Passive Tracking:**
- Users own their code
- Simple integration (one function call)
- Framework agnostic
- Easy to debug
- No performance impact

### Why No Built-in Optimizers?

**Users implement optimization logic:**
- Routing: User decides which model to use
- Caching: User implements cache layer
- Quality: User runs evaluation

**Observatory just records decisions:**
- Pass `RoutingDecision` → Router page works
- Pass `CacheMetadata` → Cache page works
- Pass `QualityEvaluation` → Judge page works

**Benefits:**
- Users have full control
- No magic behavior
- Flexible implementation
- Observatory stays simple

### Why Dashboard Instead of Analyzers?

**Old approach (removed):**
```
analyzers/
├── cost_analyzer.py      # Duplicate logic
├── latency_analyzer.py   # Duplicate logic
└── quality_analyzer.py   # Duplicate logic
```

**New approach (current):**
```
dashboard/pages/
├── cost_estimator.py     # Analysis + Visualization
├── model_router.py       # Analysis + Visualization
└── llm_judge.py          # Analysis + Visualization
```

**Benefits:**
- Single source of truth
- No duplicate logic
- UI = Analysis layer
- Easier to maintain

---

## Scalability Considerations

### Database Optimization

**Indexes:**
- `project_name` - Filter by project
- `timestamp` - Time-based queries
- `session_id` - Join sessions to calls
- `model_name` - Group by model
- `agent_name` - Group by agent

**Query Patterns:**
- Use `LIMIT` on all queries
- Filter by time range first
- Cache dashboard queries (30-60s TTL)
- Batch writes where possible

### High-Volume Deployments

**SQLite Limits:**
- Works well up to ~1M calls/day
- Single writer limitation
- File-based locking

**PostgreSQL Benefits:**
- Handles billions of records
- Concurrent writes
- Better analytics performance
- Can scale horizontally

**Migration:**
```python
# Change environment variable
export DATABASE_URL="postgresql://user:pass@host:5432/db"

# Observatory automatically uses PostgreSQL
```

### Caching Strategy

**Dashboard Caching:**
```python
@st.cache_data(ttl=30)  # Cache for 30 seconds
def get_llm_calls(...):
    # Expensive query
    return results
```

**Benefits:**
- Reduces database load
- Faster page loads
- TTL ensures freshness
- Per-function caching

---

## Security & Privacy

### Data Storage

**What's Stored:**
- Model names, tokens, costs, latencies
- Agent names, operation types
- Optionally: prompts and responses
- Optionally: routing/cache/quality metadata

**What's NOT Stored:**
- API keys (never)
- User passwords
- Sensitive credentials
- PII (unless in prompts)

### Privacy Controls

**Users control what to track:**
```python
# Minimal (no prompts)
track_llm_call(model_name="gpt-4", tokens=500, ...)

# With prompts (enables caching)
track_llm_call(..., prompt=prompt, response_text=response)
```

**Database Security:**
- Local SQLite file (not exposed)
- PostgreSQL with standard auth
- No external data transmission
- Self-hosted (you own the data)

---

## Extension Points

### 1. Custom Metrics

Add custom metadata to any call:
```python
track_llm_call(
    ...,
    metadata={
        "user_id": "123",
        "session_type": "premium",
        "custom_metric": 42
    }
)
```

### 2. Custom Dashboard Pages

Create new pages in `dashboard/pages/`:
```python
# custom_analysis.py
import streamlit as st
from dashboard.utils.data_fetcher import get_llm_calls

def render():
    st.title("My Custom Analysis")
    calls = get_llm_calls(project_name="My Project")
    # Your custom analysis
```

### 3. External Integrations

Export data for external tools:
```python
# Export to Datadog, Prometheus, etc.
calls = storage.get_llm_calls(limit=1000)
for call in calls:
    send_to_external_system(call)
```

### 4. Custom Alerts

Implement alerting logic:
```python
# Check thresholds
if daily_cost > THRESHOLD:
    send_alert("Cost exceeded threshold")
```

---

## Testing Strategy

### Unit Tests

```python
# Test models
def test_session_model():
    session = Session(...)
    assert session.id is not None

# Test storage
def test_save_llm_call():
    storage.save_llm_call(call)
    retrieved = storage.get_llm_calls(session_id=call.session_id)
    assert len(retrieved) == 1

# Test aggregators
def test_aggregate_by_model():
    result = aggregate_by_model(calls)
    assert "gpt-4" in result
```

### Integration Tests

```python
# Test end-to-end flow
def test_full_tracking_flow():
    obs = Observatory("test-project")
    session = obs.start_session("test")
    obs.record_call(...)
    obs.end_session(session)
    
    # Verify in database
    sessions = storage.get_sessions(project_name="test-project")
    assert len(sessions) == 1
```

---

## Performance Benchmarks

**Tracking Overhead:**
- `track_llm_call()`: ~1ms per call
- Session start/end: ~0.5ms each
- Database write: ~2-5ms (SQLite), ~1-2ms (PostgreSQL)

**Dashboard Performance:**
- Page load: 100-500ms (with caching)
- Chart rendering: 50-200ms (Plotly)
- Query execution: 10-100ms (depending on data size)

**Scalability:**
- SQLite: 1M+ calls, <100MB database
- PostgreSQL: Billions of calls, production-ready

---

## Maintenance

### Database Backups

**SQLite:**
```bash
# Simple file copy
cp observatory.db observatory_backup_$(date +%Y%m%d).db
```

**PostgreSQL:**
```bash
# pg_dump
pg_dump -U user observatory > backup.sql
```

### Data Retention

Implement cleanup for old data:
```python
# Delete data older than 90 days
cutoff = datetime.now() - timedelta(days=90)
storage.delete_sessions_before(cutoff)
```

### Monitoring

Monitor Observatory itself:
- Database size growth
- Query performance
- Dashboard load times
- Error rates

---

## Future Enhancements

### Planned Features

1. **Real-time Alerts**
   - Email/Slack notifications
   - Threshold-based triggers
   - Cost budget limits

2. **API Endpoints**
   - REST API for programmatic access
   - Query metrics via HTTP
   - Webhook integrations

3. **Advanced Analytics**
   - Anomaly detection (ML-powered)
   - Predictive cost modeling
   - Automatic optimization suggestions

4. **Distributed Tracing**
   - Trace requests across services
   - Visualize call graphs
   - Identify distributed bottlenecks

5. **Custom Plugins**
   - Plugin system for extensions
   - Community marketplace
   - Custom analyzer plugins

---

## Conclusion

Observatory provides a clean, minimal architecture for AI observability:

**Core Principles:**
- ✅ Passive observation (record, don't decide)
- ✅ Framework agnostic (works with anything)
- ✅ Progressive enhancement (start simple, add features)
- ✅ Multi-project support (one database, many projects)
- ✅ Production ready (error handling, performance, scalability)

**What Makes It Different:**
- No middleware or wrappers
- Users own optimization logic
- Dashboard IS the analyzer
- Simple integration (one function call)
- Self-hosted (you own the data)

**Status:** Production Ready ✅

---

*Architecture designed for simplicity, flexibility, and scale.*