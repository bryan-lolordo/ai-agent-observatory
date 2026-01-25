"""
Comparison Service - Baseline vs Optimized Analysis
====================================================

Compares different versions of an experiment to generate
deployment recommendations.

Usage:
    comparison = ComparisonService()

    result = comparison.compare(
        baseline_results=baseline_aggregated_results,
        optimized_results=optimized_aggregated_results,
        baseline_metrics={"avg_cost": 0.0623, "avg_latency_ms": 2341},
        optimized_metrics={"avg_cost": 0.0284, "avg_latency_ms": 246},
    )

    print(result.recommendation)  # "DEPLOY", "INVESTIGATE", or "REJECT"
    print(result.summary)         # Human-readable summary
"""

import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from observatory.evaluation.pipeline import AggregatedResult


class Recommendation(str, Enum):
    """Deployment recommendation"""
    DEPLOY = "DEPLOY"           # Safe to deploy
    INVESTIGATE = "INVESTIGATE"  # Review before deploying
    REJECT = "REJECT"           # Do not deploy
    NEUTRAL = "NEUTRAL"         # No significant change


@dataclass
class VersionMetrics:
    """Aggregated metrics for a version"""
    version: str
    sample_size: int

    # Quality metrics (from evaluations)
    avg_quality_score: float
    avg_tool_use_score: float
    avg_model_judge_score: float
    pass_rate: float

    # Performance metrics (from Observatory traces)
    avg_cost: float
    avg_latency_ms: float
    avg_tokens: int
    p95_latency_ms: Optional[float] = None

    # Evaluation overhead
    eval_cost: float = 0.0
    eval_latency_ms: float = 0.0


@dataclass
class ComparisonResult:
    """
    Result of comparing baseline vs optimized versions.

    Contains deltas, recommendation, and supporting data.
    """
    experiment_name: str

    # Version data
    baseline: VersionMetrics
    optimized: VersionMetrics

    # Deltas
    quality_change_abs: float       # Absolute change in quality score
    quality_change_pct: float       # Percentage change
    cost_change_pct: float          # % change in cost (negative = savings)
    latency_change_pct: float       # % change in latency (negative = faster)

    # Recommendation
    recommendation: Recommendation
    confidence: str                 # "High", "Medium", "Low"
    reason: str

    # Summary
    summary: str

    # Evaluation economics
    total_eval_cost: float
    eval_overhead_pct: float        # Eval cost as % of execution cost

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/API"""
        return {
            "experiment_name": self.experiment_name,
            "baseline": {
                "version": self.baseline.version,
                "sample_size": self.baseline.sample_size,
                "avg_quality_score": self.baseline.avg_quality_score,
                "avg_cost": self.baseline.avg_cost,
                "avg_latency_ms": self.baseline.avg_latency_ms,
                "pass_rate": self.baseline.pass_rate,
            },
            "optimized": {
                "version": self.optimized.version,
                "sample_size": self.optimized.sample_size,
                "avg_quality_score": self.optimized.avg_quality_score,
                "avg_cost": self.optimized.avg_cost,
                "avg_latency_ms": self.optimized.avg_latency_ms,
                "pass_rate": self.optimized.pass_rate,
            },
            "deltas": {
                "quality_change_abs": self.quality_change_abs,
                "quality_change_pct": self.quality_change_pct,
                "cost_change_pct": self.cost_change_pct,
                "latency_change_pct": self.latency_change_pct,
            },
            "recommendation": self.recommendation.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "summary": self.summary,
            "evaluation_economics": {
                "total_eval_cost": self.total_eval_cost,
                "eval_overhead_pct": self.eval_overhead_pct,
            },
        }


class ComparisonService:
    """
    Compares baseline vs optimized experiment versions.

    Decision Logic:
    1. Quality degraded >5%: REJECT (too risky)
    2. Quality degraded 2-5%: INVESTIGATE (maybe acceptable)
    3. Quality maintained (<2% change): DEPLOY (if perf improved)
    4. Quality improved: DEPLOY (win-win)
    """

    def __init__(
        self,
        quality_reject_threshold: float = -5.0,
        quality_investigate_threshold: float = -2.0,
        significant_improvement_threshold: float = 20.0,
    ):
        """
        Initialize comparison service.

        Args:
            quality_reject_threshold: Quality drop (%) that triggers REJECT
            quality_investigate_threshold: Quality drop (%) that triggers INVESTIGATE
            significant_improvement_threshold: Cost/latency improvement (%) considered significant
        """
        self.quality_reject_threshold = quality_reject_threshold
        self.quality_investigate_threshold = quality_investigate_threshold
        self.significant_improvement_threshold = significant_improvement_threshold

    def compare(
        self,
        baseline_results: List[AggregatedResult],
        optimized_results: List[AggregatedResult],
        baseline_metrics: Dict[str, float],
        optimized_metrics: Dict[str, float],
        experiment_name: str = "experiment",
        baseline_version: str = "baseline",
        optimized_version: str = "optimized",
    ) -> ComparisonResult:
        """
        Compare baseline vs optimized versions.

        Args:
            baseline_results: Evaluation results for baseline
            optimized_results: Evaluation results for optimized
            baseline_metrics: Performance metrics {"avg_cost", "avg_latency_ms", "avg_tokens"}
            optimized_metrics: Performance metrics for optimized version
            experiment_name: Name of the experiment
            baseline_version: Version identifier for baseline
            optimized_version: Version identifier for optimized

        Returns:
            ComparisonResult with recommendation and details
        """
        # Aggregate quality metrics
        baseline_version_metrics = self._aggregate_version_metrics(
            results=baseline_results,
            performance_metrics=baseline_metrics,
            version=baseline_version,
        )

        optimized_version_metrics = self._aggregate_version_metrics(
            results=optimized_results,
            performance_metrics=optimized_metrics,
            version=optimized_version,
        )

        # Calculate deltas
        quality_change_abs = (
            optimized_version_metrics.avg_quality_score -
            baseline_version_metrics.avg_quality_score
        )
        quality_change_pct = self._pct_change(
            baseline_version_metrics.avg_quality_score,
            optimized_version_metrics.avg_quality_score,
        )
        cost_change_pct = self._pct_change(
            baseline_version_metrics.avg_cost,
            optimized_version_metrics.avg_cost,
        )
        latency_change_pct = self._pct_change(
            baseline_version_metrics.avg_latency_ms,
            optimized_version_metrics.avg_latency_ms,
        )

        # Calculate evaluation economics
        total_eval_cost = (
            baseline_version_metrics.eval_cost +
            optimized_version_metrics.eval_cost
        )
        total_execution_cost = (
            baseline_version_metrics.avg_cost * baseline_version_metrics.sample_size +
            optimized_version_metrics.avg_cost * optimized_version_metrics.sample_size
        )
        eval_overhead_pct = (
            (total_eval_cost / total_execution_cost * 100)
            if total_execution_cost > 0 else 0
        )

        # Generate recommendation
        recommendation, confidence, reason = self._generate_recommendation(
            quality_change_abs=quality_change_abs,
            quality_change_pct=quality_change_pct,
            cost_change_pct=cost_change_pct,
            latency_change_pct=latency_change_pct,
        )

        # Generate summary
        summary = self._generate_summary(
            recommendation=recommendation,
            quality_change_abs=quality_change_abs,
            quality_change_pct=quality_change_pct,
            cost_change_pct=cost_change_pct,
            latency_change_pct=latency_change_pct,
            reason=reason,
        )

        return ComparisonResult(
            experiment_name=experiment_name,
            baseline=baseline_version_metrics,
            optimized=optimized_version_metrics,
            quality_change_abs=round(quality_change_abs, 2),
            quality_change_pct=round(quality_change_pct, 2),
            cost_change_pct=round(cost_change_pct, 2),
            latency_change_pct=round(latency_change_pct, 2),
            recommendation=recommendation,
            confidence=confidence,
            reason=reason,
            summary=summary,
            total_eval_cost=round(total_eval_cost, 6),
            eval_overhead_pct=round(eval_overhead_pct, 2),
        )

    def _aggregate_version_metrics(
        self,
        results: List[AggregatedResult],
        performance_metrics: Dict[str, float],
        version: str,
    ) -> VersionMetrics:
        """Aggregate metrics for a version"""
        if not results:
            return VersionMetrics(
                version=version,
                sample_size=0,
                avg_quality_score=0,
                avg_tool_use_score=0,
                avg_model_judge_score=0,
                pass_rate=0,
                avg_cost=performance_metrics.get("avg_cost", 0),
                avg_latency_ms=performance_metrics.get("avg_latency_ms", 0),
                avg_tokens=performance_metrics.get("avg_tokens", 0),
            )

        # Extract scores by evaluator type
        overall_scores = [r.overall_score for r in results]
        tool_use_scores = []
        model_judge_scores = []
        total_eval_cost = 0.0
        total_eval_latency = 0.0

        for result in results:
            total_eval_cost += result.total_cost
            total_eval_latency += result.total_latency_ms

            for eval_result in result.results:
                if eval_result.evaluator == "tool_use":
                    tool_use_scores.append(eval_result.score)
                elif eval_result.evaluator == "model_judge":
                    model_judge_scores.append(eval_result.score)

        passed_count = sum(1 for r in results if r.passed)
        pass_rate = passed_count / len(results) if results else 0

        return VersionMetrics(
            version=version,
            sample_size=len(results),
            avg_quality_score=statistics.mean(overall_scores) if overall_scores else 0,
            avg_tool_use_score=statistics.mean(tool_use_scores) if tool_use_scores else 0,
            avg_model_judge_score=statistics.mean(model_judge_scores) if model_judge_scores else 0,
            pass_rate=pass_rate,
            avg_cost=performance_metrics.get("avg_cost", 0),
            avg_latency_ms=performance_metrics.get("avg_latency_ms", 0),
            avg_tokens=int(performance_metrics.get("avg_tokens", 0)),
            p95_latency_ms=performance_metrics.get("p95_latency_ms"),
            eval_cost=total_eval_cost,
            eval_latency_ms=total_eval_latency,
        )

    def _generate_recommendation(
        self,
        quality_change_abs: float,
        quality_change_pct: float,
        cost_change_pct: float,
        latency_change_pct: float,
    ) -> tuple:
        """Generate deployment recommendation"""

        # Rule 1: Quality degraded significantly → REJECT
        if quality_change_abs < self.quality_reject_threshold:
            return (
                Recommendation.REJECT,
                "High",
                f"Quality degraded significantly ({quality_change_abs:+.1f} points). Not acceptable.",
            )

        # Rule 2: Quality degraded moderately → INVESTIGATE
        if quality_change_abs < self.quality_investigate_threshold:
            return (
                Recommendation.INVESTIGATE,
                "Medium",
                f"Quality degraded moderately ({quality_change_abs:+.1f} points). Review trade-offs.",
            )

        # Rule 3: Quality maintained + significant performance improvement → DEPLOY
        significant_cost_improvement = cost_change_pct < -self.significant_improvement_threshold
        significant_latency_improvement = latency_change_pct < -self.significant_improvement_threshold

        if significant_cost_improvement or significant_latency_improvement:
            improvements = []
            if significant_cost_improvement:
                improvements.append(f"cost {cost_change_pct:+.1f}%")
            if significant_latency_improvement:
                improvements.append(f"latency {latency_change_pct:+.1f}%")

            return (
                Recommendation.DEPLOY,
                "High",
                f"Quality maintained ({quality_change_abs:+.1f}), performance improved significantly ({', '.join(improvements)}).",
            )

        # Rule 4: Quality improved → DEPLOY
        if quality_change_abs > 2.0:
            return (
                Recommendation.DEPLOY,
                "High",
                f"Quality improved ({quality_change_abs:+.1f} points). Deploy immediately.",
            )

        # Rule 5: No significant changes → NEUTRAL
        return (
            Recommendation.NEUTRAL,
            "Medium",
            "No significant changes detected. Optional deployment.",
        )

    def _generate_summary(
        self,
        recommendation: Recommendation,
        quality_change_abs: float,
        quality_change_pct: float,
        cost_change_pct: float,
        latency_change_pct: float,
        reason: str,
    ) -> str:
        """Generate human-readable summary"""
        emoji = {
            Recommendation.DEPLOY: "✅",
            Recommendation.INVESTIGATE: "⚠️",
            Recommendation.REJECT: "❌",
            Recommendation.NEUTRAL: "ℹ️",
        }

        return f"""{emoji[recommendation]} RECOMMENDATION: {recommendation.value}

Quality Impact: {quality_change_abs:+.1f} points ({quality_change_pct:+.1f}%)
Performance Impact:
  - Cost: {cost_change_pct:+.1f}%
  - Latency: {latency_change_pct:+.1f}%

{reason}"""

    def _pct_change(self, baseline: float, optimized: float) -> float:
        """Calculate percentage change"""
        if baseline == 0:
            return 0.0
        return ((optimized - baseline) / baseline) * 100

    def format_report(self, result: ComparisonResult) -> str:
        """Format comparison result as detailed report"""
        return f"""
{'='*60}
OPTIMIZATION COMPARISON REPORT
{'='*60}

Experiment: {result.experiment_name}

BASELINE ({result.baseline.version})
  Sample Size:    {result.baseline.sample_size}
  Quality Score:  {result.baseline.avg_quality_score:.1f}/100
  Tool Use:       {result.baseline.avg_tool_use_score:.1f}/100
  Model Judge:    {result.baseline.avg_model_judge_score:.1f}/100
  Pass Rate:      {result.baseline.pass_rate*100:.1f}%
  Cost:           ${result.baseline.avg_cost:.4f}/request
  Latency:        {result.baseline.avg_latency_ms:.0f}ms

OPTIMIZED ({result.optimized.version})
  Sample Size:    {result.optimized.sample_size}
  Quality Score:  {result.optimized.avg_quality_score:.1f}/100 ({result.quality_change_pct:+.1f}%)
  Tool Use:       {result.optimized.avg_tool_use_score:.1f}/100
  Model Judge:    {result.optimized.avg_model_judge_score:.1f}/100
  Pass Rate:      {result.optimized.pass_rate*100:.1f}%
  Cost:           ${result.optimized.avg_cost:.4f}/request ({result.cost_change_pct:+.1f}%)
  Latency:        {result.optimized.avg_latency_ms:.0f}ms ({result.latency_change_pct:+.1f}%)

EVALUATION ECONOMICS
  Total Eval Cost:    ${result.total_eval_cost:.4f}
  Eval Overhead:      {result.eval_overhead_pct:.2f}%

{'='*60}
{result.summary}
{'='*60}
"""
