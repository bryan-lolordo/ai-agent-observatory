"""
Cache Service - Story 2 Business Logic
Location: api/services/cache_service.py

Handles cache opportunity analysis.
Returns proper CacheStoryResponse model.
"""

from typing import List, Dict, Any
from collections import defaultdict
import hashlib
from api.models import CacheStoryResponse, CacheSummary, TopOffender
from api.config.story_definitions import get_story_recommendations
from api.utils.formatters import format_cost, format_percentage

# Thresholds
DUPLICATE_THRESHOLD = 2
CACHE_OPPORTUNITY_PCT = 0.20


def get_summary(calls: List[Dict], project: str = None, days: int = 7) -> CacheStoryResponse:
    """
    Layer 1: Cache opportunities summary.
    
    Args:
        calls: List of LLM call dictionaries
        project: Project name filter
        days: Number of days analyzed
    
    Returns:
        CacheStoryResponse model
    """
    if not calls:
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
    
    # Calculate current cache metrics
    cache_hits = sum(1 for c in calls if (c.get('cache_metadata') or {}).get('cache_hit'))
    cache_misses = sum(1 for c in calls if c.get('cache_metadata') and not (c.get('cache_metadata') or {}).get('cache_hit'))
    total_with_cache = cache_hits + cache_misses
    hit_rate = cache_hits / total_with_cache if total_with_cache > 0 else 0
    
    # Find duplicates by grouping prompts
    by_operation = defaultdict(list)
    for call in calls:
        op = f"{call.get('agent_name', 'Unknown')}.{call.get('operation', 'unknown')}"
        by_operation[op].append(call)
    
    detail_table = []
    ops_with_opportunity = []
    total_duplicates = 0
    total_wasted_cost = 0
    
    for op, op_calls in by_operation.items():
        # Group by prompt hash
        prompt_groups = defaultdict(list)
        for call in op_calls:
            prompt = call.get('prompt') or ''
            if prompt:
                prompt_hash = hashlib.md5(prompt.lower().strip().encode()).hexdigest()[:12]
                prompt_groups[prompt_hash].append(call)
        
        # Count duplicates
        duplicate_count = sum(len(group) for group in prompt_groups.values() if len(group) >= DUPLICATE_THRESHOLD)
        unique_prompts = len(prompt_groups)
        wasted_cost = sum(
            (len(group) - 1) * (sum(c.get('total_cost', 0) for c in group) / len(group))
            for group in prompt_groups.values()
            if len(group) >= DUPLICATE_THRESHOLD
        )
        
        redundancy_pct = duplicate_count / len(op_calls) if op_calls else 0
        has_opportunity = redundancy_pct >= CACHE_OPPORTUNITY_PCT
        
        if has_opportunity:
            ops_with_opportunity.append((op, wasted_cost, duplicate_count, op_calls))
        
        total_duplicates += duplicate_count
        total_wasted_cost += wasted_cost
        
        status = "🔴" if redundancy_pct > 0.5 else "🟡" if redundancy_pct > 0.2 else "🟢"
        
        detail_table.append({
            'status': status,
            'operation': op,
            'total_calls': len(op_calls),
            'unique_prompts': unique_prompts,
            'duplicate_count': duplicate_count,
            'redundancy_pct': redundancy_pct,
            'redundancy_formatted': format_percentage(redundancy_pct),
            'wasted_cost': wasted_cost,
            'wasted_cost_formatted': format_cost(wasted_cost),
            'has_opportunity': has_opportunity,
        })
    
    detail_table.sort(key=lambda x: -x['wasted_cost'])
    
    # Chart data
    chart_data = [
        {
            'name': row['operation'],
            'duplicates': row['duplicate_count'],
            'wasted_cost': row['wasted_cost'],
        }
        for row in detail_table[:10]
    ]
    
    # Top offender
    top_offender = None
    if ops_with_opportunity:
        ops_with_opportunity.sort(key=lambda x: -x[1])
        top_op, top_cost, top_dups, top_calls = ops_with_opportunity[0]
        
        agent, operation = top_op.split('.', 1) if '.' in top_op else ('Unknown', top_op)
        
        top_offender = TopOffender(
            agent=agent,
            operation=operation,
            value=top_cost,
            value_formatted=format_cost(top_cost),
            call_count=len(top_calls),
            diagnosis=f"{top_dups} duplicate calls wasting ${top_cost:.3f}",
        )
    
    # Health score
    issue_count = len(ops_with_opportunity)
    if issue_count == 0 and hit_rate > 0.5:
        health_score = 100.0
        status = "ok"
    elif hit_rate > 0.3:
        health_score = max(70, 90 - (issue_count * 5))
        status = "warning"
    else:
        health_score = max(30, 70 - (issue_count * 10))
        status = "error"
    
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
            duplicate_prompts=total_duplicates,
            potential_savings=total_wasted_cost,
        ),
        top_offender=top_offender,
        detail_table=detail_table,
        chart_data=chart_data,
        recommendations=get_story_recommendations('cache'),
    )