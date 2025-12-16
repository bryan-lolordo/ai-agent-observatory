"""
Shared Test Fixtures
Location: tests/conftest.py

Provides in-memory SQLite database and sample data fixtures.
"""

import os
import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Set test database BEFORE importing anything that uses storage
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient
from api.main import app
from api.utils.data_fetcher import get_storage, reset_storage
from observatory.models import Session, LLMCall, ModelProvider, AgentRole
from tests.fixtures.sample_calls import (
    make_call,
    make_call_dict,
    make_session,
    make_slow_call,
    make_fast_call,
    make_expensive_call,
    make_low_quality_call,
)


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
def test_db():
    """
    Fresh in-memory database for each test.
    
    Yields:
        Storage instance with empty database
    """
    reset_storage()
    storage = get_storage()
    yield storage
    reset_storage()


@pytest.fixture(scope="function")
def test_client(test_db):
    """
    FastAPI TestClient with fresh database.
    
    Yields:
        TestClient instance
    """
    with TestClient(app) as client:
        yield client


# =============================================================================
# SESSION FIXTURES
# =============================================================================

@pytest.fixture
def sample_session(test_db) -> Session:
    """Create and save a single session."""
    session = make_session()
    test_db.save_session(session)
    return session


@pytest.fixture
def sample_session_with_calls(test_db) -> tuple[Session, List[LLMCall]]:
    """Create session with mixed LLM calls."""
    session = make_session()
    test_db.save_session(session)
    
    calls = [
        make_call(session_id=session.id, operation="fast_op", latency_ms=500),
        make_call(session_id=session.id, operation="fast_op", latency_ms=600),
        make_call(session_id=session.id, operation="slow_op", latency_ms=12000),
        make_call(session_id=session.id, operation="slow_op", latency_ms=15000),
        make_call(session_id=session.id, operation="medium_op", latency_ms=3000),
    ]
    
    for call in calls:
        test_db.save_llm_call(call)
    
    return session, calls


# =============================================================================
# CALL FIXTURES (for unit tests - returns dicts)
# =============================================================================

@pytest.fixture
def empty_calls() -> List[Dict]:
    """Empty call list."""
    return []


@pytest.fixture
def single_call() -> List[Dict]:
    """Single normal call."""
    return [make_call_dict()]


@pytest.fixture
def mixed_latency_calls() -> List[Dict]:
    """Calls with mixed latencies for latency story testing."""
    return [
        make_call_dict(operation="fast_op", agent_name="FastAgent", latency_ms=500),
        make_call_dict(operation="fast_op", agent_name="FastAgent", latency_ms=600),
        make_call_dict(operation="fast_op", agent_name="FastAgent", latency_ms=700),
        make_call_dict(operation="slow_op", agent_name="SlowAgent", latency_ms=12000),
        make_call_dict(operation="slow_op", agent_name="SlowAgent", latency_ms=15000),
        make_call_dict(operation="critical_op", agent_name="CriticalAgent", latency_ms=25000),
        make_call_dict(operation="medium_op", agent_name="MediumAgent", latency_ms=3000),
        make_call_dict(operation="medium_op", agent_name="MediumAgent", latency_ms=4000),
    ]


@pytest.fixture
def duplicate_prompt_calls() -> List[Dict]:
    """Calls with duplicate prompts for cache story testing."""
    return [
        make_call_dict(prompt="Generate SQL for: find jobs in SF", operation="generate_sql"),
        make_call_dict(prompt="Generate SQL for: find jobs in SF", operation="generate_sql"),
        make_call_dict(prompt="Generate SQL for: find jobs in SF", operation="generate_sql"),
        make_call_dict(prompt="Generate SQL for: find jobs in NYC", operation="generate_sql"),
        make_call_dict(prompt="Analyze resume for position", operation="analyze"),
    ]


@pytest.fixture
def quality_issue_calls() -> List[Dict]:
    """Calls with quality issues for quality story testing."""
    return [
        make_call_dict(
            operation="critique_match",
            quality_evaluation={"judge_score": 4.0, "hallucination_flag": True, "reasoning": "Hallucinated skills"},
        ),
        make_call_dict(
            operation="critique_match",
            quality_evaluation={"judge_score": 5.5, "hallucination_flag": False, "reasoning": "Missing details"},
        ),
        make_call_dict(
            operation="analyze_job",
            quality_evaluation={"judge_score": 8.5, "hallucination_flag": False, "reasoning": "Good analysis"},
        ),
        make_call_dict(
            operation="analyze_job",
            success=False,
            error="JSON parse error",
            error_type="ValidationError",
        ),
    ]


@pytest.fixture
def token_imbalance_calls() -> List[Dict]:
    """Calls with token imbalances for token efficiency story testing."""
    return [
        make_call_dict(operation="chat", prompt_tokens=2000, completion_tokens=50),  # 40:1 ratio
        make_call_dict(operation="chat", prompt_tokens=1500, completion_tokens=45),  # 33:1 ratio
        make_call_dict(operation="analyze", prompt_tokens=500, completion_tokens=400),  # 1.25:1 ratio
        make_call_dict(operation="analyze", prompt_tokens=600, completion_tokens=500),  # 1.2:1 ratio
    ]


@pytest.fixture
def cost_concentration_calls() -> List[Dict]:
    """Calls showing cost concentration for cost story testing."""
    return [
        # Expensive operation (3 calls, high cost each)
        make_call_dict(operation="deep_analyze", total_cost=0.15, prompt_tokens=2000, completion_tokens=1500),
        make_call_dict(operation="deep_analyze", total_cost=0.18, prompt_tokens=2200, completion_tokens=1600),
        make_call_dict(operation="deep_analyze", total_cost=0.16, prompt_tokens=2100, completion_tokens=1550),
        # Cheap operation (10 calls, low cost each)
        *[make_call_dict(operation="quick_check", total_cost=0.002) for _ in range(10)],
    ]


@pytest.fixture
def routing_opportunity_calls() -> List[Dict]:
    """Calls with routing opportunities for routing story testing."""
    return [
        # Simple task, high quality - downgrade candidate
        make_call_dict(
            operation="generate_sql",
            routing_decision={"complexity_score": 0.3, "chosen_model": "gpt-4o-mini"},
            quality_evaluation={"judge_score": 9.0},
        ),
        make_call_dict(
            operation="generate_sql",
            routing_decision={"complexity_score": 0.35, "chosen_model": "gpt-4o-mini"},
            quality_evaluation={"judge_score": 8.8},
        ),
        # Complex task, low quality - upgrade candidate
        make_call_dict(
            operation="critique_match",
            routing_decision={"complexity_score": 0.85, "chosen_model": "gpt-4o-mini"},
            quality_evaluation={"judge_score": 5.5},
        ),
        make_call_dict(
            operation="critique_match",
            routing_decision={"complexity_score": 0.80, "chosen_model": "gpt-4o-mini"},
            quality_evaluation={"judge_score": 6.0},
        ),
    ]


# =============================================================================
# INTEGRATION TEST FIXTURES (saves to DB)
# =============================================================================

@pytest.fixture
def db_with_latency_data(test_db) -> tuple:
    """Database populated with latency test data."""
    session = make_session(project_name="test_project")
    test_db.save_session(session)
    
    calls = [
        make_call(session_id=session.id, operation="fast_op", agent_name="FastAgent", latency_ms=500),
        make_call(session_id=session.id, operation="fast_op", agent_name="FastAgent", latency_ms=600),
        make_call(session_id=session.id, operation="slow_op", agent_name="SlowAgent", latency_ms=12000),
        make_call(session_id=session.id, operation="slow_op", agent_name="SlowAgent", latency_ms=15000),
        make_call(session_id=session.id, operation="critical_op", agent_name="CriticalAgent", latency_ms=25000),
    ]
    
    for call in calls:
        test_db.save_llm_call(call)
    
    return test_db, session, calls


@pytest.fixture
def db_with_cache_data(test_db) -> tuple:
    """Database populated with cache test data (duplicate prompts)."""
    session = make_session(project_name="test_project")
    test_db.save_session(session)
    
    # Create calls with duplicate prompts
    calls = [
        make_call(session_id=session.id, prompt="Find software engineer jobs", operation="generate_sql"),
        make_call(session_id=session.id, prompt="Find software engineer jobs", operation="generate_sql"),
        make_call(session_id=session.id, prompt="Find software engineer jobs", operation="generate_sql"),
        make_call(session_id=session.id, prompt="Find data scientist jobs", operation="generate_sql"),
        make_call(session_id=session.id, prompt="Analyze resume", operation="analyze"),
    ]
    
    for call in calls:
        test_db.save_llm_call(call)
    
    return test_db, session, calls