"""
Optimization Queue Service
Location: api/services/optimization_queue_service.py

Detects optimization opportunities across all stories.
Returns a unified list for the Optimization Queue dashboard.

Issue Detection:
- Latency: critical latency, large prompt/tool/output causing slowness, no max_tokens on critical
- Cache: repeated identical prompts (exact match)
- Cost: model overkill, expensive prompts, high-cost calls, tool bloat on premium
- Quality: low judge scores, errors, hallucinations, short responses
- Routing: model selection opportunities (upgrade/downgrade)
- Token: imbalanced ratios (20:1 warning, 50:1 critical), large prompts
- Prompt Composition: high system prompt %, large chat history, dynamic prompts, tool bloat
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta

from observatory.storage import ObservatoryStorage


# =============================================================================
# THRESHOLDS
# =============================================================================

# Latency thresholds (NEW: root-cause based)
LATENCY_CRITICAL_MS = 10000  # >10s = critical
LATENCY_HIGH_MS = 5000  # >5s = high latency
LATENCY_LARGE_PROMPT_TOKENS = 4000  # >4k tokens
LATENCY_LARGE_OUTPUT_TOKENS = 2000  # >2k completion tokens
LATENCY_TOOL_BLOAT_TOKENS = 1000  # >1k tool definition tokens

# Cache thresholds
CACHE_MIN_REPEATS = 3  # Min repeats to flag as cacheable

# Cost thresholds (NEW: expanded)
COST_OVERKILL_MODELS = ['gpt-4', 'gpt-4o', 'gpt-4-turbo', 'claude-3-opus', 'claude-3.5-sonnet', 'claude-3-sonnet']
COST_SIMPLE_MAX_TOKENS = 100  # If completion < 100 tokens, might be overkill
COST_EXPENSIVE_PROMPT_TOKENS = 4000  # >4k prompt tokens on premium model
COST_HIGH_SINGLE_CALL = 0.10  # Single call cost >$0.10
COST_TOOL_BLOAT_TOKENS = 1500  # >1.5k tool definition tokens on premium

# Quality thresholds (unchanged - working well)
QUALITY_LOW_SCORE = 7.0  # Judge score below 7 is concerning
QUALITY_CRITICAL_SCORE = 5.0  # Below 5 is critical

# Routing thresholds (unchanged - working well)
ROUTING_SIMPLE_TASK_MAX_TOKENS = 200  # Short output = maybe doesn't need premium

# Token thresholds (NEW: adjusted ratios)
TOKEN_IMBALANCED_WARNING_RATIO = 20.0  # >20:1 = warning (was 5:1)
TOKEN_IMBALANCED_CRITICAL_RATIO = 50.0  # >50:1 = critical
TOKEN_LARGE_PROMPT = 4000  # >4k tokens (was 2000)

# Prompt composition thresholds (NEW: added tool bloat)
PROMPT_SYSTEM_HIGH_PCT = 50.0  # System prompt > 50% of total is high
PROMPT_HISTORY_HIGH_PCT = 40.0  # Chat history > 40% is concerning
PROMPT_VARIABILITY_HIGH = 0.20  # >20% variation = dynamic (not cacheable)
PROMPT_TOOL_HIGH_TOKENS = 1000  # >1k tool definition tokens
PROMPT_TOOL_HIGH_PCT = 30.0  # >30% of prompt is tool definitions
PROMPT_TOOL_COUNT_BLOAT = 5  # >5 tools loaded simultaneously


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_tool_tokens(call) -> int:
    """Get tool definition tokens from call."""
    # Try direct column first
    tool_tokens = getattr(call, 'tool_definitions_tokens', 0) or 0
    if tool_tokens:
        return tool_tokens

    # Try prompt_breakdown JSON
    prompt_breakdown = getattr(call, 'prompt_breakdown', None)
    if isinstance(prompt_breakdown, dict):
        return prompt_breakdown.get('tool_definitions_tokens', 0) or 0

    return 0


def _get_tool_count(call) -> int:
    """Get number of tools from call."""
    # Try direct column
    tool_count = getattr(call, 'tool_count', 0) or 0
    if tool_count:
        return tool_count

    # Try tools JSON field
    tools = getattr(call, 'tools', None)
    if isinstance(tools, list):
        return len(tools)

    return 0


def _is_streaming(call) -> bool:
    """Check if call used streaming."""
    streaming_metrics = getattr(call, 'streaming_metrics', None)
    if streaming_metrics:
        if isinstance(streaming_metrics, dict):
            return streaming_metrics.get('is_streaming', False)
        if hasattr(streaming_metrics, 'is_streaming'):
            return streaming_metrics.is_streaming

    ttft = getattr(call, 'time_to_first_token_ms', None)
    if ttft and ttft > 0:
        return True

    return False


def _is_expensive_model(model_name: str) -> bool:
    """Check if model is an expensive tier."""
    if not model_name:
        return False
    model_lower = model_name.lower()
    return any(exp in model_lower for exp in [
        'gpt-4',
        'claude-3-opus',
        'claude-3.5-sonnet',
        'claude-3-sonnet',
        'claude-sonnet',
    ])


# =============================================================================
# ISSUE DETECTORS
# =============================================================================

def detect_latency_issues(calls: List[Any]) -> List[Dict]:
    """Detect latency-related optimization opportunities.

    NEW root-cause based detection:
    - Critical latency: >10s (1+ calls)
    - High latency + large prompt: >5s AND >4k tokens (3+ calls)
    - High latency + tool bloat: >5s AND >1k tool tokens (3+ calls)
    - High latency + large output: >5s AND >2k completion tokens (3+ calls)
    - No max_tokens on critical calls: >10s AND no max_tokens (1+ calls)
    """
    opportunities = []

    # Group by operation
    by_operation = defaultdict(list)
    for call in calls:
        agent = getattr(call, 'agent_name', None) or 'Unknown'
        operation = getattr(call, 'operation', None) or 'unknown'
        op_key = f"{agent}.{operation}"
        by_operation[op_key].append(call)

    for op_key, op_calls in by_operation.items():
        agent, operation = op_key.split('.', 1) if '.' in op_key else ('Unknown', op_key)

        # Detection 1: Critical latency (>10s) - only need 1+ calls
        critical_latency = [
            c for c in op_calls
            if (getattr(c, 'latency_ms', 0) or 0) > LATENCY_CRITICAL_MS
        ]
        if len(critical_latency) >= 1:
            avg_latency = sum(getattr(c, 'latency_ms', 0) or 0 for c in critical_latency) / len(critical_latency)
            avg_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in critical_latency) / len(critical_latency)

            opportunities.append({
                'id': f'latency-critical-{op_key}',
                'storyId': 'latency',
                'storyIcon': '🌐',
                'agent': agent,
                'operation': operation,
                'issue': f'Critical latency ({avg_latency/1000:.1f}s avg)',
                'impact': f'${avg_cost * len(critical_latency):.2f}',
                'impactValue': avg_cost * len(critical_latency),
                'effort': 'High',
                'callCount': len(critical_latency),
                'callId': critical_latency[0].id,
            })

        # Detection 2: High latency + large prompt (>5s AND >4k tokens)
        high_latency_large_prompt = [
            c for c in op_calls
            if (getattr(c, 'latency_ms', 0) or 0) > LATENCY_HIGH_MS
            and (getattr(c, 'prompt_tokens', 0) or 0) > LATENCY_LARGE_PROMPT_TOKENS
        ]
        if len(high_latency_large_prompt) >= 3:
            avg_latency = sum(getattr(c, 'latency_ms', 0) or 0 for c in high_latency_large_prompt) / len(high_latency_large_prompt)
            avg_prompt = sum(getattr(c, 'prompt_tokens', 0) or 0 for c in high_latency_large_prompt) / len(high_latency_large_prompt)
            total_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in high_latency_large_prompt)

            opportunities.append({
                'id': f'latency-large-prompt-{op_key}',
                'storyId': 'latency',
                'storyIcon': '🌐',
                'agent': agent,
                'operation': operation,
                'issue': f'Large prompt causing slowness ({avg_prompt:.0f} tokens, {avg_latency/1000:.1f}s)',
                'impact': f'${total_cost * 0.3:.2f}',
                'impactValue': total_cost * 0.3,
                'effort': 'Medium',
                'callCount': len(high_latency_large_prompt),
                'callId': high_latency_large_prompt[0].id,
            })

        # Detection 3: High latency + tool bloat (>5s AND >1k tool tokens)
        high_latency_tool_bloat = [
            c for c in op_calls
            if (getattr(c, 'latency_ms', 0) or 0) > LATENCY_HIGH_MS
            and _get_tool_tokens(c) > LATENCY_TOOL_BLOAT_TOKENS
        ]
        if len(high_latency_tool_bloat) >= 3:
            avg_latency = sum(getattr(c, 'latency_ms', 0) or 0 for c in high_latency_tool_bloat) / len(high_latency_tool_bloat)
            avg_tool_tokens = sum(_get_tool_tokens(c) for c in high_latency_tool_bloat) / len(high_latency_tool_bloat)
            total_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in high_latency_tool_bloat)

            opportunities.append({
                'id': f'latency-tool-bloat-{op_key}',
                'storyId': 'latency',
                'storyIcon': '🌐',
                'agent': agent,
                'operation': operation,
                'issue': f'Tool bloat causing slowness ({avg_tool_tokens:.0f} tool tokens, {avg_latency/1000:.1f}s)',
                'impact': f'${total_cost * 0.4:.2f}',
                'impactValue': total_cost * 0.4,
                'effort': 'Medium',
                'callCount': len(high_latency_tool_bloat),
                'callId': high_latency_tool_bloat[0].id,
            })

        # Detection 4: High latency + large output (>5s AND >2k completion tokens)
        high_latency_large_output = [
            c for c in op_calls
            if (getattr(c, 'latency_ms', 0) or 0) > LATENCY_HIGH_MS
            and (getattr(c, 'completion_tokens', 0) or 0) > LATENCY_LARGE_OUTPUT_TOKENS
        ]
        if len(high_latency_large_output) >= 3:
            avg_latency = sum(getattr(c, 'latency_ms', 0) or 0 for c in high_latency_large_output) / len(high_latency_large_output)
            avg_output = sum(getattr(c, 'completion_tokens', 0) or 0 for c in high_latency_large_output) / len(high_latency_large_output)
            total_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in high_latency_large_output)

            opportunities.append({
                'id': f'latency-large-output-{op_key}',
                'storyId': 'latency',
                'storyIcon': '🌐',
                'agent': agent,
                'operation': operation,
                'issue': f'Large output causing slowness ({avg_output:.0f} tokens, {avg_latency/1000:.1f}s)',
                'impact': f'${total_cost * 0.2:.2f}',
                'impactValue': total_cost * 0.2,
                'effort': 'Medium',
                'callCount': len(high_latency_large_output),
                'callId': high_latency_large_output[0].id,
            })

        # Detection 5: No max_tokens on critical calls (>10s AND no max_tokens)
        no_max_critical = [
            c for c in op_calls
            if (getattr(c, 'latency_ms', 0) or 0) > LATENCY_CRITICAL_MS
            and getattr(c, 'max_tokens', None) is None
        ]
        if len(no_max_critical) >= 1:
            avg_latency = sum(getattr(c, 'latency_ms', 0) or 0 for c in no_max_critical) / len(no_max_critical)
            avg_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in no_max_critical) / len(no_max_critical)

            opportunities.append({
                'id': f'latency-no-max-critical-{op_key}',
                'storyId': 'latency',
                'storyIcon': '🌐',
                'agent': agent,
                'operation': operation,
                'issue': f'No max_tokens on critical call ({avg_latency/1000:.1f}s)',
                'impact': f'${avg_cost * len(no_max_critical):.2f}',
                'impactValue': avg_cost * len(no_max_critical),
                'effort': 'Low',
                'callCount': len(no_max_critical),
                'callId': no_max_critical[0].id,
            })

    return opportunities


def detect_cache_issues(calls: List[Any]) -> List[Dict]:
    """Detect caching optimization opportunities.

    Unchanged - working well for current use case.
    """
    opportunities = []

    prompt_groups = defaultdict(list)
    for call in calls:
        cache_hit = False
        cache_metadata = getattr(call, 'cache_metadata', None)
        if cache_metadata:
            if isinstance(cache_metadata, dict):
                cache_hit = cache_metadata.get('cache_hit', False)
            elif hasattr(cache_metadata, 'cache_hit'):
                cache_hit = cache_metadata.cache_hit

        if cache_hit:
            continue

        prompt = getattr(call, 'prompt_normalized', None) or getattr(call, 'prompt', '') or ''
        system = getattr(call, 'system_prompt', '') or ''
        user = getattr(call, 'user_message', '') or ''

        key = prompt or f"{system}:{user}"
        if key and len(key) > 10:
            prompt_groups[key[:500]].append(call)

    for prompt_key, prompt_calls in prompt_groups.items():
        if len(prompt_calls) >= CACHE_MIN_REPEATS:
            sample = prompt_calls[0]
            agent = getattr(sample, 'agent_name', None) or 'Unknown'
            operation = getattr(sample, 'operation', None) or 'unknown'

            total_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in prompt_calls)
            savable_cost = total_cost - (getattr(prompt_calls[0], 'total_cost', 0) or 0)

            opportunities.append({
                'id': f'cache-repeat-{sample.id[:8]}',
                'storyId': 'cache',
                'storyIcon': '💾',
                'agent': agent,
                'operation': operation,
                'issue': f'{len(prompt_calls)}x exact repeat',
                'impact': f'${savable_cost:.2f}',
                'impactValue': savable_cost,
                'effort': 'Low',
                'callCount': len(prompt_calls),
                'callId': sample.id,
                'groupId': sample.id[:16],
            })

    return opportunities


def detect_cost_issues(calls: List[Any]) -> List[Dict]:
    """Detect cost optimization opportunities.

    NEW expanded detection:
    - Model overkill: Premium model + completion <100 tokens (5+ calls) - KEPT
    - Expensive prompts: Premium model + prompt >4k tokens (3+ calls) - NEW
    - High-cost calls: Single call cost >$0.10 (3+ calls) - NEW
    - Tool bloat on premium: tool_definitions >1.5k + premium model (3+ calls) - NEW
    """
    opportunities = []

    by_operation = defaultdict(list)
    for call in calls:
        agent = getattr(call, 'agent_name', None) or 'Unknown'
        operation = getattr(call, 'operation', None) or 'unknown'
        op_key = f"{agent}.{operation}"
        by_operation[op_key].append(call)

    for op_key, op_calls in by_operation.items():
        agent, operation = op_key.split('.', 1) if '.' in op_key else ('Unknown', op_key)

        # Detection 1: Model overkill (expensive model with low output) - KEPT
        overkill_calls = [
            c for c in op_calls
            if _is_expensive_model(getattr(c, 'model_name', None))
            and (getattr(c, 'completion_tokens', 0) or 0) < COST_SIMPLE_MAX_TOKENS
        ]
        if len(overkill_calls) >= 5:
            total_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in overkill_calls)
            potential_savings = total_cost * 0.7

            opportunities.append({
                'id': f'cost-overkill-{op_key}',
                'storyId': 'cost',
                'storyIcon': '💰',
                'agent': agent,
                'operation': operation,
                'issue': f'Model overkill ({getattr(overkill_calls[0], "model_name", "unknown")})',
                'impact': f'${potential_savings:.2f}',
                'impactValue': potential_savings,
                'effort': 'Medium',
                'callCount': len(overkill_calls),
                'callId': overkill_calls[0].id,
            })

        # Detection 2: Expensive prompts (premium model + large prompt) - NEW
        expensive_prompt_calls = [
            c for c in op_calls
            if _is_expensive_model(getattr(c, 'model_name', None))
            and (getattr(c, 'prompt_tokens', 0) or 0) > COST_EXPENSIVE_PROMPT_TOKENS
        ]
        if len(expensive_prompt_calls) >= 3:
            total_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in expensive_prompt_calls)
            avg_prompt = sum(getattr(c, 'prompt_tokens', 0) or 0 for c in expensive_prompt_calls) / len(expensive_prompt_calls)
            potential_savings = total_cost * 0.3  # 30% reduction by trimming prompts

            opportunities.append({
                'id': f'cost-expensive-prompt-{op_key}',
                'storyId': 'cost',
                'storyIcon': '💰',
                'agent': agent,
                'operation': operation,
                'issue': f'Expensive prompts ({avg_prompt:.0f} tokens on premium)',
                'impact': f'${potential_savings:.2f}',
                'impactValue': potential_savings,
                'effort': 'Medium',
                'callCount': len(expensive_prompt_calls),
                'callId': expensive_prompt_calls[0].id,
            })

        # Detection 3: High-cost calls (>$0.10 per call) - NEW
        high_cost_calls = [
            c for c in op_calls
            if (getattr(c, 'total_cost', 0) or 0) > COST_HIGH_SINGLE_CALL
        ]
        if len(high_cost_calls) >= 3:
            total_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in high_cost_calls)
            avg_cost = total_cost / len(high_cost_calls)
            potential_savings = total_cost * 0.4  # 40% potential reduction

            opportunities.append({
                'id': f'cost-high-calls-{op_key}',
                'storyId': 'cost',
                'storyIcon': '💰',
                'agent': agent,
                'operation': operation,
                'issue': f'High-cost calls (${avg_cost:.2f} avg per call)',
                'impact': f'${potential_savings:.2f}',
                'impactValue': potential_savings,
                'effort': 'High',
                'callCount': len(high_cost_calls),
                'callId': high_cost_calls[0].id,
            })

        # Detection 4: Tool bloat on premium model - NEW
        tool_bloat_premium = [
            c for c in op_calls
            if _is_expensive_model(getattr(c, 'model_name', None))
            and _get_tool_tokens(c) > COST_TOOL_BLOAT_TOKENS
        ]
        if len(tool_bloat_premium) >= 3:
            total_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in tool_bloat_premium)
            avg_tool_tokens = sum(_get_tool_tokens(c) for c in tool_bloat_premium) / len(tool_bloat_premium)
            potential_savings = total_cost * 0.35

            opportunities.append({
                'id': f'cost-tool-bloat-{op_key}',
                'storyId': 'cost',
                'storyIcon': '💰',
                'agent': agent,
                'operation': operation,
                'issue': f'Tool bloat on premium ({avg_tool_tokens:.0f} tool tokens)',
                'impact': f'${potential_savings:.2f}',
                'impactValue': potential_savings,
                'effort': 'Medium',
                'callCount': len(tool_bloat_premium),
                'callId': tool_bloat_premium[0].id,
            })

    return opportunities


def detect_quality_issues(calls: List[Any]) -> List[Dict]:
    """Detect quality optimization opportunities.

    Unchanged - working well (1.8% error rate, 7.4/10 avg score).
    """
    opportunities = []

    by_operation = defaultdict(list)
    for call in calls:
        agent = getattr(call, 'agent_name', None) or 'Unknown'
        operation = getattr(call, 'operation', None) or 'unknown'
        op_key = f"{agent}.{operation}"
        by_operation[op_key].append(call)

    for op_key, op_calls in by_operation.items():
        agent, operation = op_key.split('.', 1) if '.' in op_key else ('Unknown', op_key)

        # Detection 1: Low judge scores
        calls_with_scores = [c for c in op_calls if getattr(c, 'judge_score', None) is not None]
        low_quality = [c for c in calls_with_scores if getattr(c, 'judge_score', 10) < QUALITY_LOW_SCORE]
        critical_quality = [c for c in calls_with_scores if getattr(c, 'judge_score', 10) < QUALITY_CRITICAL_SCORE]

        if len(critical_quality) >= 2:
            avg_score = sum(getattr(c, 'judge_score', 0) for c in critical_quality) / len(critical_quality)
            opportunities.append({
                'id': f'quality-critical-{op_key}',
                'storyId': 'quality',
                'storyIcon': '⭐',
                'agent': agent,
                'operation': operation,
                'issue': f'Critical quality score ({avg_score:.1f}/10)',
                'impact': f'{len(critical_quality)} calls',
                'impactValue': len(critical_quality) * 0.1,
                'effort': 'High',
                'callCount': len(critical_quality),
                'callId': critical_quality[0].id,
            })
        elif len(low_quality) >= 3:
            avg_score = sum(getattr(c, 'judge_score', 0) for c in low_quality) / len(low_quality)
            opportunities.append({
                'id': f'quality-low-{op_key}',
                'storyId': 'quality',
                'storyIcon': '⭐',
                'agent': agent,
                'operation': operation,
                'issue': f'Low quality score ({avg_score:.1f}/10)',
                'impact': f'{len(low_quality)} calls',
                'impactValue': 0,
                'effort': 'Medium',
                'callCount': len(low_quality),
                'callId': low_quality[0].id,
            })

        # Detection 2: Error/failed calls
        error_calls = [
            c for c in op_calls
            if getattr(c, 'success', True) == False
            or getattr(c, 'success', True) == 0
            or (getattr(c, 'error', None) and len(str(getattr(c, 'error', ''))) > 0)
        ]
        if len(error_calls) >= 2:
            error_rate = len(error_calls) / len(op_calls) * 100
            opportunities.append({
                'id': f'quality-errors-{op_key}',
                'storyId': 'quality',
                'storyIcon': '⭐',
                'agent': agent,
                'operation': operation,
                'issue': f'High error rate ({error_rate:.0f}%)',
                'impact': f'{len(error_calls)} failed',
                'impactValue': len(error_calls) * 0.05,
                'effort': 'Medium',
                'callCount': len(error_calls),
                'callId': error_calls[0].id,
            })

        # Detection 3: Hallucination flags
        hallucination_calls = [
            c for c in op_calls
            if getattr(c, 'hallucination_flag', False) == True
            or getattr(c, 'hallucination_flag', False) == 1
        ]
        if len(hallucination_calls) >= 2:
            opportunities.append({
                'id': f'quality-hallucination-{op_key}',
                'storyId': 'quality',
                'storyIcon': '⭐',
                'agent': agent,
                'operation': operation,
                'issue': 'Hallucinations detected',
                'impact': f'{len(hallucination_calls)} calls',
                'impactValue': len(hallucination_calls) * 0.1,
                'effort': 'High',
                'callCount': len(hallucination_calls),
                'callId': hallucination_calls[0].id,
            })

        # Detection 4: Short responses (<50 tokens with significant input)
        short_responses = [
            c for c in op_calls
            if (getattr(c, 'completion_tokens', 0) or 0) < 50
            and (getattr(c, 'prompt_tokens', 0) or 0) > 100
        ]
        if len(short_responses) >= 3:
            opportunities.append({
                'id': f'quality-short-{op_key}',
                'storyId': 'quality',
                'storyIcon': '⭐',
                'agent': agent,
                'operation': operation,
                'issue': 'Short responses (<50 tokens)',
                'impact': f'{len(short_responses)} calls',
                'impactValue': 0,
                'effort': 'Low',
                'callCount': len(short_responses),
                'callId': short_responses[0].id,
            })

    return opportunities


def detect_routing_issues(calls: List[Any]) -> List[Dict]:
    """Detect routing optimization opportunities.

    Unchanged - working well (86% coverage, $1.20 saved).
    """
    opportunities = []

    by_operation = defaultdict(list)
    for call in calls:
        agent = getattr(call, 'agent_name', None) or 'Unknown'
        operation = getattr(call, 'operation', None) or 'unknown'
        op_key = f"{agent}.{operation}"
        by_operation[op_key].append(call)

    for op_key, op_calls in by_operation.items():
        agent, operation = op_key.split('.', 1) if '.' in op_key else ('Unknown', op_key)

        # Check for premium model on simple tasks (potential downgrade)
        downgrade_candidates = [
            c for c in op_calls
            if _is_expensive_model(getattr(c, 'model_name', None))
            and (getattr(c, 'completion_tokens', 0) or 0) < ROUTING_SIMPLE_TASK_MAX_TOKENS
        ]

        if len(downgrade_candidates) >= 3:
            total_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in downgrade_candidates)
            potential_savings = total_cost * 0.6

            opportunities.append({
                'id': f'routing-downgrade-{op_key}',
                'storyId': 'routing',
                'storyIcon': '🔀',
                'agent': agent,
                'operation': operation,
                'issue': f'Premium model for simple task ({getattr(downgrade_candidates[0], "model_name", "unknown")})',
                'impact': f'${potential_savings:.2f}',
                'impactValue': potential_savings,
                'effort': 'Medium',
                'callCount': len(downgrade_candidates),
                'callId': downgrade_candidates[0].id,
            })

        # Check for budget model on complex tasks (potential upgrade)
        upgrade_candidates = [
            c for c in op_calls
            if not _is_expensive_model(getattr(c, 'model_name', None))
            and (getattr(c, 'completion_tokens', 0) or 0) > 500
            and (
                (getattr(c, 'judge_score', None) is not None and getattr(c, 'judge_score', 10) < 6)
                or (getattr(c, 'completion_tokens', 0) or 0) > 1000
            )
        ]

        if len(upgrade_candidates) >= 3:
            opportunities.append({
                'id': f'routing-upgrade-{op_key}',
                'storyId': 'routing',
                'storyIcon': '🔀',
                'agent': agent,
                'operation': operation,
                'issue': 'Budget model may need upgrade (complex output)',
                'impact': 'Quality',
                'impactValue': 0,
                'effort': 'Medium',
                'callCount': len(upgrade_candidates),
                'callId': upgrade_candidates[0].id,
            })

    return opportunities


def detect_token_issues(calls: List[Any]) -> List[Dict]:
    """Detect token efficiency optimization opportunities.

    NEW adjusted thresholds:
    - Warning: Ratio >20:1 (was 5:1) → 3+ calls
    - Critical: Ratio >50:1 → 1+ calls
    - Large prompts: >4k tokens (was 2k) → 3+ calls
    """
    opportunities = []

    by_operation = defaultdict(list)
    for call in calls:
        agent = getattr(call, 'agent_name', None) or 'Unknown'
        operation = getattr(call, 'operation', None) or 'unknown'
        op_key = f"{agent}.{operation}"
        by_operation[op_key].append(call)

    for op_key, op_calls in by_operation.items():
        agent, operation = op_key.split('.', 1) if '.' in op_key else ('Unknown', op_key)

        # Calculate ratios for all calls with valid tokens
        calls_with_ratio = []
        for c in op_calls:
            prompt = getattr(c, 'prompt_tokens', 0) or 0
            completion = getattr(c, 'completion_tokens', 0) or 0
            if prompt > 100 and completion > 0:
                ratio = prompt / completion
                calls_with_ratio.append((c, ratio))

        # Detection 1: CRITICAL - Ratio >50:1 (only need 1+ calls)
        critical_imbalanced = [(c, r) for c, r in calls_with_ratio if r > TOKEN_IMBALANCED_CRITICAL_RATIO]
        if len(critical_imbalanced) >= 1:
            avg_ratio = sum(r for _, r in critical_imbalanced) / len(critical_imbalanced)
            total_cost = sum(getattr(c, 'total_cost', 0) or 0 for c, _ in critical_imbalanced)
            potential_savings = total_cost * 0.5  # 50% savings potential

            opportunities.append({
                'id': f'token-critical-imbalanced-{op_key}',
                'storyId': 'token',
                'storyIcon': '⚖️',
                'agent': agent,
                'operation': operation,
                'issue': f'Critical imbalance ({avg_ratio:.0f}:1 ratio)',
                'impact': f'${potential_savings:.2f}',
                'impactValue': potential_savings,
                'effort': 'High',
                'callCount': len(critical_imbalanced),
                'callId': critical_imbalanced[0][0].id,
            })

        # Detection 2: WARNING - Ratio >20:1 (need 3+ calls, exclude if already critical)
        elif len([c for c, r in calls_with_ratio if r > TOKEN_IMBALANCED_WARNING_RATIO]) >= 3:
            warning_imbalanced = [(c, r) for c, r in calls_with_ratio if r > TOKEN_IMBALANCED_WARNING_RATIO]
            avg_ratio = sum(r for _, r in warning_imbalanced) / len(warning_imbalanced)
            total_cost = sum(getattr(c, 'total_cost', 0) or 0 for c, _ in warning_imbalanced)
            potential_savings = total_cost * 0.3  # 30% savings potential

            opportunities.append({
                'id': f'token-imbalanced-{op_key}',
                'storyId': 'token',
                'storyIcon': '⚖️',
                'agent': agent,
                'operation': operation,
                'issue': f'Imbalanced ratio ({avg_ratio:.0f}:1 prompt:completion)',
                'impact': f'${potential_savings:.2f}',
                'impactValue': potential_savings,
                'effort': 'Medium',
                'callCount': len(warning_imbalanced),
                'callId': warning_imbalanced[0][0].id,
            })

        # Detection 3: Large prompts (>4k tokens)
        large_prompts = [
            c for c in op_calls
            if (getattr(c, 'prompt_tokens', 0) or 0) > TOKEN_LARGE_PROMPT
        ]

        if len(large_prompts) >= 3:
            avg_prompt = sum(getattr(c, 'prompt_tokens', 0) or 0 for c in large_prompts) / len(large_prompts)
            total_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in large_prompts)
            potential_savings = total_cost * 0.25

            opportunities.append({
                'id': f'token-large-prompt-{op_key}',
                'storyId': 'token',
                'storyIcon': '⚖️',
                'agent': agent,
                'operation': operation,
                'issue': f'Large prompts ({avg_prompt:.0f} avg tokens)',
                'impact': f'${potential_savings:.2f}',
                'impactValue': potential_savings,
                'effort': 'Medium',
                'callCount': len(large_prompts),
                'callId': large_prompts[0].id,
            })

    return opportunities


def detect_prompt_issues(calls: List[Any]) -> List[Dict]:
    """Detect prompt composition optimization opportunities.

    NEW expanded detection:
    - High system prompt: >50% of total → 5+ calls (KEPT)
    - Large chat history: >40% of prompt → 3+ calls (KEPT)
    - Dynamic system prompt: >20% variation → 3+ calls (KEPT)
    - High tool definitions: >1k tokens OR >30% of prompt → 3+ calls (NEW)
    - Tool count bloat: >5 tools loaded → 3+ calls (NEW)
    """
    opportunities = []

    by_operation = defaultdict(list)
    for call in calls:
        agent = getattr(call, 'agent_name', None) or 'Unknown'
        operation = getattr(call, 'operation', None) or 'unknown'
        op_key = f"{agent}.{operation}"
        by_operation[op_key].append(call)

    for op_key, op_calls in by_operation.items():
        agent, operation = op_key.split('.', 1) if '.' in op_key else ('Unknown', op_key)

        # Collect token breakdowns
        system_tokens_list = []
        user_tokens_list = []
        history_tokens_list = []
        tool_tokens_list = []
        tool_count_list = []
        prompt_tokens_list = []
        total_costs = []

        for call in op_calls:
            system_tokens = getattr(call, 'system_prompt_tokens', 0) or 0
            user_tokens = getattr(call, 'user_message_tokens', 0) or 0
            history_tokens = getattr(call, 'chat_history_tokens', 0) or 0
            tool_tokens = _get_tool_tokens(call)
            tool_count = _get_tool_count(call)
            prompt_tokens = getattr(call, 'prompt_tokens', 0) or 0

            # Try prompt_breakdown JSON if columns are empty
            if not system_tokens and not user_tokens:
                prompt_breakdown = getattr(call, 'prompt_breakdown', None)
                if isinstance(prompt_breakdown, dict):
                    system_tokens = prompt_breakdown.get('system_prompt_tokens', 0) or 0
                    user_tokens = prompt_breakdown.get('user_message_tokens', 0) or 0
                    history_tokens = prompt_breakdown.get('chat_history_tokens', 0) or 0

            system_tokens_list.append(system_tokens)
            user_tokens_list.append(user_tokens)
            history_tokens_list.append(history_tokens)
            tool_tokens_list.append(tool_tokens)
            tool_count_list.append(tool_count)
            prompt_tokens_list.append(prompt_tokens)
            total_costs.append(getattr(call, 'total_cost', 0) or 0)

        if not system_tokens_list:
            continue

        # Calculate averages
        avg_system = sum(system_tokens_list) / len(system_tokens_list)
        avg_user = sum(user_tokens_list) / len(user_tokens_list)
        avg_history = sum(history_tokens_list) / len(history_tokens_list)
        avg_tool = sum(tool_tokens_list) / len(tool_tokens_list)
        avg_tool_count = sum(tool_count_list) / len(tool_count_list)
        avg_prompt = sum(prompt_tokens_list) / len(prompt_tokens_list)
        total_avg = avg_system + avg_user + avg_history

        total_cost = sum(total_costs)

        # Detection 1: High system prompt percentage (KEPT)
        if total_avg > 0:
            system_pct = (avg_system / total_avg) * 100
            history_pct = (avg_history / total_avg) * 100

            high_system_calls = [
                c for i, c in enumerate(op_calls)
                if total_avg > 0 and system_tokens_list[i] > 0
                and (system_tokens_list[i] / (system_tokens_list[i] + user_tokens_list[i] + history_tokens_list[i] + 0.001)) > (PROMPT_SYSTEM_HIGH_PCT / 100)
            ]

            if len(high_system_calls) >= 5:
                potential_savings = total_cost * 0.15

                opportunities.append({
                    'id': f'prompt-high-system-{op_key}',
                    'storyId': 'system_prompt',
                    'storyIcon': '📝',
                    'agent': agent,
                    'operation': operation,
                    'issue': f'High system prompt ({system_pct:.0f}% of tokens)',
                    'impact': f'${potential_savings:.2f}',
                    'impactValue': potential_savings,
                    'effort': 'Medium',
                    'callCount': len(high_system_calls),
                    'callId': high_system_calls[0].id,
                })

            # Detection 2: Large chat history (KEPT)
            high_history_calls = [
                c for i, c in enumerate(op_calls)
                if history_tokens_list[i] > 0
                and total_avg > 0
                and (history_tokens_list[i] / (system_tokens_list[i] + user_tokens_list[i] + history_tokens_list[i] + 0.001)) > (PROMPT_HISTORY_HIGH_PCT / 100)
            ]

            if len(high_history_calls) >= 3:
                potential_savings = total_cost * 0.25

                opportunities.append({
                    'id': f'prompt-large-history-{op_key}',
                    'storyId': 'system_prompt',
                    'storyIcon': '📝',
                    'agent': agent,
                    'operation': operation,
                    'issue': f'Large chat history ({history_pct:.0f}% of tokens)',
                    'impact': f'${potential_savings:.2f}',
                    'impactValue': potential_savings,
                    'effort': 'Low',
                    'callCount': len(high_history_calls),
                    'callId': high_history_calls[0].id,
                })

        # Detection 3: Dynamic system prompts (KEPT)
        if len(system_tokens_list) >= 2 and avg_system > 0:
            variance = sum((x - avg_system) ** 2 for x in system_tokens_list) / len(system_tokens_list)
            std = variance ** 0.5
            system_variability = std / avg_system
        else:
            system_variability = 0

        if avg_system > 100 and system_variability > PROMPT_VARIABILITY_HIGH and len(op_calls) >= 3:
            opportunities.append({
                'id': f'prompt-dynamic-system-{op_key}',
                'storyId': 'system_prompt',
                'storyIcon': '📝',
                'agent': agent,
                'operation': operation,
                'issue': f'Dynamic system prompt ({system_variability*100:.0f}% variation)',
                'impact': 'Cache blocked',
                'impactValue': total_cost * 0.1,
                'effort': 'High',
                'callCount': len(op_calls),
                'callId': op_calls[0].id,
            })

        # Detection 4: High tool definitions (NEW) - >1k tokens OR >30% of prompt
        if avg_prompt > 0:
            tool_pct = (avg_tool / avg_prompt) * 100 if avg_prompt > 0 else 0

            high_tool_calls = [
                c for i, c in enumerate(op_calls)
                if tool_tokens_list[i] > PROMPT_TOOL_HIGH_TOKENS
                or (prompt_tokens_list[i] > 0 and (tool_tokens_list[i] / prompt_tokens_list[i]) > (PROMPT_TOOL_HIGH_PCT / 100))
            ]

            if len(high_tool_calls) >= 3:
                potential_savings = total_cost * 0.35

                opportunities.append({
                    'id': f'prompt-tool-bloat-{op_key}',
                    'storyId': 'system_prompt',
                    'storyIcon': '📝',
                    'agent': agent,
                    'operation': operation,
                    'issue': f'Tool bloat ({avg_tool:.0f} tokens, {tool_pct:.0f}% of prompt)',
                    'impact': f'${potential_savings:.2f}',
                    'impactValue': potential_savings,
                    'effort': 'Medium',
                    'callCount': len(high_tool_calls),
                    'callId': high_tool_calls[0].id,
                })

        # Detection 5: Tool count bloat (NEW) - >5 tools loaded
        high_tool_count_calls = [
            c for i, c in enumerate(op_calls)
            if tool_count_list[i] > PROMPT_TOOL_COUNT_BLOAT
        ]

        if len(high_tool_count_calls) >= 3:
            potential_savings = total_cost * 0.2

            opportunities.append({
                'id': f'prompt-tool-count-{op_key}',
                'storyId': 'system_prompt',
                'storyIcon': '📝',
                'agent': agent,
                'operation': operation,
                'issue': f'Too many tools loaded ({avg_tool_count:.0f} tools)',
                'impact': f'${potential_savings:.2f}',
                'impactValue': potential_savings,
                'effort': 'Low',
                'callCount': len(high_tool_count_calls),
                'callId': high_tool_count_calls[0].id,
            })

    return opportunities


# =============================================================================
# MAIN SERVICE FUNCTION
# =============================================================================

def get_optimization_opportunities(
    project: Optional[str] = None,
    days: int = 7,
    story_filter: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Get all optimization opportunities across all stories.

    Args:
        project: Optional project filter
        days: Number of days to analyze
        story_filter: Optional story ID to filter by (latency, cache, cost, quality, routing, token, system_prompt)
        limit: Max opportunities to return

    Returns:
        Dict with opportunities list and summary stats
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)

    calls = ObservatoryStorage.get_llm_calls(
        project_name=project,
        start_time=start_time,
        end_time=end_time,
        limit=5000,
    )

    if not calls:
        return {
            'opportunities': [],
            'summary': {
                'total': 0,
                'totalSavings': 0,
                'quickWins': 0,
                'byStory': {},
            }
        }

    all_opportunities = []

    if not story_filter or story_filter == 'latency':
        all_opportunities.extend(detect_latency_issues(calls))

    if not story_filter or story_filter == 'cache':
        all_opportunities.extend(detect_cache_issues(calls))

    if not story_filter or story_filter == 'cost':
        all_opportunities.extend(detect_cost_issues(calls))

    if not story_filter or story_filter == 'quality':
        all_opportunities.extend(detect_quality_issues(calls))

    if not story_filter or story_filter == 'routing':
        all_opportunities.extend(detect_routing_issues(calls))

    if not story_filter or story_filter == 'token':
        all_opportunities.extend(detect_token_issues(calls))

    if not story_filter or story_filter == 'system_prompt':
        all_opportunities.extend(detect_prompt_issues(calls))

    # Sort by impact (descending)
    all_opportunities.sort(key=lambda x: x['impactValue'], reverse=True)

    # Limit results
    opportunities = all_opportunities[:limit]

    # Calculate summary
    total_savings = sum(o['impactValue'] for o in opportunities)
    quick_wins = len([o for o in opportunities if o['effort'] == 'Low'])

    by_story = {}
    for opp in opportunities:
        story = opp['storyId']
        if story not in by_story:
            by_story[story] = 0
        by_story[story] += 1

    return {
        'opportunities': opportunities,
        'summary': {
            'total': len(opportunities),
            'totalSavings': round(total_savings, 2),
            'quickWins': quick_wins,
            'byStory': by_story,
        }
    }
