"""
TrackedLLMCall - SDK Context Manager for LLM Call Optimization
===============================================================

Async context manager that encapsulates the 10-step LLM optimization pattern,
reducing ~400 lines of boilerplate per LLM call to ~15 lines while maintaining
comprehensive tracking and all optimization opportunities.

Usage:
    from observatory import TrackedLLMCall

    async with TrackedLLMCall(
        operation="quick_score_job",
        agent_name="ResumeMatching",
        complexity=0.4,
        phase="optimized",  # For baseline/optimized comparison
        cache_key={"job_id": job_id},
    ) as ctx:
        result = await ctx.call_llm(
            chat_completion=self.chat_completion,
            system_prompt=QUICK_SCORE_PROMPT,
            user_message=f"Resume:\n{resume_text}\n\nJob:\n{job}",
        )
        return self._parse_quick_score(result, job)

Steps handled automatically:
    1. Cache check (exact match)
    2. Semantic cache check (similarity match)
    3. Prompt optimization (compression)
    4. Model routing (complexity-based)
    5. Prefix cache tracking
    6. LLM call execution
    7. Streaming detection
    8. Cache response storage
    9. Quality evaluation
    10. Observatory tracking
"""

import hashlib
import time
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from observatory import Observatory

logger = logging.getLogger(__name__)


@dataclass
class TrackedLLMCallResult:
    """
    Result container from TrackedLLMCall context manager.

    Contains all metrics and metadata from the LLM call execution,
    including cache information, routing decisions, and quality evaluations.

    Attributes:
        response_text: The LLM response text (or cached response)
        prompt_tokens: Number of input tokens used
        completion_tokens: Number of output tokens generated
        total_tokens: Sum of prompt + completion tokens
        cost: Estimated cost of the call
        latency_ms: Total latency in milliseconds
        model_used: Model that was actually used (after routing)
        cache_hit: Whether response came from cache
        cache_type: Type of cache hit ("exact" or "semantic")
        routing_decision: Full RoutingDecision object if routing occurred
        quality_evaluation: QualityEvaluation if judge evaluation ran
        optimizations_applied: Dict tracking which optimizations were applied
        metadata: Additional metadata collected during execution
    """
    response_text: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: float = 0
    model_used: str = ""
    cache_hit: bool = False
    cache_type: Optional[str] = None  # "exact" or "semantic"
    routing_decision: Any = None  # RoutingDecision
    quality_evaluation: Any = None  # QualityEvaluation
    optimizations_applied: Dict[str, bool] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TrackedLLMCall:
    """
    Async context manager that encapsulates the 10-step LLM optimization pattern.

    This abstraction reduces boilerplate from ~400 lines per LLM call to ~15 lines
    while maintaining comprehensive tracking and all optimization opportunities.

    Args:
        operation: Operation name for tracking (e.g., "quick_score_job")
        agent_name: Name of the calling agent/plugin
        agent_role: Role enum or string (e.g., "analyst", "coordinator")
        complexity: Task complexity score (0.0-1.0) for routing decisions
        phase: "baseline" or "optimized" for comparison tracking
        cache_key: Dict of values to generate unique cache key from
        cache_ttl: Cache TTL in seconds (uses CacheManager default if not set)
        memory: ConversationMemory instance for context extraction
        conversation_id: ID linking related calls together
        turn_number: Turn number in conversation
        metadata: Additional metadata to track with the call
        skip_cache: Set True to bypass cache check entirely
        skip_quality_eval: Set True to bypass quality evaluation
        skip_routing: Set True to always use default model

        # Dependency injection (optional - uses globals if not provided)
        obs: Observatory instance
        cache: CacheManager instance
        semantic_cache: SemanticCache instance
        router: ModelRouter instance
        prefix_cache: PrefixCacheDetector instance
        streaming_detector: StreamingDetector instance
        prompt_optimizer: PromptOptimizer instance
        judge: LLMJudge instance
        track_llm_call_fn: Tracking function
        default_model: Default model name
        estimate_tokens_fn: Token estimation function
        calculate_cost_fn: Cost calculation function
        create_cache_metadata_fn: Cache metadata factory
        classify_error_fn: Error classification function
    """

    def __init__(
        self,
        operation: str,
        agent_name: str = None,
        agent_role: str = None,
        complexity: float = 0.5,
        phase: str = None,  # "baseline" or "optimized"
        cache_key: dict = None,
        cache_ttl: int = None,
        memory: Any = None,
        conversation_id: str = None,
        turn_number: int = None,
        metadata: dict = None,
        skip_cache: bool = False,
        skip_quality_eval: bool = False,
        skip_routing: bool = False,
        # Dependency injection
        obs: 'Observatory' = None,
        cache: Any = None,
        semantic_cache: Any = None,
        router: Any = None,
        prefix_cache: Any = None,
        streaming_detector: Any = None,
        prompt_optimizer: Any = None,
        judge: Any = None,
        track_llm_call_fn: callable = None,
        default_model: str = None,
        estimate_tokens_fn: callable = None,
        calculate_cost_fn: callable = None,
        create_cache_metadata_fn: callable = None,
        classify_error_fn: callable = None,
    ):
        # Operation configuration
        self.operation = operation
        self.agent_name = agent_name
        self.agent_role = agent_role
        self.complexity = complexity
        self.phase = phase
        self.cache_key = cache_key or {}
        self.cache_ttl = cache_ttl
        self.memory = memory
        self.conversation_id = conversation_id
        self.turn_number = turn_number
        self.metadata = metadata or {}
        self.skip_cache = skip_cache
        self.skip_quality_eval = skip_quality_eval
        self.skip_routing = skip_routing

        # Dependency injection (use provided or fall back to None)
        self._obs = obs
        self._cache = cache
        self._semantic_cache = semantic_cache
        self._router = router
        self._prefix_cache = prefix_cache
        self._streaming_detector = streaming_detector
        self._prompt_optimizer = prompt_optimizer
        self._judge = judge
        self._track_llm_call_fn = track_llm_call_fn
        self._default_model = default_model or "gpt-4o-mini"
        self._estimate_tokens_fn = estimate_tokens_fn or self._fallback_estimate_tokens
        self._calculate_cost_fn = calculate_cost_fn
        self._create_cache_metadata_fn = create_cache_metadata_fn
        self._classify_error_fn = classify_error_fn

        # Internal state
        self._start_time: float = None
        self._result: TrackedLLMCallResult = None
        self._system_prompt: str = None
        self._user_message: str = None
        self._full_prompt: str = None
        self._optimized_prompt: str = None
        self._execution_settings: Any = None
        self._cache_key_hash: str = None
        self._routing_decision: Any = None
        self._prefix_tracked: bool = False
        self._streaming_flagged: bool = False
        self._error: Exception = None
        self._quality_task: asyncio.Task = None

    @staticmethod
    def _fallback_estimate_tokens(text: str) -> int:
        """Fallback token estimation (4 chars per token average)."""
        return len(text) // 4 if text else 0

    async def __aenter__(self) -> 'TrackedLLMCall':
        """Enter context - start timing and initialize result container."""
        self._start_time = time.perf_counter()
        self._result = TrackedLLMCallResult()
        self._result.optimizations_applied = {
            "cache_checked": False,
            "semantic_cache_checked": False,
            "prompt_optimized": False,
            "model_routed": False,
            "prefix_tracked": False,
            "streaming_flagged": False,
            "quality_evaluated": False,
        }

        # Generate cache key hash
        if self.cache_key:
            key_str = f"{self.operation}:{sorted(self.cache_key.items())}"
            self._cache_key_hash = hashlib.sha256(key_str.encode()).hexdigest()[:16]

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit context - track the call to Observatory."""
        latency_ms = (time.perf_counter() - self._start_time) * 1000
        self._result.latency_ms = latency_ms

        # Wait for quality evaluation if running
        if self._quality_task and not self._quality_task.done():
            try:
                await asyncio.wait_for(self._quality_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.debug("Quality evaluation timed out")
            except Exception as e:
                logger.debug(f"Quality evaluation failed: {e}")

        # Track the call regardless of success/failure
        try:
            await self._track_call(
                success=(exc_type is None),
                error=str(exc_val) if exc_val else None,
            )
        except Exception as track_error:
            logger.warning(f"Failed to track LLM call: {track_error}")

        # Don't suppress exceptions
        return False

    def _generate_cache_key(self, prompt: str) -> str:
        """Generate cache key from prompt and cache_key dict."""
        if self._cache_key_hash:
            return f"{self.operation}:{self._cache_key_hash}:{hashlib.sha256(prompt.encode()).hexdigest()[:16]}"
        return f"{self.operation}:{hashlib.sha256(prompt.encode()).hexdigest()[:32]}"

    async def _check_exact_cache(self, prompt: str) -> Optional[str]:
        """Step 1: Check exact match cache."""
        if self.skip_cache or not self._cache:
            return None

        if hasattr(self._cache, 'enabled') and not self._cache.enabled:
            return None

        self._result.optimizations_applied["cache_checked"] = True

        try:
            # CacheManager.get() is synchronous and uses key_data dict
            # Build key_data from cache_key dict or use prompt hash
            key_data = self.cache_key.copy() if self.cache_key else {}
            if not key_data:
                key_data = {"prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16]}

            # CacheManager.get() returns (value, CacheMetadata) tuple
            cached_value, cache_metadata = self._cache.get(
                operation=self.operation,
                key_data=key_data,
                prompt=prompt,
            )

            if cached_value is not None and cache_metadata.cache_hit:
                self._result.cache_hit = True
                self._result.cache_type = "exact"
                self._result.metadata["cache_key"] = cache_metadata.cache_key
                return cached_value
        except Exception as e:
            logger.debug(f"Cache check failed: {e}")

        return None

    async def _check_semantic_cache(self, prompt: str) -> Optional[str]:
        """Step 2: Check semantic similarity cache."""
        if self.skip_cache or not self._semantic_cache:
            return None

        if hasattr(self._semantic_cache, 'enabled') and not self._semantic_cache.enabled:
            return None

        self._result.optimizations_applied["semantic_cache_checked"] = True

        try:
            # SemanticCache.get() signature: get(prompt, operation, threshold)
            sem_result = await self._semantic_cache.get(
                prompt=prompt,
                operation=self.operation,
            )

            if sem_result and sem_result.hit:
                self._result.cache_hit = True
                self._result.cache_type = "semantic"
                self._result.metadata["semantic_similarity"] = sem_result.similarity
                self._result.metadata["cache_key"] = sem_result.cache_key
                return sem_result.response
        except Exception as e:
            logger.debug(f"Semantic cache check failed: {e}")

        return None

    def _optimize_prompt(self, system_prompt: str, user_message: str) -> tuple:
        """Step 3: Optimize prompt based on operation complexity."""
        if not self._prompt_optimizer:
            return system_prompt, user_message, None

        if hasattr(self._prompt_optimizer, 'enabled') and not self._prompt_optimizer.enabled:
            return system_prompt, user_message, None

        self._result.optimizations_applied["prompt_optimized"] = True

        try:
            result = self._prompt_optimizer.get_optimized_prompt(
                operation=self.operation,
                default_prompt=system_prompt,
            )

            optimized_system = result.get("prompt", system_prompt)
            max_tokens = result.get("max_tokens")

            self._result.metadata["prompt_variant"] = result.get("variant", "default")
            self._result.metadata["prompt_savings"] = result.get("savings", {})

            return optimized_system, user_message, max_tokens
        except Exception as e:
            logger.debug(f"Prompt optimization failed: {e}")
            return system_prompt, user_message, None

    def _route_model(self, estimated_tokens: int = None) -> str:
        """Step 4: Route to optimal model based on complexity."""
        if self.skip_routing or not self._router:
            self._result.model_used = self._default_model
            return self._default_model

        if hasattr(self._router, 'enabled') and not self._router.enabled:
            self._result.model_used = self._default_model
            return self._default_model

        self._result.optimizations_applied["model_routed"] = True

        try:
            self._routing_decision = self._router.select(
                operation=self.operation,
                complexity=self.complexity,
                estimated_tokens=estimated_tokens,
            )

            self._result.model_used = self._routing_decision.selected_model
            self._result.routing_decision = self._routing_decision
            self._result.metadata["routing_reason"] = self._routing_decision.reason

            return self._routing_decision.selected_model
        except Exception as e:
            logger.debug(f"Model routing failed: {e}")
            self._result.model_used = self._default_model
            return self._default_model

    def _track_prefix(self, prompt: str):
        """Step 5: Track prefix for Azure/Anthropic prefix caching."""
        if not self._prefix_cache:
            return

        if hasattr(self._prefix_cache, 'enabled') and not self._prefix_cache.enabled:
            return

        self._result.optimizations_applied["prefix_tracked"] = True
        self._prefix_tracked = True

        try:
            self._prefix_cache.track(
                operation=self.operation,
                prompt=prompt,
            )
        except Exception as e:
            logger.debug(f"Prefix tracking failed: {e}")

    def _flag_streaming(self, latency_ms: float, output_tokens: int):
        """Step 7: Flag for streaming if high latency or large output."""
        if not self._streaming_detector:
            return

        if hasattr(self._streaming_detector, 'enabled') and not self._streaming_detector.enabled:
            return

        try:
            should_stream = self._streaming_detector.should_stream(
                operation=self.operation,
                latency_ms=latency_ms,
                output_tokens=output_tokens,
            )

            if should_stream:
                self._streaming_flagged = True
                self._result.optimizations_applied["streaming_flagged"] = True
                self._result.metadata["streaming_recommended"] = True
        except Exception as e:
            logger.debug(f"Streaming detection failed: {e}")

    async def _cache_response(self, prompt: str, response: str):
        """Step 8: Cache the response for future use."""
        if self.skip_cache:
            return

        # Store in exact match cache (CacheManager is synchronous)
        if self._cache and (not hasattr(self._cache, 'enabled') or self._cache.enabled):
            try:
                # Build key_data from cache_key dict or use prompt hash
                key_data = self.cache_key.copy() if self.cache_key else {}
                if not key_data:
                    key_data = {"prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16]}

                # CacheManager.set() signature: set(operation, key_data, value, ttl, metadata)
                self._cache.set(
                    operation=self.operation,
                    key_data=key_data,
                    value=response,
                    ttl=self.cache_ttl,
                )
            except Exception as e:
                logger.debug(f"Exact cache storage failed: {e}")

        # Store in semantic cache (SemanticCache is async)
        if self._semantic_cache and (not hasattr(self._semantic_cache, 'enabled') or self._semantic_cache.enabled):
            try:
                # SemanticCache.set() signature: set(prompt, response, operation, metadata)
                await self._semantic_cache.set(
                    prompt=prompt,
                    response=response,
                    operation=self.operation,
                )
            except Exception as e:
                logger.debug(f"Semantic cache storage failed: {e}")

    async def _evaluate_quality(self, prompt: str, response: str) -> Optional[Any]:
        """Step 9: Evaluate response quality with LLM-as-judge."""
        if self.skip_quality_eval or not self._judge:
            return None

        if hasattr(self._judge, 'enabled') and not self._judge.enabled:
            return None

        self._result.optimizations_applied["quality_evaluated"] = True

        try:
            evaluation = await self._judge.maybe_evaluate(
                operation=self.operation,
                prompt=prompt,
                response=response,
                client=None,  # Judge uses its own client
            )

            if evaluation:
                self._result.quality_evaluation = evaluation
                self._result.metadata["quality_score"] = evaluation.overall_score

            return evaluation
        except Exception as e:
            logger.debug(f"Quality evaluation failed: {e}")
            return None

    async def _track_call(self, success: bool, error: str = None):
        """Step 10: Track the call to Observatory."""
        if not self._track_llm_call_fn:
            logger.debug("No track_llm_call function provided, skipping tracking")
            return

        # Build metadata
        tracking_metadata = {
            **self.metadata,
            **self._result.metadata,
            "optimizations_applied": self._result.optimizations_applied,
        }

        # Add phase to metadata for comparison tracking
        if self.phase:
            tracking_metadata["phase"] = self.phase

        # Extract conversation context if memory provided
        chat_history_count = None
        if self.memory:
            try:
                if hasattr(self.memory, 'chat_history') and hasattr(self.memory.chat_history, 'messages'):
                    chat_history_count = len(self.memory.chat_history.messages)
            except Exception:
                pass

        # Build cache metadata if applicable
        cache_metadata = None
        if self._result.cache_hit and self._create_cache_metadata_fn:
            cache_metadata = self._create_cache_metadata_fn(
                cache_hit=self._result.cache_hit,
                cache_key=self._generate_cache_key(self._full_prompt) if self._full_prompt else None,
                cache_type=self._result.cache_type,
            )

        # Build error info if applicable
        error_info = {}
        if self._error and self._classify_error_fn:
            error_info = self._classify_error_fn(self._error, self.operation)

        # Calculate cost if function provided
        if self._calculate_cost_fn and self._result.prompt_tokens and self._result.completion_tokens:
            try:
                self._result.cost = self._calculate_cost_fn(
                    model=self._result.model_used or self._default_model,
                    prompt_tokens=self._result.prompt_tokens,
                    completion_tokens=self._result.completion_tokens,
                )
            except Exception:
                pass

        # Track with full schema
        self._track_llm_call_fn(
            model_name=self._result.model_used or self._default_model,
            prompt_tokens=self._result.prompt_tokens,
            completion_tokens=self._result.completion_tokens,
            latency_ms=self._result.latency_ms,

            agent_name=self.agent_name,
            agent_role=self.agent_role,
            operation=self.operation,

            success=success,
            error=error,

            prompt=self._full_prompt,
            response_text=self._result.response_text,
            system_prompt=self._system_prompt,
            user_message=self._user_message,

            routing_decision=self._result.routing_decision,
            cache_metadata=cache_metadata,
            quality_evaluation=self._result.quality_evaluation,

            conversation_id=self.conversation_id,
            turn_number=self.turn_number,
            chat_history_count=chat_history_count,

            temperature=getattr(self._execution_settings, 'temperature', None) if self._execution_settings else None,
            max_tokens=getattr(self._execution_settings, 'max_tokens', None) if self._execution_settings else None,

            metadata=tracking_metadata,

            # Phase for baseline/optimized comparison
            environment=self.phase,

            **error_info,
        )

    async def call(
        self,
        llm_func: callable,
        prompt: str,
        system_prompt: str = None,
        **kwargs,
    ) -> str:
        """
        Execute an LLM call with any async callable.

        This is the main method - works with any LLM client (OpenAI, Anthropic, Azure, etc.)

        Args:
            llm_func: Async function that takes prompt and returns either:
                     - response_text (str)
                     - (response_text, usage_dict) tuple where usage_dict has:
                       {"prompt_tokens": int, "completion_tokens": int, "cost": float (optional)}
            prompt: The user message / prompt to send
            system_prompt: Optional system prompt (tracked separately)
            **kwargs: Additional arguments to pass to llm_func

        Returns:
            Response text from the LLM (or cached response)

        Example with OpenAI:
            async def call_openai(prompt, system_prompt=None, **kwargs):
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    **kwargs
                )
                return response.choices[0].message.content, {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                }

            async with TrackedLLMCall(
                operation="analyze",
                agent_name="MyAgent",
                phase="optimized",
            ) as ctx:
                result = await ctx.call(
                    llm_func=call_openai,
                    prompt="Analyze this data...",
                    system_prompt="You are an analyst.",
                    temperature=0.3,
                )
        """
        self._system_prompt = system_prompt
        self._user_message = prompt
        self._full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        # ═══════════════════════════════════════════════════════════════
        # STEP 1: Check exact match cache
        # ═══════════════════════════════════════════════════════════════
        cached = await self._check_exact_cache(self._full_prompt)
        if cached:
            self._result.response_text = cached
            return cached

        # ═══════════════════════════════════════════════════════════════
        # STEP 2: Check semantic cache
        # ═══════════════════════════════════════════════════════════════
        semantic_cached = await self._check_semantic_cache(self._full_prompt)
        if semantic_cached:
            self._result.response_text = semantic_cached
            return semantic_cached

        # ═══════════════════════════════════════════════════════════════
        # STEP 3: Optimize prompt (if optimizer provided)
        # ═══════════════════════════════════════════════════════════════
        optimized_system = system_prompt
        optimized_user = prompt
        if system_prompt:
            optimized_system, optimized_user, _ = self._optimize_prompt(system_prompt, prompt)
        self._optimized_prompt = f"{optimized_system}\n\n{optimized_user}" if optimized_system else optimized_user

        # ═══════════════════════════════════════════════════════════════
        # STEP 4: Route to optimal model
        # ═══════════════════════════════════════════════════════════════
        estimated_tokens = self._estimate_tokens_fn(self._optimized_prompt)
        selected_model = self._route_model(estimated_tokens)

        # ═══════════════════════════════════════════════════════════════
        # STEP 5: Track prefix for prefix caching (system prompt)
        # ═══════════════════════════════════════════════════════════════
        if optimized_system:
            self._track_prefix(optimized_system)

        # ═══════════════════════════════════════════════════════════════
        # STEP 6: Execute LLM call
        # ═══════════════════════════════════════════════════════════════
        call_start = time.perf_counter()

        try:
            # Pass system_prompt to llm_func if provided
            if system_prompt:
                result = await llm_func(optimized_user, system_prompt=optimized_system, **kwargs)
            else:
                result = await llm_func(optimized_user, **kwargs)

            # Handle return format: (response_text, usage_dict) or just response_text
            if isinstance(result, tuple) and len(result) == 2:
                response_text, usage = result
                self._result.prompt_tokens = usage.get('prompt_tokens', self._estimate_tokens_fn(self._optimized_prompt))
                self._result.completion_tokens = usage.get('completion_tokens', self._estimate_tokens_fn(response_text))
                # Also capture cost if provided
                if 'cost' in usage:
                    self._result.cost = usage['cost']
            else:
                response_text = str(result)
                self._result.prompt_tokens = self._estimate_tokens_fn(self._optimized_prompt)
                self._result.completion_tokens = self._estimate_tokens_fn(response_text)

            call_latency = (time.perf_counter() - call_start) * 1000
            self._result.total_tokens = self._result.prompt_tokens + self._result.completion_tokens
            self._result.response_text = response_text
            self._result.model_used = selected_model

        except Exception as e:
            self._error = e
            raise

        # ═══════════════════════════════════════════════════════════════
        # STEP 7: Flag for streaming if needed
        # ═══════════════════════════════════════════════════════════════
        self._flag_streaming(call_latency, self._result.completion_tokens)

        # ═══════════════════════════════════════════════════════════════
        # STEP 8: Cache the response
        # ═══════════════════════════════════════════════════════════════
        await self._cache_response(self._full_prompt, response_text)

        # ═══════════════════════════════════════════════════════════════
        # STEP 9: Evaluate quality (async, tracked for completion)
        # ═══════════════════════════════════════════════════════════════
        self._quality_task = asyncio.create_task(
            self._evaluate_quality(self._full_prompt, response_text)
        )

        return response_text

    @property
    def result(self) -> TrackedLLMCallResult:
        """Access the result container with all metrics."""
        return self._result


# =============================================================================
# FACTORY FUNCTION (for SDK integration)
# =============================================================================

def create_tracked_call(
    operation: str,
    # Observatory components (typically from global config)
    obs: 'Observatory' = None,
    cache: Any = None,
    semantic_cache: Any = None,
    router: Any = None,
    prefix_cache: Any = None,
    streaming_detector: Any = None,
    prompt_optimizer: Any = None,
    judge: Any = None,
    track_llm_call_fn: callable = None,
    default_model: str = None,
    estimate_tokens_fn: callable = None,
    calculate_cost_fn: callable = None,
    create_cache_metadata_fn: callable = None,
    classify_error_fn: callable = None,
    **kwargs,
) -> TrackedLLMCall:
    """
    Factory function to create a TrackedLLMCall with pre-configured dependencies.

    This is useful when you want to create a partially configured factory
    that can be reused across your application.

    Usage:
        from functools import partial
        from observatory import create_tracked_call, track_llm_call, calculate_cost

        # In your config file - create a pre-configured factory
        tracked_call = partial(
            create_tracked_call,
            obs=obs,
            cache=cache,
            router=router,
            judge=judge,
            track_llm_call_fn=lambda **kw: track_llm_call(obs, **kw),
            calculate_cost_fn=calculate_cost,
        )

        # In your plugin - use the factory
        async with tracked_call(
            operation="quick_score",
            agent_name="ResumeMatching",
            complexity=0.4,
            phase="optimized",
        ) as ctx:
            result = await ctx.call_llm(...)
    """
    return TrackedLLMCall(
        operation=operation,
        obs=obs,
        cache=cache,
        semantic_cache=semantic_cache,
        router=router,
        prefix_cache=prefix_cache,
        streaming_detector=streaming_detector,
        prompt_optimizer=prompt_optimizer,
        judge=judge,
        track_llm_call_fn=track_llm_call_fn,
        default_model=default_model,
        estimate_tokens_fn=estimate_tokens_fn,
        calculate_cost_fn=calculate_cost_fn,
        create_cache_metadata_fn=create_cache_metadata_fn,
        classify_error_fn=classify_error_fn,
        **kwargs,
    )
