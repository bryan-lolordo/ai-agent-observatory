"""
Complete Evaluation Example
===========================

This example demonstrates the full evaluation workflow:
1. Load a test suite from YAML
2. Define your agent function
3. Run evaluation
4. View reports (Console + Markdown)
5. Compare baseline vs optimized versions

Run this example:
    python examples/complete_evaluation_example.py
"""

import asyncio
from datetime import datetime
from pathlib import Path

# =============================================================================
# IMPORTS
# =============================================================================

from observatory import (
    # Core
    Observatory,
    Storage,
    # Evaluation System
    TestSuiteLoader,
    TestSuiteBuilder,
    EvaluationPipeline,
    TestRunner,
    RunnerConfig,
    EvaluationStore,
    # Reporting
    ConsoleReporter,
    MarkdownReporter,
    ReportBuilder,
)


# =============================================================================
# MOCK AGENT FUNCTION
# =============================================================================
# Replace this with your actual agent implementation

def mock_job_matcher_agent(input_data: dict) -> dict:
    """
    Mock job matcher agent that returns a trace.

    In a real scenario, this would:
    1. Call your LLM with the resume and job description
    2. Return a trace with the response

    The trace format should include:
    - tool_calls: List of function/tool calls made
    - response_text: The LLM's response
    - Any other metadata you want to track
    """
    resume = input_data.get("resume", "")
    job_desc = input_data.get("job_description", "")

    # Simulate scoring logic (replace with real LLM call)
    score = 75  # Default

    # Simple heuristics for demo
    if "senior" in resume.lower() and "senior" in job_desc.lower():
        score = 85
    elif "junior" in resume.lower() and "senior" in job_desc.lower():
        score = 25
    elif not resume.strip() or not job_desc.strip():
        score = 5

    # Return trace format expected by evaluators
    return {
        "id": f"trace_{datetime.utcnow().timestamp()}",
        "tool_calls": [
            {
                "name": "score_job_match",
                "arguments": {
                    "resume": resume[:100] + "..." if len(resume) > 100 else resume,
                    "job_description": job_desc[:100] + "..." if len(job_desc) > 100 else job_desc,
                }
            }
        ],
        "response_text": f"Based on my analysis, the match score is {score}/100. "
                        f"The candidate's skills align {'well' if score > 70 else 'poorly'} "
                        f"with the job requirements.",
        "score": score,
        "total_cost": 0.002,  # Mock cost
        "latency_ms": 500,    # Mock latency
    }


def mock_optimized_agent(input_data: dict) -> dict:
    """
    Mock 'optimized' version of the agent for comparison demo.
    In reality, this might use:
    - A different prompt
    - A different model
    - Caching
    - etc.
    """
    trace = mock_job_matcher_agent(input_data)
    # Simulate optimization: slightly better scores, lower cost
    trace["score"] = min(100, trace["score"] + 5)
    trace["total_cost"] = 0.001  # Cheaper
    trace["latency_ms"] = 300    # Faster
    return trace


# =============================================================================
# EXAMPLE 1: Basic Evaluation
# =============================================================================

async def example_basic_evaluation():
    """Run a basic evaluation from a YAML test suite."""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Basic Evaluation from YAML")
    print("=" * 60 + "\n")

    # Load test suite
    loader = TestSuiteLoader()
    suite_path = Path(__file__).parent / "test_suites" / "job_matcher_tests.yaml"

    if not suite_path.exists():
        print(f"Test suite not found at {suite_path}")
        print("Creating a minimal test suite programmatically instead...")
        suite = create_minimal_suite()
    else:
        suite = loader.load(suite_path)
        print(f"Loaded test suite: {suite.name}")
        print(f"  - {len(suite.test_cases)} test cases")
        print(f"  - Categories: {set(tc.category for tc in suite.test_cases)}")

    # Create pipeline and runner
    pipeline = EvaluationPipeline.create_default()
    runner = TestRunner(
        pipeline=pipeline,
        config=RunnerConfig(
            parallel=True,
            max_concurrent=3,
            verbose=True,
        )
    )

    # Run evaluation
    print("\nRunning evaluation...")
    run = await runner.run_suite(
        suite=suite,
        agent_func=mock_job_matcher_agent,
        experiment_version="v1_baseline",
        phase="baseline",
    )

    # Print results
    print("\n" + "-" * 40)
    reporter = ConsoleReporter(use_colors=True)
    reporter.print_run(run)

    # Quick summary
    print("\nQuick Summary:")
    print(ReportBuilder.quick_summary(run))

    runner.shutdown()
    return run


# =============================================================================
# EXAMPLE 2: Programmatic Test Suite
# =============================================================================

def create_minimal_suite():
    """Create a test suite programmatically."""
    builder = TestSuiteBuilder("job_matcher_minimal")

    suite = (builder
        .set_name("Job Matcher Minimal Tests")
        .set_description("Quick validation tests")
        .configure(
            pass_threshold=70,
            evaluators=["tool_use", "model_judge"],
        )
        .add_test_case(
            id="quick_strong_match",
            category="strong_match",
            description="Senior developer matching senior role",
            input={
                "resume": "Senior Python developer with 8 years experience, Django expert",
                "job_description": "Senior Python Developer needed, 5+ years, Django required"
            },
            expected={
                "tool_called": "score_job_match",
                "required_args": ["resume", "job_description"],
                "evaluation_criteria": "Should score 80+ for strong skill match",
            },
            ground_truth={"ideal_score_range": [80, 95]},
        )
        .add_test_case(
            id="quick_weak_match",
            category="weak_match",
            description="Junior applying for senior role",
            input={
                "resume": "Junior developer, 1 year JavaScript, learning React",
                "job_description": "Senior Full Stack Engineer, 7+ years required"
            },
            expected={
                "tool_called": "score_job_match",
                "required_args": ["resume", "job_description"],
                "evaluation_criteria": "Should score low (20-40) due to experience gap",
            },
            ground_truth={"ideal_score_range": [20, 40]},
        )
        .add_test_case(
            id="quick_edge_case",
            category="edge_case",
            description="Empty job description",
            input={
                "resume": "Software engineer with 5 years Python",
                "job_description": ""
            },
            expected={
                "tool_called": "score_job_match",
                "required_args": ["resume", "job_description"],
                "evaluation_criteria": "Should handle gracefully with low score",
            },
            ground_truth={"ideal_score_range": [0, 20]},
        )
        .build())

    return suite


async def example_programmatic_suite():
    """Build and run a test suite programmatically."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Programmatic Test Suite")
    print("=" * 60 + "\n")

    suite = create_minimal_suite()
    print(f"Created suite: {suite.name}")
    print(f"  - {len(suite.test_cases)} test cases")

    # Run with free evaluator only (no LLM cost)
    pipeline = EvaluationPipeline.create_free_only()  # Only ToolUseEvaluator
    runner = TestRunner(pipeline=pipeline)

    print("\nRunning with FREE evaluator only (no LLM cost)...")
    run = await runner.run_suite(
        suite=suite,
        agent_func=mock_job_matcher_agent,
        experiment_version="v1_free_eval",
    )

    # Console output
    reporter = ConsoleReporter(use_colors=True)
    reporter.print_run(run)

    runner.shutdown()
    return run


# =============================================================================
# EXAMPLE 3: Version Comparison
# =============================================================================

async def example_version_comparison():
    """Compare baseline vs optimized agent versions."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Version Comparison (Baseline vs Optimized)")
    print("=" * 60 + "\n")

    suite = create_minimal_suite()

    pipeline = EvaluationPipeline.create_default()
    runner = TestRunner(pipeline=pipeline)

    print("Running comparison...")
    print("  - Baseline: Original agent")
    print("  - Optimized: Improved agent")

    comparison = await runner.compare_versions(
        suite=suite,
        baseline_func=mock_job_matcher_agent,
        optimized_func=mock_optimized_agent,
        experiment_name="prompt_optimization_v1",
        baseline_version="v1_baseline",
        optimized_version="v2_optimized",
    )

    # Print comparison
    reporter = ConsoleReporter(use_colors=True)
    reporter.print_comparison(comparison)

    # Quick summary
    print("\nComparison Summary:")
    print(ReportBuilder.comparison_summary(comparison))

    runner.shutdown()
    return comparison


# =============================================================================
# EXAMPLE 4: Generate Reports
# =============================================================================

async def example_generate_reports():
    """Generate markdown and JSON reports."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Generate Reports")
    print("=" * 60 + "\n")

    suite = create_minimal_suite()
    pipeline = EvaluationPipeline.create_default()
    runner = TestRunner(pipeline=pipeline)

    run = await runner.run_suite(
        suite=suite,
        agent_func=mock_job_matcher_agent,
        experiment_version="v1_reports_demo",
    )

    # Generate reports
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)

    # Markdown report
    md_reporter = MarkdownReporter()
    md_content = md_reporter.generate_run_report(run)
    md_path = reports_dir / f"eval_report_{run.run_id}.md"
    md_reporter.save(md_path, md_content)
    print(f"Markdown report saved: {md_path}")

    # Show preview
    print("\n--- Markdown Report Preview ---")
    print(md_content[:1000] + "..." if len(md_content) > 1000 else md_content)

    runner.shutdown()
    return run


# =============================================================================
# EXAMPLE 5: With Persistence
# =============================================================================

async def example_with_persistence():
    """Run evaluation with database persistence."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Evaluation with Persistence")
    print("=" * 60 + "\n")

    # Setup storage
    db_path = Path(__file__).parent / "eval_results.db"
    storage = Storage(f"sqlite:///{db_path}")
    eval_store = EvaluationStore(storage)

    suite = create_minimal_suite()
    pipeline = EvaluationPipeline.create_default()
    runner = TestRunner(
        pipeline=pipeline,
        storage=eval_store,  # Enable persistence
    )

    print(f"Database: {db_path}")
    print("Running evaluation with persistence...")

    run = await runner.run_suite(
        suite=suite,
        agent_func=mock_job_matcher_agent,
        experiment_version="v1_persisted",
        save=True,  # Save to database
    )

    # Query historical data
    print("\nQuerying stored runs...")
    stored_runs = eval_store.get_runs(test_suite_id=suite.id, limit=5)
    print(f"Found {len(stored_runs)} stored run(s)")

    for stored_run in stored_runs:
        print(f"  - {stored_run.run_id}: {stored_run.metrics.pass_rate*100:.0f}% pass rate")

    # Get summaries
    summaries = eval_store.get_run_summaries(test_suite_id=suite.id)
    print(f"\nRun summaries: {len(summaries)}")

    runner.shutdown()
    return run


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run all examples."""
    print("=" * 60)
    print("OBSERVATORY V2 EVALUATION SYSTEM - COMPLETE EXAMPLE")
    print("=" * 60)

    # Example 1: Basic evaluation from YAML
    await example_basic_evaluation()

    # Example 2: Programmatic test suite
    await example_programmatic_suite()

    # Example 3: Version comparison
    await example_version_comparison()

    # Example 4: Generate reports
    await example_generate_reports()

    # Example 5: With persistence
    await example_with_persistence()

    print("\n" + "=" * 60)
    print("ALL EXAMPLES COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
