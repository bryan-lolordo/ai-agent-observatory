# API Reference

Observatory exposes a REST API for the dashboard and programmatic access.

**Base URL:** `http://localhost:8000`

---

## Metadata Endpoints

### List Projects
```
GET /api/projects
```
Returns all available project names.

### List Models
```
GET /api/models?project={project}
```
Returns all models used, optionally filtered by project.

### List Agents
```
GET /api/agents?project={project}
```
Returns all agent names.

### List Operations
```
GET /api/operations?project={project}
```
Returns all operation names.

---

## Call Endpoints

### List Calls
```
GET /api/calls?days=7&operation={op}&agent={agent}&limit=500
```
Returns LLM calls with optional filters.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `days` | int | 7 | Time range (1-90) |
| `operation` | string | - | Filter by operation |
| `agent` | string | - | Filter by agent |
| `call_type` | string | - | Filter: llm, api, database, tool |
| `limit` | int | 500 | Max results (1-1000) |

### Get Call Detail
```
GET /api/calls/{call_id}
```
Returns full details for a specific call (Layer 3 view).

---

## Story Endpoints

All story endpoints follow the same pattern:

| Layer | Endpoint | Description |
|-------|----------|-------------|
| Layer 1 | `GET /api/stories/{story}` | Summary KPIs + operations table |
| Layer 2 | `GET /api/stories/{story}/operations/{agent}/{operation}` | Operation detail |
| Layer 3 | `GET /api/calls/{call_id}` | Individual call detail |

### Available Stories

| Story | Endpoint | Description |
|-------|----------|-------------|
| Cost | `/api/stories/cost` | Cost analysis and breakdown |
| Latency | `/api/stories/latency` | Performance analysis |
| Token | `/api/stories/token` | Token efficiency |
| Quality | `/api/stories/quality` | Quality scores and errors |
| Prompt | `/api/stories/prompt` | Prompt composition analysis |
| Cache | `/api/stories/cache` | Caching opportunities |
| Routing | `/api/stories/routing` | Model routing analysis |

### Common Parameters

All story endpoints accept:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `project` | string | - | Filter by project |
| `days` | int | 7 | Time range (1-90) |
| `limit` | int | 2000 | Max calls to analyze |

### Example: Cost Story

**Layer 1 - Summary:**
```
GET /api/stories/cost?project=MyApp&days=7
```

Response:
```json
{
  "kpis": {
    "total_cost": 12.45,
    "avg_cost_per_call": 0.023,
    "top3_concentration": 0.67,
    "potential_savings": 3.20
  },
  "operations": [
    {
      "agent": "Analyzer",
      "operation": "deep_analyze",
      "call_count": 150,
      "total_cost": 4.56,
      "avg_cost": 0.03
    }
  ],
  "chart_data": {...}
}
```

**Layer 2 - Operation Detail:**
```
GET /api/stories/cost/operations/Analyzer/deep_analyze?days=7
```

Response:
```json
{
  "status": "high_cost",
  "total_cost": 4.56,
  "prompt_cost": 3.80,
  "completion_cost": 0.76,
  "cost_drivers": ["Large system prompt", "High token count"],
  "savings_opportunities": ["Compress system prompt", "Enable caching"],
  "calls": [...]
}
```

---

## Optimization Queue

### Get Opportunities
```
GET /api/optimization/opportunities?project={project}&days=7&story={story}
```

Returns prioritized optimization opportunities across all stories.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `project` | string | - | Filter by project |
| `days` | int | 7 | Time range |
| `story` | string | - | Filter: latency, cache, cost, quality, routing |
| `limit` | int | 100 | Max opportunities |

**Response:**
```json
{
  "opportunities": [
    {
      "id": "latency-no-max-Analyzer.deep_analyze",
      "storyId": "latency",
      "storyIcon": "🌐",
      "agent": "Analyzer",
      "operation": "deep_analyze",
      "issue": "No max_tokens set (1,200 avg tokens)",
      "impact": "$0.34",
      "impactValue": 0.34,
      "effort": "Low",
      "callCount": 47,
      "callId": "abc123..."
    }
  ],
  "summary": {
    "total": 23,
    "totalSavings": 4.56,
    "quickWins": 15,
    "byStory": {
      "latency": 10,
      "cache": 8,
      "cost": 5
    }
  }
}
```

---

## Interactive Docs

FastAPI provides interactive documentation:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
