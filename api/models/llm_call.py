"""
LLM Call Response Models
Location: api/models/llm_call.py

Models for LLM call details and lists.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# =============================================================================
# NESTED MODELS (Complex fields)
# =============================================================================

class PromptBreakdown(BaseModel):
    """Token breakdown for prompt components."""
    system_prompt_tokens: Optional[int] = None
    user_message_tokens: Optional[int] = None
    chat_history_tokens: Optional[int] = None
    conversation_context_tokens: Optional[int] = None
    tool_definitions_tokens: Optional[int] = None
    total_input_tokens: Optional[int] = None


class RoutingDecision(BaseModel):
    """Model routing decision metadata."""
    chosen_model: str
    complexity_score: Optional[float] = None
    reasoning: Optional[str] = None
    alternative_models: Optional[List[str]] = None
    estimated_cost_savings: Optional[float] = None


class CacheMetadata(BaseModel):
    """Cache hit/miss metadata."""
    cache_hit: bool
    cache_key: Optional[str] = None
    cache_cluster_id: Optional[str] = None
    similarity_score: Optional[float] = None
    ttl_seconds: Optional[int] = None


class QualityEvaluation(BaseModel):
    """LLM-as-judge quality evaluation."""
    judge_score: Optional[float] = Field(None, ge=0, le=10)
    reasoning: Optional[str] = None
    hallucination_flag: Optional[bool] = None
    error_category: Optional[str] = None
    confidence_score: Optional[float] = None
    evidence_cited: Optional[bool] = None
    factual_error: Optional[bool] = None


# =============================================================================
# LLM CALL DETAIL
# =============================================================================

class LLMCallResponse(BaseModel):
    """Complete LLM call detail."""
    # Core fields
    id: str
    session_id: str
    timestamp: datetime
    call_type: str = "llm"
    provider: str
    model_name: str
    agent_name: str
    operation: str
    
    # Tokens & Cost
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_cost: float
    completion_cost: float
    total_cost: float
    latency_ms: float
    
    # Status
    success: bool
    error: Optional[str] = None
    error_type: Optional[str] = None
    
    # Content (optional - can be large)
    prompt: Optional[str] = None
    response_text: Optional[str] = None
    system_prompt: Optional[str] = None
    user_message: Optional[str] = None
    
    # Conversation tracking
    conversation_id: Optional[str] = None
    turn_number: Optional[int] = None
    user_id: Optional[str] = None
    
    # Metadata objects
    prompt_breakdown: Optional[PromptBreakdown] = None
    routing_decision: Optional[RoutingDecision] = None
    cache_metadata: Optional[CacheMetadata] = None
    quality_evaluation: Optional[QualityEvaluation] = None
    
    # Configuration
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    
    # Observability
    environment: Optional[str] = None
    trace_id: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "call_123",
                "session_id": "sess_456",
                "timestamp": "2024-12-14T10:30:00Z",
                "provider": "AZURE",
                "model_name": "gpt-4o-mini",
                "agent_name": "DatabaseQuery",
                "operation": "generate_sql",
                "prompt_tokens": 200,
                "completion_tokens": 50,
                "total_tokens": 250,
                "prompt_cost": 0.0003,
                "completion_cost": 0.0003,
                "total_cost": 0.0006,
                "latency_ms": 850,
                "success": True,
                "conversation_id": "conv_789",
                "turn_number": 1
            }
        }


class LLMCallSummary(BaseModel):
    """Lightweight LLM call summary (for lists)."""
    id: str
    timestamp: datetime
    call_type: str = "llm"
    operation: str
    model_name: str
    total_cost: float
    latency_ms: float
    success: bool
    prompt_tokens: int
    completion_tokens: int


# =============================================================================
# LIST RESPONSES
# =============================================================================

class LLMCallListResponse(BaseModel):
    """List of LLM calls."""
    calls: List[LLMCallSummary]
    total: int
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        schema_extra = {
            "example": {
                "calls": [],
                "total": 175,
                "filters_applied": {
                    "project": "career_copilot",
                    "days": 7,
                    "operation": "generate_sql"
                }
            }
        }


class CallsByOperationResponse(BaseModel):
    """Calls grouped by operation."""
    operation: str
    call_count: int
    avg_latency_ms: float
    avg_cost: float
    total_cost: float
    calls: List[LLMCallSummary]