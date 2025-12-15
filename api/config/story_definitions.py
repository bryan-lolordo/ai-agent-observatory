"""
Story Definitions Configuration
Location: api/config/story_definitions.py

Defines metadata, thresholds, recommendations, and UI config for each optimization story.
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
# RAINBOW COLOR SCHEME
# =============================================================================

STORY_COLORS: Dict[str, Dict[str, str]] = {
    "latency": {
        "primary": "purple",
        "bg": "bg-purple-600",
        "text": "text-purple-400",
        "border": "border-purple-500",
        "gradient": "from-purple-600 to-purple-700",
        "hover": "hover:bg-purple-700",
    },
    "cache": {
        "primary": "pink",
        "bg": "bg-pink-600",
        "text": "text-pink-400",
        "border": "border-pink-500",
        "gradient": "from-pink-600 to-pink-700",
        "hover": "hover:bg-pink-700",
    },
    "cost": {
        "primary": "orange",
        "bg": "bg-orange-600",
        "text": "text-orange-400",
        "border": "border-orange-500",
        "gradient": "from-orange-600 to-orange-700",
        "hover": "hover:bg-orange-700",
    },
    "system_prompt": {
        "primary": "yellow",
        "bg": "bg-yellow-600",
        "text": "text-yellow-400",
        "border": "border-yellow-500",
        "gradient": "from-yellow-600 to-yellow-700",
        "hover": "hover:bg-yellow-700",
    },
    "token_imbalance": {
        "primary": "green",
        "bg": "bg-green-600",
        "text": "text-green-400",
        "border": "border-green-500",
        "gradient": "from-green-600 to-green-700",
        "hover": "hover:bg-green-700",
    },
    "routing": {
        "primary": "blue",
        "bg": "bg-blue-600",
        "text": "text-blue-400",
        "border": "border-blue-500",
        "gradient": "from-blue-600 to-blue-700",
        "hover": "hover:bg-blue-700",
    },
    "quality": {
        "primary": "red",
        "bg": "bg-red-600",
        "text": "text-red-400",
        "border": "border-red-500",
        "gradient": "from-red-600 to-red-700",
        "hover": "hover:bg-red-700",
    },
}


# =============================================================================
# STORY METADATA (Priority, Difficulty, Expected Impact)
# =============================================================================

STORY_METADATA: Dict[str, Dict[str, Any]] = {
    "latency": {
        "priority": "high",
        "difficulty": "medium",
        "avg_time_to_fix": "2-4 hours",
        "expected_improvement": "50-80% latency reduction",
        "requires_code_change": True,
        "automation_potential": "low",
        "related_stories": ["token_imbalance", "cost"],
    },
    "cache": {
        "priority": "high",
        "difficulty": "easy",
        "avg_time_to_fix": "1-2 hours",
        "expected_improvement": "90% cost reduction on duplicates",
        "requires_code_change": True,
        "automation_potential": "high",
        "related_stories": ["cost", "system_prompt"],
    },
    "cost": {
        "priority": "high",
        "difficulty": "medium",
        "avg_time_to_fix": "varies",
        "expected_improvement": "20-40% cost reduction",
        "requires_code_change": True,
        "automation_potential": "medium",
        "related_stories": ["cache", "routing", "system_prompt"],
    },
    "system_prompt": {
        "priority": "medium",
        "difficulty": "easy",
        "avg_time_to_fix": "30 min - 1 hour",
        "expected_improvement": "30-60% token reduction",
        "requires_code_change": True,
        "automation_potential": "low",
        "related_stories": ["cache", "cost", "token_imbalance"],
    },
    "token_imbalance": {
        "priority": "medium",
        "difficulty": "medium",
        "avg_time_to_fix": "1-3 hours",
        "expected_improvement": "40-70% token reduction",
        "requires_code_change": True,
        "automation_potential": "medium",
        "related_stories": ["latency", "cost"],
    },
    "routing": {
        "priority": "medium",
        "difficulty": "hard",
        "avg_time_to_fix": "4-8 hours",
        "expected_improvement": "30-50% cost, better quality",
        "requires_code_change": True,
        "automation_potential": "high",
        "related_stories": ["cost", "quality"],
    },
    "quality": {
        "priority": "high",
        "difficulty": "hard",
        "avg_time_to_fix": "varies",
        "expected_improvement": "2-5 point quality increase",
        "requires_code_change": True,
        "automation_potential": "low",
        "related_stories": ["routing"],
    },
}


# =============================================================================
# SUCCESS CRITERIA (How to measure if fix worked)
# =============================================================================

SUCCESS_CRITERIA: Dict[str, Dict[str, Any]] = {
    "latency": {
        "metric": "avg_latency_ms",
        "before_threshold": 5000,
        "after_target": 2000,
        "improvement_pct": 60,
        "measurement_period": "7 days",
    },
    "cache": {
        "metric": "cache_hit_rate",
        "before_threshold": 0.0,
        "after_target": 0.50,
        "improvement_pct": None,  # Absolute target
        "measurement_period": "7 days",
    },
    "cost": {
        "metric": "total_cost",
        "before_threshold": None,
        "after_target": None,
        "improvement_pct": 20,  # 20% reduction
        "measurement_period": "7 days",
    },
    "system_prompt": {
        "metric": "avg_system_tokens",
        "before_threshold": 1000,
        "after_target": 400,
        "improvement_pct": 60,
        "measurement_period": "7 days",
    },
    "token_imbalance": {
        "metric": "prompt_completion_ratio",
        "before_threshold": 10,
        "after_target": 5,
        "improvement_pct": 50,
        "measurement_period": "7 days",
    },
    "routing": {
        "metric": "quality_score",
        "before_threshold": 7.0,
        "after_target": 8.5,
        "improvement_pct": None,
        "measurement_period": "7 days",
    },
    "quality": {
        "metric": "error_rate",
        "before_threshold": 0.05,
        "after_target": 0.01,
        "improvement_pct": 80,
        "measurement_period": "7 days",
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


def get_story_colors(story_id: str) -> Optional[Dict[str, str]]:
    """Get color scheme for a specific story."""
    return STORY_COLORS.get(story_id)


def get_story_metadata(story_id: str) -> Optional[Dict[str, Any]]:
    """Get metadata (priority, difficulty, etc.) for a specific story."""
    return STORY_METADATA.get(story_id)


def get_success_criteria(story_id: str) -> Optional[Dict[str, Any]]:
    """Get success criteria for measuring improvement."""
    return SUCCESS_CRITERIA.get(story_id)


def get_all_story_ids() -> List[str]:
    """Get list of all story IDs."""
    return list(STORY_DEFINITIONS.keys())


def get_story_threshold(story_id: str, threshold_name: str) -> Optional[Any]:
    """Get a specific threshold value for a story."""
    definition = STORY_DEFINITIONS.get(story_id, {})
    thresholds = definition.get("thresholds", {})
    return thresholds.get(threshold_name)


def get_stories_by_priority(priority: str = "high") -> List[str]:
    """Get list of story IDs filtered by priority."""
    return [
        story_id
        for story_id, metadata in STORY_METADATA.items()
        if metadata.get("priority") == priority
    ]


def get_stories_by_difficulty(difficulty: str = "easy") -> List[str]:
    """Get list of story IDs filtered by difficulty."""
    return [
        story_id
        for story_id, metadata in STORY_METADATA.items()
        if metadata.get("difficulty") == difficulty
    ]