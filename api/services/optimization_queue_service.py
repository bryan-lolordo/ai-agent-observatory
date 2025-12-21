"""
Optimization Queue Service
Location: api/services/optimization_queue_service.py

Detects optimization opportunities across all stories.
Returns a unified list for the Optimization Queue dashboard.

Issue Detection:
- Latency: no max_tokens, high completion tokens, no streaming, large history
- Cache: repeated identical prompts (exact match)
- Cost: model overkill (expensive model for simple task)
- Quality: low judge scores
- Routing: missed routing opportunities
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
QUALITY_LOW_SCORE = 5.0  # Judge score below 5 is concerning


# =============================================================================
# ISSUE DETECTORS
# =============================================================================

def detect_latency_issues(calls: List[Any]) -> List[Dict]:
    """Detect latency-related optimization opportunities."""
    opportunities = []
    
    # Group by operation
    by_operation = defaultdict(list)
    for call in calls:
        op_key = f"{call.agent_name or 'Unknown'}.{call.operation or 'unknown'}"
        by_operation[op_key].append(call)
    
    for op_key, op_calls in by_operation.items():
        agent, operation = op_key.split('.', 1) if '.' in op_key else ('Unknown', op_key)
        
        # Check for no max_tokens with high completion
        no_max_token_calls = [
            c for c in op_calls 
            if c.max_tokens is None 
            and (c.completion_tokens or 0) > LATENCY_NO_MAX_TOKENS_MIN_COMPLETION
        ]
        if no_max_token_calls:
            avg_completion = sum(c.completion_tokens or 0 for c in no_max_token_calls) / len(no_max_token_calls)
            avg_cost = sum(c.total_cost or 0 for c in no_max_token_calls) / len(no_max_token_calls)
            
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
                'callId': no_max_token_calls[0].id,  # First call for drill-down
            })
        
        # Check for no streaming on slow calls
        no_stream_slow = [
            c for c in op_calls 
            if not _is_streaming(c) and (c.latency_ms or 0) > LATENCY_SLOW_MS
        ]
        if len(no_stream_slow) >= 3:
            avg_latency = sum(c.latency_ms or 0 for c in no_stream_slow) / len(no_stream_slow)
            
            opportunities.append({
                'id': f'latency-no-stream-{op_key}',
                'storyId': 'latency',
                'storyIcon': '🌐',
                'agent': agent,
                'operation': operation,
                'issue': f'Streaming disabled ({avg_latency/1000:.1f}s avg)',
                'impact': f'{avg_latency/1000:.1f}s perceived',
                'impactValue': avg_latency / 1000 * 0.1,  # Convert to $ equivalent
                'effort': 'Medium',
                'callCount': len(no_stream_slow),
                'callId': no_stream_slow[0].id,
            })
        
        # Check for large chat history
        large_history = [
            c for c in op_calls 
            if (c.chat_history_tokens or 0) > (c.prompt_tokens or 1) * LATENCY_LARGE_HISTORY_RATIO
        ]
        if len(large_history) >= 3:
            avg_history_pct = sum(
                (c.chat_history_tokens or 0) / (c.prompt_tokens or 1) * 100 
                for c in large_history
            ) / len(large_history)
            avg_cost = sum(c.total_cost or 0 for c in large_history) / len(large_history)
            
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
        # Skip cache hits - check cache_metadata
        cache_hit = False
        if call.cache_metadata:
            if hasattr(call.cache_metadata, 'cache_hit'):
                cache_hit = call.cache_metadata.cache_hit
            elif isinstance(call.cache_metadata, dict):
                cache_hit = call.cache_metadata.get('cache_hit', False)
        
        if cache_hit:
            continue
            
        # Use prompt_normalized if available, else hash system+user
        prompt = getattr(call, 'prompt_normalized', None) or call.prompt or ''
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
            agent = sample.agent_name or 'Unknown'
            operation = sample.operation or 'unknown'
            
            total_cost = sum(c.total_cost or 0 for c in prompt_calls)
            # First call is necessary, rest could be cached
            savable_cost = total_cost - (prompt_calls[0].total_cost or 0)
            
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
                'patternId': f'pattern-{sample.id[:8]}',  # For cache story navigation
            })
    
    return opportunities


def detect_cost_issues(calls: List[Any]) -> List[Dict]:
    """Detect cost optimization opportunities (model overkill)."""
    opportunities = []
    
    # Group by operation
    by_operation = defaultdict(list)
    for call in calls:
        op_key = f"{call.agent_name or 'Unknown'}.{call.operation or 'unknown'}"
        by_operation[op_key].append(call)
    
    for op_key, op_calls in by_operation.items():
        agent, operation = op_key.split('.', 1) if '.' in op_key else ('Unknown', op_key)
        
        # Check for expensive model with low output
        overkill_calls = [
            c for c in op_calls 
            if _is_expensive_model(c.model_name)
            and (c.completion_tokens or 0) < COST_SIMPLE_MAX_TOKENS
        ]
        if len(overkill_calls) >= 5:  # Need enough samples
            avg_cost = sum(c.total_cost or 0 for c in overkill_calls) / len(overkill_calls)
            total_cost = sum(c.total_cost or 0 for c in overkill_calls)
            
            # Estimate savings if using cheaper model (70% reduction)
            potential_savings = total_cost * 0.7
            
            opportunities.append({
                'id': f'cost-overkill-{op_key}',
                'storyId': 'cost',
                'storyIcon': '💰',
                'agent': agent,
                'operation': operation,
                'issue': f'Model overkill ({overkill_calls[0].model_name})',
                'impact': f'${potential_savings:.2f}',
                'impactValue': potential_savings,
                'effort': 'Medium',
                'callCount': len(overkill_calls),
                'callId': overkill_calls[0].id,
            })
    
    return opportunities


def detect_quality_issues(calls: List[Any]) -> List[Dict]:
    """Detect quality optimization opportunities."""
    opportunities = []
    
    # Group by operation
    by_operation = defaultdict(list)
    for call in calls:
        # Get judge_score from quality_evaluation
        judge_score = None
        if call.quality_evaluation:
            if hasattr(call.quality_evaluation, 'judge_score'):
                judge_score = call.quality_evaluation.judge_score
            elif isinstance(call.quality_evaluation, dict):
                judge_score = call.quality_evaluation.get('judge_score')
        
        if judge_score is not None:
            op_key = f"{call.agent_name or 'Unknown'}.{call.operation or 'unknown'}"
            # Store score with call for later use
            call._judge_score = judge_score
            by_operation[op_key].append(call)
    
    for op_key, op_calls in by_operation.items():
        agent, operation = op_key.split('.', 1) if '.' in op_key else ('Unknown', op_key)
        
        # Check for low quality scores
        low_quality = [c for c in op_calls if (getattr(c, '_judge_score', 10) or 10) < QUALITY_LOW_SCORE]
        
        if len(low_quality) >= 3:
            avg_score = sum(getattr(c, '_judge_score', 0) or 0 for c in low_quality) / len(low_quality)
            
            opportunities.append({
                'id': f'quality-low-{op_key}',
                'storyId': 'quality',
                'storyIcon': '📊',
                'agent': agent,
                'operation': operation,
                'issue': f'Low quality score ({avg_score:.1f}/10)',
                'impact': f'{len(low_quality)} calls',
                'impactValue': 0,
                'effort': 'High',
                'callCount': len(low_quality),
                'callId': low_quality[0].id,
            })
    
    return opportunities


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _is_streaming(call) -> bool:
    """Check if call used streaming."""
    # Check streaming_metrics if available
    if call.streaming_metrics:
        if hasattr(call.streaming_metrics, 'is_streaming'):
            return call.streaming_metrics.is_streaming
        if isinstance(call.streaming_metrics, dict):
            return call.streaming_metrics.get('is_streaming', False)
    
    # Check time_to_first_token as indicator
    if call.time_to_first_token_ms and call.time_to_first_token_ms > 0:
        return True
    
    return False


def _is_expensive_model(model_name: str) -> bool:
    """Check if model is an expensive tier."""
    if not model_name:
        return False
    model_lower = model_name.lower()
    return any(exp in model_lower for exp in ['gpt-4', 'claude-3-opus', 'claude-3.5-sonnet'])


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
        story_filter: Optional story ID to filter by (latency, cache, cost, quality)
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