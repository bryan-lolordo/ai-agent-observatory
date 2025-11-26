"""
Cost Estimator Page - Forecasting and Optimization
Location: dashboard/pages/cost_estimator.py

Comprehensive cost analysis, forecasting, and optimization recommendations.
Includes actual data when available and potential savings estimates.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd

from dashboard.utils.data_fetcher import (
    get_project_overview,
    get_comparative_metrics,
    get_time_series_data,
    get_sessions,
    get_cost_forecast,
)
from dashboard.utils.formatters import (
    format_cost,
    format_latency,
    format_tokens,
    format_percentage,
    format_model_name,
)
from dashboard.components.metric_cards import (
    render_metric_row,
    render_empty_state,
)
from dashboard.components.charts import (
    create_cost_breakdown_pie,
    create_time_series_chart,
    create_bar_chart,
)
from dashboard.components.filters import (
    render_time_period_filter,
)


def calculate_cost_stats(overview: Dict[str, Any], period_days: int = 7) -> Dict[str, float]:
    """Calculate cost statistics for different time periods."""
    total_cost = overview.get('kpis', {}).get('total_cost', 0)
    total_calls = overview.get('kpis', {}).get('total_calls', 0)
    
    # Calculate daily average
    cost_per_day = total_cost / max(period_days, 1)
    
    return {
        'total_cost': total_cost,
        'cost_per_day': cost_per_day,
        'cost_per_week': cost_per_day * 7,
        'cost_per_month': cost_per_day * 30,
        'cost_per_request': total_cost / max(total_calls, 1),
        'requests_per_day': total_calls / max(period_days, 1)
    }


def estimate_cache_savings(overview: Dict[str, Any]) -> Dict[str, Any]:
    """Estimate potential cache savings if not implemented."""
    cache_metrics = overview.get('cache_metrics', {})
    total_requests = cache_metrics.get('total_requests', 0)
    
    # Check if cache is actually being used
    has_real_cache = total_requests > 0 and cache_metrics.get('cache_hits', 0) > 0
    
    if has_real_cache:
        # Return actual cache performance
        hit_rate = cache_metrics.get('hit_rate', 0)
        actual_savings = cache_metrics.get('cost_saved', 0)
        return {
            'enabled': True,
            'hit_rate': hit_rate,
            'actual_savings': actual_savings,
            'tokens_saved': cache_metrics.get('tokens_saved', 0),
            'monthly_savings': actual_savings * 30  # Rough projection
        }
    else:
        # Estimate potential savings
        total_cost = overview.get('kpis', {}).get('total_cost', 0)
        total_calls = overview.get('kpis', {}).get('total_calls', 0)
        
        # Conservative estimates
        estimated_hit_rate = 0.30  # 30% of calls could be cached
        estimated_savings_per_day = total_cost * estimated_hit_rate
        
        return {
            'enabled': False,
            'estimated_hit_rate': estimated_hit_rate,
            'potential_daily_savings': estimated_savings_per_day,
            'potential_monthly_savings': estimated_savings_per_day * 30,
            'cacheable_calls': int(total_calls * estimated_hit_rate)
        }


def estimate_routing_savings(overview: Dict[str, Any]) -> Dict[str, Any]:
    """Estimate potential routing savings if not implemented."""
    routing_metrics = overview.get('routing_metrics', {})
    
    # Check if real routing is being used
    has_real_routing = routing_metrics.get('total_decisions', 0) > 0
    has_alternatives = False
    
    # Check if routing decisions have alternatives (indicates real routing)
    by_model = overview.get('by_model', {})
    if len(by_model) > 1:
        # Multiple models being used - might have routing
        has_alternatives = True
    
    if has_real_routing and has_alternatives:
        # Return actual routing performance
        return {
            'enabled': True,
            'accuracy': routing_metrics.get('routing_accuracy', 0),
            'actual_savings': routing_metrics.get('total_cost_savings', 0),
            'total_decisions': routing_metrics.get('total_decisions', 0),
            'monthly_savings': routing_metrics.get('total_cost_savings', 0) * 30
        }
    else:
        # Estimate potential savings
        total_cost = overview.get('kpis', {}).get('total_cost', 0)
        total_calls = overview.get('kpis', {}).get('total_calls', 0)
        
        # Analyze current model usage
        most_expensive_model_cost = 0
        for model, metrics in by_model.items():
            model_cost = metrics.get('total_cost', 0)
            if model_cost > most_expensive_model_cost:
                most_expensive_model_cost = model_cost
        
        # Estimate: 40% of calls could use cheaper models
        routeable_percentage = 0.40
        avg_savings_per_routed_call = 0.60  # Save 60% on routed calls
        
        potential_savings = total_cost * routeable_percentage * avg_savings_per_routed_call
        
        return {
            'enabled': False,
            'routeable_percentage': routeable_percentage,
            'potential_daily_savings': potential_savings,
            'potential_monthly_savings': potential_savings * 30,
            'routeable_calls': int(total_calls * routeable_percentage)
        }


def calculate_scenario(base_stats: Dict, multiplier: float, model_strategy: str, cache_enabled: bool) -> Dict[str, Any]:
    """Calculate cost for a given scenario."""
    # Base calculation
    daily_requests = base_stats['requests_per_day'] * multiplier
    base_cost_per_request = base_stats['cost_per_request']
    
    # Adjust for model strategy
    if model_strategy == "All Premium (GPT-4o)":
        cost_multiplier = 1.5  # 50% more expensive
    elif model_strategy == "All Budget (Mistral)":
        cost_multiplier = 0.3  # 70% cheaper
    elif model_strategy == "Optimized Mix":
        cost_multiplier = 0.65  # 35% cheaper with routing
    else:  # Current Mix
        cost_multiplier = 1.0
    
    adjusted_cost_per_request = base_cost_per_request * cost_multiplier
    daily_cost = daily_requests * adjusted_cost_per_request
    
    # Apply cache savings
    if cache_enabled:
        daily_cost *= 0.70  # 30% cache hit rate saves 30% of cost
    
    return {
        'daily_requests': int(daily_requests),
        'cost_per_request': adjusted_cost_per_request,
        'daily_cost': daily_cost,
        'weekly_cost': daily_cost * 7,
        'monthly_cost': daily_cost * 30,
        'yearly_cost': daily_cost * 365
    }


def render_cache_section(overview: Dict[str, Any], cost_stats: Dict[str, float]):
    """Render cache analysis - works with or without implementation."""
    st.subheader("💾 Cache Performance & Savings")
    
    cache_analysis = estimate_cache_savings(overview)
    
    if cache_analysis['enabled']:
        # Real cache data available
        st.success("✅ Cache Active and Working")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Hit Rate", format_percentage(cache_analysis['hit_rate']))
        with col2:
            st.metric("Actual Savings (Today)", format_cost(cache_analysis['actual_savings']))
        with col3:
            st.metric("Monthly Projection", format_cost(cache_analysis['monthly_savings']))
        with col4:
            st.metric("Tokens Saved", format_tokens(cache_analysis['tokens_saved']))
        
    else:
        # Show potential savings
        st.info("💡 Cache Not Enabled Yet - See Potential Savings Below")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Estimated Hit Rate", 
                format_percentage(cache_analysis['estimated_hit_rate']),
                help="Industry average for semantic caching"
            )
        with col2:
            st.metric(
                "Potential Daily Savings",
                format_cost(cache_analysis['potential_daily_savings'])
            )
        with col3:
            st.metric(
                "Potential Monthly Savings",
                format_cost(cache_analysis['potential_monthly_savings']),
                delta=f"-{format_percentage(cache_analysis['estimated_hit_rate'])} cost"
            )
        
        with st.expander("📊 How Cache Savings Are Calculated"):
            st.markdown(f"""
            **Current Usage:**
            - Total calls per day: ~{int(cost_stats['requests_per_day'])}
            - Current daily cost: {format_cost(cost_stats['cost_per_day'])}
            
            **With Caching (30% hit rate):**
            - Cacheable calls: ~{cache_analysis['cacheable_calls']}/day
            - Cache hits save 100% of cost for those calls
            - Daily savings: {format_cost(cache_analysis['potential_daily_savings'])}
            
            **How to Enable:**
            1. Implement prompt normalization
            2. Add semantic similarity matching
            3. Store responses in cache with TTL
            4. Check cache before LLM calls
            
            [→ View Cache Implementation Guide]
            """)


def render_routing_section(overview: Dict[str, Any], cost_stats: Dict[str, float]):
    """Render routing analysis - works with or without implementation."""
    st.subheader("🔀 Model Routing & Optimization")
    
    routing_analysis = estimate_routing_savings(overview)
    
    if routing_analysis['enabled']:
        # Real routing data available
        st.success("✅ Smart Routing Active")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Routing Accuracy", format_percentage(routing_analysis['accuracy']))
        with col2:
            st.metric("Total Decisions", f"{routing_analysis['total_decisions']:,}")
        with col3:
            st.metric("Actual Savings (Today)", format_cost(routing_analysis['actual_savings']))
        with col4:
            st.metric("Monthly Projection", format_cost(routing_analysis['monthly_savings']))
        
    else:
        # Show potential savings
        st.info("💡 Smart Routing Not Enabled Yet - See Potential Savings Below")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Routeable Calls",
                format_percentage(routing_analysis['routeable_percentage']),
                help="Percentage of calls that could use cheaper models"
            )
        with col2:
            st.metric(
                "Potential Daily Savings",
                format_cost(routing_analysis['potential_daily_savings'])
            )
        with col3:
            st.metric(
                "Potential Monthly Savings",
                format_cost(routing_analysis['potential_monthly_savings']),
                delta=f"-{format_percentage(routing_analysis['routeable_percentage'] * 0.6)} cost"
            )
        
        with st.expander("📊 How Routing Savings Are Calculated"):
            st.markdown(f"""
            **Current Usage:**
            - Total calls per day: ~{int(cost_stats['requests_per_day'])}
            - Current daily cost: {format_cost(cost_stats['cost_per_day'])}
            
            **With Smart Routing:**
            - Routeable calls: ~{routing_analysis['routeable_calls']}/day (40%)
            - These could use models 60% cheaper
            - Daily savings: {format_cost(routing_analysis['potential_daily_savings'])}
            
            **Recommended Strategy:**
            - Simple/classification → Mistral Small
            - Analysis/summary → Claude Sonnet
            - Complex reasoning → GPT-4o
            
            **How to Enable:**
            1. Analyze query complexity
            2. Map tasks to appropriate models
            3. Implement routing logic
            4. Track routing decisions
            
            [→ View Routing Implementation Guide]
            """)


def render():
    """Render the Cost Estimator page."""
    
    st.title("💰 Cost Estimator & Forecasting")
    
    # Get selected project
    selected_project = st.session_state.get('selected_project')
    
    # Project indicator
    if selected_project:
        st.info(f"📊 Analyzing costs for: **{selected_project}**")
    else:
        st.info("📊 Analyzing costs for: **All Projects**")
    
    # Time period selector
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption("Select time period for historical analysis")
    with col2:
        time_period = render_time_period_filter(key="cost_estimator_period", label="Period")
    
    # Map time period to days
    period_map = {"1h": 0.04, "24h": 1, "7d": 7, "30d": 30}
    period_days = period_map.get(time_period, 7)
    
    st.divider()
    
    # Fetch data
    try:
        with st.spinner("Loading cost data..."):
            overview = get_project_overview(selected_project)
            
            if overview['total_calls'] == 0:
                render_empty_state(
                    message="No cost data available yet",
                    icon="💰",
                    suggestion="Run your AI agents to start tracking costs"
                )
                return
    
    except Exception as e:
        st.error(f"Error loading cost data: {str(e)}")
        return
    
    # Calculate statistics
    cost_stats = calculate_cost_stats(overview, period_days)
    
    # Section 1: KPI Cards
    st.subheader("📊 Cost Overview")
    
    metrics = [
        {
            "label": f"Cost (Last {time_period})",
            "value": format_cost(cost_stats['total_cost']),
        },
        {
            "label": "Daily Average",
            "value": format_cost(cost_stats['cost_per_day']),
        },
        {
            "label": "Weekly Projection",
            "value": format_cost(cost_stats['cost_per_week']),
        },
        {
            "label": "Monthly Projection",
            "value": format_cost(cost_stats['cost_per_month']),
        },
        {
            "label": "Cost per Request",
            "value": format_cost(cost_stats['cost_per_request']),
        },
        {
            "label": "Requests/Day",
            "value": f"{cost_stats['requests_per_day']:.0f}",
        }
    ]
    
    render_metric_row(metrics, columns=3)
    
    st.divider()
    
    # Section 2: Cost Trend
    st.subheader("📈 Cost Trend")
    
    try:
        cost_timeline = get_time_series_data(
            selected_project,
            metric='cost',
            interval='day',
            hours=period_days * 24
        )
        
        if cost_timeline:
            fig = create_time_series_chart(
                cost_timeline,
                metric_name="Cost ($)",
                title="Daily Cost Trend"
            )
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Not enough historical data for trend analysis")
    
    except Exception as e:
        st.warning(f"Could not load cost trend: {str(e)}")
    
    st.divider()
    
    # Section 3: Forecast Simulator
    st.subheader("🔮 Cost Forecast Simulator")
    
    # Toggle between simple and advanced mode
    mode = st.radio(
        "Mode",
        options=["Simple", "Advanced"],
        horizontal=True,
        key="forecast_mode"
    )
    
    if mode == "Simple":
        st.caption("Quick scenario analysis with preset configurations")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            traffic_scenario = st.selectbox(
                "Traffic Level",
                options=["Current", "2x Growth", "5x Growth", "10x Growth"],
                key="simple_traffic"
            )
        
        with col2:
            model_strategy = st.selectbox(
                "Model Strategy",
                options=["Current Mix", "Optimized Mix", "All Premium (GPT-4o)", "All Budget (Mistral)"],
                key="simple_model"
            )
        
        with col3:
            cache_enabled = st.checkbox("Enable Caching", value=False, key="simple_cache")
        
        # Calculate scenario
        traffic_multipliers = {"Current": 1.0, "2x Growth": 2.0, "5x Growth": 5.0, "10x Growth": 10.0}
        multiplier = traffic_multipliers[traffic_scenario]
        
        scenario = calculate_scenario(cost_stats, multiplier, model_strategy, cache_enabled)
        
        st.markdown("### Projected Costs")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Daily", format_cost(scenario['daily_cost']))
        with col2:
            st.metric("Weekly", format_cost(scenario['weekly_cost']))
        with col3:
            st.metric("Monthly", format_cost(scenario['monthly_cost']))
        with col4:
            st.metric("Yearly", format_cost(scenario['yearly_cost']))
        
        st.caption(f"Based on {scenario['daily_requests']:,} requests/day at {format_cost(scenario['cost_per_request'])} per request")
    
    else:  # Advanced mode
        st.caption("Fine-tune all parameters for detailed forecasting")
        
        with st.expander("⚙️ Advanced Parameters", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                requests_per_day = st.number_input(
                    "Requests per Day",
                    min_value=1,
                    max_value=1000000,
                    value=int(cost_stats['requests_per_day']),
                    step=10,
                    key="adv_requests"
                )
                
                avg_prompt_tokens = st.number_input(
                    "Avg Prompt Tokens",
                    min_value=10,
                    max_value=10000,
                    value=500,
                    step=50,
                    key="adv_prompt_tokens"
                )
                
                avg_completion_tokens = st.number_input(
                    "Avg Completion Tokens",
                    min_value=10,
                    max_value=10000,
                    value=200,
                    step=50,
                    key="adv_completion_tokens"
                )
            
            with col2:
                model_mix = st.selectbox(
                    "Model Distribution",
                    options=[
                        "Current Mix",
                        "100% GPT-4o",
                        "100% Claude Sonnet",
                        "100% Mistral Small",
                        "50% Premium / 50% Budget"
                    ],
                    key="adv_model_mix"
                )
                
                cache_hit_rate = st.slider(
                    "Cache Hit Rate",
                    min_value=0,
                    max_value=80,
                    value=0,
                    step=5,
                    format="%d%%",
                    key="adv_cache_rate"
                )
                
                routing_optimization = st.slider(
                    "Routing Optimization",
                    min_value=0,
                    max_value=50,
                    value=0,
                    step=5,
                    format="%d%% cost reduction",
                    key="adv_routing_opt"
                )
        
        # Calculate with custom parameters
        try:
            forecast = get_cost_forecast(
                selected_project,
                requests_per_hour=requests_per_day / 24,
                avg_prompt_tokens=avg_prompt_tokens,
                avg_completion_tokens=avg_completion_tokens,
                model_mix={"gpt-4o": 1.0}  # Simplified for now
            )
            
            # Adjust for cache and routing
            daily_cost = forecast['daily']['cost']
            daily_cost *= (1 - cache_hit_rate / 100)
            daily_cost *= (1 - routing_optimization / 100)
            
            st.markdown("### Custom Forecast")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Daily", format_cost(daily_cost))
            with col2:
                st.metric("Weekly", format_cost(daily_cost * 7))
            with col3:
                st.metric("Monthly", format_cost(daily_cost * 30))
            with col4:
                st.metric("Yearly", format_cost(daily_cost * 365))
        
        except Exception as e:
            st.warning(f"Custom forecast calculation error: {str(e)}")
    
    st.divider()
    
    # Section 4: Quick Scenarios Comparison
    st.subheader("🎯 Quick Scenario Comparison")
    
    scenarios = {
        "Current": calculate_scenario(cost_stats, 1.0, "Current Mix", False),
        "2x Growth": calculate_scenario(cost_stats, 2.0, "Current Mix", False),
        "Optimized": calculate_scenario(cost_stats, 1.0, "Optimized Mix", True),
        "Budget Mode": calculate_scenario(cost_stats, 1.0, "All Budget (Mistral)", True),
    }
    
    scenario_df = pd.DataFrame({
        "Scenario": scenarios.keys(),
        "Daily Cost": [format_cost(s['daily_cost']) for s in scenarios.values()],
        "Monthly Cost": [format_cost(s['monthly_cost']) for s in scenarios.values()],
        "Requests/Day": [f"{s['daily_requests']:,}" for s in scenarios.values()],
    })
    
    st.dataframe(scenario_df, width='stretch', hide_index=True)
    
    st.divider()
    
    # Section 5: Cost Breakdown
    st.subheader("💸 Cost Breakdown")
    
    tab1, tab2, tab3 = st.tabs(["By Model", "By Agent", "By Operation"])
    
    with tab1:
        cost_by_model = overview.get('cost_breakdown', {})
        if cost_by_model:
            fig = create_cost_breakdown_pie(cost_by_model, "Cost Distribution by Model")
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No model cost data available")
    
    with tab2:
        by_agent = overview.get('by_agent', {})
        if by_agent:
            agent_costs = {agent: data['total_cost'] for agent, data in by_agent.items()}
            fig = create_cost_breakdown_pie(agent_costs, "Cost Distribution by Agent")
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No agent cost data available")
    
    with tab3:
        by_operation = overview.get('by_operation', {})
        if by_operation:
            operation_costs = {op: data['total_cost'] for op, data in by_operation.items()}
            fig = create_bar_chart(
                operation_costs,
                x_label="Operation",
                y_label="Cost ($)",
                title="Cost by Operation Type"
            )
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No operation cost data available")
    
    st.divider()
    
    # Section 6: Cost Hotspots
    st.subheader("🔥 Cost Hotspots")
    
    by_agent = overview.get('by_agent', {})
    if by_agent:
        # Create hotspots table
        hotspots = []
        for agent, data in by_agent.items():
            daily_cost = data['total_cost'] / period_days
            monthly_cost = daily_cost * 30
            percentage = (data['total_cost'] / cost_stats['total_cost']) * 100 if cost_stats['total_cost'] > 0 else 0
            
            hotspots.append({
                'Agent': agent,
                'Calls/Day': f"{data['count'] / period_days:.0f}",
                'Daily Cost': format_cost(daily_cost),
                'Monthly Cost': format_cost(monthly_cost),
                '% of Total': f"{percentage:.1f}%"
            })
        
        # Sort by cost
        hotspots.sort(key=lambda x: float(x['Monthly Cost'].replace('$', '').replace(',', '')), reverse=True)
        
        hotspot_df = pd.DataFrame(hotspots)
        st.dataframe(hotspot_df, width='stretch', hide_index=True)
    else:
        st.info("No agent data available")
    
    st.divider()
    
    # Section 7: Cache Savings
    render_cache_section(overview, cost_stats)
    
    st.divider()
    
    # Section 8: Routing Savings
    render_routing_section(overview, cost_stats)
    
    st.divider()
    
    # Section 9: Optimization Recommendations
    st.subheader("💡 Optimization Recommendations")
    
    recommendations = []
    
    # Analyze and generate recommendations
    cache_analysis = estimate_cache_savings(overview)
    routing_analysis = estimate_routing_savings(overview)
    
    # Cache recommendation
    if not cache_analysis['enabled']:
        recommendations.append({
            'priority': 1,
            'title': 'Implement Semantic Caching',
            'savings': cache_analysis['potential_monthly_savings'],
            'description': f"Could save {format_cost(cache_analysis['potential_monthly_savings'])}/month with 30% cache hit rate",
            'impact': 'High'
        })
    
    # Routing recommendation
    if not routing_analysis['enabled']:
        recommendations.append({
            'priority': 2,
            'title': 'Enable Smart Model Routing',
            'savings': routing_analysis['potential_monthly_savings'],
            'description': f"Could save {format_cost(routing_analysis['potential_monthly_savings'])}/month by routing to appropriate models",
            'impact': 'High'
        })
    
    # Analyze model usage
    by_model = overview.get('by_model', {})
    if 'gpt-4' in str(by_model).lower() or 'gpt-4o' in str(by_model).lower():
        recommendations.append({
            'priority': 3,
            'title': 'Optimize GPT-4 Usage',
            'savings': cost_stats['cost_per_month'] * 0.20,
            'description': 'Review GPT-4 calls - many could use Claude Sonnet or Mistral',
            'impact': 'Medium'
        })
    
    # Sort by savings
    recommendations.sort(key=lambda x: x['savings'], reverse=True)
    
    if recommendations:
        for i, rec in enumerate(recommendations[:5], 1):
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{i}. {rec['title']}** ({rec['impact']} Impact)")
                    st.caption(rec['description'])
                with col2:
                    st.metric("Potential Savings", format_cost(rec['savings']))
                st.divider()
    else:
        st.success("✅ Your setup is well optimized! No major recommendations at this time.")