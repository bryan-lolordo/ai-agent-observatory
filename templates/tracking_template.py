# =============================================================================
# OBSERVATORY TRACKING TEMPLATE
# =============================================================================
#
# Copy the relevant sections into your AI plugin/service files.
# Works with observatory_config.py and the Observatory SDK.
#
# UPDATED: Now includes patterns for all 139 fields including conversation
#          linking, token breakdown, tool tracking, model config, streaming,
#          error handling, experiments, and observability.
#
# =============================================================================


# =============================================================================
# 1. IMPORTS - Add to top of file
# =============================================================================

from semantic_kernel.functions import kernel_function  # Or your framework
from typing import Annotated
import json
import logging
import os
import time
import uuid

# Observatory Integration
from observatory_config import (
    start_session,
    end_session,
    track_llm_call,
    create_prompt_metadata,
    create_prompt_breakdown,
    create_routing_decision,
    create_cache_metadata,
    judge,
    DEFAULT_MODEL,
    PromptMetadata,
    ModelConfig,          # NEW
    StreamingMetrics,     # NEW
    ExperimentMetadata,   # NEW
    ErrorDetails,         # NEW
)

logger = logging.getLogger(__name__)


# =============================================================================
# 2. PROMPT VERSIONING - Add after imports
# =============================================================================
# Bump version when you change prompts (MAJOR.MINOR.PATCH)

MY_OPERATION_VERSION = "1.0.0"

MY_OPERATION_META = create_prompt_metadata(
    template_id="my_plugin_operation",           # Unique ID for this prompt
    version=MY_OPERATION_VERSION,
    compressible_sections=["Context", "Rules"],  # Sections that could be shortened
    optimization_flags={"cacheable": True},      # Custom flags
    config_version="1.0"
) if PromptMetadata else None


# =============================================================================
# 3. PATTERN: Database/API Operation (No LLM)
# =============================================================================

async def db_operation_example(self, query: str) -> str:
    """Track non-LLM operations like DB reads, API calls."""
    
    start_time = time.time()
    
    try:
        # Your DB/API logic
        results = []  # self.db.query(...)
        response = json.dumps({"results": results})
        
        # Track successful operation
        track_llm_call(
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=(time.time() - start_time) * 1000,
            agent_name="MyPlugin",
            agent_role="retriever",
            operation="db_operation_example",
            success=True,
            prompt=f"Query: {query}",
            response_text=response[:500],
            metadata={
                "result_count": len(results),
                "is_db_read": True
            }
        )
        
        return response
        
    except Exception as e:
        # Track failed operation
        track_llm_call(
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=(time.time() - start_time) * 1000,
            agent_name="MyPlugin",
            agent_role="retriever",
            operation="db_operation_example",
            success=False,
            error=str(e),
            prompt=f"Query: {query}",
            metadata={"is_db_read": True, "error_type": type(e).__name__}
        )
        raise


# =============================================================================
# 4. PATTERN: LLM Operation with All Tiers
# =============================================================================

async def llm_operation_example(self, user_input: str) -> str:
    """Track LLM operations with full Tier 1, 2, 3 metrics."""
    
    # Build prompt
    system_prompt = """You are a helpful assistant.
    
Your task is to process the user's request.

RULES:
1. Be concise
2. Return valid JSON"""

    user_message = f"""Input: {user_input}

Return JSON:
{{"result": "your response"}}"""

    prompt = f"{system_prompt}\n\n{user_message}"
    
    try:
        # Make LLM call
        llm_start_time = time.time()
        result = await self.kernel.invoke_prompt(prompt)
        latency_ms = (time.time() - llm_start_time) * 1000
        result_str = str(result).strip()
        
        # Estimate tokens
        prompt_tokens = len(prompt) // 4
        completion_tokens = len(result_str) // 4
        
        # ----- Tier 2: Prompt Breakdown -----
        prompt_breakdown = create_prompt_breakdown(
            system_prompt=system_prompt,
            system_prompt_tokens=len(system_prompt) // 4,
            user_message=user_message,
            user_message_tokens=len(user_message) // 4,
        ) if create_prompt_breakdown else None
        
        # ----- Tier 2: Quality Evaluation -----
        quality_eval = await judge.maybe_evaluate(
            operation="llm_operation_example",
            prompt=prompt[:5000],
            response=result_str[:5000],
            llm_client=self.kernel,
        )
        
        # ----- Tier 3: Routing Decision -----
        routing_decision = create_routing_decision(
            chosen_model=DEFAULT_MODEL,
            alternative_models=["gpt-4o", "gpt-4o-mini"],
            reasoning="Standard task - using default model",
            complexity_score=0.5,
        ) if create_routing_decision else None
        
        # ----- Tier 3: Cache Metadata -----
        cache_metadata = create_cache_metadata(
            cache_hit=False,
            cache_key=None,
            cache_cluster_id="my_operation_cluster"
        ) if create_cache_metadata else None
        
        # ----- Track Complete Call -----
        track_llm_call(
            # Tier 1: Core metrics
            model_name=DEFAULT_MODEL,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            agent_name="MyPlugin",
            agent_role="analyst",
            operation="llm_operation_example",
            success=True,
            
            # Tier 2: Prompt content
            system_prompt=system_prompt,
            user_message=user_message,
            prompt=prompt,
            response_text=result_str,
            prompt_metadata=MY_OPERATION_META,
            prompt_breakdown=prompt_breakdown,
            
            # Tier 2: Quality
            quality_evaluation=quality_eval,
            
            # Tier 3: Optimization
            routing_decision=routing_decision,
            cache_metadata=cache_metadata,
            
            # Tier 3: A/B Testing
            prompt_variant_id=None,
            test_dataset_id=None,
            
            # Custom metadata
            metadata={
                "input_length": len(user_input),
                "judged": quality_eval is not None
            }
        )
        
        return result_str
        
    except Exception as e:
        # Track failed LLM call
        track_llm_call(
            model_name=DEFAULT_MODEL,
            prompt_tokens=len(prompt) // 4 if 'prompt' in locals() else 0,
            completion_tokens=0,
            latency_ms=(time.time() - llm_start_time) * 1000 if 'llm_start_time' in locals() else 0,
            agent_name="MyPlugin",
            agent_role="analyst",
            operation="llm_operation_example",
            success=False,
            error=str(e),
            prompt=prompt if 'prompt' in locals() else None,
            prompt_metadata=MY_OPERATION_META,
            metadata={"input_length": len(user_input), "error_type": type(e).__name__}
        )
        raise


# =============================================================================
# 5. PATTERN: Session-Wrapped Multi-Step Operation
# =============================================================================

async def multi_step_operation(self, items: list) -> dict:
    """Wrap multiple related calls in a session."""
    
    session = start_session("multi_step_operation", metadata={
        "item_count": len(items)
    })
    
    results = []
    
    try:
        for item in items:
            # Each call is tracked individually (they share the session)
            result = await self.process_single_item(item)
            results.append(result)
        
        end_session(session, success=True)
        return {"results": results}
        
    except Exception as e:
        end_session(session, success=False, error=str(e))
        raise


# =============================================================================
# 6. NEW PATTERN: Multi-Turn Conversation Tracking
# =============================================================================

async def conversation_example(self, user_id: str, messages: list) -> str:
    """
    Track multi-turn conversations with conversation_id and turn_number.
    
    Use this pattern for chatbots, assistants, or any multi-turn interaction.
    """
    
    # Generate or retrieve conversation ID
    conversation_id = str(uuid.uuid4())  # Or load from session/database
    turn_number = len(messages)  # Current turn
    
    # Build context from conversation history
    chat_history = messages[:-1]  # Previous messages
    current_message = messages[-1]["content"]
    
    system_prompt = "You are a helpful AI assistant."
    
    # Calculate tokens for each component
    system_tokens = len(system_prompt) // 4
    history_tokens = sum(len(m["content"]) // 4 for m in chat_history)
    user_tokens = len(current_message) // 4
    
    # Build full prompt
    prompt = f"{system_prompt}\n\n"
    for msg in chat_history:
        prompt += f"{msg['role']}: {msg['content']}\n"
    prompt += f"user: {current_message}\nassistant:"
    
    try:
        # Make LLM call
        start_time = time.time()
        result = await self.kernel.invoke_prompt(prompt)
        latency_ms = (time.time() - start_time) * 1000
        response = str(result).strip()
        
        # Track with conversation linking
        track_llm_call(
            model_name=DEFAULT_MODEL,
            prompt_tokens=system_tokens + history_tokens + user_tokens,
            completion_tokens=len(response) // 4,
            latency_ms=latency_ms,
            agent_name="ChatAgent",
            agent_role="writer",
            operation="chat_response",
            success=True,
            
            # Conversation linking - NEW
            conversation_id=conversation_id,
            turn_number=turn_number,
            user_id=user_id,
            
            # Token breakdown - NEW
            system_prompt_tokens=system_tokens,
            user_message_tokens=user_tokens,
            chat_history_tokens=history_tokens,
            
            # Prompt content
            system_prompt=system_prompt,
            user_message=current_message,
            messages=messages,
            response_text=response,
            
            metadata={
                "conversation_length": turn_number,
                "history_message_count": len(chat_history),
            }
        )
        
        return response
        
    except Exception as e:
        track_llm_call(
            model_name=DEFAULT_MODEL,
            prompt_tokens=system_tokens + history_tokens + user_tokens,
            completion_tokens=0,
            latency_ms=(time.time() - start_time) * 1000,
            agent_name="ChatAgent",
            agent_role="writer",
            operation="chat_response",
            success=False,
            error=str(e),
            conversation_id=conversation_id,
            turn_number=turn_number,
            user_id=user_id,
        )
        raise


# =============================================================================
# 7. NEW PATTERN: Tool/Function Calling Tracking
# =============================================================================

async def tool_calling_example(self, query: str) -> str:
    """
    Track LLM calls with tool/function calling.
    
    Use this pattern when using Semantic Kernel plugins, OpenAI functions, etc.
    """
    
    # Define tools/functions available
    tools = [
        {"type": "function", "name": "search_database", "description": "Search the database"},
        {"type": "function", "name": "calculate", "description": "Perform calculations"},
    ]
    
    # Estimate tool definition tokens
    tool_tokens = sum(len(json.dumps(t)) // 4 for t in tools)
    
    system_prompt = "You are an AI with access to tools."
    prompt_tokens = len(system_prompt) // 4 + len(query) // 4 + tool_tokens
    
    # Make LLM call (with tool calling)
    start_time = time.time()
    
    try:
        # Simulate tool calls
        tool_start = time.time()
        tool_results = [
            {"tool": "search_database", "result": "Found 5 items", "time_ms": 45},
            {"tool": "calculate", "result": "Result: 42", "time_ms": 10},
        ]
        total_tool_time = (time.time() - tool_start) * 1000
        
        # Get final response
        result = await self.kernel.invoke_prompt(query)
        latency_ms = (time.time() - start_time) * 1000
        response = str(result).strip()
        
        # Track with tool metrics - NEW
        track_llm_call(
            model_name=DEFAULT_MODEL,
            prompt_tokens=prompt_tokens,
            completion_tokens=len(response) // 4,
            latency_ms=latency_ms,
            agent_name="ToolAgent",
            agent_role="orchestrator",
            operation="tool_calling_example",
            success=True,
            
            # Tool tracking - NEW
            tool_calls_made=tool_results,
            tool_call_count=len(tool_results),
            tool_execution_time_ms=total_tool_time,
            tool_definitions_tokens=tool_tokens,
            
            # Token breakdown
            system_prompt_tokens=len(system_prompt) // 4,
            user_message_tokens=len(query) // 4,
            
            system_prompt=system_prompt,
            user_message=query,
            response_text=response,
            
            metadata={
                "tools_available": len(tools),
                "tools_used": len(tool_results),
            }
        )
        
        return response
        
    except Exception as e:
        track_llm_call(
            model_name=DEFAULT_MODEL,
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            latency_ms=(time.time() - start_time) * 1000,
            agent_name="ToolAgent",
            agent_role="orchestrator",
            operation="tool_calling_example",
            success=False,
            error=str(e),
            tool_definitions_tokens=tool_tokens,
        )
        raise


# =============================================================================
# 8. NEW PATTERN: Model Configuration Tracking
# =============================================================================

async def model_config_example(self, prompt: str, temp: float = 0.7) -> str:
    """
    Track model configuration parameters.
    
    Use this when experimenting with temperature, max_tokens, top_p, etc.
    """
    
    # Model settings
    temperature = temp
    max_tokens = 1000
    top_p = 0.9
    
    try:
        start_time = time.time()
        
        # Make call with specific config
        result = await self.kernel.invoke_prompt(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency_ms = (time.time() - start_time) * 1000
        response = str(result).strip()
        
        # Track with model config - NEW
        track_llm_call(
            model_name=DEFAULT_MODEL,
            prompt_tokens=len(prompt) // 4,
            completion_tokens=len(response) // 4,
            latency_ms=latency_ms,
            agent_name="ConfigAgent",
            agent_role="writer",
            operation="model_config_example",
            success=True,
            
            # Model configuration - NEW
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            
            prompt=prompt,
            response_text=response,
            
            metadata={
                "config_preset": "creative" if temperature > 0.8 else "balanced",
            }
        )
        
        return response
        
    except Exception as e:
        track_llm_call(
            model_name=DEFAULT_MODEL,
            prompt_tokens=len(prompt) // 4,
            completion_tokens=0,
            latency_ms=(time.time() - start_time) * 1000,
            agent_name="ConfigAgent",
            agent_role="writer",
            operation="model_config_example",
            success=False,
            error=str(e),
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
        )
        raise


# =============================================================================
# 9. NEW PATTERN: Complete Token Breakdown with Conversation Context
# =============================================================================

async def complete_token_breakdown_example(self, query: str, context_data: dict) -> str:
    """
    Track complete token breakdown including conversation context.
    
    Use this when you have:
    - System prompt
    - User message
    - Chat history
    - Conversation context (memory, state, preferences)
    - Tool definitions
    """
    
    # Build all prompt components
    system_prompt = "You are a helpful AI assistant."
    user_message = query
    chat_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"},
    ]
    
    # Conversation context (from ConversationMemory, user preferences, etc.)
    conversation_context = json.dumps({
        "user_preferences": context_data.get("preferences", {}),
        "session_state": context_data.get("state", {}),
        "relevant_memory": context_data.get("memory", []),
    })
    
    # Tool definitions
    tool_definitions = [
        {"name": "search", "description": "Search database"},
    ]
    
    # Calculate tokens for EACH component
    system_tokens = len(system_prompt) // 4
    user_tokens = len(user_message) // 4
    history_tokens = sum(len(m["content"]) // 4 for m in chat_history)
    context_tokens = len(conversation_context) // 4
    tool_tokens = len(json.dumps(tool_definitions)) // 4
    
    total_prompt_tokens = system_tokens + user_tokens + history_tokens + context_tokens + tool_tokens
    
    # Build full prompt
    full_prompt = f"{system_prompt}\n\nContext: {conversation_context}\n\nHistory:\n"
    for msg in chat_history:
        full_prompt += f"{msg['role']}: {msg['content']}\n"
    full_prompt += f"\nUser: {user_message}\nAssistant:"
    
    try:
        start_time = time.time()
        result = await self.kernel.invoke_prompt(full_prompt)
        latency_ms = (time.time() - start_time) * 1000
        response = str(result).strip()
        
        # Create enhanced prompt breakdown
        prompt_breakdown = create_prompt_breakdown(
            system_prompt=system_prompt,
            system_prompt_tokens=system_tokens,
            user_message=user_message,
            user_message_tokens=user_tokens,
            chat_history=chat_history,
            chat_history_tokens=history_tokens,
            conversation_context=conversation_context,            # NEW
            conversation_context_tokens=context_tokens,           # NEW
            tool_definitions=tool_definitions,                     # NEW
            tool_definitions_tokens=tool_tokens,                   # NEW
        )
        
        # Track with complete breakdown - NEW
        track_llm_call(
            model_name=DEFAULT_MODEL,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=len(response) // 4,
            latency_ms=latency_ms,
            agent_name="ContextAgent",
            agent_role="analyst",
            operation="complete_breakdown_example",
            success=True,
            
            # Complete token breakdown - NEW
            system_prompt_tokens=system_tokens,
            user_message_tokens=user_tokens,
            chat_history_tokens=history_tokens,
            conversation_context_tokens=context_tokens,
            tool_definitions_tokens=tool_tokens,
            
            # Prompt components
            system_prompt=system_prompt,
            user_message=user_message,
            messages=chat_history,
            response_text=response,
            
            # Enhanced breakdown object
            prompt_breakdown=prompt_breakdown,
            
            metadata={
                "has_context": context_tokens > 0,
                "has_tools": tool_tokens > 0,
                "context_percentage": round(context_tokens / total_prompt_tokens * 100, 1),
            }
        )
        
        return response
        
    except Exception as e:
        track_llm_call(
            model_name=DEFAULT_MODEL,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=0,
            latency_ms=(time.time() - start_time) * 1000,
            agent_name="ContextAgent",
            agent_role="analyst",
            operation="complete_breakdown_example",
            success=False,
            error=str(e),
            system_prompt_tokens=system_tokens,
            conversation_context_tokens=context_tokens,
        )
        raise


# =============================================================================
# 10. NEW PATTERN: A/B Testing / Experiment Tracking
# =============================================================================

async def ab_testing_example(self, query: str, experiment_config: dict) -> str:
    """
    Track A/B test experiments.
    
    Use this when running prompt experiments, model comparisons, etc.
    """
    
    experiment_id = experiment_config.get("experiment_id", "exp_001")
    variant = experiment_config.get("variant", "control")
    is_control = variant == "control"
    
    # Different prompts based on variant
    if is_control:
        system_prompt = "You are a helpful assistant."  # Control
    else:
        system_prompt = "You are an expert assistant with deep knowledge."  # Variant
    
    try:
        start_time = time.time()
        result = await self.kernel.invoke_prompt(f"{system_prompt}\n\n{query}")
        latency_ms = (time.time() - start_time) * 1000
        response = str(result).strip()
        
        # Track with experiment metadata - NEW
        track_llm_call(
            model_name=DEFAULT_MODEL,
            prompt_tokens=len(system_prompt) // 4 + len(query) // 4,
            completion_tokens=len(response) // 4,
            latency_ms=latency_ms,
            agent_name="ExperimentAgent",
            agent_role="writer",
            operation="ab_testing_example",
            success=True,
            
            # Experiment tracking - NEW
            experiment_id=experiment_id,
            control_group=is_control,
            prompt_variant_id=variant,
            
            system_prompt=system_prompt,
            user_message=query,
            response_text=response,
            
            metadata={
                "experiment_name": experiment_config.get("name", "Unknown"),
                "variant": variant,
            }
        )
        
        return response
        
    except Exception as e:
        track_llm_call(
            model_name=DEFAULT_MODEL,
            prompt_tokens=len(system_prompt) // 4 + len(query) // 4,
            completion_tokens=0,
            latency_ms=(time.time() - start_time) * 1000,
            agent_name="ExperimentAgent",
            agent_role="writer",
            operation="ab_testing_example",
            success=False,
            error=str(e),
            experiment_id=experiment_id,
            control_group=is_control,
        )
        raise


# =============================================================================
# 11. NEW PATTERN: Enhanced Error Tracking
# =============================================================================

async def error_tracking_example(self, query: str) -> str:
    """
    Track detailed error information with retry logic.
    
    Use this for production systems with retry handling.
    """
    
    max_retries = 3
    retry_count = 0
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            start_time = time.time()
            result = await self.kernel.invoke_prompt(query)
            latency_ms = (time.time() - start_time) * 1000
            response = str(result).strip()
            
            # Track successful call (possibly after retries)
            track_llm_call(
                model_name=DEFAULT_MODEL,
                prompt_tokens=len(query) // 4,
                completion_tokens=len(response) // 4,
                latency_ms=latency_ms,
                agent_name="ErrorAgent",
                agent_role="writer",
                operation="error_tracking_example",
                success=True,
                
                # Error tracking (even on success if retried) - NEW
                retry_count=retry_count,
                
                prompt=query,
                response_text=response,
                
                metadata={
                    "had_retries": retry_count > 0,
                    "final_attempt": attempt + 1,
                }
            )
            
            return response
            
        except Exception as e:
            retry_count += 1
            last_error = e
            error_type = type(e).__name__
            
            # Determine error code
            error_code = None
            if hasattr(e, 'status_code'):
                error_code = str(e.status_code)
            elif "429" in str(e) or "rate limit" in str(e).lower():
                error_code = "429"
                error_type = "RATE_LIMIT"
            elif "timeout" in str(e).lower():
                error_type = "TIMEOUT"
            
            # Track failed attempt
            if attempt == max_retries:
                # Final failure
                track_llm_call(
                    model_name=DEFAULT_MODEL,
                    prompt_tokens=len(query) // 4,
                    completion_tokens=0,
                    latency_ms=(time.time() - start_time) * 1000,
                    agent_name="ErrorAgent",
                    agent_role="writer",
                    operation="error_tracking_example",
                    success=False,
                    error=str(last_error),
                    
                    # Enhanced error tracking - NEW
                    error_type=error_type,
                    error_code=error_code,
                    retry_count=retry_count,
                    
                    prompt=query,
                    
                    metadata={
                        "max_retries_exceeded": True,
                        "retry_strategy": "exponential_backoff",
                    }
                )
                raise last_error
            
            # Wait before retry (exponential backoff)
            await asyncio.sleep(2 ** attempt)


# =============================================================================
# 12. NEW PATTERN: Observability with Trace IDs
# =============================================================================

async def observability_example(self, query: str, trace_context: dict) -> str:
    """
    Track with OpenTelemetry-style trace IDs for distributed tracing.
    
    Use this in production for end-to-end request tracking.
    """
    
    # Extract from request headers or generate
    trace_id = trace_context.get("trace_id") or str(uuid.uuid4())
    request_id = trace_context.get("request_id") or str(uuid.uuid4())
    environment = os.getenv("ENVIRONMENT", "development")
    
    try:
        start_time = time.time()
        result = await self.kernel.invoke_prompt(query)
        latency_ms = (time.time() - start_time) * 1000
        response = str(result).strip()
        
        # Track with observability fields - NEW
        track_llm_call(
            model_name=DEFAULT_MODEL,
            prompt_tokens=len(query) // 4,
            completion_tokens=len(response) // 4,
            latency_ms=latency_ms,
            agent_name="ObservableAgent",
            agent_role="writer",
            operation="observability_example",
            success=True,
            
            # Observability - NEW
            trace_id=trace_id,
            request_id=request_id,
            environment=environment,
            
            prompt=query,
            response_text=response,
            
            metadata={
                "service_name": "my-ai-service",
                "instance_id": os.getenv("INSTANCE_ID", "local"),
            }
        )
        
        return response
        
    except Exception as e:
        track_llm_call(
            model_name=DEFAULT_MODEL,
            prompt_tokens=len(query) // 4,
            completion_tokens=0,
            latency_ms=(time.time() - start_time) * 1000,
            agent_name="ObservableAgent",
            agent_role="writer",
            operation="observability_example",
            success=False,
            error=str(e),
            trace_id=trace_id,
            request_id=request_id,
            environment=environment,
        )
        raise


# =============================================================================
# 13. REFERENCE: Agent Roles
# =============================================================================
#
# analyst     - Analysis, scoring, evaluation
# reviewer    - Quality review, critique
# writer      - Content generation, creative
# retriever   - Data fetching, search
# planner     - Planning, strategy
# formatter   - Formatting, transformation
# fixer       - Error correction, improvement
# orchestrator - Coordination, routing
# custom      - Anything else
#
# =============================================================================


# =============================================================================
# 14. REFERENCE: Complexity Scores (for routing decisions)
# =============================================================================
#
# 0.1 - 0.3: Simple (DB lookups, formatting, list retrieval)
# 0.4 - 0.6: Medium (SQL generation, summarization, basic analysis)
# 0.7 - 0.9: Complex (deep analysis, creative writing, multi-step reasoning)
#
# =============================================================================


# =============================================================================
# 15. REFERENCE: Error Types
# =============================================================================
#
# RATE_LIMIT      - API rate limit exceeded (429)
# TIMEOUT         - Request timeout
# INVALID_REQUEST - Bad request (400)
# AUTH_ERROR      - Authentication failed (401, 403)
# SERVER_ERROR    - Server error (500, 503)
# NETWORK_ERROR   - Network/connection error
# VALIDATION      - Input validation error
# UNKNOWN         - Unclassified error
#
# =============================================================================


# =============================================================================
# 16. REFERENCE: track_llm_call Parameters (COMPLETE 139 FIELDS)
# =============================================================================
#
# TIER 1 - Core (always include):
#   model_name              str     Model used
#   prompt_tokens           int     Input tokens
#   completion_tokens       int     Output tokens  
#   latency_ms              float   Response time in ms
#   agent_name              str     Plugin/agent name
#   agent_role              str     See roles above
#   operation               str     Operation identifier
#   success                 bool    True/False
#   error                   str     Error message if failed
#
# TIER 2 - Prompt Analysis (for LLM calls):
#   prompt                  str     Full prompt
#   response_text           str     Full response
#   system_prompt           str     System prompt separately
#   user_message            str     User message separately
#   messages                list    Chat history [{role, content}, ...]
#   prompt_metadata         obj     Version tracking
#   prompt_breakdown        obj     Token breakdown
#   quality_evaluation      obj     Judge result
#
# TIER 3 - Optimization (when preparing to optimize):
#   routing_decision        obj     Model routing info
#   cache_metadata          obj     Cache info
#   prompt_variant_id       str     A/B test variant
#   test_dataset_id         str     Evaluation dataset
#
# NEW - CONVERSATION LINKING:
#   conversation_id         str     Links multi-turn conversations
#   turn_number             int     Turn position (1, 2, 3...)
#   parent_call_id          str     For retries/branches
#   user_id                 str     User identifier
#
# NEW - MODEL CONFIGURATION:
#   temperature             float   Model temperature
#   max_tokens              int     Max tokens limit
#   top_p                   float   Top-p sampling
#   model_config            obj     Full ModelConfig object
#
# NEW - TOKEN BREAKDOWN (Top-level for fast queries):
#   system_prompt_tokens    int     System prompt tokens
#   user_message_tokens     int     User message tokens
#   chat_history_tokens     int     Chat history tokens
#   conversation_context_tokens int Conversation context tokens
#   tool_definitions_tokens int     Tool schema tokens
#
# NEW - TOOL/FUNCTION CALLING:
#   tool_calls_made         list    Detailed tool calls
#   tool_call_count         int     Number of tools called
#   tool_execution_time_ms  float   Tool execution time
#
# NEW - STREAMING:
#   time_to_first_token_ms  float   TTFT for streaming
#   streaming_metrics       obj     Full StreamingMetrics object
#
# NEW - ERROR DETAILS:
#   error_type              str     Error classification
#   error_code              str     Provider error code
#   retry_count             int     Retry attempts
#   error_details           obj     Full ErrorDetails object
#
# NEW - CACHED TOKENS:
#   cached_prompt_tokens    int     Tokens from cache
#   cached_token_savings    float   Cost saved via cache
#
# NEW - OBSERVABILITY:
#   trace_id                str     OpenTelemetry trace ID
#   request_id              str     Provider request ID
#   environment             str     dev/staging/prod
#
# NEW - EXPERIMENT TRACKING:
#   experiment_id           str     A/B test experiment ID
#   control_group           bool    Is control group?
#   experiment_metadata     obj     Full ExperimentMetadata object
#
# ALWAYS:
#   metadata                dict    Custom fields
#
# =============================================================================