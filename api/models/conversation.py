"""
Conversation Models
Location: api/models/conversation.py

Models for multi-turn conversation analysis.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ConversationTurn(BaseModel):
    """Single turn in a conversation."""
    turn_number: int
    call_id: str
    timestamp: datetime
    operation: str
    
    # Tokens
    prompt_tokens: int
    completion_tokens: int
    
    # Cost & latency
    total_cost: float
    latency_ms: float
    
    # Quality (if evaluated)
    quality_score: Optional[float] = None
    
    # Content previews
    user_message_preview: Optional[str] = None
    response_preview: Optional[str] = None


class ConversationDetail(BaseModel):
    """Multi-turn conversation detail."""
    conversation_id: str
    user_id: Optional[str] = None
    
    # Summary
    turn_count: int
    total_cost: float
    total_tokens: int
    duration_seconds: float
    
    # Status
    started_at: datetime
    ended_at: datetime
    completed: bool
    
    # Turns
    turns: List[ConversationTurn]
    
    # Metrics
    avg_latency_ms: float
    avg_quality_score: Optional[float] = None


class ConversationSummary(BaseModel):
    """Lightweight conversation summary."""
    conversation_id: str
    user_id: Optional[str] = None
    turn_count: int
    total_cost: float
    duration_seconds: float
    started_at: datetime
    avg_quality_score: Optional[float] = None


class ConversationListResponse(BaseModel):
    """List of conversations."""
    conversations: List[ConversationSummary]
    total: int


class ConversationMetrics(BaseModel):
    """Aggregate conversation metrics."""
    total_conversations: int
    avg_turns_per_conversation: float
    avg_cost_per_conversation: float
    avg_duration_seconds: float
    completion_rate: float
    
    # Quality
    avg_quality_score: Optional[float] = None
    
    # Distribution
    turns_distribution: Dict[str, int]  # "1-3", "4-6", "7+" -> count