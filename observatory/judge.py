"""
LLM Judge - Quality Evaluation System
Location: observatory/judge.py

Configurable LLM-as-a-judge for evaluating response quality.
Applications configure which operations to judge and domain-specific criteria.
"""

import json
import random
import time
from typing import Optional, Dict, Set, Any, Callable, TYPE_CHECKING

from observatory.models import QualityEvaluation

if TYPE_CHECKING:
    from observatory.collector import Observatory


# =============================================================================
# DEFAULT CONFIGURATION
# =============================================================================

DEFAULT_CRITERIA = {
    "relevance": 0.25,
    "accuracy": 0.25,
    "helpfulness": 0.25,
    "clarity": 0.15,
    "professionalism": 0.10,
}

DEFAULT_SAMPLE_RATE = 0.5


# =============================================================================
# LLM JUDGE CLASS
# =============================================================================

class LLMJudge:
    """
    Configurable LLM-as-a-Judge for quality evaluation.
    
    Usage:
        judge = LLMJudge(
            observatory=obs,
            operations={"chat", "analyze", "generate"},
            sample_rate=0.5,
            domain_context="career advice and resume optimization"
        )
        
        # In your code
        quality = await judge.maybe_evaluate(
            operation="chat",
            prompt=user_query,
            response=llm_response,
            llm_client=your_client
        )
    """
    
    def __init__(
        self,
        observatory: Optional['Observatory'] = None,
        operations: Optional[Set[str]] = None,
        skip_operations: Optional[Set[str]] = None,
        sample_rate: float = DEFAULT_SAMPLE_RATE,
        criteria: Optional[Dict[str, float]] = None,
        domain_context: str = "AI assistant responses",
        judge_model: str = "gpt-4o-mini",
        track_judge_calls: bool = True,
    ):
        """
        Initialize LLM Judge.
        
        Args:
            observatory: Observatory instance for tracking judge calls
            operations: Set of operations to evaluate (if None, evaluates all)
            skip_operations: Set of operations to skip
            sample_rate: Fraction of calls to evaluate (0.0 to 1.0)
            criteria: Dict of criteria name → weight (must sum to 1.0)
            domain_context: Description of application domain for judge prompt
            judge_model: Model to use for judging
            track_judge_calls: Whether to track judge LLM calls in Observatory
        """
        self.observatory = observatory
        self.operations = operations or set()
        self.skip_operations = skip_operations or set()
        self.sample_rate = max(0.0, min(1.0, sample_rate))
        self.criteria = criteria or DEFAULT_CRITERIA.copy()
        self.domain_context = domain_context
        self.judge_model = judge_model
        self.track_judge_calls = track_judge_calls
        
        # Statistics
        self._total_evaluated = 0
        self._total_skipped = 0
        self._total_hallucinations = 0
        self._score_sum = 0.0
    
    # =========================================================================
    # CONFIGURATION
    # =========================================================================
    
    def add_operation(self, operation: str) -> 'LLMJudge':
        """Add an operation to evaluate."""
        self.operations.add(operation)
        return self
    
    def remove_operation(self, operation: str) -> 'LLMJudge':
        """Remove an operation from evaluation."""
        self.operations.discard(operation)
        return self
    
    def set_sample_rate(self, rate: float) -> 'LLMJudge':
        """Set sampling rate (0.0 to 1.0)."""
        self.sample_rate = max(0.0, min(1.0, rate))
        return self
    
    def set_criteria(self, criteria: Dict[str, float]) -> 'LLMJudge':
        """Set evaluation criteria and weights."""
        self.criteria = criteria
        return self
    
    # =========================================================================
    # EVALUATION DECISION
    # =========================================================================
    
    def should_evaluate(self, operation: str, force: bool = False) -> bool:
        """
        Determine if an operation should be evaluated.
        
        Args:
            operation: Operation name
            force: If True, bypass sampling
        
        Returns:
            True if should evaluate
        """
        # Skip if in skip list
        if operation in self.skip_operations:
            return False
        
        # If operations set is defined, only evaluate those
        if self.operations and operation not in self.operations:
            return False
        
        # Apply sampling unless forced
        if not force and random.random() > self.sample_rate:
            self._total_skipped += 1
            return False
        
        return True
    
    # =========================================================================
    # MAIN EVALUATION METHODS
    # =========================================================================
    
    async def maybe_evaluate(
        self,
        operation: str,
        prompt: str,
        response: str,
        llm_client: Any,
        context: Optional[Dict] = None,
        force: bool = False,
    ) -> Optional[QualityEvaluation]:
        """
        Async evaluation with sampling.
        
        Args:
            operation: Operation name
            prompt: Original prompt
            response: LLM response to evaluate
            llm_client: Async LLM client with create() method
            context: Optional additional context
            force: Bypass sampling if True
        
        Returns:
            QualityEvaluation or None if skipped
        """
        if not self.should_evaluate(operation, force):
            return None
        
        return await self._evaluate_async(operation, prompt, response, llm_client, context)
    
    def maybe_evaluate_sync(
        self,
        operation: str,
        prompt: str,
        response: str,
        llm_client: Any,
        context: Optional[Dict] = None,
        force: bool = False,
    ) -> Optional[QualityEvaluation]:
        """
        Sync evaluation with sampling.
        
        Args:
            operation: Operation name
            prompt: Original prompt
            response: LLM response to evaluate
            llm_client: Sync LLM client (OpenAI/Azure)
            context: Optional additional context
            force: Bypass sampling if True
        
        Returns:
            QualityEvaluation or None if skipped
        """
        if not self.should_evaluate(operation, force):
            return None
        
        return self._evaluate_sync(operation, prompt, response, llm_client, context)
    
    # =========================================================================
    # INTERNAL EVALUATION LOGIC
    # =========================================================================
    
    async def _evaluate_async(
        self,
        operation: str,
        prompt: str,
        response: str,
        llm_client: Any,
        context: Optional[Dict] = None,
    ) -> Optional[QualityEvaluation]:
        """Internal async evaluation."""
        try:
            judge_prompt = self._create_judge_prompt(operation, prompt, response, context)
            
            start_time = time.time()
            
            # Call LLM (assumes OpenAI-style async client)
            result = await llm_client.chat.completions.create(
                model=self.judge_model,
                messages=[{"role": "user", "content": judge_prompt}],
                max_tokens=600,
                temperature=0.3,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            result_text = result.choices[0].message.content.strip()
            
            # Track judge call if enabled
            if self.track_judge_calls and self.observatory:
                from observatory.models import ModelProvider
                self.observatory.record_call(
                    provider=ModelProvider.OPENAI,
                    model_name=self.judge_model,
                    prompt_tokens=result.usage.prompt_tokens if hasattr(result, 'usage') else 0,
                    completion_tokens=result.usage.completion_tokens if hasattr(result, 'usage') else 0,
                    latency_ms=latency_ms,
                    agent_name="LLMJudge",
                    operation=f"judge_{operation}",
                    prompt=judge_prompt[:1000],
                    response_text=result_text,
                )
            
            return self._parse_and_create_evaluation(result_text, operation)
            
        except Exception as e:
            print(f"⚠️ Judge evaluation failed for {operation}: {e}")
            return None
    
    def _evaluate_sync(
        self,
        operation: str,
        prompt: str,
        response: str,
        llm_client: Any,
        context: Optional[Dict] = None,
    ) -> Optional[QualityEvaluation]:
        """Internal sync evaluation."""
        try:
            judge_prompt = self._create_judge_prompt(operation, prompt, response, context)
            
            start_time = time.time()
            
            # Call LLM (assumes OpenAI-style sync client)
            result = llm_client.chat.completions.create(
                model=self.judge_model,
                messages=[{"role": "user", "content": judge_prompt}],
                max_tokens=600,
                temperature=0.3,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            result_text = result.choices[0].message.content.strip()
            
            # Track judge call if enabled
            if self.track_judge_calls and self.observatory:
                from observatory.models import ModelProvider
                self.observatory.record_call(
                    provider=ModelProvider.OPENAI,
                    model_name=self.judge_model,
                    prompt_tokens=result.usage.prompt_tokens if hasattr(result, 'usage') else 0,
                    completion_tokens=result.usage.completion_tokens if hasattr(result, 'usage') else 0,
                    latency_ms=latency_ms,
                    agent_name="LLMJudge",
                    operation=f"judge_{operation}",
                    prompt=judge_prompt[:1000],
                    response_text=result_text,
                )
            
            return self._parse_and_create_evaluation(result_text, operation)
            
        except Exception as e:
            print(f"⚠️ Judge evaluation failed for {operation}: {e}")
            return None
    
    # =========================================================================
    # PROMPT GENERATION
    # =========================================================================
    
    def _create_judge_prompt(
        self,
        operation: str,
        prompt: str,
        response: str,
        context: Optional[Dict] = None,
    ) -> str:
        """Create the evaluation prompt."""
        
        # Truncate to avoid token limits
        prompt_preview = prompt[:1000] if len(prompt) > 1000 else prompt
        response_preview = response[:1500] if len(response) > 1500 else response
        
        # Build criteria section
        criteria_text = "\n".join([
            f"- **{name.title()}** ({int(weight*100)}%)"
            for name, weight in self.criteria.items()
        ])
        
        # Build context section
        context_section = ""
        if context:
            context_section = f"\nADDITIONAL CONTEXT:\n{json.dumps(context, indent=2)[:500]}\n"
        
        return f"""You are an expert evaluator of AI responses.

DOMAIN: {self.domain_context}

OPERATION TYPE: {operation}

EVALUATION CRITERIA (rate each 0-10):
{criteria_text}

ALSO CHECK FOR:
- **Hallucination**: Did the response make up facts, cite non-existent sources, or invent information?
- **Factual Error**: Is there incorrect information?

ORIGINAL USER REQUEST:
{prompt_preview}

AI RESPONSE:
{response_preview}
{context_section}

SCORING GUIDE:
- 9-10: Excellent - highly accurate, helpful, no issues
- 7-8: Good - mostly accurate, minor issues
- 5-6: Acceptable - some inaccuracies or vague content
- 3-4: Poor - significant issues
- 0-2: Very poor - incorrect or harmful

Return ONLY valid JSON (no markdown, no code blocks):

{{
  "score": <number 0-10>,
  "reasoning": "<one sentence explaining the overall score>",
  "criteria_scores": {{
    {", ".join([f'"{k}": <0-10>' for k in self.criteria.keys()])}
  }},
  "hallucination": <true or false>,
  "hallucination_details": "<specific made-up content, or null>",
  "factual_error": <true or false>,
  "factual_error_details": "<what was incorrect, or null>",
  "evidence_cited": <true or false>,
  "confidence": <0.0-1.0 your confidence in this evaluation>,
  "suggestions": ["<improvement 1>", "<improvement 2>"]
}}"""
    
    # =========================================================================
    # RESPONSE PARSING
    # =========================================================================
    
    def _parse_and_create_evaluation(
        self,
        result_text: str,
        operation: str,
    ) -> Optional[QualityEvaluation]:
        """Parse judge response and create QualityEvaluation."""
        try:
            data = self._parse_json_response(result_text)
            
            # Update statistics
            self._total_evaluated += 1
            self._score_sum += data.get('score', 0)
            if data.get('hallucination', False):
                self._total_hallucinations += 1
            
            # Determine failure reason
            failure_reason = None
            if data.get('hallucination', False):
                failure_reason = "HALLUCINATION"
            elif data.get('factual_error', False):
                failure_reason = "FACTUAL_ERROR"
            elif data.get('score', 10) < 3:
                failure_reason = "VERY_LOW_QUALITY"
            elif data.get('score', 10) < 5:
                failure_reason = "LOW_QUALITY"
            
            # Build improvement suggestion
            suggestions = data.get('suggestions', [])
            improvement = " | ".join(str(s) for s in suggestions[:2]) if suggestions else None
            
            evaluation = QualityEvaluation(
                judge_score=data.get('score'),
                hallucination_flag=data.get('hallucination', False),
                reasoning=data.get('reasoning'),
                confidence_score=data.get('confidence'),
                judge_model=self.judge_model,
                failure_reason=failure_reason,
                improvement_suggestion=improvement,
                hallucination_details=data.get('hallucination_details'),
                evidence_cited=data.get('evidence_cited'),
                factual_error=data.get('factual_error', False),
                criteria_scores=data.get('criteria_scores'),
            )
            
            # Log evaluation
            self._log_evaluation(operation, evaluation)
            
            return evaluation
            
        except Exception as e:
            print(f"⚠️ Failed to parse judge response: {e}")
            return None
    
    def _parse_json_response(self, result_text: str) -> dict:
        """Parse JSON from judge response, handling various formats."""
        
        # Clean up markdown code blocks
        if '```json' in result_text:
            result_text = result_text.split('```json')[1].split('```')[0].strip()
        elif '```' in result_text:
            parts = result_text.split('```')
            if len(parts) >= 2:
                result_text = parts[1].strip()
        
        # Extract JSON object
        start_idx = result_text.find('{')
        end_idx = result_text.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            raise ValueError("No JSON object found")
        
        json_str = result_text[start_idx:end_idx+1]
        data = json.loads(json_str)
        
        # Validate
        if 'score' not in data:
            raise ValueError("Missing 'score' field")
        
        score = data['score']
        if not isinstance(score, (int, float)) or score < 0 or score > 10:
            raise ValueError(f"Invalid score: {score}")
        
        return data
    
    def _log_evaluation(self, operation: str, evaluation: QualityEvaluation):
        """Log evaluation result."""
        msg = f"📊 Judged {operation}: Score {evaluation.judge_score}/10"
        if evaluation.hallucination_flag:
            msg += " 🚨 HALLUCINATION"
        if evaluation.factual_error:
            msg += " ❌ FACTUAL_ERROR"
        print(msg)
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get judge statistics."""
        avg_score = self._score_sum / self._total_evaluated if self._total_evaluated > 0 else 0
        hallucination_rate = self._total_hallucinations / self._total_evaluated if self._total_evaluated > 0 else 0
        
        return {
            "total_evaluated": self._total_evaluated,
            "total_skipped": self._total_skipped,
            "total_hallucinations": self._total_hallucinations,
            "average_score": round(avg_score, 2),
            "hallucination_rate": round(hallucination_rate, 3),
            "sample_rate": self.sample_rate,
            "operations": sorted(self.operations) if self.operations else "all",
            "skip_operations": sorted(self.skip_operations),
            "judge_model": self.judge_model,
            "criteria": self.criteria,
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self._total_evaluated = 0
        self._total_skipped = 0
        self._total_hallucinations = 0
        self._score_sum = 0.0


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def create_quality_evaluation(
    score: float,
    reasoning: str = "",
    hallucination: bool = False,
    factual_error: bool = False,
    failure_reason: Optional[str] = None,
    improvement_suggestion: Optional[str] = None,
    hallucination_details: Optional[str] = None,
    evidence_cited: Optional[bool] = None,
    confidence: float = 0.85,
    judge_model: Optional[str] = None,
    criteria_scores: Optional[Dict[str, float]] = None,
) -> QualityEvaluation:
    """
    Convenience function to create a QualityEvaluation.
    
    Args:
        score: Overall quality score (0-10)
        reasoning: Explanation of the score
        hallucination: Whether hallucination was detected
        factual_error: Whether factual error was detected
        failure_reason: Category (HALLUCINATION, FACTUAL_ERROR, LOW_QUALITY, etc.)
        improvement_suggestion: Suggested improvement
        hallucination_details: What was hallucinated
        evidence_cited: Whether sources were cited
        confidence: Confidence in evaluation (0-1)
        judge_model: Model used for judging
        criteria_scores: Per-criteria scores
    
    Returns:
        QualityEvaluation object
    """
    return QualityEvaluation(
        judge_score=score,
        hallucination_flag=hallucination,
        reasoning=reasoning,
        confidence_score=confidence,
        judge_model=judge_model,
        failure_reason=failure_reason,
        improvement_suggestion=improvement_suggestion,
        hallucination_details=hallucination_details,
        evidence_cited=evidence_cited,
        factual_error=factual_error,
        criteria_scores=criteria_scores,
    )