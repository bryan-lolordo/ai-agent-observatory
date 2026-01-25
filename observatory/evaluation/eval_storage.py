"""
Evaluation Storage
==================

High-level interface for persisting and retrieving evaluation data.

Provides:
- Save/load evaluation runs, results, and comparisons
- Query methods for analytics and history
- Export capabilities for reporting
- Integration with existing Storage class

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │                    EvaluationStore                      │
    │                                                         │
    │  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐ │
    │  │ Runs        │  │ Results      │  │ Comparisons   │ │
    │  │ - save      │  │ - save       │  │ - save        │ │
    │  │ - get       │  │ - get        │  │ - get         │ │
    │  │ - list      │  │ - query      │  │ - list        │ │
    │  │ - delete    │  │ - aggregate  │  │ - latest      │ │
    │  └─────────────┘  └──────────────┘  └───────────────┘ │
    │                         │                              │
    │                    ┌────┴────┐                        │
    │                    │ Storage │                        │
    │                    │ (SQLite)│                        │
    │                    └─────────┘                        │
    └─────────────────────────────────────────────────────────┘

Usage:
    from observatory.evaluation.eval_storage import EvaluationStore

    # Initialize with existing Storage instance
    store = EvaluationStore(storage)

    # Save evaluation run
    store.save_run(evaluation_run)

    # Save results
    store.save_results(results)

    # Query history
    history = store.get_run_history(test_suite_id="job_matcher_tests")
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

from observatory.storage import Storage
from observatory.models import (
    EvaluationRun,
    EvaluationRunMetrics,
    EvaluationResultRecord,
    ComparisonRecord,
    VersionMetrics,
    ComparisonDeltas,
    EvaluationStatus,
    Recommendation,
)


# =============================================================================
# DATA CLASSES FOR QUERY RESULTS
# =============================================================================

@dataclass
class RunSummary:
    """Summary of an evaluation run for listing"""
    run_id: str
    test_suite_id: str
    test_suite_name: Optional[str]
    experiment_version: str
    phase: str
    status: str
    pass_rate: float
    avg_quality_score: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    total_cost: float
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]


@dataclass
class TestCaseHistory:
    """History of a specific test case across runs"""
    test_case_id: str
    runs: List[Dict[str, Any]]  # List of {run_id, score, passed, timestamp}
    avg_score: float
    pass_rate: float
    trend: str  # "improving", "declining", "stable"


@dataclass
class ExperimentSummary:
    """Summary of an experiment's evaluation history"""
    experiment_name: str
    total_runs: int
    baseline_runs: int
    optimized_runs: int
    comparisons: int
    latest_recommendation: Optional[str]
    best_quality_score: float
    best_pass_rate: float


# =============================================================================
# EVALUATION STORE
# =============================================================================

class EvaluationStore:
    """
    High-level interface for evaluation data persistence.

    Wraps the Storage class with evaluation-specific methods and
    provides higher-level queries for analytics.
    """

    def __init__(self, storage: Storage):
        """
        Initialize evaluation store.

        Args:
            storage: Observatory Storage instance
        """
        self._storage = storage

    # =========================================================================
    # EVALUATION RUNS
    # =========================================================================

    def save_run(self, run: EvaluationRun) -> str:
        """
        Save an evaluation run.

        Args:
            run: EvaluationRun to save

        Returns:
            run_id of saved run
        """
        # Generate ID if not set
        if not run.run_id:
            run.run_id = self._generate_id("run")

        run_data = self._run_to_dict(run)
        self._storage.save_evaluation_run(run_data)
        return run.run_id

    def get_run(self, run_id: str) -> Optional[EvaluationRun]:
        """
        Get an evaluation run by ID.

        Args:
            run_id: Run ID to retrieve

        Returns:
            EvaluationRun or None if not found
        """
        data = self._storage.get_evaluation_run(run_id)
        if data:
            return self._dict_to_run(data)
        return None

    def get_runs(
        self,
        test_suite_id: Optional[str] = None,
        experiment_version: Optional[str] = None,
        phase: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EvaluationRun]:
        """
        Query evaluation runs with filters.

        Args:
            test_suite_id: Filter by test suite
            experiment_version: Filter by version
            phase: Filter by phase (baseline/optimized)
            status: Filter by status
            limit: Max results
            offset: Skip first N results

        Returns:
            List of EvaluationRun objects
        """
        data_list = self._storage.get_evaluation_runs(
            test_suite_id=test_suite_id,
            experiment_version=experiment_version,
            phase=phase,
            status=status,
            limit=limit,
            # Note: offset not implemented in Storage, pagination via limit only
        )
        # Apply offset manually if needed
        if offset > 0:
            data_list = data_list[offset:]
        return [self._dict_to_run(d) for d in data_list]

    def get_run_summaries(
        self,
        test_suite_id: Optional[str] = None,
        days: int = 30,
        limit: int = 50,
    ) -> List[RunSummary]:
        """
        Get summarized run information for listing.

        Args:
            test_suite_id: Filter by test suite
            days: Look back period
            limit: Max results

        Returns:
            List of RunSummary objects
        """
        runs = self.get_runs(
            test_suite_id=test_suite_id,
            limit=limit,
        )

        # Filter by time
        cutoff = datetime.utcnow() - timedelta(days=days)
        runs = [r for r in runs if r.started_at and r.started_at >= cutoff]

        summaries = []
        for run in runs:
            summary = RunSummary(
                run_id=run.run_id,
                test_suite_id=run.test_suite_id,
                test_suite_name=run.test_suite_name,
                experiment_version=run.experiment_version,
                phase=run.phase,
                status=run.status,
                pass_rate=run.metrics.pass_rate,
                avg_quality_score=run.metrics.avg_quality_score,
                total_tests=run.metrics.total_tests,
                passed_tests=run.metrics.passed_tests,
                failed_tests=run.metrics.failed_tests,
                total_cost=run.metrics.total_eval_cost,
                started_at=run.started_at,
                completed_at=run.completed_at,
                duration_seconds=run.duration_seconds,
            )
            summaries.append(summary)

        return summaries

    def update_run_status(
        self,
        run_id: str,
        status: str,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None,
    ) -> bool:
        """
        Update run status (e.g., from running to completed).

        Args:
            run_id: Run to update
            status: New status
            error_message: Error message if failed
            completed_at: Completion timestamp

        Returns:
            True if updated successfully
        """
        run = self.get_run(run_id)
        if not run:
            return False

        run.status = status
        if error_message:
            run.error_message = error_message
        if completed_at:
            run.completed_at = completed_at
            if run.started_at:
                run.duration_seconds = (completed_at - run.started_at).total_seconds()

        self.save_run(run)
        return True

    def update_run_metrics(
        self,
        run_id: str,
        metrics: EvaluationRunMetrics,
    ) -> bool:
        """
        Update run metrics after evaluation completes.

        Args:
            run_id: Run to update
            metrics: Updated metrics

        Returns:
            True if updated successfully
        """
        run = self.get_run(run_id)
        if not run:
            return False

        run.metrics = metrics
        self.save_run(run)
        return True

    def delete_run(self, run_id: str, cascade: bool = True) -> bool:
        """
        Delete an evaluation run.

        Args:
            run_id: Run to delete
            cascade: If True, also delete associated results

        Returns:
            True if deleted
        """
        if cascade:
            # Delete associated results first
            results = self.get_results(run_id=run_id)
            for result in results:
                self.delete_result(result.id)

        return self._storage.delete_evaluation_run(run_id)

    # =========================================================================
    # EVALUATION RESULTS
    # =========================================================================

    def save_result(self, result: EvaluationResultRecord) -> str:
        """
        Save a single evaluation result.

        Args:
            result: EvaluationResultRecord to save

        Returns:
            result_id of saved result
        """
        if not result.id:
            result.id = self._generate_id("result")

        result_data = self._result_to_dict(result)
        self._storage.save_evaluation_result(result_data)
        return result.id

    def save_results(self, results: List[EvaluationResultRecord]) -> List[str]:
        """
        Save multiple evaluation results in batch.

        Args:
            results: List of EvaluationResultRecord objects

        Returns:
            List of result_ids
        """
        result_ids = []
        data_list = []

        for result in results:
            if not result.id:
                result.id = self._generate_id("result")
            result_ids.append(result.id)
            data_list.append(self._result_to_dict(result))

        self._storage.save_evaluation_results_batch(data_list)
        return result_ids

    def get_results(
        self,
        run_id: Optional[str] = None,
        test_case_id: Optional[str] = None,
        evaluator: Optional[str] = None,
        passed: Optional[bool] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[EvaluationResultRecord]:
        """
        Query evaluation results.

        Args:
            run_id: Filter by run
            test_case_id: Filter by test case
            evaluator: Filter by evaluator type
            passed: Filter by pass/fail
            limit: Max results
            offset: Skip first N

        Returns:
            List of EvaluationResultRecord objects
        """
        data_list = self._storage.get_evaluation_results(
            run_id=run_id,
            test_case_id=test_case_id,
            evaluator=evaluator,
            passed=passed,
            limit=limit,
            # Note: offset not implemented in Storage, pagination via limit only
        )
        # Apply offset manually if needed
        if offset > 0:
            data_list = data_list[offset:]
        return [self._dict_to_result(d) for d in data_list]

    def get_results_for_run(self, run_id: str) -> List[EvaluationResultRecord]:
        """Get all results for a specific run"""
        return self.get_results(run_id=run_id, limit=10000)

    def get_failed_results(
        self,
        run_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[EvaluationResultRecord]:
        """Get failed evaluation results for debugging"""
        return self.get_results(run_id=run_id, passed=False, limit=limit)

    def delete_result(self, result_id: str) -> bool:
        """Delete a specific result"""
        # Implementation would require adding this to Storage class
        # For now, this is a placeholder
        return True

    # =========================================================================
    # COMPARISONS
    # =========================================================================

    def save_comparison(self, comparison: ComparisonRecord) -> str:
        """
        Save a comparison result.

        Args:
            comparison: ComparisonRecord to save

        Returns:
            comparison_id of saved comparison
        """
        if not comparison.comparison_id:
            comparison.comparison_id = self._generate_id("cmp")

        comparison_data = self._comparison_to_dict(comparison)
        self._storage.save_comparison_result(comparison_data)
        return comparison.comparison_id

    def get_comparison(self, comparison_id: str) -> Optional[ComparisonRecord]:
        """
        Get a comparison by ID.

        Args:
            comparison_id: Comparison ID

        Returns:
            ComparisonRecord or None
        """
        data = self._storage.get_comparison_result(comparison_id)
        if data:
            return self._dict_to_comparison(data)
        return None

    def get_comparisons(
        self,
        experiment_name: Optional[str] = None,
        recommendation: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ComparisonRecord]:
        """
        Query comparisons with filters.

        Args:
            experiment_name: Filter by experiment
            recommendation: Filter by recommendation (DEPLOY/INVESTIGATE/REJECT)
            limit: Max results
            offset: Skip first N

        Returns:
            List of ComparisonRecord objects
        """
        data_list = self._storage.get_comparison_results(
            experiment_name=experiment_name,
            recommendation=recommendation,
            limit=limit,
            # Note: offset not implemented in Storage, pagination via limit only
        )
        # Apply offset manually if needed
        if offset > 0:
            data_list = data_list[offset:]
        return [self._dict_to_comparison(d) for d in data_list]

    def get_latest_comparison(self, experiment_name: str) -> Optional[ComparisonRecord]:
        """
        Get the most recent comparison for an experiment.

        Args:
            experiment_name: Experiment name

        Returns:
            Most recent ComparisonRecord or None
        """
        data = self._storage.get_latest_comparison(experiment_name)
        if data:
            return self._dict_to_comparison(data)
        return None

    # =========================================================================
    # ANALYTICS & QUERIES
    # =========================================================================

    def get_test_case_history(
        self,
        test_case_id: str,
        test_suite_id: Optional[str] = None,
        limit: int = 20,
    ) -> TestCaseHistory:
        """
        Get evaluation history for a specific test case.

        Args:
            test_case_id: Test case to analyze
            test_suite_id: Filter by test suite
            limit: Max runs to include

        Returns:
            TestCaseHistory with trend analysis
        """
        results = self.get_results(test_case_id=test_case_id, limit=limit * 5)

        # Group by run
        runs_data = []
        run_ids_seen = set()

        for result in results:
            if result.run_id not in run_ids_seen:
                runs_data.append({
                    "run_id": result.run_id,
                    "score": result.score,
                    "passed": result.passed,
                    "timestamp": result.timestamp,
                    "evaluator": result.evaluator,
                })
                run_ids_seen.add(result.run_id)

        # Sort by timestamp
        runs_data.sort(key=lambda x: x.get("timestamp") or datetime.min, reverse=True)
        runs_data = runs_data[:limit]

        # Calculate stats
        scores = [r["score"] for r in runs_data if r["score"] is not None]
        passed_count = sum(1 for r in runs_data if r["passed"])

        avg_score = sum(scores) / len(scores) if scores else 0
        pass_rate = passed_count / len(runs_data) if runs_data else 0

        # Determine trend (simple: compare first half to second half)
        trend = "stable"
        if len(scores) >= 4:
            mid = len(scores) // 2
            recent_avg = sum(scores[:mid]) / mid
            older_avg = sum(scores[mid:]) / (len(scores) - mid)
            if recent_avg > older_avg + 5:
                trend = "improving"
            elif recent_avg < older_avg - 5:
                trend = "declining"

        return TestCaseHistory(
            test_case_id=test_case_id,
            runs=runs_data,
            avg_score=avg_score,
            pass_rate=pass_rate,
            trend=trend,
        )

    def get_experiment_summary(self, experiment_name: str) -> ExperimentSummary:
        """
        Get summary of an experiment's evaluation history.

        Args:
            experiment_name: Experiment to summarize

        Returns:
            ExperimentSummary with aggregate stats
        """
        # Get runs for this experiment
        runs = self.get_runs(experiment_version=experiment_name, limit=100)

        # Get comparisons
        comparisons = self.get_comparisons(experiment_name=experiment_name, limit=100)

        # Separate by phase
        baseline_runs = [r for r in runs if r.phase == "baseline"]
        optimized_runs = [r for r in runs if r.phase == "optimized"]

        # Find best scores
        all_quality_scores = [r.metrics.avg_quality_score for r in runs if r.metrics.avg_quality_score]
        all_pass_rates = [r.metrics.pass_rate for r in runs if r.metrics.pass_rate]

        # Get latest recommendation
        latest_comparison = self.get_latest_comparison(experiment_name)
        latest_recommendation = latest_comparison.recommendation if latest_comparison else None

        return ExperimentSummary(
            experiment_name=experiment_name,
            total_runs=len(runs),
            baseline_runs=len(baseline_runs),
            optimized_runs=len(optimized_runs),
            comparisons=len(comparisons),
            latest_recommendation=latest_recommendation,
            best_quality_score=max(all_quality_scores) if all_quality_scores else 0,
            best_pass_rate=max(all_pass_rates) if all_pass_rates else 0,
        )

    def get_evaluation_trends(
        self,
        test_suite_id: str,
        days: int = 30,
        granularity: str = "day",
    ) -> List[Dict[str, Any]]:
        """
        Get evaluation trends over time.

        Args:
            test_suite_id: Test suite to analyze
            days: Look back period
            granularity: "day" or "week"

        Returns:
            List of trend data points
        """
        history = self._storage.get_evaluation_history(
            test_suite_id=test_suite_id,
            days=days,
        )

        # Group by granularity
        grouped: Dict[str, List[Dict]] = {}

        for record in history:
            timestamp = record.get("started_at")
            if not timestamp:
                continue

            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)

            if granularity == "week":
                key = timestamp.strftime("%Y-W%W")
            else:
                key = timestamp.strftime("%Y-%m-%d")

            if key not in grouped:
                grouped[key] = []
            grouped[key].append(record)

        # Aggregate each period
        trends = []
        for period, records in sorted(grouped.items()):
            quality_scores = [r.get("avg_quality_score", 0) for r in records if r.get("avg_quality_score")]
            pass_rates = [r.get("pass_rate", 0) for r in records if r.get("pass_rate")]

            trends.append({
                "period": period,
                "runs": len(records),
                "avg_quality_score": sum(quality_scores) / len(quality_scores) if quality_scores else 0,
                "avg_pass_rate": sum(pass_rates) / len(pass_rates) if pass_rates else 0,
                "total_tests": sum(r.get("total_tests", 0) for r in records),
            })

        return trends

    def get_failing_test_cases(
        self,
        test_suite_id: str,
        min_failure_rate: float = 0.5,
        min_runs: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Find test cases that frequently fail.

        Args:
            test_suite_id: Test suite to analyze
            min_failure_rate: Minimum failure rate (0-1) to include
            min_runs: Minimum number of runs required

        Returns:
            List of failing test case stats
        """
        stats = self._storage.get_test_case_stats(
            test_suite_id=test_suite_id,
        )

        failing = []
        for tc_stats in stats:
            run_count = tc_stats.get("run_count", 0)
            fail_count = tc_stats.get("fail_count", 0)

            if run_count < min_runs:
                continue

            failure_rate = fail_count / run_count if run_count > 0 else 0
            if failure_rate >= min_failure_rate:
                failing.append({
                    "test_case_id": tc_stats.get("test_case_id"),
                    "run_count": run_count,
                    "fail_count": fail_count,
                    "failure_rate": failure_rate,
                    "avg_score": tc_stats.get("avg_score", 0),
                    "last_run": tc_stats.get("last_run"),
                })

        # Sort by failure rate (worst first)
        failing.sort(key=lambda x: x["failure_rate"], reverse=True)
        return failing

    # =========================================================================
    # EXPORT
    # =========================================================================

    def export_run_to_dict(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Export a complete run with all results as a dictionary.

        Args:
            run_id: Run to export

        Returns:
            Complete run data with results
        """
        run = self.get_run(run_id)
        if not run:
            return None

        results = self.get_results_for_run(run_id)

        return {
            "run": self._run_to_dict(run),
            "results": [self._result_to_dict(r) for r in results],
            "exported_at": datetime.utcnow().isoformat(),
        }

    def export_comparison_to_dict(self, comparison_id: str) -> Optional[Dict[str, Any]]:
        """
        Export a comparison with linked runs.

        Args:
            comparison_id: Comparison to export

        Returns:
            Complete comparison data with run details
        """
        comparison = self.get_comparison(comparison_id)
        if not comparison:
            return None

        baseline_run = self.get_run(comparison.baseline_run_id)
        optimized_run = self.get_run(comparison.optimized_run_id)

        return {
            "comparison": self._comparison_to_dict(comparison),
            "baseline_run": self._run_to_dict(baseline_run) if baseline_run else None,
            "optimized_run": self._run_to_dict(optimized_run) if optimized_run else None,
            "exported_at": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # CONVERSION HELPERS
    # =========================================================================

    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID with prefix"""
        return f"{prefix}_{uuid.uuid4().hex[:16]}"

    def _run_to_dict(self, run: EvaluationRun) -> Dict[str, Any]:
        """Convert EvaluationRun to storage dict"""
        return {
            "run_id": run.run_id,
            "test_suite_id": run.test_suite_id,
            "test_suite_name": run.test_suite_name,
            "experiment_name": run.experiment_name,
            "experiment_version": run.experiment_version,
            "phase": run.phase,
            "status": run.status,
            "error_message": run.error_message,
            "started_at": run.started_at,  # Keep as datetime for SQLite
            "completed_at": run.completed_at,  # Keep as datetime for SQLite
            "duration_seconds": run.duration_seconds,
            # Metrics
            "total_tests": run.metrics.total_tests,
            "passed_tests": run.metrics.passed_tests,
            "failed_tests": run.metrics.failed_tests,
            "skipped_tests": run.metrics.skipped_tests,
            "avg_quality_score": run.metrics.avg_quality_score,
            "min_quality_score": run.metrics.min_quality_score,
            "max_quality_score": run.metrics.max_quality_score,
            "avg_tool_use_score": run.metrics.avg_tool_use_score,
            "avg_model_judge_score": run.metrics.avg_model_judge_score,
            "pass_rate": run.metrics.pass_rate,
            "total_agent_cost": run.metrics.total_agent_cost,
            "total_agent_latency_ms": run.metrics.total_agent_latency_ms,
            "avg_agent_cost": run.metrics.avg_agent_cost,
            "avg_agent_latency_ms": run.metrics.avg_agent_latency_ms,
            "total_eval_cost": run.metrics.total_eval_cost,
            "total_eval_latency_ms": run.metrics.total_eval_latency_ms,
            # Metadata
            "metadata": run.metadata,
        }

    def _dict_to_run(self, data: Dict[str, Any]) -> EvaluationRun:
        """Convert storage dict to EvaluationRun"""
        metrics = EvaluationRunMetrics(
            total_tests=data.get("total_tests", 0),
            passed_tests=data.get("passed_tests", 0),
            failed_tests=data.get("failed_tests", 0),
            skipped_tests=data.get("skipped_tests", 0),
            avg_quality_score=data.get("avg_quality_score", 0),
            min_quality_score=data.get("min_quality_score"),
            max_quality_score=data.get("max_quality_score"),
            avg_tool_use_score=data.get("avg_tool_use_score"),
            avg_model_judge_score=data.get("avg_model_judge_score"),
            pass_rate=data.get("pass_rate", 0),
            total_agent_cost=data.get("total_agent_cost", 0),
            total_agent_latency_ms=data.get("total_agent_latency_ms", 0),
            avg_agent_cost=data.get("avg_agent_cost", 0),
            avg_agent_latency_ms=data.get("avg_agent_latency_ms", 0),
            total_eval_cost=data.get("total_eval_cost", 0),
            total_eval_latency_ms=data.get("total_eval_latency_ms", 0),
        )

        started_at = data.get("started_at")
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at)

        completed_at = data.get("completed_at")
        if isinstance(completed_at, str):
            completed_at = datetime.fromisoformat(completed_at)

        return EvaluationRun(
            run_id=data.get("run_id", ""),
            test_suite_id=data.get("test_suite_id", ""),
            test_suite_name=data.get("test_suite_name"),
            experiment_name=data.get("experiment_name"),
            experiment_version=data.get("experiment_version", ""),
            phase=data.get("phase", "baseline"),
            status=data.get("status", EvaluationStatus.PENDING.value),
            error_message=data.get("error_message"),
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=data.get("duration_seconds"),
            metrics=metrics,
            metadata=data.get("metadata", {}),
        )

    def _result_to_dict(self, result: EvaluationResultRecord) -> Dict[str, Any]:
        """Convert EvaluationResultRecord to storage dict"""
        return {
            "result_id": result.id,
            "run_id": result.run_id,
            "test_case_id": result.test_case_id,
            "trace_id": result.trace_id,
            "evaluator": result.evaluator,
            "evaluator_version": result.evaluator_version,
            "score": result.score,
            "passed": result.passed,
            "reasoning": result.reasoning,
            "details": result.details,
            "issues": result.issues,
            "cost": result.cost,
            "latency_ms": result.latency_ms,
            "confidence": result.confidence,
            "timestamp": result.timestamp,  # Keep as datetime for SQLite
        }

    def _dict_to_result(self, data: Dict[str, Any]) -> EvaluationResultRecord:
        """Convert storage dict to EvaluationResultRecord"""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return EvaluationResultRecord(
            id=data.get("result_id", ""),
            run_id=data.get("run_id", ""),
            test_case_id=data.get("test_case_id", ""),
            trace_id=data.get("trace_id"),
            evaluator=data.get("evaluator", ""),
            evaluator_version=data.get("evaluator_version"),
            score=data.get("score", 0),
            passed=data.get("passed", False),
            reasoning=data.get("reasoning", ""),
            details=data.get("details", {}),
            issues=data.get("issues", []),
            cost=data.get("cost", 0),
            latency_ms=data.get("latency_ms", 0),
            confidence=data.get("confidence"),
            timestamp=timestamp or datetime.utcnow(),
        )

    def _comparison_to_dict(self, comparison: ComparisonRecord) -> Dict[str, Any]:
        """Convert ComparisonRecord to storage dict"""
        return {
            "comparison_id": comparison.comparison_id,
            "experiment_name": comparison.experiment_name,
            "baseline_run_id": comparison.baseline_run_id,
            "optimized_run_id": comparison.optimized_run_id,
            # Baseline metrics
            "baseline_version": comparison.baseline.version,
            "baseline_sample_size": comparison.baseline.sample_size,
            "baseline_avg_quality_score": comparison.baseline.avg_quality_score,
            "baseline_avg_tool_use_score": comparison.baseline.avg_tool_use_score,
            "baseline_avg_model_judge_score": comparison.baseline.avg_model_judge_score,
            "baseline_pass_rate": comparison.baseline.pass_rate,
            "baseline_avg_cost": comparison.baseline.avg_cost,
            "baseline_avg_latency_ms": comparison.baseline.avg_latency_ms,
            "baseline_avg_tokens": comparison.baseline.avg_tokens,
            "baseline_p95_latency_ms": comparison.baseline.p95_latency_ms,
            # Optimized metrics
            "optimized_version": comparison.optimized.version,
            "optimized_sample_size": comparison.optimized.sample_size,
            "optimized_avg_quality_score": comparison.optimized.avg_quality_score,
            "optimized_avg_tool_use_score": comparison.optimized.avg_tool_use_score,
            "optimized_avg_model_judge_score": comparison.optimized.avg_model_judge_score,
            "optimized_pass_rate": comparison.optimized.pass_rate,
            "optimized_avg_cost": comparison.optimized.avg_cost,
            "optimized_avg_latency_ms": comparison.optimized.avg_latency_ms,
            "optimized_avg_tokens": comparison.optimized.avg_tokens,
            "optimized_p95_latency_ms": comparison.optimized.p95_latency_ms,
            # Deltas
            "quality_change_abs": comparison.deltas.quality_change_abs,
            "quality_change_pct": comparison.deltas.quality_change_pct,
            "cost_change_pct": comparison.deltas.cost_change_pct,
            "latency_change_pct": comparison.deltas.latency_change_pct,
            "pass_rate_change_abs": comparison.deltas.pass_rate_change_abs,
            "tool_use_change_abs": comparison.deltas.tool_use_change_abs,
            "model_judge_change_abs": comparison.deltas.model_judge_change_abs,
            # Recommendation
            "recommendation": comparison.recommendation,
            "confidence": comparison.confidence,
            "reason": comparison.reason,
            "summary": comparison.summary,
            # Economics
            "total_eval_cost": comparison.total_eval_cost,
            "eval_overhead_pct": comparison.eval_overhead_pct,
            # Timestamp
            "timestamp": comparison.timestamp,  # Keep as datetime for SQLite
            # Metadata
            "metadata": comparison.metadata,
        }

    def _dict_to_comparison(self, data: Dict[str, Any]) -> ComparisonRecord:
        """Convert storage dict to ComparisonRecord"""
        baseline = VersionMetrics(
            version=data.get("baseline_version", ""),
            run_id=data.get("baseline_run_id", ""),
            sample_size=data.get("baseline_sample_size", 0),
            avg_quality_score=data.get("baseline_avg_quality_score", 0),
            avg_tool_use_score=data.get("baseline_avg_tool_use_score", 0),
            avg_model_judge_score=data.get("baseline_avg_model_judge_score", 0),
            pass_rate=data.get("baseline_pass_rate", 0),
            avg_cost=data.get("baseline_avg_cost", 0),
            avg_latency_ms=data.get("baseline_avg_latency_ms", 0),
            avg_tokens=data.get("baseline_avg_tokens", 0),
            p95_latency_ms=data.get("baseline_p95_latency_ms"),
        )

        optimized = VersionMetrics(
            version=data.get("optimized_version", ""),
            run_id=data.get("optimized_run_id", ""),
            sample_size=data.get("optimized_sample_size", 0),
            avg_quality_score=data.get("optimized_avg_quality_score", 0),
            avg_tool_use_score=data.get("optimized_avg_tool_use_score", 0),
            avg_model_judge_score=data.get("optimized_avg_model_judge_score", 0),
            pass_rate=data.get("optimized_pass_rate", 0),
            avg_cost=data.get("optimized_avg_cost", 0),
            avg_latency_ms=data.get("optimized_avg_latency_ms", 0),
            avg_tokens=data.get("optimized_avg_tokens", 0),
            p95_latency_ms=data.get("optimized_p95_latency_ms"),
        )

        deltas = ComparisonDeltas(
            quality_change_abs=data.get("quality_change_abs", 0),
            quality_change_pct=data.get("quality_change_pct", 0),
            cost_change_pct=data.get("cost_change_pct", 0),
            latency_change_pct=data.get("latency_change_pct", 0),
            pass_rate_change_abs=data.get("pass_rate_change_abs", 0),
            tool_use_change_abs=data.get("tool_use_change_abs"),
            model_judge_change_abs=data.get("model_judge_change_abs"),
        )

        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return ComparisonRecord(
            comparison_id=data.get("comparison_id", ""),
            experiment_name=data.get("experiment_name", ""),
            baseline_run_id=data.get("baseline_run_id", ""),
            optimized_run_id=data.get("optimized_run_id", ""),
            baseline=baseline,
            optimized=optimized,
            deltas=deltas,
            recommendation=data.get("recommendation", Recommendation.NEUTRAL.value),
            confidence=data.get("confidence", "Medium"),
            reason=data.get("reason", ""),
            summary=data.get("summary", ""),
            total_eval_cost=data.get("total_eval_cost", 0),
            eval_overhead_pct=data.get("eval_overhead_pct", 0),
            timestamp=timestamp or datetime.utcnow(),
            metadata=data.get("metadata", {}),
        )
