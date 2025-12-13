# observatory/storage.py
# UPDATED: Complete database schema with all new fields for production observability


import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, JSON, Text, distinct
from sqlalchemy.orm import declarative_base, sessionmaker, Session as DBSession

from observatory.models import (
    Session, LLMCall, ModelProvider, AgentRole,
    RoutingDecision, CacheMetadata, QualityEvaluation,
    PromptBreakdown, PromptMetadata,
    ModelConfig, StreamingMetrics, ExperimentMetadata, ErrorDetails,
    RoutingMetrics, CacheMetrics
)


Base = declarative_base()


class SessionDB(Base):
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True)
    project_name = Column(String, index=True)
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime, nullable=True)
    
    # Basic aggregated metrics
    total_llm_calls = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    total_latency_ms = Column(Float, default=0.0)
    
    # Enhanced aggregated metrics - Routing
    total_routing_decisions = Column(Integer, default=0)
    routing_cost_savings = Column(Float, default=0.0)
    
    # Enhanced aggregated metrics - Caching
    total_cache_hits = Column(Integer, default=0)
    total_cache_misses = Column(Integer, default=0)
    cache_cost_savings = Column(Float, default=0.0)
    
    # Enhanced aggregated metrics - Quality
    avg_quality_score = Column(Float, nullable=True)
    total_hallucinations = Column(Integer, default=0)
    total_errors = Column(Integer, default=0)
    
    success = Column(Boolean, default=True)
    error = Column(Text, nullable=True)
    
    operation_type = Column(String, nullable=True, index=True)
    meta_data = Column(JSON, default={})


class LLMCallDB(Base):
    __tablename__ = "llm_calls"
    
    id = Column(String, primary_key=True)
    session_id = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    
    provider = Column(String, index=True)
    model_name = Column(String, index=True)
    
    # Prompt and response
    prompt = Column(Text, nullable=True)
    prompt_normalized = Column(Text, nullable=True)
    response_text = Column(Text, nullable=True)
    
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)
    
    prompt_cost = Column(Float)
    completion_cost = Column(Float)
    total_cost = Column(Float)
    
    latency_ms = Column(Float)
    
    agent_name = Column(String, nullable=True, index=True)
    agent_role = Column(String, nullable=True, index=True)
    operation = Column(String, nullable=True, index=True)
    
    success = Column(Boolean, default=True)
    error = Column(Text, nullable=True)
    
    # === NEW: CONVERSATION LINKING ===
    conversation_id = Column(String, nullable=True, index=True)
    turn_number = Column(Integer, nullable=True)
    parent_call_id = Column(String, nullable=True)
    user_id = Column(String, nullable=True, index=True)
    
    # === NEW: MODEL CONFIGURATION (top-level for common params) ===
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    top_p = Column(Float, nullable=True)
    
    # === NEW: TOKEN BREAKDOWN (promoted for query performance) ===
    system_prompt_tokens = Column(Integer, nullable=True, index=True)
    user_message_tokens = Column(Integer, nullable=True)
    chat_history_tokens = Column(Integer, nullable=True)
    conversation_context_tokens = Column(Integer, nullable=True)
    tool_definitions_tokens = Column(Integer, nullable=True)
    
    # === NEW: TOOL/FUNCTION CALLING ===
    tool_call_count = Column(Integer, nullable=True)
    tool_execution_time_ms = Column(Float, nullable=True)
    
    # === NEW: STREAMING ===
    time_to_first_token_ms = Column(Float, nullable=True)
    
    # === NEW: ERROR DETAILS ===
    error_type = Column(String, nullable=True, index=True)
    error_code = Column(String, nullable=True)
    retry_count = Column(Integer, nullable=True)
    
    # === NEW: CACHED TOKENS ===
    cached_prompt_tokens = Column(Integer, nullable=True)
    cached_token_savings = Column(Float, nullable=True)
    
    # === NEW: OBSERVABILITY ===
    trace_id = Column(String, nullable=True, index=True)
    request_id = Column(String, nullable=True)
    environment = Column(String, nullable=True, index=True)
    
    # === NEW: EXPERIMENT TRACKING ===
    experiment_id = Column(String, nullable=True, index=True)
    control_group = Column(Boolean, nullable=True)
    
    # === EXISTING: Enhanced fields (JSON) ===
    routing_decision = Column(JSON, nullable=True)
    cache_metadata = Column(JSON, nullable=True)
    quality_evaluation = Column(JSON, nullable=True)
    prompt_breakdown = Column(JSON, nullable=True)
    prompt_metadata = Column(JSON, nullable=True)
    
    # === NEW: Complex objects (JSON) ===
    model_config = Column(JSON, nullable=True)
    streaming_metrics = Column(JSON, nullable=True)
    experiment_metadata = Column(JSON, nullable=True)
    error_details = Column(JSON, nullable=True)
    tool_calls_made = Column(JSON, nullable=True)
    
    # === EXISTING: A/B Testing ===
    prompt_variant_id = Column(String, nullable=True, index=True)
    test_dataset_id = Column(String, nullable=True, index=True)
    
    meta_data = Column(JSON, default={})


class Storage:
    def __init__(self, database_url: Optional[str] = None):
        if database_url is None:
            database_url = os.getenv("DATABASE_URL", "sqlite:///observatory.db")
        
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    # =========================================================================
    # SESSION CONVERSION
    # =========================================================================

    def _to_session_db(self, session: Session) -> SessionDB:
        return SessionDB(
            id=session.id,
            project_name=session.project_name,
            start_time=session.start_time,
            end_time=session.end_time,
            total_llm_calls=session.total_llm_calls,
            total_tokens=session.total_tokens,
            total_cost=session.total_cost,
            total_latency_ms=session.total_latency_ms,
            total_routing_decisions=session.total_routing_decisions,
            routing_cost_savings=session.routing_cost_savings,
            total_cache_hits=session.total_cache_hits,
            total_cache_misses=session.total_cache_misses,
            cache_cost_savings=session.cache_cost_savings,
            avg_quality_score=session.avg_quality_score,
            total_hallucinations=session.total_hallucinations,
            total_errors=session.total_errors,
            success=session.success,
            error=session.error,
            operation_type=session.operation_type,
            meta_data=session.metadata,
        )

    def _from_session_db(self, session_db: SessionDB) -> Session:
        return Session(
            id=session_db.id,
            project_name=session_db.project_name,
            start_time=session_db.start_time,
            end_time=session_db.end_time,
            total_llm_calls=session_db.total_llm_calls,
            total_tokens=session_db.total_tokens,
            total_cost=session_db.total_cost,
            total_latency_ms=session_db.total_latency_ms,
            total_routing_decisions=session_db.total_routing_decisions,
            routing_cost_savings=session_db.routing_cost_savings,
            total_cache_hits=session_db.total_cache_hits,
            total_cache_misses=session_db.total_cache_misses,
            cache_cost_savings=session_db.cache_cost_savings,
            avg_quality_score=session_db.avg_quality_score,
            total_hallucinations=session_db.total_hallucinations,
            total_errors=session_db.total_errors,
            success=session_db.success,
            error=session_db.error,
            operation_type=session_db.operation_type,
            metadata=session_db.meta_data or {},
        )

    # =========================================================================
    # LLM CALL CONVERSION (UPDATED)
    # =========================================================================

    def _to_llm_call_db(self, llm_call: LLMCall) -> LLMCallDB:
        # Convert nested Pydantic models to dict for JSON storage
        routing_data = llm_call.routing_decision.model_dump() if llm_call.routing_decision else None
        cache_data = llm_call.cache_metadata.model_dump() if llm_call.cache_metadata else None
        quality_data = llm_call.quality_evaluation.model_dump() if llm_call.quality_evaluation else None
        breakdown_data = llm_call.prompt_breakdown.model_dump() if llm_call.prompt_breakdown else None
        metadata_data = llm_call.prompt_metadata.model_dump() if llm_call.prompt_metadata else None
        
        # NEW: Convert new model types
        model_config_data = llm_call.llm_config.model_dump() if llm_call.llm_config else None
        streaming_data = llm_call.streaming_metrics.model_dump() if llm_call.streaming_metrics else None
        experiment_data = llm_call.experiment_metadata.model_dump() if llm_call.experiment_metadata else None
        error_details_data = llm_call.error_details.model_dump() if llm_call.error_details else None
        
        return LLMCallDB(
            id=llm_call.id,
            session_id=llm_call.session_id,
            timestamp=llm_call.timestamp,
            provider=llm_call.provider.value,
            model_name=llm_call.model_name,
            prompt=llm_call.prompt,
            prompt_normalized=llm_call.prompt_normalized,
            response_text=llm_call.response_text,
            prompt_tokens=llm_call.prompt_tokens,
            completion_tokens=llm_call.completion_tokens,
            total_tokens=llm_call.total_tokens,
            prompt_cost=llm_call.prompt_cost,
            completion_cost=llm_call.completion_cost,
            total_cost=llm_call.total_cost,
            latency_ms=llm_call.latency_ms,
            agent_name=llm_call.agent_name,
            agent_role=llm_call.agent_role.value if llm_call.agent_role else None,
            operation=llm_call.operation,
            success=llm_call.success,
            error=llm_call.error,
            
            # NEW: Conversation linking
            conversation_id=llm_call.conversation_id,
            turn_number=llm_call.turn_number,
            parent_call_id=llm_call.parent_call_id,
            user_id=llm_call.user_id,
            
            # NEW: Model config (top-level)
            temperature=llm_call.temperature,
            max_tokens=llm_call.max_tokens,
            top_p=llm_call.top_p,
            
            # NEW: Token breakdown (promoted)
            system_prompt_tokens=llm_call.system_prompt_tokens,
            user_message_tokens=llm_call.user_message_tokens,
            chat_history_tokens=llm_call.chat_history_tokens,
            conversation_context_tokens=llm_call.conversation_context_tokens,
            tool_definitions_tokens=llm_call.tool_definitions_tokens,
            
            # NEW: Tool tracking
            tool_call_count=llm_call.tool_call_count,
            tool_execution_time_ms=llm_call.tool_execution_time_ms,
            
            # NEW: Streaming
            time_to_first_token_ms=llm_call.time_to_first_token_ms,
            
            # NEW: Error details
            error_type=llm_call.error_type,
            error_code=llm_call.error_code,
            retry_count=llm_call.retry_count,
            
            # NEW: Cached tokens
            cached_prompt_tokens=llm_call.cached_prompt_tokens,
            cached_token_savings=llm_call.cached_token_savings,
            
            # NEW: Observability
            trace_id=llm_call.trace_id,
            request_id=llm_call.request_id,
            environment=llm_call.environment,
            
            # NEW: Experiment tracking
            experiment_id=llm_call.experiment_id,
            control_group=llm_call.control_group,
            
            # Existing JSON fields
            routing_decision=routing_data,
            cache_metadata=cache_data,
            quality_evaluation=quality_data,
            prompt_breakdown=breakdown_data,
            prompt_metadata=metadata_data,
            
            # NEW: Complex objects (JSON)
            model_config=model_config_data,
            streaming_metrics=streaming_data,
            experiment_metadata=experiment_data,
            error_details=error_details_data,
            tool_calls_made=llm_call.tool_calls_made,
            
            # Existing A/B testing
            prompt_variant_id=llm_call.prompt_variant_id,
            test_dataset_id=llm_call.test_dataset_id,
            
            meta_data=llm_call.metadata,
        )

    def _from_llm_call_db(self, llm_call_db: LLMCallDB) -> LLMCall:
        # Convert JSON back to Pydantic models
        routing_decision = None
        if llm_call_db.routing_decision:
            routing_decision = RoutingDecision(**llm_call_db.routing_decision)
        
        cache_metadata = None
        if llm_call_db.cache_metadata:
            cache_metadata = CacheMetadata(**llm_call_db.cache_metadata)
        
        quality_evaluation = None
        if llm_call_db.quality_evaluation:
            quality_evaluation = QualityEvaluation(**llm_call_db.quality_evaluation)
        
        prompt_breakdown = None
        if llm_call_db.prompt_breakdown:
            prompt_breakdown = PromptBreakdown(**llm_call_db.prompt_breakdown)
        
        prompt_metadata = None
        if llm_call_db.prompt_metadata:
            prompt_metadata = PromptMetadata(**llm_call_db.prompt_metadata)
        
        # NEW: Convert new model types
        llm_config = None
        if llm_call_db.model_config:
            llm_config = ModelConfig(**llm_call_db.model_config)
        
        streaming_metrics = None
        if llm_call_db.streaming_metrics:
            streaming_metrics = StreamingMetrics(**llm_call_db.streaming_metrics)
        
        experiment_metadata = None
        if llm_call_db.experiment_metadata:
            experiment_metadata = ExperimentMetadata(**llm_call_db.experiment_metadata)
        
        error_details = None
        if llm_call_db.error_details:
            error_details = ErrorDetails(**llm_call_db.error_details)
        
        return LLMCall(
            id=llm_call_db.id,
            session_id=llm_call_db.session_id,
            timestamp=llm_call_db.timestamp,
            provider=ModelProvider(llm_call_db.provider),
            model_name=llm_call_db.model_name,
            prompt=llm_call_db.prompt,
            prompt_normalized=llm_call_db.prompt_normalized,
            response_text=llm_call_db.response_text,
            prompt_tokens=llm_call_db.prompt_tokens,
            completion_tokens=llm_call_db.completion_tokens,
            total_tokens=llm_call_db.total_tokens,
            prompt_cost=llm_call_db.prompt_cost,
            completion_cost=llm_call_db.completion_cost,
            total_cost=llm_call_db.total_cost,
            latency_ms=llm_call_db.latency_ms,
            agent_name=llm_call_db.agent_name,
            agent_role=AgentRole(llm_call_db.agent_role) if llm_call_db.agent_role else None,
            operation=llm_call_db.operation,
            success=llm_call_db.success,
            error=llm_call_db.error,
            
            # NEW: Conversation linking
            conversation_id=llm_call_db.conversation_id,
            turn_number=llm_call_db.turn_number,
            parent_call_id=llm_call_db.parent_call_id,
            user_id=llm_call_db.user_id,
            
            # NEW: Model config
            temperature=llm_call_db.temperature,
            max_tokens=llm_call_db.max_tokens,
            top_p=llm_call_db.top_p,
            
            # NEW: Token breakdown
            system_prompt_tokens=llm_call_db.system_prompt_tokens,
            user_message_tokens=llm_call_db.user_message_tokens,
            chat_history_tokens=llm_call_db.chat_history_tokens,
            conversation_context_tokens=llm_call_db.conversation_context_tokens,
            tool_definitions_tokens=llm_call_db.tool_definitions_tokens,
            
            # NEW: Tool tracking
            tool_call_count=llm_call_db.tool_call_count,
            tool_execution_time_ms=llm_call_db.tool_execution_time_ms,
            
            # NEW: Streaming
            time_to_first_token_ms=llm_call_db.time_to_first_token_ms,
            
            # NEW: Error details
            error_type=llm_call_db.error_type,
            error_code=llm_call_db.error_code,
            retry_count=llm_call_db.retry_count,
            
            # NEW: Cached tokens
            cached_prompt_tokens=llm_call_db.cached_prompt_tokens,
            cached_token_savings=llm_call_db.cached_token_savings,
            
            # NEW: Observability
            trace_id=llm_call_db.trace_id,
            request_id=llm_call_db.request_id,
            environment=llm_call_db.environment,
            
            # NEW: Experiment tracking
            experiment_id=llm_call_db.experiment_id,
            control_group=llm_call_db.control_group,
            
            # Existing optimization metadata
            routing_decision=routing_decision,
            cache_metadata=cache_metadata,
            quality_evaluation=quality_evaluation,
            prompt_breakdown=prompt_breakdown,
            prompt_metadata=prompt_metadata,
            
            # NEW: Complex objects
            llm_config=llm_config,
            streaming_metrics=streaming_metrics,
            experiment_metadata=experiment_metadata,
            error_details=error_details,
            tool_calls_made=llm_call_db.tool_calls_made,
            
            # Existing A/B testing
            prompt_variant_id=llm_call_db.prompt_variant_id,
            test_dataset_id=llm_call_db.test_dataset_id,
            
            metadata=llm_call_db.meta_data or {},
        )

    # =========================================================================
    # SESSION METHODS (UNCHANGED)
    # =========================================================================

    def save_session(self, session: Session) -> None:
        """Save or update a session."""
        db: DBSession = self.SessionLocal()
        try:
            session_db = self._to_session_db(session)
            db.merge(session_db)
            db.commit()
        finally:
            db.close()

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        db: DBSession = self.SessionLocal()
        try:
            session_db = db.query(SessionDB).filter(SessionDB.id == session_id).first()
            return self._from_session_db(session_db) if session_db else None
        finally:
            db.close()

    # =========================================================================
    # LLM CALL METHODS (UNCHANGED)
    # =========================================================================

    def save_llm_call(self, llm_call: LLMCall) -> None:
        """Save an LLM call."""
        db: DBSession = self.SessionLocal()
        try:
            llm_call_db = self._to_llm_call_db(llm_call)
            db.merge(llm_call_db)
            db.commit()
        finally:
            db.close()

    def get_llm_calls(
        self,
        session_id: Optional[str] = None,
        project_name: Optional[str] = None,
        provider: Optional[ModelProvider] = None,
        model_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        operation: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        success_only: Optional[bool] = None,
        conversation_id: Optional[str] = None,  # NEW
        user_id: Optional[str] = None,          # NEW
        experiment_id: Optional[str] = None,    # NEW
        limit: int = 1000,
    ) -> List[LLMCall]:
        """
        Get LLM calls with optional filters.
        
        UPDATED: Added conversation_id, user_id, experiment_id filters
        """
        db: DBSession = self.SessionLocal()
        try:
            query = db.query(LLMCallDB)
            
            # Session filter
            if session_id:
                query = query.filter(LLMCallDB.session_id == session_id)
            
            # Project name filter (requires join with sessions)
            if project_name:
                query = query.join(SessionDB, LLMCallDB.session_id == SessionDB.id)
                query = query.filter(SessionDB.project_name == project_name)
            
            # Basic filters
            if provider:
                query = query.filter(LLMCallDB.provider == provider.value)
            if model_name:
                query = query.filter(LLMCallDB.model_name == model_name)
            if agent_name:
                query = query.filter(LLMCallDB.agent_name == agent_name)
            if operation:
                query = query.filter(LLMCallDB.operation == operation)
            
            # Time filters
            if start_time:
                query = query.filter(LLMCallDB.timestamp >= start_time)
            if end_time:
                query = query.filter(LLMCallDB.timestamp <= end_time)
            
            # Success filter
            if success_only is True:
                query = query.filter(LLMCallDB.success == True)
            elif success_only is False:
                query = query.filter(LLMCallDB.success == False)
            
            # NEW: Conversation filter
            if conversation_id:
                query = query.filter(LLMCallDB.conversation_id == conversation_id)
            
            # NEW: User filter
            if user_id:
                query = query.filter(LLMCallDB.user_id == user_id)
            
            # NEW: Experiment filter
            if experiment_id:
                query = query.filter(LLMCallDB.experiment_id == experiment_id)
            
            query = query.order_by(LLMCallDB.timestamp.desc()).limit(limit)
            
            return [self._from_llm_call_db(c) for c in query.all()]
        finally:
            db.close()

    # =========================================================================
    # DISTINCT VALUE QUERIES (UNCHANGED)
    # =========================================================================

    def get_distinct_projects(self) -> List[str]:
        """Get list of all unique project names."""
        db: DBSession = self.SessionLocal()
        try:
            projects = db.query(distinct(SessionDB.project_name)).all()
            return sorted([p[0] for p in projects if p[0]])
        finally:
            db.close()

    def get_distinct_models(self, project_name: Optional[str] = None) -> List[str]:
        """Get list of all unique model names, optionally filtered by project."""
        db: DBSession = self.SessionLocal()
        try:
            query = db.query(distinct(LLMCallDB.model_name))
            
            if project_name:
                query = query.join(SessionDB, LLMCallDB.session_id == SessionDB.id)
                query = query.filter(SessionDB.project_name == project_name)
            
            models = query.all()
            return sorted([m[0] for m in models if m[0]])
        finally:
            db.close()

    def get_distinct_agents(self, project_name: Optional[str] = None) -> List[str]:
        """Get list of all unique agent names, optionally filtered by project."""
        db: DBSession = self.SessionLocal()
        try:
            query = db.query(distinct(LLMCallDB.agent_name))
            
            if project_name:
                query = query.join(SessionDB, LLMCallDB.session_id == SessionDB.id)
                query = query.filter(SessionDB.project_name == project_name)
            
            agents = query.all()
            return sorted([a[0] for a in agents if a[0]])
        finally:
            db.close()

    def get_distinct_operations(self, project_name: Optional[str] = None) -> List[str]:
        """Get list of all unique operation names, optionally filtered by project."""
        db: DBSession = self.SessionLocal()
        try:
            query = db.query(distinct(LLMCallDB.operation))
            
            if project_name:
                query = query.join(SessionDB, LLMCallDB.session_id == SessionDB.id)
                query = query.filter(SessionDB.project_name == project_name)
            
            operations = query.all()
            return sorted([o[0] for o in operations if o[0]])
        finally:
            db.close()

    # =========================================================================
    # UTILITY METHODS (UNCHANGED)
    # =========================================================================

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its LLM calls."""
        db: DBSession = self.SessionLocal()
        try:
            # Delete LLM calls first
            db.query(LLMCallDB).filter(LLMCallDB.session_id == session_id).delete()
            # Delete session
            result = db.query(SessionDB).filter(SessionDB.id == session_id).delete()
            db.commit()
            return result > 0
        finally:
            db.close()

    def get_call_count(
        self,
        project_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """Get count of LLM calls matching filters."""
        db: DBSession = self.SessionLocal()
        try:
            from sqlalchemy import func
            query = db.query(func.count(LLMCallDB.id))
            
            if project_name:
                query = query.join(SessionDB, LLMCallDB.session_id == SessionDB.id)
                query = query.filter(SessionDB.project_name == project_name)
            
            if start_time:
                query = query.filter(LLMCallDB.timestamp >= start_time)
            if end_time:
                query = query.filter(LLMCallDB.timestamp <= end_time)
            
            return query.scalar() or 0
        finally:
            db.close()

    def get_total_cost(
        self,
        project_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> float:
        """Get total cost of LLM calls matching filters."""
        db: DBSession = self.SessionLocal()
        try:
            from sqlalchemy import func
            query = db.query(func.sum(LLMCallDB.total_cost))
            
            if project_name:
                query = query.join(SessionDB, LLMCallDB.session_id == SessionDB.id)
                query = query.filter(SessionDB.project_name == project_name)
            
            if start_time:
                query = query.filter(LLMCallDB.timestamp >= start_time)
            if end_time:
                query = query.filter(LLMCallDB.timestamp <= end_time)
            
            return query.scalar() or 0.0
        finally:
            db.close()