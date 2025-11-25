import time
from observatory import Observatory, ModelProvider, AgentRole

# EXPLICITLY ENABLE IT
obs = Observatory(project_name="Code Review Crew", enabled=True) 

# Simulate 5 code reviews
for i in range(5):
    print(f"Review {i+1}/5...")
    
    with obs.track(f"code_review_{i+1}"):
        # Simulate different agents with different costs
        
        # Expensive GPT-4 call
        obs.record_call(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4",
            prompt_tokens=800,
            completion_tokens=400,
            latency_ms=2500,
            agent_name="CodeAnalyzer",
            agent_role=AgentRole.ANALYST,
            operation="deep_analysis",
        )
        
        # Cheaper GPT-3.5 call
        obs.record_call(
            provider=ModelProvider.OPENAI,
            model_name="gpt-3.5-turbo",
            prompt_tokens=400,
            completion_tokens=200,
            latency_ms=1200,
            agent_name="SecurityReviewer",
            agent_role=AgentRole.REVIEWER,
            operation="security_check",
        )
        
        # Another GPT-4 call
        obs.record_call(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4",
            prompt_tokens=600,
            completion_tokens=300,
            latency_ms=2000,
            agent_name="CodeFixer",
            agent_role=AgentRole.FIXER,
            operation="fix_issues",
        )
    
    time.sleep(0.5)

print("✅ Generated 5 review sessions! Refresh dashboard.")