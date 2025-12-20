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
HIGH_COST_THRESHOLD = 0.15  # >15% of total = high cost operation
MEDIUM_COST_THRESHOLD = 0.05  # >5% of total = medium cost


def _get_status(cost_share: float) -> tuple:
    """Get status and emoji based on cost share."""
    if cost_share >= HIGH_COST_THRESHOLD:
        return ("high", "🔴")
    elif cost_share >= MEDIUM_COST_THRESHOLD:
        return ("medium", "🟡")
    else:
        return ("low", "🟢")


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
                avg_cost_formatted="$0.000",
                avg_cost_per_call=0.0,
                potential_savings=0.0,
                potential_savings_formatted="$0.00",
                top_3_concentration=0.0,
                top_3_concentration_formatted="0%",
            ),
            top_offender=None,
            detail_table=[],
            chart_data=[],
            recommendations=[],
        )
    
    total_cost = sum(c.get('total_cost', 0) or 0 for c in calls)
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
                avg_cost_formatted="$0.000",
                avg_cost_per_call=0.0,
                potential_savings=0.0,
                potential_savings_formatted="$0.00",
                top_3_concentration=0.0,
                top_3_concentration_formatted="0%",
            ),
            top_offender=None,
            detail_table=[],
            chart_data=[],
            recommendations=[],
        )
    
    # Group by operation
    by_operation = defaultdict(lambda: {'calls': [], 'cost': 0})
    for call in calls:
        agent = call.get('agent_name') or 'Unknown'
        operation = call.get('operation') or 'unknown'
        op_key = f"{agent}.{operation}"
        cost = call.get('total_cost', 0) or 0
        by_operation[op_key]['calls'].append(call)
        by_operation[op_key]['cost'] += cost
        by_operation[op_key]['agent'] = agent
        by_operation[op_key]['operation'] = operation
    
    # Build detail table
    detail_table = []
    for op_key, data in by_operation.items():
        cost_share = data['cost'] / total_cost if total_cost > 0 else 0
        avg_cost = data['cost'] / len(data['calls']) if data['calls'] else 0
        
        # Calculate total tokens
        total_prompt_tokens = sum(c.get('prompt_tokens', 0) or 0 for c in data['calls'])
        total_completion_tokens = sum(c.get('completion_tokens', 0) or 0 for c in data['calls'])
        
        # Get status
        status, status_emoji = _get_status(cost_share)
        
        detail_table.append({
            # Frontend expected field names
            'agent_name': data['agent'],
            'operation_name': data['operation'],
            'total_cost': data['cost'],
            'total_cost_formatted': format_cost(data['cost']),
            'cost_pct': cost_share,
            'cost_pct_formatted': format_percentage(cost_share),
            'call_count': len(data['calls']),
            'avg_cost': avg_cost,
            'avg_cost_formatted': format_cost(avg_cost),
            'total_prompt_tokens': total_prompt_tokens,
            'total_completion_tokens': total_completion_tokens,
            'status': status,
            'status_emoji': status_emoji,
            # Keep original names for backward compatibility
            'operation': op_key,
            'agent': data['agent'],
            'cost_share': cost_share,
            'cost_share_formatted': format_percentage(cost_share),
        })
    
    # Sort by cost (highest first)
    detail_table.sort(key=lambda x: -x['total_cost'])
    
    # Calculate top 3 concentration
    top_3_cost = sum(op['total_cost'] for op in detail_table[:3])
    top_3_concentration = top_3_cost / total_cost if total_cost > 0 else 0
    
    # Calculate potential savings (estimate 20% reduction through optimization)
    potential_savings = total_cost * 0.20
    
    # Chart data with frontend expected field names
    chart_data = []
    for row in detail_table[:10]:
        pct = (row['total_cost'] / total_cost * 100) if total_cost > 0 else 0
        chart_data.append({
            'name': row['operation_name'],
            'value': row['total_cost'],
            'cost': row['total_cost'],
            'calls': row['call_count'],
            'percentage': round(pct, 1),
        })
    
    # Count high-cost operations as issues
    issue_count = sum(1 for op in detail_table if op['status'] == 'high')
    
    # Top offender (highest total cost)
    top_offender = None
    if detail_table:
        top_row = detail_table[0]
        
        top_offender = TopOffender(
            agent=top_row['agent_name'],
            operation=top_row['operation_name'],
            value=top_row['total_cost'],
            value_formatted=format_cost(top_row['total_cost']),
            call_count=top_row['call_count'],
            diagnosis=f"{top_row['cost_pct_formatted']} of total cost",
        )
    
    # Health score
    has_concentration = top_3_concentration > COST_CONCENTRATION_THRESHOLD
    if has_concentration:
        health_score = max(60, 80 - (int(top_3_concentration * 100) - 70))
        status = "warning"
    else:
        health_score = 100.0
        status = "ok"
    
    return CostStoryResponse(
        status=status,
        health_score=health_score,
        summary=CostSummary(
            total_calls=total_calls,
            issue_count=issue_count,
            total_cost=total_cost,
            total_cost_formatted=format_cost(total_cost),
            avg_cost_per_call=avg_cost_per_call,
            avg_cost_formatted=format_cost(avg_cost_per_call),
            potential_savings=potential_savings,
            potential_savings_formatted=format_cost(potential_savings),
            top_3_concentration=top_3_concentration,
            top_3_concentration_formatted=format_percentage(top_3_concentration),
        ),
        top_offender=top_offender,
        detail_table=detail_table,
        chart_data=chart_data,
        recommendations=get_story_recommendations('cost'),
    )


def get_operation_detail(
    calls: List[Dict],
    agent: str,
    operation: str
) -> Dict[str, Any]:
    """
    Layer 2: Operation cost detail.
    
    Args:
        calls: List of LLM call dictionaries
        agent: Agent name
        operation: Operation name
    
    Returns:
        Operation cost breakdown
    """
    # Filter calls for this operation
    op_calls = [
        c for c in calls
        if c.get("agent_name") == agent and c.get("operation") == operation
    ]
    
    if not op_calls:
        return None
    
    # Calculate totals
    total_cost = sum(c.get('total_cost', 0) or 0 for c in op_calls)
    total_prompt_tokens = sum(c.get('prompt_tokens', 0) or 0 for c in op_calls)
    total_completion_tokens = sum(c.get('completion_tokens', 0) or 0 for c in op_calls)
    call_count = len(op_calls)
    
    avg_cost = total_cost / call_count if call_count > 0 else 0
    avg_prompt_tokens = total_prompt_tokens / call_count if call_count > 0 else 0
    avg_completion_tokens = total_completion_tokens / call_count if call_count > 0 else 0
    
    # Get min/max costs
    costs = [c.get('total_cost', 0) or 0 for c in op_calls]
    min_cost = min(costs) if costs else 0
    max_cost = max(costs) if costs else 0
    
    return {
        "agent_name": agent,
        "operation_name": operation,
        "call_count": call_count,
        "total_cost": total_cost,
        "total_cost_formatted": format_cost(total_cost),
        "avg_cost": avg_cost,
        "avg_cost_formatted": format_cost(avg_cost),
        "min_cost": min_cost,
        "min_cost_formatted": format_cost(min_cost),
        "max_cost": max_cost,
        "max_cost_formatted": format_cost(max_cost),
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "avg_prompt_tokens": int(avg_prompt_tokens),
        "avg_completion_tokens": int(avg_completion_tokens),
    }