"""
Configuration Package
Location: api/config/__init__.py

Exports all configuration constants and helper functions.
"""

# =============================================================================
# SETTINGS (✅ Fixed to match actual settings.py names)
# =============================================================================

from .settings import (
    # Database
    DATABASE_URL,
    DB_POOL_SIZE,              # ✅ Fixed: was DATABASE_POOL_SIZE
    DB_MAX_OVERFLOW,           # ✅ Fixed: was DATABASE_MAX_OVERFLOW
    DB_POOL_TIMEOUT,           # ✅ Fixed: was DATABASE_POOL_TIMEOUT
    # DATABASE_ECHO,           # ❌ Doesn't exist in settings.py - commented out
    
    # API
    API_HOST,
    API_PORT,
    API_RELOAD,                # ✅ Added: exists in settings.py
    CORS_ORIGINS,
    DEFAULT_QUERY_LIMIT,
    MAX_QUERY_LIMIT,
    DEFAULT_DAYS,              # ✅ Added: exists in settings.py
    
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
    OBSERVATORY_PROJECT_NAME,  # ✅ Fixed: was PROJECT_NAME
    OBSERVATORY_SESSION_TTL,   # ✅ Fixed: was SESSION_TTL
    
    # Helper functions
    get_database_url,
    is_sqlite,
    is_postgres,
    validate_settings,
)


# =============================================================================
# STORY DEFINITIONS (only import what exists)
# =============================================================================

from .story_definitions import (
    # Core definitions (✅ These exist)
    STORY_DEFINITIONS,
    STORY_RECOMMENDATIONS,
    
    # NEW: Enhanced metadata (commented out until implemented)
    # STORY_COLORS,
    # STORY_METADATA,
    # SUCCESS_CRITERIA,
    
    # Helper functions (✅ These exist)
    get_story_definition,
    get_story_recommendations,
    get_all_story_ids,
    get_story_threshold,
    
    # NEW: Enhanced helpers (commented out until implemented)
    # get_story_colors,
    # get_story_metadata,
    # get_success_criteria,
    # get_stories_by_priority,
    # get_stories_by_difficulty,
)


# =============================================================================
# PLUGIN MAP (only import what exists)
# =============================================================================

from .plugin_map import (
    # Core mappings (commented out until confirmed)
    # CODE_LOCATIONS,
    
    # NEW: Enhanced metadata (commented out until implemented)
    # OPERATION_METADATA,
    # OPTIMIZATION_TEMPLATES,
    # CODE_EXAMPLES,
    # OPERATION_GROUPS,
    
    # Helper functions (✅ This exists)
    get_code_location,
    
    # Other helpers (commented out until confirmed)
    # get_all_mapped_operations,
    # get_operations_by_agent,
    # get_operations_by_file,
    # format_location,
    # add_location,
    # get_operation_metadata,
    # get_optimization_templates,
    # get_code_example,
    # get_operations_in_group,
    # is_cacheable,
    # get_recommended_model,
    # get_cache_ttl,
)


# =============================================================================
# CONVENIENCE EXPORTS
# =============================================================================

__all__ = [
    # Settings - Database
    "DATABASE_URL",
    "DB_POOL_SIZE",
    "DB_MAX_OVERFLOW",
    "DB_POOL_TIMEOUT",
    
    # Settings - API
    "API_HOST",
    "API_PORT",
    "API_RELOAD",
    "CORS_ORIGINS",
    "DEFAULT_QUERY_LIMIT",
    "MAX_QUERY_LIMIT",
    "DEFAULT_DAYS",
    
    # Settings - Story
    "MIN_CALLS_FOR_ANALYSIS",
    "MIN_CALLS_FOR_QUALITY",
    "STORY_CACHE_TTL",
    
    # Settings - Logging
    "LOG_LEVEL",
    "LOG_FORMAT",
    
    # Settings - Development
    "DEBUG",
    "ENVIRONMENT",
    "IS_PRODUCTION",
    
    # Settings - Paths
    "PROJECT_ROOT",
    "API_ROOT",
    "DATA_DIR",
    "EXPORTS_DIR",
    
    # Settings - Export
    "MAX_EXPORT_ROWS",
    "ALLOWED_EXPORT_FORMATS",
    
    # Settings - Observatory
    "OBSERVATORY_ENABLED",
    "OBSERVATORY_PROJECT_NAME",
    "OBSERVATORY_SESSION_TTL",
    
    # Settings - Functions
    "get_database_url",
    "is_sqlite",
    "is_postgres",
    "validate_settings",
    
    # Story Definitions (only what exists)
    "STORY_DEFINITIONS",
    "STORY_RECOMMENDATIONS",
    "get_story_definition",
    "get_story_recommendations",
    "get_all_story_ids",
    "get_story_threshold",
    
    # Future story helpers (uncomment when implemented):
    # "STORY_COLORS",
    # "STORY_METADATA",
    # "SUCCESS_CRITERIA",
    # "get_story_colors",
    # "get_story_metadata",
    # "get_success_criteria",
    # "get_stories_by_priority",
    # "get_stories_by_difficulty",
    
    # Plugin Map (only what exists)
    "get_code_location",
    
    # Future plugin helpers (uncomment when implemented):
    # "CODE_LOCATIONS",
    # "OPERATION_METADATA",
    # "OPTIMIZATION_TEMPLATES",
    # "CODE_EXAMPLES",
    # "OPERATION_GROUPS",
    # "get_all_mapped_operations",
    # "get_operations_by_agent",
    # "get_operations_by_file",
    # "format_location",
    # "add_location",
    # "get_operation_metadata",
    # "get_optimization_templates",
    # "get_code_example",
    # "get_operations_in_group",
    # "is_cacheable",
    # "get_recommended_model",
    # "get_cache_ttl",
]