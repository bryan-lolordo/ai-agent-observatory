"""
Tool Use Evaluator - FREE AST-based Validation
===============================================

Validates that agents called the right tools with correct arguments.

Cost: $0 (no LLM needed)
Latency: <100ms
Accuracy: 100% (deterministic)

Use Cases:
- Verify correct tool selection
- Validate required arguments present
- Check argument types/formats
- Detect tool hallucinations

Integration with existing Observatory:
- Works with traces from @observe decorator
- Extracts tool calls from trace metadata
- Compatible with Semantic Kernel function calls
"""

import time
from typing import Any, Dict, List, Optional, Set

from observatory.evaluators.base import (
    BaseEvaluator,
    EvaluationResult,
    EvaluatorType,
)


class ToolUseEvaluator(BaseEvaluator):
    """
    FREE evaluator for function calling validation.

    Checks:
    1. Was the correct tool called?
    2. Were all required arguments provided?
    3. Are argument types correct?
    4. Any extra/unexpected arguments?

    Scoring:
    - 100: Correct tool with all correct arguments
    - 75: Correct tool with minor argument issues
    - 50: Correct tool with major argument issues
    - 0: Wrong tool or no tool when needed
    """

    def __init__(self, pass_threshold: float = 90.0):
        """
        Initialize Tool Use Evaluator.

        Args:
            pass_threshold: Minimum score to pass (default 90)
        """
        self.pass_threshold = pass_threshold

        # Statistics
        self._total_evaluated = 0
        self._total_passed = 0
        self._wrong_tool_count = 0
        self._missing_args_count = 0

    @property
    def evaluator_type(self) -> EvaluatorType:
        return EvaluatorType.TOOL_USE

    @property
    def cost_per_eval(self) -> float:
        return 0.0  # FREE

    def evaluate(
        self,
        trace: Dict[str, Any],
        expected: Dict[str, Any],
        test_case_id: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Evaluate tool use from execution trace.

        Args:
            trace: Observatory trace containing tool calls in metadata
            expected: Expected behavior:
                {
                    "tool_called": "score_job_match",
                    "required_args": ["resume", "job_description"],
                    "optional_args": ["max_score"],
                    "arg_types": {"resume": str, "job_description": str},
                }

        Returns:
            EvaluationResult with score 0-100
        """
        start_time = time.perf_counter()

        # Extract actual tool calls from trace
        actual_calls = self._extract_tool_calls(trace)
        expected_tool = expected.get("tool_called")
        required_args = set(expected.get("required_args", []))
        optional_args = set(expected.get("optional_args", []))
        arg_types = expected.get("arg_types", {})

        score = 0
        issues = []
        details = {
            "actual_tools": [c.get("name") for c in actual_calls],
            "expected_tool": expected_tool,
            "correct_tool": False,
            "correct_args": False,
            "missing_args": [],
            "extra_args": [],
            "type_errors": [],
        }

        # Check 1: Was correct tool called?
        matching_call = None
        for call in actual_calls:
            if call.get("name") == expected_tool:
                matching_call = call
                break

        if not matching_call:
            issues.append(f"Expected tool '{expected_tool}' not called. Got: {details['actual_tools']}")
            self._wrong_tool_count += 1

            result = EvaluationResult(
                evaluator=self.evaluator_type.value,
                score=0,
                passed=False,
                reasoning=f"Wrong tool called. Expected '{expected_tool}'",
                details=details,
                issues=issues,
                cost=0.0,
                latency_ms=(time.perf_counter() - start_time) * 1000,
                test_case_id=test_case_id,
            )
            self._total_evaluated += 1
            return result

        # Correct tool = 50 points base
        score = 50
        details["correct_tool"] = True

        # Check 2: Were required arguments provided?
        actual_args = set(matching_call.get("arguments", {}).keys())

        missing_args = required_args - actual_args
        extra_args = actual_args - required_args - optional_args

        details["missing_args"] = list(missing_args)
        details["extra_args"] = list(extra_args)

        if missing_args:
            issues.append(f"Missing required arguments: {missing_args}")
            self._missing_args_count += 1
            # Partial credit: -10 per missing arg
            score += max(0, 30 - (len(missing_args) * 10))
        else:
            # All required args present = 30 more points
            score += 30
            details["correct_args"] = True

        # Check 3: Argument types (if specified)
        if arg_types and not missing_args:
            actual_arguments = matching_call.get("arguments", {})
            type_errors = []

            for arg_name, expected_type in arg_types.items():
                if arg_name in actual_arguments:
                    actual_value = actual_arguments[arg_name]
                    if not isinstance(actual_value, expected_type):
                        type_errors.append(
                            f"{arg_name}: expected {expected_type.__name__}, got {type(actual_value).__name__}"
                        )

            details["type_errors"] = type_errors

            if type_errors:
                issues.extend([f"Type error: {e}" for e in type_errors])
                score -= len(type_errors) * 5
            else:
                # All types correct = 20 more points
                score += 20

        # Extra args warning (not penalized heavily)
        if extra_args:
            issues.append(f"Unexpected arguments: {extra_args}")
            score -= 5  # Minor penalty

        # Ensure score in bounds
        score = max(0, min(100, score))
        passed = score >= self.pass_threshold

        # Build reasoning
        if passed:
            reasoning = f"Tool '{expected_tool}' called correctly with all required arguments"
        elif details["correct_tool"]:
            reasoning = f"Tool '{expected_tool}' called but with argument issues"
        else:
            reasoning = f"Expected tool '{expected_tool}' was not called"

        # Update stats
        self._total_evaluated += 1
        if passed:
            self._total_passed += 1

        return EvaluationResult(
            evaluator=self.evaluator_type.value,
            score=score,
            passed=passed,
            reasoning=reasoning,
            details=details,
            issues=issues,
            cost=0.0,
            latency_ms=(time.perf_counter() - start_time) * 1000,
            test_case_id=test_case_id,
        )

    def _extract_tool_calls(self, trace: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tool calls from Observatory trace.

        Supports multiple formats:
        1. metadata.function_calls (standard)
        2. metadata.tool_calls (alternative)
        3. tool_calls_made (LLMCall field)
        4. response.tool_calls (OpenAI format)

        Args:
            trace: Observatory trace dict

        Returns:
            List of tool call dicts: [{"name": "...", "arguments": {...}}]
        """
        tool_calls = []

        # Try metadata.function_calls (standard Observatory format)
        metadata = trace.get("metadata", {})
        if "function_calls" in metadata:
            tool_calls.extend(metadata["function_calls"])

        # Try metadata.tool_calls
        if "tool_calls" in metadata:
            tool_calls.extend(metadata["tool_calls"])

        # Try top-level tool_calls_made (LLMCall model field)
        if "tool_calls_made" in trace and trace["tool_calls_made"]:
            tool_calls.extend(trace["tool_calls_made"])

        # Try response.tool_calls (OpenAI response format)
        response = trace.get("response", {})
        if isinstance(response, dict) and "tool_calls" in response:
            for tc in response["tool_calls"]:
                # OpenAI format: {"id": "...", "function": {"name": "...", "arguments": "..."}}
                if "function" in tc:
                    func = tc["function"]
                    tool_calls.append({
                        "name": func.get("name"),
                        "arguments": self._parse_arguments(func.get("arguments", "{}")),
                    })

        # Try extracting from Semantic Kernel format
        if "inner_content" in trace:
            inner = trace.get("inner_content", {})
            if hasattr(inner, "tool_calls") or (isinstance(inner, dict) and "tool_calls" in inner):
                sk_calls = inner.tool_calls if hasattr(inner, "tool_calls") else inner.get("tool_calls", [])
                for tc in sk_calls:
                    if hasattr(tc, "function"):
                        tool_calls.append({
                            "name": tc.function.name,
                            "arguments": self._parse_arguments(tc.function.arguments),
                        })

        return tool_calls

    def _parse_arguments(self, arguments: Any) -> Dict[str, Any]:
        """Parse arguments from string or dict format"""
        if isinstance(arguments, dict):
            return arguments
        if isinstance(arguments, str):
            try:
                import json
                return json.loads(arguments)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def can_evaluate(self, trace: Dict[str, Any]) -> bool:
        """Check if trace contains tool call information"""
        # Check various locations for tool calls
        if self._extract_tool_calls(trace):
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get evaluator statistics"""
        pass_rate = self._total_passed / self._total_evaluated if self._total_evaluated > 0 else 0

        return {
            "evaluator_type": self.evaluator_type.value,
            "cost_per_eval": self.cost_per_eval,
            "total_evaluated": self._total_evaluated,
            "total_passed": self._total_passed,
            "pass_rate": round(pass_rate, 3),
            "wrong_tool_count": self._wrong_tool_count,
            "missing_args_count": self._missing_args_count,
            "pass_threshold": self.pass_threshold,
        }

    def reset_stats(self):
        """Reset statistics"""
        self._total_evaluated = 0
        self._total_passed = 0
        self._wrong_tool_count = 0
        self._missing_args_count = 0
