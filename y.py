"""Debug: Find calls with actual prompt content"""

from observatory.storage import ObservatoryStorage, LLMCallDB
from sqlalchemy.orm import Session as DBSession

storage = ObservatoryStorage
db: DBSession = storage.SessionLocal()

# Find calls with substantial prompt content
calls = db.query(LLMCallDB).filter(
    LLMCallDB.prompt_tokens > 100  # Actual LLM calls have more tokens
).limit(5).all()

print(f"Found {len(calls)} calls with >100 prompt tokens\n")

for call in calls:
    print(f"Call: {call.id[:8]}...")
    print(f"  operation: {call.operation}")
    print(f"  agent: {call.agent_name}")
    print(f"  model: {call.model_name}")
    print(f"  tokens: {call.prompt_tokens} in / {call.completion_tokens} out")
    print(f"  system_prompt: {bool(call.system_prompt)} ({len(call.system_prompt or '')} chars)")
    print(f"  user_message: {bool(call.user_message)} ({len(call.user_message or '')} chars)")
    print(f"  prompt: {bool(call.prompt)} ({len(call.prompt or '')} chars)")
    print(f"  response_text: {bool(call.response_text)} ({len(call.response_text or '')} chars)")
    
    # Show first 200 chars of prompt
    if call.prompt:
        print(f"  prompt preview: {call.prompt[:200]}...")
    print()

db.close()