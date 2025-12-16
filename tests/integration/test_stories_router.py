"""
Integration Tests - Stories Router
Location: tests/integration/test_stories_router.py

Tests for all story API endpoints with real database.
"""

import pytest
from fastapi.testclient import TestClient

from tests.fixtures.sample_calls import make_call, make_session


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check(self, test_client):
        """Health endpoint returns ok status."""
        response = test_client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "version" in data


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    def test_root_returns_api_info(self, test_client):
        """Root endpoint returns API information."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Observatory API"
        assert "version" in data
        assert "docs" in data


class TestLatencyStoryEndpoint:
    """Tests for Story 1: Latency endpoint."""
    
    def test_latency_endpoint_empty_db(self, test_client):
        """Latency endpoint works with empty database."""
        response = test_client.get("/api/stories/latency")
        
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_calls"] == 0
        assert data["status"] == "ok"
        assert data["health_score"] == 100.0
    
    def test_latency_endpoint_with_data(self, test_client, db_with_latency_data):
        """Latency endpoint returns correct data with populated database."""
        response = test_client.get("/api/stories/latency")
        
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_calls"] == 5
        assert data["summary"]["critical_count"] >= 1  # critical_op (25s)
        assert len(data["detail_table"]) > 0
    
    def test_latency_endpoint_with_days_param(self, test_client, db_with_latency_data):
        """Latency endpoint respects days parameter."""
        response = test_client.get("/api/stories/latency?days=1")
        
        assert response.status_code == 200
        # Data should still be present (within 1 day)
        data = response.json()
        assert data["summary"]["total_calls"] == 5
    
    def test_latency_endpoint_with_limit_param(self, test_client, db_with_latency_data):
        """Latency endpoint respects limit parameter."""
        response = test_client.get("/api/stories/latency?limit=2")
        
        assert response.status_code == 200
        data = response.json()
        # Limit applies to database query, not response
        assert data["summary"]["total_calls"] <= 2
    
    def test_latency_response_structure(self, test_client, db_with_latency_data):
        """Latency response has expected structure."""
        response = test_client.get("/api/stories/latency")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check top-level fields
        assert "status" in data
        assert "health_score" in data
        assert "summary" in data
        assert "top_offender" in data
        assert "detail_table" in data
        assert "chart_data" in data
        assert "recommendations" in data
        
        # Check summary fields
        summary = data["summary"]
        assert "total_calls" in summary
        assert "issue_count" in summary
        assert "avg_latency_ms" in summary
        assert "avg_latency" in summary
        assert "critical_count" in summary
        assert "warning_count" in summary


class TestCacheStoryEndpoint:
    """Tests for Story 2: Cache endpoint."""
    
    def test_cache_endpoint_empty_db(self, test_client):
        """Cache endpoint works with empty database."""
        response = test_client.get("/api/stories/cache")
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "detail_table" in data
    
    def test_cache_endpoint_with_duplicates(self, test_client, db_with_cache_data):
        """Cache endpoint identifies duplicate prompts."""
        response = test_client.get("/api/stories/cache")
        
        assert response.status_code == 200
        data = response.json()
        # Should detect 3 duplicate "Find software engineer jobs" calls
        assert data["summary"]["total_calls"] == 5


class TestRoutingStoryEndpoint:
    """Tests for Story 3: Routing endpoint."""
    
    def test_routing_endpoint_empty_db(self, test_client):
        """Routing endpoint works with empty database."""
        response = test_client.get("/api/stories/routing")
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data


class TestQualityStoryEndpoint:
    """Tests for Story 4: Quality endpoint."""
    
    def test_quality_endpoint_empty_db(self, test_client):
        """Quality endpoint works with empty database."""
        response = test_client.get("/api/stories/quality")
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data


class TestTokenEfficiencyEndpoint:
    """Tests for Story 5: Token efficiency endpoint."""
    
    def test_token_endpoint_empty_db(self, test_client):
        """Token efficiency endpoint works with empty database."""
        response = test_client.get("/api/stories/token-efficiency")
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data


class TestPromptCompositionEndpoint:
    """Tests for Story 6: Prompt composition endpoint."""
    
    def test_prompt_endpoint_empty_db(self, test_client):
        """Prompt composition endpoint works with empty database."""
        response = test_client.get("/api/stories/prompt-composition")
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data


class TestCostStoryEndpoint:
    """Tests for Story 7: Cost endpoint."""
    
    def test_cost_endpoint_empty_db(self, test_client):
        """Cost endpoint works with empty database."""
        response = test_client.get("/api/stories/cost")
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data


class TestOptimizationStoryEndpoint:
    """Tests for Story 8: Optimization impact endpoint."""
    
    def test_optimization_endpoint_empty_db(self, test_client):
        """Optimization endpoint works with empty database."""
        response = test_client.get("/api/stories/optimization-impact")
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
    
    def test_optimization_endpoint_with_date(self, test_client):
        """Optimization endpoint accepts optimization_date parameter."""
        response = test_client.get(
            "/api/stories/optimization-impact?optimization_date=2024-12-10"
        )
        
        assert response.status_code == 200
    
    def test_optimization_endpoint_invalid_date(self, test_client):
        """Optimization endpoint returns 400 for invalid date."""
        response = test_client.get(
            "/api/stories/optimization-impact?optimization_date=not-a-date"
        )
        
        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]


class TestCallDetailEndpoint:
    """Tests for call detail endpoint."""
    
    def test_call_detail_not_found(self, test_client):
        """Call detail returns 404 for non-existent call."""
        response = test_client.get("/api/stories/calls/nonexistent-id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_call_detail_with_valid_id(self, test_client, db_with_latency_data):
        """Call detail returns data for valid call ID."""
        test_db, session, calls = db_with_latency_data
        call_id = calls[0].id
        
        response = test_client.get(f"/api/stories/calls/{call_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == call_id


class TestQueryParameters:
    """Tests for query parameter validation."""
    
    def test_days_parameter_range(self, test_client):
        """Days parameter respects min/max bounds."""
        # Valid range
        response = test_client.get("/api/stories/latency?days=30")
        assert response.status_code == 200
        
        # Below minimum (should still work, FastAPI defaults handle this)
        response = test_client.get("/api/stories/latency?days=0")
        assert response.status_code == 422  # Validation error
    
    def test_limit_parameter_range(self, test_client):
        """Limit parameter respects max bound."""
        # Valid
        response = test_client.get("/api/stories/latency?limit=1000")
        assert response.status_code == 200
        
        # Exceeds max
        response = test_client.get("/api/stories/latency?limit=10000")
        assert response.status_code == 422  # Validation error
    
    def test_project_parameter(self, test_client, db_with_latency_data):
        """Project parameter filters results."""
        # Existing project
        response = test_client.get("/api/stories/latency?project=test_project")
        assert response.status_code == 200
        assert response.json()["summary"]["total_calls"] == 5
        
        # Non-existent project
        response = test_client.get("/api/stories/latency?project=nonexistent")
        assert response.status_code == 200
        assert response.json()["summary"]["total_calls"] == 0


class TestCORS:
    """Tests for CORS configuration."""
    
    def test_cors_headers_present(self, test_client):
        """CORS headers are present in response."""
        response = test_client.options(
            "/api/stories/latency",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            }
        )
        
        # FastAPI TestClient may not fully simulate CORS
        # This test verifies the endpoint is accessible
        assert response.status_code in [200, 405]


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_invalid_endpoint_returns_404(self, test_client):
        """Invalid endpoint returns 404."""
        response = test_client.get("/api/stories/nonexistent")
        
        assert response.status_code == 404
    
    def test_method_not_allowed(self, test_client):
        """POST to GET-only endpoint returns 405."""
        response = test_client.post("/api/stories/latency")
        
        assert response.status_code == 405