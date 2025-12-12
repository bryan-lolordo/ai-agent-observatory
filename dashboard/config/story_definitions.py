"""
Story Definitions - Metadata for Optimization Stories
Location: dashboard/config/story_definitions.py

Defines story metadata, thresholds, and target pages.
Used by story cards and drill-down navigation.

Usage:
    from dashboard.config.story_definitions import get_story_definition
    
    story = get_story_definition("latency")
    # Returns: {
    #     "id": "latency",
    #     "title": "Latency Monster",
    #     "icon": "🐌",
    #     "target_page": "🔀 Model Router",
    #     ...
    # }
"""

from typing import Dict, Any, Optional, List


# =============================================================================
# STORY DEFINITIONS
# =============================================================================

STORY_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # Story 1: Latency Monster
    # -------------------------------------------------------------------------
    "latency": {
        "id": "latency",
        "title": "Latency Monster",
        "icon": "🐌",
        "description": "Operations with excessive response times",
        "target_page": "🔀 Model Router",
        "filter_key": "latency_filter",
        "thresholds": {
            "warning_ms": 5000,
            "critical_ms": 10000,
        },
        "color": {
            "issue": "#FF6B6B",
            "ok": "#51CF66",
        },
        "recommendations": [
            "Constrain output format to reduce completion tokens",
            "Use streaming for better perceived performance",
            "Route to faster model for simple operations",
            "Implement response caching",
        ],
    },
    
    # -------------------------------------------------------------------------
    # Story 2: Zero Cache Hits
    # -------------------------------------------------------------------------
    "cache": {
        "id": "cache",
        "title": "Zero Cache Hits",
        "icon": "💾",
        "description": "Duplicate prompts that could be cached",
        "target_page": "💾 Cache Analyzer",
        "filter_key": "cache_filter",
        "thresholds": {
            "opportunity_pct": 0.20,
            "min_duplicates": 2,
        },
        "color": {
            "issue": "#FF6B6B",
            "ok": "#51CF66",
        },
        "recommendations": [
            "Enable semantic caching for repeated queries",
            "Use content hashing for cache keys",
            "Set appropriate TTL based on data freshness needs",
            "Normalize prompts before caching",
        ],
    },
    
    # -------------------------------------------------------------------------
    # Story 3: Cost Concentration
    # -------------------------------------------------------------------------
    "cost": {
        "id": "cost",
        "title": "Cost Concentration",
        "icon": "💰",
        "description": "Where your money is going",
        "target_page": "💰 Cost Estimator",
        "filter_key": "cost_filter",
        "thresholds": {
            "concentration_pct": 0.70,
            "top_n": 3,
        },
        "color": {
            "issue": "#FFA94D",
            "ok": "#51CF66",
        },
        "recommendations": [
            "Route expensive operations to cheaper models when possible",
            "Implement caching for high-cost operations",
            "Reduce prompt size to lower token costs",
            "Consider batch processing for bulk operations",
        ],
    },
    
    # -------------------------------------------------------------------------
    # Story 4: System Prompt Waste
    # -------------------------------------------------------------------------
    "system_prompt": {
        "id": "system_prompt",
        "title": "System Prompt Waste",
        "icon": "📝",
        "description": "Redundant system prompt tokens",
        "target_page": "✨ Prompt Optimizer",
        "filter_key": "system_prompt_filter",
        "thresholds": {
            "waste_pct": 0.30,
            "high_tokens": 1000,
        },
        "color": {
            "issue": "#FFA94D",
            "ok": "#51CF66",
        },
        "recommendations": [
            "Compress system prompts (60-70% reduction possible)",
            "Enable prompt caching for repeated system prompts",
            "Move static instructions to few-shot examples",
            "Use prompt versioning to track improvements",
        ],
    },
    
    # -------------------------------------------------------------------------
    # Story 5: Token Imbalance
    # -------------------------------------------------------------------------
    "token_imbalance": {
        "id": "token_imbalance",
        "title": "Token Imbalance",
        "icon": "⚖️",
        "description": "Poor prompt:completion ratios",
        "target_page": "✨ Prompt Optimizer",
        "filter_key": "token_imbalance_filter",
        "thresholds": {
            "warning_ratio": 10,
            "critical_ratio": 20,
        },
        "color": {
            "issue": "#FFA94D",
            "ok": "#51CF66",
        },
        "recommendations": [
            "Implement sliding window for chat history",
            "Summarize long conversations periodically",
            "Reduce context to only what's needed",
            "Use conversation memory instead of full history",
        ],
    },
    
    # -------------------------------------------------------------------------
    # Story 6: Model Routing
    # -------------------------------------------------------------------------
    "routing": {
        "id": "routing",
        "title": "Model Routing",
        "icon": "🔀",
        "description": "Complexity mismatches",
        "target_page": "🔀 Model Router",
        "filter_key": "routing_filter",
        "thresholds": {
            "high_complexity": 0.7,
            "low_complexity": 0.3,
        },
        "color": {
            "issue": "#FF6B6B",
            "ok": "#51CF66",
        },
        "recommendations": [
            "Route high-complexity tasks to capable models",
            "Use cheaper models for simple operations",
            "Implement complexity scoring for routing decisions",
            "A/B test routing strategies",
        ],
    },
    
    # -------------------------------------------------------------------------
    # Story 7: Quality Issues
    # -------------------------------------------------------------------------
    "quality": {
        "id": "quality",
        "title": "Quality Issues",
        "icon": "❌",
        "description": "Errors and hallucinations",
        "target_page": "⚖️ LLM Judge",
        "filter_key": "quality_filter",
        "thresholds": {
            "warning_rate": 0.02,
            "critical_rate": 0.05,
        },
        "color": {
            "issue": "#FF6B6B",
            "ok": "#51CF66",
        },
        "recommendations": [
            "Add validation for critical outputs",
            "Implement LLM-as-judge for quality monitoring",
            "Use structured output formats",
            "Add retry logic with fallback models",
        ],
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_story_definition(story_id: str) -> Optional[Dict[str, Any]]:
    """
    Get story definition by ID.
    
    Args:
        story_id: Story identifier (e.g., "latency", "cache")
    
    Returns:
        Story definition dict or None if not found
    """
    return STORY_DEFINITIONS.get(story_id)


def get_target_page(story_id: str) -> Optional[str]:
    """
    Get target page for a story.
    
    Args:
        story_id: Story identifier
    
    Returns:
        Target page name or None if not found
    """
    story = STORY_DEFINITIONS.get(story_id)
    if not story:
        return None
    return story.get("target_page")


def get_story_recommendations(story_id: str) -> List[str]:
    """
    Get recommendations for a story.
    
    Args:
        story_id: Story identifier
    
    Returns:
        List of recommendation strings
    """
    story = STORY_DEFINITIONS.get(story_id)
    if not story:
        return []
    return story.get("recommendations", [])


def get_story_thresholds(story_id: str) -> Dict[str, Any]:
    """
    Get thresholds for a story.
    
    Args:
        story_id: Story identifier
    
    Returns:
        Dict of threshold values
    """
    story = STORY_DEFINITIONS.get(story_id)
    if not story:
        return {}
    return story.get("thresholds", {})


def get_all_story_ids() -> List[str]:
    """Get list of all story IDs."""
    return list(STORY_DEFINITIONS.keys())


def get_stories_by_target_page(target_page: str) -> List[Dict[str, Any]]:
    """
    Get all stories that target a specific page.
    
    Args:
        target_page: Page name (e.g., "🔀 Model Router")
    
    Returns:
        List of story definitions
    """
    return [
        story for story in STORY_DEFINITIONS.values()
        if story.get("target_page") == target_page
    ]