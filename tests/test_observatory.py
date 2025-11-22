import pytest
from datetime import datetime

from observatory import Observatory, ModelProvider, AgentRole
from observatory.models import Session, LLMCall


class TestObservatory:
    def test_observatory_init(self):
        obs = Observatory(project_name="test-project", enabled=True)
        assert obs.collector.project_name == "test-project"
        assert obs.collector.enabled is True

    def test_start_end_session(self):
        obs = Observatory(project_name="test-project", enabled=True)
        
        session = obs.start_session(operation_type="test_op")
        assert session.id is not None
        assert session.project_name == "test-project"
        assert session.operation_type == "test_op"
        assert session.end_time is None
        
        ended_session = obs.end_session(session)
        assert ended_session.end_time is not None

    def test_record_llm_call(self):
        obs = Observatory(project_name="test-project", enabled=True)
        session = obs.start_session()
        
        call = obs.record_call(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=1000,
            agent_name="TestAgent",
            agent_role=AgentRole.ANALYST,
            session=session,
        )
        
        assert call.id is not None
        assert call.provider == ModelProvider.OPENAI
        assert call.model_name == "gpt-4"
        assert call.total_tokens == 150
        assert call.total_cost > 0

    def test_context_manager(self):
        obs = Observatory(project_name="test-project", enabled=True)
        
        with obs.track("test_operation") as session:
            assert session.id is not None
            obs.record_call(
                provider=ModelProvider.OPENAI,
                model_name="gpt-3.5-turbo",
                prompt_tokens=50,
                completion_tokens=25,
                latency_ms=500,
                session=session,
            )
        
        # Session should be ended after context
        assert session.end_time is not None

    def test_disabled_observatory(self):
        obs = Observatory(project_name="test-project", enabled=False)
        
        session = obs.start_session()
        assert session.id == "disabled"
        
        call = obs.record_call(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=1000,
        )
        assert call.id == "disabled"


class TestModels:
    def test_session_creation(self):
        session = Session(
            id="test-123",
            project_name="test-project",
            operation_type="test",
        )
        assert session.id == "test-123"
        assert session.total_cost == 0.0
        assert session.success is True

    def test_llm_call_creation(self):
        call = LLMCall(
            id="call-123",
            session_id="session-123",
            provider=ModelProvider.OPENAI,
            model_name="gpt-4",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            prompt_cost=0.003,
            completion_cost=0.006,
            total_cost=0.009,
            latency_ms=1000,
        )
        assert call.total_tokens == 150
        assert call.total_cost == 0.009


if __name__ == "__main__":
    pytest.main([__file__, "-v"])