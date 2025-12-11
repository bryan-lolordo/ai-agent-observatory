"""
Cost Estimator - Spend Analysis & Optimization (Redesigned)
Location: dashboard/pages/cost_estimator.py

Single-scroll cost analysis:
1. Spend Summary - KPIs with trends
2. Where Money Goes - Expandable agent breakdown with operations
3. Top Savings Opportunities - Actionable with [Fix →] routing
4. Scale Projection - Current vs optimized at scale

Design principles:
- Show the data, not just stats
- Every insight has an action
- [Fix →] routes to filtered destination page
- Expandable rows for drill-down without leaving page
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict
import hashlib

from dashboard.utils.data_fetcher import (
    get_project_overview,
    get_comparative_metrics,
    get_llm_calls,
    get_time_series_data,
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
from dashboard.components.charts import create_time_series_chart


# =============================================================================
# CONSTANTS
# =============================================================================

THRESHOLDS = {
    'cost_change_warning': 30,       # % increase triggers warning
    'cost_change_critical': 50,
    'duplicate_threshold': 0.20,     # 20% duplicates = caching opportunity
    'expensive_model_share': 0.50,   # 50% on expensive models = routing opportunity
    'large_prompt_tokens': 3000,     # Prompt optimization opportunity
}

EXPENSIVE_MODELS = ['gpt-4', 'gpt-4o', 'gpt-4-turbo', 'claude-3-opus', 'claude-3-5-sonnet']
CHEAP_MODELS = ['gpt-4o-mini', 'gpt-3.5-turbo', 'claude-3-haiku', 'claude-3-5-haiku']


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def analyze_agent_costs(calls: List[Dict], period_days: float) -> List[Dict[str, Any]]:
    """
    Analyze costs by agent with operation breakdown.
    
    Returns list of agent summaries with nested operations.
    """
    # Group by agent
    by_agent = defaultdict(lambda: {
        'calls': [],
        'total_cost': 0,
        'operations': defaultdict(lambda: {'calls': [], 'total_cost': 0})
    })
    
    for call in calls:
        agent = call.get('agent_name', 'Unknown')
        operation = call.get('operation', 'unknown')
        cost = call.get('total_cost', 0)
        
        by_agent[agent]['calls'].append(call)
        by_agent[agent]['total_cost'] += cost
        by_agent[agent]['operations'][operation]['calls'].append(call)
        by_agent[agent]['operations'][operation]['total_cost'] += cost
    
    # Calculate total for percentages
    total_cost = sum(a['total_cost'] for a in by_agent.values())
    
    # Build result with trends and top operation
    result = []
    for agent, data in by_agent.items():
        # Find top operation by cost
        top_op = None
        top_op_pct = 0
        if data['operations']:
            top_op_name = max(data['operations'], key=lambda o: data['operations'][o]['total_cost'])
            top_op_cost = data['operations'][top_op_name]['total_cost']
            top_op_pct = (top_op_cost / data['total_cost'] * 100) if data['total_cost'] > 0 else 0
            top_op = f"{top_op_name} ({top_op_pct:.0f}%)"
        
        # Calculate trend (compare first half to second half of period)
        calls_sorted = sorted(data['calls'], key=lambda c: c.get('timestamp') or datetime.min)
        mid = len(calls_sorted) // 2
        if mid > 0:
            first_half_cost = sum(c.get('total_cost', 0) for c in calls_sorted[:mid])
            second_half_cost = sum(c.get('total_cost', 0) for c in calls_sorted[mid:])
            if first_half_cost > 0:
                trend_pct = ((second_half_cost - first_half_cost) / first_half_cost) * 100
            else:
                trend_pct = 0
        else:
            trend_pct = 0
        
        # Build operations list
        operations = []
        for op_name, op_data in data['operations'].items():
            op_calls = op_data['calls']
            avg_cost = op_data['total_cost'] / len(op_calls) if op_calls else 0
            
            # Calculate operation trend
            op_sorted = sorted(op_calls, key=lambda c: c.get('timestamp') or datetime.min)
            op_mid = len(op_sorted) // 2
            if op_mid > 0:
                op_first = sum(c.get('total_cost', 0) for c in op_sorted[:op_mid])
                op_second = sum(c.get('total_cost', 0) for c in op_sorted[op_mid:])
                op_trend = ((op_second - op_first) / op_first * 100) if op_first > 0 else 0
            else:
                op_trend = 0
            
            operations.append({
                'name': op_name,
                'calls': len(op_calls),
                'avg_cost': avg_cost,
                'total_cost': op_data['total_cost'],
                'trend_pct': op_trend,
                'call_data': op_calls,
            })
        
        operations.sort(key=lambda x: -x['total_cost'])
        
        result.append({
            'agent': agent,
            'total_cost': data['total_cost'],
            'share_pct': (data['total_cost'] / total_cost * 100) if total_cost > 0 else 0,
            'trend_pct': trend_pct,
            'top_operation': top_op,
            'call_count': len(data['calls']),
            'operations': operations,
            'calls': data['calls'],
        })
    
    result.sort(key=lambda x: -x['total_cost'])
    return result


def find_duplicates_for_operation(calls: List[Dict]) -> Dict[str, Any]:
    """
    Find duplicate prompts within an operation's calls.
    
    Returns duplicate analysis with groups.
    """
    if not calls:
        return {'duplicate_count': 0, 'duplicate_pct': 0, 'groups': [], 'wasted_cost': 0}
    
    # Normalize and group prompts
    prompt_groups = defaultdict(list)
    
    for call in calls:
        prompt = call.get('prompt', '')
        if not prompt:
            continue
        
        # Simple normalization - could be more sophisticated
        normalized = ' '.join(prompt.lower().split())
        prompt_hash = hashlib.md5(normalized.encode()).hexdigest()[:16]
        prompt_groups[prompt_hash].append(call)
    
    # Find groups with duplicates (2+ calls)
    duplicate_groups = []
    total_duplicates = 0
    wasted_cost = 0
    
    for prompt_hash, group_calls in prompt_groups.items():
        if len(group_calls) >= 2:
            total_duplicates += len(group_calls)
            # First call is "necessary", rest are "wasted"
            group_cost = sum(c.get('total_cost', 0) for c in group_calls)
            avg_cost = group_cost / len(group_calls)
            wasted = (len(group_calls) - 1) * avg_cost
            wasted_cost += wasted
            
            # Get timestamps
            timestamps = [c.get('timestamp') for c in group_calls if c.get('timestamp')]
            timestamps.sort()
            
            duplicate_groups.append({
                'count': len(group_calls),
                'wasted_cost': wasted,
                'prompt_preview': group_calls[0].get('prompt', '')[:200],
                'timestamps': timestamps,
                'calls': group_calls,
            })
    
    duplicate_groups.sort(key=lambda x: -x['wasted_cost'])
    
    total_with_prompts = sum(1 for c in calls if c.get('prompt'))
    
    return {
        'duplicate_count': total_duplicates,
        'duplicate_pct': total_duplicates / total_with_prompts if total_with_prompts > 0 else 0,
        'groups': duplicate_groups[:5],  # Top 5 groups
        'wasted_cost': wasted_cost,
        'total_calls': len(calls),
    }


def analyze_model_usage(calls: List[Dict]) -> Dict[str, Any]:
    """
    Analyze model usage to find routing opportunities.
    """
    if not calls:
        return {'expensive_pct': 0, 'routing_opportunity': False, 'details': {}}
    
    expensive_calls = []
    cheap_calls = []
    other_calls = []
    
    for call in calls:
        model = call.get('model_name', '').lower()
        if any(em in model for em in ['gpt-4', 'opus', 'sonnet']):
            expensive_calls.append(call)
        elif any(cm in model for cm in ['mini', 'haiku', '3.5']):
            cheap_calls.append(call)
        else:
            other_calls.append(call)
    
    total = len(calls)
    expensive_pct = len(expensive_calls) / total if total > 0 else 0
    
    # Analyze if expensive calls could be routed cheaper
    simple_expensive = []
    for call in expensive_calls:
        tokens = call.get('total_tokens', 0)
        completion = call.get('completion_tokens', 0)
        # Heuristic: short output likely means simple task
        if tokens < 2000 and completion < 500:
            simple_expensive.append(call)
    
    potential_savings = 0
    if simple_expensive:
        # Estimate savings: expensive costs ~10x more than cheap
        current_cost = sum(c.get('total_cost', 0) for c in simple_expensive)
        potential_savings = current_cost * 0.7  # Could save ~70% by routing to cheap model
    
    return {
        'expensive_pct': expensive_pct,
        'expensive_count': len(expensive_calls),
        'simple_expensive_count': len(simple_expensive),
        'routing_opportunity': len(simple_expensive) > 3,
        'potential_savings': potential_savings,
        'sample_calls': simple_expensive[:3],
    }


def analyze_prompt_sizes(calls: List[Dict]) -> Dict[str, Any]:
    """
    Analyze prompt sizes to find compression opportunities.
    """
    if not calls:
        return {'large_prompt_count': 0, 'avg_tokens': 0, 'opportunity': False}
    
    prompt_tokens = [c.get('prompt_tokens', 0) for c in calls]
    avg_tokens = sum(prompt_tokens) / len(prompt_tokens) if prompt_tokens else 0
    
    large_prompts = [c for c in calls if c.get('prompt_tokens', 0) > THRESHOLDS['large_prompt_tokens']]
    
    # Estimate savings from reducing prompt size
    potential_savings = 0
    if large_prompts:
        large_cost = sum(c.get('total_cost', 0) for c in large_prompts)
        # Assume we could reduce prompts by 40%
        potential_savings = large_cost * 0.4
    
    return {
        'large_prompt_count': len(large_prompts),
        'large_prompt_pct': len(large_prompts) / len(calls) if calls else 0,
        'avg_tokens': avg_tokens,
        'opportunity': len(large_prompts) > 5,
        'potential_savings': potential_savings,
        'sample_calls': large_prompts[:3],
    }


def generate_savings_opportunities(
    agent_data: List[Dict], 
    calls: List[Dict],
    period_days: float
) -> List[Dict[str, Any]]:
    """
    Generate top savings opportunities across all agents/operations.
    """
    opportunities = []
    
    for agent in agent_data:
        for op in agent['operations']:
            op_calls = op['call_data']
            
            # Check for caching opportunity
            duplicates = find_duplicates_for_operation(op_calls)
            if duplicates['duplicate_pct'] > THRESHOLDS['duplicate_threshold']:
                monthly_savings = (duplicates['wasted_cost'] / period_days) * 30
                opportunities.append({
                    'type': 'cache',
                    'agent': agent['agent'],
                    'operation': op['name'],
                    'title': f"Cache {agent['agent']}.{op['name']}",
                    'detail': f"{len(op_calls)} calls, {format_percentage(duplicates['duplicate_pct'])} are duplicates",
                    'monthly_savings': monthly_savings,
                    'evidence': duplicates,
                    'target_page': '💾 Cache Analyzer',
                    'filter_key': 'cache_filter',
                    'filter_value': {
                        'agent': agent['agent'],
                        'operation': op['name'],
                        'tab': 'repeated',
                        'source': 'cost_estimator',
                    },
                })
            
            # Check for routing opportunity
            model_usage = analyze_model_usage(op_calls)
            if model_usage['routing_opportunity']:
                monthly_savings = (model_usage['potential_savings'] / period_days) * 30
                opportunities.append({
                    'type': 'routing',
                    'agent': agent['agent'],
                    'operation': op['name'],
                    'title': f"Route {agent['agent']}.{op['name']} to cheaper model",
                    'detail': f"{model_usage['simple_expensive_count']} simple calls using expensive model",
                    'monthly_savings': monthly_savings,
                    'evidence': model_usage,
                    'target_page': '🔀 Model Router',
                    'filter_key': 'router_filter',
                    'filter_value': {
                        'agent': agent['agent'],
                        'operation': op['name'],
                        'tab': 'cost',
                        'source': 'cost_estimator',
                    },
                })
            
            # Check for prompt size opportunity
            prompt_analysis = analyze_prompt_sizes(op_calls)
            if prompt_analysis['opportunity']:
                monthly_savings = (prompt_analysis['potential_savings'] / period_days) * 30
                opportunities.append({
                    'type': 'prompt',
                    'agent': agent['agent'],
                    'operation': op['name'],
                    'title': f"Reduce {agent['agent']}.{op['name']} prompt size",
                    'detail': f"Avg {format_tokens(int(prompt_analysis['avg_tokens']))} tokens, {prompt_analysis['large_prompt_count']} large prompts",
                    'monthly_savings': monthly_savings,
                    'evidence': prompt_analysis,
                    'target_page': '✨ Prompt Optimizer',
                    'filter_key': 'prompt_filter',
                    'filter_value': {
                        'agent': agent['agent'],
                        'operation': op['name'],
                        'tab': 'long',
                        'source': 'cost_estimator',
                    },
                })
    
    # Sort by savings potential
    opportunities.sort(key=lambda x: -x['monthly_savings'])
    
    return opportunities[:5]  # Top 5


# =============================================================================
# RENDER COMPONENTS
# =============================================================================

def render_spend_summary(overview: Dict, trends: Dict, total_potential_savings: float):
    """Render the spend summary section."""
    
    kpis = overview.get('kpis', {})
    trend_data = trends.get('trends', {})
    
    total_cost = kpis.get('total_cost', 0)
    total_calls = kpis.get('total_calls', 0)
    cost_change = trend_data.get('total_cost', {}).get('change_pct', 0)
    
    # Calculate projections
    # Assuming 7-day period for now
    daily_rate = total_cost / 7
    monthly_rate = daily_rate * 30
    cost_per_request = total_cost / total_calls if total_calls > 0 else 0
    
    # KPI row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Spend",
            format_cost(total_cost),
        )
    
    with col2:
        delta_color = "inverse" if cost_change > 0 else "normal"
        status = "⚠️" if cost_change > THRESHOLDS['cost_change_warning'] else ""
        st.metric(
            f"vs Last Week {status}",
            f"{cost_change:+.0f}%",
            delta=f"{format_cost(abs(total_cost * cost_change / 100))}",
            delta_color=delta_color
        )
    
    with col3:
        st.metric(
            "Monthly Rate",
            format_cost(monthly_rate),
        )
    
    with col4:
        st.metric(
            "Cost/Request",
            format_cost(cost_per_request),
            help=f"Across {total_calls:,} requests"
        )
    
    # Potential savings callout
    if total_potential_savings > 0:
        st.info(f"💡 **Potential savings: {format_cost(total_potential_savings)}/mo** with optimizations (see below)")


def render_agent_breakdown(agent_data: List[Dict], period_days: float):
    """Render the expandable agent breakdown section."""
    
    st.subheader("📍 Where Money Goes")
    st.caption("Click an agent row to see operation breakdown")
    
    # Build summary table
    table_data = []
    for agent in agent_data:
        trend_str = f"{agent['trend_pct']:+.0f}%"
        if agent['trend_pct'] > THRESHOLDS['cost_change_warning']:
            trend_str = f"⚠️ {trend_str}"
        
        table_data.append({
            'Agent': agent['agent'],
            'Cost': format_cost(agent['total_cost']),
            'Share': f"{agent['share_pct']:.0f}%",
            'Trend': trend_str,
            'Top Operation': agent['top_operation'] or '—',
        })
    
    # Show table
    df = pd.DataFrame(table_data)
    st.dataframe(df, width='stretch', hide_index=True)
    
    # Expandable agent details
    for agent in agent_data:
        with st.expander(f"**{agent['agent']}** — {format_cost(agent['total_cost'])} ({agent['share_pct']:.0f}%)"):
            render_agent_detail(agent, period_days)


def render_agent_detail(agent: Dict, period_days: float):
    """Render expanded agent detail with operations - clickable rows."""
    
    # Operations table
    op_data = []
    for op in agent['operations']:
        trend_str = f"{op['trend_pct']:+.0f}%"
        if op['trend_pct'] > THRESHOLDS['cost_change_warning']:
            trend_str = f"⚠️ {trend_str}"
        
        op_data.append({
            'Operation': op['name'],
            'Calls': op['calls'],
            'Avg Cost': format_cost(op['avg_cost']),
            'Total': format_cost(op['total_cost']),
            'Trend': trend_str,
        })
    
    df = pd.DataFrame(op_data)
    
    st.caption("Click a row to view calls →")
    
    selection = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"ops_table_{agent['agent']}"
    )
    
    # Handle row selection - navigate to Activity Monitor
    selected_rows = selection.selection.rows if selection.selection else []
    
    if selected_rows:
        selected_idx = selected_rows[0]
        if selected_idx < len(agent['operations']):
            op = agent['operations'][selected_idx]
            st.session_state['activity_filter_agent'] = agent['agent']
            st.session_state['activity_filter_operation'] = op['name']
            st.session_state['activity_filter_source'] = 'cost_estimator'
            st.session_state['_nav_to'] = '📡 Activity Monitor'
            st.rerun()


def render_savings_opportunities(opportunities: List[Dict]):
    """Render cost issues as a compact data-focused table."""
    
    st.subheader("🎯 Cost Issues")
    
    if not opportunities:
        st.success("✅ No cost issues detected")
        return
    
    # Type icons
    type_icons = {
        'cache': '🗄️',
        'routing': '🔀',
        'prompt': '📝',
    }
    
    # Issue labels (data-focused, not recommendation-focused)
    def get_issue_label(opp):
        if opp['type'] == 'cache':
            dupes = opp['evidence'].get('duplicate_count', 0)
            return f"{dupes} duplicates"
        elif opp['type'] == 'routing':
            count = opp['evidence'].get('simple_expensive_count', 0)
            return f"{count} on expensive model"
        elif opp['type'] == 'prompt':
            count = opp['evidence'].get('large_prompt_count', 0)
            return f"{count} large prompts"
        return "Issue"
    
    # Build table data
    table_data = []
    for opp in opportunities:
        icon = type_icons.get(opp['type'], '⚠️')
        table_data.append({
            'Type': icon,
            'Agent.Operation': f"{opp['agent']}.{opp['operation']}",
            'Issue': get_issue_label(opp),
            'Wasted': format_cost(opp['monthly_savings']) + "/mo",
        })
    
    # Display as selectable dataframe
    df = pd.DataFrame(table_data)
    
    st.caption("Click a row to view the data →")
    
    selection = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="cost_issues_table"
    )
    
    # Handle row selection - navigate to appropriate page
    selected_rows = selection.selection.rows if selection.selection else []
    
    if selected_rows:
        selected_idx = selected_rows[0]
        if selected_idx < len(opportunities):
            opp = opportunities[selected_idx]
            st.session_state[opp['filter_key']] = opp['filter_value']
            st.session_state['_nav_to'] = opp['target_page']
            st.rerun()
    
    # Total
    total_savings = sum(o['monthly_savings'] for o in opportunities)
    st.caption(f"Total: **{format_cost(total_savings)}/mo** wasted")


def render_model_breakdown(calls: List[Dict]):
    """Render cost breakdown by model."""
    
    st.subheader("📊 Cost by Model")
    
    # Group by model
    by_model = defaultdict(lambda: {'cost': 0, 'calls': 0})
    
    for call in calls:
        model = call.get('model_name', 'unknown')
        by_model[model]['cost'] += call.get('total_cost', 0)
        by_model[model]['calls'] += 1
    
    if not by_model:
        st.info("No model data available")
        return
    
    total_cost = sum(m['cost'] for m in by_model.values())
    
    # Build table
    table_data = []
    for model, data in sorted(by_model.items(), key=lambda x: -x[1]['cost']):
        share = (data['cost'] / total_cost * 100) if total_cost > 0 else 0
        table_data.append({
            'Model': format_model_name(model),
            'Calls': data['calls'],
            'Cost': format_cost(data['cost']),
            'Share': f"{share:.0f}%",
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, width='stretch', hide_index=True)


# =============================================================================
# MAIN RENDER
# =============================================================================

def render():
    """Main render function for Cost Estimator page."""
    
    # Header
    st.title("💰 Cost Estimator")
    
    selected_project = st.session_state.get('selected_project')
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        project_label = selected_project or "All Projects"
        st.caption(f"Analyzing: **{project_label}**")
    
    with col2:
        period = st.selectbox(
            "Period",
            options=['7d', '30d'],
            index=0,
            key="cost_period",
            label_visibility="collapsed"
        )
    
    with col3:
        if st.button("🔄 Refresh", width='stretch'):
            st.cache_data.clear()
            st.rerun()
    
    # Period days for calculations
    period_days = 7 if period == '7d' else 30
    
    st.divider()
    
    # Load data
    try:
        overview = get_project_overview(selected_project)
        trends = get_comparative_metrics(selected_project, period=period)
        calls = get_llm_calls(project_name=selected_project, limit=1000)
        
        if overview.get('kpis', {}).get('total_calls', 0) == 0:
            render_empty_state(
                message="No cost data available",
                icon="💰",
                suggestion="Run AI agents with Observatory tracking enabled to see cost analysis"
            )
            return
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    # Analyze data
    agent_data = analyze_agent_costs(calls, period_days)
    opportunities = generate_savings_opportunities(agent_data, calls, period_days)
    total_potential_savings = sum(o['monthly_savings'] for o in opportunities)
    
    # Section 1: Spend Summary
    st.subheader(f"📊 Spend Summary (Last {period})")
    render_spend_summary(overview, trends, total_potential_savings)
    
    st.divider()
    
    # Section 2: Where Money Goes
    render_agent_breakdown(agent_data, period_days)
    
    st.divider()
    
    # Section 3: Cost by Model
    render_model_breakdown(calls)
    
    st.divider()
    
    # Section 4: Cost Issues
    render_savings_opportunities(opportunities)