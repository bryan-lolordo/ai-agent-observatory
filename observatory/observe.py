"""
@observe Decorator - Universal LLM Call Tracking
=================================================

The ONLY public interface for Observatory tracking.

Usage:
    from observatory import observe

    @observe(operation="chat", agent_name="ChatBot")
    async def my_llm_call(prompt: str, model: str = "gpt-4o-mini"):
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response

    # That's it. All metrics tracked, all opportunities detected.

Features:
    - Auto-extracts tokens, latency, cost from LLM response
    - Auto-detects response format (OpenAI, Anthropic, Azure, Semantic Kernel)
    - Runs all detectors in baseline mode
    - Applies optimizations in optimized mode (based on OPTIMIZATIONS config)
    - Handles sync and async functions
    - Full error tracking with classification
    - Conversation linking via conversation_id and turn_number parameters

The decorator wraps your function and:
    1. Times execution
    2. Checks cache (if enabled in optimizations)
    3. Extracts response data (tokens, content, cost)
    4. Runs all detectors
    5. Tracks with full 139-field schema
"""

import asyncio
import functools
import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from observatory import Observatory

logger = logging.getLogger(__name__)


# =============================================================================
# RESPONSE EXTRACTORS
# =============================================================================

@dataclass
class ExtractedResponse:
    """Extracted data from an LLM response."""
    response_text: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model_used: str = ""
    cost: float = 0.0
    finish_reason: str = ""

    # Provider-specific cache metrics
    cached_prompt_tokens: int = 0
    cached_token_savings: float = 0.0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    # Raw response for custom processing
    raw_response: Any = None

    # Metadata extracted from response
    metadata: Dict[str, Any] = field(default_factory=dict)


def _extract_openai_response(response: Any) -> ExtractedResponse:
    """Extract data from OpenAI/Azure response format."""
    result = ExtractedResponse(raw_response=response)

    try:
        # Extract content
        if hasattr(response, 'choices') and response.choices:
            choice = response.choices[0]
            if hasattr(choice, 'message'):
                result.response_text = choice.message.content or ""
            elif hasattr(choice, 'text'):
                result.response_text = choice.text or ""
            if hasattr(choice, 'finish_reason'):
                result.finish_reason = choice.finish_reason or ""

        # Extract usage
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            result.prompt_tokens = getattr(usage, 'prompt_tokens', 0) or 0
            result.completion_tokens = getattr(usage, 'completion_tokens', 0) or 0
            result.total_tokens = getattr(usage, 'total_tokens', 0) or result.prompt_tokens + result.completion_tokens

            # Azure/OpenAI cached tokens
            if hasattr(usage, 'prompt_tokens_details'):
                details = usage.prompt_tokens_details
                if hasattr(details, 'cached_tokens'):
                    result.cached_prompt_tokens = details.cached_tokens or 0
                    # ~50% savings per cached token
                    result.cached_token_savings = result.cached_prompt_tokens * 0.0000015

        # Extract model
        if hasattr(response, 'model'):
            result.model_used = response.model or ""

    except Exception as e:
        logger.debug(f"OpenAI extraction error: {e}")

    return result


def _extract_anthropic_response(response: Any) -> ExtractedResponse:
    """Extract data from Anthropic response format."""
    result = ExtractedResponse(raw_response=response)

    try:
        # Extract content
        if hasattr(response, 'content') and response.content:
            if isinstance(response.content, list):
                # Anthropic returns content as list of blocks
                texts = []
                for block in response.content:
                    if hasattr(block, 'text'):
                        texts.append(block.text)
                    elif isinstance(block, dict) and 'text' in block:
                        texts.append(block['text'])
                result.response_text = "".join(texts)
            else:
                result.response_text = str(response.content)

        # Extract usage
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            result.prompt_tokens = getattr(usage, 'input_tokens', 0) or 0
            result.completion_tokens = getattr(usage, 'output_tokens', 0) or 0
            result.total_tokens = result.prompt_tokens + result.completion_tokens

            # Anthropic cache metrics
            if hasattr(usage, 'cache_creation_input_tokens'):
                result.cache_creation_tokens = usage.cache_creation_input_tokens or 0
            if hasattr(usage, 'cache_read_input_tokens'):
                result.cache_read_tokens = usage.cache_read_input_tokens or 0
                result.cached_prompt_tokens = result.cache_read_tokens
                # ~90% savings on cache reads
                result.cached_token_savings = result.cache_read_tokens * 0.0000027

        # Extract model and stop reason
        if hasattr(response, 'model'):
            result.model_used = response.model or ""
        if hasattr(response, 'stop_reason'):
            result.finish_reason = response.stop_reason or ""

    except Exception as e:
        logger.debug(f"Anthropic extraction error: {e}")

    return result


def _extract_semantic_kernel_response(response: Any) -> ExtractedResponse:
    """Extract data from Semantic Kernel ChatMessageContent format."""
    result = ExtractedResponse(raw_response=response)

    try:
        # Extract content
        if hasattr(response, 'content'):
            result.response_text = str(response.content) if response.content else ""

        # Extract from metadata (SK stores usage as CompletionUsage object)
        if hasattr(response, 'metadata') and response.metadata:
            metadata = response.metadata

            # Usage info - SK stores as CompletionUsage object in metadata['usage']
            usage = metadata.get('usage')
            if usage:
                # CompletionUsage object (OpenAI SDK type)
                if hasattr(usage, 'prompt_tokens'):
                    result.prompt_tokens = usage.prompt_tokens or 0
                    result.completion_tokens = usage.completion_tokens or 0
                    result.total_tokens = getattr(usage, 'total_tokens', 0) or (result.prompt_tokens + result.completion_tokens)
                elif isinstance(usage, dict):
                    result.prompt_tokens = usage.get('prompt_tokens', 0)
                    result.completion_tokens = usage.get('completion_tokens', 0)
                    result.total_tokens = usage.get('total_tokens', result.prompt_tokens + result.completion_tokens)

                # Check for cached tokens (Azure via SK)
                if hasattr(usage, 'prompt_tokens_details') and usage.prompt_tokens_details:
                    details = usage.prompt_tokens_details
                    cached = getattr(details, 'cached_tokens', 0) or 0
                    if cached:
                        result.cached_prompt_tokens = cached
                        result.cached_token_savings = cached * 0.0000015

            # Finish reason
            if 'finish_reason' in metadata:
                result.finish_reason = metadata['finish_reason'] or ""

        # Extract model and usage from inner_content (OpenAI ChatCompletion object)
        if hasattr(response, 'inner_content') and response.inner_content:
            inner = response.inner_content
            if hasattr(inner, 'model'):
                result.model_used = inner.model or ""

            # Fallback: get usage from inner_content if not in metadata
            if result.prompt_tokens == 0 and hasattr(inner, 'usage') and inner.usage:
                usage = inner.usage
                result.prompt_tokens = getattr(usage, 'prompt_tokens', 0) or 0
                result.completion_tokens = getattr(usage, 'completion_tokens', 0) or 0
                result.total_tokens = getattr(usage, 'total_tokens', 0) or (result.prompt_tokens + result.completion_tokens)

    except Exception as e:
        logger.debug(f"Semantic Kernel extraction error: {e}")

    return result


def _extract_dict_response(response: dict) -> ExtractedResponse:
    """Extract data from dictionary response format."""
    result = ExtractedResponse(raw_response=response)

    try:
        # Common keys for response text
        for key in ['content', 'text', 'response', 'message', 'output']:
            if key in response:
                result.response_text = str(response[key])
                break

        # Usage info
        usage = response.get('usage', {})
        if isinstance(usage, dict):
            result.prompt_tokens = usage.get('prompt_tokens', usage.get('input_tokens', 0))
            result.completion_tokens = usage.get('completion_tokens', usage.get('output_tokens', 0))
            result.total_tokens = usage.get('total_tokens', result.prompt_tokens + result.completion_tokens)

        # Model
        result.model_used = response.get('model', '')

    except Exception as e:
        logger.debug(f"Dict extraction error: {e}")

    return result


def _extract_tuple_response(response: tuple) -> ExtractedResponse:
    """Extract data from (text, usage_dict) tuple format."""
    result = ExtractedResponse(raw_response=response)

    try:
        if len(response) >= 1:
            result.response_text = str(response[0]) if response[0] else ""

        if len(response) >= 2 and isinstance(response[1], dict):
            usage = response[1]
            result.prompt_tokens = usage.get('prompt_tokens', 0)
            result.completion_tokens = usage.get('completion_tokens', 0)
            result.total_tokens = usage.get('total_tokens', result.prompt_tokens + result.completion_tokens)
            result.cost = usage.get('cost', 0.0)
            result.model_used = usage.get('model', '')

    except Exception as e:
        logger.debug(f"Tuple extraction error: {e}")

    return result


def extract_response(response: Any) -> ExtractedResponse:
    """
    Auto-detect response format and extract data.

    Supports:
    - OpenAI/Azure responses
    - Anthropic responses
    - Semantic Kernel ChatMessageContent
    - Dict responses
    - (text, usage_dict) tuples
    - Plain strings
    """
    if response is None:
        return ExtractedResponse()

    # Plain string
    if isinstance(response, str):
        return ExtractedResponse(response_text=response, raw_response=response)

    # Tuple format: (text, usage_dict)
    if isinstance(response, tuple):
        return _extract_tuple_response(response)

    # Dict format
    if isinstance(response, dict):
        return _extract_dict_response(response)

    # Check for OpenAI format (has .choices)
    if hasattr(response, 'choices'):
        return _extract_openai_response(response)

    # Check for Anthropic format (has .content as list and .usage.input_tokens)
    if hasattr(response, 'content') and hasattr(response, 'usage'):
        usage = response.usage
        if hasattr(usage, 'input_tokens'):
            return _extract_anthropic_response(response)

    # Check for Semantic Kernel format (has .metadata with usage)
    if hasattr(response, 'metadata') and hasattr(response, 'content'):
        return _extract_semantic_kernel_response(response)

    # Fallback: try to convert to string
    try:
        return ExtractedResponse(response_text=str(response), raw_response=response)
    except Exception:
        return ExtractedResponse(raw_response=response)


# =============================================================================
# ARGUMENT EXTRACTORS
# =============================================================================

def extract_prompt_from_args(args: tuple, kwargs: dict) -> Dict[str, Any]:
    """
    Extract prompt, system_prompt, messages, etc. from function arguments.

    Looks for common parameter patterns:
    - prompt, user_message, message, query, input
    - system_prompt, system, instructions
    - messages, chat_history, history
    - model, temperature, max_tokens
    """
    extracted = {
        'user_message': None,
        'system_prompt': None,
        'messages': None,
        'model': None,
        'temperature': None,
        'max_tokens': None,
    }

    # Check kwargs for named parameters
    user_keys = ['prompt', 'user_message', 'message', 'query', 'input', 'content']
    system_keys = ['system_prompt', 'system', 'instructions', 'system_message']
    messages_keys = ['messages', 'chat_history', 'history', 'conversation']

    for key in user_keys:
        if key in kwargs and kwargs[key]:
            extracted['user_message'] = str(kwargs[key])
            break

    for key in system_keys:
        if key in kwargs and kwargs[key]:
            extracted['system_prompt'] = str(kwargs[key])
            break

    for key in messages_keys:
        if key in kwargs and kwargs[key]:
            extracted['messages'] = kwargs[key]
            break

    # Extract model parameters
    extracted['model'] = kwargs.get('model')
    extracted['temperature'] = kwargs.get('temperature')
    extracted['max_tokens'] = kwargs.get('max_tokens')

    # If no user_message found in kwargs, try first positional arg (common pattern)
    if not extracted['user_message'] and args:
        first_arg = args[0]
        if isinstance(first_arg, str):
            extracted['user_message'] = first_arg
        elif isinstance(first_arg, list):
            # Might be messages array
            extracted['messages'] = first_arg

    return extracted


# =============================================================================
# OBSERVE DECORATOR
# =============================================================================

def observe(
    operation: str = None,
    agent_name: str = None,
    agent_role: str = None,

    # Optional - extracted from function params if not provided
    conversation_id: str = None,
    turn_number: int = None,
    user_id: str = None,

    # Cache control
    cache_key: dict = None,
    skip_cache: bool = False,

    # Quality evaluation
    skip_quality_eval: bool = False,

    # Routing
    complexity: float = 0.5,
    skip_routing: bool = False,

    # Additional metadata
    metadata: dict = None,

    # Dependency injection (typically from config file)
    obs: 'Observatory' = None,
    cache: Any = None,
    semantic_cache: Any = None,
    router: Any = None,
    prefix_cache: Any = None,
    streaming_detector: Any = None,
    batch_detector: Any = None,
    context_growth_detector: Any = None,
    token_efficiency_detector: Any = None,
    judge: Any = None,
    track_llm_call_fn: Callable = None,
    optimizations: dict = None,
    current_phase: str = None,
    default_model: str = None,
    estimate_tokens_fn: Callable = None,
    calculate_cost_fn: Callable = None,
    create_cache_metadata_fn: Callable = None,
    classify_error_fn: Callable = None,
):
    """
    Universal decorator for tracking LLM calls.

    This is THE public interface for Observatory. It replaces:
    - TrackedLLMCall context manager
    - tracked_call() factory function
    - Manual 10-step tracking pattern

    The decorator:
    1. Times execution
    2. Extracts prompts from function arguments
    3. Checks cache (if optimizations enabled)
    4. Calls your function
    5. Extracts tokens/cost from response
    6. Runs all detectors
    7. Tracks with full 139-field schema

    Args:
        operation: Operation name for tracking (defaults to function name)
        agent_name: Name of the calling agent/component
        agent_role: Role (analyst, coordinator, writer, etc.)
        conversation_id: ID linking related calls (or extract from kwargs)
        turn_number: Turn number in conversation (or extract from kwargs)
        user_id: User identifier (or extract from kwargs)
        cache_key: Dict of values to generate cache key from
        skip_cache: Skip cache check entirely
        skip_quality_eval: Skip quality evaluation
        complexity: Task complexity (0.0-1.0) for routing decisions
        skip_routing: Skip model routing
        metadata: Additional metadata to track

        # Injected by config (typically not set by user):
        obs: Observatory instance
        cache: CacheManager instance
        semantic_cache: SemanticCache instance
        router: ModelRouter instance
        prefix_cache: PrefixCacheDetector instance
        streaming_detector: StreamingDetector instance
        batch_detector: BatchDetector instance
        context_growth_detector: ContextGrowthDetector instance
        token_efficiency_detector: TokenEfficiencyDetector instance
        judge: LLMJudge instance
        track_llm_call_fn: Function to track calls
        optimizations: OPTIMIZATIONS dict from config
        current_phase: "baseline" or "optimized"
        default_model: Default model name
        estimate_tokens_fn: Token estimation function
        calculate_cost_fn: Cost calculation function
        create_cache_metadata_fn: Cache metadata factory
        classify_error_fn: Error classification function

    Returns:
        Decorated function

    Examples:
        # Basic usage
        @observe(operation="chat")
        async def chat(prompt: str):
            return await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )

        # With conversation tracking
        @observe(operation="chat", agent_name="ChatBot")
        async def chat(prompt: str, conversation_id: str = None, turn_number: int = None):
            return await client.chat.completions.create(...)

        # With custom metadata
        @observe(
            operation="analyze",
            agent_name="Analyzer",
            metadata={"domain": "finance"}
        )
        async def analyze(data: dict):
            return await client.chat.completions.create(...)
    """

    def decorator(func: Callable) -> Callable:
        # Determine operation name
        op_name = operation or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await _execute_with_tracking(
                func, args, kwargs, is_async=True,
                op_name=op_name, agent_name=agent_name, agent_role=agent_role,
                conversation_id=conversation_id, turn_number=turn_number, user_id=user_id,
                cache_key=cache_key, skip_cache=skip_cache, skip_quality_eval=skip_quality_eval,
                complexity=complexity, skip_routing=skip_routing, metadata=metadata,
                obs=obs, cache=cache, semantic_cache=semantic_cache, router=router,
                prefix_cache=prefix_cache, streaming_detector=streaming_detector,
                batch_detector=batch_detector, context_growth_detector=context_growth_detector,
                token_efficiency_detector=token_efficiency_detector, judge=judge,
                track_llm_call_fn=track_llm_call_fn, optimizations=optimizations,
                current_phase=current_phase, default_model=default_model,
                estimate_tokens_fn=estimate_tokens_fn, calculate_cost_fn=calculate_cost_fn,
                create_cache_metadata_fn=create_cache_metadata_fn,
                classify_error_fn=classify_error_fn,
            )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in event loop
            try:
                loop = asyncio.get_running_loop()
                # Already in async context - create task
                return loop.run_until_complete(
                    _execute_with_tracking(
                        func, args, kwargs, is_async=False,
                        op_name=op_name, agent_name=agent_name, agent_role=agent_role,
                        conversation_id=conversation_id, turn_number=turn_number, user_id=user_id,
                        cache_key=cache_key, skip_cache=skip_cache, skip_quality_eval=skip_quality_eval,
                        complexity=complexity, skip_routing=skip_routing, metadata=metadata,
                        obs=obs, cache=cache, semantic_cache=semantic_cache, router=router,
                        prefix_cache=prefix_cache, streaming_detector=streaming_detector,
                        batch_detector=batch_detector, context_growth_detector=context_growth_detector,
                        token_efficiency_detector=token_efficiency_detector, judge=judge,
                        track_llm_call_fn=track_llm_call_fn, optimizations=optimizations,
                        current_phase=current_phase, default_model=default_model,
                        estimate_tokens_fn=estimate_tokens_fn, calculate_cost_fn=calculate_cost_fn,
                        create_cache_metadata_fn=create_cache_metadata_fn,
                        classify_error_fn=classify_error_fn,
                    )
                )
            except RuntimeError:
                # No event loop - run synchronously
                return _execute_sync_with_tracking(
                    func, args, kwargs,
                    op_name=op_name, agent_name=agent_name, agent_role=agent_role,
                    conversation_id=conversation_id, turn_number=turn_number, user_id=user_id,
                    cache_key=cache_key, skip_cache=skip_cache, skip_quality_eval=skip_quality_eval,
                    complexity=complexity, skip_routing=skip_routing, metadata=metadata,
                    obs=obs, cache=cache, router=router, prefix_cache=prefix_cache,
                    streaming_detector=streaming_detector, batch_detector=batch_detector,
                    context_growth_detector=context_growth_detector,
                    token_efficiency_detector=token_efficiency_detector,
                    track_llm_call_fn=track_llm_call_fn, optimizations=optimizations,
                    current_phase=current_phase, default_model=default_model,
                    estimate_tokens_fn=estimate_tokens_fn, calculate_cost_fn=calculate_cost_fn,
                    create_cache_metadata_fn=create_cache_metadata_fn,
                    classify_error_fn=classify_error_fn,
                )

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


async def _execute_with_tracking(
    func: Callable,
    args: tuple,
    kwargs: dict,
    is_async: bool,
    op_name: str,
    agent_name: str,
    agent_role: str,
    conversation_id: str,
    turn_number: int,
    user_id: str,
    cache_key: dict,
    skip_cache: bool,
    skip_quality_eval: bool,
    complexity: float,
    skip_routing: bool,
    metadata: dict,
    obs: Any,
    cache: Any,
    semantic_cache: Any,
    router: Any,
    prefix_cache: Any,
    streaming_detector: Any,
    batch_detector: Any,
    context_growth_detector: Any,
    token_efficiency_detector: Any,
    judge: Any,
    track_llm_call_fn: Callable,
    optimizations: dict,
    current_phase: str,
    default_model: str,
    estimate_tokens_fn: Callable,
    calculate_cost_fn: Callable,
    create_cache_metadata_fn: Callable,
    classify_error_fn: Callable,
) -> Any:
    """Execute function with full tracking pipeline."""

    start_time = time.perf_counter()

    # Extract prompts from arguments
    extracted_args = extract_prompt_from_args(args, kwargs)
    user_message = extracted_args['user_message']
    system_prompt = extracted_args['system_prompt']
    messages = extracted_args['messages']
    model_from_args = extracted_args['model']

    # Extract conversation context from kwargs if not provided at decorator level
    conv_id = conversation_id or kwargs.get('conversation_id')
    turn_num = turn_number or kwargs.get('turn_number')
    uid = user_id or kwargs.get('user_id')

    # Build full prompt for caching
    full_prompt = ""
    if system_prompt:
        full_prompt = f"{system_prompt}\n\n"
    if user_message:
        full_prompt += user_message

    # Get operation optimizations
    op_optimizations = (optimizations or {}).get(op_name, {})
    is_optimized_phase = current_phase == "optimized"

    # Cache metadata for tracking
    cache_metadata = None
    routed_model = model_from_args or default_model
    routing_decision = None

    # =========================================================================
    # STEP 1: Check cache (if enabled)
    # =========================================================================
    if not skip_cache and cache and full_prompt:
        cache_config = op_optimizations.get('cache', {})
        cache_enabled = cache_config.get('enabled', False) if is_optimized_phase else False

        try:
            key_data = cache_key.copy() if cache_key else {}
            if not key_data:
                key_data = {"prompt_hash": hashlib.sha256(full_prompt.encode()).hexdigest()[:16]}

            cached_value, cache_meta = cache.get(
                operation=op_name,
                key_data=key_data,
                prompt=full_prompt,
            )

            if cache_meta:
                cache_metadata = cache_meta

            # Return cached value in optimized mode
            if cache_enabled and cached_value is not None and cache_meta and cache_meta.cache_hit:
                latency_ms = (time.perf_counter() - start_time) * 1000

                # Track cache hit
                if track_llm_call_fn:
                    track_llm_call_fn(
                        model_name=routed_model,
                        prompt_tokens=0,
                        completion_tokens=0,
                        latency_ms=latency_ms,
                        operation=op_name,
                        agent_name=agent_name,
                        agent_role=agent_role,
                        success=True,
                        user_message=user_message,
                        system_prompt=system_prompt,
                        response_text=str(cached_value),
                        cache_metadata=cache_metadata,
                        conversation_id=conv_id,
                        turn_number=turn_num,
                        user_id=uid,
                        metadata={**(metadata or {}), "cache_return": True},
                    )

                return cached_value
        except Exception as e:
            logger.debug(f"Cache check failed: {e}")

    # =========================================================================
    # STEP 2: Check semantic cache (if enabled)
    # =========================================================================
    # Only query semantic cache in optimized mode - embedding queries are too slow for baseline
    sem_config = op_optimizations.get('semantic_cache', {})
    sem_enabled = sem_config.get('enabled', False) if is_optimized_phase else False

    if not skip_cache and semantic_cache and full_prompt and is_optimized_phase and sem_enabled:
        try:
            sem_result = await semantic_cache.get(
                prompt=full_prompt,
                operation=op_name,
            )

            if sem_result and sem_result.hit:
                latency_ms = (time.perf_counter() - start_time) * 1000

                # Track semantic cache hit
                if track_llm_call_fn:
                    track_llm_call_fn(
                        model_name=routed_model,
                        prompt_tokens=0,
                        completion_tokens=0,
                        latency_ms=latency_ms,
                        operation=op_name,
                        agent_name=agent_name,
                        agent_role=agent_role,
                        success=True,
                        user_message=user_message,
                        system_prompt=system_prompt,
                        response_text=sem_result.response,
                        conversation_id=conv_id,
                        turn_number=turn_num,
                        user_id=uid,
                        metadata={
                            **(metadata or {}),
                            "semantic_cache_return": True,
                            "semantic_similarity": sem_result.similarity,
                        },
                    )

                return sem_result.response
        except Exception as e:
            logger.debug(f"Semantic cache check failed: {e}")

    # =========================================================================
    # STEP 3: Route model (if enabled)
    # =========================================================================
    if not skip_routing and router and full_prompt:
        route_config = op_optimizations.get('route_to')

        try:
            estimated_tokens = len(full_prompt) // 4  # Rough estimate
            if estimate_tokens_fn:
                estimated_tokens = estimate_tokens_fn(full_prompt)

            selected_model, routing_decision = router.select(
                operation=op_name,
                complexity=complexity,
                estimated_tokens=estimated_tokens,
            )

            # Apply routing in optimized mode
            if is_optimized_phase and routing_decision:
                routed_model = selected_model

            # Override with explicit route_to
            if is_optimized_phase and route_config:
                routed_model = route_config
        except Exception as e:
            logger.debug(f"Routing failed: {e}")

    # =========================================================================
    # STEP 4: Track prefix (for prefix caching detection)
    # =========================================================================
    if prefix_cache and system_prompt:
        try:
            prefix_cache.track_call(
                operation=op_name,
                system_prompt=system_prompt,
                system_prompt_tokens=len(system_prompt) // 4,
            )
        except Exception as e:
            logger.debug(f"Prefix tracking failed: {e}")

    # =========================================================================
    # STEP 5: Execute the function
    # =========================================================================
    error = None
    error_info = {}
    response = None

    try:
        if is_async:
            response = await func(*args, **kwargs)
        else:
            response = func(*args, **kwargs)
    except Exception as e:
        error = e
        if classify_error_fn:
            error_info = classify_error_fn(e, op_name)
        else:
            error_info = {"error_type": type(e).__name__, "error_code": "UNKNOWN"}

    latency_ms = (time.perf_counter() - start_time) * 1000

    # =========================================================================
    # STEP 6: Extract response data
    # =========================================================================
    extracted = extract_response(response)

    # =========================================================================
    # STEP 7: Run detectors
    # =========================================================================

    # Streaming detector
    if streaming_detector and extracted.completion_tokens:
        try:
            streaming_detector.check_call(
                operation=op_name,
                latency_ms=latency_ms,
                completion_tokens=extracted.completion_tokens,
            )
        except Exception as e:
            logger.debug(f"Streaming detection failed: {e}")

    # Batch detector
    if batch_detector:
        try:
            batch_detector.track_call(
                operation=op_name,
                timestamp=time.time(),
            )
        except Exception as e:
            logger.debug(f"Batch detection failed: {e}")

    # Context growth detector
    if context_growth_detector and messages:
        try:
            context_growth_detector.check_call(
                operation=op_name,
                messages=messages,
                prompt_tokens=extracted.prompt_tokens,
            )
        except Exception as e:
            logger.debug(f"Context growth detection failed: {e}")

    # Token efficiency detector
    if token_efficiency_detector and extracted.prompt_tokens and extracted.completion_tokens:
        try:
            token_efficiency_detector.check_call(
                operation=op_name,
                prompt_tokens=extracted.prompt_tokens,
                completion_tokens=extracted.completion_tokens,
            )
        except Exception as e:
            logger.debug(f"Token efficiency detection failed: {e}")

    # =========================================================================
    # STEP 8: Cache response (if successful)
    # =========================================================================
    if not error and not skip_cache and full_prompt and extracted.response_text:
        # Exact cache
        if cache:
            cache_config = op_optimizations.get('cache', {})
            cache_enabled = cache_config.get('enabled', False) if is_optimized_phase else False

            if cache_enabled or current_phase == "baseline":
                try:
                    key_data = cache_key.copy() if cache_key else {}
                    if not key_data:
                        key_data = {"prompt_hash": hashlib.sha256(full_prompt.encode()).hexdigest()[:16]}

                    cache.set(
                        operation=op_name,
                        key_data=key_data,
                        value=extracted.response_text,
                        ttl=cache_config.get('ttl'),
                    )
                except Exception as e:
                    logger.debug(f"Cache storage failed: {e}")

        # Semantic cache - only store in optimized mode (embedding generation is slow)
        if semantic_cache and is_optimized_phase:
            sem_config = op_optimizations.get('semantic_cache', {})
            sem_enabled = sem_config.get('enabled', False)

            if sem_enabled:
                try:
                    await semantic_cache.set(
                        prompt=full_prompt,
                        response=extracted.response_text,
                        operation=op_name,
                    )
                except Exception as e:
                    logger.debug(f"Semantic cache storage failed: {e}")

    # =========================================================================
    # STEP 9: Quality evaluation (fire-and-forget)
    # =========================================================================
    if not skip_quality_eval and judge and not error and extracted.response_text:
        try:
            # Fire and forget - don't await
            asyncio.create_task(
                judge.maybe_evaluate(
                    operation=op_name,
                    prompt=full_prompt,
                    response=extracted.response_text,
                    conversation_id=conv_id,
                    turn_number=turn_num,
                )
            )
        except Exception as e:
            logger.debug(f"Quality evaluation failed: {e}")

    # =========================================================================
    # STEP 10: Track the call
    # =========================================================================
    if track_llm_call_fn:
        try:
            # Calculate cost if function available
            cost = extracted.cost
            if not cost and calculate_cost_fn and extracted.model_used:
                try:
                    cost = calculate_cost_fn(
                        model=extracted.model_used,
                        prompt_tokens=extracted.prompt_tokens,
                        completion_tokens=extracted.completion_tokens,
                    )
                except Exception:
                    pass

            track_llm_call_fn(
                model_name=extracted.model_used or routed_model or default_model,
                prompt_tokens=extracted.prompt_tokens,
                completion_tokens=extracted.completion_tokens,
                latency_ms=latency_ms,

                operation=op_name,
                agent_name=agent_name,
                agent_role=agent_role,

                success=(error is None),
                error=str(error) if error else None,

                user_message=user_message,
                system_prompt=system_prompt,
                messages=messages,
                response_text=extracted.response_text,

                routing_decision=routing_decision,
                cache_metadata=cache_metadata,

                conversation_id=conv_id,
                turn_number=turn_num,
                user_id=uid,

                temperature=extracted_args.get('temperature'),
                max_tokens=extracted_args.get('max_tokens'),

                cached_prompt_tokens=extracted.cached_prompt_tokens,
                cached_token_savings=extracted.cached_token_savings,

                metadata={
                    **(metadata or {}),
                    "finish_reason": extracted.finish_reason,
                    "cache_creation_tokens": extracted.cache_creation_tokens,
                    "cache_read_tokens": extracted.cache_read_tokens,
                },

                **error_info,
            )
        except Exception as e:
            logger.warning(f"Failed to track LLM call: {e}")

    # Re-raise error if there was one
    if error:
        raise error

    return response


def _execute_sync_with_tracking(
    func: Callable,
    args: tuple,
    kwargs: dict,
    op_name: str,
    agent_name: str,
    agent_role: str,
    conversation_id: str,
    turn_number: int,
    user_id: str,
    cache_key: dict,
    skip_cache: bool,
    skip_quality_eval: bool,
    complexity: float,
    skip_routing: bool,
    metadata: dict,
    obs: Any,
    cache: Any,
    router: Any,
    prefix_cache: Any,
    streaming_detector: Any,
    batch_detector: Any,
    context_growth_detector: Any,
    token_efficiency_detector: Any,
    track_llm_call_fn: Callable,
    optimizations: dict,
    current_phase: str,
    default_model: str,
    estimate_tokens_fn: Callable,
    calculate_cost_fn: Callable,
    create_cache_metadata_fn: Callable,
    classify_error_fn: Callable,
) -> Any:
    """Synchronous execution with tracking (simplified - no async cache/semantic)."""

    start_time = time.perf_counter()

    # Extract prompts from arguments
    extracted_args = extract_prompt_from_args(args, kwargs)
    user_message = extracted_args['user_message']
    system_prompt = extracted_args['system_prompt']
    messages = extracted_args['messages']
    model_from_args = extracted_args['model']

    # Extract conversation context from kwargs
    conv_id = conversation_id or kwargs.get('conversation_id')
    turn_num = turn_number or kwargs.get('turn_number')
    uid = user_id or kwargs.get('user_id')

    full_prompt = ""
    if system_prompt:
        full_prompt = f"{system_prompt}\n\n"
    if user_message:
        full_prompt += user_message

    routed_model = model_from_args or default_model

    # Execute function
    error = None
    error_info = {}
    response = None

    try:
        response = func(*args, **kwargs)
    except Exception as e:
        error = e
        if classify_error_fn:
            error_info = classify_error_fn(e, op_name)
        else:
            error_info = {"error_type": type(e).__name__, "error_code": "UNKNOWN"}

    latency_ms = (time.perf_counter() - start_time) * 1000

    # Extract response
    extracted = extract_response(response)

    # Track
    if track_llm_call_fn:
        try:
            track_llm_call_fn(
                model_name=extracted.model_used or routed_model or default_model,
                prompt_tokens=extracted.prompt_tokens,
                completion_tokens=extracted.completion_tokens,
                latency_ms=latency_ms,

                operation=op_name,
                agent_name=agent_name,
                agent_role=agent_role,

                success=(error is None),
                error=str(error) if error else None,

                user_message=user_message,
                system_prompt=system_prompt,
                messages=messages,
                response_text=extracted.response_text,

                conversation_id=conv_id,
                turn_number=turn_num,
                user_id=uid,

                metadata=metadata,
                **error_info,
            )
        except Exception as e:
            logger.warning(f"Failed to track LLM call: {e}")

    if error:
        raise error

    return response


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    'observe',
    'extract_response',
    'ExtractedResponse',
]
