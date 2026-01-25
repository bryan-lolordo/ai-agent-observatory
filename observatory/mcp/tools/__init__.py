"""
MCP Tools for AI Agent Observatory

Tools are organized by category:
- cost: Cost analysis and breakdown tools
- optimization: Optimization opportunity detection
- routing: Model routing analysis
- cache: Cache effectiveness analysis
- sessions: Session management and queries
- quality: Quality evaluation tools
- comparison: A/B testing and phase comparison
"""

from observatory.mcp.tools.cost import COST_TOOLS
from observatory.mcp.tools.optimization import OPTIMIZATION_TOOLS
from observatory.mcp.tools.routing import ROUTING_TOOLS
from observatory.mcp.tools.cache import CACHE_TOOLS
from observatory.mcp.tools.sessions import SESSION_TOOLS
from observatory.mcp.tools.quality import QUALITY_TOOLS
from observatory.mcp.tools.comparison import COMPARISON_TOOLS

# All tools combined for easy registration
ALL_TOOLS = [
    *COST_TOOLS,
    *OPTIMIZATION_TOOLS,
    *ROUTING_TOOLS,
    *CACHE_TOOLS,
    *SESSION_TOOLS,
    *QUALITY_TOOLS,
    *COMPARISON_TOOLS,
]

# Tool categories for documentation/filtering
TOOL_CATEGORIES = {
    "cost": COST_TOOLS,
    "optimization": OPTIMIZATION_TOOLS,
    "routing": ROUTING_TOOLS,
    "cache": CACHE_TOOLS,
    "sessions": SESSION_TOOLS,
    "quality": QUALITY_TOOLS,
    "comparison": COMPARISON_TOOLS,
}

__all__ = [
    "ALL_TOOLS",
    "TOOL_CATEGORIES",
    "COST_TOOLS",
    "OPTIMIZATION_TOOLS",
    "ROUTING_TOOLS",
    "CACHE_TOOLS",
    "SESSION_TOOLS",
    "QUALITY_TOOLS",
    "COMPARISON_TOOLS",
]
