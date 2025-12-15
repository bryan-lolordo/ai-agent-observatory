"""
Cost Service - Story 7 Business Logic
Location: api/services/cost_service.py

Handles cost analysis and breakdown.
Returns proper CostStoryResponse model.
"""

from typing import List, Dict, Any
from collections import defaultdict
from api.models import CostStoryResponse, CostSummary, TopOffender
from api.config.story_definitions import get_story_recommendations
from api.utils.formatters import format_cost, format_percentage

# Thresholds
COST_CONCENTRATION_THRESHOLD = 0.70


def get_summary(calls: List[Dict], project: str = None, days: int = 7) -> CostStoryResponse:
    """
    Layer 1: Cost analysis summary.
    
    Args:
        calls: List of LLM call dictionaries
        project: Project name filter
        days: Number of days analyzed
    
    Returns:
        CostStoryResponse model
    """
    if not calls:
        return CostStoryResponse(
            status="ok",
            health_score=100.0,
            summary=CostSummary(
                total_calls=0,
                issue_count=0,
                total_cost=0.0,
                total_cost_formatted="$0.00",
                avg_cost_per_call=0.0,
                potential_savings=0.0,
                top_3_concentration=0.0,
            ),
            top_offender=None,
            detail_table=[],
            chart_data=[],
            recommendations=[],
        )
    
    total_cost = sum(c.get('total_cost', 0) for c in calls)
    total_calls = len(calls)
    avg_cost_per_call = total_cost / total_calls if total_calls > 0 else 0
    
    if total_cost == 0:
        return CostStoryResponse(
            status="ok",
            health_score=100.0,
            summary=CostSummary(
                total_calls=total_calls,
                issue_count=0,
                total_cost=0.0,
                total_cost_formatted="$0.00",
                avg_cost_per_call=0.0,
                potential_savings=0.0,
                top_3_concentration=0.0,
            ),
            top_offender=None,
            detail_table=[],
            chart_data=[],
            recommendations=[],
        )
    
    # Group by operation
    by_operation = defaultdict(lambda: {'calls': [], 'cost': 0})
    for call in calls:
        op = f"{call.get('agent_name', 'Unknown')}.{call.get('operation', 'unknown')}"
        cost = call.get('total_cost', 0)
        by_operation[op]['calls'].append(call)
        by_operation[op]['cost'] += cost
    
    # Build detail table
    detail_table = []
    for op, data in by_operation.items():
        cost_share = data['cost'] / total_cost if total_cost > 0 else 0
        avg_cost = data['cost'] / len(data['calls']) if data['calls'] else 0
        
        # Calculate total tokens
        total_prompt_tokens = sum(c.get('prompt_tokens', 0) for c in data['calls'])
        total_completion_tokens = sum(c.get('completion_tokens', 0) for c in data['calls'])
        
        agent, operation = op.split('.', 1) if '.' in op else ('Unknown', op)
        
        detail_table.append({
            'operation': op,
            'agent': agent,
            'total_cost': data['cost'],
            'total_cost_formatted': format_cost(data['cost']),
            'cost_share': cost_share,
            'cost_share_formatted': format_percentage(cost_share),
            'call_count': len(data['calls']),
            'avg_cost': avg_cost,
            'avg_cost_formatted': format_cost(avg_cost),
            'total_prompt_tokens': total_prompt_tokens,
            'total_completion_tokens': total_completion_tokens,
        })
    
    # Sort by cost (highest first)
    detail_table.sort(key=lambda x: -x['total_cost'])
    
    # Chart data
    chart_data = [
        {
            'name': row['operation'],
            'cost': row['total_cost'],
            'calls': row['call_count'],
        }
        for row in detail_table[:10]
    ]
    
    # Calculate top 3 concentration
    top_3_cost = sum(op['total_cost'] for op in detail_table[:3])
    top_3_concentration = top_3_cost / total_cost if total_cost > 0 else 0
    
    # Calculate potential savings (estimate 20% reduction through optimization)
    potential_savings = total_cost * 0.20
    
    # Top offender (highest total cost)
    top_offender = None
    if detail_table:
        top_row = detail_table[0]
        
        top_offender = TopOffender(
            agent=top_row['agent'],
            operation=top_row['operation'].split('.', 1)[1] if '.' in top_row['operation'] else top_row['operation'],
            value=top_row['total_cost'],
            value_formatted=format_cost(top_row['total_cost']),
            call_count=top_row['call_count'],
            diagnosis=f"{format_percentage(top_row['cost_share'])} of total cost",
        )
    
    # Health score
    has_concentration = top_3_concentration > COST_CONCENTRATION_THRESHOLD
    if has_concentration:
        health_score = max(60, 80 - (int(top_3_concentration * 100) - 70))
        status = "warning"
        issue_count = 1
    else:
        health_score = 100.0
        status = "ok"
        issue_count = 0
    
    return CostStoryResponse(
        status=status,
        health_score=health_score,
        summary=CostSummary(
            total_calls=total_calls,
            issue_count=issue_count,
            total_cost=total_cost,
            total_cost_formatted=format_cost(total_cost),
            avg_cost_per_call=avg_cost_per_call,
            potential_savings=potential_savings,
            top_3_concentration=top_3_concentration,
        ),
        top_offender=top_offender,
        detail_table=detail_table,
        chart_data=chart_data,
        recommendations=get_story_recommendations('cost'),
    )