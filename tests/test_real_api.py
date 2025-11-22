# test_real_api.py
import os
from dotenv import load_dotenv
from openai import OpenAI
from observatory import Observatory, ModelProvider

load_dotenv()

obs = Observatory(project_name="test-project")
client = OpenAI()

session = obs.start_session("test_chat")

# Make a real API call
response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Say hello!"}]
)

# Record it
obs.record_call(
    provider=ModelProvider.OPENAI,
    model_name="gpt-3.5-turbo",
    prompt_tokens=response.usage.prompt_tokens,
    completion_tokens=response.usage.completion_tokens,
    latency_ms=1000,  # You'd measure this in real code
    agent_name="TestBot",
)

obs.end_session(session)
report = obs.get_report(session)

print(f"💰 Real cost: ${report.cost_breakdown.total_cost:.6f}")
print(f"Response: {response.choices[0].message.content}")