# Architecture

## Overview

Observatory is designed as a pluggable monitoring system for AI agents. It follows a modular architecture that separates concerns and allows easy integration with any AI framework.

## Core Components

### 1. Collector (`collector.py`)

The main entry point for metrics collection. Responsibilities:
- Session management (start, end, track)
- Recording LLM calls
- Coordinating analyzers
- Generating reports

```python
collector = MetricsCollector(project_name="my-project")
session = collector.start_session()
collector.record_llm_call(...)
report = collector.get_report(session)
```

### 2. Storage (`storage.py`)

Database abstraction layer using SQLAlchemy. Supports:
- PostgreSQL for production
- SQLite for development

Tables:
- `sessions` - Session metadata and aggregates
- `llm_calls` - Individual LLM call records

### 3. Models (`models.py`)

Pydantic models for type safety and validation:
- `Session` - Represents a monitoring session
- `LLMCall` - Individual LLM call metrics
- `SessionReport` - Complete analysis report
- Breakdown models for cost, latency, tokens, quality

### 4. Analyzers

Specialized analyzers for different metrics:

#### Cost Analyzer (`analyzers/cost_analyzer.py`)
- Calculates costs based on model pricing
- Breaks down by model, provider, agent, operation
- Maintains pricing tables for all providers

#### Latency Analyzer (`analyzers/latency_analyzer.py`)
- Computes percentiles (p50, p95, p99)
- Identifies bottlenecks by agent/operation
- Tracks total and average latency

#### Token Analyzer (`analyzers/token_analyzer.py`)
- Tracks prompt vs completion tokens
- Analyzes usage by model and agent
- Identifies token-heavy operations

#### Quality Analyzer (`analyzers/quality_analyzer.py`)
- Calculates success rates
- Tracks error patterns
- Monitors average tokens per call

### 5. Integrations

Framework-specific wrappers that automatically capture metrics:

#### Base Integration (`integrations/base.py`)
- Abstract interface for all integrations
- Handles timing and error tracking
- Standardizes metric recording

#### OpenAI Integration
```python
integration = OpenAIIntegration(collector)
response = integration.wrap_completion(client, model, messages)
```

#### Anthropic Integration
```python
integration = AnthropicIntegration(collector)
response = integration.wrap_message(client, model, messages)
```

### 6. Dashboard

Streamlit-based web dashboard:
- Real-time metrics visualization
- Cost trends over time
- Session history table
- Filterable by project and time range

## Data Flow

```
┌─────────────────┐
│   AI Agent      │
│   Application   │
└────────┬────────┘
         │
         │ 1. Start Session
         ▼
┌─────────────────┐
│   Observatory   │
│   Collector     │
└────────┬────────┘
         │
         │ 2. Record LLM Calls
         ▼
┌─────────────────┐
│    Storage      │
│   (Database)    │
└────────┬────────┘
         │
         │ 3. Load Session Data
         ▼
┌─────────────────┐
│   Analyzers     │
│  (Cost, etc.)   │
└────────┬────────┘
         │
         │ 4. Generate Report
         ▼
┌─────────────────┐
│  Session Report │
│  + Suggestions  │
└─────────────────┘
```

## Integration Patterns

### Pattern 1: Manual Integration

```python
obs = Observatory(project_name="my-project")
session = obs.start_session("operation")

# Your code
result = my_agent.run()

# Record call
obs.record_call(
    provider=ModelProvider.OPENAI,
    model_name="gpt-4",
    prompt_tokens=500,
    completion_tokens=200,
    latency_ms=1500,
)

obs.end_session(session)
```

### Pattern 2: Context Manager

```python
obs = Observatory(project_name="my-project")

with obs.track("operation"):
    # Automatically starts/ends session
    result = my_agent.run()
    obs.record_call(...)
```

### Pattern 3: Framework Integration

```python
obs = Observatory(project_name="my-project")
integration = OpenAIIntegration(obs.collector)

session = obs.start_session()

# Integration handles metrics automatically
response = integration.wrap_completion(
    client=openai_client,
    model="gpt-4",
    messages=[...],
    agent_name="MyAgent",
)

obs.end_session(session)
```

## Optimization Engine (Future)

### Cache Layer
- Detect duplicate calls
- Store responses
- Return cached results

### Model Router
- Analyze task complexity
- Route simple tasks to cheaper models
- Maintain quality thresholds

### Prompt Optimizer
- A/B test prompt variations
- Measure impact on cost/quality
- Auto-select best performers

## Scalability Considerations

### Database
- Index on `session_id`, `timestamp`, `project_name`
- Partition by time for large datasets
- Consider TimescaleDB for time-series data

### Async Support
- Add async versions of all methods
- Use asyncio for parallel operations
- Non-blocking database writes

### Sampling
- For high-volume applications, sample calls
- Configurable sampling rate
- Maintain representative metrics

## Security

- No sensitive data stored by default
- Optional PII scrubbing
- Configurable metadata filtering
- Support for encrypted databases

## Extension Points

1. **Custom Analyzers**: Implement custom analysis logic
2. **Additional Integrations**: Add support for new frameworks
3. **Export Formats**: Add exporters for external tools
4. **Alerting**: Hook into monitoring systems
5. **Custom Storage**: Implement alternative storage backends