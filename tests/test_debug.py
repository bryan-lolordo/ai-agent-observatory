# test_debug.py
from observatory import Observatory, ModelProvider, AgentRole

print("Testing Observatory...")

obs = Observatory(project_name="Code Review Crew")
print(f"Observatory enabled: {obs.collector.enabled}")
print(f"Project name: {obs.collector.project_name}")

session = obs.start_session("debug_test")
print(f"Session ID: {session.id}")

obs.record_call(
    provider=ModelProvider.OPENAI,
    model_name="gpt-4",
    prompt_tokens=100,
    completion_tokens=50,
    latency_ms=1000,
    agent_name="TestAgent",
    operation="test",
)

obs.end_session(session)
print(f"Session ended: {session.end_time}")

# Check if it saved
from observatory import Storage
storage = Storage()
loaded_session = storage.get_session(session.id)
print(f"Session in DB: {loaded_session is not None}")
if loaded_session:
    print(f"Project in DB: {loaded_session.project_name}")