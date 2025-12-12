"""
Story Definitions Configuration
Location: api/config/story_definitions.py

Defines metadata, thresholds, and recommendations for each optimization story.

TODO: Replace this placeholder with your actual story_definitions.py from dashboard/config/
"""

from typing import Dict, Any, List, Optional


# =============================================================================
# STORY DEFINITIONS
# =============================================================================

STORY_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "latency": {
        "id": "latency",
        "title": "Latency Monster",
        "icon": "🐌",
        "description": "Operations with excessive response times that hurt user experience",
        "target_page": "Model Router",
        "thresholds": {
            "warning_ms": 5000,
            "critical_ms": 10000,
        },
        "data_columns": ["latency_ms", "completion_tokens", "model_name"],
    },
    "cache": {
        "id": "cache",
        "title": "Zero Cache Hits",
        "icon": "💾",
        "description": "Duplicate prompts that could be cached to save cost and time",
        "target_page": "Cache Analyzer",
        "thresholds": {
            "redundancy_pct": 0.20,
            "min_duplicates": 2,
        },
        "data_columns": ["prompt", "prompt_tokens", "total_cost"],
    },
    "cost": {
        "id": "cost",
        "title": "Cost Concentration",
        "icon": "💰",
        "description": "Identifies where the majority of spending is concentrated",
        "target_page": "Cost Estimator",
        "thresholds": {
            "concentration_threshold": 0.70,
        },
        "data_columns": ["total_cost", "agent_name", "operation"],
    },
    "system_prompt": {
        "id": "system_prompt",
        "title": "System Prompt Waste",
        "icon": "📝",
        "description": "Large system prompts sent repeatedly that could be optimized",
        "target_page": "Prompt Optimizer",
        "thresholds": {
            "waste_pct": 0.30,
            "high_tokens": 1000,
        },
        "data_columns": ["prompt_breakdown", "prompt_tokens"],
    },
    "token_imbalance": {
        "id": "token_imbalance",
        "title": "Token Imbalance",
        "icon": "⚖️",
        "description": "Operations sending lots of tokens but receiving little output",
        "target_page": "Prompt Optimizer",
        "thresholds": {
            "warning_ratio": 10,
            "critical_ratio": 20,
        },
        "data_columns": ["prompt_tokens", "completion_tokens"],
    },
    "routing": {
        "id": "routing",
        "title": "Model Routing",
        "icon": "🔀",
        "description": "Complex tasks on cheap models or simple tasks on expensive models",
        "target_page": "Model Router",
        "thresholds": {
            "complexity_threshold": 0.7,
        },
        "data_columns": ["model_name", "routing_decision", "complexity_score"],
    },
    "quality": {
        "id": "quality",
        "title": "Quality Issues",
        "icon": "❌",
        "description": "Errors, hallucinations, and low-quality responses",
        "target_page": "LLM Judge",
        "thresholds": {
            "error_rate_warning": 0.02,
            "error_rate_critical": 0.05,
        },
        "data_columns": ["success", "error", "quality_evaluation"],
    },
}


# =============================================================================
# STORY RECOMMENDATIONS
# =============================================================================

STORY_RECOMMENDATIONS: Dict[str, List[Dict[str, str]]] = {
    "latency": [
        {
            "title": "Reduce completion tokens",
            "description": "Constrain output format with JSON schema or explicit length limits",
            "impact": "High",
        },
        {
            "title": "Use streaming",
            "description": "Stream responses to improve perceived performance",
            "impact": "Medium",
        },
        {
            "title": "Switch to faster model",
            "description": "Use gpt-4o-mini or claude-3-haiku for simple operations",
            "impact": "High",
        },
    ],
    "cache": [
        {
            "title": "Enable prompt caching",
            "description": "Cache repeated prompts with semantic similarity matching",
            "impact": "High",
        },
        {
            "title": "Normalize prompts",
            "description": "Remove variable content before caching (timestamps, IDs)",
            "impact": "Medium",
        },
        {
            "title": "Set appropriate TTL",
            "description": "Configure cache expiration based on data freshness needs",
            "impact": "Low",
        },
    ],
    "cost": [
        {
            "title": "Optimize high-cost operations",
            "description": "Focus optimization efforts on the top 3 cost contributors",
            "impact": "High",
        },
        {
            "title": "Implement model routing",
            "description": "Route simple requests to cheaper models automatically",
            "impact": "High",
        },
        {
            "title": "Reduce prompt size",
            "description": "Compress or summarize context to reduce input tokens",
            "impact": "Medium",
        },
    ],
    "system_prompt": [
        {
            "title": "Compress system prompt",
            "description": "Use bullet points and remove redundant instructions",
            "impact": "High",
        },
        {
            "title": "Enable prompt caching",
            "description": "Cache the system prompt portion across calls",
            "impact": "High",
        },
        {
            "title": "Use prompt templates",
            "description": "Extract common patterns into reusable templates",
            "impact": "Medium",
        },
    ],
    "token_imbalance": [
        {
            "title": "Implement sliding window",
            "description": "Limit chat history to last N messages",
            "impact": "High",
        },
        {
            "title": "Summarize history",
            "description": "Use a summary of older messages instead of full history",
            "impact": "High",
        },
        {
            "title": "Review context necessity",
            "description": "Ensure all included context is actually needed",
            "impact": "Medium",
        },
    ],
    "routing": [
        {
            "title": "Implement complexity scoring",
            "description": "Score request complexity to route to appropriate model",
            "impact": "High",
        },
        {
            "title": "Define routing rules",
            "description": "Create rules based on operation type, token count, etc.",
            "impact": "Medium",
        },
        {
            "title": "A/B test model choices",
            "description": "Compare quality/cost tradeoffs with different models",
            "impact": "Medium",
        },
    ],
    "quality": [
        {
            "title": "Review error patterns",
            "description": "Analyze common error types to fix root causes",
            "impact": "High",
        },
        {
            "title": "Improve prompts",
            "description": "Add examples and clearer instructions to reduce errors",
            "impact": "High",
        },
        {
            "title": "Add validation",
            "description": "Validate outputs and retry on failure",
            "impact": "Medium",
        },
    ],
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_story_definition(story_id: str) -> Optional[Dict[str, Any]]:
    """Get the definition for a specific story."""
    return STORY_DEFINITIONS.get(story_id)


def get_story_recommendations(story_id: str) -> List[Dict[str, str]]:
    """Get recommendations for a specific story."""
    return STORY_RECOMMENDATIONS.get(story_id, [])


def get_all_story_ids() -> List[str]:
    """Get list of all story IDs."""
    return list(STORY_DEFINITIONS.keys())


def get_story_threshold(story_id: str, threshold_name: str) -> Optional[Any]:
    """Get a specific threshold value for a story."""
    definition = STORY_DEFINITIONS.get(story_id, {})
    thresholds = definition.get("thresholds", {})
    return thresholds.get(threshold_name)