"""
Evaluation Runner Template
==========================
Location: your-project/evals/run_evals.py

Setup:
    1. Copy this file to your project's evals/ directory
    2. Import your agent function(s)
    3. Update the AGENT_FUNCTIONS mapping
    4. Run: python evals/run_evals.py

Usage:
    # Run all test suites
    python evals/run_evals.py

    # Run specific suite
    python evals/run_evals.py --suite my_agent

    # Compare baseline vs optimized
    python evals/run_evals.py --compare --baseline v1 --optimized v2

    # Generate reports only (no LLM cost)
    python evals/run_evals.py --free-only
"""

import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# =============================================================================
# IMPORTS FROM YOUR PROJECT
# =============================================================================

# Import your observatory config
from observatory_config import (
    EVALUATION_CONFIG,
    create_eval_pipeline,
    create_eval_runner,
    load_test_suite,
    # Evaluation classes
    TestSuiteLoader,
    EvaluationPipeline,
    ConsoleReporter,
    MarkdownReporter,
    ReportBuilder,
)

# ↓↓↓ CUSTOMIZE: Import your agent function(s) ↓↓↓
# from my_app.agents import my_agent_function, my_optimized_agent_function


# =============================================================================
# AGENT FUNCTION MAPPING
# =============================================================================

# ↓↓↓ CUSTOMIZE: Map agent names to their functions ↓↓↓
# The key should match 'agent_name' in your test suite YAML

AGENT_FUNCTIONS = {
    # "my_agent": my_agent_function,
    # "my_agent_optimized": my_optimized_agent_function,
}


# Example agent wrapper for testing (replace with your actual agent)
def example_agent_wrapper(input_data: dict) -> dict:
    """
    Example agent wrapper that returns a trace format.

    Your agent function should accept input_data (dict) and return a trace dict.
    The trace format should include:
    - tool_calls_made: List of tool/function calls made
    - response_text: The agent's response
    - Any other metadata you want to track
    """
    return {
        "id": f"trace_{datetime.utcnow().timestamp()}",
        "tool_calls_made": [
            {
                "name": "your_tool_name",
                "arguments": input_data,
            }
        ],
        "response_text": "Example response",
        "total_cost": 0.001,
        "latency_ms": 100,
    }


# =============================================================================
# EVALUATION COMMANDS
# =============================================================================

async def run_suite(suite_name: str, version: str = "v1", free_only: bool = False):
    """Run a single test suite."""
    print(f"\n{'='*60}")
    print(f"Running: {suite_name}")
    print(f"{'='*60}\n")

    # Load suite
    try:
        suite = load_test_suite(suite_name)
    except FileNotFoundError:
        # List available suites
        suites_dir = Path(EVALUATION_CONFIG.get("test_suites_dir", "evals/test_suites"))
        available = list(suites_dir.glob("*.yaml"))
        print(f"Test suite not found: {suite_name}")
        print(f"Available suites: {[s.stem for s in available]}")
        return None

    # Get agent function
    agent_func = AGENT_FUNCTIONS.get(suite.agent_name)
    if agent_func is None:
        print(f"No agent function registered for: {suite.agent_name}")
        print(f"Available agents: {list(AGENT_FUNCTIONS.keys())}")
        print("\nUsing example_agent_wrapper for demonstration...")
        agent_func = example_agent_wrapper

    # Create pipeline
    if free_only:
        pipeline = EvaluationPipeline.create_free_only()
        print("Using FREE evaluator only (no LLM cost)")
    else:
        pipeline = create_eval_pipeline()

    # Create runner
    runner = create_eval_runner(pipeline=pipeline)

    # Run evaluation
    print(f"Running {len(suite.test_cases)} test cases...")
    run = await runner.run_suite(
        suite=suite,
        agent_func=agent_func,
        experiment_version=version,
        phase="evaluation",
        save=True,
    )

    # Print results
    reporter = ConsoleReporter(use_colors=True)
    reporter.print_run(run)

    # Quick summary
    print("\nQuick Summary:")
    print(ReportBuilder.quick_summary(run))

    runner.shutdown()
    return run


async def run_all_suites(version: str = "v1", free_only: bool = False):
    """Run all test suites in the test_suites directory."""
    suites_dir = Path(EVALUATION_CONFIG.get("test_suites_dir", "evals/test_suites"))

    if not suites_dir.exists():
        print(f"Test suites directory not found: {suites_dir}")
        print("Create the directory and add your test suite YAML files.")
        return

    suite_files = list(suites_dir.glob("*.yaml"))
    if not suite_files:
        print(f"No test suites found in: {suites_dir}")
        return

    print(f"Found {len(suite_files)} test suite(s)")
    results = []

    for suite_file in suite_files:
        suite_name = suite_file.stem
        run = await run_suite(suite_name, version=version, free_only=free_only)
        if run:
            results.append((suite_name, run))

    # Summary
    if results:
        print(f"\n{'='*60}")
        print("OVERALL SUMMARY")
        print(f"{'='*60}")
        for name, run in results:
            metrics = run.metrics
            status = "PASS" if metrics.pass_rate >= 0.75 else "FAIL"
            print(f"  {name}: {metrics.pass_rate*100:.0f}% pass rate [{status}]")


async def compare_versions(
    suite_name: str,
    baseline_version: str,
    optimized_version: str,
    baseline_agent: str = None,
    optimized_agent: str = None,
):
    """Compare baseline vs optimized agent versions."""
    print(f"\n{'='*60}")
    print(f"Comparing: {baseline_version} vs {optimized_version}")
    print(f"Suite: {suite_name}")
    print(f"{'='*60}\n")

    # Load suite
    suite = load_test_suite(suite_name)

    # Get agent functions
    baseline_func = AGENT_FUNCTIONS.get(baseline_agent or suite.agent_name)
    optimized_func = AGENT_FUNCTIONS.get(optimized_agent or f"{suite.agent_name}_optimized")

    if baseline_func is None or optimized_func is None:
        print("Agent functions not found. Using example wrappers for demonstration.")
        baseline_func = example_agent_wrapper
        optimized_func = example_agent_wrapper

    # Create runner
    pipeline = create_eval_pipeline()
    runner = create_eval_runner(pipeline=pipeline)

    # Run comparison
    comparison = await runner.compare_versions(
        suite=suite,
        baseline_func=baseline_func,
        optimized_func=optimized_func,
        experiment_name=f"{suite_name}_comparison",
        baseline_version=baseline_version,
        optimized_version=optimized_version,
    )

    # Print comparison
    reporter = ConsoleReporter(use_colors=True)
    reporter.print_comparison(comparison)

    # Summary
    print("\nComparison Summary:")
    print(ReportBuilder.comparison_summary(comparison))

    runner.shutdown()
    return comparison


async def generate_report(suite_name: str, version: str = "v1"):
    """Generate markdown report for a test run."""
    run = await run_suite(suite_name, version=version)

    if run is None:
        return

    reports_dir = Path(EVALUATION_CONFIG.get("reports_dir", "evals/reports"))
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Generate markdown report
    md_reporter = MarkdownReporter()
    md_content = md_reporter.generate_run_report(run)
    md_path = reports_dir / f"{suite_name}_{version}_{run.run_id}.md"
    md_reporter.save(md_path, md_content)

    print(f"\nReport saved: {md_path}")
    return md_path


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Run Observatory evaluations")
    parser.add_argument("--suite", "-s", help="Specific test suite to run")
    parser.add_argument("--version", "-v", default="v1", help="Version label")
    parser.add_argument("--compare", "-c", action="store_true", help="Compare two versions")
    parser.add_argument("--baseline", default="v1_baseline", help="Baseline version")
    parser.add_argument("--optimized", default="v2_optimized", help="Optimized version")
    parser.add_argument("--baseline-agent", help="Baseline agent name")
    parser.add_argument("--optimized-agent", help="Optimized agent name")
    parser.add_argument("--report", "-r", action="store_true", help="Generate markdown report")
    parser.add_argument("--free-only", "-f", action="store_true", help="Use free evaluator only")
    parser.add_argument("--list", "-l", action="store_true", help="List available test suites")

    args = parser.parse_args()

    # List suites
    if args.list:
        suites_dir = Path(EVALUATION_CONFIG.get("test_suites_dir", "evals/test_suites"))
        if suites_dir.exists():
            suites = list(suites_dir.glob("*.yaml"))
            print("Available test suites:")
            for s in suites:
                print(f"  - {s.stem}")
        else:
            print(f"Test suites directory not found: {suites_dir}")
        return

    # Compare versions
    if args.compare:
        if not args.suite:
            print("--suite required for comparison")
            return
        asyncio.run(compare_versions(
            suite_name=args.suite,
            baseline_version=args.baseline,
            optimized_version=args.optimized,
            baseline_agent=args.baseline_agent,
            optimized_agent=args.optimized_agent,
        ))
        return

    # Generate report
    if args.report:
        if not args.suite:
            print("--suite required for report generation")
            return
        asyncio.run(generate_report(args.suite, version=args.version))
        return

    # Run specific suite or all suites
    if args.suite:
        asyncio.run(run_suite(args.suite, version=args.version, free_only=args.free_only))
    else:
        asyncio.run(run_all_suites(version=args.version, free_only=args.free_only))


if __name__ == "__main__":
    main()
