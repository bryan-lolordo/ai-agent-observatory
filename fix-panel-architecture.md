# FixPanel Architecture

## Overview

The FixPanel displays optimization recommendations for LLM calls. It shows rule-based fixes generated from call analysis, plus an AI-powered analysis section.

## Data Flow

```
Story Config (e.g., latency.js)    →    CallDetail Page    →    Layer3Shell    →    FixPanel
         ↓                                    ↓                      ↓               ↓
   get[Story]Fixes(call, factors)      Calls config functions    Passes props    Renders fixes
```

## Step-by-Step Process

### 1. Story Config File

Each story has its own config in `frontend/src/config/layer3/`:

| Story | Config File |
|-------|-------------|
| Latency | `latency.js` |
| Cost | `cost.js` |
| Quality | `quality.jsx` |
| Token | `token.js` |
| Cache | `cache.js` |
| Routing | `routing.js` |
| Prompt | `prompt.js` |

Each config exports a `get[Story]Fixes(call, factors)` function:

```js
// Example from latency.js
export function getLatencyFixes(call, factors) {
  const fixes = [];

  // Conditionally add fixes based on detected factors
  if (factors.some(f => f.id === 'large_history')) {
    fixes.push({
      id: 'truncate_history',
      title: 'Prune Conversation History',
      subtitle: 'Remove old turns (keep last 2)',
      effort: 'Low',
      metrics: [...],
      codeBefore: '...',
      codeAfter: '...',
      tradeoffs: [...],
      benefits: [...],
    });
  }

  if (factors.some(f => f.id === 'no_streaming')) {
    fixes.push({
      id: 'enable_streaming',
      title: 'Enable Streaming',
      // ...
    });
  }

  return fixes.slice(0, 4); // Max 4 fixes
}
```

### 2. CallDetail Page

Located in `frontend/src/pages/stories/[story]/CallDetail.jsx`

The page:
1. Fetches call data from API
2. Analyzes the call to detect issues (factors)
3. Generates fixes based on detected factors
4. Passes everything to Layer3Shell

```jsx
// Example from latency/CallDetail.jsx (lines 168-170)
const factors = analyzeLatencyFactors(call);  // Detect issues
const fixes = getLatencyFixes(call, factors); // Generate fixes based on issues

// Then passes to Layer3Shell
<Layer3Shell
  fixes={fixes}
  responseText={call.response_text}
  // ...
/>
```

### 3. Layer3Shell

Located in `frontend/src/components/stories/Layer3/index.jsx`

The shell component:
- Manages tab navigation (DIAGNOSE, ATTRIBUTE, TRACE, SIMILAR, RAW, FIX)
- Tracks implemented fixes state
- Passes props to the active panel

```jsx
// Lines 330-346
{activeTab === 'fix' && (
  <FixPanel
    fixes={fixes}                      // Array of fix objects
    implementedFixes={implementedFixes} // IDs of applied fixes
    currentState={currentState}         // For comparison table
    onMarkImplemented={handleMarkImplemented}
    theme={theme}
    entityId={entityId}
    entityType={entityType}
    responseText={responseText}         // For before/after preview
    aiCallId={aiCallId}
  />
)}
```

### 4. FixPanel Component

Located in `frontend/src/components/stories/Layer3/FixPanel.jsx`

Renders fixes in two views:

**Comparison View** (default):
- Stacked FixCard components for each fix
- Quick Comparison Table showing all fixes side-by-side
- Cumulative Impact section showing total savings
- AI Analysis Panel at the bottom

**Detail View** (when a fix is selected):
- Full code before/after with copy buttons
- Output preview showing before/after changes
- Tradeoffs and Benefits lists
- "Apply This Fix" button

## Fix Object Structure

Each fix object has this shape:

```js
{
  // Identity
  id: 'truncate_history',           // Unique identifier
  title: 'Prune Conversation History',
  subtitle: 'Remove old turns (keep last 2)',

  // Effort indicator
  effort: 'Low',                    // 'Low' | 'Medium' | 'High'
  effortColor: 'text-green-400',    // Tailwind color class
  recommended: true,                // Shows ⭐ badge

  // Metrics comparison
  metrics: [
    {
      label: 'Latency',
      before: '12.5s',
      after: '~6.2s',
      changePercent: -50
    },
    {
      label: 'Tokens',
      before: '8,000',
      after: '3,200',
      changePercent: -60
    },
    {
      label: 'Cost',
      before: '$0.024',
      after: '$0.010',
      changePercent: -58
    },
    {
      label: 'Quality',
      before: 'Full context',
      after: '✅ Recent only',
      changePercent: 0
    },
  ],

  // Code examples
  codeBefore: `# Full history
messages = conversation_history`,

  codeAfter: `MAX_HISTORY = 10
def truncate_history(messages):
    system = messages[0] if messages[0]["role"] == "system" else None
    recent = messages[-MAX_HISTORY:]
    return [system] + recent if system else recent

messages = truncate_history(conversation_history)`,

  // Output preview
  outputPreview: 'Same quality output with less input context',
  outputNote: '✅ Same output quality, 4,800 fewer input tokens',
  outputNoteColor: 'text-green-400',
  outputTruncated: false,           // Shows warning if true

  // Pros and cons
  tradeoffs: [
    'Loses early conversation context',
    'May forget initial instructions from Turn 1-2',
    'Not suitable for tasks requiring full history',
  ],
  benefits: [
    'Removes 4,800 unnecessary tokens',
    'Significantly faster processing',
    'Lower token costs',
    'Simple to implement',
  ],

  // Use case
  bestFor: 'Multi-turn chats where recent context is most important',
}
```

## AI Analysis Section

The FixPanel also includes an `AIAnalysisPanel` component at the bottom (lines 393-405) that provides LLM-powered recommendations:

```jsx
{canShowAI && (
  <div className="mt-8 pt-8 border-t">
    <h3>🤖 AI-Powered Analysis</h3>
    <AIAnalysisPanel
      callId={callIdForAI}
      responseText={responseText}
    />
  </div>
)}
```

This appears when:
- `entityType === 'call'` (individual call view)
- OR `aiCallId` is provided (pattern view with a sample call)

## Component Hierarchy

```
FixPanel (main export)
├── FixComparisonView (default view)
│   ├── FixCard (one per fix)
│   │   └── Metrics grid, output preview, "View Details" button
│   ├── QuickComparisonTable
│   │   └── Side-by-side metrics for all fixes
│   ├── CumulativeImpact
│   │   └── Total savings if all fixes applied
│   └── AIAnalysisPanel
│       └── LLM-powered recommendations
│
└── FixDetailView (when fix selected)
    ├── Header with title, effort badge
    ├── Large KPI cards
    ├── Code Before/After with copy buttons
    ├── Output Change preview
    ├── Tradeoffs & Benefits lists
    └── Action buttons (Back, Copy, Apply)
```

## Adding a New Fix

To add a new fix to a story:

1. **Add factor detection** in `analyze[Story]Factors()`:
```js
if (call.some_condition) {
  factors.push({
    id: 'new_issue',
    severity: 'warning',
    label: 'Issue Label',
    impact: 'Impact description',
    hasFix: true,
  });
}
```

2. **Add fix generation** in `get[Story]Fixes()`:
```js
if (factors.some(f => f.id === 'new_issue')) {
  fixes.push({
    id: 'new_fix',
    title: 'Fix Title',
    // ... full fix object
  });
}
```

The FixPanel will automatically render the new fix.
