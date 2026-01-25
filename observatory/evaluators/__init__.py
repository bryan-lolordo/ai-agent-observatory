"""
Observatory Evaluators - V2 Evaluation System
==============================================

Multi-tier evaluation for optimization validation.

Tier 1: Free Evaluators (run on every call)
  - ToolUseEvaluator: AST-based function call validation

Tier 2: Cheap LLM Evaluators (run on test suites)
  - ModelJudgeEvaluator: Haiku-based semantic evaluation

Integration with existing LLMJudge:
  - LLMJudge (judge.py): Production quality monitoring (gpt-4o, sampling)
  - V2 Evaluators: Optimization validation (test suites, comparison)

Usage:
    from observatory.evaluators import ToolUseEvaluator, ModelJudgeEvaluator

    # Free evaluation
    tool_eval = ToolUseEvaluator()
    result = tool_eval.evaluate(trace, expected)

    # Cheap semantic evaluation
    model_eval = ModelJudgeEvaluator()
    result = await model_eval.evaluate(trace, expected)
"""

from observatory.evaluators.base import BaseEvaluator, EvaluationResult
from observatory.evaluators.tool_use import ToolUseEvaluator
from observatory.evaluators.model_judge import ModelJudgeEvaluator

__all__ = [
    'BaseEvaluator',
    'EvaluationResult',
    'ToolUseEvaluator',
    'ModelJudgeEvaluator',
]
