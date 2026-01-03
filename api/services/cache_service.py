"""
Cache Service - Story 2 Business Logic
Location: api/services/cache_service.py

Handles cache opportunity analysis with 4 cache types:
- 🎯 Exact Match: Identical prompts
- 📌 Stable/Prefix: Large system prompt (>50% of tokens)
- 💎 High-Value: Expensive or slow calls worth caching
- 🧠 Semantic: Similar meaning (future - requires embeddings)

Returns proper response models for Layer 1, 2, and 3.
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import hashlib

from api.models import CacheStoryResponse, CacheSummary, TopOffender
from api.config.story_definitions import get_story_recommendations
from api.utils.formatters import format_cost, format_percentage


# =============================================================================
# THRESHOLDS
# =============================================================================

THRESHOLDS = {
    # Minimum repeats to be considered a cache opportunity
    "min_repeats": 2,
    
    # Redundancy percentage to flag operation
    "redundancy_warning": 0.20,  # 20%
    "redundancy_critical": 0.50,  # 50%
    
    # Stable/Prefix detection: system prompt > X% of total prompt tokens
    "stable_system_ratio": 0.50,  # 50%
    
    # High-Value detection
    "high_value_cost": 0.03,      # $0.03 per call
    "high_value_latency": 3000,   # 3 seconds
}


# Cache type definitions
CACHE_TYPES = {
    "exact": {
        "id": "exact",
        "name": "Exact Match",
        "emoji": "🎯",
        "effort": "low",
        "description": "Identical prompts returning identical responses",
    },
    "stable": {
        "id": "stable",
        "name": "Stable/Prefix",
        "emoji": "📌",
        "effort": "low",
        "description": "Large system prompt that rarely changes",
    },
    "high_value": {
        "id": "high_value",
        "name": "High-Value",
        "emoji": "💎",
        "effort": "medium",
        "description": "Expensive or slow calls worth caching",
    },
    "semantic": {
        "id": "semantic",
        "name": "Semantic",
        "emoji": "🧠",
        "effort": "high",
        "description": "Similar meaning, different wording (coming soon)",
    },
    "none": {
        "id": "none",
        "name": "None",
        "emoji": "—",
        "effort": "none",
        "description": "No caching opportunity detected",
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _normalize_prompt(prompt: str) -> str:
    """Normalize prompt for comparison."""
    if not prompt:
        return ""
    return ' '.join(prompt.lower().strip().split())


def _hash_prompt(prompt: str) -> str:
    """Create hash of normalized prompt."""
    normalized = _normalize_prompt(prompt)
    return hashlib.md5(normalized.encode()).hexdigest()[:16]


def _classify_cache_type(call: Dict, group_size: int = 1) -> str:
    """
    Classify a call into one of the 4 cache types.
    
    Priority order:
    1. Exact match (if group_size > 1, it's part of exact match group)
    2. Stable/Prefix (large system prompt)
    3. High-Value (expensive or slow)
    4. None (not cacheable)
    """
    # If already in a duplicate group, it's exact match
    if group_size >= THRESHOLDS["min_repeats"]:
        return "exact"
    
    # Check for Stable/Prefix (large system prompt ratio)
    system_tokens = call.get('system_prompt_tokens') or 0
    prompt_tokens = call.get('prompt_tokens') or 0
    
    if prompt_tokens > 0 and system_tokens > 0:
        ratio = system_tokens / prompt_tokens
        if ratio >= THRESHOLDS["stable_system_ratio"]:
            return "stable"
    
    # Check for High-Value (expensive or slow)
    cost = call.get('total_cost') or 0
    latency = call.get('latency_ms') or 0
    
    if cost >= THRESHOLDS["high_value_cost"] or latency >= THRESHOLDS["high_value_latency"]:
        return "high_value"
    
    return "none"


def _get_effort_level(cache_type: str) -> str:
    """Get implementation effort for cache type."""
    return CACHE_TYPES.get(cache_type, {}).get("effort", "medium")


def _get_type_emoji(cache_type: str) -> str:
    """Get emoji for cache type."""
    return CACHE_TYPES.get(cache_type, {}).get("emoji", "—")


def _get_type_name(cache_type: str) -> str:
    """Get display name for cache type."""
    return CACHE_TYPES.get(cache_type, {}).get("name", "—")


# =============================================================================
# LAYER 1: SUMMARY
# =============================================================================

def get_summary(calls: List[Dict], project: str = None, days: int = 7) -> CacheStoryResponse:
    """
    Layer 1: Cache opportunities summary.
    
    Groups calls by operation, detects duplicates, classifies cache types.
    """
    if not calls:
        return _empty_response()
    
    # Group calls by operation
    by_operation = defaultdict(list)
    for call in calls:
        op = f"{call.get('agent_name', 'Unknown')}.{call.get('operation', 'unknown')}"
        by_operation[op].append(call)
    
    # Analyze each operation
    detail_table = []
    total_cacheable = 0
    total_wasted_cost = 0.0
    
    for op, op_calls in by_operation.items():
        op_analysis = _analyze_operation_summary(op, op_calls)
        detail_table.append(op_analysis)
        
        total_cacheable += op_analysis['cacheable_count']
        total_wasted_cost += op_analysis['wasted_cost']
    
    # Sort by wasted cost descending
    detail_table.sort(key=lambda x: -x['wasted_cost'])
    
    # Calculate cache hit rate (from existing cache metadata)
    cache_hits = sum(1 for c in calls if (c.get('cache_metadata') or {}).get('cache_hit'))
    total_with_cache = sum(1 for c in calls if c.get('cache_metadata'))
    cache_misses = total_with_cache - cache_hits
    hit_rate = cache_hits / total_with_cache if total_with_cache > 0 else 0
    
    # Find top offender
    top_offender = _find_top_offender(detail_table)
    
    # Calculate health score
    health_score, status = _calculate_health(total_cacheable, len(calls), hit_rate)
    
    # Chart data - top 10 operations by wasted cost
    chart_data = [
        {
            'name': row['operation_name'][:20] if row.get('operation_name') else row['operation'].split('.')[-1][:20],
            'operation': row['operation'],
            'cacheable': row['cacheable_count'],
            'wasted_cost': row['wasted_cost'],
        }
        for row in detail_table[:10]
        if row['wasted_cost'] > 0
    ]
    
    # Count issues (operations with opportunities)
    issue_count = sum(1 for row in detail_table if row['has_opportunity'])
    
    return CacheStoryResponse(
        status=status,
        health_score=health_score,
        summary=CacheSummary(
            total_calls=len(calls),
            issue_count=issue_count,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            hit_rate=hit_rate,
            hit_rate_formatted=format_percentage(hit_rate),
            duplicate_prompts=total_cacheable,
            potential_savings=total_wasted_cost,
        ),
        top_offender=top_offender,
        detail_table=detail_table,
        chart_data=chart_data,
        recommendations=get_story_recommendations('cache'),
    )


def _analyze_operation_summary(op: str, op_calls: List[Dict]) -> Dict:
    """Analyze a single operation for cache opportunities (Layer 1 summary)."""
    
    # Group by prompt hash (exact match detection)
    prompt_groups = defaultdict(list)
    for call in op_calls:
        prompt = call.get('prompt') or ''
        prompt_hash = _hash_prompt(prompt)
        prompt_groups[prompt_hash].append(call)
    
    # Count exact match duplicates
    exact_duplicate_count = 0
    exact_wasted = 0.0
    
    for prompt_hash, group in prompt_groups.items():
        if len(group) >= THRESHOLDS["min_repeats"]:
            avg_cost = sum(c.get('total_cost', 0) for c in group) / len(group)
            wasted = (len(group) - 1) * avg_cost
            exact_duplicate_count += len(group)
            exact_wasted += wasted
    
    # Check for stable/prefix opportunities
    stable_count = 0
    stable_wasted = 0.0
    
    for call in op_calls:
        if _classify_cache_type(call, group_size=1) == "stable":
            stable_count += 1
            stable_wasted += call.get('total_cost', 0) * 0.5  # 50% savings estimate
    
    # Check for high-value opportunities
    high_value_count = 0
    high_value_wasted = 0.0
    
    for call in op_calls:
        cost = call.get('total_cost') or 0
        latency = call.get('latency_ms') or 0
        
        if cost >= THRESHOLDS["high_value_cost"] or latency >= THRESHOLDS["high_value_latency"]:
            # Only count if not already in exact match
            call_hash = _hash_prompt(call.get('prompt', ''))
            in_exact = len(prompt_groups.get(call_hash, [])) >= THRESHOLDS["min_repeats"]
            
            if not in_exact:
                high_value_count += 1
                high_value_wasted += cost * 0.3  # Conservative estimate
    
    # Determine primary cache type for this operation
    type_savings = {
        'exact': exact_wasted,
        'stable': stable_wasted,
        'high_value': high_value_wasted,
    }
    top_type = max(type_savings, key=type_savings.get) if any(type_savings.values()) else 'none'
    
    # Calculate totals
    total_cacheable = exact_duplicate_count
    total_wasted = exact_wasted  # Primary savings from exact matches
    
    redundancy_pct = total_cacheable / len(op_calls) if op_calls else 0
    has_opportunity = redundancy_pct >= THRESHOLDS["redundancy_warning"] or exact_wasted > 0.01
    
    # Status
    if redundancy_pct >= THRESHOLDS["redundancy_critical"]:
        status = "🔴"
    elif has_opportunity:
        status = "🟡"
    else:
        status = "🟢"
    
    # Parse agent/operation
    parts = op.split('.', 1)
    agent = parts[0] if len(parts) > 0 else 'Unknown'
    operation = parts[1] if len(parts) > 1 else op
    
    return {
        'status': status,
        'operation': op,
        'agent_name': agent,
        'operation_name': operation,
        'total_calls': len(op_calls),
        'unique_prompts': len(prompt_groups),
        'cacheable_count': total_cacheable,
        'redundancy_pct': redundancy_pct,
        'redundancy_formatted': format_percentage(redundancy_pct),
        'wasted_cost': total_wasted,
        'wasted_cost_formatted': format_cost(total_wasted),
        'has_opportunity': has_opportunity,
        'top_type': top_type,
        'top_type_emoji': _get_type_emoji(top_type),
        'top_type_name': _get_type_name(top_type),
        'effort': _get_effort_level(top_type),
    }


def _find_top_offender(detail_table: List[Dict]) -> Optional[TopOffender]:
    """Find the operation with highest wasted cost."""
    opportunities = [row for row in detail_table if row['has_opportunity']]
    
    if not opportunities:
        return None
    
    top = max(opportunities, key=lambda x: x['wasted_cost'])
    
    return TopOffender(
        agent=top['agent_name'],
        operation=top['operation_name'],
        value=top['wasted_cost'],
        value_formatted=format_cost(top['wasted_cost']),
        call_count=top['total_calls'],
        diagnosis=f"{top['cacheable_count']} cacheable calls ({top['top_type_emoji']} {top['top_type_name']})",
    )


def _calculate_health(cacheable: int, total: int, hit_rate: float) -> Tuple[float, str]:
    """Calculate health score and status."""
    if total == 0:
        return 100.0, "ok"
    
    cacheable_pct = cacheable / total
    
    # Good: low cacheable rate OR high hit rate
    if cacheable_pct < 0.1 or hit_rate >= 0.7:
        return 100.0, "ok"
    elif cacheable_pct < 0.3 or hit_rate >= 0.4:
        return max(70, 90 - (cacheable_pct * 50)), "warning"
    else:
        return max(30, 70 - (cacheable_pct * 80)), "error"


def _empty_response() -> CacheStoryResponse:
    """Return empty response when no data."""
    return CacheStoryResponse(
        status="ok",
        health_score=100.0,
        summary=CacheSummary(
            total_calls=0,
            issue_count=0,
            cache_hits=0,
            cache_misses=0,
            hit_rate=0.0,
            hit_rate_formatted="0%",
            duplicate_prompts=0,
            potential_savings=0.0,
        ),
        top_offender=None,
        detail_table=[],
        chart_data=[],
        recommendations=[],
    )


# =============================================================================
# LAYER 2: ALL OPPORTUNITIES (for Layer2Table)
# =============================================================================

def get_all_opportunities(
    calls: List[Dict],
    cache_type_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get ALL cache opportunities across all operations.
    
    Used by Layer 2 table to show all patterns with agent/operation columns.
    Supports filtering by cache_type via URL params.
    
    Returns:
        Dict with 'patterns' list and 'stats' summary
    """
    if not calls:
        return {'patterns': [], 'stats': {'total_patterns': 0, 'total_wasted': 0}}
    
    # Group calls by operation first
    by_operation = defaultdict(list)
    for call in calls:
        op = f"{call.get('agent_name', 'Unknown')}.{call.get('operation', 'unknown')}"
        by_operation[op].append(call)
    
    # Collect all opportunities across all operations
    all_opportunities = []
    
    for op, op_calls in by_operation.items():
        # Parse agent/operation
        parts = op.split('.', 1)
        agent = parts[0] if len(parts) > 0 else 'Unknown'
        operation = parts[1] if len(parts) > 1 else op
        
        # Group by prompt hash within this operation
        prompt_groups = defaultdict(list)
        for call in op_calls:
            prompt = call.get('prompt') or ''
            prompt_hash = _hash_prompt(prompt)
            prompt_groups[prompt_hash].append(call)
        
        # Build opportunities for this operation
        for prompt_hash, group in prompt_groups.items():
            # Calculate metrics
            avg_cost = sum(c.get('total_cost', 0) for c in group) / len(group) if group else 0
            avg_latency = sum(c.get('latency_ms', 0) for c in group) / len(group) if group else 0
            total_cost = sum(c.get('total_cost', 0) for c in group)
            
            # Classify cache type
            if len(group) >= THRESHOLDS["min_repeats"]:
                cache_type = "exact"
                wasted = (len(group) - 1) * avg_cost
            else:
                cache_type = _classify_cache_type(group[0], group_size=1)
                wasted = total_cost * 0.3 if cache_type != "none" else 0
            
            # Skip if no opportunity
            if cache_type == "none":
                continue
            
            # Apply cache_type filter if specified
            if cache_type_filter and cache_type != cache_type_filter:
                continue
            
            # Get prompt preview
            first_call = group[0]
            prompt_text = first_call.get('prompt') or ''
            prompt_preview = prompt_text[:100] + '...' if len(prompt_text) > 100 else prompt_text
            
            # Effort level
            effort = _get_effort_level(cache_type)
            
            # Build opportunity record with agent/operation for Layer 2 table
            opportunity = {
                'pattern_id': prompt_hash,
                'group_id': prompt_hash,
                'agent_name': agent,
                'operation': operation,
                'cache_type': cache_type,
                'cache_type_emoji': _get_type_emoji(cache_type),
                'cache_type_name': _get_type_name(cache_type),
                'effort': effort,
                'prompt_preview': prompt_preview,
                'repeat_count': len(group),
                'wasted_cost': wasted,
                'wasted_cost_formatted': format_cost(wasted),
                'avg_latency_ms': avg_latency,
                'avg_cost': avg_cost,
                'savable_time_ms': avg_latency * (len(group) - 1) if len(group) > 1 else avg_latency,
                'savable_time_formatted': f"~{(avg_latency * (len(group) - 1)) / 1000:.1f}s" if len(group) > 1 else f"~{avg_latency / 1000:.1f}s",
            }
            
            all_opportunities.append(opportunity)
    
    # Sort by wasted cost descending
    all_opportunities.sort(key=lambda x: -x['wasted_cost'])
    
    # Calculate stats
    stats = {
        'total_patterns': len(all_opportunities),
        'total_wasted': sum(o['wasted_cost'] for o in all_opportunities),
        'total_repeats': sum(o['repeat_count'] for o in all_opportunities),
        'by_type': {
            'exact': len([o for o in all_opportunities if o['cache_type'] == 'exact']),
            'stable': len([o for o in all_opportunities if o['cache_type'] == 'stable']),
            'high_value': len([o for o in all_opportunities if o['cache_type'] == 'high_value']),
            'semantic': len([o for o in all_opportunities if o['cache_type'] == 'semantic']),
        }
    }
    
    return {
        'patterns': all_opportunities,
        'stats': stats,
    }


# =============================================================================
# LAYER 2: OPERATION DETAIL
# =============================================================================

def get_operation_detail(
    calls: List[Dict],
    agent_name: str,
    operation_name: str,
) -> Dict[str, Any]:
    """
    Layer 2: Detailed cache opportunities for a single operation.
    
    Returns all cache opportunity groups with type classification.
    """
    # Filter to this operation
    op_calls = [
        c for c in calls
        if c.get('agent_name') == agent_name and c.get('operation') == operation_name
    ]
    
    if not op_calls:
        return {
            'agent_name': agent_name,
            'operation': operation_name,
            'total_calls': 0,
            'unique_prompts': 0,
            'cacheable_count': 0,
            'wasted_cost': 0,
            'wasted_cost_formatted': '$0.00',
            'opportunities': [],
            'type_counts': {},
        }
    
    # Group by prompt hash
    prompt_groups = defaultdict(list)
    for call in op_calls:
        prompt = call.get('prompt') or ''
        prompt_hash = _hash_prompt(prompt)
        prompt_groups[prompt_hash].append(call)
    
    # Build opportunities list
    opportunities = []
    type_counts = defaultdict(int)
    
    for prompt_hash, group in prompt_groups.items():
        # Calculate metrics for this group
        avg_cost = sum(c.get('total_cost', 0) for c in group) / len(group) if group else 0
        avg_latency = sum(c.get('latency_ms', 0) for c in group) / len(group) if group else 0
        total_cost = sum(c.get('total_cost', 0) for c in group)
        
        # Classify cache type
        if len(group) >= THRESHOLDS["min_repeats"]:
            cache_type = "exact"
            wasted = (len(group) - 1) * avg_cost
        else:
            cache_type = _classify_cache_type(group[0], group_size=1)
            wasted = total_cost * 0.3 if cache_type != "none" else 0
        
        # Skip if no opportunity
        if cache_type == "none":
            continue
        
        # Get prompt preview
        first_call = group[0]
        prompt_text = first_call.get('prompt') or ''
        prompt_preview = prompt_text[:100] + '...' if len(prompt_text) > 100 else prompt_text
        
        # Effort badge
        effort = _get_effort_level(cache_type)
        effort_badge = "🟢" if effort == "low" else "🟡" if effort == "medium" else "🔴"
        
        # Build opportunity record
        opportunity = {
            'group_id': prompt_hash,
            'cache_type': cache_type,
            'cache_type_emoji': _get_type_emoji(cache_type),
            'cache_type_name': _get_type_name(cache_type),
            'effort': effort,
            'effort_badge': effort_badge,
            'prompt_preview': prompt_preview,
            'repeat_count': len(group),
            'wasted_cost': wasted,
            'wasted_cost_formatted': format_cost(wasted),
            'avg_latency_ms': avg_latency,
            'avg_cost': avg_cost,
            'savable_time_ms': avg_latency * (len(group) - 1) if len(group) > 1 else avg_latency,
            'savable_time_formatted': f"~{(avg_latency * (len(group) - 1)) / 1000:.1f}s" if len(group) > 1 else f"~{avg_latency / 1000:.1f}s",
            'call_ids': [c.get('id') for c in group],
        }
        
        opportunities.append(opportunity)
        type_counts[cache_type] += 1
    
    # Sort by wasted cost
    opportunities.sort(key=lambda x: -x['wasted_cost'])
    
    # Summary metrics
    total_cacheable = sum(o['repeat_count'] for o in opportunities if o['cache_type'] == 'exact')
    total_wasted = sum(o['wasted_cost'] for o in opportunities)
    
    return {
        'agent_name': agent_name,
        'operation': operation_name,
        'total_calls': len(op_calls),
        'unique_prompts': len(prompt_groups),
        'cacheable_count': total_cacheable,
        'wasted_cost': total_wasted,
        'wasted_cost_formatted': format_cost(total_wasted),
        'opportunities': opportunities,
        'type_counts': dict(type_counts),
    }


# =============================================================================
# LAYER 3: OPPORTUNITY DETAIL
# =============================================================================

def get_opportunity_detail(
    calls: List[Dict],
    agent_name: str,
    operation_name: str,
    group_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Layer 3: Detailed view of a single cache opportunity.
    
    ENHANCED: Includes detailed prompt breakdown for CacheablePromptView component.
    """
    # Filter to this operation
    op_calls = [
        c for c in calls
        if c.get('agent_name') == agent_name and c.get('operation') == operation_name
    ]
    
    # Find calls matching this group_id (prompt hash)
    group_calls = [
        c for c in op_calls
        if _hash_prompt(c.get('prompt', '')) == group_id
    ]
    
    if not group_calls:
        return None
    
    # Get the representative call (first one)
    first_call = group_calls[0]
    
    # Classify cache type
    cache_type = "exact" if len(group_calls) >= THRESHOLDS["min_repeats"] else _classify_cache_type(first_call)
    
    # Calculate metrics
    avg_cost = sum(c.get('total_cost', 0) for c in group_calls) / len(group_calls)
    avg_latency = sum(c.get('latency_ms', 0) for c in group_calls) / len(group_calls)
    total_cost = sum(c.get('total_cost', 0) for c in group_calls)
    wasted_cost = (len(group_calls) - 1) * avg_cost if len(group_calls) > 1 else 0
    savable_time = avg_latency * (len(group_calls) - 1) if len(group_calls) > 1 else 0
    
    # Extract prompt components for CacheablePromptView
    system_prompt = first_call.get('system_prompt', '')
    system_prompt_tokens = first_call.get('system_prompt_tokens') or 0
    user_message = first_call.get('user_message', '')
    
    # Calculate averages for variable components - FIX: Handle None values
    avg_user_tokens = sum((c.get('user_message_tokens') or 0) for c in group_calls) / len(group_calls)
    avg_history_tokens = sum((c.get('chat_history_tokens') or 0) for c in group_calls) / len(group_calls)
    avg_tool_tokens = sum((c.get('tool_definitions_tokens') or 0) for c in group_calls) / len(group_calls)
    
    # Total tokens and cacheable analysis
    total_tokens = system_prompt_tokens + avg_user_tokens + avg_history_tokens + avg_tool_tokens
    if total_tokens == 0:
        total_tokens = first_call.get('prompt_tokens', 0)
        cacheable_tokens = int(total_tokens * 0.5)
        cacheable_percentage = 50.0
    else:
        if cache_type == "exact":
            cacheable_tokens = int(total_tokens)
            cacheable_percentage = 100.0
        else:
            cacheable_tokens = system_prompt_tokens
            cacheable_percentage = (system_prompt_tokens / total_tokens * 100) if total_tokens > 0 else 0
    
    # Build insights for CacheablePromptView
    insights = []
    if cache_type == "exact":
        insights.extend([
            f"Entire prompt is 100% identical across {len(group_calls)} calls",
            "Perfect candidate for response caching (key-value cache)",
            f"Save ${wasted_cost / (len(group_calls) - 1):.4f} per call by caching responses" if len(group_calls) > 1 else "Cache responses to avoid redundant API calls",
            "First call generates response, subsequent calls serve from cache instantly",
        ])
    elif cache_type == "stable":
        insights.extend([
            f"System prompt is 100% static across all {len(group_calls)} calls - perfect for caching",
            f"By enabling prompt caching, you'll save ${wasted_cost / (len(group_calls) - 1) if len(group_calls) > 1 else 0:.4f} per call",
            "First call will write the cache (same cost), all subsequent calls benefit from 90% reduction",
        ])
        if avg_history_tokens > 0:
            insights.append("Chat history changes on every turn - cannot be cached (conversation state)")
        if len(set(c.get('user_message', '') for c in group_calls)) == len(group_calls):
            insights.append("User message is unique each time - cannot be cached")
    
    # Build chat_history structure if present
    chat_history = None
    if avg_history_tokens > 0:
        for c in group_calls:
            if (c.get('chat_history_tokens') or 0) > 0:
                chat_history = [{"role": "assistant", "content": "(Previous conversation turn)", "tokens": int(avg_history_tokens)}]
                break
    
    # Build calls table
    affected_calls = []
    sorted_calls = sorted(group_calls, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    for idx, call in enumerate(sorted_calls):
        affected_calls.append({
            'index': idx + 1,
            'call_id': call.get('id'),
            'timestamp': call.get('timestamp'),
            'timestamp_formatted': str(call.get('timestamp', ''))[:19] if call.get('timestamp') else '—',
            'user_id': call.get('user_id') or '—',
            'session_id': call.get('session_id') or '—',
            'latency_ms': call.get('latency_ms'),
            'latency_formatted': f"{call.get('latency_ms', 0) / 1000:.2f}s",
            'total_cost': call.get('total_cost'),
            'cost_formatted': format_cost(call.get('total_cost', 0)),
            'is_first': idx == len(sorted_calls) - 1,
            'note': '✅ (first call)' if idx == len(sorted_calls) - 1 else '🔄 cacheable',
            'user_message_preview': (call.get('user_message', '') or '')[:100],
        })
    
    # Get diagnosis and code snippet based on cache type
    diagnosis = _get_diagnosis(cache_type, len(group_calls), wasted_cost, avg_latency, operation_name)
    
    return {
        'group_id': group_id,
        'agent_name': agent_name,
        'operation': operation_name,
        'cache_type': cache_type,
        'cache_type_emoji': _get_type_emoji(cache_type),
        'cache_type_name': _get_type_name(cache_type),
        'effort': _get_effort_level(cache_type),
        'repeat_count': len(group_calls),
        'occurrence_count': len(group_calls),
        'wasted_calls': len(group_calls) - 1,
        'wasted_cost': wasted_cost,
        'wasted_cost_formatted': format_cost(wasted_cost),
        'total_wasted': wasted_cost,
        'savable_time_ms': savable_time,
        'savable_time_formatted': f"~{savable_time / 1000:.1f}s" if savable_time > 1000 else f"~{savable_time:.0f}ms",
        'avg_cost': avg_cost,
        'avg_cost_formatted': format_cost(avg_cost),
        'current_cost_per_call': avg_cost,
        'avg_latency_ms': avg_latency,
        'avg_latency_formatted': f"{avg_latency / 1000:.2f}s",
        'prompt': first_call.get('prompt'),
        'response_text': first_call.get('response_text'),
        'prompt_tokens': first_call.get('prompt_tokens'),
        'completion_tokens': first_call.get('completion_tokens'),
        'system_prompt': system_prompt,
        'system_prompt_tokens': system_prompt_tokens,
        'user_message': user_message,
        'user_message_tokens': int(avg_user_tokens),
        'chat_history': chat_history,
        'chat_history_tokens': int(avg_history_tokens),
        'tool_definitions': first_call.get('tool_definitions') if avg_tool_tokens > 0 else None,
        'tool_definitions_tokens': int(avg_tool_tokens),
        'total_tokens': int(total_tokens),
        'cacheable_tokens': cacheable_tokens,
        'cacheable_percentage': round(cacheable_percentage, 1),
        'savings_per_call': wasted_cost / (len(group_calls) - 1) if len(group_calls) > 1 else 0,
        'cache_enabled': False,
        'diagnosis': diagnosis,
        'insights': insights,
        'calls': affected_calls,
        'affected_calls': affected_calls,
    }

def _get_diagnosis(cache_type: str, repeat_count: int, wasted_cost: float, avg_latency: float, operation: str) -> Dict[str, Any]:
    """Generate type-specific diagnosis with code snippet."""
    
    if cache_type == "exact":
        return {
            'problem': f"Same prompt sent {repeat_count} times → same response generated {repeat_count} times",
            'why': "No caching layer between app and LLM. Users or code paths are making redundant calls.",
            'fix_title': "Simple Key-Value Cache",
            'fix_description': "Hash the prompt and cache the response. Return cached response for identical prompts.",
            'code_snippet': f'''import hashlib
from redis import Redis

cache = Redis()

def {operation}_cached(prompt: str, ttl: int = 86400) -> str:
    """Cache LLM responses by prompt hash."""
    cache_key = f"llm:{{hashlib.sha256(prompt.encode()).hexdigest()}}"
    
    # Check cache first
    if cached := cache.get(cache_key):
        return cached.decode()
    
    # Generate and cache
    response = llm.complete(prompt)
    cache.setex(cache_key, ttl, response)
    return response''',
            'expected_impact': {
                'calls_before': repeat_count,
                'calls_after': 1,
                'reduction_pct': round(((repeat_count - 1) / repeat_count) * 100, 1) if repeat_count > 0 else 0,
                'cost_saved': wasted_cost,
                'cost_saved_formatted': format_cost(wasted_cost),
                'latency_cached_ms': 10,
                'latency_original_ms': avg_latency,
            },
        }
    
    elif cache_type == "stable":
        return {
            'problem': f"Large system prompt repeated across {repeat_count} calls",
            'why': "System prompt consumes >50% of tokens. Enable provider prompt caching.",
            'fix_title': "Prompt Caching (Anthropic/OpenAI)",
            'fix_description': "Use cache_control to cache the static system prompt prefix.",
            'code_snippet': '''# Anthropic prompt caching
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"}  # Cache this!
        }
    ],
    messages=[{"role": "user", "content": user_message}]
)

# OpenAI prefix caching (automatic for >1024 tokens)
# Just ensure system prompt is consistent across calls''',
            'expected_impact': {
                'calls_before': repeat_count,
                'calls_after': repeat_count,  # Same calls, just cheaper
                'reduction_pct': 50,  # ~50% cost reduction on cached tokens
                'cost_saved': wasted_cost,
                'cost_saved_formatted': format_cost(wasted_cost),
                'latency_cached_ms': avg_latency * 0.7,  # ~30% faster
                'latency_original_ms': avg_latency,
            },
        }
    
    elif cache_type == "high_value":
        return {
            'problem': f"Expensive/slow calls (${wasted_cost:.4f} avg, {avg_latency/1000:.1f}s avg)",
            'why': "These calls are costly to regenerate. Cache with background refresh.",
            'fix_title': "High-Value Cache with Background Refresh",
            'fix_description': "Cache expensive responses. Refresh in background before TTL expires.",
            'code_snippet': f'''from functools import lru_cache
import asyncio

# Simple in-memory cache for expensive calls
@lru_cache(maxsize=1000)
def {operation}_cached(prompt_hash: str, prompt: str) -> str:
    """Cache expensive LLM calls."""
    return llm.complete(prompt)

# Or with Redis + background refresh
async def get_with_refresh(key: str, generator_fn, ttl: int = 3600):
    """Get from cache, refresh in background if stale."""
    cached = cache.get(key)
    ttl_remaining = cache.ttl(key)
    
    if cached:
        # Refresh in background if <20% TTL remaining
        if ttl_remaining < ttl * 0.2:
            asyncio.create_task(refresh_cache(key, generator_fn, ttl))
        return cached
    
    # Generate and cache
    result = await generator_fn()
    cache.setex(key, ttl, result)
    return result''',
            'expected_impact': {
                'calls_before': repeat_count,
                'calls_after': 1,
                'reduction_pct': 70,  # Conservative estimate
                'cost_saved': wasted_cost * 0.7,
                'cost_saved_formatted': format_cost(wasted_cost * 0.7),
                'latency_cached_ms': 50,
                'latency_original_ms': avg_latency,
            },
        }
    
    else:  # semantic or none
        return {
            'problem': "Potential semantic similarity detected",
            'why': "These prompts may have similar meaning but different wording.",
            'fix_title': "Semantic Cache (Advanced)",
            'fix_description': "Use embeddings to find similar prompts. Requires vector database.",
            'code_snippet': '''# Semantic caching with embeddings
from openai import OpenAI
import numpy as np

client = OpenAI()

def semantic_cache_lookup(prompt: str, threshold: float = 0.95):
    """Find semantically similar cached responses."""
    # Get embedding for new prompt
    embedding = client.embeddings.create(
        model="text-embedding-3-small",
        input=prompt
    ).data[0].embedding
    
    # Search vector DB for similar
    results = vector_db.search(
        vector=embedding,
        limit=1,
        threshold=threshold
    )
    
    if results:
        return results[0].response
    
    # Generate and store
    response = llm.complete(prompt)
    vector_db.upsert(prompt, embedding, response)
    return response''',
            'expected_impact': {
                'calls_before': repeat_count,
                'calls_after': repeat_count,
                'reduction_pct': 0,
                'cost_saved': 0,
                'cost_saved_formatted': '$0.00',
                'latency_cached_ms': avg_latency,
                'latency_original_ms': avg_latency,
            },
        }