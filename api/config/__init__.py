"""
Configuration Package
Location: api/config/__init__.py

Exports all configuration constants and helper functions.
"""

# =============================================================================
# SETTINGS
# =============================================================================

from .settings import (
    # Database
    DATABASE_URL,
    DATABASE_POOL_SIZE,
    DATABASE_MAX_OVERFLOW,
    DATABASE_POOL_TIMEOUT,
    DATABASE_ECHO,
    
    # API
    API_HOST,
    API_PORT,
    CORS_ORIGINS,
    DEFAULT_QUERY_LIMIT,
    MAX_QUERY_LIMIT,
    
    # Story Analysis
    MIN_CALLS_FOR_ANALYSIS,
    MIN_CALLS_FOR_QUALITY,
    STORY_CACHE_TTL,
    
    # Logging
    LOG_LEVEL,
    LOG_FORMAT,
    
    # Development
    DEBUG,
    ENVIRONMENT,
    IS_PRODUCTION,
    
    # Paths
    PROJECT_ROOT,
    API_ROOT,
    DATA_DIR,
    EXPORTS_DIR,
    
    # Export
    MAX_EXPORT_ROWS,
    ALLOWED_EXPORT_FORMATS,
    
    # Observatory SDK
    OBSERVATORY_ENABLED,
    PROJECT_NAME,
    SESSION_TTL,
    
    # Helper functions
    get_database_url,
    is_sqlite,
    is_postgres,
    validate_settings,
)


# =============================================================================
# STORY DEFINITIONS
# =============================================================================

from .story_definitions import (
    # Core definitions
    STORY_DEFINITIONS,
    STORY_RECOMMENDATIONS,
    
    # NEW: Enhanced metadata
    STORY_COLORS,
    STORY_METADATA,
    SUCCESS_CRITERIA,
    
    # Helper functions
    get_story_definition,
    get_story_recommendations,
    get_all_story_ids,
    get_story_threshold,
    
    # NEW: Enhanced helpers
    get_story_colors,
    get_story_metadata,
    get_success_criteria,
    get_stories_by_priority,
    get_stories_by_difficulty,
)


# =============================================================================
# PLUGIN MAP
# =============================================================================

from .plugin_map import (
    # Core mappings
    CODE_LOCATIONS,
    
    # NEW: Enhanced metadata
    OPERATION_METADATA,
    OPTIMIZATION_TEMPLATES,
    CODE_EXAMPLES,
    OPERATION_GROUPS,
    
    # Helper functions
    get_code_location,
    get_all_mapped_operations,
    get_operations_by_agent,
    get_operations_by_file,
    format_location,
    add_location,
    
    # NEW: Enhanced helpers
    get_operation_metadata,
    get_optimization_templates,
    get_code_example,
    get_operations_in_group,
    is_cacheable,
    get_recommended_model,
    get_cache_ttl,
)


# =============================================================================
# CONVENIENCE EXPORTS
# =============================================================================

__all__ = [
    # Settings
    "DATABASE_URL",
    "API_HOST",
    "API_PORT",
    "CORS_ORIGINS",
    "DEFAULT_QUERY_LIMIT",
    "MAX_QUERY_LIMIT",
    "DEBUG",
    "ENVIRONMENT",
    "get_database_url",
    "validate_settings",
    
    # Story Definitions
    "STORY_DEFINITIONS",
    "STORY_RECOMMENDATIONS",
    "STORY_COLORS",
    "STORY_METADATA",
    "SUCCESS_CRITERIA",
    "get_story_definition",
    "get_story_recommendations",
    "get_story_colors",
    "get_story_metadata",
    "get_success_criteria",
    "get_all_story_ids",
    "get_stories_by_priority",
    "get_stories_by_difficulty",
    
    # Plugin Map
    "CODE_LOCATIONS",
    "OPERATION_METADATA",
    "OPTIMIZATION_TEMPLATES",
    "CODE_EXAMPLES",
    "OPERATION_GROUPS",
    "get_code_location",
    "get_operation_metadata",
    "get_optimization_templates",
    "get_code_example",
    "get_operations_in_group",
    "is_cacheable",
    "get_recommended_model",
    "get_cache_ttl",
]