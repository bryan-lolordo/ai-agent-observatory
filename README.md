# AI Agent Observatory

A toolkit for monitoring, analyzing, and optimizing AI agent metrics and performance.
# 🔭 AI Agent Observatory

**Monitoring, evaluation, and optimization platform for AI agents**

Observatory helps you understand and optimize your AI applications by providing comprehensive metrics on cost, latency, token usage, and quality.

## Features

- 📊 **Real-time Monitoring**: Track all LLM calls across your AI applications
- 💰 **Cost Analysis**: Understand spending by model, agent, and operation
- ⚡ **Latency Profiling**: Identify bottlenecks and optimize performance
- 🎯 **Quality Metrics**: Monitor success rates and output quality
- 🔧 **Optimization Suggestions**: Get actionable recommendations to reduce costs and improve speed
- 📈 **Interactive Dashboard**: Visualize metrics with Streamlit
- 🔌 **Framework Agnostic**: Works with AutoGen, LangGraph, Semantic Kernel, and more

## Installation

### From source
```bash
git clone https://github.com/yourusername/ai-agent-observatory.git
cd ai-agent-observatory
pip install -e .
```

### As a dependency
```bash
pip install ai-agent-observatory
```

## Quick Start

### Basic Usage

```python
from observatory import Observatory, ModelProvider

# Initialize Observatory
obs = Observatory(
    project_name="my-ai-project",
    enabled=True,
)

# Start a session
session = obs.start_session(operation_type="code_review")

# Record LLM calls
obs.record_call(
    provider=ModelProvider.OPENAI,
    model_name="gpt-4",
    prompt_tokens=500,
    completion_tokens=200,
    latency_ms=1500,
    agent_name="CodeAnalyzer",
    operation="analyze_code",
)

# End session
obs.end_session(session)

# Get report
report = obs.get_report(session)
print(f"Total Cost: ${report.cost_breakdown.total_cost:.4f}")
print(f"Suggestions: {report.optimization_suggestions}")
```

### Context Manager

```python
with obs.track("refactor_code"):
    # Your AI agent code here
    obs.record_call(...)
```

### Integration Example

```python
from observatory import Observatory
from observatory.integrations.base import OpenAIIntegration
from openai import OpenAI

obs = Observatory(project_name="my-project")
client = OpenAI()
integration = OpenAIIntegration(obs.collector)

# Start session
session = obs.start_session("chat")

# Wrapped call automatically tracks metrics
response = integration.wrap_completion(
    client=client,
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}],
    agent_name="ChatBot",
)

obs.end_session(session)
```

## Dashboard

Launch the interactive dashboard:

```bash
streamlit run dashboard/app.py
```

Features:
- Real-time cost tracking
- Latency analysis
- Session history
- Optimization recommendations

## Configuration

### Environment Variables

Create a `.env` file:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/observatory
# Or SQLite: DATABASE_URL=sqlite:///observatory.db

# Enable/disable monitoring
ENABLE_OBSERVATORY=true

# Project name
OBSERVATORY_PROJECT_NAME=my-project
```

### Database Setup

Observatory supports PostgreSQL and SQLite:

```bash
# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/observatory

# SQLite (default)
DATABASE_URL=sqlite:///observatory.db
```

## Architecture

```
observatory/
├── collector.py          # Main metrics collector
├── models.py             # Data models
├── storage.py            # Database layer
├── analyzers/            # Cost, latency, token, quality analyzers
├── integrations/         # Framework integrations (OpenAI, Anthropic, etc.)
└── optimizers/           # Optimization engines
```

## Supported Providers

- ✅ OpenAI (GPT-4, GPT-3.5, embeddings)
- ✅ Anthropic (Claude 3, Claude 4)
- ✅ Azure OpenAI
- 🔄 More coming soon

## Examples

See the `examples/` directory:

- `monitor_basic.py` - Basic monitoring
- `monitor_code_review.py` - Code review crew example
- `compare_frameworks.py` - Compare different frameworks

## Roadmap

- [ ] Caching layer for duplicate calls
- [ ] A/B testing for prompts
- [ ] Model routing optimization
- [ ] Real-time alerting
- [ ] Export to external tools (Prometheus, Datadog)

## Contributing

Contributions welcome! Please open an issue or PR.

## License

MIT License