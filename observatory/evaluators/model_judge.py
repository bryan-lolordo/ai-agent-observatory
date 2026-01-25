"""
Model Judge Evaluator - Cheap Semantic Evaluation
=================================================

Uses Claude Haiku for semantic quality evaluation.
10x cheaper than existing LLMJudge (gpt-4o).

Cost: ~$0.0003 per evaluation
Latency: ~1-2 seconds
Accuracy: ~90-95% vs human judgment

Use Cases:
- Evaluate reasoning quality
- Check output correctness vs ground truth
- Validate semantic alignment
- Detect hallucinations

Comparison with existing LLMJudge:
- LLMJudge: gpt-4o, ~$0.002/eval, production sampling
- ModelJudgeEvaluator: Haiku, ~$0.0003/eval, test suite validation
"""

import json
import os
import time
from typing import Any, Dict, Optional

from observatory.evaluators.base import (
    BaseEvaluator,
    EvaluationResult,
    EvaluatorType,
)


class ModelJudgeEvaluator(BaseEvaluator):
    """
    Cheap semantic evaluator using Claude Haiku.

    Evaluates:
    1. Output correctness vs ground truth
    2. Score reasonableness (for scoring tasks)
    3. Reasoning quality
    4. Key point coverage

    Scoring:
    - 90-100: Excellent - matches ground truth, good reasoning
    - 75-89: Good - mostly correct, minor issues
    - 50-74: Acceptable - some issues but usable
    - 25-49: Poor - significant problems
    - 0-24: Failed - incorrect or unusable
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-haiku-3-5-20241022",
        pass_threshold: float = 75.0,
        max_input_chars: int = 1000,
        max_output_chars: int = 1500,
    ):
        """
        Initialize Model Judge Evaluator.

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
            model: Model to use for evaluation (default: Haiku 3.5)
            pass_threshold: Minimum score to pass (default 75)
            max_input_chars: Max chars of input to send to judge
            max_output_chars: Max chars of output to send to judge
        """
        self._api_key = api_key
        self.model = model
        self.pass_threshold = pass_threshold
        self.max_input_chars = max_input_chars
        self.max_output_chars = max_output_chars

        # Lazy-initialized client
        self._client = None

        # Statistics
        self._total_evaluated = 0
        self._total_passed = 0
        self._total_cost = 0.0
        self._total_latency_ms = 0.0

    @property
    def evaluator_type(self) -> EvaluatorType:
        return EvaluatorType.MODEL_JUDGE

    @property
    def cost_per_eval(self) -> float:
        return 0.0003  # ~$0.0003 per evaluation with Haiku

    def _get_client(self):
        """Get or create Anthropic client"""
        if self._client is not None:
            return self._client

        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            )

        api_key = self._api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "No Anthropic API key found. Set ANTHROPIC_API_KEY or pass api_key parameter."
            )

        self._client = Anthropic(api_key=api_key)
        return self._client

    def evaluate(
        self,
        trace: Dict[str, Any],
        expected: Dict[str, Any],
        test_case_id: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Synchronous evaluation (calls async internally).

        For async usage, use evaluate_async() directly.
        """
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            # Already in async context
            return loop.run_until_complete(
                self.evaluate_async(trace, expected, test_case_id)
            )
        except RuntimeError:
            # No event loop
            return asyncio.run(
                self.evaluate_async(trace, expected, test_case_id)
            )

    async def evaluate_async(
        self,
        trace: Dict[str, Any],
        expected: Dict[str, Any],
        test_case_id: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Evaluate output quality using Haiku as judge.

        Args:
            trace: Observatory trace containing input/output
            expected: Expected behavior and ground truth:
                {
                    "evaluation_criteria": "Evaluate if the score is reasonable...",
                    "ground_truth": {
                        "ideal_score_range": [75, 95],
                        "key_points": ["Python", "ML experience"],
                    },
                    "score_range": [0, 100],  # Expected score range for outputs
                }

        Returns:
            EvaluationResult with score 0-100
        """
        start_time = time.perf_counter()

        try:
            # Build evaluation prompt
            prompt = self._build_prompt(trace, expected)

            # Call Haiku
            client = self._get_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.0,  # Deterministic
                messages=[{"role": "user", "content": prompt}],
            )

            result_text = response.content[0].text.strip()
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Calculate cost
            cost = self._calculate_cost(response.usage)

            # Parse response
            parsed = self._parse_response(result_text)

            # Update stats
            self._total_evaluated += 1
            self._total_cost += cost
            self._total_latency_ms += latency_ms

            passed = parsed["score"] >= self.pass_threshold
            if passed:
                self._total_passed += 1

            return EvaluationResult(
                evaluator=self.evaluator_type.value,
                score=parsed["score"],
                passed=passed,
                reasoning=parsed["reasoning"],
                details={
                    "strengths": parsed.get("strengths", []),
                    "weaknesses": parsed.get("weaknesses", []),
                    "ground_truth_alignment": parsed.get("alignment", "unknown"),
                },
                issues=parsed.get("weaknesses", []),
                cost=cost,
                latency_ms=latency_ms,
                test_case_id=test_case_id,
                confidence=parsed.get("confidence"),
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000

            return EvaluationResult(
                evaluator=self.evaluator_type.value,
                score=0,
                passed=False,
                reasoning=f"Evaluation failed: {str(e)}",
                details={"error": str(e)},
                issues=[f"Evaluation error: {str(e)}"],
                cost=0.0,
                latency_ms=latency_ms,
                test_case_id=test_case_id,
            )

    def _build_prompt(self, trace: Dict[str, Any], expected: Dict[str, Any]) -> str:
        """Build evaluation prompt for Haiku"""
        # Extract input/output from trace
        input_data = trace.get("request", trace.get("input", {}))
        output_data = trace.get("response", trace.get("output", {}))

        # Handle different trace formats
        if isinstance(input_data, dict):
            input_preview = json.dumps(input_data, indent=2)[:self.max_input_chars]
        else:
            input_preview = str(input_data)[:self.max_input_chars]

        if isinstance(output_data, dict):
            output_preview = json.dumps(output_data, indent=2)[:self.max_output_chars]
        else:
            output_preview = str(output_data)[:self.max_output_chars]

        # Get evaluation criteria and ground truth
        criteria = expected.get(
            "evaluation_criteria",
            "Evaluate the quality and correctness of the AI agent's output."
        )
        ground_truth = expected.get("ground_truth", {})

        prompt = f"""You are evaluating the quality of an AI agent's output.

EVALUATION CRITERIA:
{criteria}

INPUT TO AGENT:
{input_preview}

AGENT'S OUTPUT:
{output_preview}

GROUND TRUTH (Reference):
{json.dumps(ground_truth, indent=2) if ground_truth else "No ground truth provided - evaluate based on general quality."}

Your task:
1. Evaluate the quality of the agent's output on a scale of 0-100
2. Provide brief reasoning (2-3 sentences)
3. List key strengths (if any)
4. List key weaknesses (if any)
5. Rate your confidence in this evaluation (0.0-1.0)

Scoring Guidelines:
- 90-100: Excellent - highly accurate, matches ground truth, comprehensive
- 75-89: Good - mostly accurate, minor issues
- 50-74: Acceptable - significant issues but usable
- 25-49: Poor - major problems
- 0-24: Failed - incorrect or unusable

Respond in this EXACT format:
SCORE: <number 0-100>
REASONING: <2-3 sentence explanation>
STRENGTHS: <comma-separated list or "None">
WEAKNESSES: <comma-separated list or "None">
ALIGNMENT: <"matches", "partial", "differs", or "no_ground_truth">
CONFIDENCE: <0.0-1.0>

Be objective and concise."""

        return prompt

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Haiku's response into structured format"""
        result = {
            "score": 0,
            "reasoning": "",
            "strengths": [],
            "weaknesses": [],
            "alignment": "unknown",
            "confidence": 0.5,
        }

        lines = response_text.strip().split('\n')

        for line in lines:
            line = line.strip()

            if line.startswith("SCORE:"):
                score_str = line.replace("SCORE:", "").strip()
                try:
                    score = float(score_str)
                    # Ensure 0-100 range
                    result["score"] = max(0, min(100, score))
                except ValueError:
                    result["score"] = 0

            elif line.startswith("REASONING:"):
                result["reasoning"] = line.replace("REASONING:", "").strip()

            elif line.startswith("STRENGTHS:"):
                strengths_str = line.replace("STRENGTHS:", "").strip()
                if strengths_str.lower() != "none":
                    result["strengths"] = [s.strip() for s in strengths_str.split(',') if s.strip()]

            elif line.startswith("WEAKNESSES:"):
                weaknesses_str = line.replace("WEAKNESSES:", "").strip()
                if weaknesses_str.lower() != "none":
                    result["weaknesses"] = [w.strip() for w in weaknesses_str.split(',') if w.strip()]

            elif line.startswith("ALIGNMENT:"):
                result["alignment"] = line.replace("ALIGNMENT:", "").strip().lower()

            elif line.startswith("CONFIDENCE:"):
                conf_str = line.replace("CONFIDENCE:", "").strip()
                try:
                    result["confidence"] = max(0.0, min(1.0, float(conf_str)))
                except ValueError:
                    result["confidence"] = 0.5

        return result

    def _calculate_cost(self, usage) -> float:
        """
        Calculate cost based on Haiku pricing.

        Haiku 3.5 pricing (as of Jan 2026):
        - Input: $0.80 per million tokens
        - Output: $4.00 per million tokens
        """
        input_tokens = getattr(usage, 'input_tokens', 0)
        output_tokens = getattr(usage, 'output_tokens', 0)

        input_cost = (input_tokens / 1_000_000) * 0.80
        output_cost = (output_tokens / 1_000_000) * 4.00

        return round(input_cost + output_cost, 6)

    def get_stats(self) -> Dict[str, Any]:
        """Get evaluator statistics"""
        pass_rate = self._total_passed / self._total_evaluated if self._total_evaluated > 0 else 0
        avg_latency = self._total_latency_ms / self._total_evaluated if self._total_evaluated > 0 else 0
        avg_cost = self._total_cost / self._total_evaluated if self._total_evaluated > 0 else 0

        return {
            "evaluator_type": self.evaluator_type.value,
            "model": self.model,
            "cost_per_eval": self.cost_per_eval,
            "total_evaluated": self._total_evaluated,
            "total_passed": self._total_passed,
            "pass_rate": round(pass_rate, 3),
            "total_cost_usd": round(self._total_cost, 6),
            "avg_cost_per_eval": round(avg_cost, 6),
            "avg_latency_ms": round(avg_latency, 1),
            "pass_threshold": self.pass_threshold,
        }

    def reset_stats(self):
        """Reset statistics"""
        self._total_evaluated = 0
        self._total_passed = 0
        self._total_cost = 0.0
        self._total_latency_ms = 0.0
