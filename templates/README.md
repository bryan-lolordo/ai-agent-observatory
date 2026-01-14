# Observatory Integration Templates

These templates help you add Observatory tracking to your AI applications.

## Quick Start

### 1. Install the SDK

```bash
# From local clone
pip install -e /path/to/ai-agent-observatory

# Or from GitHub
pip install git+https://github.com/bryan-lolordo/ai-agent-observatory.git

# Optional: for semantic caching
pip install chromadb
```

### 2. Copy the Config Template

```bash
cp templates/observatory_config_template.py your-project/observatory_config.py
```

Edit `observatory_config.py` and customize:
- `PROJECT_NAME` - Your project name
- `operations` in judge, cache, router - Your operations
- `PROMPT_VARIANTS` and `OPERATION_COMPLEXITY` - Your prompts

### 3. Add Tracking to Your Code

Open `templates/llm_call_template.py` and copy the relevant pattern into your code:

| Pattern | Use Case |
|---------|----------|
| **Import Block** | Add to top of any file that makes LLM calls |
| **Chat Handler** | Main chatbot entry points (Streamlit, CLI) |
| **Plugin Pattern** | Standalone LLM functions (analysis, scoring) |
| **Simple Tracking** | Non-LLM operations (DB queries, API calls) |

## File Overview

| File | Purpose |
|------|---------|
| `observatory_config_template.py` | One-time setup - creates all Observatory components |
| `llm_call_template.py` | Reference patterns - copy into your LLM-calling code |

## The 10-Step Optimization Pattern

Every LLM call should follow these steps:

1. **Check exact cache** - Skip LLM if we have cached response
2. **Check semantic cache** - Skip if similar prompt was answered
3. **Get optimized prompt** - Compress if in optimized phase
4. **Get routed model** - Select best model for operation
5. **Track prefix cache** - Detect prefix caching opportunities
6. **Make LLM call** - The actual API call
7. **Extract tokens** - Get usage from response
8. **Cache response** - Store for future hits
9. **Evaluate quality** - LLM Judge scoring
10. **Track with Observatory** - Record everything

## Phases

Set via environment variable:

```bash
# Baseline: Track metrics only, no behavior changes (default)
export OBSERVATORY_PHASE=baseline

# Optimized: Apply caching, routing, compression
export OBSERVATORY_PHASE=optimized
```

Start with `baseline` to collect data, then switch to `optimized` to see savings.
