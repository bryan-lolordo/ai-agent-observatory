"""
Observatory API - FastAPI Backend
Location: api/main.py

REST API for the React dashboard.
Wraps existing data_fetcher and story_analyzer functions.
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import datetime, timedelta
import sys
import math
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()


def sanitize_for_json(obj):
    """Replace inf/nan with None for JSON serialization."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, float):
        if math.isinf(obj) or math.isnan(obj):
            return None
        return obj
    return obj


# Updated imports - now from api.utils instead of dashboard.utils
from api.utils.data_fetcher import (
    get_llm_calls,
    get_available_projects,
    get_available_models,
    get_available_agents,
    get_available_operations,
)
from api.utils.story_analyzer import (
    get_story_summary,
    analyze_all_stories,
    analyze_latency_story,
    analyze_cache_story,
    analyze_cost_story,
    analyze_system_prompt_story,
    analyze_token_imbalance_story,
    analyze_routing_story,
    analyze_quality_story,
)

# Config imports - these still come from dashboard for now
# TODO: Move these to api/config/ if needed
from api.config.plugin_map import get_code_location
from api.config.story_definitions import (
    get_story_definition,
    get_story_recommendations,
)

app = FastAPI(
    title="Observatory API",
    description="API for AI Agent Observatory Dashboard",
    version="1.0.0",
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# =============================================================================
# FILTERS / METADATA
# =============================================================================

@app.get("/api/projects")
def get_projects():
    """Get available projects."""
    return {"projects": get_available_projects()}


@app.get("/api/models")
def get_models(project: Optional[str] = None):
    """Get available models."""
    return {"models": get_available_models(project_name=project)}


@app.get("/api/agents")
def get_agents(project: Optional[str] = None):
    """Get available agents."""
    return {"agents": get_available_agents(project_name=project)}


@app.get("/api/operations")
def get_operations(project: Optional[str] = None):
    """Get available operations."""
    return {"operations": get_available_operations(project_name=project)}


# =============================================================================
# LLM CALLS
# =============================================================================

@app.get("/api/calls")
def get_calls(
    project: Optional[str] = None,
    agent: Optional[str] = None,
    operation: Optional[str] = None,
    model: Optional[str] = None,
    hours: Optional[int] = None,
    days: Optional[int] = 7,
    limit: int = Query(default=1000, le=5000),
):
    """Get LLM calls with filters."""
    # Calculate time range
    end_time = datetime.utcnow()
    if hours:
        start_time = end_time - timedelta(hours=hours)
    elif days:
        start_time = end_time - timedelta(days=days)
    else:
        start_time = None
    
    calls = get_llm_calls(
        project_name=project,
        agent_name=agent,
        operation=operation,
        model_name=model,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    
    # Convert datetime objects to ISO strings for JSON
    for call in calls:
        if call.get('timestamp'):
            call['timestamp'] = call['timestamp'].isoformat()
    
    return {
        "calls": calls,
        "count": len(calls),
        "filters": {
            "project": project,
            "agent": agent,
            "operation": operation,
            "model": model,
            "days": days,
            "hours": hours,
        }
    }


# =============================================================================
# STORIES
# =============================================================================

@app.get("/api/stories")
def get_stories(
    project: Optional[str] = None,
    days: int = 7,
    limit: int = 2000,
):
    """Get all story summaries."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    calls = get_llm_calls(
        project_name=project,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    
    stories = get_story_summary(calls)
    
    # Add recommendations to each story
    for story in stories:
        story['recommendations'] = get_story_recommendations(story['id'])
        definition = get_story_definition(story['id'])
        if definition:
            story['description'] = definition.get('description', '')
            story['thresholds'] = definition.get('thresholds', {})
    
    # Calculate health metrics
    issues_count = sum(1 for s in stories if s.get('has_issues'))
    total_count = len(stories)
    
    return sanitize_for_json({
        "stories": stories,
        "health": {
            "issues_count": issues_count,
            "passed_count": total_count - issues_count,
            "total_count": total_count,
            "health_score": ((total_count - issues_count) / total_count * 100) if total_count > 0 else 0,
        },
        "meta": {
            "calls_analyzed": len(calls),
            "days": days,
            "project": project,
        }
    })


@app.get("/api/stories/{story_id}")
def get_story_detail(
    story_id: str,
    project: Optional[str] = None,
    days: int = 7,
    limit: int = 2000,
):
    """Get detailed analysis for a specific story."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    calls = get_llm_calls(
        project_name=project,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    
    # Get specific story analysis
    analyzers = {
        "latency": analyze_latency_story,
        "cache": analyze_cache_story,
        "cost": analyze_cost_story,
        "system_prompt": analyze_system_prompt_story,
        "token_imbalance": analyze_token_imbalance_story,
        "routing": analyze_routing_story,
        "quality": analyze_quality_story,
    }
    
    analyzer = analyzers.get(story_id)
    if not analyzer:
        return {"error": f"Unknown story: {story_id}"}
    
    analysis = analyzer(calls)
    
    # Remove call objects from detail_table (too large for JSON)
    if 'detail_table' in analysis:
        for row in analysis['detail_table']:
            if isinstance(row, dict):
                row.pop('calls', None)
                row.pop('duplicate_groups', None)
    
    # Add metadata
    definition = get_story_definition(story_id)
    analysis['recommendations'] = get_story_recommendations(story_id)
    analysis['definition'] = definition
    
    return sanitize_for_json({
        "story_id": story_id,
        "analysis": analysis,
        "meta": {
            "calls_analyzed": len(calls),
            "days": days,
            "project": project,
        }
    })


# =============================================================================
# CODE LOCATION
# =============================================================================

@app.get("/api/code-location")
def get_code_loc(agent: str, operation: str):
    """Get code location for an agent/operation."""
    location = get_code_location(agent, operation)
    return {"location": location}


# =============================================================================
# RUN SERVER
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)