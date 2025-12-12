"""
Dashboard Configuration Package
Location: dashboard/config/__init__.py

Configuration for story-driven optimization dashboard.
"""

from dashboard.config.plugin_map import (
    PLUGIN_MAP,
    get_code_location,
    get_file_path,
    get_method_name,
    get_all_agents,
    get_agent_operations,
)

from dashboard.config.story_definitions import (
    STORY_DEFINITIONS,
    get_story_definition,
    get_target_page,
    get_story_recommendations,
    get_story_thresholds,
    get_all_story_ids,
    get_stories_by_target_page,
)

from dashboard.config.filter_keys import (
    FilterKeys,
    StoryFilterContext,
    set_story_filter,
    get_story_filter,
    clear_story_filter,
    has_active_story_filter,
)

__all__ = [
    # Plugin Map
    'PLUGIN_MAP',
    'get_code_location',
    'get_file_path',
    'get_method_name',
    'get_all_agents',
    'get_agent_operations',
    
    # Story Definitions
    'STORY_DEFINITIONS',
    'get_story_definition',
    'get_target_page',
    'get_story_recommendations',
    'get_story_thresholds',
    'get_all_story_ids',
    'get_stories_by_target_page',
    
    # Filter Keys
    'FilterKeys',
    'StoryFilterContext',
    'set_story_filter',
    'get_story_filter',
    'clear_story_filter',
    'has_active_story_filter',
]