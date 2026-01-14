# Tracked Metrics Reference

Observatory tracks 70+ fields for every LLM call. This document provides the complete reference.

---

## Core Metrics

| Field | Description |
|-------|-------------|
| `id` | Unique call identifier |
| `session_id` | Session grouping |
| `timestamp` | When the call occurred |
| `call_type` | LLM, API, Database, or Tool |
| `provider` | OpenAI, Anthropic, Azure, etc. |
| `model_name` | Specific model used |
| `success` | Whether call succeeded |
| `error` | Error message if failed |

---

## Token Tracking

| Field | Description |
|-------|-------------|
| `prompt_tokens` | Input token count |
| `completion_tokens` | Output token count |
| `total_tokens` | Combined total |
| `system_prompt_tokens` | System prompt portion |
| `user_message_tokens` | User message portion |
| `chat_history_tokens` | Conversation history |
| `chat_history_count` | Number of history messages |
| `conversation_context_tokens` | Memory/context tokens |
| `tool_definitions_tokens` | Function schema tokens |
| `cached_prompt_tokens` | Tokens served from cache |

---

## Cost Tracking

| Field | Description |
|-------|-------------|
| `prompt_cost` | Input token cost |
| `completion_cost` | Output token cost |
| `total_cost` | Combined cost |
| `cached_token_savings` | Cost saved via caching |

---

## Latency & Performance

| Field | Description |
|-------|-------------|
| `latency_ms` | Total response time |
| `time_to_first_token_ms` | Streaming TTFT |
| `tool_execution_time_ms` | Time spent in tools |

---

## Context & Identity

| Field | Description |
|-------|-------------|
| `agent_name` | Which agent made the call |
| `agent_role` | Agent's role (analyst, writer, reviewer, planner, etc.) |
| `operation` | What operation was performed |
| `conversation_id` | Conversation grouping |
| `turn_number` | Position in conversation |
| `parent_call_id` | For retries/branches |
| `user_id` | User identifier |

---

## Model Configuration

| Field | Description |
|-------|-------------|
| `temperature` | Sampling temperature (0-2) |
| `max_tokens` | Token limit |
| `top_p` | Nucleus sampling |
| `frequency_penalty` | Repetition penalty |
| `presence_penalty` | Topic penalty |
| `response_format` | Text or JSON mode |
| `seed` | For reproducibility |
| `stop_sequences` | Stop tokens |

---

## Cache Metadata

| Field | Description |
|-------|-------------|
| `cache_hit` | Whether cache was used |
| `cache_key` | Cache lookup key |
| `cache_cluster_id` | Semantic cluster |
| `similarity_score` | Semantic match score (0-1) |
| `content_hash` | Prompt fingerprint |
| `ttl_seconds` | Cache expiration |
| `normalization_strategy` | How prompt was normalized |
| `eviction_info` | Why cache entry was evicted |

---

## Routing Decision

| Field | Description |
|-------|-------------|
| `chosen_model` | Selected model |
| `alternative_models` | Other options considered |
| `model_scores` | Scores for each model option |
| `complexity_score` | Task complexity (0-1) |
| `routing_strategy` | Rule that triggered |
| `rule_triggered` | Specific rule name |
| `estimated_cost_savings` | Projected savings |
| `reasoning` | Why this model was chosen |

---

## Quality Evaluation

| Field | Description |
|-------|-------------|
| `judge_score` | Quality score (0-10) |
| `hallucination_flag` | Detected hallucination |
| `hallucination_details` | Specifics of hallucination |
| `confidence_score` | Judge confidence (0-1) |
| `error_category` | Error classification |
| `failure_reason` | Why the call failed |
| `improvement_suggestion` | How to improve |
| `evidence_cited` | Whether evidence was provided |
| `factual_error` | Whether factual errors exist |
| `criteria_scores` | Per-criteria breakdown |
| `judge_model` | Model used for judging |

---

## Error Details

| Field | Description |
|-------|-------------|
| `error_type` | RATE_LIMIT, TIMEOUT, INVALID_REQUEST, etc. |
| `error_code` | Provider error code (e.g., "429") |
| `retry_count` | Number of retries |
| `retry_strategy` | exponential_backoff, linear, etc. |
| `final_success` | Did retry eventually succeed |
| `error_details` | Full error message |

---

## Streaming Metrics

| Field | Description |
|-------|-------------|
| `is_streaming` | Streaming enabled |
| `time_to_first_token_ms` | Perceived latency |
| `stream_chunk_count` | Number of chunks |
| `stream_interrupted` | Whether stream failed |
| `average_chunk_size` | Tokens per chunk |

---

## Experiment Tracking

| Field | Description |
|-------|-------------|
| `experiment_id` | A/B test identifier |
| `experiment_name` | Human-readable name |
| `variant_id` | Which variant (A, B, etc.) |
| `variant_name` | Human-readable variant name |
| `control_group` | Is baseline group |
| `sample_rate` | % of traffic allocated |
| `hypothesis` | What you're testing |
| `expected_improvement` | Target metric |
| `cohort` | User segment |
| `prompt_variant_id` | Prompt version |
| `test_dataset_id` | Evaluation dataset |

---

## Prompt Analysis

| Field | Description |
|-------|-------------|
| `prompt` | Full prompt text |
| `prompt_normalized` | Normalized for caching |
| `prompt_template_id` | Template identifier |
| `prompt_version` | Template version |
| `prompt_hash` | Content hash |
| `compressible_sections` | Sections that can be compressed |
| `system_to_total_ratio` | System prompt % of total |
| `history_to_total_ratio` | History % of total |

---

## Observability

| Field | Description |
|-------|-------------|
| `trace_id` | OpenTelemetry trace |
| `request_id` | Provider request ID |
| `environment` | dev, staging, prod |
| `prompt_prefix_hash` | For prefix caching detection |

---

## Custom Metadata

| Field | Description |
|-------|-------------|
| `metadata` | Dict for any custom fields |

You can store any additional data in the `metadata` field:

```python
track_llm_call(
    # ... standard fields
    metadata={
        "user_tier": "premium",
        "feature_flag": "new_prompt_v2",
        "request_source": "mobile_app",
    }
)
```
