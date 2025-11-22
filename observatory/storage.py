import os
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session as DBSession

from observatory.models import Session, LLMCall, ModelProvider, AgentRole


Base = declarative_base()


class SessionDB(Base):
    __tablename__ = "sessions"
    
    id = Column(String, primary_key=True)
    project_name = Column(String, index=True)
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime, nullable=True)
    
    total_llm_calls = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    total_latency_ms = Column(Float, default=0.0)
    
    success = Column(Boolean, default=True)
    error = Column(Text, nullable=True)
    
    operation_type = Column(String, nullable=True, index=True)
    metadata = Column(JSON, default={})


class LLMCallDB(Base):
    __tablename__ = "llm_calls"
    
    id = Column(String, primary_key=True)
    session_id = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    
    provider = Column(String, index=True)
    model_name = Column(String, index=True)
    
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
    
    metadata = Column(JSON, default={})


class Storage:
    def __init__(self, database_url: Optional[str] = None):
        if database_url is None:
            database_url = os.getenv("DATABASE_URL", "sqlite:///observatory.db")
        
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

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
            success=session.success,
            error=session.error,
            operation_type=session.operation_type,
            metadata=session.metadata,
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
            success=session_db.success,
            error=session_db.error,
            operation_type=session_db.operation_type,
            metadata=session_db.metadata or {},
        )

    def _to_llm_call_db(self, llm_call: LLMCall) -> LLMCallDB:
        return LLMCallDB(
            id=llm_call.id,
            session_id=llm_call.session_id,
            timestamp=llm_call.timestamp,
            provider=llm_call.provider.value,
            model_name=llm_call.model_name,
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
            metadata=llm_call.metadata,
        )

    def _from_llm_call_db(self, llm_call_db: LLMCallDB) -> LLMCall:
        return LLMCall(
            id=llm_call_db.id,
            session_id=llm_call_db.session_id,
            timestamp=llm_call_db.timestamp,
            provider=ModelProvider(llm_call_db.provider),
            model_name=llm_call_db.model_name,
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
            metadata=llm_call_db.metadata or {},
        )

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

    def save_llm_call(self, llm_call: LLMCall):
        db: DBSession = self.SessionLocal()
        try:
            llm_call_db = self._to_llm_call_db(llm_call)
            db.merge(llm_call_db)
            db.commit()
        finally:
            db.close()

    def get_sessions(
        self,
        project_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
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
            
            query = query.order_by(SessionDB.start_time.desc()).limit(limit)
            
            return [self._from_session_db(s) for s in query.all()]
        finally:
            db.close()

    def get_llm_calls(
        self,
        session_id: Optional[str] = None,
        provider: Optional[ModelProvider] = None,
        model_name: Optional[str] = None,
        limit: int = 1000,
    ) -> List[LLMCall]:
        db: DBSession = self.SessionLocal()
        try:
            query = db.query(LLMCallDB)
            
            if session_id:
                query = query.filter(LLMCallDB.session_id == session_id)
            if provider:
                query = query.filter(LLMCallDB.provider == provider.value)
            if model_name:
                query = query.filter(LLMCallDB.model_name == model_name)
            
            query = query.order_by(LLMCallDB.timestamp.desc()).limit(limit)
            
            return [self._from_llm_call_db(c) for c in query.all()]
        finally:
            db.close()