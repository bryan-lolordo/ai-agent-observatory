# Observatory Data Mapping Guide

> **Version:** 1.0  
> **Last Updated:** December 2024  
> **Purpose:** Standardized reference for integrating AI applications with the Observatory dashboard

---

## Table of Contents

1. [Overview](#overview)
2. [Database Schema](#database-schema)
3. [JSON Field Structures](#json-field-structures)
4. [Page Data Requirements](#page-data-requirements)
5. [Field Priority Matrix](#field-priority-matrix)
6. [Tracking Tiers](#tracking-tiers)
7. [Integration Patterns](#integration-patterns)
8. [Helper Functions](#helper-functions)
9. [Common Patterns by Use Case](#common-patterns-by-use-case)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The Observatory is a comprehensive monitoring and optimization dashboard for AI/LLM applications. It tracks LLM calls across multiple dimensions:

- **Cost** — Token usage and spend analysis
- **Performance** — Latency and throughput metrics
- **Quality** — Response quality and hallucination detection
- **Optimization** — Routing, caching, and prompt optimization opportunities

### Architecture Flow

```
Your AI Application
        │
        ▼
   track_llm_call()  ──────►  Observatory Database (SQLite)
        │                              │
        │                              ▼
        │                     Dashboard Pages
        │                     ├── 🏠 Home
        │                     ├── 📡 Activity Monitor
        │                     ├── 💰 Cost Estimator
        │                     ├── 🔀 Model Router
        │                     ├── 💾 Cache Analyzer
        │                     ├── ⚖️ LLM Judge
        │                     ├── ✨ Prompt Optimizer
        │                     └── 📈 Optimization Impact
        │
        ▼
   Your Application Response
```

---

## Database Schema

### Sessions Table (`sessions`)

Tracks high-level session/workflow information.

| Column | Type | Description | Index |
|--------|------|-------------|-------|
| `id` | String | Unique session ID (UUID) | PK |
| `project_name` | String | Project identifier (e.g., "CareerCopilot") | ✅ |
| `start_time` | DateTime | Session start timestamp | ✅ |
| `end_time` | DateTime | Session end timestamp (nullable) | |
| `total_llm_calls` | Integer | Count of LLM calls in session | |
| `total_tokens` | Integer | Sum of all tokens used | |
| `total_cost` | Float | Sum of all costs | |
| `total_latency_ms` | Float | Sum of all latencies | |
| `total_routing_decisions` | Integer | Count of routing decisions | |
| `routing_cost_savings` | Float | Estimated savings from routing | |
| `total_cache_hits` | Integer | Count of cache hits | |
| `total_cache_misses` | Integer | Count of cache misses | |
| `cache_cost_savings` | Float | Estimated savings from caching | |
| `avg_quality_score` | Float | Average quality score (0-10) | |
| `total_hallucinations` | Integer | Count of hallucinations detected | |
| `total_errors` | Integer | Count of errors | |
| `success` | Boolean | Whether session completed successfully | |
| `error` | Text | Error message if failed | |
| `operation_type` | String | Type of operation/workflow | ✅ |
| `meta_data` | JSON | Additional session metadata | |

### LLM Calls Table (`llm_calls`)

The primary table tracking individual LLM API calls.

| Column | Type | Description | Index | Required |
|--------|------|-------------|-------|----------|
| `id` | String | Unique call ID (UUID) | PK | ✅ |
| `session_id` | String | Foreign key to sessions | ✅ | ✅ |
| `timestamp` | DateTime | When call occurred | ✅ | ✅ |
| `provider` | String | "openai", "azure", "anthropic", "other" | ✅ | ✅ |
| `model_name` | String | Model identifier (e.g., "gpt-4o-mini") | ✅ | ✅ |
| `prompt` | Text | Raw prompt text | | Recommended |
| `prompt_normalized` | Text | Normalized prompt for cache matching | | Optional |
| `response_text` | Text | LLM response content | | Recommended |
| `prompt_tokens` | Integer | Input token count | | ✅ |
| `completion_tokens` | Integer | Output token count | | ✅ |
| `total_tokens` | Integer | Sum of prompt + completion tokens | | ✅ |
| `prompt_cost` | Float | Cost for prompt tokens | | Auto-calculated |
| `completion_cost` | Float | Cost for completion tokens | | Auto-calculated |
| `total_cost` | Float | Total cost for the call | | Auto-calculated |
| `latency_ms` | Float | Response time in milliseconds | | ✅ |
| `agent_name` | String | Name of agent/plugin making call | ✅ | ✅ |
| `agent_role` | String | Role enum (analyst, reviewer, etc.) | ✅ | Optional |
| `operation` | String | Specific operation/function name | ✅ | ✅ |
| `success` | Boolean | Whether call succeeded | | ✅ |
| `error` | Text | Error message if failed | | Optional |
| `routing_decision` | JSON | Routing metadata (see below) | | Optional |
| `cache_metadata` | JSON | Cache metadata (see below) | | Optional |
| `quality_evaluation` | JSON | Quality/judge metadata (see below) | | Optional |
| `prompt_breakdown` | JSON | Prompt component analysis (see below) | | Optional |
| `prompt_metadata` | JSON | Prompt versioning metadata (see below) | | Optional |
| `prompt_variant_id` | String | A/B test variant identifier | ✅ | Optional |
| `test_dataset_id` | String | Test dataset identifier | ✅ | Optional |
| `meta_data` | JSON | Additional custom metadata | | Optional |

---

## JSON Field Structures

### `routing_decision`

Used by: **Model Router** page

Tracks model selection decisions for cost/performance optimization.

```json
{
    "chosen_model": "gpt-4o-mini",
    "alternative_models": ["gpt-4o", "gpt-4"],
    "model_scores": {
        "gpt-4o-mini": 0.85,
        "gpt-4o": 0.72
    },
    "reasoning": "Simple task with low complexity score",
    "rule_triggered": "JobPlugin.find_jobs → gpt-4o-mini",
    "complexity_score": 0.3,
    "estimated_cost_savings": 0.0023,
    "routing_strategy": "complexity_based"
}
```

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `chosen_model` | String | Model that was selected | ✅ |
| `alternative_models` | List[String] | Other models considered | ✅ |
| `model_scores` | Dict[String, Float] | Scores for each model | Optional |
| `reasoning` | String | Why this model was chosen | Recommended |
| `rule_triggered` | String | Which routing rule fired | Optional |
| `complexity_score` | Float (0-1) | Task complexity estimate | Recommended |
| `estimated_cost_savings` | Float | Estimated $ saved vs default | Optional |
| `routing_strategy` | String | Strategy used (complexity_based, cost_optimized, quality_first) | Optional |

### `cache_metadata`

Used by: **Cache Analyzer** page

Tracks caching behavior for identifying optimization opportunities.

```json
{
    "cache_hit": false,
    "cache_key": "job_search:python:chicago:5",
    "cache_cluster_id": "job_searches",
    "normalization_strategy": "lowercase_strip_whitespace",
    "similarity_score": 0.95,
    "eviction_info": null,
    "cache_key_candidates": ["job_search:python:chicago"],
    "dynamic_fields": ["timestamp", "user_id"],
    "content_hash": "a1b2c3d4e5f6",
    "ttl_seconds": 3600
}
```

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `cache_hit` | Boolean | Whether response came from cache | ✅ |
| `cache_key` | String | Cache key used | Recommended |
| `cache_cluster_id` | String | Semantic cluster identifier | Optional |
| `normalization_strategy` | String | How prompt was normalized | Optional |
| `similarity_score` | Float (0-1) | Semantic similarity to cached prompt | Optional |
| `eviction_info` | String | Why cache entry was evicted | Optional |
| `cache_key_candidates` | List[String] | Alternative keys considered | Optional |
| `dynamic_fields` | List[String] | Fields excluded from caching | Optional |
| `content_hash` | String | Hash of cacheable content | Optional |
| `ttl_seconds` | Integer | Time-to-live for cache entry | Optional |

### `quality_evaluation`

Used by: **LLM Judge** page

Tracks quality assessments from LLM-as-judge or manual evaluation.

```json
{
    "judge_score": 8.5,
    "hallucination_flag": false,
    "error_category": null,
    "reasoning": "Response accurately addresses the query with relevant details",
    "confidence_score": 0.92,
    "judge_model": "gpt-4o",
    "failure_reason": null,
    "improvement_suggestion": null,
    "hallucination_details": null,
    "evidence_cited": true,
    "factual_error": false,
    "criteria_scores": {
        "relevance": 9.0,
        "accuracy": 8.5,
        "completeness": 8.0
    }
}
```

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `judge_score` | Float (0-10) | Overall quality score | ✅ |
| `hallucination_flag` | Boolean | Whether hallucination detected | ✅ |
| `error_category` | String | Type of error if any | Optional |
| `reasoning` | String | Explanation of score | Recommended |
| `confidence_score` | Float (0-1) | Confidence in evaluation | Optional |
| `judge_model` | String | Model used for judging | Optional |
| `failure_reason` | String | HALLUCINATION, FACTUAL_ERROR, LOW_QUALITY | Optional |
| `improvement_suggestion` | String | Auto-generated fix suggestion | Optional |
| `hallucination_details` | String | What was hallucinated | Optional |
| `evidence_cited` | Boolean | Whether sources were cited | Optional |
| `factual_error` | Boolean | Whether factual error found | Optional |
| `criteria_scores` | Dict[String, Float] | Per-criteria scores | Optional |

### `prompt_breakdown`

Used by: **Prompt Optimizer** and **Model Router** pages

Analyzes prompt composition for optimization opportunities.

```json
{
    "system_prompt": "You are a helpful career advisor...",
    "system_prompt_tokens": 450,
    "chat_history": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ],
    "chat_history_tokens": 1200,
    "chat_history_count": 6,
    "user_message": "Find Python developer jobs in Chicago",
    "user_message_tokens": 12,
    "response_text": "I found 5 Python developer positions..."
}
```

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `system_prompt` | String | System prompt text (truncated) | Optional |
| `system_prompt_tokens` | Integer | Tokens in system prompt | Recommended |
| `chat_history` | List[Dict] | Message history | Optional |
| `chat_history_tokens` | Integer | Tokens in chat history | Recommended |
| `chat_history_count` | Integer | Number of history messages | Recommended |
| `user_message` | String | Current user message | Optional |
| `user_message_tokens` | Integer | Tokens in user message | Recommended |
| `response_text` | String | Response text (truncated) | Optional |

### `prompt_metadata`

Used by: **Prompt Optimizer** page

Tracks prompt template versioning for A/B testing and optimization.

```json
{
    "prompt_template_id": "job_search_v2",
    "prompt_version": "2.1.0",
    "compressible_sections": ["system_prompt", "examples"],
    "optimization_flags": {
        "caching_enabled": true,
        "compression_enabled": false
    },
    "config_version": "1.0"
}
```

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `prompt_template_id` | String | Template identifier | Optional |
| `prompt_version` | String | Semantic version | Optional |
| `compressible_sections` | List[String] | Sections that can be compressed | Optional |
| `optimization_flags` | Dict[String, Boolean] | Feature flags | Optional |
| `config_version` | String | Config file version | Optional |

---

## Page Data Requirements

### 🏠 Home Page

**Purpose:** High-level KPIs, trends, and alerts

| Section | Required Fields | Optional Fields |
|---------|-----------------|-----------------|
| KPI Cards | `total_cost`, `total_tokens`, `latency_ms`, row count | |
| Trend Charts | `timestamp`, `total_cost` | |
| Top Agents | `agent_name`, `total_cost` | |
| Quality Alerts | | `quality_evaluation.hallucination_flag`, `quality_evaluation.judge_score` |
| Error Summary | `success`, `error` | |

**Minimum Query:**
```sql
SELECT timestamp, total_cost, total_tokens, latency_ms, 
       agent_name, operation, success
FROM llm_calls
WHERE timestamp > :start_date
```

---

### 📡 Activity Monitor

**Purpose:** Live feed of LLM calls with drill-down diagnostics

| Section | Required Fields | Optional Fields |
|---------|-----------------|-----------------|
| Live Feed | `timestamp`, `agent_name`, `operation`, `model_name`, `latency_ms`, `total_cost`, `success` | |
| Call Detail | | `prompt`, `response_text`, `error` |
| Diagnosis | `prompt_tokens`, `completion_tokens` | `routing_decision`, `quality_evaluation` |
| Filters | `agent_name`, `operation`, `success` | |

**Minimum Query:**
```sql
SELECT timestamp, agent_name, operation, model_name, 
       latency_ms, total_cost, total_tokens, success,
       prompt_tokens, completion_tokens
FROM llm_calls
ORDER BY timestamp DESC
LIMIT :limit
```

---

### 💰 Cost Estimator

**Purpose:** Spend analysis and cost optimization opportunities

| Section | Required Fields | Optional Fields |
|---------|-----------------|-----------------|
| Spend Summary | `total_cost`, `timestamp` | |
| Where Money Goes | `agent_name`, `operation`, `total_cost` | |
| Cost by Model | `model_name`, `total_cost` | |
| Routing Opportunities | `model_name`, `total_tokens`, `completion_tokens` | |
| Cache Opportunities | | `prompt` (for duplicate detection) |
| Prompt Size Issues | `prompt_tokens` | |

**Cost Issues Detection Logic:**

| Issue Type | Detection Method |
|------------|------------------|
| Routing | Expensive model (`gpt-4o`, `gpt-4`) + Simple task (`total_tokens < 1500`) |
| Caching | Duplicate prompts (hash match on `prompt`) |
| Prompt Size | `prompt_tokens > 3000` |

**Minimum Query:**
```sql
SELECT timestamp, agent_name, operation, model_name,
       total_cost, prompt_tokens, completion_tokens, prompt
FROM llm_calls
WHERE timestamp > :start_date
```

---

### 🔀 Model Router

**Purpose:** Model selection optimization

| Section | Required Fields | Optional Fields |
|---------|-----------------|-----------------|
| **Discovery Mode** | | |
| Opportunities Table | `agent_name`, `operation`, `model_name`, `total_tokens`, `total_cost`, `latency_ms` | |
| Token Breakdown | `prompt_tokens` | `prompt_breakdown.*` |
| Suggested Rules | Above fields | `quality_evaluation.judge_score` |
| **Active Mode** | | |
| Rule Performance | | `routing_decision.rule_triggered`, `routing_decision.chosen_model` |
| Routing Mistakes | | `routing_decision` + `quality_evaluation.judge_score < 7` |
| Cost Savings | | `routing_decision.estimated_cost_savings` |

**Discovery Mode Query:**
```sql
SELECT agent_name, operation, model_name, 
       AVG(total_tokens) as avg_tokens,
       AVG(prompt_tokens) as avg_prompt_tokens,
       AVG(latency_ms) as avg_latency,
       SUM(total_cost) as total_cost,
       COUNT(*) as call_count
FROM llm_calls
GROUP BY agent_name, operation, model_name
```

**Active Mode Query:**
```sql
SELECT agent_name, operation, model_name,
       routing_decision, quality_evaluation,
       total_cost, latency_ms
FROM llm_calls
WHERE routing_decision IS NOT NULL
```

---

### 💾 Cache Analyzer

**Purpose:** Identify caching opportunities and monitor cache performance

| Section | Required Fields | Optional Fields |
|---------|-----------------|-----------------|
| **Discovery Mode** | | |
| Duplicate Groups | `prompt`, `agent_name`, `operation` | |
| Wasted Cost | `total_cost` | |
| Caching Candidates | `agent_name`, `operation`, duplicate count | |
| **Active Mode** | | |
| Hit Rate | | `cache_metadata.cache_hit` |
| Savings | | `cache_metadata.cache_hit`, `total_cost`, `latency_ms` |
| Cluster Analysis | | `cache_metadata.cache_cluster_id` |

**Discovery Mode Query:**
```sql
SELECT agent_name, operation, prompt, total_cost, timestamp,
       MD5(LOWER(TRIM(prompt))) as prompt_hash
FROM llm_calls
WHERE prompt IS NOT NULL
```

**Active Mode Query:**
```sql
SELECT agent_name, operation,
       cache_metadata,
       total_cost, latency_ms
FROM llm_calls
WHERE cache_metadata IS NOT NULL
```

---

### ⚖️ LLM Judge

**Purpose:** Quality monitoring and hallucination detection

| Section | Required Fields | Optional Fields |
|---------|-----------------|-----------------|
| Summary KPIs | `quality_evaluation.judge_score`, `quality_evaluation.hallucination_flag` | |
| Evaluations Table | `quality_evaluation.*`, `agent_name`, `operation`, `model_name`, `timestamp` | |
| Evaluation Detail | | `quality_evaluation.reasoning`, `prompt`, `response_text` |
| By Operation | `agent_name`, `operation`, `quality_evaluation.judge_score` | |
| Coverage Gaps | `agent_name`, `operation`, presence of `quality_evaluation` | |

**Requires `quality_evaluation` to be populated.** Without this, page shows empty state.

**Query:**
```sql
SELECT agent_name, operation, model_name, timestamp,
       quality_evaluation, prompt, response_text
FROM llm_calls
WHERE quality_evaluation IS NOT NULL
```

---

### ✨ Prompt Optimizer

**Purpose:** Prompt size analysis and optimization suggestions

| Section | Required Fields | Optional Fields |
|---------|-----------------|-----------------|
| Summary KPIs | `prompt_tokens` | |
| Prompts by Operation | `agent_name`, `operation`, `prompt_tokens` | |
| Token Breakdown | `prompt_tokens` | `prompt_breakdown.*` |
| Optimization Suggestions | `prompt_tokens` | `prompt_breakdown` |
| Prompt Versions | | `prompt_variant_id`, `prompt_metadata.prompt_version` |

**Query:**
```sql
SELECT agent_name, operation,
       AVG(prompt_tokens) as avg_tokens,
       MAX(prompt_tokens) as max_tokens,
       COUNT(*) as call_count,
       prompt_breakdown
FROM llm_calls
GROUP BY agent_name, operation
```

---

### 📈 Optimization Impact

**Purpose:** Before/after comparison of optimizations

| Section | Required Fields | Optional Fields |
|---------|-----------------|-----------------|
| Metrics Comparison | `timestamp`, `total_cost`, `latency_ms`, `total_tokens` | |
| By Optimization Type | | `routing_decision`, `cache_metadata` |
| Savings Attribution | | `routing_decision.estimated_cost_savings`, `cache_metadata.cache_hit` |

**Query:**
```sql
SELECT DATE(timestamp) as date,
       SUM(total_cost) as daily_cost,
       AVG(latency_ms) as avg_latency,
       SUM(total_tokens) as total_tokens,
       SUM(CASE WHEN cache_metadata->>'cache_hit' = 'true' THEN 1 ELSE 0 END) as cache_hits
FROM llm_calls
GROUP BY DATE(timestamp)
ORDER BY date
```

---

## Field Priority Matrix

Shows which fields are used by which pages.

| Field | Home | Activity | Cost | Router | Cache | Judge | Prompt | Impact |
|-------|:----:|:--------:|:----:|:------:|:-----:|:-----:|:------:|:------:|
| `timestamp` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `agent_name` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `operation` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `model_name` | ⚪ | ✅ | ✅ | ✅ | ⚪ | ✅ | ⚪ | ⚪ |
| `total_cost` | ✅ | ✅ | ✅ | ✅ | ✅ | ⚪ | ⚪ | ✅ |
| `prompt_tokens` | ⚪ | ✅ | ✅ | ✅ | ⚪ | ⚪ | ✅ | ⚪ |
| `completion_tokens` | ⚪ | ✅ | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ⚪ |
| `total_tokens` | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ | ✅ |
| `latency_ms` | ✅ | ✅ | ⚪ | ✅ | ⚪ | ⚪ | ⚪ | ✅ |
| `success` | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |
| `error` | ⚪ | ✅ | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |
| `prompt` | ⚪ | 🔶 | 🔶 | 🔶 | ✅ | 🔶 | 🔶 | ⚪ |
| `response_text` | ⚪ | 🔶 | ⚪ | ⚪ | ⚪ | 🔶 | ⚪ | ⚪ |
| `routing_decision` | ⚪ | 🔶 | ⚪ | 🔶 | ⚪ | ⚪ | ⚪ | 🔶 |
| `cache_metadata` | ⚪ | ⚪ | ⚪ | ⚪ | 🔶 | ⚪ | ⚪ | 🔶 |
| `quality_evaluation` | 🔶 | 🔶 | ⚪ | 🔶 | ⚪ | ✅ | ⚪ | ⚪ |
| `prompt_breakdown` | ⚪ | ⚪ | ⚪ | 🔶 | ⚪ | ⚪ | 🔶 | ⚪ |
| `prompt_metadata` | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ | 🔶 | ⚪ |

**Legend:**
- ✅ **Required** — Page needs this field to function
- 🔶 **Enhanced** — Enables additional features (page works without)
- ⚪ **Not Used** — Field not used by this page

---

## Tracking Tiers

Progressive levels of instrumentation, from basic to comprehensive.

### Tier 1: Baseline

**Effort:** Minimal  
**Pages Enabled:** Home, Activity, Cost (basic), Router (discovery basic)

```python
track_llm_call(
    model_name="gpt-4o-mini",
    prompt_tokens=150,
    completion_tokens=200,
    latency_ms=850.5,
    agent_name="JobPlugin",
    operation="find_jobs",
    success=True,
)
```

**What You Get:**
- ✅ Home: All KPIs and trends
- ✅ Activity: Live feed with basic details
- ✅ Cost: Spend by agent/operation/model
- ✅ Router: Downgrade/upgrade opportunities (estimated)
- ❌ Cache: No duplicate detection
- ❌ Judge: No quality data
- ❌ Prompt: Basic token counts only

---

### Tier 2: + Prompts

**Effort:** Low  
**Pages Enabled:** All Tier 1 + Cache (discovery), better diagnostics

```python
track_llm_call(
    model_name="gpt-4o-mini",
    prompt_tokens=150,
    completion_tokens=200,
    latency_ms=850.5,
    agent_name="JobPlugin",
    operation="find_jobs",
    success=True,
    # NEW
    prompt="Find Python developer jobs in Chicago",
    response_text="I found 5 Python developer positions...",
)
```

**What You Add:**
- ✅ Cache: Duplicate detection and caching candidates
- ✅ Activity: Full prompt/response in detail view
- ✅ Cost: Duplicate-based cost savings opportunities
- ✅ Router: Better token breakdown estimation

---

### Tier 3: + Quality Evaluation

**Effort:** Medium (requires LLM-as-judge implementation)  
**Pages Enabled:** All Tier 2 + Judge, quality alerts

```python
track_llm_call(
    model_name="gpt-4o-mini",
    prompt_tokens=150,
    completion_tokens=200,
    latency_ms=850.5,
    agent_name="JobPlugin",
    operation="find_jobs",
    success=True,
    prompt="Find Python developer jobs in Chicago",
    response_text="I found 5 Python developer positions...",
    # NEW
    quality_evaluation=create_quality_evaluation(
        judge_score=8.5,
        hallucination_flag=False,
        reasoning="Response accurately lists relevant positions",
        confidence_score=0.92
    ),
)
```

**What You Add:**
- ✅ Judge: Full quality monitoring dashboard
- ✅ Home: Quality alerts for hallucinations/low scores
- ✅ Router: Detect routing mistakes (low quality + cheap model)
- ✅ Activity: Quality indicators in feed

---

### Tier 4: + Routing & Caching (Active Mode)

**Effort:** Medium (requires routing/caching implementation)  
**Pages Enabled:** All Tier 3 + Router Active Mode, Cache Active Mode

```python
track_llm_call(
    model_name="gpt-4o-mini",
    prompt_tokens=150,
    completion_tokens=200,
    latency_ms=850.5,
    agent_name="JobPlugin",
    operation="find_jobs",
    success=True,
    prompt="Find Python developer jobs in Chicago",
    response_text="I found 5 Python developer positions...",
    quality_evaluation=create_quality_evaluation(
        judge_score=8.5,
        hallucination_flag=False,
    ),
    # NEW
    routing_decision=create_routing_decision(
        chosen_model="gpt-4o-mini",
        alternative_models=["gpt-4o"],
        reasoning="Simple search task",
        complexity_score=0.3,
        estimated_cost_savings=0.002
    ),
    cache_metadata=create_cache_metadata(
        cache_hit=False,
        cache_key="job_search:python:chicago",
        cache_cluster_id="job_searches"
    ),
)
```

**What You Add:**
- ✅ Router: Active mode with rule performance tracking
- ✅ Cache: Active mode with hit rate and savings
- ✅ Impact: Optimization attribution and savings tracking

---

### Tier 5: + Prompt Analysis (Full)

**Effort:** High  
**Pages Enabled:** All features

```python
track_llm_call(
    model_name="gpt-4o-mini",
    prompt_tokens=150,
    completion_tokens=200,
    latency_ms=850.5,
    agent_name="JobPlugin",
    operation="find_jobs",
    success=True,
    prompt="Find Python developer jobs in Chicago",
    response_text="I found 5 Python developer positions...",
    quality_evaluation=create_quality_evaluation(
        judge_score=8.5,
        hallucination_flag=False,
    ),
    routing_decision=create_routing_decision(
        chosen_model="gpt-4o-mini",
        alternative_models=["gpt-4o"],
        reasoning="Simple search task",
        complexity_score=0.3,
    ),
    cache_metadata=create_cache_metadata(
        cache_hit=False,
        cache_key="job_search:python:chicago",
    ),
    # NEW
    prompt_breakdown=PromptBreakdown(
        system_prompt_tokens=450,
        chat_history_tokens=0,
        chat_history_count=0,
        user_message_tokens=12
    ),
    prompt_metadata=PromptMetadata(
        prompt_template_id="job_search_v2",
        prompt_version="2.1.0"
    ),
)
```

**What You Add:**
- ✅ Prompt: Detailed component breakdown
- ✅ Router: Accurate token attribution
- ✅ A/B testing support with version tracking

---

### Tier Comparison Summary

| Feature | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Tier 5 |
|---------|:------:|:------:|:------:|:------:|:------:|
| Home KPIs | ✅ | ✅ | ✅ | ✅ | ✅ |
| Activity Feed | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cost Analysis | ✅ | ✅ | ✅ | ✅ | ✅ |
| Router Discovery | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cache Discovery | ❌ | ✅ | ✅ | ✅ | ✅ |
| Quality Alerts | ❌ | ❌ | ✅ | ✅ | ✅ |
| LLM Judge | ❌ | ❌ | ✅ | ✅ | ✅ |
| Router Active | ❌ | ❌ | ❌ | ✅ | ✅ |
| Cache Active | ❌ | ❌ | ❌ | ✅ | ✅ |
| Impact Tracking | ❌ | ❌ | ❌ | ✅ | ✅ |
| Prompt Breakdown | ❌ | ❌ | ❌ | ❌ | ✅ |
| A/B Testing | ❌ | ❌ | ❌ | ❌ | ✅ |

**Recommendation:** Start with **Tier 2**. It provides 80% of the value with minimal effort. Add Tier 3 when you implement LLM-as-judge. Add Tier 4 when you implement actual routing/caching.

---

## Integration Patterns

### Pattern 1: Semantic Kernel Plugin

```python
from semantic_kernel.functions import kernel_function
from observatory_config import track_llm_call
import time

class MyPlugin:
    @kernel_function(name="my_function", description="...")
    async def my_function(self, query: str) -> str:
        start_time = time.time()
        
        # Your LLM call here
        response = await self.llm.complete(query)
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Track it
        track_llm_call(
            model_name=self.model_name,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            latency_ms=latency_ms,
            agent_name="MyPlugin",
            operation="my_function",
            prompt=query,
            response_text=response.content,
        )
        
        return response.content
```

### Pattern 2: LangChain Callback

```python
from langchain.callbacks.base import BaseCallbackHandler
from observatory_config import track_llm_call
import time

class ObservatoryCallback(BaseCallbackHandler):
    def __init__(self, agent_name: str, operation: str):
        self.agent_name = agent_name
        self.operation = operation
        self.start_time = None
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        self.start_time = time.time()
        self.prompt = prompts[0] if prompts else ""
    
    def on_llm_end(self, response, **kwargs):
        latency_ms = (time.time() - self.start_time) * 1000
        
        track_llm_call(
            model_name=response.llm_output.get("model_name", "unknown"),
            prompt_tokens=response.llm_output.get("token_usage", {}).get("prompt_tokens", 0),
            completion_tokens=response.llm_output.get("token_usage", {}).get("completion_tokens", 0),
            latency_ms=latency_ms,
            agent_name=self.agent_name,
            operation=self.operation,
            prompt=self.prompt,
            response_text=response.generations[0][0].text,
        )
```

### Pattern 3: OpenAI Client Wrapper

```python
from openai import OpenAI
from observatory_config import track_llm_call
import time

class TrackedOpenAI:
    def __init__(self, agent_name: str):
        self.client = OpenAI()
        self.agent_name = agent_name
    
    def chat_complete(self, operation: str, messages: list, model: str = "gpt-4o-mini"):
        start_time = time.time()
        
        response = self.client.chat.completions.create(
            model=model,
            messages=messages
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        track_llm_call(
            model_name=model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            latency_ms=latency_ms,
            agent_name=self.agent_name,
            operation=operation,
            prompt=messages[-1]["content"],  # Last user message
            response_text=response.choices[0].message.content,
        )
        
        return response
```

---

## Helper Functions

Your `observatory_config.py` should expose these helper functions:

### `track_llm_call()`

Main tracking function.

```python
def track_llm_call(
    # Required
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
    
    # Recommended
    agent_name: str = None,
    operation: str = None,
    prompt: str = None,
    response_text: str = None,
    
    # Optional
    success: bool = True,
    error: str = None,
    routing_decision: RoutingDecision = None,
    cache_metadata: CacheMetadata = None,
    quality_evaluation: QualityEvaluation = None,
    prompt_breakdown: PromptBreakdown = None,
    prompt_metadata: PromptMetadata = None,
    metadata: dict = None,
) -> LLMCall:
    ...
```

### `create_routing_decision()`

Helper to create routing decision objects.

```python
def create_routing_decision(
    chosen_model: str,
    alternative_models: list = None,
    reasoning: str = "",
    complexity_score: float = None,
    estimated_cost_savings: float = None,
) -> RoutingDecision:
    return RoutingDecision(
        chosen_model=chosen_model,
        alternative_models=alternative_models or [],
        reasoning=reasoning,
        complexity_score=complexity_score,
        estimated_cost_savings=estimated_cost_savings,
    )
```

### `create_cache_metadata()`

Helper to create cache metadata objects.

```python
def create_cache_metadata(
    cache_hit: bool,
    cache_key: str = None,
    cache_cluster_id: str = None,
    similarity_score: float = None,
) -> CacheMetadata:
    return CacheMetadata(
        cache_hit=cache_hit,
        cache_key=cache_key,
        cache_cluster_id=cache_cluster_id,
        similarity_score=similarity_score,
    )
```

### `create_quality_evaluation()`

Helper to create quality evaluation objects.

```python
def create_quality_evaluation(
    judge_score: float,
    hallucination_flag: bool = False,
    reasoning: str = None,
    confidence_score: float = None,
) -> QualityEvaluation:
    return QualityEvaluation(
        judge_score=judge_score,
        hallucination_flag=hallucination_flag,
        reasoning=reasoning,
        confidence_score=confidence_score,
    )
```

### `start_tracking_session()` / `end_tracking_session()`

Session management.

```python
def start_tracking_session(
    operation_type: str = None,
    metadata: dict = None,
) -> Session:
    ...

def end_tracking_session(
    session: Session,
    success: bool = True,
    error: str = None,
) -> Session:
    ...
```

---

## Common Patterns by Use Case

### Multi-Agent System

Track each agent separately:

```python
# Agent 1: Classifier
track_llm_call(
    agent_name="Classifier",
    operation="classify_intent",
    ...
)

# Agent 2: Responder
track_llm_call(
    agent_name="Responder", 
    operation="generate_response",
    ...
)

# Agent 3: Reviewer
track_llm_call(
    agent_name="Reviewer",
    operation="review_response",
    ...
)
```

### Chatbot with History

Track conversation context:

```python
track_llm_call(
    agent_name="Chatbot",
    operation="chat_turn",
    prompt=current_message,
    prompt_breakdown=PromptBreakdown(
        system_prompt_tokens=system_tokens,
        chat_history_tokens=history_tokens,
        chat_history_count=len(history),
        user_message_tokens=message_tokens,
    ),
    ...
)
```

### RAG Pipeline

Track retrieval and generation separately:

```python
# Track retrieval (optional - no LLM call)
track_llm_call(
    agent_name="RAG",
    operation="retrieve_context",
    prompt_tokens=query_tokens,
    completion_tokens=0,  # No generation
    latency_ms=retrieval_time,
    ...
)

# Track generation
track_llm_call(
    agent_name="RAG",
    operation="generate_answer",
    prompt=f"{context}\n\n{query}",
    ...
)
```

### A/B Testing Prompts

Track variants:

```python
track_llm_call(
    agent_name="SearchAgent",
    operation="search",
    prompt_variant_id="search_prompt_v2",
    prompt_metadata=PromptMetadata(
        prompt_template_id="search_template",
        prompt_version="2.0.0",
    ),
    ...
)
```

---

## Troubleshooting

### Page Shows Empty State

| Page | Likely Cause | Solution |
|------|--------------|----------|
| All pages | No data in database | Run test script or make real calls |
| LLM Judge | No `quality_evaluation` | Add quality evaluation to tracking |
| Cache Active | No `cache_metadata` | Add cache metadata to tracking |
| Router Active | No `routing_decision` | Add routing decision to tracking |

### Missing Agent/Operation Breakdown

- **Cause:** `agent_name` or `operation` is null
- **Solution:** Always provide these fields in `track_llm_call()`

### Costs Show as $0.00

- **Cause:** Model not in pricing table
- **Solution:** Add your model to `calculate_cost()` in `collector.py`

### Cache Not Detecting Duplicates

- **Cause:** `prompt` field is empty
- **Solution:** Pass the actual prompt text to `track_llm_call()`

### Quality Alerts Not Appearing

- **Cause:** No calls with `quality_evaluation.hallucination_flag=True` or `judge_score < 7`
- **Solution:** Implement LLM-as-judge and populate quality_evaluation

---

## Quick Reference Card

```python
# Minimum viable tracking
track_llm_call(
    model_name="gpt-4o-mini",
    prompt_tokens=100,
    completion_tokens=200,
    latency_ms=500,
    agent_name="MyAgent",      # ← ALWAYS SET THIS
    operation="my_operation",  # ← ALWAYS SET THIS
)

# Recommended tracking (Tier 2)
track_llm_call(
    model_name="gpt-4o-mini",
    prompt_tokens=100,
    completion_tokens=200,
    latency_ms=500,
    agent_name="MyAgent",
    operation="my_operation",
    prompt=user_input,          # ← ADD THIS
    response_text=llm_response, # ← ADD THIS
)

# Full tracking (Tier 4)
track_llm_call(
    model_name="gpt-4o-mini",
    prompt_tokens=100,
    completion_tokens=200,
    latency_ms=500,
    agent_name="MyAgent",
    operation="my_operation",
    prompt=user_input,
    response_text=llm_response,
    routing_decision=create_routing_decision(...),
    cache_metadata=create_cache_metadata(...),
    quality_evaluation=create_quality_evaluation(...),
)
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Dec 2024 | Initial release |

---

*For questions or contributions, see the Observatory repository.*