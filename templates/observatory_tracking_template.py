# =============================================================================
# OBSERVATORY TRACKING TEMPLATE
# =============================================================================
# 
# Location: career-copilot/templates/observatory_tracking_template.py
# 
# This template shows ALL Observatory monitoring capabilities.
# Copy relevant sections when adding tracking to new files.
#
# TRACKING TIERS:
#   Tier 1 (Core):     tokens, latency, cost, success/error
#   Tier 2 (Quality):  prompt_breakdown, prompt_metadata, quality_evaluation
#   Tier 3 (Optimize): routing_decision, cache_metadata, A/B testing
#
# =============================================================================


# =============================================================================
# SECTION 1: STANDARD IMPORTS
# =============================================================================

from semantic_kernel.functions import kernel_function
from typing import Annotated, Optional, Dict, List, Any
import json
import logging
import os
import time

# Observatory Integration - Complete imports
from observatory_config import (
    # Session management
    start_session,
    end_session,
    
    # Core tracking
    track_llm_call,
    
    # Tier 2: Prompt analysis
    create_prompt_metadata,
    create_prompt_breakdown,
    
    # Tier 3: Optimization tracking
    create_routing_decision,
    create_cache_metadata,
    
    # LLM Judge for quality evaluation
    judge,
    
    # Config values
    DEFAULT_MODEL,
    
    # Types (for type hints)
    PromptMetadata,
)


# =============================================================================
# SECTION 2: LOGGING CONFIGURATION
# =============================================================================

logger = logging.getLogger(__name__)

# Optional: Custom formatter for this module
# if not logger.handlers:
#     handler = logging.StreamHandler()
#     formatter = logging.Formatter("[%(name)s] %(levelname)s - %(message)s")
#     handler.setFormatter(formatter)
#     logger.addHandler(handler)
# logger.setLevel(logging.INFO)


# =============================================================================
# SECTION 3: PROMPT VERSIONING
# =============================================================================
# 
# Bump version when you change prompts!
# Format: MAJOR.MINOR.PATCH
#   MAJOR: Breaking changes to prompt structure
#   MINOR: New capabilities or significant changes
#   PATCH: Bug fixes, minor tweaks
#
# =============================================================================

MY_OPERATION_PROMPT_VERSION = "1.0.0"
ANOTHER_OPERATION_VERSION = "1.0.0"

# Create PromptMetadata for each distinct operation
MY_OPERATION_META = create_prompt_metadata(
    template_id="my_plugin_operation_name",      # Unique identifier
    version=MY_OPERATION_PROMPT_VERSION,         # Semantic version
    compressible_sections=["Context", "Rules"],  # Sections that could be compressed
    optimization_flags={                         # Custom flags for your operation
        "deterministic": False,
        "cacheable": True,
        "requires_context": True,
    },
    config_version="1.0"                         # Config schema version
) if PromptMetadata else None


# =============================================================================
# SECTION 4: AGENT ROLES REFERENCE
# =============================================================================
#
# Available agent roles (from AgentRole enum):
#   - "analyst"      → Analysis, scoring, evaluation tasks
#   - "reviewer"     → Quality review, critique tasks  
#   - "writer"       → Content generation, creative tasks
#   - "retriever"    → Data fetching, search tasks
#   - "planner"      → Planning, strategy tasks
#   - "formatter"    → Formatting, transformation tasks
#   - "fixer"        → Error correction, improvement tasks
#   - "orchestrator" → Coordination, routing tasks
#   - "custom"       → Anything else
#
# =============================================================================


# =============================================================================
# SECTION 5: COMPLEXITY SCORE REFERENCE
# =============================================================================
#
# Complexity scores (0.0 - 1.0) for routing decisions:
#
#   0.1 - 0.3: Simple tasks
#       - Database lookups
#       - Simple formatting
#       - List retrieval
#       - Basic transformations
#
#   0.4 - 0.6: Medium tasks  
#       - SQL generation
#       - Summarization
#       - Basic analysis
#       - Template filling
#
#   0.7 - 0.9: Complex tasks
#       - Deep analysis
#       - Creative writing
#       - Multi-step reasoning
#       - Quality-critical content
#
#   1.0: Maximum complexity
#       - Novel problem solving
#       - Complex multi-domain tasks
#
# =============================================================================


# =============================================================================
# SECTION 6: CLASS TEMPLATE
# =============================================================================

class MyPluginTemplate:
    """
    Template plugin demonstrating all Observatory tracking patterns.
    """
    
    def __init__(self, kernel, db_service=None, memory=None):
        """
        Initialize plugin with required dependencies.
        
        Args:
            kernel: Semantic Kernel instance for LLM calls
            db_service: Optional database service
            memory: Optional conversation memory
        """
        self.kernel = kernel
        self.db = db_service
        self.memory = memory
    
    # =========================================================================
    # PATTERN A: Full LLM Operation with All Tiers
    # =========================================================================
    
    @kernel_function(
        name="full_tracking_example",
        description="Example operation with complete Observatory tracking"
    )
    async def full_tracking_example(
        self,
        user_input: Annotated[str, "The user's input"],
        option: Annotated[str, "An optional parameter"] = "default"
    ) -> Annotated[str, "The operation result"]:
        """
        Full example showing all tracking capabilities.
        Use this pattern for important LLM operations.
        """
        
        logger.info(f"Starting full_tracking_example: {user_input[:50]}...")
        
        # ---------------------------------------------------------------------
        # Build prompt
        # ---------------------------------------------------------------------
        system_prompt = """You are a helpful assistant.

Your task is to process the user's request.

RULES:
1. Be concise
2. Be accurate
3. Return valid JSON"""

        user_message = f"""User Input: {user_input}
Option: {option}

Return JSON format:
{{
    "result": "your response here",
    "confidence": 0.95
}}"""

        full_prompt = f"{system_prompt}\n\n{user_message}"
        
        # ---------------------------------------------------------------------
        # Make LLM call
        # ---------------------------------------------------------------------
        llm_start_time = time.time()
        
        try:
            result = await self.kernel.invoke_prompt(full_prompt)
            
            latency_ms = (time.time() - llm_start_time) * 1000
            result_str = str(result).strip()
            
            # Estimate tokens (or extract from response metadata if available)
            prompt_tokens = len(full_prompt) // 4
            completion_tokens = len(result_str) // 4
            
            logger.info(f"LLM response received: {latency_ms:.0f}ms")
            
            # -----------------------------------------------------------------
            # Tier 2: Create prompt breakdown
            # -----------------------------------------------------------------
            prompt_breakdown = create_prompt_breakdown(
                system_prompt=system_prompt,
                system_prompt_tokens=len(system_prompt) // 4,
                user_message=user_message,
                user_message_tokens=len(user_message) // 4,
                chat_history=None,              # Include if using conversation history
                chat_history_tokens=None,
                chat_history_count=None,
            ) if create_prompt_breakdown else None
            
            # -----------------------------------------------------------------
            # Tier 2: LLM Judge evaluation (sampled)
            # -----------------------------------------------------------------
            quality_eval = await judge.maybe_evaluate(
                operation="full_tracking_example",   # Must match operation name
                prompt=full_prompt[:5000],           # Truncate for judge
                response=result_str[:5000],          # Truncate for judge
                llm_client=self.kernel,              # Required: LLM client
            )
            
            # -----------------------------------------------------------------
            # Tier 3: Routing decision
            # -----------------------------------------------------------------
            routing_decision = create_routing_decision(
                chosen_model=DEFAULT_MODEL,
                alternative_models=["gpt-4o", "gpt-4o-mini", "gpt-4"],
                reasoning="Medium complexity task - using default model",
                complexity_score=0.5,                # 0.0 - 1.0
                estimated_cost_savings=0.0,          # Optional: estimated savings
            ) if create_routing_decision else None
            
            # -----------------------------------------------------------------
            # Tier 3: Cache metadata
            # -----------------------------------------------------------------
            cache_metadata = create_cache_metadata(
                cache_hit=False,                     # Was this a cache hit?
                cache_key=f"example:{hash(user_input)}",  # Cache key used
                cache_cluster_id="my_operation",     # Group related caches
                ttl_seconds=3600,                    # Optional: TTL
            ) if create_cache_metadata else None
            
            # -----------------------------------------------------------------
            # Track in Observatory - COMPLETE
            # -----------------------------------------------------------------
            track_llm_call(
                # === Tier 1: Core Metrics ===
                model_name=DEFAULT_MODEL,            # Or extract from response
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                
                # === Context ===
                agent_name="MyPlugin",               # Your plugin/agent name
                agent_role="analyst",                # See AGENT ROLES REFERENCE
                operation="full_tracking_example",   # Operation identifier
                
                # === Status ===
                success=True,
                error=None,
                
                # === Prompt Content ===
                prompt=full_prompt,                  # Full prompt (or truncated)
                response_text=result_str,            # Full response (or truncated)
                system_prompt=system_prompt,         # Tracked separately
                user_message=user_message,           # Tracked separately
                messages=None,                       # For chat: [{role, content}, ...]
                
                # === Tier 2: Prompt Analysis ===
                prompt_metadata=MY_OPERATION_META,   # Version tracking
                prompt_breakdown=prompt_breakdown,   # Token breakdown
                
                # === Tier 2: Quality ===
                quality_evaluation=quality_eval,     # Judge result (may be None)
                
                # === Tier 3: Optimization ===
                routing_decision=routing_decision,
                cache_metadata=cache_metadata,
                
                # === Tier 3: A/B Testing ===
                prompt_variant_id=None,              # For prompt experiments
                test_dataset_id=None,                # For evaluation runs
                
                # === Custom Metadata ===
                metadata={
                    "user_input_length": len(user_input),
                    "option": option,
                    "custom_field": "any_value",
                    "judged": quality_eval is not None,
                }
            )
            
            logger.info(f"Tracked: {latency_ms:.0f}ms, ~{prompt_tokens + completion_tokens} tokens")
            
            # Clean and return result
            return self._clean_json_response(result_str)
            
        except Exception as e:
            # -----------------------------------------------------------------
            # Track failed call
            # -----------------------------------------------------------------
            logger.error(f"Error in full_tracking_example: {e}", exc_info=True)
            
            track_llm_call(
                model_name=DEFAULT_MODEL,
                prompt_tokens=len(full_prompt) // 4 if 'full_prompt' in locals() else 0,
                completion_tokens=0,
                latency_ms=(time.time() - llm_start_time) * 1000,
                
                agent_name="MyPlugin",
                agent_role="analyst",
                operation="full_tracking_example",
                
                success=False,                       # IMPORTANT: Mark as failed
                error=str(e),                        # Include error message
                
                prompt=full_prompt if 'full_prompt' in locals() else None,
                prompt_metadata=MY_OPERATION_META,
                
                # Omit optional fields for failed calls
                quality_evaluation=None,
                routing_decision=None,
                cache_metadata=None,
                
                metadata={
                    "user_input_length": len(user_input),
                    "error_type": type(e).__name__,
                }
            )
            
            raise
    
    # =========================================================================
    # PATTERN B: Simple Database/API Operation (No LLM)
    # =========================================================================
    
    @kernel_function(
        name="simple_db_operation",
        description="Example database operation tracking"
    )
    async def simple_db_operation(
        self,
        query: Annotated[str, "What to look up"]
    ) -> Annotated[str, "Query results"]:
        """
        Pattern for non-LLM operations (DB reads, API calls).
        Simpler tracking - just core metrics.
        """
        
        start_time = time.time()
        
        try:
            # Your database/API logic here
            results = []  # db.query(...)
            
            result = json.dumps({"results": results})
            
            # Track operation (minimal fields for non-LLM)
            track_llm_call(
                prompt_tokens=0,                     # No LLM tokens
                completion_tokens=0,
                latency_ms=(time.time() - start_time) * 1000,
                
                agent_name="MyPlugin",
                agent_role="retriever",              # DB operations are retriever
                operation="simple_db_operation",
                
                success=True,
                
                prompt=f"Query: {query}",            # Log what was requested
                response_text=result[:500],          # Truncate for storage
                
                # Skip Tier 2/3 for simple operations
                prompt_metadata=None,
                prompt_breakdown=None,
                quality_evaluation=None,
                routing_decision=None,
                cache_metadata=None,
                prompt_variant_id=None,
                test_dataset_id=None,
                
                metadata={
                    "query": query,
                    "results_count": len(results),
                    "is_db_read": True,
                }
            )
            
            return result
            
        except Exception as e:
            track_llm_call(
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=(time.time() - start_time) * 1000,
                agent_name="MyPlugin",
                agent_role="retriever",
                operation="simple_db_operation",
                success=False,
                error=str(e),
                metadata={"query": query, "is_db_read": True}
            )
            raise
    
    # =========================================================================
    # PATTERN C: Session-Wrapped Multi-Step Operation
    # =========================================================================
    
    async def multi_step_operation(self, items: List[str]) -> dict:
        """
        Pattern for operations with multiple LLM calls.
        Wrap in a session to group related calls.
        """
        
        # Start session to group all calls
        session = start_session(
            operation_type="multi_step_operation",
            metadata={
                "item_count": len(items),
                "started_at": time.time(),
            }
        )
        
        results = []
        errors = []
        
        try:
            for i, item in enumerate(items):
                try:
                    # Each call is tracked individually
                    result = await self._process_single_item(item, i + 1, len(items))
                    results.append(result)
                except Exception as e:
                    errors.append({"item": item, "error": str(e)})
            
            # End session successfully
            end_session(session, success=True)
            
            return {
                "results": results,
                "errors": errors,
                "success_rate": len(results) / len(items) if items else 0,
            }
            
        except Exception as e:
            # End session with error
            end_session(session, success=False, error=str(e))
            raise
    
    async def _process_single_item(self, item: str, index: int, total: int) -> dict:
        """Process a single item within a session."""
        
        llm_start_time = time.time()
        
        prompt = f"Process this item: {item}"
        result = await self.kernel.invoke_prompt(prompt)
        result_str = str(result)
        
        # Track each call - they're grouped by session
        track_llm_call(
            prompt_tokens=len(prompt) // 4,
            completion_tokens=len(result_str) // 4,
            latency_ms=(time.time() - llm_start_time) * 1000,
            agent_name="MyPlugin",
            agent_role="analyst",
            operation="process_single_item",
            success=True,
            prompt=prompt,
            response_text=result_str,
            metadata={
                "item_index": index,
                "total_items": total,
            }
        )
        
        return {"item": item, "result": result_str}
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _clean_json_response(self, response: str) -> str:
        """Clean LLM response to extract valid JSON."""
        result = response.strip()
        
        # Remove markdown code blocks
        if '```json' in result:
            result = result.split('```json')[1].split('```')[0].strip()
        elif '```' in result:
            result = result.split('```')[1].split('```')[0].strip()
        
        # Extract JSON object
        start_idx = result.find('{')
        end_idx = result.rfind('}')
        if start_idx != -1 and end_idx != -1:
            result = result[start_idx:end_idx + 1]
        
        return result


# =============================================================================
# SECTION 7: QUICK REFERENCE - TRACK_LLM_CALL PARAMETERS
# =============================================================================
#
# track_llm_call(
#     # Tier 1: Core (always include)
#     model_name=str,              # Model used (or DEFAULT_MODEL)
#     prompt_tokens=int,           # Input tokens
#     completion_tokens=int,       # Output tokens
#     latency_ms=float,            # Response time in ms
#     
#     # Context (always include)
#     agent_name=str,              # Plugin/agent name
#     agent_role=str,              # analyst|reviewer|writer|retriever|planner|formatter|fixer|orchestrator|custom
#     operation=str,               # Operation identifier
#     
#     # Status (always include)
#     success=bool,                # True/False
#     error=str|None,              # Error message if failed
#     
#     # Prompt content (include for LLM calls)
#     prompt=str,                  # Full prompt
#     response_text=str,           # Full response
#     system_prompt=str,           # System prompt separately
#     user_message=str,            # User message separately
#     messages=List[Dict],         # Chat history: [{role, content}, ...]
#     prompt_normalized=str,       # Normalized for caching
#     
#     # Tier 2: Quality (include for important operations)
#     prompt_metadata=PromptMetadata,     # Version tracking
#     prompt_breakdown=PromptBreakdown,   # Token breakdown
#     quality_evaluation=QualityEval,     # Judge result
#     
#     # Tier 3: Optimization (include when preparing for optimization)
#     routing_decision=RoutingDecision,   # Model routing info
#     cache_metadata=CacheMetadata,       # Cache info
#     
#     # Tier 3: A/B Testing (include for experiments)
#     prompt_variant_id=str,              # Prompt experiment ID
#     test_dataset_id=str,                # Evaluation dataset ID
#     
#     # Custom (always include)
#     metadata=dict,                      # Any custom fields
# )
#
# =============================================================================


# =============================================================================
# SECTION 8: JUDGE CONFIGURATION REFERENCE
# =============================================================================
#
# In observatory_config.py, judge is configured with:
#
# judge = LLMJudge(
#     operations={...},        # Operations TO evaluate
#     skip_operations={...},   # Operations to SKIP
#     sample_rate=0.5,         # Evaluate 50% of calls
#     criteria={...},          # Evaluation criteria with weights
#     domain_context="...",    # Domain context for judge
# )
#
# Usage:
#     quality_eval = await judge.maybe_evaluate(
#         operation="my_operation",      # Must be in operations set
#         prompt=prompt[:5000],
#         response=response[:5000],
#         llm_client=self.kernel,
#     )
#
# Returns None if:
#   - Operation is in skip_operations
#   - Operation not in operations
#   - Failed sample_rate check (e.g., 50% of calls skipped)
#
# =============================================================================


# =============================================================================
# SECTION 9: CACHE CLUSTER NAMING CONVENTIONS
# =============================================================================
#
# Use consistent cluster IDs to group related operations:
#
#   "job_search"        - Job search API results
#   "sql_generation"    - Generated SQL queries  
#   "resume_matching"   - Match scoring results
#   "resume_tailoring"  - Tailoring suggestions
#   "chat"              - Chat/conversation responses
#   "db_queries"        - Database query results
#   "analysis"          - Analysis/evaluation results
#   "critique"          - Quality critique results
#   "refinements"       - Refinement suggestions
#
# =============================================================================