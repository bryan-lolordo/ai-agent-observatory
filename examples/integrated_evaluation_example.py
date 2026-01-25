"""
Integrated Evaluation Example
=============================

Shows how to use both the existing LLMJudge (production monitoring)
and the new V2 evaluation system (optimization validation) together.

Two Use Cases:
1. Production Monitoring: LLMJudge samples traffic and scores quality
2. Optimization Validation: V2 evaluators validate changes before deployment

Run this example:
    python examples/integrated_evaluation_example.py
"""

import asyncio
from typing import Dict, Any, List

# =============================================================================
# IMPORTS
# =============================================================================

from observatory import (
    # Core
    Observatory,
    # Production monitoring (existing)
    LLMJudge,
    # V2 Evaluation (new)
    ToolUseEvaluator,
    ModelJudgeEvaluator,
    EvaluationPipeline,
    ComparisonService,
)


# =============================================================================
# EXAMPLE TEST CASES
# =============================================================================

TEST_CASES = [
    {
        "id": "test_001",
        "category": "strong_match",
        "description": "Senior engineer matches senior engineering role",
        "input": {
            "resume": "Senior Software Engineer with 5 years Python, ML experience...",
            "job_description": "Looking for Senior Python Developer with ML background...",
        },
        "expected": {
            "tool_called": "score_job_match",
            "required_args": ["resume", "job_description"],
            "evaluation_criteria": "Score should be 75-95 for strong match",
            "ground_truth": {
                "ideal_score_range": [75, 95],
                "key_matches": ["Python", "ML", "Senior level"],
            },
        },
    },
    {
        "id": "test_002",
        "category": "weak_match",
        "description": "Software engineer vs marketing role",
        "input": {
            "resume": "Senior Software Engineer with 5 years Python...",
            "job_description": "Junior Marketing Coordinator for social media...",
        },
        "expected": {
            "tool_called": "score_job_match",
            "required_args": ["resume", "job_description"],
            "evaluation_criteria": "Score should be 0-25 for weak match",
            "ground_truth": {
                "ideal_score_range": [0, 25],
                "key_mismatches": ["Different field", "Different seniority"],
            },
        },
    },
]


# =============================================================================
# SIMULATED AGENT TRACES
# =============================================================================

def simulate_baseline_trace(test_case: Dict) -> Dict[str, Any]:
    """Simulate a trace from baseline agent (no batching)"""
    return {
        "id": f"trace_baseline_{test_case['id']}",
        "operation": "score_job_match",
        "request": test_case["input"],
        "response": {"score": 82},
        "response_text": "Score: 82",
        "metadata": {
            "function_calls": [
                {
                    "name": "score_job_match",
                    "arguments": test_case["input"],
                }
            ],
            "phase": "baseline",
        },
        "latency_ms": 2341,
        "cost": 0.0623,
        "tokens": 1500,
    }


def simulate_optimized_trace(test_case: Dict) -> Dict[str, Any]:
    """Simulate a trace from optimized agent (with batching)"""
    return {
        "id": f"trace_optimized_{test_case['id']}",
        "operation": "score_job_match",
        "request": test_case["input"],
        "response": {"score": 81},  # Slightly different due to batching
        "response_text": "Score: 81",
        "metadata": {
            "function_calls": [
                {
                    "name": "score_job_match",
                    "arguments": test_case["input"],
                }
            ],
            "phase": "optimized",
            "optimization": "batching",
        },
        "latency_ms": 246,  # Much faster
        "cost": 0.0284,     # Much cheaper
        "tokens": 1450,
    }


# =============================================================================
# USE CASE 1: PRODUCTION MONITORING (LLMJudge)
# =============================================================================

async def demo_production_monitoring():
    """
    Use Case 1: Production Quality Monitoring

    LLMJudge samples production traffic and evaluates quality.
    Good for: Ongoing quality assurance, drift detection.
    """
    print("\n" + "="*60)
    print("USE CASE 1: PRODUCTION MONITORING (LLMJudge)")
    print("="*60)

    # Initialize Observatory and Judge
    obs = Observatory(project_name="CareerCopilot")

    judge = LLMJudge(
        observatory=obs,
        operations={"score_job_match", "deep_analyze"},
        sample_rate=0.5,  # Evaluate 50% of calls
        criteria={
            "relevance": 0.30,
            "accuracy": 0.30,
            "helpfulness": 0.25,
            "clarity": 0.15,
        },
        domain_context="career advice and job-resume matching",
        judge_model="gpt-4o",  # Uses expensive model for high quality
    )

    print(f"\nLLMJudge Configuration:")
    print(f"  - Operations: {judge.operations}")
    print(f"  - Sample Rate: {judge.sample_rate}")
    print(f"  - Judge Model: {judge.judge_model}")
    print(f"  - Cost per eval: ~$0.002")

    # Simulate production traffic
    print("\n[Simulating production traffic...]")

    for test_case in TEST_CASES:
        trace = simulate_optimized_trace(test_case)

        # LLMJudge evaluates based on sampling
        # Note: This would call OpenAI in real usage
        should_eval = judge.should_evaluate(trace["operation"])
        print(f"  - {test_case['id']}: {'Evaluating' if should_eval else 'Skipped (sampling)'}")

    print("\nProduction monitoring provides:")
    print("  ✓ Ongoing quality scores")
    print("  ✓ Hallucination detection")
    print("  ✓ Trends over time")
    print("  ✗ NOT suitable for validation (too expensive, no ground truth)")


# =============================================================================
# USE CASE 2: OPTIMIZATION VALIDATION (V2 Evaluators)
# =============================================================================

async def demo_optimization_validation():
    """
    Use Case 2: Optimization Validation

    V2 evaluators validate that code changes don't break quality.
    Good for: Pre-deployment validation, A/B testing.
    """
    print("\n" + "="*60)
    print("USE CASE 2: OPTIMIZATION VALIDATION (V2 Evaluators)")
    print("="*60)

    # Create evaluation pipeline with default evaluators
    pipeline = EvaluationPipeline.create_default()

    print(f"\nV2 Pipeline Configuration:")
    print(f"  - ToolUseEvaluator: FREE (AST-based)")
    print(f"  - ModelJudgeEvaluator: ~$0.0003 (Haiku)")
    print(f"  - Total cost per eval: ~$0.0003")

    # Run baseline evaluations
    print("\n[Running BASELINE evaluations...]")
    baseline_results = []

    for test_case in TEST_CASES:
        trace = simulate_baseline_trace(test_case)
        result = await pipeline.evaluate(
            trace=trace,
            expected=test_case["expected"],
            test_case_id=test_case["id"],
            experiment_version="v1_baseline",
        )
        baseline_results.append(result)
        print(f"  - {test_case['id']}: Score={result.overall_score:.1f}, Passed={result.passed}")

    # Run optimized evaluations
    print("\n[Running OPTIMIZED evaluations...]")
    optimized_results = []

    for test_case in TEST_CASES:
        trace = simulate_optimized_trace(test_case)
        result = await pipeline.evaluate(
            trace=trace,
            expected=test_case["expected"],
            test_case_id=test_case["id"],
            experiment_version="v2_batched",
        )
        optimized_results.append(result)
        print(f"  - {test_case['id']}: Score={result.overall_score:.1f}, Passed={result.passed}")

    # Compare versions
    print("\n[Comparing baseline vs optimized...]")

    comparison = ComparisonService()

    # Calculate average performance metrics
    baseline_metrics = {
        "avg_cost": sum(simulate_baseline_trace(tc)["cost"] for tc in TEST_CASES) / len(TEST_CASES),
        "avg_latency_ms": sum(simulate_baseline_trace(tc)["latency_ms"] for tc in TEST_CASES) / len(TEST_CASES),
        "avg_tokens": sum(simulate_baseline_trace(tc)["tokens"] for tc in TEST_CASES) / len(TEST_CASES),
    }

    optimized_metrics = {
        "avg_cost": sum(simulate_optimized_trace(tc)["cost"] for tc in TEST_CASES) / len(TEST_CASES),
        "avg_latency_ms": sum(simulate_optimized_trace(tc)["latency_ms"] for tc in TEST_CASES) / len(TEST_CASES),
        "avg_tokens": sum(simulate_optimized_trace(tc)["tokens"] for tc in TEST_CASES) / len(TEST_CASES),
    }

    report = comparison.compare(
        baseline_results=baseline_results,
        optimized_results=optimized_results,
        baseline_metrics=baseline_metrics,
        optimized_metrics=optimized_metrics,
        experiment_name="career_copilot_batching",
        baseline_version="v1_baseline",
        optimized_version="v2_batched",
    )

    # Print formatted report
    print(comparison.format_report(report))


# =============================================================================
# USE CASE 3: INTEGRATED WORKFLOW
# =============================================================================

async def demo_integrated_workflow():
    """
    Use Case 3: Integrated Workflow

    Shows how to use both systems together:
    1. V2 evaluators for pre-deployment validation
    2. LLMJudge for production monitoring
    """
    print("\n" + "="*60)
    print("USE CASE 3: INTEGRATED WORKFLOW")
    print("="*60)

    print("""
    Development Workflow:

    ┌─────────────────┐
    │  Code Change    │
    │  (Optimization) │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  V2 Evaluators  │  ← Run test suite
    │  (ToolUse +     │    Compare baseline vs optimized
    │   ModelJudge)   │    Get recommendation
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  Deploy?        │  ← DEPLOY / INVESTIGATE / REJECT
    └────────┬────────┘
             │ (if DEPLOY)
             ▼
    ┌─────────────────┐
    │  Production     │  ← LLMJudge monitors quality
    │  (LLMJudge)     │    Samples 20% of traffic
    └─────────────────┘

    Cost Comparison:
    ┌────────────────────┬──────────────┬──────────────┐
    │ System             │ Cost/Eval    │ When Used    │
    ├────────────────────┼──────────────┼──────────────┤
    │ ToolUseEvaluator   │ $0 (FREE)    │ Every test   │
    │ ModelJudgeEvaluator│ ~$0.0003     │ Every test   │
    │ LLMJudge           │ ~$0.002      │ 20% of prod  │
    └────────────────────┴──────────────┴──────────────┘

    This gives you:
    ✓ Cheap validation before deployment (V2)
    ✓ High-quality monitoring in production (LLMJudge)
    ✓ Ground truth comparison (V2 test cases)
    ✓ Deployment recommendations (V2 ComparisonService)
    """)


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run all demos"""
    print("\n" + "="*60)
    print("OBSERVATORY: INTEGRATED EVALUATION SYSTEM")
    print("="*60)

    # Demo 1: Production monitoring
    await demo_production_monitoring()

    # Demo 2: Optimization validation
    await demo_optimization_validation()

    # Demo 3: Integrated workflow
    await demo_integrated_workflow()

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("""
    You now have two complementary evaluation systems:

    1. LLMJudge (existing):
       - Production quality monitoring
       - Samples traffic, scores responses
       - Uses gpt-4o (~$0.002/eval)
       - Good for: Drift detection, ongoing QA

    2. V2 Evaluators (new):
       - Optimization validation
       - Runs test suites, compares versions
       - Uses Haiku + FREE validators (~$0.0003/eval)
       - Good for: Pre-deployment validation, A/B testing

    Use them together for complete coverage!
    """)


if __name__ == "__main__":
    asyncio.run(main())
