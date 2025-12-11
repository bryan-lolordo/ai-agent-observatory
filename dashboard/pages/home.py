"""
Home Page - Executive Dashboard (Redesigned)
Location: dashboard/pages/home.py

Single-scroll executive overview:
1. System Health - Status at a glance with clickable drilldowns
2. Top Actions - Prioritized with direct navigation
3. Week-over-Week - Trend comparison

Design principles:
- No tabs - everything visible in one scroll
- Clickable elements expand or navigate
- Actions paired with their fixes
- KPIs show judgment (good/bad), not just numbers
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional

from dashboard.utils.data_fetcher import (
    get_project_overview,
    get_comparative_metrics,
    get_llm_calls,
)
from dashboard.utils.formatters import (
    format_cost,
    format_latency,
    format_tokens,
    format_percentage,
    format_score,
    format_model_name,
    truncate_text,
)
from dashboard.components.metric_cards import render_empty_state


# =============================================================================
# CONSTANTS
# =============================================================================

# Thresholds for health status
THRESHOLDS = {
    'cost_change_warning': 30,      # % increase
    'cost_change_critical': 50,
    'quality_warning': 7.5,
    'quality_critical': 6.5,
    'hallucination_warning': 0.03,
    'hallucination_critical': 0.05,
    'error_rate_warning': 0.03,
    'error_rate_critical': 0.05,
    'cache_hit_target': 0.30,
    'latency_warning': 3000,        # ms
    'latency_critical': 5000,
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def determine_health_status(
    overview: Dict[str, Any], 
    trends: Dict[str, Any]
) -> Tuple[str, str, List[str]]:
    """
    Determine overall system health.
    
    Returns:
        Tuple of (status, emoji, list of issues)
        status: "healthy", "warning", "critical"
    """
    issues = []
    
    kpis = overview.get('kpis', {})
    quality_metrics = overview.get('quality_metrics', {})
    trend_data = trends.get('trends', {})
    
    # Check hallucinations (highest priority)
    hall_rate = quality_metrics.get('hallucination_rate', 0)
    if hall_rate > THRESHOLDS['hallucination_critical']:
        return ("critical", "🔴", [f"Hallucination rate {format_percentage(hall_rate)} is critical"])
    elif hall_rate > THRESHOLDS['hallucination_warning']:
        issues.append(f"Hallucinations at {format_percentage(hall_rate)}")
    
    # Check error rate
    error_rate = 1 - kpis.get('success_rate', 1.0)
    if error_rate > THRESHOLDS['error_rate_critical']:
        return ("critical", "🔴", [f"Error rate {format_percentage(error_rate)} is critical"])
    elif error_rate > THRESHOLDS['error_rate_warning']:
        issues.append(f"Error rate at {format_percentage(error_rate)}")
    
    # Check cost spike
    cost_change = trend_data.get('total_cost', {}).get('change_pct', 0)
    if cost_change > THRESHOLDS['cost_change_critical']:
        issues.append(f"Cost spiked +{cost_change:.0f}%")
    elif cost_change > THRESHOLDS['cost_change_warning']:
        issues.append(f"Cost up +{cost_change:.0f}%")
    
    # Check quality score
    avg_score = quality_metrics.get('avg_judge_score')
    if avg_score:
        if avg_score < THRESHOLDS['quality_critical']:
            issues.append(f"Quality score {avg_score:.1f} below target")
        elif avg_score < THRESHOLDS['quality_warning']:
            issues.append(f"Quality score {avg_score:.1f} needs attention")
    
    if issues:
        return ("warning", "🟡", issues)
    
    return ("healthy", "🟢", ["All systems operational"])


def get_kpi_status(value: float, metric_type: str, change_pct: Optional[float] = None) -> Tuple[str, str]:
    """
    Get status indicator for a KPI.
    
    Returns:
        Tuple of (status_emoji, status_class)
    """
    if metric_type == 'cost':
        if change_pct and change_pct > THRESHOLDS['cost_change_critical']:
            return ("⚠️", "critical")
        elif change_pct and change_pct > THRESHOLDS['cost_change_warning']:
            return ("⚠️", "warning")
        return ("✓", "healthy")
    
    elif metric_type == 'quality':
        if value < THRESHOLDS['quality_critical']:
            return ("⚠️", "critical")
        elif value < THRESHOLDS['quality_warning']:
            return ("⚠️", "warning")
        return ("✓", "healthy")
    
    elif metric_type == 'hallucination':
        if value > THRESHOLDS['hallucination_critical']:
            return ("⚠️", "critical")
        elif value > THRESHOLDS['hallucination_warning']:
            return ("⚠️", "warning")
        return ("✓", "healthy")
    
    elif metric_type == 'error':
        if value > THRESHOLDS['error_rate_critical']:
            return ("⚠️", "critical")
        elif value > THRESHOLDS['error_rate_warning']:
            return ("⚠️", "warning")
        return ("✓", "healthy")
    
    elif metric_type == 'latency':
        if value > THRESHOLDS['latency_critical']:
            return ("⚠️", "critical")
        elif value > THRESHOLDS['latency_warning']:
            return ("⚠️", "warning")
        return ("✓", "healthy")
    
    return ("", "neutral")


def generate_smart_actions(
    overview: Dict[str, Any], 
    trends: Dict[str, Any],
    calls: List[Dict]
) -> List[Dict[str, Any]]:
    """
    Generate prioritized actions with specific targets and navigation.
    
    Each action includes:
    - priority: high/medium/low
    - title: Short description
    - detail: Specific finding
    - impact: Estimated benefit
    - target_page: Page to navigate to
    - filter_key: Session state key to set
    - filter_value: Value to filter by
    """
    actions = []
    
    kpis = overview.get('kpis', {})
    quality_metrics = overview.get('quality_metrics', {})
    cache_metrics = overview.get('cache_metrics', {})
    by_agent = overview.get('by_agent', {})
    by_model = overview.get('by_model', {})
    
    total_cost = kpis.get('total_cost', 0)
    
    # 1. Hallucination issues → LLM Judge
    hall_rate = quality_metrics.get('hallucination_rate', 0)
    hall_count = quality_metrics.get('hallucination_count', 0)
    if hall_rate > THRESHOLDS['hallucination_warning']:
        # Find which agent has most hallucinations
        worst_agent = None
        if calls:
            agent_halls = {}
            for call in calls:
                qual = call.get('quality_evaluation') or {}
                if qual.get('hallucination_flag'):
                    agent = call.get('agent_name', 'Unknown')
                    agent_halls[agent] = agent_halls.get(agent, 0) + 1
            if agent_halls:
                worst_agent = max(agent_halls, key=agent_halls.get)
        
        actions.append({
            "priority": "high" if hall_rate > THRESHOLDS['hallucination_critical'] else "medium",
            "title": "Fix hallucinations",
            "detail": f"{hall_count} hallucinations detected" + (f" (mostly in {worst_agent})" if worst_agent else ""),
            "impact": f"Reduce {format_percentage(hall_rate)} hallucination rate",
            "target_page": "pages/llm_judge.py",
            "filter_key": "llm_judge_tab",
            "filter_value": "hallucinations",
        })
    
    # 2. Low quality scores → LLM Judge
    avg_score = quality_metrics.get('avg_judge_score')
    if avg_score and avg_score < THRESHOLDS['quality_warning']:
        # Find worst operation
        worst_op = None
        if calls:
            op_scores = {}
            for call in calls:
                qual = call.get('quality_evaluation') or {}
                score = qual.get('judge_score') or qual.get('score')
                if score is not None:
                    op = call.get('operation', 'unknown')
                    if op not in op_scores:
                        op_scores[op] = []
                    op_scores[op].append(score)
            if op_scores:
                op_avgs = {op: sum(s)/len(s) for op, s in op_scores.items()}
                worst_op = min(op_avgs, key=op_avgs.get)
        
        actions.append({
            "priority": "high" if avg_score < THRESHOLDS['quality_critical'] else "medium",
            "title": "Improve low-quality responses",
            "detail": f"Average score {avg_score:.1f}/10" + (f" (worst: {worst_op})" if worst_op else ""),
            "impact": f"Raise quality to 8.0+ target",
            "target_page": "pages/llm_judge.py",
            "filter_key": "llm_judge_tab",
            "filter_value": "failures",
        })
    
    # 3. Cache opportunity → Cache Analyzer
    hit_rate = cache_metrics.get('hit_rate', 0)
    if hit_rate < THRESHOLDS['cache_hit_target']:
        # Count duplicate prompts
        duplicate_count = 0
        if calls:
            prompts = [c.get('prompt', '') for c in calls if c.get('prompt')]
            from collections import Counter
            prompt_counts = Counter(prompts)
            duplicate_count = sum(1 for c in prompt_counts.values() if c > 1)
        
        potential_savings = total_cost * (THRESHOLDS['cache_hit_target'] - hit_rate)
        
        actions.append({
            "priority": "high" if potential_savings > 1.0 else "medium",
            "title": "Enable caching",
            "detail": f"{duplicate_count} duplicate prompts found, only {format_percentage(hit_rate)} hit rate",
            "impact": f"Save ~{format_cost(potential_savings)}/period",
            "target_page": "pages/cache_analyzer.py",
            "filter_key": "cache_tab",
            "filter_value": "repeated",
        })
    
    # 4. Model routing opportunity → Model Router
    if by_model and total_cost > 0:
        # Find expensive model usage for simple tasks
        expensive_models = ['gpt-4', 'gpt-4o', 'gpt-4-turbo', 'claude-3-opus']
        expensive_cost = sum(
            data.get('total_cost', 0) 
            for model, data in by_model.items() 
            if any(em in model.lower() for em in expensive_models)
        )
        
        if expensive_cost / total_cost > 0.5:
            potential_savings = expensive_cost * 0.3
            actions.append({
                "priority": "high" if potential_savings > 2.0 else "medium",
                "title": "Route to cheaper models",
                "detail": f"{format_percentage(expensive_cost/total_cost)} of cost on premium models",
                "impact": f"Save ~{format_cost(potential_savings)}/period",
                "target_page": "pages/model_router.py",
                "filter_key": "router_tab",
                "filter_value": "cost",
            })
    
    # 5. High latency → Model Router
    avg_latency = kpis.get('avg_latency_ms', 0)
    if avg_latency > THRESHOLDS['latency_warning']:
        actions.append({
            "priority": "high" if avg_latency > THRESHOLDS['latency_critical'] else "medium",
            "title": "Reduce latency",
            "detail": f"Average response time {format_latency(avg_latency)}",
            "impact": f"Target < {format_latency(THRESHOLDS['latency_warning'])}",
            "target_page": "pages/model_router.py",
            "filter_key": "router_tab",
            "filter_value": "latency",
        })
    
    # 6. Error patterns → Activity Monitor
    error_rate = 1 - kpis.get('success_rate', 1.0)
    if error_rate > THRESHOLDS['error_rate_warning']:
        error_cost = total_cost * error_rate
        actions.append({
            "priority": "high" if error_rate > THRESHOLDS['error_rate_critical'] else "medium",
            "title": "Fix error patterns",
            "detail": f"{format_percentage(error_rate)} of requests failing",
            "impact": f"Recover ~{format_cost(error_cost)} in failed requests",
            "target_page": "pages/activity_monitor.py",
            "filter_key": "activity_filter",
            "filter_value": "errors",
        })
    
    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    actions.sort(key=lambda x: priority_order.get(x['priority'], 2))
    
    return actions[:3]  # Top 3 only


def calculate_wow_metrics(
    overview: Dict[str, Any], 
    trends: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Calculate week-over-week comparison metrics."""
    
    kpis = overview.get('kpis', {})
    quality_metrics = overview.get('quality_metrics', {})
    cache_metrics = overview.get('cache_metrics', {})
    trend_data = trends.get('trends', {})
    
    metrics = []
    
    # Cost
    cost = kpis.get('total_cost', 0)
    cost_change = trend_data.get('total_cost', {}).get('change_pct', 0)
    cost_prev = cost / (1 + cost_change/100) if cost_change != -100 else 0
    status, _ = get_kpi_status(cost, 'cost', cost_change)
    metrics.append({
        'name': 'Cost',
        'current': format_cost(cost),
        'previous': format_cost(cost_prev),
        'change': f"{cost_change:+.0f}%",
        'status': status,
        'good_direction': 'down',
    })
    
    # Quality
    quality = quality_metrics.get('avg_judge_score')
    if quality:
        quality_change = trend_data.get('avg_quality', {}).get('change_pct', 0)
        quality_prev = quality / (1 + quality_change/100) if quality_change != -100 else 0
        status, _ = get_kpi_status(quality, 'quality')
        metrics.append({
            'name': 'Quality',
            'current': f"{quality:.1f}/10",
            'previous': f"{quality_prev:.1f}/10" if quality_prev else "—",
            'change': f"{quality_change:+.0f}%" if quality_change else "—",
            'status': status,
            'good_direction': 'up',
        })
    
    # Cache Hits
    cache_rate = cache_metrics.get('hit_rate', 0)
    cache_change = trend_data.get('cache_hit_rate', {}).get('change_pct', 0)
    cache_prev = cache_rate / (1 + cache_change/100) if cache_change != -100 else 0
    metrics.append({
        'name': 'Cache Hits',
        'current': format_percentage(cache_rate),
        'previous': format_percentage(cache_prev),
        'change': f"{cache_change:+.0f}%" if cache_change else "—",
        'status': "✓" if cache_rate >= THRESHOLDS['cache_hit_target'] else "⚠️",
        'good_direction': 'up',
    })
    
    # Errors
    error_rate = 1 - kpis.get('success_rate', 1.0)
    error_change = trend_data.get('error_rate', {}).get('change_pct', 0)
    error_prev = error_rate / (1 + error_change/100) if error_change != -100 else 0
    status, _ = get_kpi_status(error_rate, 'error')
    metrics.append({
        'name': 'Errors',
        'current': format_percentage(error_rate),
        'previous': format_percentage(error_prev),
        'change': f"{error_change:+.0f}%" if error_change else "—",
        'status': status,
        'good_direction': 'down',
    })
    
    return metrics


def get_filtered_calls(calls: List[Dict], filter_type: str) -> List[Dict]:
    """Get calls filtered by type for drilldown tables."""
    
    if filter_type == 'hallucinations':
        return [
            c for c in calls 
            if (c.get('quality_evaluation') or {}).get('hallucination_flag')
        ]
    
    elif filter_type == 'low_quality':
        return [
            c for c in calls 
            if (c.get('quality_evaluation') or {}).get('judge_score', 10) < THRESHOLDS['quality_warning']
            or (c.get('quality_evaluation') or {}).get('score', 10) < THRESHOLDS['quality_warning']
        ]
    
    elif filter_type == 'errors':
        return [c for c in calls if not c.get('success', True)]
    
    elif filter_type == 'slow':
        return [c for c in calls if c.get('latency_ms', 0) > THRESHOLDS['latency_warning']]
    
    elif filter_type == 'expensive':
        return sorted(calls, key=lambda c: c.get('total_cost', 0), reverse=True)[:20]
    
    return calls


def render_drilldown_table(calls: List[Dict], filter_type: str):
    """Render a drilldown table for filtered calls."""
    
    if not calls:
        st.info("No matching calls found")
        return
    
    # Build table data based on filter type
    table_data = []
    
    for call in calls[:15]:  # Limit to 15 rows
        row = {
            'Agent': call.get('agent_name', 'Unknown')[:15],
            'Operation': call.get('operation', 'unknown')[:20],
            'Model': format_model_name(call.get('model_name', ''))[:12],
        }
        
        if filter_type == 'hallucinations':
            qual = call.get('quality_evaluation') or {}
            row['Score'] = f"{qual.get('judge_score', qual.get('score', 'N/A'))}"
            row['Details'] = truncate_text(qual.get('hallucination_details', qual.get('reasoning', 'N/A')), 40)
        
        elif filter_type == 'low_quality':
            qual = call.get('quality_evaluation') or {}
            row['Score'] = f"{qual.get('judge_score', qual.get('score', 'N/A'))}/10"
            row['Feedback'] = truncate_text(qual.get('reasoning', qual.get('judge_feedback', 'N/A')), 40)
        
        elif filter_type == 'errors':
            row['Error'] = truncate_text(call.get('error', 'Unknown error'), 50)
            row['Latency'] = format_latency(call.get('latency_ms', 0))
        
        elif filter_type == 'slow':
            row['Latency'] = format_latency(call.get('latency_ms', 0))
            row['Tokens'] = format_tokens(call.get('total_tokens', 0))
            row['Cost'] = format_cost(call.get('total_cost', 0))
        
        elif filter_type == 'expensive':
            row['Cost'] = format_cost(call.get('total_cost', 0))
            row['Tokens'] = format_tokens(call.get('total_tokens', 0))
            row['Latency'] = format_latency(call.get('latency_ms', 0))
        
        table_data.append(row)
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, width='stretch', hide_index=True)
    
    if len(calls) > 15:
        st.caption(f"Showing 15 of {len(calls)} matching calls")


def navigate_to_page(page: str, filter_key: str = None, filter_value: str = None):
    """Set session state and navigate to a page."""
    if filter_key and filter_value:
        st.session_state[filter_key] = filter_value
    st.session_state['_nav_to'] = page
    st.rerun()


# =============================================================================
# MAIN RENDER FUNCTION
# =============================================================================

def render():
    """Render the redesigned Home page."""
    
    # =========================================================================
    # HEADER
    # =========================================================================
    st.title("🏠 Observatory")
    
    selected_project = st.session_state.get('selected_project')
    
    col1, col2 = st.columns([3, 1])
    with col1:
        project_label = selected_project or "All Projects"
        st.caption(f"Monitoring: **{project_label}**")
    with col2:
        if st.button("🔄 Refresh", width='stretch'):
            st.cache_data.clear()
            st.rerun()
    
    st.divider()
    
    # =========================================================================
    # LOAD DATA
    # =========================================================================
    try:
        overview = get_project_overview(selected_project)
        trends = get_comparative_metrics(selected_project, period="7d")
        calls = get_llm_calls(project_name=selected_project, limit=500)
        
        if overview.get('kpis', {}).get('total_calls', 0) == 0:
            render_empty_state(
                message="No data available",
                icon="🏠",
                suggestion="Run AI agents with Observatory tracking enabled to see your dashboard"
            )
            return
            
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    kpis = overview.get('kpis', {})
    quality_metrics = overview.get('quality_metrics', {})
    cache_metrics = overview.get('cache_metrics', {})
    trend_data = trends.get('trends', {})
    
    # =========================================================================
    # SECTION 1: SYSTEM HEALTH
    # =========================================================================
    health_status, health_emoji, health_issues = determine_health_status(overview, trends)
    
    # Health banner
    if health_status == "critical":
        st.error(f"{health_emoji} **CRITICAL** — {health_issues[0]}")
    elif health_status == "warning":
        st.warning(f"{health_emoji} **NEEDS ATTENTION** — {', '.join(health_issues[:2])}")
    else:
        st.success(f"{health_emoji} **HEALTHY** — {health_issues[0]}")
    
    st.markdown("")  # Spacing
    
    # KPI Cards (clickable)
    col1, col2, col3, col4 = st.columns(4)
    
    # Cost KPI
    with col1:
        cost = kpis.get('total_cost', 0)
        cost_change = trend_data.get('total_cost', {}).get('change_pct', 0)
        status, _ = get_kpi_status(cost, 'cost', cost_change)
        
        st.metric(
            label=f"Cost (7d) {status}",
            value=format_cost(cost),
            delta=f"{cost_change:+.0f}%" if cost_change else None,
            delta_color="inverse"
        )
        if st.button("View expensive calls", key="drill_cost", width='stretch'):
            st.session_state['home_drilldown'] = 'expensive'
    
    # Quality KPI
    with col2:
        quality = quality_metrics.get('avg_judge_score')
        if quality:
            status, _ = get_kpi_status(quality, 'quality')
            st.metric(
                label=f"Quality {status}",
                value=f"{quality:.1f}/10",
            )
            if st.button("View low quality", key="drill_quality", width='stretch'):
                st.session_state['home_drilldown'] = 'low_quality'
        else:
            st.metric(label="Quality", value="—")
            st.caption("Enable LLM Judge")
    
    # Hallucinations KPI
    with col3:
        hall_rate = quality_metrics.get('hallucination_rate', 0)
        hall_count = quality_metrics.get('hallucination_count', 0)
        status, _ = get_kpi_status(hall_rate, 'hallucination')
        
        st.metric(
            label=f"Hallucinations {status}",
            value=format_percentage(hall_rate),
            help=f"{hall_count} total"
        )
        if hall_count > 0:
            if st.button("View all", key="drill_hall", width='stretch'):
                st.session_state['home_drilldown'] = 'hallucinations'
    
    # Errors KPI
    with col4:
        error_rate = 1 - kpis.get('success_rate', 1.0)
        error_count = int(kpis.get('total_calls', 0) * error_rate)
        status, _ = get_kpi_status(error_rate, 'error')
        
        st.metric(
            label=f"Errors {status}",
            value=format_percentage(error_rate),
            help=f"{error_count} total"
        )
        if error_count > 0:
            if st.button("View errors", key="drill_errors", width='stretch'):
                st.session_state['home_drilldown'] = 'errors'
    
    # Drilldown table (if a KPI was clicked)
    if st.session_state.get('home_drilldown'):
        drilldown_type = st.session_state['home_drilldown']
        
        st.markdown("")
        
        drilldown_titles = {
            'hallucinations': '🚨 Hallucinations',
            'low_quality': '📉 Low Quality Responses',
            'errors': '❌ Failed Requests',
            'expensive': '💰 Most Expensive Calls',
            'slow': '🐌 Slowest Calls',
        }
        
        with st.expander(f"**{drilldown_titles.get(drilldown_type, 'Details')}**", expanded=True):
            col1, col2 = st.columns([4, 1])
            with col2:
                if st.button("✕ Close", key="close_drilldown"):
                    del st.session_state['home_drilldown']
                    st.rerun()
            
            filtered_calls = get_filtered_calls(calls, drilldown_type)
            render_drilldown_table(filtered_calls, drilldown_type)
            
            # Link to full page
            page_map = {
                'hallucinations': ('⚖️ LLM Judge', 'llm_judge_tab', 'hallucinations'),
                'low_quality': ('⚖️ LLM Judge', 'llm_judge_tab', 'failures'),
                'errors': ('📡 Activity Monitor', 'activity_filter', 'errors'),
                'expensive': ('💰 Cost Estimator', None, None),
                'slow': ('🔀 Model Router', 'router_tab', 'latency'),
            }
            
            if drilldown_type in page_map:
                page, key, value = page_map[drilldown_type]
                if st.button(f"🔍 See full analysis →", key=f"goto_{drilldown_type}"):
                    navigate_to_page(page, key, value)
    
    st.divider()
    
    # =========================================================================
    # SECTION 2: TOP ACTIONS
    # =========================================================================
    st.subheader("🎯 Top Actions")
    
    actions = generate_smart_actions(overview, trends, calls)
    
    if actions:
        for i, action in enumerate(actions, 1):
            priority_emoji = "🔴" if action['priority'] == 'high' else "🟡"
            
            col1, col2, col3 = st.columns([3, 1.5, 1])
            
            with col1:
                st.markdown(f"**{i}. {action['title']}**")
                st.caption(action['detail'])
            
            with col2:
                st.markdown(f"→ {action['impact']}")
            
            with col3:
                if st.button(
                    "Fix →", 
                    key=f"action_{i}",
                    width='stretch',
                    type="primary" if action['priority'] == 'high' else "secondary"
                ):
                    navigate_to_page(
                        action['target_page'],
                        action.get('filter_key'),
                        action.get('filter_value')
                    )
            
            if i < len(actions):
                st.markdown("---")
    else:
        st.success("✅ No critical actions needed. System is performing well!")
    
    st.divider()
    
    # =========================================================================
    # SECTION 3: WEEK OVER WEEK
    # =========================================================================
    st.subheader("📊 This Week vs Last Week")
    
    wow_metrics = calculate_wow_metrics(overview, trends)
    
    # Build comparison table
    table_data = []
    for metric in wow_metrics:
        # Determine if change is good or bad
        change_str = metric['change']
        if change_str != "—":
            change_val = float(change_str.replace('%', '').replace('+', ''))
            if metric['good_direction'] == 'down':
                change_color = "🟢" if change_val < 0 else "🔴" if change_val > 20 else "🟡"
            else:
                change_color = "🟢" if change_val > 0 else "🔴" if change_val < -20 else "🟡"
            change_display = f"{change_color} {change_str}"
        else:
            change_display = "—"
        
        table_data.append({
            'Metric': metric['name'],
            'This Week': f"{metric['status']} {metric['current']}",
            'Last Week': metric['previous'],
            'Change': change_display,
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, width='stretch', hide_index=True)
    
    # Summary insight
    improving = sum(1 for m in wow_metrics if m['change'] != "—" and (
        (m['good_direction'] == 'down' and float(m['change'].replace('%', '').replace('+', '')) < 0) or
        (m['good_direction'] == 'up' and float(m['change'].replace('%', '').replace('+', '')) > 0)
    ))
    
    if improving >= 3:
        st.success(f"📈 **Trending positive** — {improving}/4 metrics improving")
    elif improving >= 2:
        st.info(f"📊 **Mixed results** — {improving}/4 metrics improving")
    else:
        st.warning(f"📉 **Needs attention** — Only {improving}/4 metrics improving")
    
