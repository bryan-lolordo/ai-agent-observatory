"""
MCP Prompts for AI Agent Observatory.

Prompts are pre-defined templates that Claude can offer to users
as quick actions or workflows.

Categories:
- analysis: Cost and usage analysis prompts
- reports: Report generation prompts
"""

from observatory.mcp.prompts.analysis import ANALYSIS_PROMPTS
from observatory.mcp.prompts.reports import REPORT_PROMPTS

# All prompts combined for registration
ALL_PROMPTS = [
    *ANALYSIS_PROMPTS,
    *REPORT_PROMPTS,
]

PROMPT_CATEGORIES = {
    "analysis": ANALYSIS_PROMPTS,
    "reports": REPORT_PROMPTS,
}

__all__ = [
    "ALL_PROMPTS",
    "PROMPT_CATEGORIES",
    "ANALYSIS_PROMPTS",
    "REPORT_PROMPTS",
]
