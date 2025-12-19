"""
Shared Helpers for Story Routers
Location: api/routers/stories/_helpers.py

Common utilities used across all story endpoints.
"""

from datetime import datetime, timedelta
from typing import Optional

from api.utils.data_fetcher import get_llm_calls


def get_filtered_calls(
    project: Optional[str] = None,
    days: int = 7,
    limit: int = 2000,
) -> list:
    """
    Get LLM calls with common filters.
    
    Used by all story endpoints to fetch data with consistent filtering.
    
    Args:
        project: Optional project name filter
        days: Number of days to look back (default 7)
        limit: Maximum number of calls to return (default 2000)
        
    Returns:
        List of LLM call records
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    return get_llm_calls(
        project_name=project,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )