"""
Observatory Evaluation System - V2
==================================

Complete evaluation infrastructure for AI agent testing and optimization.

Components:
    Pipeline:
        - EvaluationPipeline: Orchestrates multiple evaluators
        - AggregatedResult: Combined evaluation results

    Comparison:
        - ComparisonService: Compares baseline vs optimized versions
        - ComparisonResult: Comparison output with recommendation

    Test Suites:
        - TestSuiteLoader: Load suites from YAML/JSON
        - TestSuiteBuilder: Programmatic suite creation
        - TestSuiteValidator: Schema validation
        - TestSuiteWriter: Export suites to files

    Storage:
        - EvaluationStore: Persist and query evaluation data

    Runner:
        - TestRunner: Execute test suites against agents
        - RunnerConfig: Runner configuration
        - TestResult: Individual test result

    Reporting:
        - ConsoleReporter: Rich terminal output
        - MarkdownReporter: GitHub-flavored markdown
        - JSONReporter: Structured JSON output
        - ReportBuilder: Convenience utilities

Integration with existing Observatory:
    - Works alongside LLMJudge (production monitoring)
    - Uses same trace format from @observe decorator
    - Stores results compatible with existing models

Usage:
    from observatory.evaluation import (
        # Pipeline
        EvaluationPipeline,
        # Test suites
        TestSuiteLoader,
        TestSuiteBuilder,
        # Runner
        TestRunner,
        # Storage
        EvaluationStore,
        # Reporting
        ConsoleReporter,
        MarkdownReporter,
    )

    # Load test suite
    loader = TestSuiteLoader()
    suite = loader.load("tests/my_agent_tests.yaml")

    # Run tests
    runner = TestRunner(pipeline=EvaluationPipeline.create_default())
    run = await runner.run_suite(suite, my_agent_func)

    # Report results
    reporter = ConsoleReporter()
    reporter.print_run(run)
"""

# =============================================================================
# PIPELINE
# =============================================================================

from observatory.evaluation.pipeline import (
    EvaluationPipeline,
    AggregatedResult,
)

# =============================================================================
# COMPARISON
# =============================================================================

from observatory.evaluation.comparison import (
    ComparisonService,
    ComparisonResult,
)

# =============================================================================
# TEST SUITES
# =============================================================================

from observatory.evaluation.test_suite import (
    # Loader
    TestSuiteLoader,
    # Builder
    TestSuiteBuilder,
    # Validator
    TestSuiteValidator,
    ValidationResult,
    ValidationError,
    # Writer
    TestSuiteWriter,
    # Utilities
    generate_suite_id,
    merge_test_suites,
    filter_test_cases,
    create_subset_suite,
)

# =============================================================================
# STORAGE
# =============================================================================

from observatory.evaluation.eval_storage import (
    EvaluationStore,
    # Query result types
    RunSummary,
    TestCaseHistory,
    ExperimentSummary,
)

# =============================================================================
# RUNNER
# =============================================================================

from observatory.evaluation.runner import (
    TestRunner,
    RunnerConfig,
    TestResult,
)

# =============================================================================
# REPORTING
# =============================================================================

from observatory.evaluation.reporter import (
    # Console
    ConsoleReporter,
    Colors,
    Symbols,
    # Markdown
    MarkdownReporter,
    # JSON
    JSONReporter,
    # Utilities
    ReportBuilder,
)

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Pipeline
    "EvaluationPipeline",
    "AggregatedResult",

    # Comparison
    "ComparisonService",
    "ComparisonResult",

    # Test Suites - Loading
    "TestSuiteLoader",
    "TestSuiteBuilder",
    "TestSuiteValidator",
    "ValidationResult",
    "ValidationError",
    "TestSuiteWriter",

    # Test Suites - Utilities
    "generate_suite_id",
    "merge_test_suites",
    "filter_test_cases",
    "create_subset_suite",

    # Storage
    "EvaluationStore",
    "RunSummary",
    "TestCaseHistory",
    "ExperimentSummary",

    # Runner
    "TestRunner",
    "RunnerConfig",
    "TestResult",

    # Reporting
    "ConsoleReporter",
    "Colors",
    "Symbols",
    "MarkdownReporter",
    "JSONReporter",
    "ReportBuilder",
]
