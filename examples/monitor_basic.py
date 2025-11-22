"""
Basic example of using Observatory to monitor an AI application.
"""

import os
import time
from observatory import Observatory, ModelProvider, AgentRole


def simulate_llm_call(duration_ms: float = 1000):
    """Simulate an LLM call with sleep."""
    time.sleep(duration_ms / 1000)


def main():
    # Initialize Observatory
    obs = Observatory(
        project_name="example-project",
        enabled=True,
    )
    
    # Example 1: Manual session tracking
    print("Example 1: Manual Session Tracking")
    session = obs.start_session(operation_type="code_review")
    
    # Simulate some LLM calls
    simulate_llm_call(500)
    obs.record_call(
        provider=ModelProvider.OPENAI,
        model_name="gpt-4",
        prompt_tokens=500,
        completion_tokens=200,
        latency_ms=500,
        agent_name="CodeAnalyzer",
        agent_role=AgentRole.ANALYST,
        operation="analyze_code",
    )
    
    simulate_llm_call(800)
    obs.record_call(
        provider=ModelProvider.OPENAI,
        model_name="gpt-3.5-turbo",
        prompt_tokens=300,
        completion_tokens=150,
        latency_ms=800,
        agent_name="SecurityReviewer",
        agent_role=AgentRole.REVIEWER,
        operation="security_check",
    )
    
    obs.end_session(session)
    
    # Get report
    report = obs.get_report(session)
    print(f"\nSession Report:")
    print(f"  Total Cost: ${report.cost_breakdown.total_cost:.4f}")
    print(f"  Total Latency: {report.latency_breakdown.total_latency_ms:.0f}ms")
    print(f"  Total Tokens: {report.token_breakdown.total_tokens}")
    print(f"  Success Rate: {report.quality_metrics.success_rate:.1%}")
    
    if report.optimization_suggestions:
        print(f"\nOptimization Suggestions:")
        for suggestion in report.optimization_suggestions:
            print(f"  • {suggestion}")
    
    # Example 2: Context manager
    print("\n\nExample 2: Context Manager")
    with obs.track("refactor_code"):
        simulate_llm_call(600)
        obs.record_call(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-5-sonnet",
            prompt_tokens=400,
            completion_tokens=250,
            latency_ms=600,
            agent_name="CodeFixer",
            agent_role=AgentRole.FIXER,
            operation="refactor",
        )
    
    print("✅ Session completed and tracked automatically")


if __name__ == "__main__":
    main()