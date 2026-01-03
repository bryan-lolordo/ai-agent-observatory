# Backend File Structure

```
api/
├── __init__.py
├── dependencies.py
├── main.py
├── config/
│   ├── __init__.py
│   ├── plugin_map.py
│   ├── settings.py
│   └── story_definitions.py
├── models/
│   ├── __init__.py
│   ├── alerts.py
│   ├── analytics.py
│   ├── base.py
│   ├── batch.py
│   ├── code_location.py
│   ├── conversation.py
│   ├── dashboard.py
│   ├── experiment.py
│   ├── filters.py
│   ├── llm_call.py
│   ├── metadata.py
│   ├── optimization.py
│   ├── responses.py
│   ├── user_preferences.py
│   └── webhooks.py
├── routers/
│   ├── __init__.py
│   ├── alerts.py
│   ├── analysis.py
│   ├── analytics.py
│   ├── calls.py
│   ├── experiments.py
│   ├── metadata.py
│   ├── optimizations.py
│   ├── optimization_queue.py
│   ├── webhooks.py
│   └── stories/
│       ├── __init__.py
│       ├── _helpers.py
│       ├── cache.py
│       ├── cost.py
│       ├── latency.py
│       ├── optimization.py
│       ├── prompt.py
│       ├── quality.py
│       ├── routing.py
│       └── token.py
├── services/
│   ├── __init__.py
│   ├── alert_service.py
│   ├── analytics_service.py
│   ├── batch_service.py
│   ├── cache_service.py
│   ├── cost_service.py
│   ├── dashboard_service.py
│   ├── experiment_service.py
│   ├── fix_analysis_service.py
│   ├── latency_service.py
│   ├── llm_call_service.py
│   ├── optimization_queue_service.py
│   ├── optimization_service.py
│   ├── prompt_service.py
│   ├── quality_service.py
│   ├── routing_service.py
│   ├── token_service.py
│   └── webhook_service.py
└── utils/
    ├── __init__.py
    ├── aggregators.py
    ├── data_fetcher.py
    ├── exceptions.py
    └── formatters.py

observatory/
├── __init__.py
├── cache.py
├── collector.py
├── judge.py
├── models.py
├── prompts.py
├── router.py
├── semantic_cache.py
└── storage.py
```
