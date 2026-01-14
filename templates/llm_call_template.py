"""
LLM Call Template - Standardized Pattern for Observatory Integration
Location: your-project/ (reference file - copy patterns into your code)

================================================================================
HOW THE TEMPLATES WORK TOGETHER
================================================================================

STEP 1: Set up observatory_config.py (one-time setup)
    - Copy templates/observatory_config_template.py → your-project/observatory_config.py
    - Customize operations, prompts, routing rules for YOUR application
    - This creates: obs, cache, router, judge, track_llm_call, etc.

STEP 2: Use THIS file as a reference
    - Copy the IMPORT BLOCK into each file that makes LLM calls
    - Copy the relevant PATTERN (chat handler, plugin, or simple tracking)
    - Customize for your specific operations

================================================================================
PREREQUISITES
================================================================================

Before using these patterns, ensure you have:

1. Installed the Observatory SDK:
   pip install -e /path/to/ai-agent-observatory

2. (Optional) Installed ChromaDB for semantic caching:
   pip install chromadb

3. Created observatory_config.py in your project root
   (from templates/observatory_config_template.py)

================================================================================
PATTERNS INCLUDED
================================================================================

1. IMPORT BLOCK - Standard imports for any LLM-calling file
2. MAIN CHAT HANDLER - For chatbot/orchestrator patterns (Streamlit, CLI)
3. PLUGIN/FUNCTION PATTERN - For Semantic Kernel plugins or standalone functions
4. SIMPLE TRACKING - Minimal tracking for non-LLM operations (DB reads, etc.)
5. PROMPT VERSIONING - Best practice for tracking prompt changes
"""

# =============================================================================
# PATTERN 1: STANDARDIZED IMPORT BLOCK
# =============================================================================
# Copy this import block to the top of any file that makes LLM calls

"""
# ═══════════════════════════════════════════════════════════════════════════
# OBSERVATORY INTEGRATION - STANDARDIZED IMPORT BLOCK FOR LLM-MAKING FILES
# ═══════════════════════════════════════════════════════════════════════════
from observatory_config import (
    # Main tracking
    track_llm_call,

    # Optimization components (10-step pattern)
    cache,
    semantic_cache,
    prefix_cache,
    router,
    prompt_optimizer,
    streaming_detector,
    batch_detector,
    parallel_detector,
    judge,

    # Config constants
    DEFAULT_MODEL,
    CURRENT_PHASE,

    # Data models (import as needed)
    PromptMetadata,
    PromptBreakdown,
    RoutingDecision,
    CacheMetadata,
    QualityEvaluation,

    # Helper functions
    create_prompt_metadata,
    create_prompt_breakdown,
    create_routing_decision,
    create_cache_metadata,
    estimate_tokens,
    classify_error,
)
"""

import os
import time
import uuid
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# =============================================================================
# PATTERN 2: MAIN CHAT HANDLER (Streamlit/CLI Chatbot Pattern)
# =============================================================================
# Use this pattern for your main chat entry point that orchestrates LLM calls

async def chat_handler_template(
    message: str,
    history: Any,  # ChatHistory object
    memory: Any,   # ConversationMemory object
    chat_completion: Any,  # LLM client
    kernel: Any,   # Semantic Kernel (if using)
    execution_settings: Any,
    system_prompt: str,
    tool_definitions_tokens: int = 0,
) -> str:
    """
    Template for main chat handler with full 10-step optimization pattern.

    This is the ORCHESTRATOR pattern - used for main chatbot entry points
    that may call plugins/functions.
    """
    # Import inside function to show what's needed
    from observatory_config import (
        track_llm_call, cache, semantic_cache, prefix_cache, router,
        prompt_optimizer, streaming_detector, batch_detector, judge,
        DEFAULT_MODEL, CURRENT_PHASE,
        create_cache_metadata, estimate_tokens, classify_error,
    )

    logger.info(f"Processing message: '{message[:50]}...'")
    start_time = time.time()

    # Update memory tracking (if using conversation memory)
    memory.turn_number += 1
    memory.request_id = f"{memory.conversation_id}_turn{memory.turn_number}"

    try:
        # Add user message to history
        history.add_user_message(message)

        # ═══════════════════════════════════════════════════════════════
        # STEP 1: Check exact cache
        # ═══════════════════════════════════════════════════════════════
        operation = "main_chat"  # TODO: Set your operation name
        cache_key_data = {"user_message": message, "turn": memory.turn_number}

        cached_response, cache_meta = cache.get(
            operation=operation,
            key_data=cache_key_data
        )

        if cached_response:  # None in baseline, actual response in optimized
            track_llm_call(
                operation=operation,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=1.0,
                success=True,
                response_text=cached_response,
                cache_metadata=cache_meta,
                agent_name="ChatAgent",
                agent_role="orchestrator",
                conversation_id=memory.conversation_id,
                turn_number=memory.turn_number,
                request_id=memory.request_id,
                trace_id=memory.conversation_id,
                environment=os.getenv("ENVIRONMENT", "development"),
                metadata={
                    "phase": CURRENT_PHASE,
                    "cache_hit": True,
                }
            )

            history.add_assistant_message(cached_response)
            logger.info(f"Cache hit! Skipped LLM call.")
            return cached_response

        # ═══════════════════════════════════════════════════════════════
        # STEP 2: Check semantic cache (if available)
        # ═══════════════════════════════════════════════════════════════
        if semantic_cache:
            result = semantic_cache.get(operation=operation, prompt=message)
            if result.hit:
                track_llm_call(
                    operation=operation,
                    prompt_tokens=0,
                    completion_tokens=0,
                    latency_ms=1.0,
                    success=True,
                    response_text=result.response,
                    cache_metadata=create_cache_metadata(
                        cache_hit=True,
                        similarity_score=result.similarity
                    ),
                    agent_name="ChatAgent",
                    agent_role="orchestrator",
                    conversation_id=memory.conversation_id,
                    turn_number=memory.turn_number,
                    request_id=memory.request_id,
                    trace_id=memory.conversation_id,
                    environment=os.getenv("ENVIRONMENT", "development"),
                    metadata={
                        "phase": CURRENT_PHASE,
                        "semantic_cache_hit": True,
                        "similarity": result.similarity,
                    }
                )

                history.add_assistant_message(result.response)
                logger.info(f"Semantic cache hit ({result.similarity:.1%} similar)!")
                return result.response

        # ═══════════════════════════════════════════════════════════════
        # STEP 3: Get optimized prompt and max_tokens
        # ═══════════════════════════════════════════════════════════════
        optimized_prompt, max_tokens_limit, prompt_meta = prompt_optimizer.get_optimized_prompt(
            operation=operation,
            default_prompt=system_prompt
        )
        # Returns: default in baseline, compressed in optimized

        # ═══════════════════════════════════════════════════════════════
        # STEP 4: Get routed model
        # ═══════════════════════════════════════════════════════════════
        routed_model, routing_meta = router.route(
            operation=operation,
            prompt_tokens=estimate_tokens(optimized_prompt),
            complexity=0.5  # Adjust based on operation complexity (0.0-1.0)
        )
        # Returns: default model in baseline, routed model in optimized

        # ═══════════════════════════════════════════════════════════════
        # STEP 5: Track prefix for prefix caching detection
        # ═══════════════════════════════════════════════════════════════
        prefix_cache.track_call(
            operation=operation,
            system_prompt=optimized_prompt,
            system_prompt_tokens=estimate_tokens(optimized_prompt),
        )

        # ═══════════════════════════════════════════════════════════════
        # STEP 6: Make LLM call
        # ═══════════════════════════════════════════════════════════════
        execution_settings.max_tokens = max_tokens_limit

        # Update system prompt if optimized
        if optimized_prompt != system_prompt and len(history.messages) > 0:
            if history.messages[0].role.value.lower() in ['system', 'developer']:
                history.messages[0].content = optimized_prompt

        llm_start_time = time.time()

        try:
            response = await chat_completion.get_chat_message_content(
                chat_history=history,
                settings=execution_settings,
                kernel=kernel,
            )

            latency_ms = (time.time() - llm_start_time) * 1000
            response_text = str(response)
            success = True
            error = None
            error_type = None
            error_code = None

        except Exception as e:
            latency_ms = (time.time() - llm_start_time) * 1000
            response_text = f"Error: {str(e)}"
            success = False
            error = str(e)

            error_info = classify_error(e, operation=operation)
            error_type = error_info['error_type']
            error_code = error_info['error_code']

            logger.error(f"LLM call failed: {error_type} - {error_code}")
            response = None

        # ═══════════════════════════════════════════════════════════════
        # STEP 7: Extract token usage
        # ═══════════════════════════════════════════════════════════════
        prompt_tokens = 0
        completion_tokens = 0
        time_to_first_token_ms = None

        if success and response and hasattr(response, 'metadata') and response.metadata:
            usage = response.metadata.get('usage')
            if usage:
                prompt_tokens = getattr(usage, 'prompt_tokens', 0)
                completion_tokens = getattr(usage, 'completion_tokens', 0)

            if response.metadata.get('is_streaming'):
                time_to_first_token_ms = response.metadata.get('time_to_first_token_ms')

        # ═══════════════════════════════════════════════════════════════
        # STEP 8: Detect streaming candidates
        # ═══════════════════════════════════════════════════════════════
        streaming_candidate = streaming_detector.check_call(
            operation=operation,
            latency_ms=latency_ms,
            completion_tokens=completion_tokens,
        )

        # ═══════════════════════════════════════════════════════════════
        # STEP 9: Cache the response (if successful)
        # ═══════════════════════════════════════════════════════════════
        if success:
            cache.set(
                operation=operation,
                key_data=cache_key_data,
                value=response_text
            )

            if semantic_cache:
                semantic_cache.set(
                    operation=operation,
                    prompt=message,
                    response=response_text
                )

        # ═══════════════════════════════════════════════════════════════
        # STEP 10: Track with Observatory (CRITICAL)
        # ═══════════════════════════════════════════════════════════════

        # LLM Judge evaluation (if enabled and successful)
        quality_eval = None
        if success:
            quality_eval = await judge.maybe_evaluate(
                operation=operation,
                prompt=message,
                response=response_text,
                llm_client=kernel,
            )

        track_llm_call(
            # Core metrics
            model_name=routed_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            agent_name="ChatAgent",
            agent_role="orchestrator",
            operation=operation,
            success=success,
            error=error,

            # Prompt content
            system_prompt=optimized_prompt,
            user_message=message,
            response_text=response_text,

            # Optimization tracking
            routing_decision=routing_meta,
            cache_metadata=cache_meta,
            quality_evaluation=quality_eval,
            prompt_metadata=prompt_meta,

            # Model configuration
            temperature=execution_settings.temperature,
            max_tokens=max_tokens_limit,
            top_p=getattr(execution_settings, 'top_p', None),

            # Token breakdown
            system_prompt_tokens=estimate_tokens(optimized_prompt),
            user_message_tokens=estimate_tokens(message),
            tool_definitions_tokens=tool_definitions_tokens,

            # Streaming
            time_to_first_token_ms=time_to_first_token_ms,

            # Error details
            error_type=error_type,
            error_code=error_code,

            # Conversation linking
            conversation_id=memory.conversation_id,
            turn_number=memory.turn_number,
            request_id=memory.request_id,

            # Observability
            trace_id=memory.conversation_id,
            environment=os.getenv("ENVIRONMENT", "development"),

            # Metadata - CRITICAL: Include phase
            metadata={
                "phase": CURRENT_PHASE,
                "judged": quality_eval is not None,
                "streaming_candidate": streaming_candidate,
            }
        )

        # ═══════════════════════════════════════════════════════════════
        # STEP 11: Track batch detection
        # ═══════════════════════════════════════════════════════════════
        batch_detector.track_call(
            operation=operation,
            call_id=memory.request_id,
            latency_ms=latency_ms,
        )

        if success:
            history.add_message(response)

        return response_text

    except Exception as e:
        logger.error(f"Error in chat handler: {e}", exc_info=True)
        raise


# =============================================================================
# PATTERN 3: PLUGIN/FUNCTION PATTERN (Standalone LLM Call)
# =============================================================================
# Use this pattern for plugins or standalone functions that make LLM calls

async def plugin_llm_call_template(
    system_prompt: str,
    user_message: str,
    operation: str,
    chat_completion: Any,
    kernel: Any = None,
    memory: Any = None,
    cache_key_data: dict = None,
) -> dict:
    """
    Template for plugin/function LLM calls with full 10-step optimization.

    This is the WORKER pattern - used for specific LLM tasks like:
    - Resume scoring
    - Document analysis
    - SQL generation
    - etc.
    """
    from observatory_config import (
        track_llm_call, cache, semantic_cache, prefix_cache, router,
        prompt_optimizer, streaming_detector, judge,
        DEFAULT_MODEL, CURRENT_PHASE,
        create_prompt_breakdown, create_cache_metadata,
        estimate_tokens, classify_error,
    )

    # ═══════════════════════════════════════════════════════════════
    # INITIALIZE ALL VARIABLES (prevents undefined variable errors)
    # ═══════════════════════════════════════════════════════════════
    cache_meta = None
    routing_meta = None
    prompt_meta = None
    quality_eval = None
    streaming_candidate = False
    prompt_breakdown = None
    result_str = None
    latency_ms = 0
    prompt_tokens = 0
    completion_tokens = 0
    optimized_prompt = system_prompt
    max_tokens_limit = 1500
    routed_model = DEFAULT_MODEL

    try:
        # ═══════════════════════════════════════════════════════════════
        # STEP 1: Check exact cache
        # ═══════════════════════════════════════════════════════════════
        if cache_key_data:
            cached_result, cache_meta = cache.get(
                operation=operation,
                key_data=cache_key_data
            )

            if isinstance(cache_meta, dict) and not cache_meta:
                cache_meta = None

            if cached_result:
                logger.debug(f"Cache hit for operation {operation}")

                track_llm_call(
                    operation=operation,
                    prompt_tokens=0,
                    completion_tokens=0,
                    latency_ms=1.0,
                    success=True,
                    response_text=cached_result,
                    cache_metadata=cache_meta,
                    agent_name="PluginAgent",
                    agent_role="analyst",
                    conversation_id=memory.conversation_id if memory else None,
                    turn_number=memory.turn_number if memory else None,
                    parent_call_id=memory.request_id if memory else None,
                    request_id=str(uuid.uuid4()),
                    trace_id=memory.conversation_id if memory else None,
                    environment=os.getenv("ENVIRONMENT", "development"),
                    metadata={
                        "phase": CURRENT_PHASE,
                        "cache_hit": True,
                    }
                )

                return {"response": cached_result, "cached": True}

        # ═══════════════════════════════════════════════════════════════
        # STEP 2: Check semantic cache (if available)
        # ═══════════════════════════════════════════════════════════════
        full_prompt = f"{system_prompt}\n\n{user_message}"

        if semantic_cache:
            result = await semantic_cache.get(operation=operation, prompt=full_prompt)
            if result.hit:
                logger.debug(f"Semantic cache hit ({result.similarity:.1%})")

                track_llm_call(
                    operation=operation,
                    prompt_tokens=0,
                    completion_tokens=0,
                    latency_ms=1.0,
                    success=True,
                    response_text=result.response,
                    cache_metadata=create_cache_metadata(
                        cache_hit=True,
                        similarity_score=result.similarity
                    ),
                    agent_name="PluginAgent",
                    agent_role="analyst",
                    conversation_id=memory.conversation_id if memory else None,
                    turn_number=memory.turn_number if memory else None,
                    parent_call_id=memory.request_id if memory else None,
                    request_id=str(uuid.uuid4()),
                    trace_id=memory.conversation_id if memory else None,
                    environment=os.getenv("ENVIRONMENT", "development"),
                    metadata={
                        "phase": CURRENT_PHASE,
                        "semantic_cache_hit": True,
                        "similarity": result.similarity,
                    }
                )

                return {"response": result.response, "cached": True, "semantic": True}

        # ═══════════════════════════════════════════════════════════════
        # STEP 3: Get optimized prompt and max_tokens
        # ═══════════════════════════════════════════════════════════════
        optimized_prompt, max_tokens_limit, prompt_meta = prompt_optimizer.get_optimized_prompt(
            operation=operation,
            default_prompt=system_prompt
        )

        # Passthrough: if optimizer returns None, use original
        if optimized_prompt is None:
            optimized_prompt = system_prompt
        if max_tokens_limit is None:
            max_tokens_limit = 1500

        # ═══════════════════════════════════════════════════════════════
        # STEP 4: Get routed model
        # ═══════════════════════════════════════════════════════════════
        routed_model, routing_meta = router.select(
            operation=operation,
            prompt=optimized_prompt + user_message,
            estimated_tokens=estimate_tokens(optimized_prompt + user_message),
            complexity=0.5  # TODO: Adjust per operation
        )

        # ═══════════════════════════════════════════════════════════════
        # STEP 5: Track prefix for prefix caching detection
        # ═══════════════════════════════════════════════════════════════
        prefix_cache.track_call(
            operation=operation,
            system_prompt=optimized_prompt,
            system_prompt_tokens=estimate_tokens(optimized_prompt),
        )

        # ═══════════════════════════════════════════════════════════════
        # STEP 6: Make LLM call
        # ═══════════════════════════════════════════════════════════════
        from semantic_kernel.contents import ChatHistory
        from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
            AzureChatPromptExecutionSettings,
        )

        # Create isolated chat history (doesn't inherit system prompt)
        call_history = ChatHistory()
        call_history.add_system_message(optimized_prompt)
        call_history.add_user_message(user_message)

        # Create ISOLATED execution settings WITHOUT function calling
        call_settings = AzureChatPromptExecutionSettings()
        call_settings.max_tokens = max_tokens_limit
        call_settings.temperature = 0.3  # TODO: Adjust per operation
        # NO function_choice_behavior - pure completion

        llm_start_time = time.time()
        result = await chat_completion.get_chat_message_content(
            chat_history=call_history,
            settings=call_settings,
            # NOTE: NOT passing kernel to prevent function calling
        )
        latency_ms = (time.time() - llm_start_time) * 1000

        result_str = str(result)

        # Extract token usage
        if hasattr(result, 'metadata') and result.metadata:
            usage = result.metadata.get('usage')
            if usage:
                if hasattr(usage, 'prompt_tokens'):
                    prompt_tokens = usage.prompt_tokens or 0
                    completion_tokens = usage.completion_tokens or 0
                elif isinstance(usage, dict):
                    prompt_tokens = usage.get('prompt_tokens', 0)
                    completion_tokens = usage.get('completion_tokens', 0)

        # Fallback estimation
        if not prompt_tokens:
            prompt_tokens = estimate_tokens(optimized_prompt + user_message)
        if not completion_tokens:
            completion_tokens = estimate_tokens(result_str)

        # ═══════════════════════════════════════════════════════════════
        # STEP 7: Detect streaming candidates
        # ═══════════════════════════════════════════════════════════════
        streaming_candidate = streaming_detector.check_call(
            operation=operation,
            latency_ms=latency_ms,
            completion_tokens=completion_tokens,
        )

        # ═══════════════════════════════════════════════════════════════
        # STEP 8: Cache the response
        # ═══════════════════════════════════════════════════════════════
        if cache_key_data:
            cache.set(
                operation=operation,
                key_data=cache_key_data,
                value=result_str
            )

        if semantic_cache:
            await semantic_cache.set(
                operation=operation,
                prompt=full_prompt,
                response=result_str
            )

        # ═══════════════════════════════════════════════════════════════
        # STEP 9: Create prompt breakdown and evaluate quality
        # ═══════════════════════════════════════════════════════════════
        prompt_breakdown = create_prompt_breakdown(
            system_prompt=optimized_prompt,
            system_prompt_tokens=estimate_tokens(optimized_prompt),
            user_message=user_message,
            user_message_tokens=estimate_tokens(user_message),
        )

        # LLM Judge evaluation
        quality_eval = await judge.maybe_evaluate(
            operation=operation,
            prompt=full_prompt[:5000],
            response=result_str[:5000],
            llm_client=kernel,
            conversation_id=memory.conversation_id if memory else None,
            turn_number=memory.turn_number if memory else None,
        )

        # ═══════════════════════════════════════════════════════════════
        # STEP 10: Track with Observatory (CRITICAL)
        # ═══════════════════════════════════════════════════════════════
        track_llm_call(
            # Core metrics
            model_name=routed_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            agent_name="PluginAgent",  # TODO: Update for your plugin
            agent_role="analyst",
            operation=operation,
            success=True,

            # Prompt content
            system_prompt=optimized_prompt,
            user_message=user_message,
            response_text=result_str,
            prompt_breakdown=prompt_breakdown,

            # Optimization tracking
            routing_decision=routing_meta,
            cache_metadata=None,
            quality_evaluation=quality_eval,
            prompt_metadata=None,

            # Model configuration
            temperature=0.3,  # TODO: Match your settings
            max_tokens=max_tokens_limit,

            # Token breakdown
            system_prompt_tokens=estimate_tokens(optimized_prompt),
            user_message_tokens=estimate_tokens(user_message),

            # Conversation linking
            conversation_id=memory.conversation_id if memory else None,
            turn_number=memory.turn_number if memory else None,
            parent_call_id=memory.request_id if memory else None,
            request_id=str(uuid.uuid4()),

            # Observability
            trace_id=memory.conversation_id if memory else None,
            environment=os.getenv("ENVIRONMENT", "development"),

            # Metadata - CRITICAL: Include phase
            metadata={
                "phase": CURRENT_PHASE,
                "judged": quality_eval is not None,
                "streaming_candidate": bool(streaming_candidate),
            }
        )

        logger.debug(f"LLM call complete: {latency_ms:.0f}ms, {prompt_tokens + completion_tokens} tokens")

        return {"response": result_str, "cached": False}

    except Exception as e:
        logger.error(f"Error in plugin LLM call: {e}")

        error_info = classify_error(e, operation=operation)

        track_llm_call(
            model_name=DEFAULT_MODEL,
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=0,
            agent_name="PluginAgent",
            agent_role="analyst",
            operation=operation,
            success=False,
            error=str(e),
            error_type=error_info['error_type'],
            error_code=error_info['error_code'],
            retry_count=0,
            conversation_id=memory.conversation_id if memory else None,
            turn_number=memory.turn_number if memory else None,
            parent_call_id=memory.request_id if memory else None,
            request_id=str(uuid.uuid4()),
            trace_id=memory.conversation_id if memory else None,
            environment=os.getenv("ENVIRONMENT", "development"),
            metadata={
                "phase": CURRENT_PHASE,
                "error_type": error_info['error_type'],
            }
        )

        raise


# =============================================================================
# PATTERN 4: SIMPLE TRACKING (Non-LLM Operations)
# =============================================================================
# Use this pattern for tracking operations that DON'T make LLM calls
# (database reads, API calls, etc.)

def track_db_operation_template(
    operation: str,
    result_count: int,
    latency_ms: float,
    memory: Any = None,
    success: bool = True,
    error: str = None,
    metadata: dict = None,
):
    """
    Template for tracking non-LLM operations like database reads.

    Use this for:
    - Database queries
    - File operations
    - API calls to external services
    - etc.
    """
    from observatory_config import (
        track_llm_call, CURRENT_PHASE, classify_error,
    )

    # Merge custom metadata with defaults
    full_metadata = {
        "phase": CURRENT_PHASE,
        "result_count": result_count,
        "is_db_read": True,
    }
    if metadata:
        full_metadata.update(metadata)

    # Handle errors
    error_type = None
    error_code = None
    if not success and error:
        try:
            error_info = classify_error(Exception(error), operation=operation)
            error_type = error_info['error_type']
            error_code = error_info['error_code']
        except:
            error_type = "UnknownError"
            error_code = "UNKNOWN"

    track_llm_call(
        prompt_tokens=0,
        completion_tokens=0,
        latency_ms=latency_ms,
        agent_name="DatabasePlugin",  # TODO: Update for your plugin
        agent_role="retriever",
        operation=operation,
        success=success,
        error=error,
        error_type=error_type,
        error_code=error_code,
        conversation_id=memory.conversation_id if memory else None,
        turn_number=memory.turn_number if memory else None,
        parent_call_id=memory.request_id if memory else None,
        request_id=str(uuid.uuid4()),
        trace_id=memory.conversation_id if memory else None,
        environment=os.getenv("ENVIRONMENT", "development"),
        metadata=full_metadata,
    )


# =============================================================================
# PATTERN 5: PROMPT VERSIONING
# =============================================================================
# Best practice: Define prompt versions at the top of each plugin file

"""
# =============================================================================
# PROMPT VERSIONING - Bump version when prompt changes
# =============================================================================
OPERATION_NAME_PROMPT_VERSION = "1.0.0"

# Define your prompts as constants
OPERATION_NAME_SYSTEM_PROMPT = '''You are an expert at [task].

Analyze:
1. [Criterion 1]
2. [Criterion 2]
3. [Criterion 3]

CRITICAL: Return ONLY valid JSON. No markdown, no code blocks.

JSON format:
{
  "field1": "value",
  "field2": 123,
  "field3": ["item1", "item2"]
}'''

OPERATION_NAME_USER_TEMPLATE = '''Input Data:
{input_data}

Please analyze and respond.'''
"""


# =============================================================================
# QUICK REFERENCE: THE 10-STEP PATTERN
# =============================================================================
"""
Every LLM call should follow these 10 steps:

1. CHECK EXACT CACHE
   cached_result, cache_meta = cache.get(operation, key_data)

2. CHECK SEMANTIC CACHE
   result = semantic_cache.get(operation, prompt)

3. GET OPTIMIZED PROMPT
   optimized_prompt, max_tokens, prompt_meta = prompt_optimizer.get_optimized_prompt(operation, default_prompt)

4. GET ROUTED MODEL
   routed_model, routing_meta = router.route(operation, prompt_tokens, complexity)

5. TRACK PREFIX CACHE
   prefix_cache.track_call(operation, system_prompt, tokens)

6. MAKE LLM CALL
   result = await chat_completion.get_chat_message_content(...)

7. EXTRACT TOKENS / DETECT STREAMING
   streaming_candidate = streaming_detector.check_call(operation, latency, tokens)

8. CACHE RESPONSE
   cache.set(operation, key_data, value)
   semantic_cache.set(operation, prompt, response)

9. EVALUATE QUALITY
   quality_eval = await judge.maybe_evaluate(operation, prompt, response, client)

10. TRACK WITH OBSERVATORY
    track_llm_call(
        model_name=routed_model,
        prompt_tokens=...,
        completion_tokens=...,
        latency_ms=...,
        operation=operation,
        success=True,
        metadata={"phase": CURRENT_PHASE, ...}  # CRITICAL: Always include phase
    )

BONUS: TRACK BATCH DETECTION
    batch_detector.track_call(operation, call_id, latency_ms)
"""


# =============================================================================
# CRITICAL METADATA REQUIREMENTS
# =============================================================================
"""
ALWAYS include these in your metadata dict:

metadata={
    "phase": CURRENT_PHASE,  # CRITICAL - enables baseline vs optimized analysis

    # Optional but recommended:
    "judged": quality_eval is not None,
    "streaming_candidate": bool(streaming_candidate),
    "system_prompt_version": PROMPT_VERSION,  # Track prompt versions

    # Operation-specific (examples):
    "job_id": job.get('id'),
    "result_count": len(results),
    "cache_hit": True/False,
}
"""
