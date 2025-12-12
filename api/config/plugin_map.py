"""
Plugin Map Configuration
Location: api/config/plugin_map.py

Maps agent names and operations to source code locations.
This helps users find where to make code changes.

TODO: Replace this placeholder with your actual plugin_map.py from dashboard/config/
"""

from typing import Dict, Any, Optional


# =============================================================================
# PLUGIN MAP - Update with your actual plugin locations
# =============================================================================

PLUGIN_MAP: Dict[str, Dict[str, Any]] = {
    # Example structure:
    # "ChatAgent": {
    #     "file": "agents/plugins/ChatPlugin.py",
    #     "class": "ChatPlugin",
    #     "operations": {
    #         "streamlit_chat": {"method": "streamlit_chat", "line_hint": 45},
    #         "process_message": {"method": "process_message", "line_hint": 120},
    #     }
    # },
    # "ResumeMatching": {
    #     "file": "agents/plugins/ResumeMatchingPlugin.py",
    #     "class": "ResumeMatchingPlugin",
    #     "operations": {
    #         "quick_score_job": {"method": "quick_score_job", "line_hint": 80},
    #         "detailed_match": {"method": "detailed_match", "line_hint": 150},
    #     }
    # },
}


def get_code_location(agent: str, operation: str) -> Dict[str, Any]:
    """
    Get the code location for a given agent and operation.
    
    Args:
        agent: Agent name (e.g., "ChatAgent")
        operation: Operation name (e.g., "streamlit_chat")
    
    Returns:
        Dictionary with file path, method name, and line hint
    """
    agent_config = PLUGIN_MAP.get(agent, {})
    
    if not agent_config:
        return {
            "found": False,
            "agent": agent,
            "operation": operation,
            "message": f"Agent '{agent}' not found in plugin map"
        }
    
    operations = agent_config.get("operations", {})
    op_config = operations.get(operation, {})
    
    if not op_config:
        return {
            "found": False,
            "agent": agent,
            "operation": operation,
            "file": agent_config.get("file"),
            "message": f"Operation '{operation}' not found for agent '{agent}'"
        }
    
    return {
        "found": True,
        "agent": agent,
        "operation": operation,
        "file": agent_config.get("file"),
        "class": agent_config.get("class"),
        "method": op_config.get("method"),
        "line_hint": op_config.get("line_hint"),
    }


def get_all_agents() -> list:
    """Get list of all configured agents."""
    return list(PLUGIN_MAP.keys())


def get_agent_operations(agent: str) -> list:
    """Get list of operations for an agent."""
    agent_config = PLUGIN_MAP.get(agent, {})
    return list(agent_config.get("operations", {}).keys())