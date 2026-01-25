"""
Report generation prompts for MCP.

These prompts help users generate structured reports.
"""

from observatory.mcp.types import PromptDefinition


REPORT_PROMPTS = [
    PromptDefinition(
        name="weekly_report",
        description="Generate a weekly LLM usage and cost report",
        template="""Generate a weekly report covering the last 7 days:

## Executive Summary
- Total LLM calls and cost
- Week-over-week change (if data available)
- Key highlights

## Cost Breakdown
- By model
- By operation
- By agent

## Performance Metrics
- Average latency
- Error rate
- Cache hit rate

## Optimization Status
- Routing savings achieved
- Cache savings achieved
- Pending optimization opportunities

## Recommendations
- Top 3 actionable items for next week

Format as a clean, readable report.""",
        category="reports",
    ),
    PromptDefinition(
        name="daily_summary",
        description="Generate a quick daily summary",
        template="""Generate a brief daily summary:

1. Today's total calls and cost
2. Comparison to yesterday (if available)
3. Any anomalies or issues
4. Top 3 operations by cost

Keep it concise - this is a quick status check.""",
        category="reports",
    ),
    PromptDefinition(
        name="session_report",
        description="Generate a report for a specific session",
        template="""Generate a detailed session report:

1. Session overview (start time, duration, status)
2. Total calls, cost, and tokens used
3. Models used and their distribution
4. Operations performed
5. Any errors or issues
6. Cache and routing effectiveness during session
7. Quality scores (if evaluated)

Provide insights on session efficiency.""",
        arguments=[
            {
                "name": "session_id",
                "description": "The session ID to report on",
                "required": True,
            }
        ],
        category="reports",
    ),
    PromptDefinition(
        name="comparison_report",
        description="Compare two time periods or configurations",
        template="""Generate a comparison report:

Compare the baseline period with the current/optimized period:

1. Cost comparison (total, by model, by operation)
2. Performance comparison (latency, error rate)
3. Efficiency comparison (cache hit rate, routing savings)
4. Quality comparison (if evaluated)

Calculate percentage improvements and highlight wins/regressions.

Provide a clear verdict: Is the new configuration better?""",
        arguments=[
            {
                "name": "baseline_period",
                "description": "The baseline time range (e.g., '7d' or specific dates)",
                "required": False,
                "default": "Previous 7 days",
            },
            {
                "name": "comparison_period",
                "description": "The comparison time range",
                "required": False,
                "default": "Last 7 days",
            }
        ],
        category="reports",
    ),
]
