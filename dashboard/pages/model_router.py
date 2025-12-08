"""
Model Router - Developer Diagnostic Dashboard
Location: dashboard/pages/model_router.py

Developer-focused diagnostic tool that surfaces:
- WHERE inefficiencies exist in your LLM calls
- WHY they're happening (root cause with prompt breakdown)
- HOW to fix them (specific routing recommendations with code)

Tabs:
1. Overview - Aggregated patterns and quick wins
2. Latency - Slow calls and why
3. Cost - Expensive calls and why
4. Quality - Failed/poor calls and why
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict
import re

from dashboard.utils.data_fetcher import (
    get_project_overview,
    get_llm_calls,
)
from dashboard.utils.formatters import (
    format_cost,
    format_latency,
    format_tokens,
    format_percentage,
    format_model_name,
    truncate_text,
)
from dashboard.components.metric_cards import render_empty_state
from dashboard.components.charts import create_bar_chart


# =============================================================================
# CONSTANTS
# =============================================================================

PREMIUM_MODELS = ['gpt-4o', 'gpt-4', 'gpt-4-turbo', 'claude-3-opus', 'claude-3-5-sonnet']
MID_TIER_MODELS = ['gpt-3.5-turbo', 'claude-3-sonnet', 'claude-3-haiku']
BUDGET_MODELS = ['mistral-small', 'mistral-tiny', 'mixtral']

LATENCY_THRESHOLD_MS = 10000  # 10 seconds
COST_THRESHOLD = 0.05  # $0.05
QUALITY_THRESHOLD = 7.0  # Score out of 10


# =============================================================================
# PROMPT PARSING & ANALYSIS
# =============================================================================

def parse_prompt_components(call: Dict) -> Dict[str, Any]:
    """
    Parse prompt into components: system prompt, chat history, user message.
    
    Attempts to extract from metadata first, then estimates from prompt text.
    """
    metadata = call.get('metadata', {}) or {}
    prompt_text = call.get('prompt', '') or ''
    prompt_tokens = call.get('prompt_tokens', 0)
    
    # Try to get from metadata (ideal case - instrumented code)
    if metadata.get('system_prompt_tokens'):
        return {
            'system_prompt': metadata.get('system_prompt', '')[:500],
            'system_prompt_tokens': metadata.get('system_prompt_tokens', 0),
            'chat_history': metadata.get('chat_history', []),
            'chat_history_tokens': metadata.get('chat_history_tokens', 0),
            'chat_history_count': metadata.get('chat_history_count', 0),
            'user_message': metadata.get('user_message', '')[:500],
            'user_message_tokens': metadata.get('user_message_tokens', 0),
            'parsed_from': 'metadata'
        }
    
    # Estimate from prompt text
    return estimate_prompt_components(prompt_text, prompt_tokens)


def estimate_prompt_components(prompt_text: str, total_prompt_tokens: int) -> Dict[str, Any]:
    """Estimate prompt components when not available in metadata."""
    
    if not prompt_text:
        return {
            'system_prompt': '',
            'system_prompt_tokens': 0,
            'chat_history': [],
            'chat_history_tokens': 0,
            'chat_history_count': 0,
            'user_message': '',
            'user_message_tokens': total_prompt_tokens,
            'parsed_from': 'estimated_no_prompt'
        }
    
    # Count message patterns to estimate chat history
    message_patterns = [
        r'Human:|User:|Assistant:|AI:|\[User\]|\[Assistant\]',
        r'Message \d+:',
        r'<human>|<assistant>|<user>',
    ]
    
    message_count = 0
    for pattern in message_patterns:
        matches = re.findall(pattern, prompt_text, re.IGNORECASE)
        message_count = max(message_count, len(matches))
    
    # Estimate token distribution
    # Rough heuristic: 1 token ≈ 4 characters
    total_chars = len(prompt_text)
    
    # Look for system prompt markers
    system_markers = ['You are', 'System:', '<system>', 'Instructions:']
    has_system = any(marker in prompt_text[:1000] for marker in system_markers)
    
    if message_count > 1:
        # Has chat history
        # Estimate: system = 25%, history = proportional to message count, user = remainder
        system_pct = 0.25 if has_system else 0.10
        history_pct = min(0.60, message_count * 0.08)
        user_pct = 1 - system_pct - history_pct
        
        system_tokens = int(total_prompt_tokens * system_pct)
        history_tokens = int(total_prompt_tokens * history_pct)
        user_tokens = int(total_prompt_tokens * user_pct)
    else:
        # No chat history detected
        system_tokens = int(total_prompt_tokens * 0.30) if has_system else 0
        history_tokens = 0
        user_tokens = total_prompt_tokens - system_tokens
    
    # Extract preview text
    system_preview = prompt_text[:500] if has_system else ''
    user_preview = prompt_text[-500:] if len(prompt_text) > 500 else prompt_text
    
    return {
        'system_prompt': system_preview,
        'system_prompt_tokens': system_tokens,
        'chat_history': [],
        'chat_history_tokens': history_tokens,
        'chat_history_count': message_count,
        'user_message': user_preview,
        'user_message_tokens': user_tokens,
        'parsed_from': 'estimated'
    }


def analyze_call(call: Dict) -> Dict[str, Any]:
    """Analyze a single call and identify issues."""
    
    components = parse_prompt_components(call)
    total_tokens = call.get('total_tokens', 0)
    prompt_tokens = call.get('prompt_tokens', 0)
    completion_tokens = call.get('completion_tokens', 0)
    latency_ms = call.get('latency_ms', 0)
    cost = call.get('total_cost', 0)
    success = call.get('success', True)
    model = call.get('model_name', 'unknown')
    
    # Get quality score if available
    quality_eval = call.get('quality_evaluation') or {}
    quality_score = quality_eval.get('judge_score') or quality_eval.get('score')
    hallucination = quality_eval.get('hallucination_flag', False)
    
    # Calculate percentages
    system_pct = (components['system_prompt_tokens'] / prompt_tokens * 100) if prompt_tokens > 0 else 0
    history_pct = (components['chat_history_tokens'] / prompt_tokens * 100) if prompt_tokens > 0 else 0
    user_pct = (components['user_message_tokens'] / prompt_tokens * 100) if prompt_tokens > 0 else 0
    response_pct = (completion_tokens / total_tokens * 100) if total_tokens > 0 else 0
    
    # Identify issues
    issues = []
    
    # LATENCY ISSUES
    if latency_ms > LATENCY_THRESHOLD_MS:
        if components['chat_history_count'] > 6:
            issues.append({
                'type': 'LATENCY',
                'cause': 'LONG_CONVERSATION_HISTORY',
                'severity': 'high',
                'detail': f"{components['chat_history_count']} messages in history ({history_pct:.0f}% of prompt)",
                'fix': 'sliding_window',
                'fix_description': 'Implement sliding window to keep only last 6 messages',
            })
        elif components['system_prompt_tokens'] > 3000:
            issues.append({
                'type': 'LATENCY',
                'cause': 'LARGE_SYSTEM_PROMPT',
                'severity': 'medium',
                'detail': f"System prompt is {components['system_prompt_tokens']:,} tokens ({system_pct:.0f}%)",
                'fix': 'prompt_compression',
                'fix_description': 'Compress or cache system prompt, use references instead of full context',
            })
        elif model in PREMIUM_MODELS and total_tokens < 2000:
            issues.append({
                'type': 'LATENCY',
                'cause': 'SLOW_MODEL_SIMPLE_TASK',
                'severity': 'medium',
                'detail': f"Using {model} for small request ({total_tokens:,} tokens)",
                'fix': 'model_routing',
                'fix_description': 'Route simple tasks to faster models (Mistral, Haiku)',
            })
    
    # COST ISSUES
    if cost > COST_THRESHOLD:
        is_premium = any(p in model.lower() for p in ['gpt-4', 'opus', 'sonnet'])
        
        if components['user_message_tokens'] < 200 and is_premium:
            issues.append({
                'type': 'COST',
                'cause': 'SIMPLE_MESSAGE_EXPENSIVE_MODEL',
                'severity': 'high',
                'detail': f"Simple message ({components['user_message_tokens']} tokens) using {model}",
                'fix': 'intent_routing',
                'fix_description': 'Detect simple messages and route to budget models',
            })
        elif components['chat_history_tokens'] > 5000:
            issues.append({
                'type': 'COST',
                'cause': 'EXPENSIVE_HISTORY',
                'severity': 'high',
                'detail': f"Chat history consuming {components['chat_history_tokens']:,} tokens ({history_pct:.0f}%)",
                'fix': 'sliding_window',
                'fix_description': 'Limit conversation history to reduce token usage',
            })
        elif is_premium and total_tokens < 3000:
            issues.append({
                'type': 'COST',
                'cause': 'PREMIUM_MODEL_SIMPLE_TASK',
                'severity': 'medium',
                'detail': f"Using {model} for {total_tokens:,} token request",
                'fix': 'model_routing',
                'fix_description': 'Route to GPT-3.5 or Claude Haiku for simple tasks',
            })
    
    # QUALITY ISSUES
    if not success:
        issues.append({
            'type': 'QUALITY',
            'cause': 'CALL_FAILED',
            'severity': 'high',
            'detail': f"Call failed: {call.get('error', 'Unknown error')[:100]}",
            'fix': 'error_handling',
            'fix_description': 'Add retry logic or fallback to different model',
        })
    elif quality_score is not None and quality_score < QUALITY_THRESHOLD:
        is_budget = any(b in model.lower() for b in ['mistral', 'haiku', '3.5'])
        if is_budget:
            issues.append({
                'type': 'QUALITY',
                'cause': 'MODEL_TOO_WEAK',
                'severity': 'high',
                'detail': f"Quality score {quality_score:.1f}/10 with {model}",
                'fix': 'upgrade_model',
                'fix_description': 'Use stronger model for complex tasks',
            })
        else:
            issues.append({
                'type': 'QUALITY',
                'cause': 'LOW_QUALITY_OUTPUT',
                'severity': 'medium',
                'detail': f"Quality score {quality_score:.1f}/10",
                'fix': 'prompt_improvement',
                'fix_description': 'Review and improve prompt structure',
            })
    
    if hallucination:
        issues.append({
            'type': 'QUALITY',
            'cause': 'HALLUCINATION',
            'severity': 'high',
            'detail': 'Hallucination detected in response',
            'fix': 'grounding',
            'fix_description': 'Add grounding context or use RAG',
        })
    
    return {
        'call': call,
        'components': components,
        'issues': issues,
        'metrics': {
            'latency_ms': latency_ms,
            'cost': cost,
            'total_tokens': total_tokens,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'quality_score': quality_score,
            'success': success,
        },
        'percentages': {
            'system': system_pct,
            'history': history_pct,
            'user': user_pct,
            'response': response_pct,
        }
    }


def calculate_fix_impact(analysis: Dict, fix_type: str) -> Dict[str, Any]:
    """Calculate the potential impact of applying a fix."""
    
    metrics = analysis['metrics']
    components = analysis['components']
    model = analysis['call'].get('model_name', '')
    
    if fix_type == 'sliding_window':
        # Estimate: keep 6 messages, remove the rest
        current_history = components['chat_history_count']
        if current_history > 6:
            reduction_ratio = 6 / current_history
            new_history_tokens = int(components['chat_history_tokens'] * reduction_ratio)
            tokens_saved = components['chat_history_tokens'] - new_history_tokens
            
            token_reduction = tokens_saved / metrics['total_tokens'] if metrics['total_tokens'] > 0 else 0
            new_cost = metrics['cost'] * (1 - token_reduction)
            new_latency = metrics['latency_ms'] * (1 - token_reduction * 0.8)  # Latency doesn't scale linearly
            
            return {
                'tokens_saved': tokens_saved,
                'new_cost': new_cost,
                'cost_savings': metrics['cost'] - new_cost,
                'cost_savings_pct': token_reduction * 100,
                'new_latency_ms': new_latency,
                'latency_improvement_pct': (1 - new_latency / metrics['latency_ms']) * 100 if metrics['latency_ms'] > 0 else 0,
            }
    
    elif fix_type in ['model_routing', 'intent_routing']:
        # Estimate switching to cheaper/faster model
        current_cost_per_token = metrics['cost'] / metrics['total_tokens'] if metrics['total_tokens'] > 0 else 0
        
        # Rough estimates for model costs
        if 'gpt-4' in model.lower() or 'opus' in model.lower():
            new_cost = metrics['cost'] * 0.15  # Switch to Mistral/Haiku
            new_latency = metrics['latency_ms'] * 0.4
        elif 'sonnet' in model.lower():
            new_cost = metrics['cost'] * 0.25
            new_latency = metrics['latency_ms'] * 0.5
        else:
            new_cost = metrics['cost'] * 0.5
            new_latency = metrics['latency_ms'] * 0.6
        
        return {
            'new_cost': new_cost,
            'cost_savings': metrics['cost'] - new_cost,
            'cost_savings_pct': (1 - new_cost / metrics['cost']) * 100 if metrics['cost'] > 0 else 0,
            'new_latency_ms': new_latency,
            'latency_improvement_pct': (1 - new_latency / metrics['latency_ms']) * 100 if metrics['latency_ms'] > 0 else 0,
        }
    
    elif fix_type == 'upgrade_model':
        # Quality fix - costs more but improves quality
        return {
            'new_cost': metrics['cost'] * 2,
            'cost_increase': metrics['cost'],
            'expected_quality_improvement': '+1-2 points',
        }
    
    return {}


# =============================================================================
# RENDERING FUNCTIONS
# =============================================================================

def render_token_breakdown_bar(components: Dict, total_tokens: int):
    """Render a visual token breakdown bar."""
    
    system_pct = components['system_prompt_tokens'] / total_tokens * 100 if total_tokens > 0 else 0
    history_pct = components['chat_history_tokens'] / total_tokens * 100 if total_tokens > 0 else 0
    user_pct = components['user_message_tokens'] / total_tokens * 100 if total_tokens > 0 else 0
    
    st.markdown(f"""
    **Token Breakdown:**
    
    | Component | Tokens | % |
    |-----------|--------|---|
    | System Prompt | {components['system_prompt_tokens']:,} | {system_pct:.0f}% |
    | Chat History ({components['chat_history_count']} msgs) | {components['chat_history_tokens']:,} | {history_pct:.0f}% |
    | User Message | {components['user_message_tokens']:,} | {user_pct:.0f}% |
    """)


def render_issue_card(analysis: Dict, issue: Dict, show_prompt: bool = True):
    """Render a detailed issue card with prompt breakdown and fix."""
    
    call = analysis['call']
    components = analysis['components']
    metrics = analysis['metrics']
    
    # Header
    severity_icon = "🔴" if issue['severity'] == 'high' else "🟡"
    
    st.markdown(f"### {severity_icon} {issue['cause'].replace('_', ' ').title()}")
    st.caption(f"{call.get('operation', 'unknown')} • {call.get('agent_name', 'unknown')} • {format_model_name(call.get('model_name', ''))}")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Metrics
        st.markdown("**Metrics:**")
        st.write(f"- Latency: {format_latency(metrics['latency_ms'])}")
        st.write(f"- Cost: {format_cost(metrics['cost'])}")
        st.write(f"- Tokens: {metrics['total_tokens']:,}")
        if metrics['quality_score']:
            st.write(f"- Quality: {metrics['quality_score']:.1f}/10")
        
        # Root cause
        st.markdown("**Root Cause:**")
        st.error(issue['detail'])
    
    with col2:
        # Token breakdown
        render_token_breakdown_bar(components, metrics['prompt_tokens'])
    
    # Prompt preview
    if show_prompt:
        with st.expander("📝 View Prompt Details"):
            if components['system_prompt']:
                st.markdown("**System Prompt Preview:**")
                st.code(truncate_text(components['system_prompt'], 300), language="text")
            
            if components['chat_history_count'] > 0:
                st.markdown(f"**Chat History:** {components['chat_history_count']} messages")
                st.caption(f"({components['chat_history_tokens']:,} tokens)")
            
            if components['user_message']:
                st.markdown("**User Message:**")
                st.code(truncate_text(components['user_message'], 300), language="text")
            
            if call.get('response_text'):
                st.markdown("**Response Preview:**")
                st.code(truncate_text(call['response_text'], 300), language="text")
    
    # Fix recommendation
    impact = calculate_fix_impact(analysis, issue['fix'])
    
    st.markdown("**🛠️ Recommended Fix:**")
    st.info(issue['fix_description'])
    
    if impact:
        if 'cost_savings' in impact:
            st.success(f"**Impact:** Save {format_cost(impact['cost_savings'])} ({impact['cost_savings_pct']:.0f}% reduction)")
        if 'latency_improvement_pct' in impact and impact['latency_improvement_pct'] > 0:
            st.success(f"**Latency:** {impact['latency_improvement_pct']:.0f}% faster")
    
    # Code snippet
    with st.expander("📋 Implementation Code"):
        if issue['fix'] == 'sliding_window':
            st.code('''
def get_chat_history(messages: list, max_messages: int = 6) -> list:
    """Keep only the most recent messages."""
    if len(messages) <= max_messages:
        return messages
    # Keep first message (context) + last N-1 messages
    return [messages[0]] + messages[-(max_messages-1):]

# Usage in your chat function:
history = get_chat_history(conversation.messages, max_messages=6)
            ''', language='python')
        
        elif issue['fix'] in ['model_routing', 'intent_routing']:
            st.code(f'''
def select_model(user_message: str, operation: str, token_count: int) -> str:
    """Route to appropriate model based on task complexity."""
    
    # Simple messages → budget model
    simple_patterns = ["thanks", "ok", "got it", "yes", "no", "hello"]
    if any(p in user_message.lower() for p in simple_patterns):
        return "mistral-small"
    
    # Structured tasks → mid-tier
    if operation in ["generate_sql", "extract_entities", "classify"]:
        return "gpt-3.5-turbo"
    
    # Low token count → don't need premium
    if token_count < 1500:
        return "claude-3-haiku"
    
    # Complex tasks → premium
    return "gpt-4o"

# Current call would route: {call.get('model_name')} → mistral-small
            ''', language='python')
        
        elif issue['fix'] == 'upgrade_model':
            st.code('''
def select_model_for_complex_task(task_type: str, previous_failures: int = 0) -> str:
    """Upgrade model for complex tasks or after failures."""
    
    if previous_failures > 0:
        return "gpt-4o"  # Fallback to strongest
    
    complexity_map = {
        "simple_sql": "mistral-small",
        "complex_sql": "gpt-3.5-turbo",  
        "analysis": "claude-3-sonnet",
        "reasoning": "gpt-4o",
    }
    
    return complexity_map.get(task_type, "claude-3-sonnet")
            ''', language='python')


def render_overview_tab(analyses: List[Dict]):
    """Render the Overview tab with aggregated patterns."""
    
    st.subheader("📊 Routing Opportunities Overview")
    
    # Count issues by type
    latency_issues = [a for a in analyses if any(i['type'] == 'LATENCY' for i in a['issues'])]
    cost_issues = [a for a in analyses if any(i['type'] == 'COST' for i in a['issues'])]
    quality_issues = [a for a in analyses if any(i['type'] == 'QUALITY' for i in a['issues'])]
    optimized = [a for a in analyses if not a['issues']]
    
    # Calculate total potential savings
    total_cost_savings = 0
    for analysis in analyses:
        for issue in analysis['issues']:
            if issue['type'] in ['COST', 'LATENCY']:
                impact = calculate_fix_impact(analysis, issue['fix'])
                total_cost_savings += impact.get('cost_savings', 0)
    
    # Summary KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🐌 Latency Issues", len(latency_issues), help="Calls > 10s")
    with col2:
        st.metric("💸 Cost Issues", len(cost_issues), help="Calls > $0.05")
    with col3:
        st.metric("⚠️ Quality Issues", len(quality_issues), help="Failed or low quality")
    with col4:
        st.metric("✅ Optimized", len(optimized), help="No issues detected")
    
    if total_cost_savings > 0:
        st.success(f"💰 **Total Savings Opportunity:** {format_cost(total_cost_savings)}/period (~{format_cost(total_cost_savings * 30)}/month)")
    
    st.divider()
    
    # Aggregate patterns
    st.subheader("🔍 Common Patterns")
    
    pattern_counts = defaultdict(lambda: {'count': 0, 'total_cost': 0, 'calls': []})
    
    for analysis in analyses:
        for issue in analysis['issues']:
            key = issue['cause']
            pattern_counts[key]['count'] += 1
            pattern_counts[key]['total_cost'] += analysis['metrics']['cost']
            pattern_counts[key]['calls'].append(analysis)
    
    if pattern_counts:
        pattern_data = []
        for cause, data in sorted(pattern_counts.items(), key=lambda x: x[1]['count'], reverse=True):
            # Calculate potential savings for this pattern
            pattern_savings = 0
            for analysis in data['calls']:
                for issue in analysis['issues']:
                    if issue['cause'] == cause:
                        impact = calculate_fix_impact(analysis, issue['fix'])
                        pattern_savings += impact.get('cost_savings', 0)
            
            pattern_data.append({
                'Pattern': cause.replace('_', ' ').title(),
                'Calls': data['count'],
                'Total Cost': format_cost(data['total_cost']),
                'Fix Savings': format_cost(pattern_savings),
                'Fix': data['calls'][0]['issues'][0]['fix'] if data['calls'] and data['calls'][0]['issues'] else '',
            })
        
        df = pd.DataFrame(pattern_data)
        st.dataframe(df, width='stretch', hide_index=True)
    else:
        st.info("No patterns detected - your calls look well optimized!")
    
    st.divider()
    
    # Quick wins
    st.subheader("🎯 Quick Wins")
    st.caption("Highest impact fixes you can implement now")
    
    # Find top 3 opportunities
    opportunities = []
    for analysis in analyses:
        for issue in analysis['issues']:
            impact = calculate_fix_impact(analysis, issue['fix'])
            savings = impact.get('cost_savings', 0)
            if savings > 0:
                opportunities.append({
                    'analysis': analysis,
                    'issue': issue,
                    'savings': savings,
                })
    
    opportunities.sort(key=lambda x: x['savings'], reverse=True)
    
    for i, opp in enumerate(opportunities[:3], 1):
        call = opp['analysis']['call']
        st.markdown(f"**{i}. {opp['issue']['fix_description']}**")
        st.caption(f"{call.get('operation')} • Save {format_cost(opp['savings'])}")
        st.divider()


def render_issue_tab(analyses: List[Dict], issue_type: str, threshold_label: str):
    """Render a tab showing issues of a specific type."""
    
    # Filter to issues of this type
    filtered = [a for a in analyses if any(i['type'] == issue_type for i in a['issues'])]
    
    if not filtered:
        st.success(f"✅ No {issue_type.lower()} issues detected!")
        st.caption(f"All calls are within acceptable {threshold_label} thresholds.")
        return
    
    st.subheader(f"{len(filtered)} calls with {issue_type.lower()} issues")
    
    # Sort by severity and impact
    def sort_key(a):
        issue = next((i for i in a['issues'] if i['type'] == issue_type), None)
        if not issue:
            return 0
        if issue_type == 'LATENCY':
            return a['metrics']['latency_ms']
        elif issue_type == 'COST':
            return a['metrics']['cost']
        else:
            return 10 - (a['metrics'].get('quality_score') or 10)
    
    filtered.sort(key=sort_key, reverse=True)
    
    # Show top issues
    for i, analysis in enumerate(filtered[:10], 1):
        issue = next((i for i in analysis['issues'] if i['type'] == issue_type), None)
        if issue:
            call = analysis['call']
            
            # Summary line
            if issue_type == 'LATENCY':
                summary = f"#{i} — {format_latency(analysis['metrics']['latency_ms'])} — {call.get('operation', 'unknown')}"
            elif issue_type == 'COST':
                summary = f"#{i} — {format_cost(analysis['metrics']['cost'])} — {call.get('operation', 'unknown')}"
            else:
                score = analysis['metrics'].get('quality_score', 'N/A')
                summary = f"#{i} — Score: {score}/10 — {call.get('operation', 'unknown')}"
            
            with st.expander(summary, expanded=(i == 1)):
                render_issue_card(analysis, issue, show_prompt=True)
            
            st.divider()
    
    if len(filtered) > 10:
        st.caption(f"Showing top 10 of {len(filtered)} issues")


# =============================================================================
# MAIN RENDER
# =============================================================================

def render():
    """Main render function for Model Router page."""
    
    st.title("🔀 Model Router — Diagnostics")
    st.caption("Find inefficiencies in your LLM calls and how to fix them")
    
    # Get selected project
    selected_project = st.session_state.get('selected_project')
    
    # Controls
    col1, col2 = st.columns([3, 1])
    with col1:
        if selected_project:
            st.info(f"Analyzing: **{selected_project}**")
    with col2:
        if st.button("🔄 Refresh", width='stretch'):
            st.cache_data.clear()
            st.rerun()
    
    st.divider()
    
    # Load and analyze data
    try:
        calls = get_llm_calls(project_name=selected_project, limit=500)
        
        if not calls:
            render_empty_state(
                message="No LLM calls found",
                icon="🔀",
                suggestion="Start making LLM calls with Observatory tracking enabled"
            )
            return
        
        # Analyze all calls
        with st.spinner("Analyzing calls..."):
            analyses = [analyze_call(call) for call in calls]
        
        # Create tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            f"📊 Overview",
            f"🐌 Latency",
            f"💸 Cost",
            f"⚠️ Quality"
        ])
        
        with tab1:
            render_overview_tab(analyses)
        
        with tab2:
            st.subheader("🐌 Latency Issues")
            st.caption(f"Calls taking longer than {LATENCY_THRESHOLD_MS/1000:.0f} seconds")
            render_issue_tab(analyses, 'LATENCY', 'latency')
        
        with tab3:
            st.subheader("💸 Cost Issues")
            st.caption(f"Calls costing more than {format_cost(COST_THRESHOLD)}")
            render_issue_tab(analyses, 'COST', 'cost')
        
        with tab4:
            st.subheader("⚠️ Quality Issues")
            st.caption(f"Calls with quality score < {QUALITY_THRESHOLD} or failures")
            render_issue_tab(analyses, 'QUALITY', 'quality')
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        import traceback
        st.code(traceback.format_exc())