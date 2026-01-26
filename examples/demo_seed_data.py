"""
Demo Data Seeder for MCP Server Demo

This script creates realistic sample data for demonstrating
the Observatory MCP server with Claude Desktop.

Run this before your demo:
    python examples/demo_seed_data.py
"""

import random
import uuid
from datetime import datetime, timedelta
from observatory.storage import Storage
from observatory.models import (
    LLMCall, Session, ModelProvider, AgentRole, CallType,
    RoutingDecision, CacheMetadata, QualityEvaluation
)


def create_demo_data(db_url: str = "sqlite:///demo_observatory.db"):
    """Create demo data for MCP server demonstration."""

    storage = Storage(db_url)
    print(f"Creating demo data in: {db_url}")

    # Configuration for realistic data
    models = {
        "expensive": ["gpt-4o", "claude-opus-4", "claude-sonnet-4"],
        "cheap": ["gpt-4o-mini", "claude-haiku"],
    }

    agents = [
        ("ResearchAgent", AgentRole.ANALYST, "research"),
        ("WriterAgent", AgentRole.WRITER, "content_generation"),
        ("ReviewerAgent", AgentRole.REVIEWER, "code_review"),
        ("PlannerAgent", AgentRole.PLANNER, "task_planning"),
        ("FixerAgent", AgentRole.FIXER, "bug_fixing"),
    ]

    operations = [
        "analyze_document",
        "generate_summary",
        "review_code",
        "plan_task",
        "fix_bug",
        "answer_question",
        "extract_data",
        "translate_text",
    ]

    # Create sessions over the last 14 days
    sessions = []
    all_calls = []

    for day_offset in range(14, -1, -1):
        day = datetime.utcnow() - timedelta(days=day_offset)

        # 2-5 sessions per day
        num_sessions = random.randint(2, 5)

        for _ in range(num_sessions):
            session_id = str(uuid.uuid4())
            session_start = day.replace(
                hour=random.randint(8, 18),
                minute=random.randint(0, 59)
            )

            # 5-20 calls per session
            num_calls = random.randint(5, 20)
            session_calls = []
            session_cost = 0.0
            session_tokens = 0
            cache_hits = 0
            routing_savings = 0.0

            agent_name, agent_role, base_operation = random.choice(agents)

            for i in range(num_calls):
                call_time = session_start + timedelta(minutes=i * random.randint(1, 5))

                # 30% chance of using expensive model
                use_expensive = random.random() < 0.3
                model = random.choice(models["expensive"] if use_expensive else models["cheap"])
                provider = ModelProvider.OPENAI if "gpt" in model else ModelProvider.ANTHROPIC

                # Token counts
                prompt_tokens = random.randint(200, 2000)
                completion_tokens = random.randint(50, 500)
                system_tokens = random.randint(100, 800)

                # Cost calculation (rough estimates)
                if use_expensive:
                    prompt_cost = prompt_tokens * 0.00003
                    completion_cost = completion_tokens * 0.00006
                else:
                    prompt_cost = prompt_tokens * 0.000001
                    completion_cost = completion_tokens * 0.000002

                total_cost = prompt_cost + completion_cost

                # Cache simulation (20% hit rate)
                cache_hit = random.random() < 0.2
                cache_savings = total_cost * 0.9 if cache_hit else 0

                # Routing simulation (for expensive models, 50% get routed)
                routing_decision = None
                call_routing_savings = 0.0
                if use_expensive and random.random() < 0.5:
                    cheaper_model = random.choice(models["cheap"])
                    call_routing_savings = total_cost * 0.7
                    routing_decision = RoutingDecision(
                        chosen_model=cheaper_model,
                        alternative_models=[model],
                        reasoning=f"Routed from {model} to {cheaper_model} for cost savings",
                        rule_triggered="cost_optimization",
                        complexity_score=random.uniform(0.2, 0.5),
                        estimated_cost_savings=call_routing_savings,
                    )

                # Quality evaluation (80% of calls get evaluated)
                quality_eval = None
                if random.random() < 0.8:
                    quality_score = random.uniform(3.0, 5.0)
                    hallucination = random.random() < 0.05  # 5% hallucination rate
                    quality_eval = QualityEvaluation(
                        judge_score=quality_score,
                        hallucination_flag=hallucination,
                        confidence_score=random.uniform(0.7, 0.95),
                        judge_model="gpt-4o-mini",
                    )

                operation = random.choice(operations)

                call = LLMCall(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    timestamp=call_time,
                    call_type=CallType.LLM,
                    provider=provider,
                    model_name=model,
                    prompt=f"Sample prompt for {operation}...",
                    response_text=f"Sample response for {operation}...",
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    system_prompt_tokens=system_tokens,
                    prompt_cost=prompt_cost,
                    completion_cost=completion_cost,
                    total_cost=total_cost,
                    latency_ms=random.uniform(500, 3000),
                    agent_name=agent_name,
                    agent_role=agent_role,
                    operation=operation,
                    success=random.random() > 0.02,  # 2% error rate
                    routing_decision=routing_decision,
                    cache_metadata=CacheMetadata(
                        cache_hit=cache_hit,
                        cache_type="exact" if cache_hit else None,
                    ) if cache_hit else None,
                    quality_evaluation=quality_eval,
                    phase="baseline" if day_offset > 7 else "optimized",
                )

                session_calls.append(call)
                session_cost += total_cost
                session_tokens += prompt_tokens + completion_tokens
                if cache_hit:
                    cache_hits += 1
                routing_savings += call_routing_savings

            # Create session
            session = Session(
                id=session_id,
                project_name="demo_project",
                start_time=session_start,
                end_time=session_start + timedelta(minutes=len(session_calls) * 5),
                llm_calls=session_calls,
                total_llm_calls=len(session_calls),
                total_tokens=session_tokens,
                total_cost=session_cost,
                total_cache_hits=cache_hits,
                total_cache_misses=len(session_calls) - cache_hits,
                routing_cost_savings=routing_savings,
                operation_type=base_operation,
            )

            sessions.append(session)
            all_calls.extend(session_calls)

    # Save to storage
    print(f"Saving {len(sessions)} sessions with {len(all_calls)} LLM calls...")

    for session in sessions:
        storage.save_session(session)

    # Print summary
    total_cost = sum(c.total_cost for c in all_calls)
    total_tokens = sum(c.total_tokens for c in all_calls)

    print("\n" + "=" * 60)
    print("DEMO DATA CREATED SUCCESSFULLY")
    print("=" * 60)
    print(f"Sessions:     {len(sessions)}")
    print(f"LLM Calls:    {len(all_calls)}")
    print(f"Total Cost:   ${total_cost:.2f}")
    print(f"Total Tokens: {total_tokens:,}")
    print(f"Date Range:   Last 14 days")
    print(f"Database:     {db_url}")
    print("=" * 60)
    print("\nYou can now start the MCP server with:")
    print(f"  OBSERVATORY_DB_URL={db_url} python -m observatory.mcp.server")
    print("\nOr configure Claude Desktop with this database URL.")

    return storage


if __name__ == "__main__":
    create_demo_data()
