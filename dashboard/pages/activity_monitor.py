"""
Activity Monitor - Real-Time System Status (Redesigned)
Location: dashboard/pages/activity_monitor.py

Single-scroll real-time monitoring:
1. Health status bar - everything at a glance
2. Issue counts - clickable filters
3. Live feed - always visible, filterable
4. Inline detail expansion - click row to see diagnosis

Design principles:
- Live feed is the hero, not hidden
- Click row to expand details inline
- Smart diagnosis based on call data
- Navigation to other pages for deeper analysis
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict

from dashboard.utils.data_fetcher import (
    get_llm_calls,
    get_time_series_data,
    get_available_agents,
    get_available_operations,
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

THRESHOLDS = {
    'slow_latency_ms': 3000,
    'very_slow_latency_ms': 10000,
    'expensive_cost': 0.10,
    'large_prompt_tokens': 4000,
    'large_history_tokens': 2000,
    'error_rate_warning': 0.05,
}


# =============================================================================
# DIAGNOSIS ENGINE
# =============================================================================

def diagnose_call(call: Dict) -> Optional[Dict[str, Any]]:
    """
    Analyze a call and return diagnosis if there's an issue.
    
    Returns:
        Dict with icon, title, reason, target_page, action_label
        Or None if no issues
    """
    latency = call.get('latency_ms', 0)
    prompt_tokens = call.get('prompt_tokens', 0)
    completion_tokens = call.get('completion_tokens', 0)
    total_tokens = call.get('total_tokens', 0)
    cost = call.get('total_cost', 0)
    success = call.get('success', True)
    error = call.get('error', '')
    
    # Get prompt breakdown if available
    breakdown = call.get('prompt_breakdown') or {}
    history_tokens = breakdown.get('chat_history_tokens', 0)
    history_count = breakdown.get('chat_history_count', 0)
    system_tokens = breakdown.get('system_prompt_tokens', 0)
    
    # Get quality info if available
    quality = call.get('quality_evaluation') or {}
    hallucination = quality.get('hallucination_flag') or quality.get('hallucination', False)
    
    # Priority 1: Hallucination
    if hallucination:
        return {
            'icon': '🚨',
            'badge': 'HALLUCINATION',
            'title': 'HALLUCINATION DETECTED',
            'reason': quality.get('hallucination_details', 'Response contains fabricated information'),
            'target_page': '⚖️ LLM Judge',
            'target_filter': ('llm_judge_tab', 'hallucinations'),
            'action_label': 'Review in LLM Judge',
        }
    
    # Priority 2: Error
    if not success:
        if 'timeout' in error.lower():
            return {
                'icon': '❌',
                'badge': 'ERROR',
                'title': 'TIMEOUT ERROR',
                'reason': f"Request timed out after {format_latency(latency)} — reduce prompt size or increase timeout",
                'target_page': '✨ Prompt Optimizer',
                'target_filter': ('prompt_tab', 'long'),
                'action_label': 'Optimize prompt',
            }
        elif 'rate' in error.lower() or 'limit' in error.lower():
            return {
                'icon': '❌',
                'badge': 'ERROR',
                'title': 'RATE LIMIT',
                'reason': 'Hit API rate limit — implement exponential backoff or request limit increase',
                'target_page': None,
                'target_filter': None,
                'action_label': None,
            }
        elif 'context' in error.lower() or 'token' in error.lower():
            return {
                'icon': '❌',
                'badge': 'ERROR',
                'title': 'CONTEXT LENGTH EXCEEDED',
                'reason': f"Prompt too long ({format_tokens(prompt_tokens)}) — implement chunking or summarization",
                'target_page': '✨ Prompt Optimizer',
                'target_filter': ('prompt_tab', 'long'),
                'action_label': 'Optimize prompt',
            }
        else:
            return {
                'icon': '❌',
                'badge': 'ERROR',
                'title': 'ERROR',
                'reason': error[:150] if error else 'Unknown error',
                'target_page': None,
                'target_filter': None,
                'action_label': None,
            }
    
    # Priority 3: Slow call
    if latency > THRESHOLDS['slow_latency_ms']:
        # Try to identify why it's slow
        if history_tokens > THRESHOLDS['large_history_tokens']:
            return {
                'icon': '🐌',
                'badge': 'SLOW',
                'title': 'SLOW — Large Chat History',
                'reason': f"Chat history is {format_tokens(history_tokens)} ({history_count} messages) — consider sliding window to keep last 6",
                'target_page': '✨ Prompt Optimizer',
                'target_filter': ('prompt_tab', 'long'),
                'action_label': 'Optimize in Prompt Optimizer',
            }
        elif system_tokens > THRESHOLDS['large_history_tokens']:
            return {
                'icon': '🐌',
                'badge': 'SLOW',
                'title': 'SLOW — Large System Prompt',
                'reason': f"System prompt is {format_tokens(system_tokens)} — compress or use prompt caching",
                'target_page': '✨ Prompt Optimizer',
                'target_filter': ('prompt_tab', 'long'),
                'action_label': 'Optimize in Prompt Optimizer',
            }
        elif prompt_tokens > THRESHOLDS['large_prompt_tokens']:
            return {
                'icon': '🐌',
                'badge': 'SLOW',
                'title': 'SLOW — Large Prompt',
                'reason': f"Prompt is {format_tokens(prompt_tokens)} — likely includes large context or history",
                'target_page': '✨ Prompt Optimizer',
                'target_filter': ('prompt_tab', 'long'),
                'action_label': 'Optimize in Prompt Optimizer',
            }
        elif total_tokens < 1000:
            return {
                'icon': '🐌',
                'badge': 'SLOW',
                'title': 'SLOW — Small Request',
                'reason': f"Only {format_tokens(total_tokens)} but took {format_latency(latency)} — may be API/network issue or model overloaded",
                'target_page': '🔀 Model Router',
                'target_filter': ('router_tab', 'latency'),
                'action_label': 'Check in Model Router',
            }
        else:
            return {
                'icon': '🐌',
                'badge': 'SLOW',
                'title': 'SLOW',
                'reason': f"{format_latency(latency)} for {format_tokens(total_tokens)} — consider faster model for this operation",
                'target_page': '🔀 Model Router',
                'target_filter': ('router_tab', 'latency'),
                'action_label': 'Analyze in Model Router',
            }
    
    # Priority 4: Expensive call
    if cost > THRESHOLDS['expensive_cost']:
        if prompt_tokens > THRESHOLDS['large_prompt_tokens'] * 2:
            return {
                'icon': '💰',
                'badge': 'EXPENSIVE',
                'title': 'EXPENSIVE — Large Prompt',
                'reason': f"Prompt is {format_tokens(prompt_tokens)} at {format_cost(cost)} — compress or implement caching",
                'target_page': '💾 Cache Analyzer',
                'target_filter': ('cache_tab', 'high_value'),
                'action_label': 'Check caching opportunity',
            }
        elif completion_tokens > prompt_tokens:
            return {
                'icon': '💰',
                'badge': 'EXPENSIVE',
                'title': 'EXPENSIVE — Long Response',
                'reason': f"Response is {format_tokens(completion_tokens)} at {format_cost(cost)} — consider max_tokens limit",
                'target_page': '🔀 Model Router',
                'target_filter': ('router_tab', 'cost'),
                'action_label': 'Review in Model Router',
            }
        else:
            return {
                'icon': '💰',
                'badge': 'EXPENSIVE',
                'title': 'EXPENSIVE',
                'reason': f"{format_cost(cost)} — consider routing to cheaper model for this operation",
                'target_page': '🔀 Model Router',
                'target_filter': ('router_tab', 'cost'),
                'action_label': 'Check routing options',
            }
    
    return None


def get_call_badge(call: Dict) -> Tuple[str, str]:
    """
    Get the status badge for a call.
    
    Returns:
        Tuple of (emoji, css_class)
    """
    diagnosis = diagnose_call(call)
    
    if diagnosis:
        badge_map = {
            'HALLUCINATION': ('🚨', 'hallucination'),
            'ERROR': ('❌', 'error'),
            'SLOW': ('🐌', 'slow'),
            'EXPENSIVE': ('💰', 'expensive'),
        }
        return badge_map.get(diagnosis['badge'], ('⚠️', 'warning'))
    
    return ('✅', 'success')


# =============================================================================
# METRICS CALCULATION
# =============================================================================

def calculate_live_metrics(calls: List[Dict], window_minutes: int = 5) -> Dict[str, Any]:
    """Calculate real-time metrics from recent calls."""
    if not calls:
        return {
            'requests_per_min': 0,
            'cost_per_hour': 0,
            'avg_latency_ms': 0,
            'error_rate': 0,
            'total_requests': 0,
        }
    
    # Filter to time window
    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
    recent = [c for c in calls if c.get('timestamp') and c['timestamp'] >= cutoff]
    
    if not recent:
        recent = calls[:50]  # Fallback to most recent
    
    total = len(recent)
    total_cost = sum(c.get('total_cost', 0) for c in recent)
    total_latency = sum(c.get('latency_ms', 0) for c in recent)
    errors = sum(1 for c in recent if not c.get('success', True))
    
    time_span_min = max(window_minutes, 1)
    
    return {
        'requests_per_min': total / time_span_min,
        'cost_per_hour': (total_cost / time_span_min) * 60,
        'avg_latency_ms': total_latency / max(total, 1),
        'error_rate': errors / max(total, 1),
        'total_requests': total,
    }


def count_issues(calls: List[Dict], window_minutes: int = 5) -> Dict[str, List[Dict]]:
    """Count and categorize issues in recent calls."""
    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
    recent = [c for c in calls if c.get('timestamp') and c['timestamp'] >= cutoff]
    
    if not recent:
        recent = calls[:50]
    
    issues = {
        'slow': [],
        'expensive': [],
        'errors': [],
        'hallucinations': [],
    }
    
    for call in recent:
        if not call.get('success', True):
            issues['errors'].append(call)
        elif (call.get('quality_evaluation') or {}).get('hallucination_flag'):
            issues['hallucinations'].append(call)
        elif call.get('latency_ms', 0) > THRESHOLDS['slow_latency_ms']:
            issues['slow'].append(call)
        elif call.get('total_cost', 0) > THRESHOLDS['expensive_cost']:
            issues['expensive'].append(call)
    
    return issues


def determine_health_status(metrics: Dict[str, Any], issues: Dict[str, List]) -> Tuple[str, str]:
    """
    Determine overall system health.
    
    Returns:
        Tuple of (status_emoji, status_text)
    """
    error_rate = metrics.get('error_rate', 0)
    
    if error_rate > 0.10:
        return ('🔴', 'CRITICAL')
    elif issues['hallucinations']:
        return ('🔴', 'CRITICAL')
    elif error_rate > 0.05 or len(issues['errors']) >= 3:
        return ('🟡', 'DEGRADED')
    elif len(issues['slow']) >= 3:
        return ('🟡', 'DEGRADED')
    elif metrics.get('total_requests', 0) == 0:
        return ('⚪', 'NO ACTIVITY')
    else:
        return ('🟢', 'HEALTHY')


# =============================================================================
# RENDER COMPONENTS
# =============================================================================

def render_health_bar(metrics: Dict[str, Any], issues: Dict[str, List]):
    """Render the compact health status bar."""
    status_emoji, status_text = determine_health_status(metrics, issues)
    
    # Build metrics string
    metrics_parts = [
        f"{metrics['requests_per_min']:.1f} req/min",
        f"{format_cost(metrics['cost_per_hour'])}/hr",
        f"{format_latency(metrics['avg_latency_ms'])} avg",
        f"{format_percentage(metrics['error_rate'])} errors",
    ]
    metrics_str = " • ".join(metrics_parts)
    
    if status_text == 'CRITICAL':
        st.error(f"{status_emoji} **{status_text}** — {metrics_str}")
    elif status_text == 'DEGRADED':
        st.warning(f"{status_emoji} **{status_text}** — {metrics_str}")
    elif status_text == 'NO ACTIVITY':
        st.info(f"{status_emoji} **{status_text}** — No recent requests detected")
    else:
        st.success(f"{status_emoji} **{status_text}** — {metrics_str}")


def render_issue_counts(issues: Dict[str, List]):
    """Render clickable issue count buttons."""
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        count = len(issues['slow'])
        if count > 0:
            if st.button(f"🐌 {count} Slow (>3s)", key="filter_slow", width='stretch'):
                st.session_state['activity_filter'] = 'slow'
        else:
            st.button("🐌 0 Slow", key="filter_slow_disabled", disabled=True, width='stretch')
    
    with col2:
        count = len(issues['expensive'])
        if count > 0:
            if st.button(f"💰 {count} Expensive (>$0.10)", key="filter_expensive", width='stretch'):
                st.session_state['activity_filter'] = 'expensive'
        else:
            st.button("💰 0 Expensive", key="filter_expensive_disabled", disabled=True, width='stretch')
    
    with col3:
        count = len(issues['errors'])
        if count > 0:
            if st.button(f"❌ {count} Errors", key="filter_errors", width='stretch', type="primary"):
                st.session_state['activity_filter'] = 'errors'
        else:
            st.button("❌ 0 Errors", key="filter_errors_disabled", disabled=True, width='stretch')
    
    with col4:
        count = len(issues['hallucinations'])
        if count > 0:
            if st.button(f"🚨 {count} Hallucinations", key="filter_hall", width='stretch', type="primary"):
                st.session_state['activity_filter'] = 'hallucinations'
        else:
            st.button("🚨 0 Hallucinations", key="filter_hall_disabled", disabled=True, width='stretch')


def render_live_feed(calls: List[Dict], issues: Dict[str, List]):
    """Render the live feed table with filters."""
    
    # Get unique agents and operations for filters
    agents = sorted(set(c.get('agent_name', 'Unknown') for c in calls))
    operations = sorted(set(c.get('operation', 'unknown') for c in calls))
    
    # Filter controls
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        agent_filter = st.selectbox(
            "Agent",
            options=['All Agents'] + agents,
            key="feed_agent_filter",
            label_visibility="collapsed"
        )
    
    with col2:
        operation_filter = st.selectbox(
            "Operation", 
            options=['All Operations'] + operations,
            key="feed_operation_filter",
            label_visibility="collapsed"
        )
    
    with col3:
        status_filter = st.selectbox(
            "Status",
            options=['All Status', 'Success Only', 'Issues Only', 'Errors Only'],
            key="feed_status_filter",
            label_visibility="collapsed"
        )
    
    with col4:
        if st.button("Clear", key="clear_filters", width='stretch'):
            st.session_state['activity_filter'] = None
            st.session_state['feed_agent_filter'] = 'All Agents'
            st.session_state['feed_operation_filter'] = 'All Operations'
            st.session_state['feed_status_filter'] = 'All Status'
            st.rerun()
    
    # Apply quick filter from issue counts
    quick_filter = st.session_state.get('activity_filter')
    
    # Filter calls
    filtered_calls = calls
    
    # Quick filter takes precedence
    if quick_filter == 'slow':
        filtered_calls = issues['slow']
    elif quick_filter == 'expensive':
        filtered_calls = issues['expensive']
    elif quick_filter == 'errors':
        filtered_calls = issues['errors']
    elif quick_filter == 'hallucinations':
        filtered_calls = issues['hallucinations']
    else:
        # Apply dropdown filters
        if agent_filter != 'All Agents':
            filtered_calls = [c for c in filtered_calls if c.get('agent_name') == agent_filter]
        
        if operation_filter != 'All Operations':
            filtered_calls = [c for c in filtered_calls if c.get('operation') == operation_filter]
        
        if status_filter == 'Success Only':
            filtered_calls = [c for c in filtered_calls if c.get('success', True) and not diagnose_call(c)]
        elif status_filter == 'Issues Only':
            filtered_calls = [c for c in filtered_calls if diagnose_call(c)]
        elif status_filter == 'Errors Only':
            filtered_calls = [c for c in filtered_calls if not c.get('success', True)]
    
    # Show active quick filter
    if quick_filter:
        filter_labels = {
            'slow': '🐌 Slow calls',
            'expensive': '💰 Expensive calls',
            'errors': '❌ Errors',
            'hallucinations': '🚨 Hallucinations',
        }
        st.info(f"Filtered to: **{filter_labels.get(quick_filter, quick_filter)}** — Click Clear to show all")
    
    if not filtered_calls:
        st.info("No calls match the current filters")
        return
    
    # Build table
    table_data = []
    for call in filtered_calls[:20]:  # Limit display
        badge, _ = get_call_badge(call)
        
        timestamp = call.get('timestamp')
        time_str = timestamp.strftime("%H:%M:%S") if timestamp else "—"
        
        table_data.append({
            '': badge,
            'Time': time_str,
            'Agent': call.get('agent_name', 'Unknown')[:15],
            'Operation': call.get('operation', 'unknown')[:18],
            'Latency': format_latency(call.get('latency_ms', 0)),
            'Cost': format_cost(call.get('total_cost', 0)),
        })
    
    # Display as dataframe
    df = pd.DataFrame(table_data)
    
    # Use st.dataframe with selection
    selection = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="feed_table"
    )
    
    st.caption(f"Showing {len(table_data)} of {len(filtered_calls)} calls")
    
    # Handle row selection
    selected_rows = selection.selection.rows if selection.selection else []
    
    if selected_rows:
        selected_idx = selected_rows[0]
        if selected_idx < len(filtered_calls):
            render_call_detail(filtered_calls[selected_idx])


def render_call_detail(call: Dict):
    """Render expanded detail panel for a selected call."""
    
    st.markdown("---")
    
    diagnosis = diagnose_call(call)
    
    # Header with diagnosis
    agent = call.get('agent_name', 'Unknown')
    operation = call.get('operation', 'unknown')
    timestamp = call.get('timestamp')
    time_str = timestamp.strftime("%H:%M:%S") if timestamp else "—"
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"### {agent} • {operation} • {time_str}")
    with col2:
        if st.button("✕ Close", key="close_detail"):
            st.rerun()
    
    # Diagnosis banner
    if diagnosis:
        if diagnosis['badge'] in ['ERROR', 'HALLUCINATION']:
            st.error(f"**{diagnosis['icon']} {diagnosis['title']}** — {diagnosis['reason']}")
        else:
            st.warning(f"**{diagnosis['icon']} {diagnosis['title']}** — {diagnosis['reason']}")
    else:
        st.success("✅ **NORMAL** — No issues detected")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Latency", format_latency(call.get('latency_ms', 0)))
    with col2:
        st.metric("Cost", format_cost(call.get('total_cost', 0)))
    with col3:
        st.metric("Prompt Tokens", format_tokens(call.get('prompt_tokens', 0)))
    with col4:
        st.metric("Completion Tokens", format_tokens(call.get('completion_tokens', 0)))
    
    # Prompt breakdown if available
    breakdown = call.get('prompt_breakdown') or {}
    if breakdown:
        st.markdown("**Token Breakdown:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"System: {format_tokens(breakdown.get('system_prompt_tokens', 0))}")
        with col2:
            st.write(f"History: {format_tokens(breakdown.get('chat_history_tokens', 0))} ({breakdown.get('chat_history_count', 0)} msgs)")
        with col3:
            st.write(f"User: {format_tokens(breakdown.get('user_message_tokens', 0))}")
    
    # Prompt and Response
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Prompt:**")
        prompt = call.get('prompt') or 'N/A'
        st.code(truncate_text(str(prompt), 500), language="text")
        if len(str(prompt)) > 500:
            with st.expander("Show full prompt"):
                st.code(prompt, language="text")
    
    with col2:
        st.markdown("**Response:**")
        response = call.get('response_text') or call.get('response') or 'N/A'
        st.code(truncate_text(str(response), 500), language="text")
        if len(str(response)) > 500:
            with st.expander("Show full response"):
                st.code(response, language="text")
    
    # Error details if failed
    if not call.get('success', True):
        st.markdown("**Error:**")
        st.error(call.get('error', 'Unknown error'))
    
    # Quality evaluation if available
    quality = call.get('quality_evaluation') or {}
    if quality:
        st.markdown("**Quality Evaluation:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            score = quality.get('judge_score') or quality.get('score')
            st.write(f"Score: {score}/10" if score else "Score: N/A")
        with col2:
            st.write(f"Hallucination: {'Yes 🚨' if quality.get('hallucination_flag') else 'No'}")
        with col3:
            st.write(f"Factual Error: {'Yes' if quality.get('factual_error') else 'No'}")
        
        if quality.get('reasoning'):
            st.caption(f"Feedback: {quality['reasoning'][:200]}")
    
    # Navigation buttons
    if diagnosis and diagnosis.get('target_page'):
        st.markdown("---")
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            if st.button(f"→ {diagnosis['action_label']}", key="nav_primary", type="primary"):
                if diagnosis['target_filter']:
                    key, value = diagnosis['target_filter']
                    st.session_state[key] = value
                st.session_state['_nav_to'] = diagnosis['target_page']
                st.rerun()
        
        with col2:
            if st.button("→ View in Model Router", key="nav_router"):
                st.session_state['router_call_id'] = call.get('id')
                st.session_state['_nav_to'] = '🔀 Model Router'
                st.rerun()
        
        with col3:
            if st.button("→ View in Prompt Optimizer", key="nav_prompt"):
                st.session_state['prompt_call_id'] = call.get('id')
                st.session_state['_nav_to'] = '✨ Prompt Optimizer'
                st.rerun()


# =============================================================================
# MAIN RENDER
# =============================================================================

def render():
    """Main render function for Activity Monitor page."""
    
    # Header
    st.title("📡 Activity Monitor")
    
    selected_project = st.session_state.get('selected_project')
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        project_label = selected_project or "All Projects"
        st.caption(f"Monitoring: **{project_label}**")
    
    with col2:
        auto_refresh = st.checkbox("Auto-refresh", value=False, key="auto_refresh")
    
    with col3:
        if st.button("🔄 Refresh", width='stretch'):
            st.cache_data.clear()
            st.rerun()
    
    # Check for incoming filters from other pages
    incoming_agent = st.session_state.get('activity_filter_agent')
    incoming_operation = st.session_state.get('activity_filter_operation')
    incoming_source = st.session_state.get('activity_filter_source')
    
    if incoming_agent or incoming_operation:
        filter_parts = []
        if incoming_agent:
            filter_parts.append(incoming_agent)
        if incoming_operation:
            filter_parts.append(incoming_operation)
        filter_label = " → ".join(filter_parts)
        
        col1, col2 = st.columns([4, 1])
        with col1:
            st.info(f"📍 Filtered: **{filter_label}**")
        with col2:
            if st.button("Clear Filter", width='stretch'):
                if 'activity_filter_agent' in st.session_state:
                    del st.session_state['activity_filter_agent']
                if 'activity_filter_operation' in st.session_state:
                    del st.session_state['activity_filter_operation']
                if 'activity_filter_source' in st.session_state:
                    del st.session_state['activity_filter_source']
                st.rerun()
    
    st.divider()
    
    # Load data
    try:
        calls = get_llm_calls(project_name=selected_project, limit=100)
        
        if not calls:
            render_empty_state(
                message="No activity detected",
                icon="📡",
                suggestion="Run AI agents with Observatory enabled to see real-time monitoring"
            )
            return
        
        # Apply incoming filters to data
        if incoming_agent:
            calls = [c for c in calls if c.get('agent_name') == incoming_agent]
        if incoming_operation:
            calls = [c for c in calls if c.get('operation') == incoming_operation]
        
        if not calls and (incoming_agent or incoming_operation):
            st.warning("No calls match the current filter")
            return
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    # Calculate metrics
    metrics = calculate_live_metrics(calls, window_minutes=5)
    issues = count_issues(calls, window_minutes=5)
    
    # Section 1: Health Status Bar
    render_health_bar(metrics, issues)
    
    st.divider()
    
    # Section 2: Issue Counts
    st.markdown("**⚡ Issues in Last 5 Min**")
    render_issue_counts(issues)
    
    st.divider()
    
    # Section 3: Live Feed
    st.markdown("**📋 Live Feed**")
    render_live_feed(calls, issues)
    
    # Auto-refresh
    if auto_refresh:
        import time
        st.caption("Auto-refreshing every 5s...")
        time.sleep(5)
        st.rerun()