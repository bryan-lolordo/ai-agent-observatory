"""
Plugin Map Configuration
Location: api/config/plugin_map.py

Maps agent operations to source code locations and provides optimization metadata.
Used for "where to fix" guidance in Story detail pages.
"""

from typing import Dict, Any, List, Optional


# =============================================================================
# CODE LOCATIONS (File, Class, Method, Line)
# =============================================================================

CODE_LOCATIONS: Dict[str, Dict[str, Any]] = {
    # Example mappings - replace with actual Career Copilot locations
    "DatabaseQuery.generate_sql": {
        "file": "plugins/database_query.py",
        "class": "QueryDatabasePlugin",
        "method": "generate_sql",
        "line": 45,
    },
    "ResumeMatching.quick_score_job": {
        "file": "plugins/resume_matching.py",
        "class": "ResumeMatchingPlugin",
        "method": "quick_score_job",
        "line": 180,
    },
    "ResumeMatching.deep_analyze_job": {
        "file": "plugins/resume_matching.py",
        "class": "ResumeMatchingPlugin",
        "method": "deep_analyze_job",
        "line": 250,
    },
    "ResumeTailoring.improve_bullet": {
        "file": "plugins/resume_tailoring.py",
        "class": "ResumeTailoringPlugin",
        "method": "improve_bullet",
        "line": 92,
    },
}


# =============================================================================
# OPERATION METADATA (Expected Metrics, Cacheability)
# =============================================================================

OPERATION_METADATA: Dict[str, Dict[str, Any]] = {
    "DatabaseQuery.generate_sql": {
        "expected_latency_ms": 800,
        "expected_prompt_tokens": 200,
        "expected_completion_tokens": 50,
        "expected_cost": 0.004,
        "complexity_score": 0.3,
        "can_cache": True,
        "cache_ttl": 3600,  # 1 hour
        "cache_strategy": "semantic",
        "recommended_model": "gpt-4o-mini",
    },
    "ResumeMatching.quick_score_job": {
        "expected_latency_ms": 2000,
        "expected_prompt_tokens": 800,
        "expected_completion_tokens": 200,
        "expected_cost": 0.04,
        "complexity_score": 0.5,
        "can_cache": True,
        "cache_ttl": 1800,  # 30 min
        "cache_strategy": "semantic",
        "recommended_model": "gpt-4o-mini",
    },
    "ResumeMatching.deep_analyze_job": {
        "expected_latency_ms": 5000,
        "expected_prompt_tokens": 1500,
        "expected_completion_tokens": 400,
        "expected_cost": 0.10,
        "complexity_score": 0.7,
        "can_cache": True,
        "cache_ttl": 3600,
        "cache_strategy": "exact",
        "recommended_model": "gpt-4o",
    },
    "ResumeTailoring.improve_bullet": {
        "expected_latency_ms": 3000,
        "expected_prompt_tokens": 400,
        "expected_completion_tokens": 300,
        "expected_cost": 0.02,
        "complexity_score": 0.4,
        "can_cache": False,  # Each bullet is unique
        "cache_ttl": None,
        "cache_strategy": None,
        "recommended_model": "gpt-4o-mini",
    },
}


# =============================================================================
# OPTIMIZATION TEMPLATES (Fix Hints Per Operation)
# =============================================================================

OPTIMIZATION_TEMPLATES: Dict[str, Dict[str, str]] = {
    "DatabaseQuery.generate_sql": {
        "cache": "Add prompt caching for schema (saves 90% on repeated queries)",
        "prompt": "Move database schema to user message instead of system prompt to enable prefix caching",
        "output": "Constrain output to SQL only (no explanation) to reduce tokens by 60%",
        "routing": "This is a simple operation - gpt-4o-mini is appropriate",
    },
    "ResumeMatching.quick_score_job": {
        "cache": "Cache based on job_id + resume_hash for 30 minutes",
        "prompt": "System prompt is good, but consider compressing job description",
        "output": "Use JSON schema to constrain output format (score, top 3 strengths, top 3 gaps)",
        "routing": "Medium complexity - gpt-4o-mini is appropriate",
    },
    "ResumeMatching.deep_analyze_job": {
        "cache": "Cache exact matches for 1 hour",
        "prompt": "Consider two-tier approach: quick score first, deep analysis only if requested",
        "output": "Constrain output with JSON schema (currently generates 2,000+ token essays)",
        "routing": "High complexity - consider upgrading to gpt-4o for better quality",
    },
    "ResumeTailoring.improve_bullet": {
        "cache": "Not recommended - each bullet is unique",
        "prompt": "System prompt is efficient",
        "output": "Already constrained well",
        "routing": "Medium complexity - gpt-4o-mini is appropriate",
    },
}


# =============================================================================
# CODE EXAMPLES (Before/After Snippets)
# =============================================================================

CODE_EXAMPLES: Dict[str, Dict[str, str]] = {
    "DatabaseQuery.generate_sql": {
        "before": '''# ❌ Schema in system prompt blocks caching
messages = [
    {"role": "system", "content": f"""
        Schema: {schema}  # Dynamic content first!
        You are a SQL generator...
    """},
    {"role": "user", "content": user_query}
]''',
        "after": '''# ✅ Static prefix enables caching
messages = [
    {"role": "system", "content": """
        You are a SQL generator...  # Static first!
    """},
    {"role": "user", "content": f"""
        Schema: {schema}  # Dynamic in user message
        Query: {user_query}
    """}
]''',
        "savings": "90% cache hit rate, 66% token reduction",
    },
    "ResumeMatching.deep_analyze_job": {
        "before": '''# ❌ Free-form output (2,000 tokens)
prompt = "Analyze this job match. Provide detailed analysis..."
# Result: Long essay with 8 sections''',
        "after": '''# ✅ Constrained JSON output (200 tokens)
prompt = """
Analyze this job match. Return JSON:
{
    "score": 0-100,
    "strengths": [max 3],
    "gaps": [max 3],
    "recommendation": "string"
}
"""''',
        "savings": "90% token reduction, 85% cost savings",
    },
}


# =============================================================================
# OPERATION GROUPS (For Bulk Fixes)
# =============================================================================

OPERATION_GROUPS: Dict[str, List[str]] = {
    "sql_operations": [
        "DatabaseQuery.generate_sql",
        "DatabaseQuery.validate_sql",
        "DatabaseQuery.optimize_query",
    ],
    "resume_operations": [
        "ResumeMatching.quick_score_job",
        "ResumeMatching.deep_analyze_job",
        "ResumeMatching.critique_match",
    ],
    "tailoring_operations": [
        "ResumeTailoring.improve_bullet",
        "ResumeTailoring.tailor_resume",
    ],
    "judge_operations": [
        "LLMJudge.judge_improve_bullet",
        "LLMJudge.judge_deep_analyze_job",
        "LLMJudge.judge_critique_match",
    ],
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_code_location(agent: str, operation: str) -> Optional[Dict[str, Any]]:
    """
    Get code location for an agent/operation pair.
    
    Args:
        agent: Agent name (e.g., "DatabaseQuery")
        operation: Operation name (e.g., "generate_sql")
    
    Returns:
        Dictionary with file, class, method, line or None
    """
    key = f"{agent}.{operation}"
    return CODE_LOCATIONS.get(key)


def get_operation_metadata(agent: str, operation: str) -> Optional[Dict[str, Any]]:
    """
    Get expected metrics and cacheability for an operation.
    
    Args:
        agent: Agent name
        operation: Operation name
    
    Returns:
        Dictionary with expected metrics or None
    """
    key = f"{agent}.{operation}"
    return OPERATION_METADATA.get(key)


def get_optimization_templates(agent: str, operation: str) -> Optional[Dict[str, str]]:
    """
    Get optimization fix hints for an operation.
    
    Args:
        agent: Agent name
        operation: Operation name
    
    Returns:
        Dictionary with optimization templates or None
    """
    key = f"{agent}.{operation}"
    return OPTIMIZATION_TEMPLATES.get(key)


def get_code_example(agent: str, operation: str) -> Optional[Dict[str, str]]:
    """
    Get before/after code examples for an operation.
    
    Args:
        agent: Agent name
        operation: Operation name
    
    Returns:
        Dictionary with before, after, savings or None
    """
    key = f"{agent}.{operation}"
    return CODE_EXAMPLES.get(key)


def get_all_mapped_operations() -> List[str]:
    """Get list of all operations that have code locations."""
    return list(CODE_LOCATIONS.keys())


def get_operations_by_agent(agent: str) -> List[str]:
    """Get all operations for a specific agent."""
    return [
        op for op in CODE_LOCATIONS.keys()
        if op.startswith(f"{agent}.")
    ]


def get_operations_by_file(file_path: str) -> List[str]:
    """Get all operations defined in a specific file."""
    return [
        op for op, loc in CODE_LOCATIONS.items()
        if loc.get("file") == file_path
    ]


def get_operations_in_group(group_name: str) -> List[str]:
    """Get all operations in a named group."""
    return OPERATION_GROUPS.get(group_name, [])


def format_location(location: Dict[str, Any]) -> str:
    """
    Format a code location as a human-readable string.
    
    Args:
        location: Dictionary from get_code_location()
    
    Returns:
        Formatted string like "resume_matching.py:180 (ResumeMatchingPlugin.quick_score_job)"
    """
    file = location.get("file", "unknown")
    line = location.get("line", "?")
    cls = location.get("class", "")
    method = location.get("method", "")
    
    if cls and method:
        return f"{file}:{line} ({cls}.{method})"
    elif method:
        return f"{file}:{line} ({method})"
    else:
        return f"{file}:{line}"


def add_location(
    agent: str,
    operation: str,
    file: str,
    class_name: Optional[str] = None,
    method: Optional[str] = None,
    line: Optional[int] = None,
):
    """
    Dynamically add a code location (useful for runtime registration).
    
    Args:
        agent: Agent name
        operation: Operation name
        file: Source file path
        class_name: Class name (optional)
        method: Method name (optional)
        line: Line number (optional)
    """
    key = f"{agent}.{operation}"
    CODE_LOCATIONS[key] = {
        "file": file,
        "class": class_name,
        "method": method,
        "line": line,
    }


def is_cacheable(agent: str, operation: str) -> bool:
    """Check if an operation is cacheable."""
    metadata = get_operation_metadata(agent, operation)
    return metadata.get("can_cache", False) if metadata else False


def get_recommended_model(agent: str, operation: str) -> Optional[str]:
    """Get recommended model for an operation."""
    metadata = get_operation_metadata(agent, operation)
    return metadata.get("recommended_model") if metadata else None


def get_cache_ttl(agent: str, operation: str) -> Optional[int]:
    """Get recommended cache TTL for an operation."""
    metadata = get_operation_metadata(agent, operation)
    return metadata.get("cache_ttl") if metadata else None