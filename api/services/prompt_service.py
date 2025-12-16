"""
Prompt Service - Story 6 Business Logic
Location: api/services/prompt_service.py

Handles prompt composition analysis.
Returns proper SystemPromptStoryResponse model.
"""

from typing import List, Dict, Any
from collections import defaultdict
from api.models import SystemPromptStoryResponse, SystemPromptSummary, TopOffender
from api.config.story_definitions import get_story_recommendations
from api.routers import llm_calls
from api.utils.formatters import format_tokens, format_percentage

# Thresholds
SYSTEM_PROMPT_WASTE_PCT = 0.30
SYSTEM_PROMPT_HIGH_TOKENS = 1000


def get_summary(calls: List[Dict], project: str = None, days: int = 7) -> SystemPromptStoryResponse:
    """
    Layer 1: Prompt composition summary.
    
    Args:
        calls: List of LLM call dictionaries
        project: Project name filter
        days: Number of days analyzed
    
    Returns:
        SystemPromptStoryResponse model
    """
    if not calls:
        return SystemPromptStoryResponse(
            status="ok",
            health_score=100.0,
            summary=SystemPromptSummary(
                total_calls=0,
                issue_count=0,
                avg_system_tokens=0,
                avg_user_tokens=0,
                avg_context_tokens=0,
                total_system_tokens=0,
                largest_system_prompt=0,
                total_redundant_tokens=0,
            ),
            top_offender=None,
            detail_table=[],
            chart_data=[],
            recommendations=[],
        )
    
    # Filter to only LLM calls
    llm_calls = [c for c in calls if (c.get('prompt_tokens') or 0) > 0]
    
    if not llm_calls:
        return SystemPromptStoryResponse(
            status="ok",
            health_score=100.0,
            summary=SystemPromptSummary(
                total_calls=0,
                issue_count=0,
                avg_system_tokens=0,
                avg_user_tokens=0,
                avg_context_tokens=0,
                total_system_tokens=0,
                largest_system_prompt=0,
                total_redundant_tokens=0,
            ),
            top_offender=None,
            detail_table=[],
            chart_data=[],
            recommendations=[],
        )
    
    # Group by operation
    by_operation = defaultdict(list)
    for call in llm_calls:
        op = f"{call.get('agent_name', 'Unknown')}.{call.get('operation', 'unknown')}"
        by_operation[op].append(call)
    
    detail_table = []
    ops_with_waste = []
    total_redundant_tokens = 0
    all_system_tokens = []
    
    for op, op_calls in by_operation.items():
        system_tokens_list = []
        user_tokens_list = []
        context_tokens_list = []
        total_prompt_tokens = 0
        
        for call in op_calls:
            prompt_tokens = call.get('prompt_tokens') or 0
            total_prompt_tokens += prompt_tokens
            
            # Get from breakdown or estimate
            breakdown = call.get('prompt_breakdown') or {}
            system_tokens = breakdown.get('system_prompt_tokens') or 0
            user_tokens = breakdown.get('user_message_tokens') or 0
            context_tokens = breakdown.get('chat_history_tokens') or 0
            
            # If not available, estimate
            if not system_tokens and prompt_tokens > 500:
                system_tokens = int(prompt_tokens * 0.4)
            
            system_tokens_list.append(system_tokens)
            user_tokens_list.append(user_tokens)
            context_tokens_list.append(context_tokens)
            all_system_tokens.append(system_tokens)
        
        avg_system_tokens = sum(system_tokens_list) / len(system_tokens_list) if system_tokens_list else 0
        avg_user_tokens = sum(user_tokens_list) / len(user_tokens_list) if user_tokens_list else 0
        avg_context_tokens = sum(context_tokens_list) / len(context_tokens_list) if context_tokens_list else 0
        total_system_tokens = sum(system_tokens_list)
        
        # Calculate waste: if same system prompt sent N times, (N-1) are redundant
        call_count = len(op_calls)
        if call_count > 1 and avg_system_tokens > 100:
            redundant_tokens = int(avg_system_tokens * (call_count - 1))
        else:
            redundant_tokens = 0
        
        avg_prompt_tokens = total_prompt_tokens / call_count if call_count > 0 else 0
        system_pct = avg_system_tokens / avg_prompt_tokens if avg_prompt_tokens > 0 else 0
        
        has_waste = (system_pct > SYSTEM_PROMPT_WASTE_PCT or 
                     avg_system_tokens > SYSTEM_PROMPT_HIGH_TOKENS)
        
        status = "🔴" if has_waste else "🟢"
        
        if has_waste:
            ops_with_waste.append((op, redundant_tokens, avg_system_tokens, op_calls))
        
        total_redundant_tokens += redundant_tokens
        
        detail_table.append({
            'status': status,
            'operation': op,
            'call_count': call_count,
            'avg_system_tokens': int(avg_system_tokens),
            'avg_user_tokens': int(avg_user_tokens),
            'avg_context_tokens': int(avg_context_tokens),
            'total_system_tokens': total_system_tokens,
            'avg_prompt_tokens': int(avg_prompt_tokens),
            'system_pct': system_pct,
            'system_pct_formatted': format_percentage(system_pct),
            'redundant_tokens': redundant_tokens,
            'has_waste': has_waste,
        })
    
    # Sort by redundant tokens (most waste first)
    detail_table.sort(key=lambda x: -x['redundant_tokens'])
    
    # Chart data
    chart_data = [
        {
            'name': row['operation'],
            'system': row['avg_system_tokens'],
            'user': row['avg_user_tokens'],
            'context': row['avg_context_tokens'],
        }
        for row in detail_table[:10]
    ]
    
    # Calculate global metrics
    global_total_system_tokens = sum(all_system_tokens)
    largest_system_prompt = max(all_system_tokens) if all_system_tokens else 0
    
    # Top offender
    top_offender = None
    if ops_with_waste:
        ops_with_waste.sort(key=lambda x: -x[1])
        top_op, top_redundant, top_avg_system, top_calls = ops_with_waste[0]
        
        agent, operation = top_op.split('.', 1) if '.' in top_op else ('Unknown', top_op)
        
        recommendation = _get_system_prompt_recommendation(top_avg_system, len(top_calls))
        
        top_offender = TopOffender(
            agent=agent,
            operation=operation,
            value=top_redundant,
            value_formatted=format_tokens(top_redundant),
            call_count=len(top_calls),
            diagnosis=recommendation,
        )
    
    # Health score
    issue_count = len(ops_with_waste)
    if total_redundant_tokens > 50000:
        health_score = max(40, 60 - (issue_count * 5))
        status = "error"
    elif issue_count > 0:
        health_score = max(70, 90 - (issue_count * 5))
        status = "warning"
    else:
        health_score = 100.0
        status = "ok"
    
    # Calculate averages
    avg_system = sum(all_system_tokens) / len(all_system_tokens) if all_system_tokens else 0
    avg_user = sum((c.get('prompt_breakdown') or {}).get('user_message_tokens', 0) for c in llm_calls) / len(llm_calls)
    avg_context = sum((c.get('prompt_breakdown') or {}).get('chat_history_tokens', 0) for c in llm_calls) / len(llm_calls)
    
    return SystemPromptStoryResponse(
        status=status,
        health_score=health_score,
        summary=SystemPromptSummary(
            total_calls=len(llm_calls),
            issue_count=issue_count,
            avg_system_tokens=int(avg_system),
            avg_user_tokens=int(avg_user),
            avg_context_tokens=int(avg_context),
            total_system_tokens=global_total_system_tokens,
            largest_system_prompt=largest_system_prompt,
            total_redundant_tokens=total_redundant_tokens,
        ),
        top_offender=top_offender,
        detail_table=detail_table,
        chart_data=chart_data,
        recommendations=get_story_recommendations('system_prompt'),
    )


def _get_system_prompt_recommendation(avg_tokens: float, call_count: int) -> str:
    """Get recommendation for system prompt optimization."""
    if avg_tokens > 1500:
        return "Compress system prompt (can often reduce by 60-70%)"
    elif call_count > 10:
        return "Enable prompt caching for repeated system prompts"
    else:
        return "Consider prompt caching or compression"