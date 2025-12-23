"""
Optimization Queue Service
Location: api/services/optimization_queue_service.py

Detects optimization opportunities across all stories.
Returns a unified list for the Optimization Queue dashboard.

Issue Detection:
- Latency: no max_tokens, high completion tokens, no streaming, large history
- Cache: repeated identical prompts (exact match)
- Cost: model overkill (expensive model for simple task)
- Quality: low judge scores, errors, hallucinations, short responses
- Routing: model selection opportunities (upgrade/downgrade)
- Token: imbalanced ratios, large prompts
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta

from observatory.storage import ObservatoryStorage


# =============================================================================
# THRESHOLDS
# =============================================================================

# Latency thresholds
LATENCY_HIGH_COMPLETION_TOKENS = 800
LATENCY_NO_MAX_TOKENS_MIN_COMPLETION = 300
LATENCY_LARGE_HISTORY_RATIO = 0.5  # History > 50% of prompt
LATENCY_SLOW_MS = 5000

# Cache thresholds
CACHE_MIN_REPEATS = 3  # Min repeats to flag as cacheable

# Cost thresholds
COST_OVERKILL_MODELS = ['gpt-4', 'gpt-4o', 'gpt-4-turbo', 'claude-3-opus']
COST_SIMPLE_MAX_TOKENS = 100  # If completion < 100 tokens, might be overkill

# Quality thresholds
QUALITY_LOW_SCORE = 7.0  # Judge score below 7 is concerning (room for improvement)
QUALITY_CRITICAL_SCORE = 5.0  # Below 5 is critical

# Routing thresholds
ROUTING_SIMPLE_TASK_MAX_TOKENS = 200  # Short output = maybe doesn't need premium

# Token thresholds
TOKEN_IMBALANCED_RATIO = 5.0  # Prompt:completion ratio > 5:1 is imbalanced
TOKEN_HIGH_PROMPT = 2000  # Prompts over 2000 tokens


# =============================================================================
# ISSUE DETECTORS
# =============================================================================

def detect_latency_issues(calls: List[Any]) -> List[Dict]:
    """Detect latency-related optimization opportunities."""
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
        
        # Check for no max_tokens with high completion
        no_max_token_calls = [
            c for c in op_calls 
            if getattr(c, 'max_tokens', None) is None 
            and (getattr(c, 'completion_tokens', 0) or 0) > LATENCY_NO_MAX_TOKENS_MIN_COMPLETION
        ]
        if no_max_token_calls:
            avg_completion = sum(getattr(c, 'completion_tokens', 0) or 0 for c in no_max_token_calls) / len(no_max_token_calls)
            avg_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in no_max_token_calls) / len(no_max_token_calls)
            
            opportunities.append({
                'id': f'latency-no-max-{op_key}',
                'storyId': 'latency',
                'storyIcon': '🌐',
                'agent': agent,
                'operation': operation,
                'issue': f'No max_tokens ({avg_completion:.0f} avg tokens)',
                'impact': f'${avg_cost * len(no_max_token_calls):.2f}',
                'impactValue': avg_cost * len(no_max_token_calls),
                'effort': 'Low',
                'callCount': len(no_max_token_calls),
                'callId': no_max_token_calls[0].id,
            })
        
        # Check for no streaming on slow calls
        no_stream_slow = [
            c for c in op_calls 
            if not _is_streaming(c) and (getattr(c, 'latency_ms', 0) or 0) > LATENCY_SLOW_MS
        ]
        if len(no_stream_slow) >= 3:
            avg_latency = sum(getattr(c, 'latency_ms', 0) or 0 for c in no_stream_slow) / len(no_stream_slow)
            
            opportunities.append({
                'id': f'latency-no-stream-{op_key}',
                'storyId': 'latency',
                'storyIcon': '🌐',
                'agent': agent,
                'operation': operation,
                'issue': f'Streaming disabled ({avg_latency/1000:.1f}s avg)',
                'impact': f'{avg_latency/1000:.1f}s perceived',
                'impactValue': avg_latency / 1000 * 0.1,
                'effort': 'Medium',
                'callCount': len(no_stream_slow),
                'callId': no_stream_slow[0].id,
            })
        
        # Check for large chat history
        large_history = [
            c for c in op_calls 
            if (getattr(c, 'chat_history_tokens', 0) or 0) > (getattr(c, 'prompt_tokens', 1) or 1) * LATENCY_LARGE_HISTORY_RATIO
        ]
        if len(large_history) >= 3:
            avg_history_pct = sum(
                (getattr(c, 'chat_history_tokens', 0) or 0) / (getattr(c, 'prompt_tokens', 1) or 1) * 100 
                for c in large_history
            ) / len(large_history)
            avg_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in large_history) / len(large_history)
            
            opportunities.append({
                'id': f'latency-history-{op_key}',
                'storyId': 'latency',
                'storyIcon': '🌐',
                'agent': agent,
                'operation': operation,
                'issue': f'Large history ({avg_history_pct:.0f}% of prompt)',
                'impact': f'${avg_cost * len(large_history) * 0.4:.2f}',
                'impactValue': avg_cost * len(large_history) * 0.4,
                'effort': 'Low',
                'callCount': len(large_history),
                'callId': large_history[0].id,
            })
    
    return opportunities


def detect_cache_issues(calls: List[Any]) -> List[Dict]:
    """Detect caching optimization opportunities."""
    opportunities = []
    
    # Group by normalized prompt (or system_prompt + user_message)
    prompt_groups = defaultdict(list)
    for call in calls:
        # Skip cache hits - check cache_metadata JSON
        cache_hit = False
        cache_metadata = getattr(call, 'cache_metadata', None)
        if cache_metadata:
            if isinstance(cache_metadata, dict):
                cache_hit = cache_metadata.get('cache_hit', False)
            elif hasattr(cache_metadata, 'cache_hit'):
                cache_hit = cache_metadata.cache_hit
        
        if cache_hit:
            continue
        
        # Use prompt_normalized if available, else use prompt or system+user
        prompt = getattr(call, 'prompt_normalized', None) or getattr(call, 'prompt', '') or ''
        system = getattr(call, 'system_prompt', '') or ''
        user = getattr(call, 'user_message', '') or ''
        
        key = prompt or f"{system}:{user}"
        if key and len(key) > 10:  # Ignore empty/tiny prompts
            prompt_groups[key[:500]].append(call)  # Truncate for grouping
    
    # Find repeated prompts
    for prompt_key, prompt_calls in prompt_groups.items():
        if len(prompt_calls) >= CACHE_MIN_REPEATS:
            # Get representative call
            sample = prompt_calls[0]
            agent = getattr(sample, 'agent_name', None) or 'Unknown'
            operation = getattr(sample, 'operation', None) or 'unknown'
            
            total_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in prompt_calls)
            # First call is necessary, rest could be cached
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
                'groupId': sample.id[:16],  # For cache story navigation
            })
    
    return opportunities


def detect_cost_issues(calls: List[Any]) -> List[Dict]:
    """Detect cost optimization opportunities (model overkill)."""
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
        
        # Check for expensive model with low output
        overkill_calls = [
            c for c in op_calls 
            if _is_expensive_model(getattr(c, 'model_name', None))
            and (getattr(c, 'completion_tokens', 0) or 0) < COST_SIMPLE_MAX_TOKENS
        ]
        if len(overkill_calls) >= 5:
            avg_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in overkill_calls) / len(overkill_calls)
            total_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in overkill_calls)
            
            # Estimate savings if using cheaper model (70% reduction)
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
    
    return opportunities


def detect_quality_issues(calls: List[Any]) -> List[Dict]:
    """Detect quality optimization opportunities.
    
    Uses direct columns from schema:
    - judge_score (FLOAT)
    - hallucination_flag (BOOLEAN)
    - success (BOOLEAN)
    - error (TEXT)
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
        
        # Detection 1: Low judge scores (use getattr for safety)
        calls_with_scores = [c for c in op_calls if getattr(c, 'judge_score', None) is not None]
        low_quality = [c for c in calls_with_scores if getattr(c, 'judge_score', 10) < QUALITY_LOW_SCORE]
        critical_quality = [c for c in calls_with_scores if getattr(c, 'judge_score', 10) < QUALITY_CRITICAL_SCORE]
        
        if len(critical_quality) >= 2:
            avg_score = sum(getattr(c, 'judge_score', 0) for c in critical_quality) / len(critical_quality)
            opportunities.append({
                'id': f'quality-critical-{op_key}',
                'storyId': 'quality',
                'storyIcon': '📊',
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
                'storyIcon': '📊',
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
                'storyIcon': '📊',
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
                'storyIcon': '📊',
                'agent': agent,
                'operation': operation,
                'issue': 'Hallucinations detected',
                'impact': f'{len(hallucination_calls)} calls',
                'impactValue': len(hallucination_calls) * 0.1,
                'effort': 'High',
                'callCount': len(hallucination_calls),
                'callId': hallucination_calls[0].id,
            })
        
        # Detection 4: Very short responses
        short_responses = [
            c for c in op_calls 
            if (getattr(c, 'completion_tokens', 0) or 0) < 10 
            and (getattr(c, 'prompt_tokens', 0) or 0) > 100
        ]
        if len(short_responses) >= 3:
            opportunities.append({
                'id': f'quality-short-{op_key}',
                'storyId': 'quality',
                'storyIcon': '📊',
                'agent': agent,
                'operation': operation,
                'issue': 'Unusually short responses (<10 tokens)',
                'impact': f'{len(short_responses)} calls',
                'impactValue': 0,
                'effort': 'Low',
                'callCount': len(short_responses),
                'callId': short_responses[0].id,
            })
    
    return opportunities


def detect_routing_issues(calls: List[Any]) -> List[Dict]:
    """Detect routing optimization opportunities (model selection)."""
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
        
        # Check for premium model on simple tasks (potential downgrade)
        downgrade_candidates = [
            c for c in op_calls 
            if _is_expensive_model(getattr(c, 'model_name', None))
            and (getattr(c, 'completion_tokens', 0) or 0) < ROUTING_SIMPLE_TASK_MAX_TOKENS
        ]
        
        if len(downgrade_candidates) >= 3:
            total_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in downgrade_candidates)
            # Estimate 60% savings by downgrading
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
    """Detect token efficiency optimization opportunities."""
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
        
        # Check for imbalanced prompt:completion ratio (too much input for output)
        imbalanced = [
            c for c in op_calls 
            if (getattr(c, 'prompt_tokens', 0) or 0) > 100 
            and (getattr(c, 'completion_tokens', 1) or 1) > 0
            and (getattr(c, 'prompt_tokens', 0) or 0) / (getattr(c, 'completion_tokens', 1) or 1) > TOKEN_IMBALANCED_RATIO
        ]
        
        if len(imbalanced) >= 3:
            avg_ratio = sum(
                (getattr(c, 'prompt_tokens', 0) or 0) / (getattr(c, 'completion_tokens', 1) or 1) 
                for c in imbalanced
            ) / len(imbalanced)
            avg_prompt_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in imbalanced) * 0.6 / len(imbalanced)
            # Estimate 30% of prompt cost could be saved with optimization
            potential_savings = avg_prompt_cost * len(imbalanced) * 0.3
            
            opportunities.append({
                'id': f'token-imbalanced-{op_key}',
                'storyId': 'token',
                'storyIcon': '🔢',
                'agent': agent,
                'operation': operation,
                'issue': f'Imbalanced ratio ({avg_ratio:.1f}:1 prompt:completion)',
                'impact': f'${potential_savings:.2f}',
                'impactValue': potential_savings,
                'effort': 'Medium',
                'callCount': len(imbalanced),
                'callId': imbalanced[0].id,
            })
        
        # Check for very large prompts
        large_prompts = [
            c for c in op_calls 
            if (getattr(c, 'prompt_tokens', 0) or 0) > TOKEN_HIGH_PROMPT
        ]
        
        if len(large_prompts) >= 3:
            avg_prompt = sum(getattr(c, 'prompt_tokens', 0) or 0 for c in large_prompts) / len(large_prompts)
            total_cost = sum(getattr(c, 'total_cost', 0) or 0 for c in large_prompts)
            # Estimate 20% savings by reducing prompt size
            potential_savings = total_cost * 0.2
            
            opportunities.append({
                'id': f'token-large-prompt-{op_key}',
                'storyId': 'token',
                'storyIcon': '🔢',
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


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _is_streaming(call) -> bool:
    """Check if call used streaming."""
    # Check streaming_metrics JSON if available
    streaming_metrics = getattr(call, 'streaming_metrics', None)
    if streaming_metrics:
        if isinstance(streaming_metrics, dict):
            return streaming_metrics.get('is_streaming', False)
        if hasattr(streaming_metrics, 'is_streaming'):
            return streaming_metrics.is_streaming
    
    # Check time_to_first_token as indicator (direct column)
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
        story_filter: Optional story ID to filter by (latency, cache, cost, quality, routing, token)
        limit: Max opportunities to return
    
    Returns:
        Dict with opportunities list and summary stats
    """
    # Fetch calls
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    calls = ObservatoryStorage.get_llm_calls(
        project_name=project,
        start_time=start_time,
        end_time=end_time,
        limit=5000,  # Analyze more calls for better detection
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
    
    # Detect issues from each story
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