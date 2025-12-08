"""
Prompt Optimizer - Prompt Diagnostics Dashboard
Location: dashboard/pages/prompt_optimizer.py

Developer-focused prompt analysis:
1. Overview - Prompt health summary
2. Long Prompts - Token reduction opportunities
3. Low Performers - Quality-correlated prompt issues
4. Compare - Side-by-side prompt comparison
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
from collections import defaultdict
import difflib
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


# =============================================================================
# CONSTANTS
# =============================================================================

LONG_PROMPT_THRESHOLD = 4000  # tokens
VERY_LONG_PROMPT_THRESHOLD = 8000  # tokens
LOW_QUALITY_THRESHOLD = 7.0


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def parse_prompt_components(call: Dict) -> Dict[str, Any]:
    """Parse prompt into components."""
    
    metadata = call.get('metadata', {}) or {}
    prompt = call.get('prompt', '') or ''
    prompt_tokens = call.get('prompt_tokens', 0)
    
    # Try metadata first
    if metadata.get('system_prompt_tokens'):
        return {
            'system_prompt': metadata.get('system_prompt', '')[:500],
            'system_prompt_tokens': metadata.get('system_prompt_tokens', 0),
            'chat_history_tokens': metadata.get('chat_history_tokens', 0),
            'chat_history_count': metadata.get('chat_history_count', 0),
            'user_message': metadata.get('user_message', '')[:300],
            'user_message_tokens': metadata.get('user_message_tokens', 0),
            'has_breakdown': True,
        }
    
    # Estimate from prompt
    has_history = bool(re.search(r'Human:|User:|Assistant:|AI:', prompt, re.I))
    message_count = len(re.findall(r'Human:|User:|Assistant:|AI:', prompt, re.I))
    
    # Rough estimation
    if has_history and message_count > 2:
        system_pct = 0.25
        history_pct = min(0.60, message_count * 0.08)
        user_pct = 1 - system_pct - history_pct
    else:
        system_pct = 0.30
        history_pct = 0
        user_pct = 0.70
    
    return {
        'system_prompt': prompt[:500],
        'system_prompt_tokens': int(prompt_tokens * system_pct),
        'chat_history_tokens': int(prompt_tokens * history_pct),
        'chat_history_count': message_count,
        'user_message': prompt[-300:],
        'user_message_tokens': int(prompt_tokens * user_pct),
        'has_breakdown': False,
    }


def analyze_prompt_health(calls: List[Dict]) -> Dict[str, Any]:
    """Analyze overall prompt health."""
    
    total = len(calls)
    
    # Categorize prompts
    long_prompts = []
    low_quality_prompts = []
    
    by_operation = defaultdict(lambda: {
        'calls': [],
        'total_tokens': 0,
        'scores': [],
    })
    
    for call in calls:
        prompt_tokens = call.get('prompt_tokens', 0)
        op = call.get('operation', 'unknown')
        
        by_operation[op]['calls'].append(call)
        by_operation[op]['total_tokens'] += prompt_tokens
        
        qual = call.get('quality_evaluation') or {}
        if qual.get('score') is not None:
            by_operation[op]['scores'].append(qual['score'])
        
        if prompt_tokens > LONG_PROMPT_THRESHOLD:
            long_prompts.append(call)
        
        if qual.get('score') is not None and qual['score'] < LOW_QUALITY_THRESHOLD:
            low_quality_prompts.append(call)
    
    # Calculate per-operation stats
    operations = []
    for op, stats in by_operation.items():
        avg_tokens = stats['total_tokens'] / len(stats['calls'])
        avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else None
        
        # Determine status
        if avg_tokens > VERY_LONG_PROMPT_THRESHOLD:
            status = 'VERY_LONG'
        elif avg_tokens > LONG_PROMPT_THRESHOLD:
            status = 'LONG'
        elif avg_score and avg_score < LOW_QUALITY_THRESHOLD:
            status = 'LOW_QUALITY'
        else:
            status = 'HEALTHY'
        
        operations.append({
            'operation': op,
            'call_count': len(stats['calls']),
            'avg_tokens': avg_tokens,
            'avg_score': avg_score,
            'status': status,
        })
    
    operations.sort(key=lambda x: -x['avg_tokens'])
    
    return {
        'total_calls': total,
        'long_prompt_count': len(long_prompts),
        'low_quality_count': len(low_quality_prompts),
        'avg_prompt_tokens': sum(c.get('prompt_tokens', 0) for c in calls) / total if total > 0 else 0,
        'operations': operations,
    }


def find_long_prompts(calls: List[Dict]) -> List[Dict]:
    """Find calls with long prompts and analyze reduction opportunities."""
    
    long_prompts = []
    
    for call in calls:
        prompt_tokens = call.get('prompt_tokens', 0)
        
        if prompt_tokens > LONG_PROMPT_THRESHOLD:
            components = parse_prompt_components(call)
            
            # Identify optimization opportunities
            opportunities = []
            potential_savings = 0
            
            # Check for long chat history
            if components['chat_history_count'] > 6:
                history_reduction = components['chat_history_tokens'] * 0.5  # Keep ~half
                opportunities.append({
                    'type': 'SLIDING_WINDOW',
                    'description': f"Limit chat history from {components['chat_history_count']} to 6 messages",
                    'token_savings': int(history_reduction),
                })
                potential_savings += history_reduction
            
            # Check for large system prompt
            if components['system_prompt_tokens'] > 2000:
                system_reduction = components['system_prompt_tokens'] * 0.4  # 40% reduction possible
                opportunities.append({
                    'type': 'COMPRESS_SYSTEM',
                    'description': "Compress or summarize system prompt content",
                    'token_savings': int(system_reduction),
                })
                potential_savings += system_reduction
            
            # Calculate cost savings
            cost_per_token = call.get('total_cost', 0) / call.get('total_tokens', 1) if call.get('total_tokens', 0) > 0 else 0
            cost_savings = potential_savings * cost_per_token
            
            long_prompts.append({
                'call': call,
                'prompt_tokens': prompt_tokens,
                'components': components,
                'opportunities': opportunities,
                'potential_savings_tokens': int(potential_savings),
                'potential_savings_cost': cost_savings,
                'reduction_pct': potential_savings / prompt_tokens if prompt_tokens > 0 else 0,
            })
    
    # Sort by potential savings
    long_prompts.sort(key=lambda x: -x['potential_savings_tokens'])
    
    return long_prompts


def find_low_performers(calls: List[Dict]) -> List[Dict]:
    """Find prompts correlated with low quality."""
    
    low_performers = []
    
    for call in calls:
        qual = call.get('quality_evaluation') or {}
        if qual.get('score') is None:
            continue
        
        score = qual['score']
        if score < LOW_QUALITY_THRESHOLD:
            components = parse_prompt_components(call)
            
            # Analyze potential prompt issues
            issues = []
            
            prompt = call.get('prompt', '')
            
            # Check for vague instructions
            if not any(word in prompt.lower() for word in ['must', 'should', 'always', 'never', 'required']):
                issues.append({
                    'type': 'VAGUE_INSTRUCTIONS',
                    'description': 'Prompt lacks explicit requirements or constraints',
                    'fix': 'Add specific requirements: "You must...", "Always include..."',
                })
            
            # Check for missing examples
            if 'example' not in prompt.lower() and 'e.g.' not in prompt.lower():
                issues.append({
                    'type': 'NO_EXAMPLES',
                    'description': 'Prompt has no examples to guide output',
                    'fix': 'Add 1-2 examples of expected output format',
                })
            
            # Check for missing output format
            if not any(word in prompt.lower() for word in ['format', 'json', 'markdown', 'structure', 'return']):
                issues.append({
                    'type': 'NO_FORMAT',
                    'description': 'No output format specification',
                    'fix': 'Specify expected output format explicitly',
                })
            
            low_performers.append({
                'call': call,
                'score': score,
                'components': components,
                'issues': issues,
                'judge_feedback': qual.get('reasoning', qual.get('judge_feedback', '')),
            })
    
    # Sort by score (lowest first)
    low_performers.sort(key=lambda x: x['score'])
    
    return low_performers


def generate_prompt_diff(prompt_a: str, prompt_b: str) -> List[Dict]:
    """Generate diff between two prompts."""
    
    lines_a = prompt_a.split('\n')
    lines_b = prompt_b.split('\n')
    
    differ = difflib.unified_diff(lines_a, lines_b, lineterm='', n=3)
    
    changes = []
    for line in differ:
        if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
            continue
        elif line.startswith('+'):
            changes.append({'type': 'add', 'text': line[1:]})
        elif line.startswith('-'):
            changes.append({'type': 'remove', 'text': line[1:]})
        else:
            changes.append({'type': 'same', 'text': line})
    
    return changes


# =============================================================================
# RENDERING FUNCTIONS
# =============================================================================

def render_prompt_health_banner(health: Dict):
    """Render prompt health banner."""
    
    long_count = health['long_prompt_count']
    low_qual_count = health['low_quality_count']
    
    if long_count > 10 or low_qual_count > 5:
        st.error(f"🔴 **Prompt Issues Detected** — {long_count} long prompts, {low_qual_count} low-quality outputs")
    elif long_count > 0 or low_qual_count > 0:
        st.warning(f"🟡 **{long_count} prompts need optimization** — Avg {format_tokens(int(health['avg_prompt_tokens']))} tokens/prompt")
    else:
        st.success(f"🟢 **Prompts Healthy** — Avg {format_tokens(int(health['avg_prompt_tokens']))} tokens/prompt")


def render_token_breakdown(components: Dict, total_tokens: int):
    """Render token breakdown visualization."""
    
    system_pct = components['system_prompt_tokens'] / total_tokens * 100 if total_tokens > 0 else 0
    history_pct = components['chat_history_tokens'] / total_tokens * 100 if total_tokens > 0 else 0
    user_pct = components['user_message_tokens'] / total_tokens * 100 if total_tokens > 0 else 0
    
    st.markdown("**Token Breakdown:**")
    
    data = {
        'Component': ['System Prompt', 'Chat History', 'User Message'],
        'Tokens': [
            f"{components['system_prompt_tokens']:,}",
            f"{components['chat_history_tokens']:,} ({components['chat_history_count']} msgs)",
            f"{components['user_message_tokens']:,}",
        ],
        '%': [f"{system_pct:.0f}%", f"{history_pct:.0f}%", f"{user_pct:.0f}%"],
    }
    
    st.dataframe(pd.DataFrame(data), width='stretch', hide_index=True)
    
    if not components['has_breakdown']:
        st.caption("⚠️ Estimated breakdown — add instrumentation for exact values")


def render_long_prompt_card(item: Dict, index: int):
    """Render a long prompt card."""
    
    call = item['call']
    
    severity = "🔴" if item['prompt_tokens'] > VERY_LONG_PROMPT_THRESHOLD else "🟡"
    
    st.markdown(f"### {severity} #{index} — {format_tokens(item['prompt_tokens'])} tokens — {call.get('operation', 'unknown')}")
    st.caption(f"{call.get('agent_name', 'unknown')} • {format_model_name(call.get('model_name', ''))} • {format_cost(call.get('total_cost', 0))}")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        render_token_breakdown(item['components'], item['prompt_tokens'])
    
    with col2:
        st.markdown("**Optimization Opportunities:**")
        
        if item['opportunities']:
            for opp in item['opportunities']:
                st.write(f"- {opp['description']} (save ~{format_tokens(opp['token_savings'])})")
            
            st.success(f"**Potential:** {format_tokens(item['potential_savings_tokens'])} tokens ({item['reduction_pct']:.0%} reduction)")
            st.write(f"Save ~{format_cost(item['potential_savings_cost'])}/call")
        else:
            st.info("No obvious optimization opportunities detected")
    
    with st.expander("📝 View Prompt Preview"):
        st.markdown("**System Prompt:**")
        st.code(item['components']['system_prompt'], language="text")
        
        if item['components']['chat_history_count'] > 0:
            st.markdown(f"**Chat History:** {item['components']['chat_history_count']} messages")
        
        st.markdown("**User Message:**")
        st.code(item['components']['user_message'], language="text")


def render_low_performer_card(item: Dict, index: int):
    """Render a low performer card."""
    
    call = item['call']
    
    st.markdown(f"### 📉 #{index} — Score: {item['score']:.1f}/10 — {call.get('operation', 'unknown')}")
    st.caption(f"{call.get('agent_name', 'unknown')} • {format_model_name(call.get('model_name', ''))}")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("**Prompt Issues Detected:**")
        
        if item['issues']:
            for issue in item['issues']:
                st.error(f"**{issue['type']}:** {issue['description']}")
                st.caption(f"Fix: {issue['fix']}")
        else:
            st.info("No obvious prompt issues detected — may be model limitation")
    
    with col2:
        if item['judge_feedback']:
            st.markdown("**Judge Feedback:**")
            st.info(item['judge_feedback'][:300])
    
    with st.expander("📝 View Full Prompt"):
        st.code(call.get('prompt', 'N/A')[:1000], language="text")


def render_overview_tab(calls: List[Dict], health: Dict):
    """Render Overview tab."""
    
    st.subheader("📊 Prompt Health Summary")
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Calls", f"{health['total_calls']:,}")
    with col2:
        st.metric("Avg Tokens", format_tokens(int(health['avg_prompt_tokens'])))
    with col3:
        st.metric("Long Prompts", health['long_prompt_count'])
    with col4:
        st.metric("Low Quality", health['low_quality_count'])
    
    st.divider()
    
    # By operation
    st.subheader("🎯 Prompt Stats by Operation")
    
    op_data = []
    for op in health['operations']:
        status_display = {
            'VERY_LONG': '🔴 Very long',
            'LONG': '🟡 Long',
            'LOW_QUALITY': '🟠 Low quality',
            'HEALTHY': '🟢 Healthy',
        }
        
        op_data.append({
            'Operation': op['operation'],
            'Calls': op['call_count'],
            'Avg Tokens': format_tokens(int(op['avg_tokens'])),
            'Avg Score': f"{op['avg_score']:.1f}/10" if op['avg_score'] else "—",
            'Status': status_display.get(op['status'], op['status']),
        })
    
    st.dataframe(pd.DataFrame(op_data), width='stretch', hide_index=True)


def render_long_prompts_tab(long_prompts: List[Dict]):
    """Render Long Prompts tab."""
    
    if not long_prompts:
        st.success(f"✅ No prompts over {format_tokens(LONG_PROMPT_THRESHOLD)} tokens!")
        return
    
    st.subheader(f"📏 {len(long_prompts)} Long Prompts")
    st.caption(f"Prompts over {format_tokens(LONG_PROMPT_THRESHOLD)} tokens")
    
    # Summary
    total_potential = sum(p['potential_savings_tokens'] for p in long_prompts)
    total_cost_savings = sum(p['potential_savings_cost'] for p in long_prompts)
    
    if total_potential > 0:
        st.info(f"💡 **Total Optimization Potential:** {format_tokens(total_potential)} tokens, ~{format_cost(total_cost_savings)}/period")
    
    st.divider()
    
    for i, item in enumerate(long_prompts[:10], 1):
        with st.container():
            render_long_prompt_card(item, i)
            st.divider()
    
    if len(long_prompts) > 10:
        st.caption(f"Showing top 10 of {len(long_prompts)} long prompts")


def render_low_performers_tab(low_performers: List[Dict]):
    """Render Low Performers tab."""
    
    if not low_performers:
        st.success("✅ No low-quality prompts detected!")
        return
    
    st.subheader(f"📉 {len(low_performers)} Low-Performing Prompts")
    st.caption(f"Prompts with quality score < {LOW_QUALITY_THRESHOLD}")
    
    for i, item in enumerate(low_performers[:10], 1):
        with st.container():
            render_low_performer_card(item, i)
            st.divider()


def render_compare_tab(calls: List[Dict]):
    """Render Compare tab for side-by-side comparison."""
    
    st.subheader("🔬 Compare Prompts")
    st.caption("Select two calls to compare their prompts")
    
    # Filter to calls with prompts
    calls_with_prompts = [c for c in calls if c.get('prompt')][:50]
    
    if len(calls_with_prompts) < 2:
        st.info("Need at least 2 calls with prompts to compare")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        idx_a = st.selectbox(
            "Select Call A",
            options=range(len(calls_with_prompts)),
            format_func=lambda i: f"{calls_with_prompts[i].get('operation', 'unknown')} - {format_tokens(calls_with_prompts[i].get('prompt_tokens', 0))}",
            key="compare_a"
        )
    
    with col2:
        idx_b = st.selectbox(
            "Select Call B",
            options=range(len(calls_with_prompts)),
            format_func=lambda i: f"{calls_with_prompts[i].get('operation', 'unknown')} - {format_tokens(calls_with_prompts[i].get('prompt_tokens', 0))}",
            key="compare_b",
            index=min(1, len(calls_with_prompts) - 1)
        )
    
    if idx_a == idx_b:
        st.warning("Select different calls to compare")
        return
    
    call_a = calls_with_prompts[idx_a]
    call_b = calls_with_prompts[idx_b]
    
    st.divider()
    
    # Comparison metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Call A")
        st.write(f"- Operation: {call_a.get('operation', 'unknown')}")
        st.write(f"- Tokens: {format_tokens(call_a.get('prompt_tokens', 0))}")
        st.write(f"- Cost: {format_cost(call_a.get('total_cost', 0))}")
        
        qual_a = call_a.get('quality_evaluation', {})
        if qual_a.get('score'):
            st.write(f"- Score: {qual_a['score']:.1f}/10")
    
    with col2:
        st.markdown("### Call B")
        st.write(f"- Operation: {call_b.get('operation', 'unknown')}")
        st.write(f"- Tokens: {format_tokens(call_b.get('prompt_tokens', 0))}")
        st.write(f"- Cost: {format_cost(call_b.get('total_cost', 0))}")
        
        qual_b = call_b.get('quality_evaluation', {})
        if qual_b.get('score'):
            st.write(f"- Score: {qual_b['score']:.1f}/10")
    
    st.divider()
    
    # Side-by-side prompts
    st.markdown("### Prompts")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Prompt A:**")
        st.code(truncate_text(call_a.get('prompt', ''), 1000), language="text")
    
    with col2:
        st.markdown("**Prompt B:**")
        st.code(truncate_text(call_b.get('prompt', ''), 1000), language="text")
    
    # Diff view
    with st.expander("📋 View Diff"):
        diff = generate_prompt_diff(
            call_a.get('prompt', '')[:2000], 
            call_b.get('prompt', '')[:2000]
        )
        
        for change in diff[:50]:
            if change['type'] == 'add':
                st.markdown(f"<span style='background-color: #90EE90'>+ {change['text']}</span>", unsafe_allow_html=True)
            elif change['type'] == 'remove':
                st.markdown(f"<span style='background-color: #FFB6C1'>- {change['text']}</span>", unsafe_allow_html=True)


# =============================================================================
# MAIN RENDER
# =============================================================================

def render():
    """Main render function for Prompt Optimizer page."""
    
    st.title("📝 Prompt Diagnostics")
    st.caption("Find inefficient prompts and how to improve them")
    
    selected_project = st.session_state.get('selected_project')
    
    col1, col2 = st.columns([3, 1])
    with col1:
        if selected_project:
            st.info(f"Analyzing: **{selected_project}**")
    with col2:
        if st.button("🔄 Refresh", width='stretch'):
            st.cache_data.clear()
            st.rerun()
    
    try:
        calls = get_llm_calls(project_name=selected_project, limit=500)
        
        if not calls:
            render_empty_state(
                message="No LLM calls found",
                icon="📝",
                suggestion="Start making LLM calls with Observatory tracking enabled"
            )
            return
        
        # Analyze
        with st.spinner("Analyzing prompts..."):
            health = analyze_prompt_health(calls)
            long_prompts = find_long_prompts(calls)
            low_performers = find_low_performers(calls)
        
        # Status banner
        render_prompt_health_banner(health)
        
        st.divider()
        
        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Overview",
            f"📏 Long ({len(long_prompts)})",
            f"📉 Low Perf ({len(low_performers)})",
            "🔬 Compare"
        ])
        
        with tab1:
            render_overview_tab(calls, health)
        
        with tab2:
            render_long_prompts_tab(long_prompts)
        
        with tab3:
            render_low_performers_tab(low_performers)
        
        with tab4:
            render_compare_tab(calls)
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        import traceback
        st.code(traceback.format_exc())