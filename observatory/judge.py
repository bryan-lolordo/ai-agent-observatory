"""
LLM Judge - Quality Evaluation System
Location: observatory/judge.py

Configurable LLM-as-a-judge for evaluating response quality.
Applications configure which operations to judge and domain-specific criteria.

UPDATED: Now supports multiple client types:
  - OpenAI / Azure OpenAI clients
  - Semantic Kernel
  - Generic async/sync callables

UPDATED (Phase 2): Added token breakdown, routing decision, and cache metadata
to all judge call tracking for complete Observatory metrics coverage.
"""

import asyncio
import hashlib
import json
import random
import time
from typing import Optional, Dict, Set, Any, Tuple, TYPE_CHECKING

from observatory.models import (
    QualityEvaluation,
    ModelProvider,
    RoutingDecision,
    CacheMetadata,
)

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
# CLIENT TYPE DETECTION
# =============================================================================

class ClientType:
    """Enum for supported client types."""
    OPENAI = "openai"
    SEMANTIC_KERNEL = "semantic_kernel"
    CALLABLE = "callable"
    UNKNOWN = "unknown"


def detect_client_type(client: Any) -> str:
    """
    Detect the type of LLM client.
    
    Args:
        client: The LLM client to detect
        
    Returns:
        ClientType string
    """
    # OpenAI / Azure OpenAI style (has .chat.completions.create)
    if hasattr(client, 'chat') and hasattr(client.chat, 'completions'):
        return ClientType.OPENAI
    
    # Semantic Kernel (has .invoke_prompt)
    if hasattr(client, 'invoke_prompt'):
        return ClientType.SEMANTIC_KERNEL
    
    # Generic callable (function or lambda)
    if callable(client):
        return ClientType.CALLABLE
    
    return ClientType.UNKNOWN


# =============================================================================
# LLM JUDGE CLASS
# =============================================================================

class LLMJudge:
    """
    Configurable LLM-as-a-Judge for quality evaluation.
    
    Supports multiple client types:
      - OpenAI / Azure OpenAI: client.chat.completions.create()
      - Semantic Kernel: kernel.invoke_prompt()
      - Generic callable: async def my_llm(prompt) -> str
    
    Usage:
        judge = LLMJudge(
            observatory=obs,
            operations={"chat", "analyze", "generate"},
            sample_rate=0.5,
            domain_context="career advice and resume optimization"
        )
        
        # In your code - works with any client type
        quality = await judge.maybe_evaluate(
            operation="chat",
            prompt=user_query,
            response=llm_response,
            llm_client=kernel  # or openai_client, or callable
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
        # Conversation tracking
        conversation_id: Optional[str] = None,
        turn_number: Optional[int] = None,
        parent_call_id: Optional[str] = None,
    ) -> Optional[QualityEvaluation]:
        """
        Async evaluation with sampling.
        
        Args:
            operation: Operation name
            prompt: Original prompt
            response: LLM response to evaluate
            llm_client: LLM client (OpenAI, Semantic Kernel, or callable)
            context: Optional additional context
            force: Bypass sampling if True
            conversation_id: Conversation identifier for linking
            turn_number: Turn number in conversation
        
        Returns:
            QualityEvaluation or None if skipped
        """
        if not self.should_evaluate(operation, force):
            return None
        
        return await self._evaluate_async(
            operation, prompt, response, llm_client, context,
            conversation_id=conversation_id, turn_number=turn_number,
            parent_call_id=parent_call_id,
        )
    
    def maybe_evaluate_sync(
        self,
        operation: str,
        prompt: str,
        response: str,
        llm_client: Any,
        context: Optional[Dict] = None,
        force: bool = False,
        # Conversation tracking
        conversation_id: Optional[str] = None,
        turn_number: Optional[int] = None,
        parent_call_id: Optional[str] = None,
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
            conversation_id: Conversation identifier for linking
            turn_number: Turn number in conversation
        
        Returns:
            QualityEvaluation or None if skipped
        """
        if not self.should_evaluate(operation, force):
            return None
        
        return self._evaluate_sync(
            operation, prompt, response, llm_client, context,
            conversation_id=conversation_id, turn_number=turn_number,
            parent_call_id=parent_call_id, 
        )
    
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
        conversation_id: Optional[str] = None,  
        turn_number: Optional[int] = None, 
        parent_call_id: Optional[str] = None,
    ) -> Optional[QualityEvaluation]:
        """Internal async evaluation with multi-client support."""
        try:
            judge_prompt = self._create_judge_prompt(operation, prompt, response, context)
            
            start_time = time.time()
            
            # Detect client type and call appropriately
            client_type = detect_client_type(llm_client)
            result_text, prompt_tokens, completion_tokens = await self._call_llm_async(
                llm_client, client_type, judge_prompt
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Track judge call if enabled
            if self.track_judge_calls and self.observatory:
                self._track_judge_call(
                    operation=operation,
                    judge_prompt=judge_prompt,
                    result_text=result_text,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=latency_ms,
                    client_type=client_type,
                    conversation_id=conversation_id,
                    turn_number=turn_number,
                    parent_call_id=parent_call_id,
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
        conversation_id: Optional[str] = None,
        turn_number: Optional[int] = None,
        parent_call_id: Optional[str] = None,
    ) -> Optional[QualityEvaluation]:
        """Internal sync evaluation with multi-client support."""
        try:
            judge_prompt = self._create_judge_prompt(operation, prompt, response, context)
            
            start_time = time.time()
            
            # Detect client type and call appropriately
            client_type = detect_client_type(llm_client)
            result_text, prompt_tokens, completion_tokens = self._call_llm_sync(
                llm_client, client_type, judge_prompt
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Track judge call if enabled
            if self.track_judge_calls and self.observatory:
                self._track_judge_call(
                    operation=operation,
                    judge_prompt=judge_prompt,
                    result_text=result_text,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=latency_ms,
                    client_type=client_type,
                    conversation_id=conversation_id,
                    turn_number=turn_number,
                    parent_call_id=parent_call_id,
                )
            
            return self._parse_and_create_evaluation(result_text, operation)
            
        except Exception as e:
            print(f"⚠️ Judge evaluation failed for {operation}: {e}")
            return None
    
    # =========================================================================
    # JUDGE CALL TRACKING (Phase 2 - Complete metrics)
    # =========================================================================
    
    def _track_judge_call(
        self,
        operation: str,
        judge_prompt: str,
        result_text: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        client_type: str,
        conversation_id: Optional[str] = None,
        turn_number: Optional[int] = None,
        parent_call_id: Optional[str] = None,
    ):
        """
        Track judge call with complete Observatory metrics.
        
        Phase 2 Update: Now includes token breakdown, routing decision, 
        and cache metadata for full Tier 2/3 coverage.
        """
        # Token breakdown - judge prompt has system instructions + user content
        # Split at "ORIGINAL USER REQUEST:" marker
        system_instructions_end = judge_prompt.find("ORIGINAL USER REQUEST:")
        if system_instructions_end > 0:
            system_part = judge_prompt[:system_instructions_end]
            user_part = judge_prompt[system_instructions_end:]
        else:
            system_part = ""
            user_part = judge_prompt
        
        system_tokens = len(system_part) // 4
        user_tokens = len(user_part) // 4
        
        # Cache key for judge calls (same prompt = same evaluation)
        cache_key = hashlib.md5(judge_prompt.encode()).hexdigest()[:16]
        
        # Routing decision - judge calls use specific model with low temperature
        routing_decision = RoutingDecision(
            chosen_model=self.judge_model,
            alternative_models=["gpt-4o-mini", "gpt-4o"],
            reasoning="Quality evaluation - deterministic judging with low temperature",
            complexity_score=0.5,
        )
        
        # Cache metadata - judge calls not cached yet but tracking for future
        cache_metadata = CacheMetadata(
            cache_hit=False,
            cache_key=cache_key,
            cache_cluster_id=f"judge_{operation}",
        )
        
        # Record the call with complete metrics
        self.observatory.record_call(
            # Core metrics (Tier 1)
            provider=ModelProvider.OPENAI,
            model_name=self.judge_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            agent_name="LLMJudge",
            agent_role="reviewer",
            operation=f"judge_{operation}",
            
            # Content
            prompt=judge_prompt[:1000],
            response_text=result_text,
            
            # Token breakdown (Tier 2) - Phase 2 addition
            system_prompt_tokens=system_tokens,
            user_message_tokens=user_tokens,
            
            # Model config (Tier 2)
            temperature=0.3,
            max_tokens=600,
            
            # Routing decision (Tier 3) - Phase 2 addition
            routing_decision=routing_decision,
            
            # Cache metadata (Tier 3) - Phase 2 addition
            cache_metadata=cache_metadata,
            
            # Conversation linking
            conversation_id=conversation_id,
            turn_number=turn_number,
            parent_call_id=parent_call_id,
            
            # Metadata
            metadata={"client_type": client_type},
        )
    
    # =========================================================================
    # MULTI-CLIENT LLM CALLING
    # =========================================================================
    
    async def _call_llm_async(
        self,
        client: Any,
        client_type: str,
        prompt: str,
    ) -> Tuple[str, int, int]:
        """
        Call LLM based on client type (async).
        
        Returns:
            Tuple of (result_text, prompt_tokens, completion_tokens)
        """
        
        if client_type == ClientType.OPENAI:
            # OpenAI / Azure OpenAI style
            result = await client.chat.completions.create(
                model=self.judge_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.3,
            )
            result_text = result.choices[0].message.content.strip()
            prompt_tokens = result.usage.prompt_tokens if hasattr(result, 'usage') and result.usage else len(prompt) // 4
            completion_tokens = result.usage.completion_tokens if hasattr(result, 'usage') and result.usage else len(result_text) // 4
            return result_text, prompt_tokens, completion_tokens
        
        elif client_type == ClientType.SEMANTIC_KERNEL:
            # Semantic Kernel
            result = await client.invoke_prompt(prompt)
            result_text = str(result).strip()
            # Estimate tokens (Semantic Kernel doesn't expose usage easily)
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(result_text) // 4
            return result_text, prompt_tokens, completion_tokens
        
        elif client_type == ClientType.CALLABLE:
            # Generic callable - check if async
            if asyncio.iscoroutinefunction(client):
                result_text = await client(prompt)
            else:
                # Run sync callable in executor
                loop = asyncio.get_event_loop()
                result_text = await loop.run_in_executor(None, client, prompt)
            result_text = str(result_text).strip()
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(result_text) // 4
            return result_text, prompt_tokens, completion_tokens
        
        else:
            raise ValueError(
                f"Unsupported client type: {type(client).__name__}. "
                f"Expected OpenAI client (has .chat.completions), "
                f"Semantic Kernel (has .invoke_prompt), or callable."
            )
    
    def _call_llm_sync(
        self,
        client: Any,
        client_type: str,
        prompt: str,
    ) -> Tuple[str, int, int]:
        """
        Call LLM based on client type (sync).
        
        Returns:
            Tuple of (result_text, prompt_tokens, completion_tokens)
        """
        
        if client_type == ClientType.OPENAI:
            # OpenAI / Azure OpenAI style
            result = client.chat.completions.create(
                model=self.judge_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.3,
            )
            result_text = result.choices[0].message.content.strip()
            prompt_tokens = result.usage.prompt_tokens if hasattr(result, 'usage') and result.usage else len(prompt) // 4
            completion_tokens = result.usage.completion_tokens if hasattr(result, 'usage') and result.usage else len(result_text) // 4
            return result_text, prompt_tokens, completion_tokens
        
        elif client_type == ClientType.SEMANTIC_KERNEL:
            # Semantic Kernel - sync version requires running async
            raise ValueError(
                "Semantic Kernel is async-only. Use maybe_evaluate() instead of maybe_evaluate_sync()."
            )
        
        elif client_type == ClientType.CALLABLE:
            # Generic callable
            if asyncio.iscoroutinefunction(client):
                raise ValueError(
                    "Async callable passed to sync method. Use maybe_evaluate() instead."
                )
            result_text = str(client(prompt)).strip()
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(result_text) // 4
            return result_text, prompt_tokens, completion_tokens
        
        else:
            raise ValueError(
                f"Unsupported client type: {type(client).__name__}. "
                f"Expected OpenAI client (has .chat.completions) or callable."
            )
    
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
        if not isinstance(score, (int, float)) or score < 0:
            raise ValueError(f"Invalid score: {score}")
        
        # Normalize if LLM returned 0-100 scale instead of 0-10
        if score > 10:
            score = round(score / 10.0, 1)
        data['score'] = score
        
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