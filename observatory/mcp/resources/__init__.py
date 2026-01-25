"""
MCP Resources for AI Agent Observatory

Resources provide live/subscribed data:
- optimization_stories: Pending optimization opportunities
- active_sessions: Currently running sessions
- system_health: Observatory health status
"""

from observatory.mcp.resources.opportunities import OPPORTUNITY_RESOURCES
from observatory.mcp.resources.monitoring import MONITORING_RESOURCES

# All resources combined for easy registration
ALL_RESOURCES = [
    *OPPORTUNITY_RESOURCES,
    *MONITORING_RESOURCES,
]

# Resource categories for documentation
RESOURCE_CATEGORIES = {
    "opportunities": OPPORTUNITY_RESOURCES,
    "monitoring": MONITORING_RESOURCES,
}

__all__ = [
    "ALL_RESOURCES",
    "RESOURCE_CATEGORIES",
    "OPPORTUNITY_RESOURCES",
    "MONITORING_RESOURCES",
]
