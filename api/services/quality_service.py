"""
Quality Service - Story 4 Business Logic
Location: api/services/quality_service.py

Handles quality monitoring and error analysis.
Returns proper QualityStoryResponse model.
"""

from typing import List, Dict, Any
from collections import defaultdict
from api.models import QualityStoryResponse, QualitySummary, TopOffender
from api.config.story_definitions import get_story_recommendations
from api.utils.formatters import format_percentage

# Thresholds
ERROR_RATE_WARNING = 0.02
ERROR_RATE_CRITICAL = 0.05


def get_summary(calls: List[Dict], project: str = None, days: int = 7) -> QualityStoryResponse:
    """
    Layer 1: Quality monitoring summary.
    
    Args:
        calls: List of LLM call dictionaries
        project: Project name filter
        days: Number of days analyzed
    
    Returns:
        QualityStoryResponse model
    """
    if not calls:
        return QualityStoryResponse(
            status="ok",
            health_score=100.0,
            summary=QualitySummary(
                total_calls=0,
                issue_count=0,
                error_count=0,
                error_rate=0.0,
                error_rate_formatted="0%",
                success_count=0,
                success_rate=1.0,
                avg_quality_score=0.0,
                hallucination_count=0,
                operations_affected=0,
            ),
            top_offender=None,
            detail_table=[],
            chart_data=[],
            recommendations=[],
        )
    
    # Count errors and quality issues
    errors = []
    hallucinations = []
    
    for call in calls:
        success = call.get('success', True)
        error = call.get('error') or ''
        
        if not success or error:
            errors.append({
                'agent': call.get('agent_name') or 'Unknown',
                'agent_name': call.get('agent_name') or 'Unknown',
                'operation': call.get('operation') or 'unknown',
                'error': error or 'Unknown error',
                'error_message': error or 'Unknown error',
                'error_type': call.get('error_type') or 'UNKNOWN',
                'timestamp': call.get('timestamp'),
                'call': call,
            })
        
        quality_eval = call.get('quality_evaluation') or {}
        if quality_eval.get('hallucination_flag'):
            hallucinations.append({
                'agent': call.get('agent_name') or 'Unknown',
                'operation': call.get('operation') or 'unknown',
                'details': quality_eval.get('hallucination_details') or 'Hallucination detected',
                'score': quality_eval.get('judge_score'),
                'call': call,
            })
    
    total_calls = len(calls)
    error_count = len(errors)
    success_count = total_calls - error_count
    error_rate = error_count / total_calls if total_calls > 0 else 0
    success_rate = success_count / total_calls if total_calls > 0 else 1.0
    
    # Calculate average quality score
    quality_scores = [
        call.get('quality_evaluation', {}).get('judge_score')
        for call in calls
        if call.get('quality_evaluation') and call.get('quality_evaluation', {}).get('judge_score') is not None
    ]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    # Group errors by operation
    error_by_op = defaultdict(list)
    for err in errors:
        key = f"{err['agent']}.{err['operation']}"
        error_by_op[key].append(err)
    
    operations_affected = len(error_by_op)
    
    # Group by operation for table
    by_operation = defaultdict(list)
    for call in calls:
        op = f"{call.get('agent_name', 'Unknown')}.{call.get('operation', 'unknown')}"
        by_operation[op].append(call)
    
    detail_table = []
    ops_with_issues = []
    
    for op, op_calls in by_operation.items():
        # Count errors for this operation
        op_errors = sum(1 for c in op_calls if not c.get('success', True) or c.get('error'))
        
        # Calculate quality scores
        op_quality_scores = [
            c.get('quality_evaluation', {}).get('judge_score')
            for c in op_calls
            if c.get('quality_evaluation') and c.get('quality_evaluation', {}).get('judge_score') is not None
        ]
        avg_score = sum(op_quality_scores) / len(op_quality_scores) if op_quality_scores else None
        min_score = min(op_quality_scores) if op_quality_scores else None
        
        # Determine status
        has_issues = op_errors > 0 or (avg_score is not None and avg_score < 7.0)
        status = "🔴" if has_issues else "🟢"
        
        if has_issues:
            ops_with_issues.append((op, op_errors, avg_score or 0, op_calls))
        
        detail_table.append({
            'status': status,
            'operation': op,
            'call_count': len(op_calls),
            'avg_score': avg_score,
            'min_score': min_score,
            'error_count': op_errors,
            'has_issues': has_issues,
        })
    
    # Sort by error count (most errors first)
    detail_table.sort(key=lambda x: -x['error_count'])
    
    # Chart data
    chart_data = [
        {
            'name': row['operation'],
            'errors': row['error_count'],
            'quality': row['avg_score'] or 0,
        }
        for row in detail_table[:10]
    ]
    
    # Top offender (most errors)
    top_offender = None
    if ops_with_issues:
        ops_with_issues.sort(key=lambda x: -x[1])  # Sort by error count
        top_op, top_errors, top_quality, top_calls = ops_with_issues[0]
        
        agent, operation = top_op.split('.', 1) if '.' in top_op else ('Unknown', top_op)
        
        top_offender = TopOffender(
            agent=agent,
            operation=operation,
            value=top_errors,
            value_formatted=f"{top_errors} errors",
            call_count=len(top_calls),
            diagnosis=f"{top_errors} errors, avg quality {top_quality:.1f}/10" if top_quality > 0 else f"{top_errors} errors",
        )
    
    # Health score
    issue_count = len(ops_with_issues)
    if error_rate >= ERROR_RATE_CRITICAL:
        health_score = max(0, 30 - (error_count * 5))
        status = "error"
    elif error_rate >= ERROR_RATE_WARNING:
        health_score = max(50, 70 - (error_count * 3))
        status = "warning"
    elif issue_count > 0:
        health_score = max(70, 90 - (issue_count * 5))
        status = "warning"
    else:
        health_score = 100.0
        status = "ok"
    
    return QualityStoryResponse(
        status=status,
        health_score=health_score,
        summary=QualitySummary(
            total_calls=total_calls,
            issue_count=issue_count,
            error_count=error_count,
            error_rate=error_rate,
            error_rate_formatted=format_percentage(error_rate),
            success_count=success_count,
            success_rate=success_rate,
            avg_quality_score=avg_quality,
            hallucination_count=len(hallucinations),
            operations_affected=operations_affected,
        ),
        top_offender=top_offender,
        detail_table=detail_table,
        chart_data=chart_data,
        recommendations=get_story_recommendations('quality'),
    )