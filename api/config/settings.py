"""
API Settings
Location: api/config/settings.py

Environment variables and configuration settings.
"""

import os
from typing import Optional
from pathlib import Path


# =============================================================================
# DATABASE SETTINGS
# =============================================================================

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "sqlite:///observatory.db"
)

# Database connection pool settings (for PostgreSQL)
DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))


# =============================================================================
# API SETTINGS
# =============================================================================

# API server
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
API_RELOAD: bool = os.getenv("API_RELOAD", "true").lower() == "true"

# CORS settings
CORS_ORIGINS: list = [
    "http://localhost:3000",  # React dev
    "http://localhost:5173",  # Vite dev
    os.getenv("FRONTEND_URL", ""),
]
CORS_ORIGINS = [origin for origin in CORS_ORIGINS if origin]  # Remove empty strings

# API limits
DEFAULT_QUERY_LIMIT: int = int(os.getenv("DEFAULT_QUERY_LIMIT", "1000"))
MAX_QUERY_LIMIT: int = int(os.getenv("MAX_QUERY_LIMIT", "5000"))
DEFAULT_DAYS: int = int(os.getenv("DEFAULT_DAYS", "7"))


# =============================================================================
# STORY SETTINGS
# =============================================================================

# Minimum data requirements for story analysis
MIN_CALLS_FOR_ANALYSIS: int = int(os.getenv("MIN_CALLS_FOR_ANALYSIS", "10"))
MIN_CALLS_FOR_QUALITY: int = int(os.getenv("MIN_CALLS_FOR_QUALITY", "5"))

# Story refresh interval (minutes)
STORY_CACHE_TTL: int = int(os.getenv("STORY_CACHE_TTL", "5"))


# =============================================================================
# LOGGING SETTINGS
# =============================================================================

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = os.getenv(
    "LOG_FORMAT",
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


# =============================================================================
# DEVELOPMENT SETTINGS
# =============================================================================

DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION: bool = ENVIRONMENT == "production"


# =============================================================================
# FILE PATHS
# =============================================================================

# Project root
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
API_ROOT: Path = PROJECT_ROOT / "api"

# Data directories
DATA_DIR: Path = PROJECT_ROOT / "data"
EXPORTS_DIR: Path = DATA_DIR / "exports"

# Create directories if they don't exist
for directory in [DATA_DIR, EXPORTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


# =============================================================================
# EXPORT SETTINGS
# =============================================================================

# Max rows for Excel export
MAX_EXPORT_ROWS: int = int(os.getenv("MAX_EXPORT_ROWS", "10000"))

# Export formats
ALLOWED_EXPORT_FORMATS: list = ["xlsx", "csv", "json"]


# =============================================================================
# OBSERVATORY SDK SETTINGS (if using observatory package)
# =============================================================================

# These would be used if you're tracking LLM calls
OBSERVATORY_ENABLED: bool = os.getenv("OBSERVATORY_ENABLED", "true").lower() == "true"
OBSERVATORY_PROJECT_NAME: Optional[str] = os.getenv("OBSERVATORY_PROJECT_NAME")
OBSERVATORY_SESSION_TTL: int = int(os.getenv("OBSERVATORY_SESSION_TTL", "3600"))


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_database_url() -> str:
    """Get database URL with validation."""
    url = DATABASE_URL
    if not url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return url


def is_sqlite() -> bool:
    """Check if using SQLite database."""
    return DATABASE_URL.startswith("sqlite")


def is_postgres() -> bool:
    """Check if using PostgreSQL database."""
    return DATABASE_URL.startswith("postgresql")


def validate_settings() -> None:
    """Validate all settings on startup."""
    # Check database URL
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL must be set")
    
    # Check API settings
    if API_PORT < 1 or API_PORT > 65535:
        raise ValueError(f"Invalid API_PORT: {API_PORT}")
    
    # Check limits
    if DEFAULT_QUERY_LIMIT > MAX_QUERY_LIMIT:
        raise ValueError("DEFAULT_QUERY_LIMIT cannot exceed MAX_QUERY_LIMIT")
    
    print(f"✅ Settings validated")
    print(f"   Database: {DATABASE_URL}")
    print(f"   API: {API_HOST}:{API_PORT}")
    print(f"   Environment: {ENVIRONMENT}")