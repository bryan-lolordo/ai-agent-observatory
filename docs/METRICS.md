# Tracked Metrics Reference

Observatory tracks **139 fields** for every LLM call. This document provides the complete reference.

---

## Database Columns (89 direct columns)

### Core Identification

| Field | Type | Description |
|-------|------|-------------|
| `id` | String | Unique call identifier |
| `session_id` | String | Session grouping |
| `timestamp` | DateTime | When the call occurred |
| `call_type` | String | llm, api, database, or tool |
| `provider` | String | openai, anthropic, azure, other |
| `model_name` | String | Specific model used (gpt-4, claude-3, etc.) |

### Token Metrics

| Field | Type | Description |
|-------|------|-------------|
| `prompt_tokens` | Integer | Input token count |
| `completion_tokens` | Integer | Output token count |
| `total_tokens` | Integer | Combined total |
| `system_prompt_tokens` | Integer | System prompt portion |
| `user_message_tokens` | Integer | User message portion |
| `chat_history_tokens` | Integer | Conversation history tokens |
| `chat_history_count` | Integer | Number of history messages |
| `conversation_context_tokens` | Integer | Memory/context tokens |
| `tool_definitions_tokens` | Integer | Function schema tokens |
| `cached_prompt_tokens` | Integer | Tokens served from provider cache |

### Cost Metrics

| Field | Type | Description |
|-------|------|-------------|
| `prompt_cost` | Float | Input token cost ($) |
| `completion_cost` | Float | Output token cost ($) |
| `total_cost` | Float | Combined cost ($) |
| `cached_token_savings` | Float | Cost saved via provider caching |
| `estimated_cost_savings` | Float | Routing/optimization savings |
| `cost_per_quality_point` | Float | Efficiency metric (cost/quality) |

### Latency & Performance

| Field | Type | Description |
|-------|------|-------------|
| `latency_ms` | Float | Total response time |
| `time_to_first_token_ms` | Float | Streaming TTFT (perceived latency) |
| `tool_execution_time_ms` | Float | Time spent executing tools |

### Prompt & Response Content

| Field | Type | Description |
|-------|------|-------------|
| `prompt` | Text | Full prompt text |
| `prompt_normalized` | Text | Normalized for caching comparison |
| `content_hash` | String | Hash for deduplication detection |
| `response_text` | Text | LLM response |
| `system_prompt` | Text | Extracted system prompt |
| `user_message` | Text | Extracted user message |
| `response_length_chars` | Integer | Response character count |
| `response_length_words` | Integer | Response word count |

### Context & Identity

| Field | Type | Description |
|-------|------|-------------|
| `agent_name` | String | Which agent made the call |
| `agent_role` | String | analyst, reviewer, writer, orchestrator, etc. |
| `operation` | String | What operation was performed |
| `conversation_id` | String | Conversation grouping |
| `turn_number` | Integer | Position in conversation |
| `parent_call_id` | String | For retries/call chains |
| `user_id` | String | User identifier |
| `team_id` | String | Team for cost attribution |

### Model Configuration

| Field | Type | Description |
|-------|------|-------------|
| `temperature` | Float | Sampling temperature (0-2) |
| `max_tokens` | Integer | Token limit |
| `top_p` | Float | Nucleus sampling |
| `model_version` | String | Specific model version |

### Cache Tracking

| Field | Type | Description |
|-------|------|-------------|
| `cache_hit` | Boolean | Whether cache was used |
| `cache_key` | String | Cache lookup key |
| `prompt_prefix_hash` | String | For prefix caching detection |
| `compression_ratio` | Float | Prompt compression ratio |
| `compression_method` | String | Compression technique used |

### Routing Decision

| Field | Type | Description |
|-------|------|-------------|
| `chosen_model` | String | Model selected by router |
| `complexity_score` | Float | Task complexity (0-1) |

### Quality Evaluation

| Field | Type | Description |
|-------|------|-------------|
| `judge_score` | Float | Quality score (0-10) |
| `hallucination_flag` | Boolean | Detected hallucination |
| `confidence_score` | Float | Judge confidence (0-1) |
| `evidence_cited` | Boolean | Whether evidence was provided |
| `factual_error` | Boolean | Factual accuracy issue |
| `error_category` | String | Error classification |

### Error Tracking

| Field | Type | Description |
|-------|------|-------------|
| `success` | Boolean | Whether call succeeded |
| `error` | Text | Error message |
| `error_type` | String | RATE_LIMIT, TIMEOUT, INVALID_REQUEST, etc. |
| `error_code` | String | Provider error code (e.g., "429") |
| `retry_count` | Integer | Number of retries attempted |
| `is_retry` | Boolean | Is this call a retry |

### Experiment Tracking

| Field | Type | Description |
|-------|------|-------------|
| `experiment_id` | String | A/B test identifier |
| `control_group` | Boolean | Is baseline group |
| `prompt_variant_id` | String | Prompt version |
| `prompt_template_id` | String | Template identifier |
| `test_dataset_id` | String | Evaluation dataset |

### Business Attribution

| Field | Type | Description |
|-------|------|-------------|
| `business_outcome` | String | Conversion/outcome tracking |
| `conversion_event` | Boolean | ROI tracking flag |

### Compliance

| Field | Type | Description |
|-------|------|-------------|
| `contains_pii` | Boolean | GDPR compliance flag |
| `data_retention_days` | Integer | Auto-cleanup policy |
| `geographic_region` | String | Data residency |

### Observability

| Field | Type | Description |
|-------|------|-------------|
| `trace_id` | String | OpenTelemetry trace |
| `request_id` | String | Provider request ID |
| `environment` | String | dev, staging, prod |

---

## JSON Fields (Nested Objects)

These fields store detailed objects with additional metrics:

### routing_decision (JSON)

| Field | Type | Description |
|-------|------|-------------|
| `chosen_model` | String | Selected model |
| `alternative_models` | List | Other options considered |
| `model_scores` | Dict | Scores for each model |
| `reasoning` | String | Why this model was chosen |
| `rule_triggered` | String | Which routing rule fired |
| `complexity_score` | Float | Task complexity (0-1) |
| `estimated_cost_savings` | Float | Projected savings |
| `routing_strategy` | String | Strategy used |

### cache_metadata (JSON)

| Field | Type | Description |
|-------|------|-------------|
| `cache_hit` | Boolean | Hit or miss |
| `cache_key` | String | Lookup key |
| `cache_cluster_id` | String | Semantic cluster |
| `normalization_strategy` | String | How prompt was normalized |
| `similarity_score` | Float | Semantic match score (0-1) |
| `eviction_info` | String | Why entry was evicted |
| `cache_key_candidates` | List | Alternative keys considered |
| `dynamic_fields` | List | Fields excluded from cache key |
| `content_hash` | String | Prompt fingerprint |
| `ttl_seconds` | Integer | Time to live |

### quality_evaluation (JSON)

| Field | Type | Description |
|-------|------|-------------|
| `judge_score` | Float | Quality score (0-10) |
| `hallucination_flag` | Boolean | Detected hallucination |
| `error_category` | String | Error classification |
| `reasoning` | String | Judge's reasoning |
| `confidence_score` | Float | Confidence (0-1) |
| `judge_model` | String | Model used for judging |
| `failure_reason` | String | Why the call failed |
| `improvement_suggestion` | String | How to improve |
| `hallucination_details` | String | Specifics of hallucination |
| `evidence_cited` | Boolean | Whether evidence provided |
| `factual_error` | Boolean | Factual accuracy issue |
| `criteria_scores` | Dict | Per-criteria breakdown |

### prompt_breakdown (JSON)

| Field | Type | Description |
|-------|------|-------------|
| `system_prompt` | String | System prompt (truncated) |
| `system_prompt_tokens` | Integer | System prompt tokens |
| `user_message` | String | User message (truncated) |
| `user_message_tokens` | Integer | User message tokens |
| `chat_history` | List | Message history |
| `chat_history_tokens` | Integer | History tokens |
| `chat_history_count` | Integer | History message count |
| `conversation_context` | String | Memory state |
| `conversation_context_tokens` | Integer | Context tokens |
| `tool_definitions` | List | Function schemas |
| `tool_definitions_tokens` | Integer | Tool definition tokens |
| `tool_definitions_count` | Integer | Number of tools |
| `total_input_tokens` | Integer | Total input |
| `system_to_total_ratio` | Float | System % of total |
| `history_to_total_ratio` | Float | History % of total |
| `context_to_total_ratio` | Float | Context % of total |

### model_config (JSON)

| Field | Type | Description |
|-------|------|-------------|
| `temperature` | Float | Sampling temperature |
| `max_tokens` | Integer | Token limit |
| `top_p` | Float | Nucleus sampling |
| `frequency_penalty` | Float | Repetition penalty |
| `presence_penalty` | Float | Topic penalty |
| `stop_sequences` | List | Stop tokens |
| `response_format` | String | text or json_object |
| `seed` | Integer | For reproducibility |

### streaming_metrics (JSON)

| Field | Type | Description |
|-------|------|-------------|
| `is_streaming` | Boolean | Streaming enabled |
| `time_to_first_token_ms` | Float | Perceived latency |
| `stream_chunk_count` | Integer | Number of chunks |
| `stream_interrupted` | Boolean | Whether stream failed |
| `average_chunk_size` | Integer | Tokens per chunk |

### experiment_metadata (JSON)

| Field | Type | Description |
|-------|------|-------------|
| `experiment_id` | String | A/B test ID |
| `experiment_name` | String | Human-readable name |
| `variant_id` | String | Which variant (A, B, etc.) |
| `variant_name` | String | Variant description |
| `control_group` | Boolean | Is baseline |
| `start_date` | DateTime | Experiment start |
| `end_date` | DateTime | Experiment end |
| `sample_rate` | Float | % of traffic |
| `hypothesis` | String | What you're testing |
| `expected_improvement` | String | Target metric |
| `cohort` | String | User segment |
| `test_dataset_id` | String | Evaluation dataset |
| `baseline_cost` | Float | Baseline cost |
| `baseline_latency` | Float | Baseline latency |
| `baseline_quality` | Float | Baseline quality |

### error_details (JSON)

| Field | Type | Description |
|-------|------|-------------|
| `error_type` | String | Error category |
| `error_code` | String | Provider code |
| `retry_count` | Integer | Retry attempts |
| `retry_strategy` | String | Backoff strategy |
| `final_success` | Boolean | Did retry succeed |
| `error_details` | String | Full error message |

---

## Custom Metadata

You can store any additional data in the `metadata` field:

```python
track_llm_call(
    # ... standard fields
    metadata={
        "user_tier": "premium",
        "feature_flag": "new_prompt_v2",
        "request_source": "mobile_app",
        "custom_metric": 123.45,
    }
)
```

---

## Session-Level Metrics

The `sessions` table aggregates metrics across calls:

| Field | Type | Description |
|-------|------|-------------|
| `total_llm_calls` | Integer | Call count |
| `total_tokens` | Integer | Total tokens used |
| `total_cost` | Float | Total cost |
| `total_latency_ms` | Float | Total latency |
| `total_routing_decisions` | Integer | Routing decisions made |
| `routing_cost_savings` | Float | Savings from routing |
| `total_cache_hits` | Integer | Cache hits |
| `total_cache_misses` | Integer | Cache misses |
| `cache_cost_savings` | Float | Savings from caching |
| `avg_quality_score` | Float | Average quality |
| `total_hallucinations` | Integer | Hallucination count |
| `total_errors` | Integer | Error count |
