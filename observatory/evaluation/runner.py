"""
Test Runner
============

Orchestrates running test suites against agents and collecting evaluation results.

Architecture:
    ┌─────────────────────────────────────────────────────────────────────┐
    │                          TestRunner                                  │
    │                                                                      │
    │  ┌──────────────┐    ┌──────────────┐    ┌───────────────────────┐ │
    │  │  TestSuite   │───▶│  Run Tests   │───▶│  EvaluationPipeline   │ │
    │  │  (inputs)    │    │  (agent)     │    │  (evaluate traces)    │ │
    │  └──────────────┘    └──────────────┘    └───────────────────────┘ │
    │                             │                        │              │
    │                             ▼                        ▼              │
    │                      ┌────────────┐          ┌─────────────┐       │
    │                      │   Traces   │          │   Results   │       │
    │                      │ (captured) │          │ (scores)    │       │
    │                      └────────────┘          └─────────────┘       │
    │                                                     │              │
    │                                              ┌──────┴──────┐       │
    │                                              │EvaluationRun│       │
    │                                              │ (aggregate) │       │
    │                                              └─────────────┘       │
    └─────────────────────────────────────────────────────────────────────┘

Usage:
    # Basic usage
    runner = TestRunner(pipeline)
    run = await runner.run_suite(suite, agent_func)

    # With storage
    runner = TestRunner(pipeline, storage=eval_store)
    run = await runner.run_suite(suite, agent_func, save=True)

    # Run specific tests
    run = await runner.run_tests(suite, test_ids=["test_1", "test_2"], agent_func=agent)

    # Compare versions
    comparison = await runner.compare_versions(
        suite=suite,
        baseline_func=old_agent,
        optimized_func=new_agent,
    )
"""

import asyncio
import time
import uuid
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union, Awaitable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

from observatory.models import (
    TestCase,
    TestSuite,
    EvaluationRun,
    EvaluationRunMetrics,
    EvaluationResultRecord,
    EvaluationStatus,
    Recommendation,
)
from observatory.evaluation.pipeline import EvaluationPipeline, AggregatedResult
from observatory.evaluation.eval_storage import EvaluationStore
from observatory.evaluation.test_suite import filter_test_cases
from observatory.evaluators.base import EvaluationResult


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

# Agent function type: takes input dict, returns trace dict
AgentFunction = Callable[[Dict[str, Any]], Union[Dict[str, Any], Awaitable[Dict[str, Any]]]]


# =============================================================================
# RUNNER CONFIGURATION
# =============================================================================

@dataclass
class RunnerConfig:
    """Configuration for test runner"""
    # Parallelism
    parallel: bool = True
    max_concurrent: int = 5

    # Timeouts
    test_timeout_seconds: int = 30
    suite_timeout_seconds: int = 600  # 10 minutes

    # Retries
    retry_failed: bool = False
    retry_count: int = 1
    retry_delay_seconds: float = 1.0

    # Behavior
    fail_fast: bool = False                 # Stop on first failure
    continue_on_error: bool = True          # Continue if test errors
    capture_exceptions: bool = True         # Include exception details

    # Filtering
    categories: Optional[List[str]] = None  # Only run these categories
    tags: Optional[List[str]] = None        # Only run tests with these tags
    difficulties: Optional[List[str]] = None

    # Verbosity
    verbose: bool = False
    progress_callback: Optional[Callable[[int, int, str], None]] = None


# =============================================================================
# TEST RESULT
# =============================================================================

@dataclass
class TestResult:
    """Result from running a single test"""
    test_case_id: str
    success: bool                           # Did test run without error?
    passed: bool                            # Did evaluation pass?

    # Trace from agent
    trace: Optional[Dict[str, Any]] = None

    # Evaluation result
    evaluation: Optional[AggregatedResult] = None

    # Timing
    agent_latency_ms: float = 0.0           # Time to run agent
    eval_latency_ms: float = 0.0            # Time to run evaluation
    total_latency_ms: float = 0.0

    # Error info
    error: Optional[str] = None
    error_type: Optional[str] = None

    # Cost tracking
    agent_cost: float = 0.0
    eval_cost: float = 0.0

    # Retry info
    retry_count: int = 0


# =============================================================================
# TEST RUNNER
# =============================================================================

class TestRunner:
    """
    Runs test suites against agent functions and collects evaluation results.

    Supports:
    - Parallel test execution
    - Async and sync agent functions
    - Automatic retry on failure
    - Progress tracking
    - Result persistence
    """

    def __init__(
        self,
        pipeline: Optional[EvaluationPipeline] = None,
        storage: Optional[EvaluationStore] = None,
        config: Optional[RunnerConfig] = None,
    ):
        """
        Initialize test runner.

        Args:
            pipeline: EvaluationPipeline to use (default: create_default())
            storage: EvaluationStore for persistence (optional)
            config: RunnerConfig for behavior settings
        """
        self._pipeline = pipeline or EvaluationPipeline.create_default()
        self._storage = storage
        self._config = config or RunnerConfig()

        # Execution stats
        self._runs_executed = 0
        self._tests_executed = 0
        self._total_cost = 0.0

        # Thread pool for sync functions
        self._executor = ThreadPoolExecutor(max_workers=self._config.max_concurrent)

    # =========================================================================
    # MAIN API
    # =========================================================================

    async def run_suite(
        self,
        suite: TestSuite,
        agent_func: AgentFunction,
        experiment_version: Optional[str] = None,
        phase: str = "baseline",
        save: bool = False,
        run_id: Optional[str] = None,
    ) -> EvaluationRun:
        """
        Run all enabled tests in a suite.

        Args:
            suite: TestSuite to run
            agent_func: Function that takes input and returns trace
            experiment_version: Version identifier (default: suite.id)
            phase: "baseline" or "optimized"
            save: If True and storage is configured, save results
            run_id: Optional specific run ID (generated if not provided)

        Returns:
            EvaluationRun with all results
        """
        # Setup
        run_id = run_id or self._generate_run_id()
        experiment_version = experiment_version or suite.id

        # Create run record
        run = EvaluationRun(
            run_id=run_id,
            test_suite_id=suite.id,
            test_suite_name=suite.name,
            experiment_version=experiment_version,
            phase=phase,
            status=EvaluationStatus.RUNNING.value,
            started_at=datetime.utcnow(),
        )

        # Filter test cases
        test_cases = self._filter_tests(suite)

        if not test_cases:
            run.status = EvaluationStatus.COMPLETED.value
            run.completed_at = datetime.utcnow()
            run.error_message = "No test cases to run after filtering"
            return run

        # Apply suite config to runner config
        effective_config = self._merge_suite_config(suite.config)

        try:
            # Run tests
            if effective_config.parallel:
                results = await self._run_parallel(
                    test_cases=test_cases,
                    agent_func=agent_func,
                    experiment_version=experiment_version,
                    run_id=run_id,
                    config=effective_config,
                )
            else:
                results = await self._run_sequential(
                    test_cases=test_cases,
                    agent_func=agent_func,
                    experiment_version=experiment_version,
                    run_id=run_id,
                    config=effective_config,
                )

            # Convert results to records
            result_records = self._results_to_records(results, run_id)
            run.results = result_records

            # Calculate metrics
            run.metrics = self._calculate_metrics(results)
            run.status = EvaluationStatus.COMPLETED.value

        except Exception as e:
            run.status = EvaluationStatus.FAILED.value
            run.error_message = str(e)
            if self._config.capture_exceptions:
                run.metadata["traceback"] = traceback.format_exc()

        # Finalize
        run.completed_at = datetime.utcnow()
        if run.started_at:
            run.duration_seconds = (run.completed_at - run.started_at).total_seconds()

        # Save if requested
        if save and self._storage:
            self._storage.save_run(run)
            self._storage.save_results(run.results)

        # Update stats
        self._runs_executed += 1
        self._tests_executed += len(test_cases)

        return run

    async def run_tests(
        self,
        suite: TestSuite,
        test_ids: List[str],
        agent_func: AgentFunction,
        experiment_version: Optional[str] = None,
        phase: str = "baseline",
    ) -> EvaluationRun:
        """
        Run specific tests from a suite.

        Args:
            suite: TestSuite containing tests
            test_ids: List of test case IDs to run
            agent_func: Function that takes input and returns trace
            experiment_version: Version identifier
            phase: "baseline" or "optimized"

        Returns:
            EvaluationRun with results for specified tests
        """
        # Filter to specified tests
        test_cases = [tc for tc in suite.test_cases if tc.id in test_ids]

        if not test_cases:
            raise ValueError(f"No test cases found with IDs: {test_ids}")

        # Create temporary subset suite
        subset_suite = TestSuite(
            id=f"{suite.id}__subset",
            name=f"{suite.name} (Subset)",
            version=suite.version,
            config=suite.config,
            test_cases=test_cases,
        )

        return await self.run_suite(
            suite=subset_suite,
            agent_func=agent_func,
            experiment_version=experiment_version,
            phase=phase,
        )

    async def run_single(
        self,
        test_case: TestCase,
        agent_func: AgentFunction,
        experiment_version: str = "single",
    ) -> TestResult:
        """
        Run a single test case.

        Args:
            test_case: TestCase to run
            agent_func: Agent function
            experiment_version: Version identifier

        Returns:
            TestResult for this test
        """
        return await self._run_test(
            test_case=test_case,
            agent_func=agent_func,
            experiment_version=experiment_version,
            config=self._config,
        )

    async def compare_versions(
        self,
        suite: TestSuite,
        baseline_func: AgentFunction,
        optimized_func: AgentFunction,
        experiment_name: str,
        baseline_version: str = "v1_baseline",
        optimized_version: str = "v2_optimized",
        save: bool = False,
    ) -> Dict[str, Any]:
        """
        Run comparison between baseline and optimized versions.

        Args:
            suite: TestSuite to run
            baseline_func: Baseline agent function
            optimized_func: Optimized agent function
            experiment_name: Name for this comparison
            baseline_version: Version string for baseline
            optimized_version: Version string for optimized
            save: If True, save results to storage

        Returns:
            Comparison summary with both runs and deltas
        """
        # Run baseline
        baseline_run = await self.run_suite(
            suite=suite,
            agent_func=baseline_func,
            experiment_version=baseline_version,
            phase="baseline",
            save=save,
        )

        # Run optimized
        optimized_run = await self.run_suite(
            suite=suite,
            agent_func=optimized_func,
            experiment_version=optimized_version,
            phase="optimized",
            save=save,
        )

        # Calculate comparison
        comparison = self._calculate_comparison(
            baseline=baseline_run,
            optimized=optimized_run,
            experiment_name=experiment_name,
        )

        return comparison

    # =========================================================================
    # INTERNAL: TEST EXECUTION
    # =========================================================================

    async def _run_parallel(
        self,
        test_cases: List[TestCase],
        agent_func: AgentFunction,
        experiment_version: str,
        run_id: str,
        config: RunnerConfig,
    ) -> List[TestResult]:
        """Run tests in parallel with concurrency limit"""
        semaphore = asyncio.Semaphore(config.max_concurrent)

        async def run_with_semaphore(tc: TestCase, index: int) -> TestResult:
            async with semaphore:
                result = await self._run_test(
                    test_case=tc,
                    agent_func=agent_func,
                    experiment_version=experiment_version,
                    config=config,
                )

                # Progress callback
                if config.progress_callback:
                    config.progress_callback(index + 1, len(test_cases), tc.id)

                return result

        tasks = [
            run_with_semaphore(tc, i)
            for i, tc in enumerate(test_cases)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to TestResults
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(TestResult(
                    test_case_id=test_cases[i].id,
                    success=False,
                    passed=False,
                    error=str(result),
                    error_type=type(result).__name__,
                ))
            else:
                final_results.append(result)

        return final_results

    async def _run_sequential(
        self,
        test_cases: List[TestCase],
        agent_func: AgentFunction,
        experiment_version: str,
        run_id: str,
        config: RunnerConfig,
    ) -> List[TestResult]:
        """Run tests sequentially"""
        results = []

        for i, tc in enumerate(test_cases):
            result = await self._run_test(
                test_case=tc,
                agent_func=agent_func,
                experiment_version=experiment_version,
                config=config,
            )
            results.append(result)

            # Progress callback
            if config.progress_callback:
                config.progress_callback(i + 1, len(test_cases), tc.id)

            # Fail fast
            if config.fail_fast and not result.passed:
                break

        return results

    async def _run_test(
        self,
        test_case: TestCase,
        agent_func: AgentFunction,
        experiment_version: str,
        config: RunnerConfig,
    ) -> TestResult:
        """Run a single test with optional retries"""
        last_result = None
        retry_count = 0

        max_attempts = 1 + (config.retry_count if config.retry_failed else 0)

        for attempt in range(max_attempts):
            try:
                result = await self._execute_test(
                    test_case=test_case,
                    agent_func=agent_func,
                    experiment_version=experiment_version,
                    timeout_seconds=config.test_timeout_seconds,
                )
                result.retry_count = retry_count

                # Success or passed - return immediately
                if result.success and result.passed:
                    return result

                last_result = result

                # Retry delay
                if attempt < max_attempts - 1 and config.retry_failed:
                    await asyncio.sleep(config.retry_delay_seconds)
                    retry_count += 1

            except Exception as e:
                last_result = TestResult(
                    test_case_id=test_case.id,
                    success=False,
                    passed=False,
                    error=str(e),
                    error_type=type(e).__name__,
                    retry_count=retry_count,
                )

                if not config.continue_on_error:
                    raise

        return last_result or TestResult(
            test_case_id=test_case.id,
            success=False,
            passed=False,
            error="Test failed after retries",
        )

    async def _execute_test(
        self,
        test_case: TestCase,
        agent_func: AgentFunction,
        experiment_version: str,
        timeout_seconds: int,
    ) -> TestResult:
        """Execute single test without retries"""
        start_time = time.time()

        # Run agent
        agent_start = time.time()
        try:
            trace = await self._call_agent(agent_func, test_case.input, timeout_seconds)
        except asyncio.TimeoutError:
            return TestResult(
                test_case_id=test_case.id,
                success=False,
                passed=False,
                error=f"Agent timed out after {timeout_seconds}s",
                error_type="TimeoutError",
            )
        except Exception as e:
            return TestResult(
                test_case_id=test_case.id,
                success=False,
                passed=False,
                error=str(e),
                error_type=type(e).__name__,
            )
        agent_latency = (time.time() - agent_start) * 1000

        # Run evaluation
        eval_start = time.time()
        try:
            expected_dict = self._test_case_to_expected_dict(test_case)
            evaluation = await self._pipeline.evaluate(
                trace=trace,
                expected=expected_dict,
                test_case_id=test_case.id,
                experiment_version=experiment_version,
            )
        except Exception as e:
            return TestResult(
                test_case_id=test_case.id,
                success=True,  # Agent succeeded, but eval failed
                passed=False,
                trace=trace,
                error=f"Evaluation error: {str(e)}",
                error_type=type(e).__name__,
                agent_latency_ms=agent_latency,
            )
        eval_latency = (time.time() - eval_start) * 1000

        total_latency = (time.time() - start_time) * 1000

        return TestResult(
            test_case_id=test_case.id,
            success=True,
            passed=evaluation.passed,
            trace=trace,
            evaluation=evaluation,
            agent_latency_ms=agent_latency,
            eval_latency_ms=eval_latency,
            total_latency_ms=total_latency,
            agent_cost=trace.get("total_cost", 0) if trace else 0,
            eval_cost=evaluation.total_cost,
        )

    async def _call_agent(
        self,
        agent_func: AgentFunction,
        input_data: Dict[str, Any],
        timeout_seconds: int,
    ) -> Dict[str, Any]:
        """Call agent function (handles sync and async)"""
        # Check if async
        if asyncio.iscoroutinefunction(agent_func):
            return await asyncio.wait_for(
                agent_func(input_data),
                timeout=timeout_seconds,
            )
        else:
            # Run sync function in thread pool
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(self._executor, agent_func, input_data),
                timeout=timeout_seconds,
            )

    # =========================================================================
    # INTERNAL: HELPERS
    # =========================================================================

    def _filter_tests(self, suite: TestSuite) -> List[TestCase]:
        """Filter test cases based on config"""
        return filter_test_cases(
            suite=suite,
            categories=self._config.categories,
            tags=self._config.tags,
            difficulties=self._config.difficulties,
            enabled_only=True,
        )

    def _merge_suite_config(self, suite_config) -> RunnerConfig:
        """Merge suite config with runner config"""
        return RunnerConfig(
            parallel=suite_config.parallel if hasattr(suite_config, 'parallel') else self._config.parallel,
            max_concurrent=suite_config.max_concurrent if hasattr(suite_config, 'max_concurrent') else self._config.max_concurrent,
            test_timeout_seconds=suite_config.timeout_seconds if hasattr(suite_config, 'timeout_seconds') else self._config.test_timeout_seconds,
            retry_failed=suite_config.retry_failed if hasattr(suite_config, 'retry_failed') else self._config.retry_failed,
            retry_count=suite_config.retry_count if hasattr(suite_config, 'retry_count') else self._config.retry_count,
            fail_fast=self._config.fail_fast,
            continue_on_error=self._config.continue_on_error,
            capture_exceptions=self._config.capture_exceptions,
            verbose=self._config.verbose,
            progress_callback=self._config.progress_callback,
        )

    def _test_case_to_expected_dict(self, test_case: TestCase) -> Dict[str, Any]:
        """Convert TestCase expected to dict for pipeline"""
        expected = test_case.expected
        return {
            "tool_called": expected.tool_called,
            "required_args": expected.required_args,
            "optional_args": expected.optional_args,
            "arg_types": expected.arg_types,
            "evaluation_criteria": expected.evaluation_criteria,
            "score_range": expected.score_range,
            # Include ground truth if available
            "ground_truth": test_case.ground_truth.__dict__ if test_case.ground_truth else None,
        }

    def _results_to_records(
        self,
        results: List[TestResult],
        run_id: str,
    ) -> List[EvaluationResultRecord]:
        """Convert TestResults to EvaluationResultRecords"""
        records = []

        for result in results:
            if result.evaluation:
                # Create records for each evaluator result
                for eval_result in result.evaluation.results:
                    record = EvaluationResultRecord(
                        id=f"{run_id}_{result.test_case_id}_{eval_result.evaluator}",
                        run_id=run_id,
                        test_case_id=result.test_case_id,
                        trace_id=result.trace.get("id") if result.trace else None,
                        evaluator=eval_result.evaluator,
                        score=eval_result.score,
                        passed=eval_result.passed,
                        reasoning=eval_result.reasoning,
                        details=eval_result.details,
                        issues=eval_result.issues,
                        cost=eval_result.cost,
                        latency_ms=eval_result.latency_ms,
                        confidence=eval_result.confidence,
                        timestamp=datetime.utcnow(),
                    )
                    records.append(record)
            elif result.error:
                # Create error record
                record = EvaluationResultRecord(
                    id=f"{run_id}_{result.test_case_id}_error",
                    run_id=run_id,
                    test_case_id=result.test_case_id,
                    evaluator="error",
                    score=0,
                    passed=False,
                    reasoning=f"Test execution failed: {result.error}",
                    details={"error_type": result.error_type},
                    issues=[result.error],
                    timestamp=datetime.utcnow(),
                )
                records.append(record)

        return records

    def _calculate_metrics(self, results: List[TestResult]) -> EvaluationRunMetrics:
        """Calculate aggregated metrics from test results"""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        # Gather scores
        quality_scores = []
        tool_use_scores = []
        model_judge_scores = []
        agent_costs = []
        agent_latencies = []
        eval_costs = []
        eval_latencies = []

        for result in results:
            if result.evaluation:
                quality_scores.append(result.evaluation.overall_score)

                for eval_result in result.evaluation.results:
                    if eval_result.evaluator == "tool_use":
                        tool_use_scores.append(eval_result.score)
                    elif eval_result.evaluator == "model_judge":
                        model_judge_scores.append(eval_result.score)

            agent_costs.append(result.agent_cost)
            agent_latencies.append(result.agent_latency_ms)
            eval_costs.append(result.eval_cost)
            eval_latencies.append(result.eval_latency_ms)

        return EvaluationRunMetrics(
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=0,
            avg_quality_score=sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            min_quality_score=min(quality_scores) if quality_scores else None,
            max_quality_score=max(quality_scores) if quality_scores else None,
            avg_tool_use_score=sum(tool_use_scores) / len(tool_use_scores) if tool_use_scores else None,
            avg_model_judge_score=sum(model_judge_scores) / len(model_judge_scores) if model_judge_scores else None,
            pass_rate=passed / total if total > 0 else 0,
            total_agent_cost=sum(agent_costs),
            total_agent_latency_ms=sum(agent_latencies),
            avg_agent_cost=sum(agent_costs) / len(agent_costs) if agent_costs else 0,
            avg_agent_latency_ms=sum(agent_latencies) / len(agent_latencies) if agent_latencies else 0,
            total_eval_cost=sum(eval_costs),
            total_eval_latency_ms=sum(eval_latencies),
        )

    def _calculate_comparison(
        self,
        baseline: EvaluationRun,
        optimized: EvaluationRun,
        experiment_name: str,
    ) -> Dict[str, Any]:
        """Calculate comparison between two runs"""
        b = baseline.metrics
        o = optimized.metrics

        # Calculate deltas
        quality_change = o.avg_quality_score - b.avg_quality_score
        quality_change_pct = (quality_change / b.avg_quality_score * 100) if b.avg_quality_score > 0 else 0

        cost_change_pct = 0
        if b.avg_agent_cost > 0:
            cost_change_pct = ((o.avg_agent_cost - b.avg_agent_cost) / b.avg_agent_cost) * 100

        latency_change_pct = 0
        if b.avg_agent_latency_ms > 0:
            latency_change_pct = ((o.avg_agent_latency_ms - b.avg_agent_latency_ms) / b.avg_agent_latency_ms) * 100

        pass_rate_change = o.pass_rate - b.pass_rate

        # Determine recommendation
        recommendation = self._determine_recommendation(
            quality_change=quality_change,
            cost_change_pct=cost_change_pct,
            pass_rate_change=pass_rate_change,
        )

        return {
            "experiment_name": experiment_name,
            "baseline": {
                "run_id": baseline.run_id,
                "version": baseline.experiment_version,
                "avg_quality_score": b.avg_quality_score,
                "pass_rate": b.pass_rate,
                "avg_cost": b.avg_agent_cost,
                "avg_latency_ms": b.avg_agent_latency_ms,
            },
            "optimized": {
                "run_id": optimized.run_id,
                "version": optimized.experiment_version,
                "avg_quality_score": o.avg_quality_score,
                "pass_rate": o.pass_rate,
                "avg_cost": o.avg_agent_cost,
                "avg_latency_ms": o.avg_agent_latency_ms,
            },
            "deltas": {
                "quality_change_abs": round(quality_change, 2),
                "quality_change_pct": round(quality_change_pct, 2),
                "cost_change_pct": round(cost_change_pct, 2),
                "latency_change_pct": round(latency_change_pct, 2),
                "pass_rate_change_abs": round(pass_rate_change, 4),
            },
            "recommendation": recommendation,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _determine_recommendation(
        self,
        quality_change: float,
        cost_change_pct: float,
        pass_rate_change: float,
    ) -> str:
        """Determine deployment recommendation"""
        # Quality significantly worse
        if quality_change < -5:
            return Recommendation.REJECT.value

        # Pass rate dropped significantly
        if pass_rate_change < -0.1:  # 10% drop
            return Recommendation.REJECT.value

        # Quality improved and costs reasonable
        if quality_change >= 2 and cost_change_pct <= 20:
            return Recommendation.DEPLOY.value

        # Costs reduced significantly without quality loss
        if cost_change_pct < -20 and quality_change >= -2:
            return Recommendation.DEPLOY.value

        # Mixed results
        if abs(quality_change) < 2 and abs(cost_change_pct) < 10:
            return Recommendation.NEUTRAL.value

        return Recommendation.INVESTIGATE.value

    def _generate_run_id(self) -> str:
        """Generate unique run ID"""
        return f"run_{uuid.uuid4().hex[:16]}"

    # =========================================================================
    # STATS & CLEANUP
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get runner statistics"""
        return {
            "runs_executed": self._runs_executed,
            "tests_executed": self._tests_executed,
            "total_cost_usd": round(self._total_cost, 6),
            "pipeline_stats": self._pipeline.get_stats(),
            "config": {
                "parallel": self._config.parallel,
                "max_concurrent": self._config.max_concurrent,
                "retry_failed": self._config.retry_failed,
            },
        }

    def shutdown(self) -> None:
        """Shutdown thread pool"""
        self._executor.shutdown(wait=False)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
