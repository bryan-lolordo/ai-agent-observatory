"""
Routing Service - Story 3 Business Logic
Location: api/services/routing_service.py

Handles model routing opportunity analysis.
Returns proper RoutingStoryResponse model.
"""

from typing import List, Dict, Any
from collections import defaultdict
from api.models import RoutingStoryResponse, RoutingSummary, TopOffender
from api.config.story_definitions import get_story_recommendations
from api.utils.formatters import format_cost, format_percentage

# Thresholds
HIGH_COMPLEXITY_THRESHOLD = 0.7
CHEAP_MODELS = ['gpt-4o-mini', 'gpt-3.5-turbo', 'claude-3-haiku', 'claude-3.5-haiku']


def get_summary(calls: List[Dict], project: str = None, days: int = 7) -> RoutingStoryResponse:
    """
    Layer 1: Routing opportunities summary.
    
    Args:
        calls: List of LLM call dictionaries
        project: Project name filter
        days: Number of days analyzed
    
    Returns:
        RoutingStoryResponse model
    """
    if not calls:
        return RoutingStoryResponse(
            status="ok",
            health_score=100.0,
            summary=RoutingSummary(
                total_calls=0,
                issue_count=0,
                upgrade_candidates=0,
                downgrade_candidates=0,
                high_complexity_calls=0,
                misrouted_calls=0,
                potential_savings=0.0,
            ),
            top_offender=None,
            detail_table=[],
            chart_data=[],
            recommendations=[],
        )
    
    # Filter to only LLM calls (exclude API operations)
    llm_calls = [c for c in calls if (c.get('prompt_tokens') or 0) > 0]
    
    if not llm_calls:
        return RoutingStoryResponse(
            status="ok",
            health_score=100.0,
            summary=RoutingSummary(
                total_calls=0,
                issue_count=0,
                upgrade_candidates=0,
                downgrade_candidates=0,
                high_complexity_calls=0,
                misrouted_calls=0,
                potential_savings=0.0,
            ),
            top_offender=None,
            detail_table=[],
            chart_data=[],
            recommendations=[],
        )
    
    # Group by operation
    by_operation = defaultdict(list)
    for call in llm_calls:
        op = f"{call.get('agent_name', 'Unknown')}.{call.get('operation', 'unknown')}"
        by_operation[op].append(call)
    
    detail_table = []
    upgrade_candidates = []
    downgrade_candidates = []
    high_complexity_count = 0
    misrouted_count = 0
    
    for op, op_calls in by_operation.items():
        # Calculate average complexity
        complexity_scores = []
        for call in op_calls:
            routing = call.get('routing_decision') or {}
            complexity = routing.get('complexity_score')
            if complexity is not None:
                complexity_scores.append(complexity)
                if complexity >= HIGH_COMPLEXITY_THRESHOLD:
                    high_complexity_count += 1
        
        avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else None
        
        # Get primary model
        models_used = defaultdict(int)
        for call in op_calls:
            model = call.get('model_name') or 'unknown'
            models_used[model] += 1
        primary_model = max(models_used, key=models_used.get) if models_used else 'unknown'
        
        is_cheap_model = any(cheap in primary_model.lower() for cheap in CHEAP_MODELS)
        
        # Calculate average quality
        quality_scores = [
            call.get('quality_evaluation', {}).get('judge_score', 0)
            for call in op_calls
            if call.get('quality_evaluation')
        ]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
        
        # Determine if upgrade/downgrade candidate
        is_upgrade = False
        is_downgrade = False
        status = "🟢"
        
        if avg_complexity is not None:
            if avg_complexity >= 0.7 and is_cheap_model:
                is_upgrade = True
                status = "🔴"
                upgrade_candidates.append((op, avg_complexity, op_calls))
                misrouted_count += len(op_calls)
            elif avg_complexity < 0.4 and avg_quality and avg_quality > 8.0:
                is_downgrade = True
                status = "🟡"
                downgrade_candidates.append((op, avg_complexity, op_calls))
        
        total_cost = sum(c.get('total_cost', 0) for c in op_calls)
        
        detail_table.append({
            'status': status,
            'operation': op,
            'call_count': len(op_calls),
            'avg_complexity': avg_complexity,
            'avg_quality': avg_quality,
            'primary_model': primary_model,
            'model_name': primary_model,  # Alias for frontend
            'total_cost': total_cost,
            'is_upgrade_candidate': is_upgrade,
            'is_downgrade_candidate': is_downgrade,
        })
    
    # Sort by complexity (highest first)
    detail_table.sort(key=lambda x: -(x['avg_complexity'] or 0))
    
    # Chart data
    chart_data = [
        {
            'name': row['operation'],
            'complexity': row['avg_complexity'] or 0,
            'quality': row['avg_quality'] or 0,
        }
        for row in detail_table[:10]
    ]
    
    # Top offender (highest complexity on cheap model)
    top_offender = None
    if upgrade_candidates:
        upgrade_candidates.sort(key=lambda x: -x[1])
        top_op, top_complexity, top_calls = upgrade_candidates[0]
        
        agent, operation = top_op.split('.', 1) if '.' in top_op else ('Unknown', top_op)
        
        top_offender = TopOffender(
            agent=agent,
            operation=operation,
            value=top_complexity,
            value_formatted=f"{top_complexity:.2f}",
            call_count=len(top_calls),
            diagnosis=f"High complexity ({top_complexity:.2f}) on cheap model - upgrade recommended",
        )
    
    # Calculate potential savings (rough estimate)
    potential_savings = len(downgrade_candidates) * 0.02  # Estimate $0.02 saved per downgrade
    
    # Health score
    issue_count = len(upgrade_candidates) + len(downgrade_candidates)
    if issue_count == 0:
        health_score = 100.0
        status = "ok"
    elif len(upgrade_candidates) > 0:
        health_score = max(50, 80 - (len(upgrade_candidates) * 10))
        status = "warning"
    else:
        health_score = max(70, 90 - (len(downgrade_candidates) * 5))
        status = "ok"
    
    return RoutingStoryResponse(
        status=status,
        health_score=health_score,
        summary=RoutingSummary(
            total_calls=len(llm_calls),
            issue_count=issue_count,
            upgrade_candidates=len(upgrade_candidates),
            downgrade_candidates=len(downgrade_candidates),
            high_complexity_calls=high_complexity_count,
            misrouted_calls=misrouted_count,
            potential_savings=potential_savings,
        ),
        top_offender=top_offender,
        detail_table=detail_table,
        chart_data=chart_data,
        recommendations=get_story_recommendations('routing'),
    )