"""
Analysis prompts for MCP.

These prompts help users run common analysis workflows.
"""

from observatory.mcp.types import PromptDefinition


ANALYSIS_PROMPTS = [
    PromptDefinition(
        name="cost_analysis",
        description="Analyze LLM costs and identify spending patterns",
        template="""Analyze my LLM costs and provide insights:

1. Get the cost summary for the specified time range
2. Identify the top spending areas (by model, agent, operation)
3. Check the cost trend (increasing/decreasing/stable)
4. Highlight any unusually expensive calls

Provide actionable recommendations to reduce costs.""",
        arguments=[
            {
                "name": "time_range",
                "description": "Time period to analyze",
                "required": False,
                "default": "7d",
            }
        ],
        category="analysis",
    ),
    PromptDefinition(
        name="optimization_scan",
        description="Scan for all optimization opportunities",
        template="""Run a comprehensive optimization scan:

1. Check for model routing opportunities (expensive models used for simple tasks)
2. Find caching opportunities (duplicate/similar prompts)
3. Identify token efficiency issues (bloated prompts, large system messages)
4. Calculate total potential savings

Prioritize recommendations by potential impact.""",
        arguments=[
            {
                "name": "min_savings",
                "description": "Minimum monthly savings to report",
                "required": False,
                "default": "0.01",
            }
        ],
        category="analysis",
    ),
    PromptDefinition(
        name="cache_audit",
        description="Audit cache effectiveness and find improvement opportunities",
        template="""Audit the caching system:

1. Check current cache hit rates (exact, semantic, prefix)
2. Identify cacheable patterns that aren't being cached
3. Find the highest-value caching opportunities
4. Provide specific recommendations to improve hit rates

Include potential savings estimates.""",
        category="analysis",
    ),
    PromptDefinition(
        name="routing_audit",
        description="Audit model routing effectiveness",
        template="""Audit the model routing system:

1. Analyze routing decisions made in the specified period
2. Calculate total savings from routing
3. Identify which operations benefit most from routing
4. Check if any operations should have different routing rules

Provide recommendations for routing rule improvements.""",
        arguments=[
            {
                "name": "time_range",
                "description": "Time period to analyze",
                "required": False,
                "default": "7d",
            }
        ],
        category="analysis",
    ),
]
