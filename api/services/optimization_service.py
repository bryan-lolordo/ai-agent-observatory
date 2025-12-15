"""
Optimization Service - Story 8 Business Logic
Location: api/services/optimization_service.py

Handles optimization impact tracking (baseline and comparison).
Returns proper OptimizationStoryResponse model.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
from api.models import (
    OptimizationStoryResponse,
    OptimizationSummary,
    BaselineMetrics,
    OptimizationImpactSimple,
)
from api.config.story_definitions import get_story_recommendations
from api.utils.formatters import format_cost, format_latency, format_percentage


def get_summary(
    calls: List[Dict],
    project: str = None,
    days: int = 7,
    optimization_date: Optional[datetime] = None
) -> OptimizationStoryResponse:
    """
    summary: OptimizationStoryResponse = ...
    baseline: BeforeAfterMetrics = ...
    Shows baseline metrics if no optimization_date provided,
    return OptimizationStoryResponse(...)
    
    Args:
        calls: List of LLM call dictionaries
        project: Project name filter
        days: Number of days analyzed
        optimization_date: Date optimization was deployed (optional)
    
    Returns:
        OptimizationStoryResponse model
    """
    if not calls:
        return OptimizationStoryResponse(
            mode="baseline",
            status="ok",
            health_score=100.0,
            summary=OptimizationSummary(
                total_optimizations=0,
                total_cost_saved=0.0,
                total_latency_reduction=0.0,
                avg_quality_improvement=0.0,
            ),
            baseline=None,
            optimizations=[],
            detail_table=[],
            chart_data=[],
            recommendations=[],
        )
    
    # Determine mode
    if optimization_date is None:
        # BASELINE MODE - show current metrics
        return _get_baseline_summary(calls, project, days)
    else:
        # IMPACT MODE - show before/after
        return _get_impact_summary(calls, optimization_date, project, days)


def _get_baseline_summary(
    calls: List[Dict],
    project: str,
    days: int
) -> OptimizationStoryResponse:
    """Generate baseline metrics summary."""
    
    # Calculate baseline metrics
    total_cost = sum(c.get('total_cost', 0) for c in calls)
    latencies = [c.get('latency_ms', 0) for c in calls]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    
    quality_scores = [
        c.get('quality_evaluation', {}).get('judge_score', 0)
        for c in calls
        if c.get('quality_evaluation')
    ]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    # Cache metrics
    cache_hits = sum(1 for c in calls if (c.get('cache_metadata') or {}).get('cache_hit'))
    cache_total = sum(1 for c in calls if c.get('cache_metadata'))
    cache_hit_rate = cache_hits / cache_total if cache_total > 0 else 0
    
    # Error rate
    errors = sum(1 for c in calls if not c.get('success', True))
    error_rate = errors / len(calls) if calls else 0
    
    baseline = BaselineMetrics(
        total_calls=len(calls),
        avg_latency_ms=avg_latency,
        avg_latency=format_latency(avg_latency),
        total_cost=total_cost,
        total_cost_formatted=format_cost(total_cost),
        avg_quality_score=avg_quality,
        cache_hit_rate=cache_hit_rate,
        cache_hit_rate_formatted=format_percentage(cache_hit_rate),
        error_rate=error_rate,
        error_rate_formatted=format_percentage(error_rate),
    )
    
    # Build detail table with baseline by operation
    by_operation = defaultdict(list)
    for call in calls:
        op = f"{call.get('agent_name', 'Unknown')}.{call.get('operation', 'unknown')}"
        by_operation[op].append(call)
    
    detail_table = []
    for op, op_calls in by_operation.items():
        op_latencies = [c.get('latency_ms', 0) for c in op_calls]
        op_cost = sum(c.get('total_cost', 0) for c in op_calls)
        
        detail_table.append({
            'operation': op,
            'call_count': len(op_calls),
            'avg_latency_ms': sum(op_latencies) / len(op_latencies),
            'avg_latency': format_latency(sum(op_latencies) / len(op_latencies)),
            'total_cost': op_cost,
            'total_cost_formatted': format_cost(op_cost),
        })
    
    detail_table.sort(key=lambda x: -x['total_cost'])
    
    # Chart data
    chart_data = [
        {
            'name': row['operation'],
            'latency': row['avg_latency_ms'],
            'cost': row['total_cost'],
        }
        for row in detail_table[:10]
    ]
    
    return OptimizationStoryResponse(
        mode="baseline",
        status="ok",
        health_score=100.0,
        summary=OptimizationSummary(
            total_optimizations=0,
            total_cost_saved=0.0,
            total_latency_reduction=0.0,
            avg_quality_improvement=0.0,
        ),
        baseline=baseline,
        optimizations=[],
        detail_table=detail_table,
        chart_data=chart_data,
        recommendations=get_story_recommendations('cost'),  # Generic optimization recs
    )


def _get_impact_summary(
    calls: List[Dict],
    optimization_date: datetime,
    project: str,
    days: int
) -> OptimizationStoryResponse:
    """Generate before/after impact summary."""
    
    # Split calls into before/after
    before_calls = [c for c in calls if c.get('timestamp') < optimization_date]
    after_calls = [c for c in calls if c.get('timestamp') >= optimization_date]
    
    if not before_calls or not after_calls:
        # Not enough data for comparison
        return _get_baseline_summary(calls, project, days)
    
    # Calculate before metrics
    before_cost = sum(c.get('total_cost', 0) for c in before_calls)
    before_latencies = [c.get('latency_ms', 0) for c in before_calls]
    before_avg_latency = sum(before_latencies) / len(before_latencies)
    
    before_quality = [
        c.get('quality_evaluation', {}).get('judge_score', 0)
        for c in before_calls
        if c.get('quality_evaluation')
    ]
    before_avg_quality = sum(before_quality) / len(before_quality) if before_quality else 0
    
    # Calculate after metrics
    after_cost = sum(c.get('total_cost', 0) for c in after_calls)
    after_latencies = [c.get('latency_ms', 0) for c in after_calls]
    after_avg_latency = sum(after_latencies) / len(after_latencies)
    
    after_quality = [
        c.get('quality_evaluation', {}).get('judge_score', 0)
        for c in after_calls
        if c.get('quality_evaluation')
    ]
    after_avg_quality = sum(after_quality) / len(after_quality) if after_quality else 0
    
    # Calculate improvements
    cost_saved = before_cost - after_cost
    latency_reduction = ((before_avg_latency - after_avg_latency) / before_avg_latency) if before_avg_latency > 0 else 0
    quality_improvement = after_avg_quality - before_avg_quality
    
    # Create optimization impact object
    optimization = OptimizationImpactSimple(
        id="optimization_1",
        name="Optimization Deployed",
        target_operation="all",
        implemented_date=optimization_date,
        before_avg_latency_ms=before_avg_latency,
        after_avg_latency_ms=after_avg_latency,
        before_total_cost=before_cost,
        after_total_cost=after_cost,
        before_avg_quality=before_avg_quality,
        after_avg_quality=after_avg_quality,
        cost_saved=cost_saved,
        latency_reduction_pct=latency_reduction,
        quality_improvement=quality_improvement,
    )
    
    # Health score based on improvements
    if cost_saved > 0 and latency_reduction > 0 and quality_improvement > 0:
        health_score = 100.0
        status = "ok"
    elif cost_saved > 0 or latency_reduction > 0:
        health_score = 85.0
        status = "ok"
    else:
        health_score = 60.0
        status = "warning"
    
    return OptimizationStoryResponse(
        mode="impact",
        status=status,
        health_score=health_score,
        summary=OptimizationSummary(
            total_optimizations=1,
            total_cost_saved=cost_saved,
            total_latency_reduction=latency_reduction,
            avg_quality_improvement=quality_improvement,
        ),
        baseline=None,
        optimizations=[optimization],
        detail_table=[],
        chart_data=[],
        recommendations=[],
    )