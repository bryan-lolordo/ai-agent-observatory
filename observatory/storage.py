"""
Observatory Storage Layer
Location: observatory/storage.py

SQLAlchemy-based storage with support for:
- Sessions and LLM calls
- Routing, caching, quality metadata
- Prompt breakdown (NEW)
- Enhanced diagnostics fields (NEW)
"""

import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, JSON, Text, Index
from sqlalchemy.orm import declarative_base, sessionmaker, Session as DBSession

from observatory.models import (
    Session, LLMCall, ModelProvider, AgentRole,
    RoutingDecision, CacheMetadata, QualityEvaluation,
    PromptBreakdown, PromptMetadata,
    RoutingMetrics, CacheMetrics
)


Base = declarative_base()


# =============================================================================
# DATABASE MODELS
# =============================================================================

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
    
    # Enhanced fields - Routing (stored as JSON)
    routing_decision = Column(JSON, nullable=True)
    
    # Enhanced fields - Caching (stored as JSON)
    cache_metadata = Column(JSON, nullable=True)
    
    # Enhanced fields - Quality (stored as JSON)
    quality_evaluation = Column(JSON, nullable=True)
    
    # Enhanced fields - Prompt Variants
    prompt_variant_id = Column(String, nullable=True, index=True)
    test_dataset_id = Column(String, nullable=True, index=True)
    
    # NEW: Structured prompt breakdown (stored as JSON)
    prompt_breakdown = Column(JSON, nullable=True)
    
    # NEW: Prompt metadata for optimization tracking (stored as JSON)
    prompt_metadata = Column(JSON, nullable=True)
    
    # Flexible metadata
    meta_data = Column(JSON, default={})
    
    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_llm_calls_session_timestamp', 'session_id', 'timestamp'),
        Index('ix_llm_calls_operation_timestamp', 'operation', 'timestamp'),
        Index('ix_llm_calls_model_operation', 'model_name', 'operation'),
    )


# =============================================================================
# STORAGE CLASS
# =============================================================================

class Storage:
    def __init__(self, database_url: Optional[str] = None):
        if database_url is None:
            database_url = os.getenv("DATABASE_URL", "sqlite:///observatory.db")
        
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    # =========================================================================
    # CONVERSION: Session
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
    # CONVERSION: LLM Call
    # =========================================================================
    
    def _to_llm_call_db(self, llm_call: LLMCall) -> LLMCallDB:
        # Convert nested Pydantic models to dict for JSON storage
        routing_data = llm_call.routing_decision.model_dump() if llm_call.routing_decision else None
        cache_data = llm_call.cache_metadata.model_dump() if llm_call.cache_metadata else None
        quality_data = llm_call.quality_evaluation.model_dump() if llm_call.quality_evaluation else None
        breakdown_data = llm_call.prompt_breakdown.model_dump() if llm_call.prompt_breakdown else None
        prompt_meta_data = llm_call.prompt_metadata.model_dump() if llm_call.prompt_metadata else None
        
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
            routing_decision=routing_data,
            cache_metadata=cache_data,
            quality_evaluation=quality_data,
            prompt_variant_id=llm_call.prompt_variant_id,
            test_dataset_id=llm_call.test_dataset_id,
            prompt_breakdown=breakdown_data,
            prompt_metadata=prompt_meta_data,
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
            routing_decision=routing_decision,
            cache_metadata=cache_metadata,
            quality_evaluation=quality_evaluation,
            prompt_variant_id=llm_call_db.prompt_variant_id,
            test_dataset_id=llm_call_db.test_dataset_id,
            prompt_breakdown=prompt_breakdown,
            prompt_metadata=prompt_metadata,
            metadata=llm_call_db.meta_data or {},
        )

    # =========================================================================
    # SESSION OPERATIONS
    # =========================================================================
    
    def save_session(self, session: Session):
        db: DBSession = self.SessionLocal()
        try:
            session_db = self._to_session_db(session)
            db.merge(session_db)
            db.commit()
        finally:
            db.close()

    def update_session(self, session: Session):
        self.save_session(session)

    def get_session(self, session_id: str) -> Optional[Session]:
        db: DBSession = self.SessionLocal()
        try:
            session_db = db.query(SessionDB).filter(SessionDB.id == session_id).first()
            if not session_db:
                return None
            
            session = self._from_session_db(session_db)
            
            # Load LLM calls
            llm_calls_db = db.query(LLMCallDB).filter(LLMCallDB.session_id == session_id).all()
            session.llm_calls = [self._from_llm_call_db(call) for call in llm_calls_db]
            
            return session
        finally:
            db.close()

    def get_sessions(
        self,
        project_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        operation_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Session]:
        db: DBSession = self.SessionLocal()
        try:
            query = db.query(SessionDB)
            
            if project_name:
                query = query.filter(SessionDB.project_name == project_name)
            if start_time:
                query = query.filter(SessionDB.start_time >= start_time)
            if end_time:
                query = query.filter(SessionDB.start_time <= end_time)
            if operation_type:
                query = query.filter(SessionDB.operation_type == operation_type)
            
            query = query.order_by(SessionDB.start_time.desc()).limit(limit)
            
            return [self._from_session_db(s) for s in query.all()]
        finally:
            db.close()

    # =========================================================================
    # LLM CALL OPERATIONS
    # =========================================================================
    
    def save_llm_call(self, llm_call: LLMCall):
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
        has_quality_eval: Optional[bool] = None,
        has_routing: Optional[bool] = None,
        has_cache: Optional[bool] = None,
        limit: int = 1000,
    ) -> List[LLMCall]:
        """
        Get LLM calls with flexible filtering.
        
        Args:
            session_id: Filter by session
            project_name: Filter by project
            provider: Filter by provider
            model_name: Filter by model
            agent_name: Filter by agent
            operation: Filter by operation
            start_time: Filter by start time
            end_time: Filter by end time
            success_only: Only successful calls
            has_quality_eval: Only calls with quality evaluation
            has_routing: Only calls with routing decision
            has_cache: Only calls with cache metadata
            limit: Maximum results
        
        Returns:
            List of LLMCall objects
        """
        db: DBSession = self.SessionLocal()
        try:
            query = db.query(LLMCallDB)
            
            if session_id:
                query = query.filter(LLMCallDB.session_id == session_id)
            
            # Filter by project name (requires join with sessions)
            if project_name:
                query = query.join(SessionDB, LLMCallDB.session_id == SessionDB.id)
                query = query.filter(SessionDB.project_name == project_name)
            
            if provider:
                query = query.filter(LLMCallDB.provider == provider.value)
            if model_name:
                query = query.filter(LLMCallDB.model_name == model_name)
            if agent_name:
                query = query.filter(LLMCallDB.agent_name == agent_name)
            if operation:
                query = query.filter(LLMCallDB.operation == operation)
            if start_time:
                query = query.filter(LLMCallDB.timestamp >= start_time)
            if end_time:
                query = query.filter(LLMCallDB.timestamp <= end_time)
            if success_only is not None:
                query = query.filter(LLMCallDB.success == success_only)
            if has_quality_eval is not None:
                if has_quality_eval:
                    query = query.filter(LLMCallDB.quality_evaluation.isnot(None))
                else:
                    query = query.filter(LLMCallDB.quality_evaluation.is_(None))
            if has_routing is not None:
                if has_routing:
                    query = query.filter(LLMCallDB.routing_decision.isnot(None))
                else:
                    query = query.filter(LLMCallDB.routing_decision.is_(None))
            if has_cache is not None:
                if has_cache:
                    query = query.filter(LLMCallDB.cache_metadata.isnot(None))
                else:
                    query = query.filter(LLMCallDB.cache_metadata.is_(None))
            
            query = query.order_by(LLMCallDB.timestamp.desc()).limit(limit)
            
            return [self._from_llm_call_db(c) for c in query.all()]
        finally:
            db.close()

    # =========================================================================
    # DISTINCT VALUE QUERIES
    # =========================================================================
    
    def get_distinct_projects(self) -> List[str]:
        """Get list of all unique project names"""
        db: DBSession = self.SessionLocal()
        try:
            from sqlalchemy import distinct
            projects = db.query(distinct(SessionDB.project_name)).all()
            return sorted([p[0] for p in projects if p[0]])
        finally:
            db.close()

    def get_distinct_models(self, project_name: Optional[str] = None) -> List[str]:
        """Get list of all unique model names, optionally filtered by project"""
        db: DBSession = self.SessionLocal()
        try:
            from sqlalchemy import distinct
            query = db.query(distinct(LLMCallDB.model_name))
            
            if project_name:
                query = query.join(SessionDB, LLMCallDB.session_id == SessionDB.id)
                query = query.filter(SessionDB.project_name == project_name)
            
            models = query.all()
            return sorted([m[0] for m in models if m[0]])
        finally:
            db.close()

    def get_distinct_agents(self, project_name: Optional[str] = None) -> List[str]:
        """Get list of all unique agent names, optionally filtered by project"""
        db: DBSession = self.SessionLocal()
        try:
            from sqlalchemy import distinct
            query = db.query(distinct(LLMCallDB.agent_name))
            
            if project_name:
                query = query.join(SessionDB, LLMCallDB.session_id == SessionDB.id)
                query = query.filter(SessionDB.project_name == project_name)
            
            agents = query.all()
            return sorted([a[0] for a in agents if a[0]])
        finally:
            db.close()

    def get_distinct_operations(self, project_name: Optional[str] = None) -> List[str]:
        """Get list of all unique operation names, optionally filtered by project"""
        db: DBSession = self.SessionLocal()
        try:
            from sqlalchemy import distinct
            query = db.query(distinct(LLMCallDB.operation))
            
            if project_name:
                query = query.join(SessionDB, LLMCallDB.session_id == SessionDB.id)
                query = query.filter(SessionDB.project_name == project_name)
            
            operations = query.all()
            return sorted([o[0] for o in operations if o[0]])
        finally:
            db.close()

    # =========================================================================
    # AGGREGATION QUERIES
    # =========================================================================
    
    def get_call_stats(
        self,
        project_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics for calls.
        
        Returns:
            Dict with total_calls, total_cost, total_tokens, avg_latency, etc.
        """
        db: DBSession = self.SessionLocal()
        try:
            from sqlalchemy import func
            
            query = db.query(
                func.count(LLMCallDB.id).label('total_calls'),
                func.sum(LLMCallDB.total_cost).label('total_cost'),
                func.sum(LLMCallDB.total_tokens).label('total_tokens'),
                func.avg(LLMCallDB.latency_ms).label('avg_latency'),
                func.sum(LLMCallDB.prompt_tokens).label('total_prompt_tokens'),
                func.sum(LLMCallDB.completion_tokens).label('total_completion_tokens'),
            )
            
            if project_name:
                query = query.join(SessionDB, LLMCallDB.session_id == SessionDB.id)
                query = query.filter(SessionDB.project_name == project_name)
            if start_time:
                query = query.filter(LLMCallDB.timestamp >= start_time)
            if end_time:
                query = query.filter(LLMCallDB.timestamp <= end_time)
            
            result = query.first()
            
            return {
                'total_calls': result.total_calls or 0,
                'total_cost': result.total_cost or 0,
                'total_tokens': result.total_tokens or 0,
                'avg_latency': result.avg_latency or 0,
                'total_prompt_tokens': result.total_prompt_tokens or 0,
                'total_completion_tokens': result.total_completion_tokens or 0,
            }
        finally:
            db.close()

    def get_stats_by_operation(
        self,
        project_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get aggregated statistics grouped by operation."""
        db: DBSession = self.SessionLocal()
        try:
            from sqlalchemy import func
            
            query = db.query(
                LLMCallDB.operation,
                func.count(LLMCallDB.id).label('call_count'),
                func.sum(LLMCallDB.total_cost).label('total_cost'),
                func.sum(LLMCallDB.total_tokens).label('total_tokens'),
                func.avg(LLMCallDB.latency_ms).label('avg_latency'),
            ).group_by(LLMCallDB.operation)
            
            if project_name:
                query = query.join(SessionDB, LLMCallDB.session_id == SessionDB.id)
                query = query.filter(SessionDB.project_name == project_name)
            if start_time:
                query = query.filter(LLMCallDB.timestamp >= start_time)
            if end_time:
                query = query.filter(LLMCallDB.timestamp <= end_time)
            
            results = query.all()
            
            return [
                {
                    'operation': r.operation,
                    'call_count': r.call_count,
                    'total_cost': r.total_cost or 0,
                    'total_tokens': r.total_tokens or 0,
                    'avg_latency': r.avg_latency or 0,
                }
                for r in results
            ]
        finally:
            db.close()

    def get_stats_by_model(
        self,
        project_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get aggregated statistics grouped by model."""
        db: DBSession = self.SessionLocal()
        try:
            from sqlalchemy import func
            
            query = db.query(
                LLMCallDB.model_name,
                func.count(LLMCallDB.id).label('call_count'),
                func.sum(LLMCallDB.total_cost).label('total_cost'),
                func.sum(LLMCallDB.total_tokens).label('total_tokens'),
                func.avg(LLMCallDB.latency_ms).label('avg_latency'),
            ).group_by(LLMCallDB.model_name)
            
            if project_name:
                query = query.join(SessionDB, LLMCallDB.session_id == SessionDB.id)
                query = query.filter(SessionDB.project_name == project_name)
            if start_time:
                query = query.filter(LLMCallDB.timestamp >= start_time)
            if end_time:
                query = query.filter(LLMCallDB.timestamp <= end_time)
            
            results = query.all()
            
            return [
                {
                    'model_name': r.model_name,
                    'call_count': r.call_count,
                    'total_cost': r.total_cost or 0,
                    'total_tokens': r.total_tokens or 0,
                    'avg_latency': r.avg_latency or 0,
                }
                for r in results
            ]
        finally:
            db.close()