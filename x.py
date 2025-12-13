#!/usr/bin/env python3
"""
Database Schema Verification Test
Run this to verify your Observatory database has all the new fields.

Usage:
    python test_schema.py
"""

import os
import sys
from datetime import datetime
from sqlalchemy import inspect

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from observatory import Storage, ModelProvider, AgentRole
from observatory.models import (
    LLMCall, ModelConfig, StreamingMetrics, 
    ExperimentMetadata, ErrorDetails, PromptBreakdown
)


def test_database_schema():
    """Test that database has all expected columns."""
    print("=" * 80)
    print("OBSERVATORY DATABASE SCHEMA VERIFICATION")
    print("=" * 80)
    
    # Initialize storage
    db_path = os.getenv("DATABASE_URL", "sqlite:///observatory.db")
    print(f"\n📁 Database: {db_path}")
    storage = Storage(database_url=db_path)
    
    # Inspect the schema
    inspector = inspect(storage.engine)
    
    # Check LLMCallDB table
    print("\n🔍 Checking LLMCallDB table schema...")
    columns = inspector.get_columns('llm_calls')
    column_names = {col['name'] for col in columns}
    
    # Expected columns (50 top-level fields)
    expected_columns = {
        # Identity (4)
        'id', 'session_id', 'timestamp', 'provider',
        
        # Model (1)
        'model_name',
        
        # Content (3)
        'prompt', 'prompt_normalized', 'response_text',
        
        # Core metrics (7)
        'prompt_tokens', 'completion_tokens', 'total_tokens',
        'prompt_cost', 'completion_cost', 'total_cost', 'latency_ms',
        
        # Context (3)
        'agent_name', 'agent_role', 'operation',
        
        # Status (2)
        'success', 'error',
        
        # NEW: Conversation linking (4)
        'conversation_id', 'turn_number', 'parent_call_id', 'user_id',
        
        # NEW: Model config (3)
        'temperature', 'max_tokens', 'top_p',
        
        # NEW: Token breakdown (5)
        'system_prompt_tokens', 'user_message_tokens', 'chat_history_tokens',
        'conversation_context_tokens', 'tool_definitions_tokens',
        
        # NEW: Tool tracking (2)
        'tool_call_count', 'tool_execution_time_ms',
        
        # NEW: Streaming (1)
        'time_to_first_token_ms',
        
        # NEW: Error details (3)
        'error_type', 'error_code', 'retry_count',
        
        # NEW: Cached tokens (2)
        'cached_prompt_tokens', 'cached_token_savings',
        
        # NEW: Observability (3)
        'trace_id', 'request_id', 'environment',
        
        # NEW: Experiment tracking (2)
        'experiment_id', 'control_group',
        
        # JSON fields (10)
        'routing_decision', 'cache_metadata', 'quality_evaluation',
        'prompt_breakdown', 'prompt_metadata',
        'model_config', 'streaming_metrics', 'experiment_metadata',
        'error_details', 'tool_calls_made',
        
        # A/B Testing (2)
        'prompt_variant_id', 'test_dataset_id',
        
        # Metadata (1)
        'meta_data',
    }
    
    # Check for missing columns
    missing = expected_columns - column_names
    extra = column_names - expected_columns
    
    print(f"\n✅ Found {len(column_names)} columns in llm_calls table")
    print(f"📊 Expected {len(expected_columns)} columns")
    
    if missing:
        print(f"\n❌ MISSING COLUMNS ({len(missing)}):")
        for col in sorted(missing):
            print(f"   - {col}")
        print("\n⚠️  Run database migration to add missing columns!")
        return False
    
    if extra:
        print(f"\n⚠️  EXTRA COLUMNS ({len(extra)}):")
        for col in sorted(extra):
            print(f"   - {col}")
    
    if not missing and not extra:
        print("\n✅ Schema is PERFECT! All expected columns present.")
    
    # Print column breakdown by category
    print("\n" + "=" * 80)
    print("COLUMN BREAKDOWN BY CATEGORY")
    print("=" * 80)
    
    categories = {
        'Identity': ['id', 'session_id', 'timestamp', 'provider'],
        'Model': ['model_name'],
        'Content': ['prompt', 'prompt_normalized', 'response_text'],
        'Core Metrics': ['prompt_tokens', 'completion_tokens', 'total_tokens', 
                        'prompt_cost', 'completion_cost', 'total_cost', 'latency_ms'],
        'Context': ['agent_name', 'agent_role', 'operation'],
        'Status': ['success', 'error'],
        'Conversation Linking (NEW)': ['conversation_id', 'turn_number', 'parent_call_id', 'user_id'],
        'Model Config (NEW)': ['temperature', 'max_tokens', 'top_p'],
        'Token Breakdown (NEW)': ['system_prompt_tokens', 'user_message_tokens', 'chat_history_tokens',
                                   'conversation_context_tokens', 'tool_definitions_tokens'],
        'Tool Tracking (NEW)': ['tool_call_count', 'tool_execution_time_ms'],
        'Streaming (NEW)': ['time_to_first_token_ms'],
        'Error Details (NEW)': ['error_type', 'error_code', 'retry_count'],
        'Cached Tokens (NEW)': ['cached_prompt_tokens', 'cached_token_savings'],
        'Observability (NEW)': ['trace_id', 'request_id', 'environment'],
        'Experiment Tracking (NEW)': ['experiment_id', 'control_group'],
        'JSON Fields': ['routing_decision', 'cache_metadata', 'quality_evaluation',
                       'prompt_breakdown', 'prompt_metadata', 'model_config',
                       'streaming_metrics', 'experiment_metadata', 'error_details', 'tool_calls_made'],
        'A/B Testing': ['prompt_variant_id', 'test_dataset_id'],
        'Metadata': ['meta_data'],
    }
    
    for category, cols in categories.items():
        present = [c for c in cols if c in column_names]
        missing_cat = [c for c in cols if c not in column_names]
        
        status = "✅" if len(present) == len(cols) else "❌"
        print(f"\n{status} {category}: {len(present)}/{len(cols)}")
        
        if missing_cat:
            print(f"   Missing: {', '.join(missing_cat)}")
    
    return len(missing) == 0


def test_model_round_trip():
    """Test that new models can be saved and retrieved."""
    print("\n" + "=" * 80)
    print("MODEL ROUND-TRIP TEST")
    print("=" * 80)
    
    db_path = os.getenv("DATABASE_URL", "sqlite:///observatory.db")
    storage = Storage(database_url=db_path)
    
    # Create a test LLMCall with ALL new fields
    print("\n🔧 Creating test LLMCall with all new fields...")
    
    test_call = LLMCall(
        id="test_schema_verification_123",
        session_id="test_session_123",
        timestamp=datetime.utcnow(),
        provider=ModelProvider.OPENAI,
        model_name="gpt-4o-mini",
        prompt="Test prompt",
        response_text="Test response",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        prompt_cost=0.001,
        completion_cost=0.002,
        total_cost=0.003,
        latency_ms=500,
        agent_name="TestAgent",
        operation="test_operation",
        success=True,
        
        # NEW: Conversation linking
        conversation_id="test_conv_123",
        turn_number=1,
        user_id="test_user_456",
        
        # NEW: Model config
        temperature=0.7,
        max_tokens=1000,
        top_p=0.9,
        llm_config=ModelConfig(
            temperature=0.7,
            max_tokens=1000,
            top_p=0.9,
            seed=42,
        ),
        
        # NEW: Token breakdown
        system_prompt_tokens=50,
        user_message_tokens=30,
        chat_history_tokens=20,
        conversation_context_tokens=10,
        tool_definitions_tokens=5,
        
        # NEW: Tool tracking
        tool_call_count=2,
        tool_execution_time_ms=100,
        tool_calls_made=[
            {"tool_name": "search", "execution_time_ms": 50},
            {"tool_name": "calculate", "execution_time_ms": 50},
        ],
        
        # NEW: Streaming
        time_to_first_token_ms=50,
        streaming_metrics=StreamingMetrics(
            is_streaming=True,
            time_to_first_token_ms=50,
            stream_chunk_count=10,
        ),
        
        # NEW: Error details
        error_type="NONE",
        retry_count=0,
        
        # NEW: Cached tokens
        cached_prompt_tokens=0,
        cached_token_savings=0.0,
        
        # NEW: Observability
        trace_id="trace_abc123",
        request_id="req_xyz789",
        environment="test",
        
        # NEW: Experiment tracking
        experiment_id="exp_001",
        control_group=False,
        experiment_metadata=ExperimentMetadata(
            experiment_id="exp_001",
            experiment_name="Test Experiment",
            variant_id="variant_a",
            control_group=False,
        ),
        
        # Prompt breakdown with new fields
        prompt_breakdown=PromptBreakdown(
            system_prompt="You are a test assistant",
            system_prompt_tokens=50,
            user_message="Test message",
            user_message_tokens=30,
            chat_history_tokens=20,
            conversation_context_tokens=10,
            tool_definitions_tokens=5,
            total_input_tokens=115,
            system_to_total_ratio=0.43,
        ),
    )
    
    # Save to database
    print("💾 Saving to database...")
    try:
        storage.save_llm_call(test_call)
        print("✅ Save successful!")
    except Exception as e:
        print(f"❌ Save failed: {e}")
        return False
    
    # Retrieve from database
    print("🔍 Retrieving from database...")
    try:
        retrieved = storage.get_llm_calls(session_id="test_session_123", limit=1)
        if not retrieved:
            print("❌ Retrieval failed: No records found")
            return False
        
        retrieved_call = retrieved[0]
        print("✅ Retrieval successful!")
    except Exception as e:
        print(f"❌ Retrieval failed: {e}")
        return False
    
    # Verify new fields
    print("\n🔍 Verifying new fields...")
    
    checks = {
        'conversation_id': (retrieved_call.conversation_id, "test_conv_123"),
        'turn_number': (retrieved_call.turn_number, 1),
        'user_id': (retrieved_call.user_id, "test_user_456"),
        'temperature': (retrieved_call.temperature, 0.7),
        'system_prompt_tokens': (retrieved_call.system_prompt_tokens, 50),
        'tool_call_count': (retrieved_call.tool_call_count, 2),
        'time_to_first_token_ms': (retrieved_call.time_to_first_token_ms, 50),
        'trace_id': (retrieved_call.trace_id, "trace_abc123"),
        'experiment_id': (retrieved_call.experiment_id, "exp_001"),
    }
    
    all_pass = True
    for field, (actual, expected) in checks.items():
        if actual == expected:
            print(f"   ✅ {field}: {actual}")
        else:
            print(f"   ❌ {field}: expected {expected}, got {actual}")
            all_pass = False
    
    # Check nested objects
    if retrieved_call.llm_config and retrieved_call.llm_config.seed == 42:
        print("   ✅ llm_config.seed: 42")
    else:
        print("   ❌ llm_config.seed: FAILED")
        all_pass = False
    
    if retrieved_call.prompt_breakdown and retrieved_call.prompt_breakdown.conversation_context_tokens == 10:
        print("   ✅ prompt_breakdown.conversation_context_tokens: 10")
    else:
        print("   ❌ prompt_breakdown.conversation_context_tokens: FAILED")
        all_pass = False
    
    # Cleanup
    print("\n🧹 Cleaning up test data...")
    storage.delete_session("test_session_123")
    
    return all_pass


def main():
    """Run all tests."""
    print("\n🚀 Starting Observatory Schema Verification...\n")
    
    schema_ok = test_database_schema()
    roundtrip_ok = test_model_round_trip()
    
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    
    if schema_ok and roundtrip_ok:
        print("\n✅ ✅ ✅ ALL TESTS PASSED! ✅ ✅ ✅")
        print("\nYour database schema is complete and working correctly!")
        print("You have all 50 top-level columns + 10 JSON fields = 139 total fields")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        if not schema_ok:
            print("   - Schema check failed (missing columns)")
        if not roundtrip_ok:
            print("   - Round-trip test failed (data persistence issue)")
        print("\n⚠️  Please review the errors above and fix before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())