"""
Latency Service - Story 1 Business Logic
Location: api/services/latency_service.py

Handles all latency analysis logic for Layer 1 and Layer 2.
Returns proper LatencyStoryResponse model.
"""

from typing import List, Dict, Any
from collections import defaultdict
from api.config.story_definitions import get_story_recommendations
from api.models import LatencyStoryResponse, LatencySummary, TopOffender
from api.utils.formatters import format_latency

# Thresholds
LATENCY_WARNING_MS = 5000
LATENCY_CRITICAL_MS = 10000


def get_summary(calls: List[Dict], project: str = None, days: int = 7) -> LatencyStoryResponse:
    """
    Layer 1: Latency summary with KPI cards + table.
    
    Args:
        calls: List of LLM call dictionaries
        project: Project name filter
        days: Number of days analyzed
    
    Returns:
        LatencyStoryResponse model with complete story data
    """
    if not calls:
        return LatencyStoryResponse(
            status="ok",
            health_score=100.0,
            summary=LatencySummary(
                total_calls=0,
                issue_count=0,
                total_slow_calls=0,
                avg_latency_ms=0,
                avg_latency="0ms",
                critical_count=0,
                warning_count=0,
            ),
            top_offender=None,
            detail_table=[],
            chart_data=[],
            recommendations=[],
        )
    
    # Calculate metrics
    latencies = [c.get('latency_ms', 0) for c in calls]
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    
    # Group by operation
    by_operation = defaultdict(list)
    for call in calls:
        op = f"{call.get('agent_name', 'Unknown')}.{call.get('operation', 'unknown')}"
        by_operation[op].append(call)
    
    # Build detail table
    detail_table = []
    slow_operations = []
    critical_count = 0
    warning_count = 0
    total_slow_calls = 0
    
    for op, op_calls in by_operation.items():
        op_latencies = [c.get('latency_ms', 0) for c in op_calls]
        avg = sum(op_latencies) / len(op_latencies)
        max_lat = max(op_latencies)
        
        is_critical = avg > LATENCY_CRITICAL_MS
        is_warning = avg > LATENCY_WARNING_MS
        
        if is_critical:
            status = "🔴"
            critical_count += 1
            total_slow_calls += len(op_calls)
            slow_operations.append((op, avg, op_calls))
        elif is_warning:
            status = "🟡"
            warning_count += 1
            total_slow_calls += len(op_calls)
            slow_operations.append((op, avg, op_calls))
        else:
            status = "🟢"
        
        detail_table.append({
            'status': status,
            'operation': op,
            'agent_name': op_calls[0].get('agent_name', 'Unknown'),
            'avg_latency_ms': round(avg, 1),
            'avg_latency': format_latency(avg),
            'max_latency_ms': round(max_lat, 1),
            'max_latency': format_latency(max_lat),
            'call_count': len(op_calls),
            'is_slow': is_critical or is_warning,
        })
    
    # Sort by avg latency (slowest first)
    detail_table.sort(key=lambda x: -x['avg_latency_ms'])
    
    # Build chart data (top 10 slowest operations)
    chart_data = [
        {
            'name': row['operation'],
            'avg_latency_ms': row['avg_latency_ms'],
            'call_count': row['call_count'],
        }
        for row in detail_table[:10]
    ]
    
    # Determine top offender
    top_offender = None
    if slow_operations:
        slow_operations.sort(key=lambda x: -x[1])  # Sort by avg latency
        top_op, top_avg, top_calls = slow_operations[0]
        
        agent, operation = top_op.split('.', 1) if '.' in top_op else ('Unknown', top_op)
        
        top_offender = TopOffender(
            agent=agent,
            operation=operation,
            value=top_avg,
            value_formatted=format_latency(top_avg),
            call_count=len(top_calls),
            diagnosis=_diagnose_latency(top_avg, top_calls),
        )
    
    # Calculate health score
    issue_count = critical_count + warning_count
    if issue_count == 0:
        health_score = 100.0
    elif critical_count > 0:
        health_score = max(0, 50 - (critical_count * 10))
    else:
        health_score = max(50, 85 - (warning_count * 5))
    
    # Determine status
    if critical_count > 0:
        status = "error"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "ok"
    
    return LatencyStoryResponse(
        status=status,
        health_score=health_score,
        summary=LatencySummary(
            total_calls=len(calls),
            issue_count=issue_count,
            total_slow_calls=total_slow_calls,
            avg_latency_ms=round(avg_latency, 1),
            avg_latency=format_latency(avg_latency),
            critical_count=critical_count,
            warning_count=warning_count,
        ),
        top_offender=top_offender,
        detail_table=detail_table,
        chart_data=chart_data,
        recommendations=get_story_recommendations('latency'),
    )


def _diagnose_latency(avg_latency: float, calls: List[Dict]) -> str:
    """Generate diagnosis for slow operation."""
    avg_completion = sum(c.get('completion_tokens', 0) for c in calls) / len(calls) if calls else 0
    avg_prompt = sum(c.get('prompt_tokens', 0) for c in calls) / len(calls) if calls else 0
    
    if avg_completion > 1500:
        return f"High completion tokens ({avg_completion:.0f}) - constrain output format"
    elif avg_prompt > 4000:
        return f"Large prompt ({avg_prompt:.0f} tokens) - reduce context or use caching"
    else:
        return "Consider faster model or optimize prompt"