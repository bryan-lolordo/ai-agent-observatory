"""
Call Router (Layer 2 + Layer 3)
Location: api/routers/calls.py
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import Optional

from api.services.llm_call_service import (
    get_detail, 
    get_calls, 
    get_calls_by_parent,          
    get_calls_by_conversation,   
    build_chat_history_breakdown,
)

# Database dependencies for routing endpoint
from api.dependencies import get_db
from observatory.storage import LLMCallDB

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("")
def list_calls(
    days: int = Query(default=7, ge=1, le=90),
    operation: Optional[str] = None,
    agent: Optional[str] = None,
    call_type: Optional[str] = Query(default=None, description="Filter by call type: llm, api, database, tool"),
    limit: int = Query(default=500, ge=1, le=1000)
):
    """
    Get all LLM calls with optional filters (Layer 2).
    """
    calls = get_calls(
        days=days,
        operation=operation,
        agent=agent,
        call_type=call_type,
        limit=limit
    )
    return {"calls": calls, "total": len(calls)}


@router.get("/{call_id}")
def get_call(call_id: str):
    """
    Get detailed information about a specific LLM call (Layer 3).
    """
    call_detail = get_detail(call_id)
    
    if not call_detail:
        raise HTTPException(
            status_code=404,
            detail=f"Call not found: {call_id}"
        )
    
    return call_detail

@router.get("/{call_id}/trace")
def get_call_trace(
    call_id: str,
    include_siblings: bool = Query(True, description="Include sibling turns"),
    max_depth: int = Query(5, description="Maximum recursion depth"),
):
    """
    Get full trace tree for a call.
    
    Returns hierarchical structure with children and stats.
    """
    # Get root call
    root_call = get_detail(call_id)
    if not root_call:
        raise HTTPException(status_code=404, detail=f"Call {call_id} not found")
    
    # Build tree
    trace = {
        "root_call": root_call,
        "children": [],
        "conversation_turns": [],
        "stats": {
            "total_calls": 1,
            "total_cost": root_call.get("total_cost", 0) or 0,
            "total_latency_ms": root_call.get("latency_ms", 0) or 0,
            "max_depth": 0,
            "turns": 1,
        }
    }
    
    # Recursive function to build children
    def build_children(parent_request_id: str, depth: int):
        if depth >= max_depth:
            return []
        
        children_calls = get_calls_by_parent(parent_request_id)
        children_with_subtrees = []
        
        for child in children_calls:
            # Update stats
            trace["stats"]["total_calls"] += 1
            trace["stats"]["total_cost"] += child.get("total_cost", 0) or 0
            trace["stats"]["total_latency_ms"] += child.get("latency_ms", 0) or 0
            trace["stats"]["max_depth"] = max(trace["stats"]["max_depth"], depth + 1)
            
            # Recursively get grandchildren
            grandchildren = []
            if child.get("request_id"):
                grandchildren = build_children(child["request_id"], depth + 1)
            
            children_with_subtrees.append({
                "call": child,
                "children": grandchildren
            })
        
        return children_with_subtrees
    
    # Build tree
    if root_call.get("request_id"):
        trace["children"] = build_children(root_call["request_id"], 0)
    
    # Get sibling turns if requested
    if include_siblings and root_call.get("conversation_id"):
        all_turns = get_calls_by_conversation(
            root_call["conversation_id"],
            role_filter="orchestrator",
            order_by="turn_number"
        )
        trace["conversation_turns"] = all_turns
        trace["stats"]["turns"] = len(all_turns)
    
    return trace


@router.get("/conversations/{conversation_id}/tree")
def get_conversation_tree(
    conversation_id: str,
    max_depth: int = Query(5, description="Maximum recursion depth"),
):
    """
    Get full trace tree for entire conversation.
    
    Returns all turns with their children in hierarchical structure.
    """
    # Get all orchestrator calls (one per turn)
    orchestrator_calls = get_calls_by_conversation(
        conversation_id,
        role_filter="orchestrator",
        order_by="turn_number"
    )
    
    if not orchestrator_calls:
        raise HTTPException(
            status_code=404,
            detail=f"No calls found for conversation {conversation_id}"
        )
    
    # Build tree for each turn
    turns_data = []
    total_stats = {
        "total_calls": 0,
        "total_cost": 0.0,
        "total_latency_ms": 0.0,
        "max_depth": 0,
        "turns": len(orchestrator_calls)
    }
    
    for orch_call in orchestrator_calls:
        # Get tree for this turn (reuse get_call_trace logic)
        turn_trace = get_call_trace(
            orch_call["call_id"],
            include_siblings=False,
            max_depth=max_depth
        )

        turn_number = orch_call.get("turn_number", 0)
        chat_breakdown = build_chat_history_breakdown(conversation_id, turn_number)
        
        turn_data = {
            "turn_number": orch_call.get("turn_number", 0),
            "orchestrator_call": orch_call,
            "children": turn_trace["children"],
            "user_message": orch_call.get("user_message", ""),
            "total_cost": turn_trace["stats"]["total_cost"],
            "total_latency_ms": turn_trace["stats"]["total_latency_ms"],
            "total_calls": turn_trace["stats"]["total_calls"],
            "chatHistoryBreakdown": chat_breakdown,
        }
        
        turns_data.append(turn_data)
        
        # Update overall stats
        total_stats["total_calls"] += turn_trace["stats"]["total_calls"]
        total_stats["total_cost"] += turn_trace["stats"]["total_cost"]
        total_stats["total_latency_ms"] += turn_trace["stats"]["total_latency_ms"]
        total_stats["max_depth"] = max(total_stats["max_depth"], turn_trace["stats"]["max_depth"])
    
    return {
        "conversation_id": conversation_id,
        "turns": turns_data,
        "stats": total_stats
    }


# =============================================================================
# NEW: ROUTING TRACE ENDPOINT (for Routing Story Layer 3 Trace Tab)
# =============================================================================

@router.get("/conversations/{conversation_id}/routing-trace")
async def get_conversation_routing_trace(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """
    Get routing analysis for entire conversation.
    Shows turn-by-turn routing decisions with grouped calls.
    
    Returns:
    - conversation_id: str
    - summary: {total_turns, model, routing_type, routing_score, opportunity_count, insights}
    - turns: [{turn_number, user_message, total_calls, total_cost, total_latency, calls}]
    """
    # Get all calls in conversation, ordered by turn
    calls = db.query(LLMCallDB).filter(                          # ✅ CHANGED: LLMCall → LLMCallDB
        LLMCallDB.conversation_id == conversation_id             # ✅ CHANGED: LLMCall → LLMCallDB
    ).order_by(LLMCallDB.turn_number, LLMCallDB.timestamp).all()  # ✅ CHANGED: LLMCall → LLMCallDB
    
    if not calls:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Group by turns
    turns_dict = {}
    for call in calls:
        turn_num = call.turn_number or 1
        if turn_num not in turns_dict:
            turns_dict[turn_num] = {
                'turn_number': turn_num,
                'calls': [],
                'total_calls': 0,
                'total_cost': 0,
                'total_latency': 0,
                'user_message': None,
            }
        
        # Get user message from ChatAgent call if available
        if call.agent_name == 'ChatAgent' and call.user_message:
            turns_dict[turn_num]['user_message'] = call.user_message
        
        # Get routing analysis for this call
        from api.services.routing_service import analyze_call_routing
        routing = analyze_call_routing({
            "model_name": call.model_name,
            "complexity_score": call.complexity_score,
            "judge_score": call.judge_score,
            "prompt_tokens": call.prompt_tokens,
            "completion_tokens": call.completion_tokens,
            "total_cost": call.total_cost,
            "operation": call.operation,
            "tool_call_count": 0,
        })
        
        turns_dict[turn_num]['calls'].append({
            'call_id': call.id,  # Note: LLMCallDB uses 'id', not 'call_id'
            'agent_name': call.agent_name,
            'operation': call.operation,
            'model_name': call.model_name,
            'latency_ms': call.latency_ms,
            'total_cost': call.total_cost,
            'complexity_score': call.complexity_score,
            'judge_score': call.judge_score,
            'routing_analysis': routing,
        })
        
        turns_dict[turn_num]['total_calls'] += 1
        turns_dict[turn_num]['total_cost'] += call.total_cost or 0
        turns_dict[turn_num]['total_latency'] += call.latency_ms or 0
    
    # Convert to list and sort
    turns = sorted(turns_dict.values(), key=lambda t: t['turn_number'])
    
    # Calculate summary stats
    total_calls = len(calls)
    optimal_count = 0
    for turn in turns:
        for call_data in turn['calls']:
            if call_data['routing_analysis'].get('verdict') == 'optimal':
                optimal_count += 1
    
    total_turns = len(turns)
    
    # Detect routing pattern
    models_used = set(c.model_name for c in calls)
    routing_type = "Static" if len(models_used) == 1 else "Dynamic"
    primary_model = calls[0].model_name if calls else "unknown"
    
    # Count opportunities
    opportunity_count = 0
    for turn in turns:
        for call_data in turn['calls']:
            if call_data['routing_analysis'].get('verdict') != 'optimal':
                opportunity_count += 1
    
    # Calculate routing score
    routing_score = int((optimal_count / total_calls * 100)) if total_calls > 0 else 0
    
    # Generate insights
    insights = []
    if routing_type == "Static":
        insights.append(f"🎯 Static Routing Detected: All calls use {primary_model} regardless of complexity")
    if opportunity_count > 0:
        insights.append(f"💡 {opportunity_count} calls could benefit from better routing")
    if routing_score < 60:
        insights.append(f"⚠️ Low routing score ({routing_score}%) - consider complexity-based routing")
    
    summary = {
        'total_turns': total_turns,
        'total_calls': total_calls,
        'model': primary_model,
        'routing_type': routing_type,
        'routing_score': routing_score,
        'opportunity_count': opportunity_count,
        'insights': insights,
    }
    
    return {
        'conversation_id': conversation_id,
        'summary': summary,
        'turns': turns,
    }