"""
Evaluation Pipeline - Orchestrates Multiple Evaluators
======================================================

Coordinates running multiple evaluators on traces, aggregates results,
and integrates with the existing LLMJudge for production monitoring.

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │                  EvaluationPipeline                      │
    │                                                          │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
    │  │ToolUse   │  │Model     │  │LLMJudge  │  │Custom   │ │
    │  │Evaluator │  │Judge     │  │(existing)│  │Evaluator│ │
    │  │(FREE)    │  │(Haiku)   │  │(gpt-4o)  │  │         │ │
    │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
    │       │             │             │             │       │
    │       └─────────────┴─────────────┴─────────────┘       │
    │                         │                                │
    │                    Aggregate                             │
    │                         │                                │
    │              ┌──────────┴──────────┐                    │
    │              │ AggregatedResult    │                    │
    │              │ • overall_score     │                    │
    │              │ • all_results       │                    │
    │              │ • passed            │                    │
    │              └─────────────────────┘                    │
    └─────────────────────────────────────────────────────────┘
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from observatory.evaluators.base import BaseEvaluator, EvaluationResult, EvaluatorType
from observatory.evaluators.tool_use import ToolUseEvaluator
from observatory.evaluators.model_judge import ModelJudgeEvaluator

if TYPE_CHECKING:
    from observatory.judge import LLMJudge


@dataclass
class AggregatedResult:
    """
    Aggregated results from all evaluators.

    Combines scores from multiple evaluators into a single assessment.
    """
    # Overall assessment
    overall_score: float            # Weighted average 0-100
    passed: bool                    # Did all required evaluators pass?

    # Individual results
    results: List[EvaluationResult] = field(default_factory=list)

    # Summary
    total_evaluators: int = 0
    passed_count: int = 0
    failed_count: int = 0

    # Cost tracking
    total_cost: float = 0.0
    total_latency_ms: float = 0.0

    # Linking
    trace_id: Optional[str] = None
    test_case_id: Optional[str] = None
    experiment_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "overall_score": self.overall_score,
            "passed": self.passed,
            "results": [r.to_dict() for r in self.results],
            "total_evaluators": self.total_evaluators,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "total_cost": self.total_cost,
            "total_latency_ms": self.total_latency_ms,
            "trace_id": self.trace_id,
            "test_case_id": self.test_case_id,
            "experiment_version": self.experiment_version,
        }


class EvaluationPipeline:
    """
    Orchestrates multiple evaluators for comprehensive quality assessment.

    Modes:
    1. Test Mode: Run all evaluators for validation (test suites)
    2. Production Mode: Run free evaluators + sampling for LLM judge

    Integration with existing LLMJudge:
    - Can include LLMJudge as an evaluator for production monitoring
    - Adapts LLMJudge's 0-10 scores to 0-100 scale
    - Respects LLMJudge's sampling configuration

    Usage:
        pipeline = EvaluationPipeline()
        pipeline.add_evaluator(ToolUseEvaluator())
        pipeline.add_evaluator(ModelJudgeEvaluator())

        # Optional: Include existing LLMJudge
        pipeline.set_llm_judge(my_judge)

        result = await pipeline.evaluate(trace, expected)
    """

    def __init__(
        self,
        evaluator_weights: Optional[Dict[str, float]] = None,
        require_all_pass: bool = False,
        skip_on_first_failure: bool = False,
    ):
        """
        Initialize evaluation pipeline.

        Args:
            evaluator_weights: Weight for each evaluator type in overall score
                Default: {"tool_use": 0.4, "model_judge": 0.6}
            require_all_pass: If True, overall pass requires all evaluators to pass
            skip_on_first_failure: If True, stop evaluating after first failure
        """
        self._evaluators: List[BaseEvaluator] = []
        self._llm_judge: Optional['LLMJudge'] = None

        self.evaluator_weights = evaluator_weights or {
            EvaluatorType.TOOL_USE.value: 0.4,
            EvaluatorType.MODEL_JUDGE.value: 0.6,
            EvaluatorType.LLM_JUDGE.value: 0.0,  # Optional, not in default weight
        }

        self.require_all_pass = require_all_pass
        self.skip_on_first_failure = skip_on_first_failure

        # Statistics
        self._total_evaluations = 0
        self._total_cost = 0.0

    def add_evaluator(self, evaluator: BaseEvaluator) -> 'EvaluationPipeline':
        """Add an evaluator to the pipeline"""
        self._evaluators.append(evaluator)
        return self

    def remove_evaluator(self, evaluator_type: EvaluatorType) -> 'EvaluationPipeline':
        """Remove evaluator by type"""
        self._evaluators = [e for e in self._evaluators if e.evaluator_type != evaluator_type]
        return self

    def set_llm_judge(self, judge: 'LLMJudge') -> 'EvaluationPipeline':
        """
        Set existing LLMJudge for integration.

        The LLMJudge will be called with its own sampling logic.
        Results are converted from 0-10 to 0-100 scale.
        """
        self._llm_judge = judge
        return self

    def set_weights(self, weights: Dict[str, float]) -> 'EvaluationPipeline':
        """Set evaluator weights for overall score calculation"""
        self.evaluator_weights = weights
        return self

    async def evaluate(
        self,
        trace: Dict[str, Any],
        expected: Dict[str, Any],
        test_case_id: Optional[str] = None,
        experiment_version: Optional[str] = None,
        include_llm_judge: bool = False,
    ) -> AggregatedResult:
        """
        Run all evaluators on a trace.

        Args:
            trace: Observatory trace containing request/response/metadata
            expected: Expected behavior from test case
            test_case_id: Optional test case ID for linking
            experiment_version: Optional experiment version (e.g., "v1_baseline")
            include_llm_judge: If True and LLMJudge is set, include it

        Returns:
            AggregatedResult with overall score and individual results
        """
        results: List[EvaluationResult] = []
        total_cost = 0.0
        total_latency = 0.0

        # Run V2 evaluators
        for evaluator in self._evaluators:
            if not evaluator.can_evaluate(trace):
                continue

            try:
                # Check if evaluator has async method
                if hasattr(evaluator, 'evaluate_async'):
                    result = await evaluator.evaluate_async(trace, expected, test_case_id)
                else:
                    result = evaluator.evaluate(trace, expected, test_case_id)

                if result:
                    results.append(result)
                    total_cost += result.cost
                    total_latency += result.latency_ms

                    # Early exit on failure if configured
                    if self.skip_on_first_failure and not result.passed:
                        break

            except Exception as e:
                # Record failure but continue
                results.append(EvaluationResult(
                    evaluator=evaluator.evaluator_type.value,
                    score=0,
                    passed=False,
                    reasoning=f"Evaluator error: {str(e)}",
                    issues=[str(e)],
                ))

        # Run LLMJudge if requested
        if include_llm_judge and self._llm_judge:
            try:
                # Extract prompt and response for LLMJudge
                prompt = trace.get("prompt", trace.get("request", {}).get("prompt", ""))
                response = trace.get("response_text", trace.get("response", ""))

                if isinstance(prompt, dict):
                    prompt = str(prompt)
                if isinstance(response, dict):
                    response = str(response)

                operation = trace.get("operation", "evaluate")

                # LLMJudge has its own sampling
                quality_eval = await self._llm_judge.evaluate_async(
                    operation=operation,
                    prompt=prompt,
                    response=response,
                )

                if quality_eval:
                    # Convert 0-10 to 0-100
                    score_100 = (quality_eval.judge_score or 0) * 10

                    results.append(EvaluationResult(
                        evaluator=EvaluatorType.LLM_JUDGE.value,
                        score=score_100,
                        passed=score_100 >= 70,  # 7/10 = 70/100
                        reasoning=quality_eval.reasoning or "",
                        details={
                            "judge_model": quality_eval.judge_model,
                            "hallucination": quality_eval.hallucination_flag,
                            "criteria_scores": quality_eval.criteria_scores,
                        },
                        issues=([quality_eval.hallucination_details] if quality_eval.hallucination_flag else []),
                        confidence=quality_eval.confidence_score,
                    ))

            except Exception as e:
                # LLMJudge failure is not fatal
                pass

        # Calculate overall score
        overall_score = self._calculate_overall_score(results)

        # Determine pass/fail
        passed_count = sum(1 for r in results if r.passed)
        failed_count = len(results) - passed_count

        if self.require_all_pass:
            overall_passed = failed_count == 0 and len(results) > 0
        else:
            overall_passed = overall_score >= 75  # Default threshold

        # Update stats
        self._total_evaluations += 1
        self._total_cost += total_cost

        return AggregatedResult(
            overall_score=overall_score,
            passed=overall_passed,
            results=results,
            total_evaluators=len(results),
            passed_count=passed_count,
            failed_count=failed_count,
            total_cost=total_cost,
            total_latency_ms=total_latency,
            trace_id=trace.get("id"),
            test_case_id=test_case_id,
            experiment_version=experiment_version,
        )

    def _calculate_overall_score(self, results: List[EvaluationResult]) -> float:
        """Calculate weighted overall score"""
        if not results:
            return 0.0

        weighted_sum = 0.0
        weight_sum = 0.0

        for result in results:
            weight = self.evaluator_weights.get(result.evaluator, 0.5)
            weighted_sum += result.score * weight
            weight_sum += weight

        if weight_sum == 0:
            return sum(r.score for r in results) / len(results)

        return round(weighted_sum / weight_sum, 1)

    async def evaluate_batch(
        self,
        traces: List[Dict[str, Any]],
        expected_list: List[Dict[str, Any]],
        experiment_version: Optional[str] = None,
    ) -> List[AggregatedResult]:
        """
        Evaluate multiple traces concurrently.

        Args:
            traces: List of traces to evaluate
            expected_list: List of expected behaviors (parallel to traces)
            experiment_version: Version identifier for all traces

        Returns:
            List of AggregatedResults
        """
        tasks = [
            self.evaluate(
                trace=trace,
                expected=expected,
                test_case_id=expected.get("id"),
                experiment_version=experiment_version,
            )
            for trace, expected in zip(traces, expected_list)
        ]

        return await asyncio.gather(*tasks)

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        evaluator_stats = {e.evaluator_type.value: e.get_stats() for e in self._evaluators}

        return {
            "total_evaluations": self._total_evaluations,
            "total_cost_usd": round(self._total_cost, 6),
            "evaluator_weights": self.evaluator_weights,
            "require_all_pass": self.require_all_pass,
            "evaluator_stats": evaluator_stats,
            "has_llm_judge": self._llm_judge is not None,
        }

    @classmethod
    def create_default(cls) -> 'EvaluationPipeline':
        """
        Create pipeline with default evaluators.

        Includes:
        - ToolUseEvaluator (FREE)
        - ModelJudgeEvaluator (Haiku)
        """
        pipeline = cls()
        pipeline.add_evaluator(ToolUseEvaluator())
        pipeline.add_evaluator(ModelJudgeEvaluator())
        return pipeline

    @classmethod
    def create_free_only(cls) -> 'EvaluationPipeline':
        """
        Create pipeline with only free evaluators.

        Useful for rapid iteration without LLM costs.
        """
        pipeline = cls()
        pipeline.add_evaluator(ToolUseEvaluator())
        return pipeline
