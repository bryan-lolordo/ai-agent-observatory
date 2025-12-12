"""
Plugin Map - Agent/Operation to Code Location Mapping
Location: dashboard/config/plugin_map.py

Maps agent_name and operation to source code locations.
Used by story drill-downs to show developers exactly where to make changes.

Usage:
    from dashboard.config.plugin_map import get_code_location
    
    location = get_code_location("ResumeMatching", "deep_analyze_job")
    # Returns: {
    #     "file_path": "agents/plugins/ResumeMatchingPlugin.py",
    #     "method": "deep_analyze_job",
    #     "line_hint": 85,
    #     "class_name": "ResumeMatchingPlugin"
    # }
"""

from typing import Dict, Any, Optional


# =============================================================================
# PLUGIN MAP CONFIGURATION
# =============================================================================

PLUGIN_MAP: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # ChatAgent
    # -------------------------------------------------------------------------
    "ChatAgent": {
        "file_path": "agents/plugins/ChatPlugin.py",
        "class_name": "ChatPlugin",
        "operations": {
            "streamlit_chat": {
                "method": "streamlit_chat",
                "line_hint": 45,
                "description": "Main chat interface handler",
            },
            "chat": {
                "method": "chat",
                "line_hint": 30,
                "description": "Core chat completion",
            },
        },
    },
    
    # -------------------------------------------------------------------------
    # ResumeMatching
    # -------------------------------------------------------------------------
    "ResumeMatching": {
        "file_path": "agents/plugins/ResumeMatchingPlugin.py",
        "class_name": "ResumeMatchingPlugin",
        "operations": {
            "deep_analyze_job": {
                "method": "deep_analyze_job",
                "line_hint": 85,
                "description": "Deep analysis of job-resume match",
            },
            "quick_score_job": {
                "method": "quick_score_job",
                "line_hint": 120,
                "description": "Quick scoring for job matches",
            },
            "explain_recent_match": {
                "method": "explain_recent_match",
                "line_hint": 150,
                "description": "Generate explanation for match",
            },
        },
    },
    
    # -------------------------------------------------------------------------
    # ResumeTailoring
    # -------------------------------------------------------------------------
    "ResumeTailoring": {
        "file_path": "agents/plugins/ResumeTailoringPlugin.py",
        "class_name": "ResumeTailoringPlugin",
        "operations": {
            "tailor_resume": {
                "method": "tailor_resume",
                "line_hint": 50,
                "description": "Tailor resume to job description",
            },
            "suggest_improvements": {
                "method": "suggest_improvements",
                "line_hint": 100,
                "description": "Suggest resume improvements",
            },
        },
    },
    
    # -------------------------------------------------------------------------
    # DatabaseQuery
    # -------------------------------------------------------------------------
    "DatabaseQuery": {
        "file_path": "agents/plugins/QueryDatabasePlugin.py",
        "class_name": "QueryDatabasePlugin",
        "operations": {
            "get_top_matches": {
                "method": "get_top_matches",
                "line_hint": 40,
                "description": "Query top job matches",
            },
            "search_jobs": {
                "method": "search_jobs",
                "line_hint": 75,
                "description": "Search jobs by criteria",
            },
            "query": {
                "method": "query",
                "line_hint": 30,
                "description": "Generic database query",
            },
        },
    },
    
    # -------------------------------------------------------------------------
    # SelfImprovingMatch
    # -------------------------------------------------------------------------
    "SelfImprovingMatch": {
        "file_path": "agents/plugins/SelfImprovingMatchPlugin.py",
        "class_name": "SelfImprovingMatchPlugin",
        "operations": {
            "refine_analysis": {
                "method": "refine_analysis",
                "line_hint": 60,
                "description": "Self-improving match refinement",
            },
            "evaluate_match": {
                "method": "evaluate_match",
                "line_hint": 90,
                "description": "Evaluate match quality",
            },
        },
    },
    
    # -------------------------------------------------------------------------
    # JobPlugin
    # -------------------------------------------------------------------------
    "JobPlugin": {
        "file_path": "agents/plugins/JobPlugin.py",
        "class_name": "JobPlugin",
        "operations": {
            "search": {
                "method": "search",
                "line_hint": 35,
                "description": "Search for jobs",
            },
            "get_details": {
                "method": "get_details",
                "line_hint": 70,
                "description": "Get job details",
            },
        },
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_code_location(agent_name: str, operation: str) -> Optional[Dict[str, Any]]:
    """
    Get code location for an agent/operation combination.
    
    Args:
        agent_name: Name of the agent (e.g., "ResumeMatching")
        operation: Operation name (e.g., "deep_analyze_job")
    
    Returns:
        Dict with file_path, method, line_hint, class_name, description
        or None if not found
    """
    agent_config = PLUGIN_MAP.get(agent_name)
    if not agent_config:
        return None
    
    op_config = agent_config.get("operations", {}).get(operation)
    if not op_config:
        # Return agent-level info without operation specifics
        return {
            "file_path": agent_config.get("file_path"),
            "class_name": agent_config.get("class_name"),
            "method": operation,
            "line_hint": None,
            "description": None,
        }
    
    return {
        "file_path": agent_config.get("file_path"),
        "class_name": agent_config.get("class_name"),
        "method": op_config.get("method", operation),
        "line_hint": op_config.get("line_hint"),
        "description": op_config.get("description"),
    }


def get_file_path(agent_name: str) -> Optional[str]:
    """
    Get file path for an agent.
    
    Args:
        agent_name: Name of the agent
    
    Returns:
        File path string or None if not found
    """
    agent_config = PLUGIN_MAP.get(agent_name)
    if not agent_config:
        return None
    return agent_config.get("file_path")


def get_method_name(agent_name: str, operation: str) -> Optional[str]:
    """
    Get method name for an agent/operation.
    
    Args:
        agent_name: Name of the agent
        operation: Operation name
    
    Returns:
        Method name string or None if not found
    """
    agent_config = PLUGIN_MAP.get(agent_name)
    if not agent_config:
        return operation
    
    op_config = agent_config.get("operations", {}).get(operation)
    if not op_config:
        return operation
    
    return op_config.get("method", operation)


def get_all_agents() -> list:
    """Get list of all configured agent names."""
    return list(PLUGIN_MAP.keys())


def get_agent_operations(agent_name: str) -> list:
    """Get list of all operations for an agent."""
    agent_config = PLUGIN_MAP.get(agent_name)
    if not agent_config:
        return []
    return list(agent_config.get("operations", {}).keys())