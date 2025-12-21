api/
├── __init__.py
├── __pycache__/
├── dependencies.py
├── main.py
├── config/
│   ├── __init__.py
│   ├── __pycache__/
│   ├── plugin_map.py
│   ├── settings.py
│   └── story_definitions.py
├── models/
│   ├── __init__.py
│   ├── __pycache__/
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
│   ├── __pycache__/
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
│       ├── __pycache__/
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
│   ├── __pycache__/
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
    ├── __pycache__/
    ├── aggregators.py
    ├── data_fetcher.py
    ├── exceptions.py
    └── formatters.py


src/
├── App.jsx
├── main.jsx
├── assets/
│   ├── fonts/
│   └── images/
│       ├── empty-state.svg
│       └── logo.svg
├── components/
│   ├── common/
│   │   ├── KPICard.jsx
│   │   ├── Loading.jsx
│   │   └── StatusBadge.jsx
│   ├── layout/
│   │   ├── Footer.jsx
│   │   ├── Header.jsx
│   │   └── Sidebar.jsx
│   ├── stories/
│   │   ├── Layer2Table/
│   │   │   ├── AddColumnDropdown.jsx
│   │   │   ├── ColumnHeader.jsx
│   │   │   ├── exports.js
│   │   │   ├── FilterBar.jsx
│   │   │   ├── index.jsx
│   │   │   ├── QuickFilters.jsx
│   │   │   └── TableRow.jsx
│   │   ├── Layer3/
│   │   │   ├── AIAnalysisPanel.jsx
│   │   │   ├── AttributePanel.jsx
│   │   │   ├── DiagnosePanel.jsx
│   │   │   ├── FixPanel.jsx
│   │   │   ├── index.jsx
│   │   │   ├── RawPanel.jsx
│   │   │   ├── SimilarPanel.jsx
│   │   │   └── shared/
│   │   │       ├── index.js
│   │   │       ├── KPICard.jsx
│   │   │       ├── PromptBreakdownBar.jsx
│   │   │       ├── SeverityBadge.jsx
│   │   │       └── TimeBreakdownBar.jsx
│   │   ├── LLMCallDetail.jsx
│   │   ├── OperationTable.jsx
│   │   ├── StoryCard.jsx
│   │   └── StoryNavTabs.jsx
│   └── ui/
│       ├── badge.jsx
│       ├── button.jsx
│       ├── card.jsx
│       └── table.jsx
├── config/
│   ├── columnDefinitions.js
│   ├── layer3/
│   │   ├── cache.js
│   │   ├── cost.js
│   │   ├── latency.js
│   │   ├── quality.js
│   │   └── token.js
│   ├── storyDefinitions.js
│   └── theme.js
├── constants/
│   ├── apiEndpoints.js
│   └── storyDefinitions.js
├── hooks/
│   ├── useCalls.js
│   ├── useDebounce.js
│   └── useStories.js
├── lib/
│   └── utils.js
├── pages/
│   ├── Dashboard.jsx
│   ├── OptimizationQueue.jsx
│   ├── stories/
│   │   ├── cache/
│   │   │   ├── index.jsx
│   │   │   ├── OperationDetail.jsx
│   │   │   └── PatternDetail.jsx
│   │   ├── CallDetail.jsx
│   │   ├── cost/
│   │   │   ├── CallDetail.jsx
│   │   │   ├── index.jsx
│   │   │   └── OperationDetail.jsx
│   │   ├── latency/
│   │   │   ├── CallDetail.jsx
│   │   │   ├── index.jsx
│   │   │   └── OperationDetail.jsx
│   │   ├── optimization/
│   │   │   ├── ComparisonDetail.jsx
│   │   │   └── index.jsx
│   │   ├── prompt/
│   │   │   ├── index.jsx
│   │   │   └── OperationDetail.jsx
│   │   ├── quality/
│   │   │   ├── CallDetail.jsx
│   │   │   ├── index.jsx
│   │   │   └── OperationDetail.jsx
│   │   ├── routing/
│   │   │   ├── index.jsx
│   │   │   └── OperationDetail.jsx
│   │   └── token/
│   │       ├── CallDetail.jsx
│   │       ├── index.jsx
│   │       └── OperationDetail.jsx
├── services/
│   └── api.js
├── styles/
│   └── index.css
└── utils/
    ├── formatters.js
    ├── helpers.js
    └── validators.js


observatory/
├── __init__.py
├── __pycache__/
├── cache.py
├── collector.py
├── judge.py
├── models.py
├── prompts.py
├── router.py
└── storage.py