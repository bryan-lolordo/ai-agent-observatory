"""
Latency Service - Story 1 Business Logic
Location: api/services/latency_service.py

Handles all latency analysis logic for Layer 1 and Layer 2.
"""

from typing import List, Dict, Any
from api.config.story_definitions import get_story_recommendations

# Thresholds
LATENCY_WARNING_MS = 5000
LATENCY_CRITICAL_MS = 10000


def get_summary(calls: List[Dict], project: str, days: int) -> Dict[str, Any]:
    """
    Layer 1: Latency summary with KPI cards + table.
    
    Args:
        calls: List of LLM call dictionaries
        project: Project name filter
        days: Number of days analyzed
    
    Returns:
        {
            "kpi_cards": {...},
            "table": [...],
            "insights": [...],
            "meta": {...}
        }
    """
    if not calls:
        return {
            "kpi_cards": {
                "avg_latency_ms": 0,
                "slow_ops_count": 0,
                "max_latency_ms": 0,
            },
            "table": [],
            "insights": ["No calls found"],
            "meta": {
                "calls_analyzed": 0,
                "days": days,
                "project": project,
            }
        }
    
    # Calculate KPI cards
    latencies = [c.get('latency_ms', 0) for c in calls]
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    
    # Group by operation
    by_operation = {}
    for call in calls:
        op = call.get('operation', 'unknown')
        if op not in by_operation:
            by_operation[op] = []
        by_operation[op].append(call)
    
    # Build table
    table = []
    slow_count = 0
    
    for op, op_calls in by_operation.items():
        op_latencies = [c.get('latency_ms', 0) for c in op_calls]
        avg = sum(op_latencies) / len(op_latencies)
        max_lat = max(op_latencies)
        
        is_slow = avg > LATENCY_WARNING_MS
        if is_slow:
            slow_count += 1
        
        table.append({
            'status': '🔴' if is_slow else '🟢',
            'operation': op,
            'agent_name': op_calls[0].get('agent_name', 'Unknown'),
            'avg_latency_ms': round(avg, 1),
            'max_latency_ms': round(max_lat, 1),
            'call_count': len(op_calls),
        })
    
    # Sort by avg latency (slowest first)
    table.sort(key=lambda x: -x['avg_latency_ms'])
    
    # Generate insights
    insights = []
    if slow_count > 0:
        insights.append(f"{slow_count} operations exceed {LATENCY_WARNING_MS/1000}s threshold")
        top_slow = table[0]
        insights.append(
            f"Slowest: {top_slow['operation']} ({top_slow['avg_latency_ms']/1000:.1f}s avg)"
        )
    else:
        insights.append("All operations performing well")
    
    return {
        "kpi_cards": {
            "avg_latency_ms": round(avg_latency, 1),
            "slow_ops_count": slow_count,
            "max_latency_ms": round(max_latency, 1),
        },
        "table": table,
        "insights": insights,
        "meta": {
            "calls_analyzed": len(calls),
            "days": days,
            "project": project,
        }
    }


def get_operation_detail(
    calls: List[Dict], 
    operation: str, 
    project: str, 
    days: int
) -> Dict[str, Any]:
    """
    Layer 2: Operation drill-down with call details.
    
    Args:
        calls: List of LLM calls for this operation
        operation: Operation name
        project: Project name filter
        days: Number of days analyzed
    
    Returns:
        {
            "operation_summary": {...},
            "calls_table": [...],
            "pattern": {...},
            "recommendations": [...]
        }
    """
    if not calls:
        return {
            "error": f"No calls found for operation: {operation}",
            "operation": operation,
        }
    
    # Calculate operation summary
    latencies = [c.get('latency_ms', 0) for c in calls]
    avg_latency = sum(latencies) / len(latencies)
    
    avg_prompt = sum(c.get('prompt_tokens', 0) for c in calls) / len(calls)
    avg_completion = sum(c.get('completion_tokens', 0) for c in calls) / len(calls)
    total_cost = sum(c.get('total_cost', 0) for c in calls)
    
    # Build calls table
    calls_table = [
        {
            'id': c['id'],
            'prompt_preview': (c.get('prompt', '') or '')[:50] + '...',
            'latency_ms': round(c.get('latency_ms', 0), 1),
            'prompt_tokens': c.get('prompt_tokens', 0),
            'completion_tokens': c.get('completion_tokens', 0),
            'total_cost': round(c.get('total_cost', 0), 4),
        }
        for c in calls
    ]
    
    # Sort by latency (slowest first)
    calls_table.sort(key=lambda x: -x['latency_ms'])
    
    # Detect pattern
    pattern_type = None
    pattern_message = None
    
    if avg_completion > 1500:
        pattern_type = "high_completion"
        pattern_message = f"All calls have ~{avg_completion:.0f} completion tokens - high output volume likely causing slow response"
    elif avg_prompt > 3000:
        pattern_type = "high_prompt"
        pattern_message = f"Large prompts (~{avg_prompt:.0f} tokens) may be contributing to latency"
    
    return {
        "operation_summary": {
            "operation": operation,
            "agent_name": calls[0].get('agent_name', 'Unknown'),
            "avg_latency_ms": round(avg_latency, 1),
            "avg_prompt_tokens": round(avg_prompt, 0),
            "avg_completion_tokens": round(avg_completion, 0),
            "total_cost": round(total_cost, 4),
            "call_count": len(calls),
        },
        "calls_table": calls_table,
        "pattern": {
            "type": pattern_type,
            "message": pattern_message,
        },
        "recommendations": get_story_recommendations('latency'),
        "meta": {
            "calls_analyzed": len(calls),
            "days": days,
            "project": project,
        }
    }