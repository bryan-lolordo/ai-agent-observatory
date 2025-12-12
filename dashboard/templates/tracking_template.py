# =============================================================================
# OBSERVATORY TRACKING TEMPLATE
# =============================================================================
#
# Copy the relevant sections into your AI plugin/service files.
# Works with observatory_config.py and the Observatory SDK.
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
    PromptMetadata
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
# 6. REFERENCE: Agent Roles
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
# 7. REFERENCE: Complexity Scores (for routing decisions)
# =============================================================================
#
# 0.1 - 0.3: Simple (DB lookups, formatting, list retrieval)
# 0.4 - 0.6: Medium (SQL generation, summarization, basic analysis)
# 0.7 - 0.9: Complex (deep analysis, creative writing, multi-step reasoning)
#
# =============================================================================


# =============================================================================
# 8. REFERENCE: track_llm_call Parameters
# =============================================================================
#
# TIER 1 - Core (always include):
#   model_name          str     Model used
#   prompt_tokens       int     Input tokens
#   completion_tokens   int     Output tokens  
#   latency_ms          float   Response time in ms
#   agent_name          str     Plugin/agent name
#   agent_role          str     See roles above
#   operation           str     Operation identifier
#   success             bool    True/False
#   error               str     Error message if failed
#
# TIER 2 - Prompt Analysis (for LLM calls):
#   prompt              str     Full prompt
#   response_text       str     Full response
#   system_prompt       str     System prompt separately
#   user_message        str     User message separately
#   messages            list    Chat history [{role, content}, ...]
#   prompt_metadata     obj     Version tracking
#   prompt_breakdown    obj     Token breakdown
#   quality_evaluation  obj     Judge result
#
# TIER 3 - Optimization (when preparing to optimize):
#   routing_decision    obj     Model routing info
#   cache_metadata      obj     Cache info
#   prompt_variant_id   str     A/B test variant
#   test_dataset_id     str     Evaluation dataset
#
# ALWAYS:
#   metadata            dict    Custom fields
#
# =============================================================================