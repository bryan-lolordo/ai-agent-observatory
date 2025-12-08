"""
Cost Estimator - Spend Analysis & Forecasting
Location: dashboard/pages/cost_estimator.py

Executive-focused cost analysis:
- Current spend summary with trends
- Where money is going (model + agent breakdown)
- Scale calculator for growth planning
- Savings opportunity summary
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any

from dashboard.utils.data_fetcher import (
    get_project_overview,
    get_comparative_metrics,
    get_time_series_data,
)
from dashboard.utils.formatters import (
    format_cost,
    format_tokens,
    format_percentage,
    format_model_name,
)
from dashboard.components.metric_cards import render_empty_state
from dashboard.components.charts import (
    create_cost_breakdown_pie,
    create_time_series_chart,
)
from dashboard.components.filters import render_time_period_filter


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_cost_stats(overview: Dict[str, Any], period_days: float) -> Dict[str, float]:
    """Calculate cost statistics for projections."""
    total_cost = overview.get('kpis', {}).get('total_cost', 0)
    total_calls = overview.get('kpis', {}).get('total_calls', 0)
    
    cost_per_day = total_cost / max(period_days, 0.04)  # Handle hourly
    
    return {
        'total_cost': total_cost,
        'cost_per_day': cost_per_day,
        'cost_per_month': cost_per_day * 30,
        'cost_per_year': cost_per_day * 365,
        'cost_per_request': total_cost / max(total_calls, 1),
        'total_requests': total_calls,
    }


def calculate_total_savings_potential(overview: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate combined savings potential from all optimizations."""
    cache_metrics = overview.get('cache_metrics', {})
    routing_metrics = overview.get('routing_metrics', {})
    total_cost = overview.get('kpis', {}).get('total_cost', 0)
    
    # Actual savings (if optimizations are enabled)
    actual_cache_savings = cache_metrics.get('cost_saved', 0) or 0
    actual_routing_savings = routing_metrics.get('total_savings', 0) or 0
    actual_total = actual_cache_savings + actual_routing_savings
    
    # Potential additional savings
    cache_enabled = cache_metrics.get('total_requests', 0) > 0 and cache_metrics.get('cache_hits', 0) > 0
    routing_enabled = routing_metrics.get('total_decisions', 0) > 0
    
    potential_cache = 0 if cache_enabled else total_cost * 0.25  # 25% potential
    potential_routing = 0 if routing_enabled else total_cost * 0.20  # 20% potential
    potential_total = potential_cache + potential_routing
    
    return {
        'actual_savings': actual_total,
        'actual_cache': actual_cache_savings,
        'actual_routing': actual_routing_savings,
        'potential_savings': potential_total,
        'potential_cache': potential_cache,
        'potential_routing': potential_routing,
        'cache_enabled': cache_enabled,
        'routing_enabled': routing_enabled,
        'monthly_potential': potential_total * 30,
    }


def scale_projection(cost_stats: Dict[str, float], multiplier: float) -> Dict[str, float]:
    """Project costs at a given scale multiplier."""
    return {
        'daily': cost_stats['cost_per_day'] * multiplier,
        'monthly': cost_stats['cost_per_month'] * multiplier,
        'yearly': cost_stats['cost_per_year'] * multiplier,
        'requests_per_day': (cost_stats['total_requests'] / max(cost_stats['total_cost'] / cost_stats['cost_per_day'], 1)) * multiplier,
    }


# =============================================================================
# MAIN RENDER FUNCTION
# =============================================================================

def render():
    """Render the Cost Estimator page."""
    
    st.title("💰 Cost Estimator")
    
    selected_project = st.session_state.get('selected_project')
    
    # Header controls
    col1, col2 = st.columns([3, 1])
    with col1:
        project_label = selected_project or "All Projects"
        st.caption(f"Analyzing: **{project_label}**")
    with col2:
        time_period = render_time_period_filter(key="cost_period", label="Period")
    
    # Map period to days
    period_map = {"1h": 0.04, "24h": 1, "7d": 7, "30d": 30}
    period_days = period_map.get(time_period, 7)
    
    st.divider()
    
    # Load data
    try:
        overview = get_project_overview(selected_project)
        trends = get_comparative_metrics(selected_project, period=time_period)
        
        if overview.get('kpis', {}).get('total_calls', 0) == 0:
            render_empty_state(
                message="No cost data available",
                icon="💰",
                suggestion="Run AI agents with Observatory to start tracking costs"
            )
            return
            
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    # Calculate stats
    cost_stats = calculate_cost_stats(overview, period_days)
    savings = calculate_total_savings_potential(overview)
    trend_data = trends.get('trends', {})
    
    # =========================================================================
    # SECTION 1: Spend Summary
    # =========================================================================
    st.subheader("📊 Spend Summary")
    
    # Savings callout if applicable
    if savings['actual_savings'] > 0:
        st.success(f"💰 **Saved {format_cost(savings['actual_savings'])} this period** through optimizations")
    
    # Core metrics
    cost_change = trend_data.get('total_cost', {}).get('change_pct', 0)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            f"Spend ({time_period})",
            format_cost(cost_stats['total_cost']),
            delta=f"{cost_change:+.0f}%" if abs(cost_change) > 1 else None,
            delta_color="inverse"
        )
    
    with col2:
        st.metric(
            "Daily Rate",
            format_cost(cost_stats['cost_per_day']),
            help="Average daily spend"
        )
    
    with col3:
        st.metric(
            "Monthly Projection",
            format_cost(cost_stats['cost_per_month']),
            help="Based on current daily rate"
        )
    
    with col4:
        st.metric(
            "Cost per Request",
            format_cost(cost_stats['cost_per_request']),
            help=f"Across {cost_stats['total_requests']:,} requests"
        )
    
    # Cost trend chart
    try:
        interval = 'hour' if period_days <= 1 else 'day'
        cost_data = get_time_series_data(
            selected_project,
            metric='cost',
            interval=interval,
            hours=int(period_days * 24)
        )
        
        if cost_data:
            fig = create_time_series_chart(cost_data, metric_name="Cost ($)", title="")
            st.plotly_chart(fig, width='stretch')
    except Exception:
        pass  # Skip chart if data unavailable
    
    st.divider()
    
    # =========================================================================
    # SECTION 2: Where Money Goes
    # =========================================================================
    st.subheader("📍 Where Money Goes")
    
    col1, col2 = st.columns([1, 1])
    
    # Model breakdown (pie chart)
    with col1:
        st.markdown("**By Model**")
        cost_breakdown = overview.get('cost_breakdown', {})
        if cost_breakdown:
            fig = create_cost_breakdown_pie(cost_breakdown, title="")
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No model data")
    
    # Agent breakdown (table with ALL agents)
    with col2:
        st.markdown("**By Agent**")
        by_agent = overview.get('by_agent', {})
        
        if by_agent:
            # Build table for ALL agents
            agent_data = []
            for agent, data in by_agent.items():
                daily_cost = data['total_cost'] / max(period_days, 0.04)
                pct_of_total = (data['total_cost'] / cost_stats['total_cost'] * 100) if cost_stats['total_cost'] > 0 else 0
                
                agent_data.append({
                    'Agent': agent,
                    'Cost': format_cost(data['total_cost']),
                    'Monthly': format_cost(daily_cost * 30),
                    'Share': f"{pct_of_total:.1f}%",
                    '_sort': data['total_cost']  # Hidden sort column
                })
            
            # Sort by cost descending
            agent_data.sort(key=lambda x: x['_sort'], reverse=True)
            
            # Remove sort column and display
            df = pd.DataFrame([{k: v for k, v in row.items() if k != '_sort'} for row in agent_data])
            st.dataframe(df, width='stretch', hide_index=True)
        else:
            st.info("No agent data")
    
    st.divider()
    
    # =========================================================================
    # SECTION 3: Scale Calculator
    # =========================================================================
    st.subheader("📈 Scale Calculator")
    st.caption("Project costs at different traffic levels")
    
    # Simple slider
    scale = st.slider(
        "Traffic Multiplier",
        min_value=1,
        max_value=20,
        value=1,
        step=1,
        format="%dx",
        key="scale_slider"
    )
    
    projection = scale_projection(cost_stats, scale)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Daily", format_cost(projection['daily']))
    with col2:
        st.metric("Monthly", format_cost(projection['monthly']))
    with col3:
        st.metric("Yearly", format_cost(projection['yearly']))
    with col4:
        st.metric("Requests/Day", f"{projection['requests_per_day']:,.0f}")
    
    if scale > 1:
        increase = projection['monthly'] - cost_stats['cost_per_month']
        st.info(f"At **{scale}x** traffic: +{format_cost(increase)}/month additional spend")
    
    st.divider()
    
    # =========================================================================
    # SECTION 4: Savings Opportunity
    # =========================================================================
    st.subheader("💡 Savings Opportunity")
    
    if savings['potential_savings'] > 0:
        # There are savings to be had
        st.warning(
            f"**You could save ~{format_cost(savings['monthly_potential'])}/month** by enabling optimizations"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if not savings['cache_enabled']:
                st.markdown("**🗄️ Semantic Caching**")
                st.write(f"Potential: {format_cost(savings['potential_cache'] * 30)}/month")
                st.caption("→ Go to **Cache Analyzer** to enable")
            else:
                st.success(f"✅ Cache enabled — saving {format_cost(savings['actual_cache'])}")
        
        with col2:
            if not savings['routing_enabled']:
                st.markdown("**🔀 Smart Model Routing**")
                st.write(f"Potential: {format_cost(savings['potential_routing'] * 30)}/month")
                st.caption("→ Go to **Model Router** to enable")
            else:
                st.success(f"✅ Routing enabled — saving {format_cost(savings['actual_routing'])}")
    
    elif savings['actual_savings'] > 0:
        # Already optimized
        st.success("✅ **Optimizations active!**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Saved", format_cost(savings['actual_savings']))
        with col2:
            st.metric("Cache Savings", format_cost(savings['actual_cache']))
        with col3:
            st.metric("Routing Savings", format_cost(savings['actual_routing']))
    
    else:
        # No data yet
        st.info("Enable caching and routing to start saving. See **Cache Analyzer** and **Model Router** pages.")