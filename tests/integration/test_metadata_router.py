"""
Integration Tests - Metadata Router
Location: tests/integration/test_metadata_router.py

Tests for metadata API endpoints (projects, models, agents, operations).
"""

import pytest
from fastapi.testclient import TestClient

from tests.fixtures.sample_calls import make_call, make_session


class TestProjectsEndpoint:
    """Tests for /api/projects endpoint."""
    
    def test_projects_empty_db(self, test_client):
        """Projects endpoint works with empty database."""
        response = test_client.get("/api/projects")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_projects_returns_unique(self, test_client, db_with_latency_data):
        """Projects endpoint returns unique project names."""
        response = test_client.get("/api/projects")
        
        assert response.status_code == 200
        data = response.json()
        assert "test_project" in data


class TestModelsEndpoint:
    """Tests for /api/models endpoint."""
    
    def test_models_empty_db(self, test_client):
        """Models endpoint works with empty database."""
        response = test_client.get("/api/models")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_models_returns_unique(self, test_client, db_with_latency_data):
        """Models endpoint returns unique model names."""
        response = test_client.get("/api/models")
        
        assert response.status_code == 200
        data = response.json()
        assert "gpt-4o-mini" in data
    
    def test_models_filter_by_project(self, test_client, db_with_latency_data):
        """Models endpoint filters by project."""
        response = test_client.get("/api/models?project=test_project")
        
        assert response.status_code == 200
        data = response.json()
        assert "gpt-4o-mini" in data
        
        # Non-existent project
        response = test_client.get("/api/models?project=nonexistent")
        assert response.status_code == 200
        assert len(response.json()) == 0


class TestAgentsEndpoint:
    """Tests for /api/agents endpoint."""
    
    def test_agents_empty_db(self, test_client):
        """Agents endpoint works with empty database."""
        response = test_client.get("/api/agents")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_agents_returns_unique(self, test_client, db_with_latency_data):
        """Agents endpoint returns unique agent names."""
        response = test_client.get("/api/agents")
        
        assert response.status_code == 200
        data = response.json()
        # From db_with_latency_data fixture
        assert "FastAgent" in data
        assert "SlowAgent" in data
        assert "CriticalAgent" in data
    
    def test_agents_filter_by_project(self, test_client, db_with_latency_data):
        """Agents endpoint filters by project."""
        response = test_client.get("/api/agents?project=test_project")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0


class TestOperationsEndpoint:
    """Tests for /api/operations endpoint."""
    
    def test_operations_empty_db(self, test_client):
        """Operations endpoint works with empty database."""
        response = test_client.get("/api/operations")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_operations_returns_unique(self, test_client, db_with_latency_data):
        """Operations endpoint returns unique operation names."""
        response = test_client.get("/api/operations")
        
        assert response.status_code == 200
        data = response.json()
        # From db_with_latency_data fixture
        assert "fast_op" in data
        assert "slow_op" in data
        assert "critical_op" in data
    
    def test_operations_filter_by_project(self, test_client, db_with_latency_data):
        """Operations endpoint filters by project."""
        response = test_client.get("/api/operations?project=test_project")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0


class TestMetadataCombined:
    """Tests for combined metadata operations."""
    
    def test_all_metadata_endpoints_work_together(self, test_client, db_with_latency_data):
        """All metadata endpoints return consistent data."""
        projects = test_client.get("/api/projects").json()
        models = test_client.get("/api/models").json()
        agents = test_client.get("/api/agents").json()
        operations = test_client.get("/api/operations").json()
        
        # All should have data
        assert len(projects) > 0
        assert len(models) > 0
        assert len(agents) > 0
        assert len(operations) > 0
        
        # Filter by project should also work
        filtered_models = test_client.get(
            f"/api/models?project={projects[0]}"
        ).json()
        assert len(filtered_models) > 0