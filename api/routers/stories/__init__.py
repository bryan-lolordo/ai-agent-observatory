"""
Stories Router Package
Location: api/routers/stories/__init__.py

FIXED: Uses correct field names from actual service outputs.

Each story returns:
- health_score: 0-100
- hero_metric: The big number (e.g., "2.1s", "$4.56")
- hero_label: Description of the metric
- issue_count: Number of issues found
- issue_label: What the issues are
- savings: What you'd gain by fixing
"""

from fastapi import APIRouter, Query
from typing import Optional

# Import all story routers
from .latency import router as latency_router
from .cache import router as cache_router
from .routing import router as routing_router
from .quality import router as quality_router
from .token import router as token_router
from .prompt import router as prompt_router
from .cost import router as cost_router
from .optimization import router as optimization_router

# Import services for summary endpoint
from api.services import (
    get_latency_summary,
    get_cache_summary,
    get_routing_summary,
    get_quality_summary,
    get_token_summary,
    get_prompt_summary,
    get_cost_summary,
    get_optimization_summary,
)
from ._helpers import get_filtered_calls


# =============================================================================
# HELPERS
# =============================================================================

def _get_health_score(story_result) -> float:
    """Extract health_score from either a dict or Pydantic model."""
    if hasattr(story_result, 'health_score'):
        return story_result.health_score
    elif isinstance(story_result, dict) and 'health_score' in story_result:
        return story_result['health_score']
    return 0.0


def _normalize_story_result(story_result) -> dict:
    """Convert Pydantic model to dict if needed."""
    if hasattr(story_result, 'model_dump'):
        return story_result.model_dump()
    elif hasattr(story_result, 'dict'):
        return story_result.dict()
    elif isinstance(story_result, dict):
        return story_result
    return {}


# =============================================================================
# STORY DATA EXTRACTORS (FIXED FIELD NAMES)
# =============================================================================

def _extract_latency_data(story_data: dict) -> dict:
    """Extract opportunity data for Latency story."""
    summary = story_data.get('summary', {})
    
    avg_latency = summary.get('avg_latency', '—')
    avg_latency_ms = summary.get('avg_latency_ms', 0)
    critical = summary.get('critical_count', 0)
    warning = summary.get('warning_count', 0)
    issue_count = critical + warning
    
    # Calculate potential savings
    slow_calls = summary.get('total_slow_calls', 0)
    savings = ""
    if slow_calls > 0 and avg_latency_ms > 5000:
        potential_save = (avg_latency_ms - 2000) / 1000  # Target 2s
        savings = f"Save ~{potential_save:.1f}s/request"
    elif issue_count > 0:
        savings = "Reduce response times"
    
    return {
        "health_score": story_data.get('health_score', 0),
        "hero_metric": avg_latency,
        "hero_label": "avg response time",
        "issue_count": issue_count,
        "issue_label": "slow operations" if issue_count != 1 else "slow operation",
        "savings": savings,
        **story_data,
    }


def _extract_cache_data(story_data: dict) -> dict:
    """Extract opportunity data for Cache story.
    
    FIXED: Uses correct field names:
    - hit_rate (not cache_hit_rate)
    - duplicate_prompts (not duplicate_count)
    - potential_savings (not wasted_cost)
    """
    summary = story_data.get('summary', {})
    
    # FIXED: Correct field names
    hit_rate = summary.get('hit_rate', 0) * 100  # Convert 0-1 to percentage
    duplicate_count = summary.get('duplicate_prompts', 0)
    potential_savings = summary.get('potential_savings', 0)
    issue_count = summary.get('issue_count', 0)
    
    # Format hero metric
    hero_metric = f"{hit_rate:.0f}%"
    
    # Calculate savings
    savings = ""
    if potential_savings > 0:
        savings = f"Save ${potential_savings:.2f}/day"
    elif duplicate_count > 0:
        savings = "Reduce redundant calls"
    elif issue_count == 0:
        savings = "✓ No issues detected"
    
    return {
        "health_score": story_data.get('health_score', 0),
        "hero_metric": hero_metric,
        "hero_label": "cache hit rate",
        "issue_count": issue_count if issue_count > 0 else duplicate_count,
        "issue_label": "cacheable operations" if issue_count != 1 else "cacheable operation",
        "savings": savings,
        **story_data,
    }


def _extract_routing_data(story_data: dict) -> dict:
    """Extract opportunity data for Routing story.
    
    FIXED: Uses correct field names:
    - upgrade_count (not upgrade_candidates)
    - downgrade_count (not downgrade_candidates)
    - current_model (models_used doesn't exist)
    """
    summary = story_data.get('summary', {})
    
    # FIXED: Correct field names
    upgrade_count = summary.get('upgrade_count', 0)
    downgrade_count = summary.get('downgrade_count', 0)
    total_opportunities = upgrade_count + downgrade_count
    potential_savings = summary.get('potential_savings', 0)
    
    # FIXED: Use current_model, not models_used
    current_model = summary.get('current_model', 'unknown')
    # Just show "1 model" since we only have one model type
    hero_metric = "1 model"
    
    # Potential savings
    savings = ""
    if potential_savings > 0:
        savings = f"Save ${potential_savings:.2f}/day"
    elif downgrade_count > 0:
        savings = f"Downgrade {downgrade_count} ops"
    elif upgrade_count > 0:
        savings = f"Upgrade {upgrade_count} for quality"
    elif total_opportunities == 0:
        savings = "✓ No issues detected"
    
    return {
        "health_score": story_data.get('health_score', 0),
        "hero_metric": hero_metric,
        "hero_label": "in use",
        "issue_count": total_opportunities,
        "issue_label": "routing opportunities" if total_opportunities != 1 else "routing opportunity",
        "savings": savings,
        **story_data,
    }


def _extract_quality_data(story_data: dict) -> dict:
    """Extract opportunity data for Quality story.
    
    FIXED: Uses correct field names:
    - avg_quality (not avg_score or avg_quality_score)
    - low_quality_count (not low_quality_ops_count)
    """
    summary = story_data.get('summary', {})
    
    # FIXED: Correct field name is avg_quality
    avg_score = summary.get('avg_quality')
    low_quality_count = summary.get('low_quality_count', 0)
    error_rate = summary.get('error_rate', 0)
    error_count = summary.get('error_count', 0)
    
    # Format hero metric
    hero_metric = f"{avg_score:.1f}/10" if avg_score else "—"
    
    # Issue count: low quality ops
    issue_count = low_quality_count
    
    # Savings/benefit
    savings = ""
    if low_quality_count > 0:
        savings = "Improve response quality"
    elif error_rate > 2:
        savings = f"Reduce {error_rate:.1f}% error rate"
    elif error_count == 0 and (avg_score is None or avg_score >= 7):
        savings = "✓ No issues detected"
    
    return {
        "health_score": story_data.get('health_score', 0),
        "hero_metric": hero_metric,
        "hero_label": "avg quality score",
        "issue_count": issue_count,
        "issue_label": "ops below threshold" if issue_count != 1 else "op below threshold",
        "savings": savings,
        **story_data,
    }


def _extract_token_data(story_data: dict) -> dict:
    """Extract opportunity data for Token Efficiency story.
    
    FIXED: Uses correct field names:
    - imbalanced_count (not imbalanced_ops_count)
    """
    summary = story_data.get('summary', {})
    
    avg_ratio = summary.get('avg_ratio', 0)
    # FIXED: Correct field name
    imbalanced_count = summary.get('imbalanced_count', 0)
    wasted_cost = summary.get('wasted_cost', 0)
    
    # Format hero metric
    hero_metric = f"{avg_ratio:.1f}:1" if avg_ratio else "—"
    
    # Savings
    savings = ""
    if wasted_cost > 0:
        savings = f"Save ${wasted_cost:.2f}/day"
    elif imbalanced_count > 0:
        savings = "Optimize token usage"
    elif imbalanced_count == 0:
        savings = "✓ No issues detected"
    
    return {
        "health_score": story_data.get('health_score', 0),
        "hero_metric": hero_metric,
        "hero_label": "prompt:completion ratio",
        "issue_count": imbalanced_count,
        "issue_label": "imbalanced operations" if imbalanced_count != 1 else "imbalanced operation",
        "savings": savings,
        **story_data,
    }


def _extract_prompt_data(story_data: dict) -> dict:
    """Extract opportunity data for Prompt Composition story."""
    summary = story_data.get('summary', {})
    
    cache_ready = summary.get('cache_ready_count', 0)
    total_ops = summary.get('total_operations', 0)
    not_ready = total_ops - cache_ready if total_ops > 0 else 0
    
    # Calculate percentage
    if total_ops > 0:
        pct = (cache_ready / total_ops) * 100
        hero_metric = f"{pct:.0f}%"
    else:
        hero_metric = "—"
    
    # Savings
    savings = ""
    if not_ready > 0:
        savings = "Enable prefix caching"
    elif total_ops > 0:
        savings = "✓ All cache-ready"
    
    return {
        "health_score": story_data.get('health_score', 0),
        "hero_metric": hero_metric,
        "hero_label": "cache-ready operations",
        "issue_count": not_ready,
        "issue_label": "need restructuring" if not_ready != 1 else "needs restructuring",
        "savings": savings,
        **story_data,
    }


def _extract_cost_data(story_data: dict) -> dict:
    """Extract opportunity data for Cost story."""
    summary = story_data.get('summary', {})
    
    total_cost = summary.get('total_cost', 0)
    potential_savings = summary.get('potential_savings', 0)
    concentration = summary.get('top_3_concentration', 0)
    issue_count_from_summary = summary.get('issue_count', 0)
    
    # Format hero metric
    if isinstance(total_cost, (int, float)):
        hero_metric = f"${total_cost:.2f}"
    else:
        hero_metric = str(total_cost) if total_cost else "$0.00"
    
    # Issue: high concentration or high-cost ops
    issue_count = issue_count_from_summary
    issue_label = "concentration issues"
    if concentration > 0.80:
        issue_count = max(issue_count, 3)
        issue_label = "ops = 80%+ of cost"
    elif concentration > 0.60:
        issue_count = max(issue_count, 3)
        issue_label = "ops = 60%+ of cost"
    
    # Savings
    savings = ""
    if potential_savings > 0:
        savings = f"Save ${potential_savings:.2f}/week"
    elif concentration > 0.60:
        savings = "Reduce cost concentration"
    elif issue_count == 0:
        savings = "✓ No issues detected"
    
    return {
        "health_score": story_data.get('health_score', 0),
        "hero_metric": hero_metric,
        "hero_label": "total this period",
        "issue_count": issue_count,
        "issue_label": issue_label,
        "savings": savings,
        **story_data,
    }


def _extract_optimization_data(story_data: dict) -> dict:
    """Extract opportunity data for Optimization Impact story."""
    summary = story_data.get('summary', {})
    
    mode = story_data.get('mode') or summary.get('mode', 'baseline')
    total_savings = summary.get('total_savings') or summary.get('cost_saved', 0)
    pending_count = summary.get('pending_optimizations', 0)
    active_count = summary.get('active_optimizations', 0)
    
    # Hero metric depends on mode
    if mode == 'baseline':
        hero_metric = "Baseline"
        hero_label = "collecting data"
        issue_count = pending_count
        issue_label = "optimizations pending" if pending_count != 1 else "optimization pending"
        savings = "Implement & track impact"
    else:
        if total_savings > 0:
            hero_metric = f"${total_savings:.2f}"
            hero_label = "total saved"
        else:
            hero_metric = f"{active_count}"
            hero_label = "active optimizations"
        issue_count = pending_count
        issue_label = "more to implement" if pending_count != 1 else "more to implement"
        savings = "Continue optimizing" if pending_count > 0 else ""
    
    return {
        "health_score": story_data.get('health_score', 0),
        "hero_metric": hero_metric,
        "hero_label": hero_label,
        "issue_count": issue_count,
        "issue_label": issue_label,
        "savings": savings,
        **story_data,
    }


# Mapping of story_id to extractor function
STORY_EXTRACTORS = {
    "latency": _extract_latency_data,
    "cache": _extract_cache_data,
    "routing": _extract_routing_data,
    "quality": _extract_quality_data,
    "token_imbalance": _extract_token_data,
    "system_prompt": _extract_prompt_data,
    "cost": _extract_cost_data,
    "optimization": _extract_optimization_data,
}


# =============================================================================
# MAIN ROUTER
# =============================================================================

router = APIRouter(prefix="/api/stories", tags=["stories"])


# =============================================================================
# ALL STORIES SUMMARY (Dashboard Endpoint)
# =============================================================================

@router.get("", response_model=dict)
def get_all_stories(
    project: Optional[str] = None,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=2000, le=5000),
):
    """
    Get all story summaries for dashboard display.
    
    Returns opportunity-focused data for each story:
    - health_score: 0-100
    - hero_metric: Primary metric value (e.g., "2.1s")
    - hero_label: Metric description (e.g., "avg response time")
    - issue_count: Number of issues found
    - issue_label: What the issues are
    - savings: Potential benefit from fixing
    """
    calls = get_filtered_calls(project, days, limit)
    
    # Get raw results from all services
    raw_stories = {
        "latency": get_latency_summary(calls, project, days),
        "cache": get_cache_summary(calls, project, days),
        "routing": get_routing_summary(calls, project, days),
        "quality": get_quality_summary(calls, project, days),
        "token_imbalance": get_token_summary(calls, project, days),
        "system_prompt": get_prompt_summary(calls, project, days),
        "cost": get_cost_summary(calls, project, days),
        "optimization": get_optimization_summary(calls, project, days),
    }
    
    # Transform each story with opportunity-focused data
    stories = {}
    for story_id, raw_result in raw_stories.items():
        normalized = _normalize_story_result(raw_result)
        extractor = STORY_EXTRACTORS.get(story_id)
        if extractor:
            stories[story_id] = extractor(normalized)
        else:
            stories[story_id] = normalized
    
    # Calculate overall health
    health_scores = [s.get('health_score', 0) for s in stories.values()]
    overall_health = sum(health_scores) / len(health_scores) if health_scores else 0
    
    # Build global summary for KPI cards
    latency_summary = stories.get('latency', {}).get('summary', {})
    cost_summary = stories.get('cost', {}).get('summary', {})
    quality_summary = stories.get('quality', {}).get('summary', {})
    
    total_cost = cost_summary.get('total_cost', 0)
    if isinstance(total_cost, (int, float)):
        total_cost_str = f"${total_cost:.2f}"
    else:
        total_cost_str = str(total_cost)
    
    # FIXED: Use avg_quality not avg_score
    avg_quality = quality_summary.get('avg_quality', 0)
    avg_quality_str = f"{avg_quality:.1f}/10" if avg_quality else "—"
    
    return {
        "overall_health": overall_health,
        "total_calls": len(calls),
        "summary": {
            "total_calls": len(calls),
            "avg_latency": latency_summary.get('avg_latency', '—'),
            "total_cost": total_cost_str,
            "avg_quality": avg_quality_str,
        },
        "stories": stories,
    }


# =============================================================================
# INCLUDE SUB-ROUTERS
# =============================================================================

router.include_router(latency_router)       # /api/stories/latency
router.include_router(cache_router)         # /api/stories/cache
router.include_router(routing_router)       # /api/stories/routing
router.include_router(quality_router)       # /api/stories/quality
router.include_router(token_router)         # /api/stories/token_imbalance
router.include_router(prompt_router)        # /api/stories/system_prompt
router.include_router(cost_router)          # /api/stories/cost
router.include_router(optimization_router)  # /api/stories/optimization


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = ["router"]