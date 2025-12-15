# Observatory Configuration Template

## 📋 Overview

This template provides a **production-ready configuration file** for integrating Observatory into any Python AI project. It includes full support for the **85-column schema** (58 original + 27 extracted columns) that enables all 7 Data Stories.

---

## ✅ Features

- ✅ **27-Column Support:** Auto-creates `prompt_breakdown` for Stories 2 & 6
- ✅ **Auto-Extraction:** Pulls token breakdown and model parameters automatically
- ✅ **Metadata Cleaning:** Removes non-serializable objects before saving
- ✅ **Phase Support:** Baseline vs Optimized tracking
- ✅ **Full Configuration:** Judge, Cache, Router, Prompts all configurable
- ✅ **Type-Safe:** Full type hints for all 85 columns
- ✅ **Framework Agnostic:** Works with any LLM framework (Semantic Kernel, LangChain, raw OpenAI, etc.)

---

## 🚀 Quick Start

### 1. Copy Template to Your Project

```bash
# Copy the template
cp observatory_config_template.py <your-project>/observatory_config.py

# Make sure Observatory SDK is installed
pip install observatory  # Or however you've packaged it
```

### 2. Customize for Your Project

Open `observatory_config.py` and look for `# 🔧 CUSTOMIZE` markers:

**Required Changes:**
```python
# Line 88: Project name
PROJECT_NAME = "My AI Project"  # 🔧 Change this

# Line 91: Model provider
DEFAULT_PROVIDER = ModelProvider.OPENAI  # Options: OPENAI, AZURE, ANTHROPIC

# Line 92: Default model
DEFAULT_MODEL = "gpt-4o-mini"  # 🔧 Your default model

# Line 95: Database path
OBSERVATORY_DB_PATH = "/path/to/observatory.db"  # 🔧 Adjust this
```

**Optional Customizations:**

1. **LLM Judge Configuration** (Lines 108-137)
   - Add your operations to judge
   - Configure domain-specific criteria
   - Adjust sample rate

2. **Cache Manager** (Lines 143-163)
   - Add operations to cache
   - Set TTL values
   - Configure cache clusters

3. **Model Router** (Lines 169-210)
   - Define routing rules
   - Set complexity thresholds
   - Configure fallback models

### 3. Use in Your Code

```python
from observatory_config import obs, track_llm_call, judge, cache, router

# Example: Track a simple LLM call
track_llm_call(
    model_name="gpt-4o-mini",
    prompt_tokens=100,
    completion_tokens=50,
    latency_ms=1250.0,
    operation="generate_response",
    agent_name="MyAgent",
    system_prompt="You are a helpful assistant.",
    user_message="Hello!",
    response_text="Hi! How can I help you today?"
)

# Example: Track with quality evaluation
quality = await judge.maybe_evaluate(
    operation="generate_response",
    prompt="You are a helpful assistant.\n\nHello!",
    response="Hi! How can I help you today?",
    client=openai_client  # Your LLM client
)

track_llm_call(
    model_name="gpt-4o-mini",
    prompt_tokens=100,
    completion_tokens=50,
    latency_ms=1250.0,
    operation="generate_response",
    agent_name="MyAgent",
    system_prompt="You are a helpful assistant.",
    user_message="Hello!",
    response_text="Hi! How can I help you today?",
    quality_evaluation=quality  # ✨ Quality scores tracked
)
```

---

## 🎯 What Gets Auto-Tracked

### Critical Columns (Stories 2 & 6):
When you pass `system_prompt` and `user_message` to `track_llm_call()`:

1. ✅ `prompt_breakdown` is **auto-created**
2. ✅ `system_prompt` column **auto-populated** (Story 6: Prompt Waste)
3. ✅ `user_message` column **auto-populated** (Story 2: Cache Opportunities)

**This happens automatically - you don't need to do anything!**

### Other Auto-Tracked Columns:

**From parameters you pass:**
- `cache_hit`, `cache_key` → Extracted from `cache_metadata`
- `judge_score`, `hallucination_flag` → Extracted from `quality_evaluation`
- `chosen_model`, `complexity_score` → Extracted from `routing_decision`
- `prompt_template_id` → Extracted from `prompt_metadata`

**Auto-calculated:**
- `response_length_chars` → Calculated from `response_text`
- `response_length_words` → Word count from `response_text`
- `cost_per_quality_point` → `total_cost / judge_score`

**From metadata dict:**
- `team_id`, `business_outcome`, `conversion_event`, `contains_pii`, etc.
- Just add these keys to your `metadata` dict

---

## 🔧 Advanced Configuration

### Multi-Turn Conversation Tracking

```python
# Link turns in a conversation
conversation_id = "conv_12345"

# Turn 1
track_llm_call(
    ...,
    conversation_id=conversation_id,
    turn_number=1,
    system_prompt="You are a helpful assistant.",
    user_message="What's the weather?"
)

# Turn 2 (references turn 1)
track_llm_call(
    ...,
    conversation_id=conversation_id,
    turn_number=2,
    user_message="How about tomorrow?"
)
```

### Business Metrics Tracking

```python
# Track conversion events
track_llm_call(
    ...,
    metadata={
        "team_id": "product_team",
        "business_outcome": "purchase_completed",
        "conversion_event": True,
    }
)
```

### Compliance Tracking

```python
# Track GDPR compliance
track_llm_call(
    ...,
    metadata={
        "contains_pii": True,
        "geographic_region": "EU",
        "data_retention_days": 30,
    }
)
```

### Session Management

```python
# Group related operations
session = start_session(
    operation_type="user_workflow",
    metadata={"user_id": "user_123"}
)

# Make multiple LLM calls...
track_llm_call(..., metadata={"session_id": session.id})
track_llm_call(..., metadata={"session_id": session.id})

end_session(session, success=True)
```

---

## 📊 What Stories This Enables

With this configuration, all 7 Data Stories work out of the box:

| Story | Enabled By | Auto-Tracked |
|-------|-----------|--------------|
| 1. Latency Monster | `latency_ms` | ✅ Always |
| 2. Cache Opportunities | `system_prompt` column | ✅ Auto-created |
| 3. Model Routing | `chosen_model`, `complexity_score` | ✅ From routing_decision |
| 4. Quality Issues | `judge_score`, `hallucination_flag` | ✅ From quality_evaluation |
| 5. Token Imbalance | `prompt_tokens`, `completion_tokens` | ✅ Always |
| 6. Prompt Waste | `system_prompt`, `system_prompt_tokens` | ✅ Auto-created |
| 7. Cost Deep Dive | `total_cost`, `operation` | ✅ Always |

---

## ⚠️ Important Notes

### Critical for Stories 2 & 6:

**ALWAYS pass `system_prompt` and `user_message` when calling `track_llm_call()`:**

```python
# ✅ GOOD - Stories 2 & 6 will work
track_llm_call(
    ...,
    system_prompt="You are a helpful assistant.",
    user_message="Hello!",
)

# ❌ BAD - Stories 2 & 6 won't work
track_llm_call(
    ...,
    prompt="You are a helpful assistant.\n\nHello!",  # Combined, can't extract
)
```

### Metadata Cleaning:

The template auto-removes these from metadata:
- `conversation_memory`
- `execution_settings`

If your framework uses other non-serializable objects, add them to the cleanup section (line 672):

```python
if metadata:
    metadata.pop('conversation_memory', None)
    metadata.pop('execution_settings', None)
    metadata.pop('your_custom_object', None)  # 🔧 Add yours here
```

---

## 🎯 Environment Variables

```bash
# .env file
OBSERVATORY_PHASE=baseline        # or 'optimized'
OPENAI_API_KEY=sk-...             # Your API key
OPENAI_MODEL=gpt-4o-mini          # Default model
DATABASE_URL=sqlite:///path/to/observatory.db  # Optional override
```

---

## 📝 Template Locations

**In Observatory Project:**
```
ai-agent-observatory/
├── examples/
│   └── observatory_config_template.py  # ← Put template here
└── README.md  # ← Link to template
```

**In Your Project:**
```
your-project/
├── observatory_config.py  # ← Copied and customized template
└── .env
```

---

## ✅ Testing Your Configuration

```python
# test_observatory.py
from observatory_config import obs, track_llm_call

# Make a test call
track_llm_call(
    model_name="gpt-4o-mini",
    prompt_tokens=10,
    completion_tokens=5,
    latency_ms=100.0,
    operation="test",
    agent_name="TestAgent",
    system_prompt="Test system prompt",
    user_message="Test message",
    response_text="Test response"
)

print("✅ Observatory tracking successful!")
```

Then check your database:
```sql
SELECT 
    operation, 
    system_prompt, 
    user_message,
    response_length_chars
FROM llm_calls
WHERE operation = 'test';
```

You should see:
- ✅ `system_prompt`: "Test system prompt"
- ✅ `user_message`: "Test message"
- ✅ `response_length_chars`: 13

**If these columns are populated → Template working perfectly!** ✅

---

## 🚀 Next Steps

1. ✅ Copy template to your project
2. ✅ Customize project-specific settings
3. ✅ Test with a simple LLM call
4. ✅ Verify columns populated in database
5. ✅ Run your application
6. ✅ Generate test data
7. ✅ Analyze with Stories dashboard

---

*Template Version: 1.0*  
*Schema Support: 85 columns (58 + 27 extracted)*  
*Compatible with: Observatory v1.0+*