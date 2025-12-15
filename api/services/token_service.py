"""
Token Service - Story 5 Business Logic
Location: api/services/token_service.py

Handles token efficiency analysis.
Returns proper TokenStoryResponse model.
"""

from typing import List, Dict, Any
from collections import defaultdict
from api.models import TokenStoryResponse, TokenSummary, TopOffender
from api.config.story_definitions import get_story_recommendations
from api.utils.formatters import format_tokens

# Thresholds
TOKEN_RATIO_WARNING = 10
TOKEN_RATIO_CRITICAL = 20


def get_summary(calls: List[Dict], project: str = None, days: int = 7) -> TokenStoryResponse:
    """
    Layer 1: Token efficiency summary.
    
    Args:
        calls: List of LLM call dictionaries
        project: Project name filter
        days: Number of days analyzed
    
    Returns:
        TokenStoryResponse model
    """
    if not calls:
        return TokenStoryResponse(
            status="ok",
            health_score=100.0,
            summary=TokenSummary(
                total_calls=0,
                issue_count=0,
                avg_ratio=0.0,
                avg_ratio_formatted="0:1",
                worst_ratio=0.0,
                worst_ratio_formatted="0:1",
                imbalanced_count=0,
            ),
            top_offender=None,
            detail_table=[],
            chart_data=[],
            recommendations=[],
        )
    
    # Filter to only LLM calls
    llm_calls = [c for c in calls if (c.get('prompt_tokens') or 0) > 0]
    
    if not llm_calls:
        return TokenStoryResponse(
            status="ok",
            health_score=100.0,
            summary=TokenSummary(
                total_calls=0,
                issue_count=0,
                avg_ratio=0.0,
                avg_ratio_formatted="0:1",
                worst_ratio=0.0,
                worst_ratio_formatted="0:1",
                imbalanced_count=0,
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
    imbalanced_ops = []
    all_ratios = []
    
    for op, op_calls in by_operation.items():
        total_prompt = sum(c.get('prompt_tokens', 0) for c in op_calls)
        total_completion = sum(c.get('completion_tokens', 0) for c in op_calls)
        total_cost = sum(c.get('total_cost', 0) for c in op_calls)
        
        avg_prompt = total_prompt / len(op_calls) if op_calls else 0
        avg_completion = total_completion / len(op_calls) if op_calls else 0
        
        # Calculate ratio
        if avg_completion > 0:
            ratio = avg_prompt / avg_completion
            all_ratios.append(ratio)
        else:
            ratio = float('inf')
        
        is_critical = ratio > TOKEN_RATIO_CRITICAL if ratio != float('inf') else False
        is_imbalanced = ratio > TOKEN_RATIO_WARNING if ratio != float('inf') else False
        
        status = "🔴" if is_critical else "🟡" if is_imbalanced else "🟢"
        
        if is_imbalanced:
            imbalanced_ops.append((op, ratio, avg_prompt, avg_completion, op_calls))
        
        detail_table.append({
            'status': status,
            'operation': op,
            'call_count': len(op_calls),
            'avg_prompt_tokens': int(avg_prompt),
            'avg_prompt': format_tokens(avg_prompt),
            'avg_completion_tokens': int(avg_completion),
            'avg_completion': format_tokens(avg_completion),
            'ratio': ratio if ratio != float('inf') else 0,
            'ratio_formatted': f"{ratio:.0f}:1" if ratio != float('inf') and ratio < 1000 else "Very high",
            'total_cost': total_cost,
            'is_imbalanced': is_imbalanced,
            'is_critical': is_critical,
        })
    
    # Sort by ratio (highest first)
    detail_table.sort(key=lambda x: -x['ratio'] if x['ratio'] != float('inf') else -999999)
    
    # Chart data
    chart_data = [
        {
            'name': row['operation'],
            'prompt': row['avg_prompt_tokens'],
            'completion': row['avg_completion_tokens'],
            'ratio': row['ratio'],
        }
        for row in detail_table[:10]
    ]
    
    # Calculate global metrics
    worst_ratio = max(all_ratios) if all_ratios else 0
    avg_ratio = sum(all_ratios) / len(all_ratios) if all_ratios else 0
    imbalanced_count = len(imbalanced_ops)
    
    # Top offender
    top_offender = None
    if imbalanced_ops:
        imbalanced_ops.sort(key=lambda x: -x[1])
        top_op, top_ratio, top_prompt, top_completion, top_calls = imbalanced_ops[0]
        
        agent, operation = top_op.split('.', 1) if '.' in top_op else ('Unknown', top_op)
        
        diagnosis = _diagnose_imbalance(top_prompt, top_completion)
        
        top_offender = TopOffender(
            agent=agent,
            operation=operation,
            value=top_ratio,
            value_formatted=f"{top_ratio:.0f}:1",
            call_count=len(top_calls),
            diagnosis=diagnosis,
        )
    
    # Health score
    issue_count = imbalanced_count
    critical_count = sum(1 for op in imbalanced_ops if op[1] > TOKEN_RATIO_CRITICAL)
    
    if critical_count > 0:
        health_score = max(30, 60 - (critical_count * 10))
        status = "error"
    elif issue_count > 0:
        health_score = max(60, 85 - (issue_count * 5))
        status = "warning"
    else:
        health_score = 100.0
        status = "ok"
    
    return TokenStoryResponse(
        status=status,
        health_score=health_score,
        summary=TokenSummary(
            total_calls=len(llm_calls),
            issue_count=issue_count,
            avg_ratio=avg_ratio,
            avg_ratio_formatted=f"{avg_ratio:.1f}:1" if avg_ratio > 0 else "—",
            worst_ratio=worst_ratio,
            worst_ratio_formatted=f"{worst_ratio:.1f}:1" if worst_ratio > 0 else "—",
            imbalanced_count=imbalanced_count,
        ),
        top_offender=top_offender,
        detail_table=detail_table,
        chart_data=chart_data,
        recommendations=get_story_recommendations('token_imbalance'),
    )


def _diagnose_imbalance(avg_prompt: float, avg_completion: float) -> str:
    """Generate diagnosis for token imbalance."""
    if avg_prompt > 3000 and avg_completion < 200:
        return "Large context with minimal output - likely chat history bloat. Implement sliding window."
    elif avg_prompt > 1500:
        return "Consider summarizing history or reducing context."
    else:
        return "Review if all context is necessary for this operation."