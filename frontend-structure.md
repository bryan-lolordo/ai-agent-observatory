# Frontend Source Structure

```
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
│   │   ├── ScrollToTop.jsx
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
│   │   │   ├── TracePanel.jsx
│   │   │   └── shared/
│   │   │       ├── ChatHistoryBreakdown.jsx
│   │   │       ├── ComparisonBenchmarks.jsx
│   │   │       ├── index.js
│   │   │       ├── KPICard.jsx
│   │   │       ├── PromptBreakdownBar.jsx
│   │   │       ├── RootCausesTable.jsx
│   │   │       ├── SeverityBadge.jsx
│   │   │       ├── TimeBreakdownBar.jsx
│   │   │       └── TraceTree.jsx
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
│   │   ├── prompt.js
│   │   ├── quality.js
│   │   ├── routing.js
│   │   └── token.js
│   ├── storyDefinitions.js
│   └── theme.js
├── constants/
│   ├── apiEndpoints.js
│   └── storyDefinitions.js
├── context/
│   └── TimeRangeContext.jsx
├── hooks/
│   ├── useCalls.js
│   ├── useDebounce.js
│   └── useStories.js
├── lib/
│   └── utils.js
├── pages/
│   ├── Dashboard.jsx
│   ├── OptimizationQueue.jsx
│   └── stories/
│       ├── cache/
│       │   ├── index.jsx
│       │   ├── OperationDetail.jsx
│       │   └── PatternDetail.jsx
│       ├── cost/
│       │   ├── CallDetail.jsx
│       │   ├── index.jsx
│       │   └── OperationDetail.jsx
│       ├── latency/
│       │   ├── CallDetail.jsx
│       │   ├── index.jsx
│       │   └── OperationDetail.jsx
│       ├── optimization/
│       │   ├── ComparisonDetail.jsx
│       │   └── index.jsx
│       ├── prompt/
│       │   ├── CallDetail.jsx
│       │   ├── index.jsx
│       │   └── OperationDetail.jsx
│       ├── quality/
│       │   ├── CallDetail.jsx
│       │   ├── index.jsx
│       │   └── OperationDetail.jsx
│       ├── routing/
│       │   ├── CallDetail.jsx
│       │   ├── index.jsx
│       │   └── OperationDetail.jsx
│       └── token/
│           ├── CallDetail.jsx
│           ├── index.jsx
│           └── OperationDetail.jsx
├── services/
│   └── api.js
├── styles/
│   └── index.css
└── utils/
    ├── formatters.js
    ├── helpers.js
    └── validators.js
```
