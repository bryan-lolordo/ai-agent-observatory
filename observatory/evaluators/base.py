"""
Base Evaluator Interface
========================

All V2 evaluators inherit from this base class.
Provides consistent interface for the EvaluationPipeline.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class EvaluatorType(str, Enum):
    """Types of evaluators"""
    TOOL_USE = "tool_use"           # Free, AST-based
    MODEL_JUDGE = "model_judge"     # Haiku-based ($0.0003)
    LLM_JUDGE = "llm_judge"         # Existing gpt-4o judge (production)
    SCHEMA = "schema"               # JSON schema validation (free)
    RANGE = "range"                 # Score range validation (free)


@dataclass
class EvaluationResult:
    """
    Standardized result from any evaluator.

    Designed to be compatible with existing QualityEvaluation model
    but with additional fields for V2 features.
    """
    # Core fields
    evaluator: str                      # "tool_use", "model_judge", etc.
    score: float                        # 0-100 scale (V2 uses 0-100, existing uses 0-10)
    passed: bool                        # Did it meet threshold?

    # Details
    reasoning: str = ""                 # Explanation
    details: Dict[str, Any] = field(default_factory=dict)  # Evaluator-specific details

    # Issues found
    issues: List[str] = field(default_factory=list)

    # Cost tracking
    cost: float = 0.0                   # $ cost of this evaluation
    latency_ms: float = 0.0             # Time taken

    # Linking
    trace_id: Optional[str] = None
    test_case_id: Optional[str] = None

    # Confidence (for model-based evaluators)
    confidence: Optional[float] = None  # 0.0-1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/API"""
        return {
            "evaluator": self.evaluator,
            "score": self.score,
            "passed": self.passed,
            "reasoning": self.reasoning,
            "details": self.details,
            "issues": self.issues,
            "cost": self.cost,
            "latency_ms": self.latency_ms,
            "trace_id": self.trace_id,
            "test_case_id": self.test_case_id,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvaluationResult':
        """Create from dictionary"""
        return cls(
            evaluator=data.get("evaluator", "unknown"),
            score=data.get("score", 0),
            passed=data.get("passed", False),
            reasoning=data.get("reasoning", ""),
            details=data.get("details", {}),
            issues=data.get("issues", []),
            cost=data.get("cost", 0.0),
            latency_ms=data.get("latency_ms", 0.0),
            trace_id=data.get("trace_id"),
            test_case_id=data.get("test_case_id"),
            confidence=data.get("confidence"),
        )

    def to_quality_score(self) -> float:
        """Convert 0-100 score to 0-10 for compatibility with QualityEvaluation"""
        return self.score / 10.0


@dataclass
class TestCase:
    """
    Test case definition for evaluation.

    Contains input, expected output, and ground truth for validation.
    """
    id: str
    category: str                       # "strong_match", "weak_match", "edge_case"
    description: str

    # Input to the agent
    input: Dict[str, Any]               # {"resume": "...", "job_description": "..."}

    # Expected behavior
    expected: Dict[str, Any]            # {"tool_called": "score_job_match", "required_args": [...]}

    # Ground truth for scoring
    ground_truth: Optional[Dict[str, Any]] = None  # {"ideal_score": 85, "key_matches": [...]}

    # Metadata
    tags: List[str] = field(default_factory=list)
    difficulty: str = "normal"          # "easy", "normal", "hard"


class BaseEvaluator(ABC):
    """
    Abstract base class for all V2 evaluators.

    Subclasses must implement:
    - evaluate(): Run evaluation on a trace
    - evaluator_type: Return the evaluator type
    """

    @property
    @abstractmethod
    def evaluator_type(self) -> EvaluatorType:
        """Return the type of this evaluator"""
        pass

    @property
    def cost_per_eval(self) -> float:
        """Estimated cost per evaluation (override in subclass)"""
        return 0.0

    @abstractmethod
    def evaluate(
        self,
        trace: Dict[str, Any],
        expected: Dict[str, Any],
        test_case_id: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Evaluate a trace against expected outcomes.

        Args:
            trace: Observatory trace containing request/response/metadata
            expected: Expected behavior from test case
            test_case_id: Optional link to test case

        Returns:
            EvaluationResult with score, pass/fail, and details
        """
        pass

    def can_evaluate(self, trace: Dict[str, Any]) -> bool:
        """
        Check if this evaluator can handle the given trace.

        Override in subclass if evaluator has specific requirements.
        """
        return True

    def get_stats(self) -> Dict[str, Any]:
        """
        Get evaluator statistics.

        Override in subclass to track custom stats.
        """
        return {
            "evaluator_type": self.evaluator_type.value,
            "cost_per_eval": self.cost_per_eval,
        }
