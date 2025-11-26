# 🔭 AI Agent Observatory

**Production-ready observability platform for AI agents and LLM applications**

Observatory provides comprehensive monitoring, cost tracking, and optimization insights for your AI systems. Track every LLM call, analyze performance patterns, and optimize costs across multiple projects from a single unified dashboard.

---

## ✨ Features

### 📊 **8 Comprehensive Dashboard Pages**
- **Home (Mission Control)**: Overview KPIs, trends, agent/model breakdowns
- **Live Demo**: Real-time monitoring with auto-refresh event streams
- **Cost Estimator**: Forecasting, scenario modeling, optimization recommendations
- **Model Router**: Routing effectiveness analysis and savings tracking
- **Cache Analyzer**: Semantic prompt clustering and cache performance
- **LLM Judge**: Quality evaluation, hallucination detection, performance leaderboards
- **Prompt Optimizer**: A/B testing framework with diff viewer
- **Settings**: Project management, database configuration, preferences

### 💡 **Core Capabilities**
- ✅ **Multi-Project Support**: Track unlimited projects in one centralized database
- ✅ **Real-Time Monitoring**: Live dashboard with configurable auto-refresh
- ✅ **Cost Analysis**: Track spending by model, agent, operation, and project
- ✅ **Performance Profiling**: Latency analysis, bottleneck identification
- ✅ **Quality Tracking**: Success rates, error patterns, hallucination detection
- ✅ **Semantic Caching**: Prompt clustering with similarity detection (70%+ threshold)
- ✅ **Routing Analysis**: Model selection effectiveness and cost savings
- ✅ **Framework Agnostic**: Works with any LLM framework (LangGraph, AutoGen, Semantic Kernel, etc.)

### 🎯 **Production Features**
- Progressive enhancement (works now, better with more data)
- Dual-mode operation (basic → advanced as you add features)
- Export capabilities (CSV, JSON, Excel)
- Project-aware filtering throughout
- Empty state handling with actionable guidance
- Professional Plotly visualizations

---

## 🚀 Installation

### **Global Installation (Recommended)**

Install Observatory once, use in all projects:

```bash
# Navigate to Observatory
cd ai-agent-observatory

# Install globally (outside any virtual environment)
pip install -e .

# Verify installation
python -c "from observatory import Observatory; print('✅ Observatory installed!')"
```

### **Per-Project Installation**

Install in each project's virtual environment:

```bash
# In your project
cd your-project
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install from local path
pip install -e ../ai-agent-observatory
```

---

## 📖 Quick Start

### **Step 1: Copy Config Template**

Copy `observatory_config.py` to your project root:

```bash
cp ai-agent-observatory/dashboard/templates/observatory_config.py your-project/
```

Edit the `PROJECT_NAME`:

```python
PROJECT_NAME = "Your Project Name"  # e.g., "Career Copilot", "SQL Query Agent"
```

### **Step 2: Basic Integration**

Track your LLM calls:

```python
from observatory_config import track_llm_call
import time

# Your LLM call
start = time.time()
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)
latency_ms = (time.time() - start) * 1000

# Track it
track_llm_call(
    model_name="gpt-4",
    prompt_tokens=response.usage.prompt_tokens,
    completion_tokens=response.usage.completion_tokens,
    latency_ms=latency_ms,
    agent_name="Chatbot",      # Optional but recommended
    operation="greeting"        # Optional but recommended
)
```

### **Step 3: View Dashboard**

```bash
cd ai-agent-observatory
streamlit run dashboard/app.py
```

Open http://localhost:8501 to see your metrics!

---

## 🎓 Integration Patterns

### **Pattern 1: Basic Tracking (Minimum)**

Enables: Home page, Cost Estimator basics

```python
track_llm_call(
    model_name="gpt-4",
    prompt_tokens=500,
    completion_tokens=200,
    latency_ms=1200
)
```

### **Pattern 2: With Prompt/Response (Recommended)**

Enables: Cache Analyzer with semantic clustering

```python
track_llm_call(
    model_name="gpt-4",
    prompt_tokens=500,
    completion_tokens=200,
    latency_ms=1200,
    prompt=original_prompt,        # ← Enables cache analysis
    response_text=llm_response      # ← Enables quality evaluation
)
```

### **Pattern 3: Full-Featured (All Dashboard Pages)**

Enables: All 8 pages with complete functionality

```python
from observatory_config import (
    track_llm_call,
    create_routing_decision,
    create_cache_metadata,
    create_quality_evaluation
)

# Your routing logic
routing = create_routing_decision(
    chosen_model="gpt-4",
    alternative_models=["gpt-4o-mini", "claude-sonnet-4"],
    reasoning="Complex task requires premium model"
)

# Your cache check
cache = create_cache_metadata(
    cache_hit=True,
    cache_key="abc123",
    cache_cluster_id="code_analysis"
)

# Your quality evaluation (optional - sample 10% to save cost)
quality = create_quality_evaluation(
    judge_score=8.5,
    reasoning="Good response with minor issues",
    hallucination_flag=False,
    confidence=0.9
)

# Track everything
track_llm_call(
    model_name="gpt-4",
    prompt_tokens=500,
    completion_tokens=200,
    latency_ms=1200,
    prompt=prompt,
    response_text=response,
    routing_decision=routing,       # ← Enables Model Router page
    cache_metadata=cache,           # ← Enables Cache Analyzer page
    quality_evaluation=quality      # ← Enables LLM Judge page
)
```

### **Pattern 4: Session Tracking**

Track multi-step workflows:

```python
from observatory_config import start_tracking_session, end_tracking_session

session = start_tracking_session(
    operation_type="code_review_workflow",
    metadata={"file": "app.py", "user": "bryan"}
)

try:
    # Step 1
    result1 = analyze_code()
    track_llm_call(...)
    
    # Step 2
    result2 = review_code()
    track_llm_call(...)
    
    # Step 3
    result3 = fix_code()
    track_llm_call(...)
    
    end_tracking_session(session, success=True)
    
except Exception as e:
    end_tracking_session(session, success=False, error=str(e))
    raise
```

See `dashboard/templates/integration_patterns.py` for more examples!

---

## 🏗️ Architecture

```
ai-agent-observatory/
│
├── observatory/                    # Core tracking library (4 files)
│   ├── __init__.py                 # Main exports
│   ├── collector.py                # Tracks sessions & LLM calls
│   ├── models.py                   # Data models (Pydantic)
│   └── storage.py                  # Database layer (SQLAlchemy)
│
├── dashboard/                      # Analytics dashboard (21 files)
│   ├── app.py                      # Main entry point
│   │
│   ├── templates/                  # Integration templates
│   │   ├── observatory_config.py   # Full config (copy to projects)
│   │   └── integration_patterns.py # Quick reference patterns
│   │
│   ├── pages/                      # 8 dashboard pages
│   │   ├── home.py
│   │   ├── live_demo.py
│   │   ├── cost_estimator.py
│   │   ├── model_router.py
│   │   ├── cache_analyzer.py
│   │   ├── llm_judge.py
│   │   ├── prompt_optimizer.py
│   │   └── settings.py
│   │
│   ├── components/                 # Reusable UI components
│   │   ├── metric_cards.py
│   │   ├── charts.py
│   │   ├── tables.py
│   │   └── filters.py
│   │
│   └── utils/                      # Dashboard utilities
│       ├── data_fetcher.py         # Query layer
│       ├── aggregators.py          # Metric calculations
│       └── formatters.py           # Display formatting
│
├── observatory.db                  # Centralized metrics database
├── pyproject.toml                  # Package configuration
└── README.md
```

### **Design Philosophy**

**Observatory is a PASSIVE observer:**
- ✅ Tracks what happened (metrics collection)
- ✅ Shows insights (dashboard visualization)
- ❌ Doesn't make decisions for you
- ❌ Doesn't wrap your LLM calls

**Users are ACTIVE decision-makers:**
- You implement routing → pass `RoutingDecision`
- You implement caching → pass `CacheMetadata`
- You implement quality eval → pass `QualityEvaluation`
- Observatory records and visualizes everything

---

## 📊 Dashboard Pages Overview

### **1. Home (Mission Control)**
- Project overview with key metrics
- Cost, latency, token trends
- Model and agent breakdowns
- 4 tabs: Overview, Models, Agents, Trends

### **2. Live Demo**
- Real-time monitoring with auto-refresh (2s, 5s, 10s, 30s, 60s)
- Live event stream
- Agent activity breakdown
- Request timeline visualization

### **3. Cost Estimator**
- Simple and advanced forecasting modes
- Scenario comparison (baseline vs optimized)
- Cost breakdown by model/agent/operation
- Cache and routing savings analysis (dual-mode)
- Data-driven recommendations

### **4. Model Router**
- Routing performance KPIs
- Model distribution analysis
- Routing effectiveness matrix
- Cost vs quality scatter plots
- Decision examples with reasoning
- Savings summary

### **5. Cache Analyzer**
- Semantic prompt clustering (70%+ similarity)
- Cacheability scoring (0-100)
- Hit/miss timeline charts
- Per-cluster drilldown
- AI-generated optimization recommendations
- Adjustable similarity threshold

### **6. LLM Judge**
- Quality metrics KPIs
- Trend charts over time
- Performance leaderboards (model & agent)
- Error category breakdown
- Best vs worst examples
- Detailed evaluation drilldown
- A/B comparison tool

### **7. Prompt Optimizer**
- Side-by-side prompt editor
- A/B test configuration
- Results summary with KPI comparison
- Win/loss heatmap
- Detailed per-query comparison
- Prompt diff viewer with color coding
- Routing impact analysis
- Per-model performance breakdown
- AI-generated optimization insights
- Export functionality (JSON, Python, Text)

### **8. Settings**
- Project management
- Database statistics
- Display preferences
- Alert thresholds
- Performance tuning
- Export/import configuration
- Advanced settings

---

## 🎯 Supported Providers

- ✅ **OpenAI** (GPT-4, GPT-4o, GPT-3.5, o1, embeddings)
- ✅ **Anthropic** (Claude 4, Claude 3.5, Claude 3)
- ✅ **Azure OpenAI** (All models)
- ✅ **AWS Bedrock** (All models)
- ✅ **Google** (Gemini models)
- ✅ **Mistral** (All models)
- ✅ **Any LLM** (provider-agnostic tracking)

---

## 💾 Database

**Default: SQLite** (zero configuration, perfect for development and small-medium deployments)

```python
# Automatic - no setup needed!
# Database stored at: ai-agent-observatory/observatory.db
```

**Production: PostgreSQL** (optional, for high-volume deployments)

```python
# Set environment variable
export DATABASE_URL="postgresql://user:password@localhost:5432/observatory"
```

---

## 📈 What You Get

### **Immediate Value (Day 1)**
- Cost tracking across all LLM calls
- Latency profiling and bottleneck identification
- Token usage analysis
- Project-specific filtering

### **With Prompts/Responses (Day 2)**
- Semantic cache analysis
- Prompt clustering and similarity detection
- Quality evaluation readiness
- Duplicate call detection

### **With Full Features (Day 3+)**
- Complete routing effectiveness analysis
- Cache hit/miss rates and savings
- Quality scores and hallucination detection
- A/B testing capabilities
- Comprehensive optimization recommendations

---

## 🔧 Configuration

### **Environment Variables**

```bash
# Database URL (optional - defaults to SQLite)
DATABASE_URL=sqlite:///observatory.db

# Or PostgreSQL for production
DATABASE_URL=postgresql://user:password@localhost:5432/observatory
```

### **Project Configuration**

In your `observatory_config.py`:

```python
# Basic configuration
PROJECT_NAME = "Your Project Name"

# Database path (automatically configured)
OBSERVATORY_DB_PATH = "../ai-agent-observatory/observatory.db"

# Enable/disable tracking
obs = Observatory(
    project_name=PROJECT_NAME,
    enabled=True  # Set to False to disable
)
```

---

## 🎓 Real-World Examples

### **Example 1: LangGraph Integration**

```python
# In your LangGraph nodes
from observatory_config import track_llm_call

def my_node(state: State) -> State:
    prompt = f"Analyze: {state['input']}"
    
    start = time.time()
    response = llm.invoke(prompt)
    latency_ms = (time.time() - start) * 1000
    
    track_llm_call(
        model_name="gpt-4",
        prompt_tokens=len(prompt) // 4,
        completion_tokens=len(response) // 4,
        latency_ms=latency_ms,
        agent_name="Analyzer",
        operation="analyze",
        prompt=prompt,
        response_text=response
    )
    
    return {"result": response}
```

### **Example 2: AutoGen Integration**

```python
# In your AutoGen agent
from observatory_config import track_llm_call

class MyAgent(ConversableAgent):
    def _generate_reply(self, messages, sender):
        start = time.time()
        reply = super()._generate_reply(messages, sender)
        latency_ms = (time.time() - start) * 1000
        
        track_llm_call(
            model_name=self.llm_config["model"],
            prompt_tokens=self.total_usage["prompt_tokens"],
            completion_tokens=self.total_usage["completion_tokens"],
            latency_ms=latency_ms,
            agent_name=self.name,
            operation="generate_reply"
        )
        
        return reply
```

### **Example 3: Semantic Kernel Integration**

```python
# In your Semantic Kernel functions
from observatory_config import track_llm_call

@kernel_function
def my_function(input: str):
    start = time.time()
    result = kernel.invoke(prompt=input)
    latency_ms = (time.time() - start) * 1000
    
    track_llm_call(
        model_name="gpt-4",
        prompt_tokens=result.usage.prompt_tokens,
        completion_tokens=result.usage.completion_tokens,
        latency_ms=latency_ms,
        agent_name="MyFunction",
        operation="process",
        prompt=input,
        response_text=str(result)
    )
    
    return result
```

---

## 🚀 Performance

- **Minimal Overhead**: ~1ms per track_llm_call()
- **Async Writes**: Non-blocking database operations
- **Smart Caching**: Dashboard queries cached for 30-60 seconds
- **Scalable**: Handles millions of LLM calls
- **Production Ready**: Error handling, retry logic, transaction safety

---

## 📝 Best Practices

### **Cost Optimization**
1. Start with basic tracking
2. Add prompts/responses for cache analysis
3. Implement routing based on dashboard insights
4. Use quality evaluation with sampling (10-20%)
5. Export and analyze trends monthly

### **Quality Tracking**
1. Sample quality evaluations (don't evaluate every call)
2. Focus on high-value or high-cost operations
3. Use LLM Judge for automated evaluation
4. Track hallucinations on critical tasks
5. Monitor trends over time

### **Performance**
1. Use database indexes (automatically created)
2. Archive old data periodically
3. Use PostgreSQL for high-volume (1M+ calls/day)
4. Monitor dashboard load times
5. Adjust cache TTL as needed

---

## 🤝 Contributing

Contributions welcome! This is an active project.

**How to contribute:**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

**Areas where help is appreciated:**
- Additional LLM provider support
- Dashboard UI/UX improvements
- Performance optimizations
- Documentation improvements
- Bug fixes

---

## 📄 License

MIT License - use freely in personal and commercial projects.

---

## 🎯 Roadmap

### **Completed ✅**
- [x] Core tracking library
- [x] Multi-project support
- [x] 8 comprehensive dashboard pages
- [x] Real-time monitoring
- [x] Cost forecasting
- [x] Semantic cache analysis
- [x] Quality evaluation framework
- [x] Model routing analysis
- [x] A/B testing for prompts
- [x] Export capabilities

### **In Progress 🚧**
- [ ] Alert system (email/Slack notifications)
- [ ] API endpoints for programmatic access
- [ ] Batch export for data warehouses
- [ ] Custom analyzer plugins

### **Planned 📋**
- [ ] Distributed tracing support
- [ ] Real-time dashboards (WebSocket updates)
- [ ] ML-powered anomaly detection
- [ ] Cost budgets and limits
- [ ] Integration marketplace

---

## 💬 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/ai-agent-observatory/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/ai-agent-observatory/discussions)
- **Email**: your-email@example.com

---

## 🌟 Showcase Your Project

Built something cool with Observatory? We'd love to feature it!

---

**Made with ❤️ for the AI community**

*Observatory: Because you can't optimize what you don't measure.*