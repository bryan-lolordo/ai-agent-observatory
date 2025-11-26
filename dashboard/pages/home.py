"""
Home Page - Mission Control Dashboard
Location: dashboard/pages/home.py

Comprehensive overview of AI agent performance with:
- KPIs with trends
- System activity and cost breakdown
- Performance metrics and health status
- Quality evaluation and routing insights
- Alerts and AI-generated optimization suggestions
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from dashboard.utils.data_fetcher import (
    get_project_overview,
    get_comparative_metrics,
    get_time_series_data,
    get_routing_analysis,
    get_quality_analysis,
    get_cache_analysis,
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
from dashboard.components.metric_cards import (
    render_kpi_grid,
    render_status_indicator,
    render_empty_state,
)
from dashboard.components.charts import (
    create_cost_breakdown_pie,
    create_time_series_chart,
    create_multi_line_chart,
    create_gauge_chart,
    create_bar_chart,
)
from dashboard.components.tables import (
    render_agent_comparison_table,
    render_routing_decisions_table,
    render_quality_scores_table,
)
from dashboard.components.filters import render_time_period_filter


def calculate_system_health(overview: Dict[str, Any]) -> list:
    """Calculate system health indicators based on metrics."""
    health_indicators = []
    
    # Cache health
    cache_metrics = overview.get('cache_metrics', {})
    hit_rate = cache_metrics.get('hit_rate', 0)
    if hit_rate > 0.30:
        health_indicators.append(("healthy", "Cache", f"Hit rate: {format_percentage(hit_rate)}"))
    elif hit_rate > 0.15:
        health_indicators.append(("warning", "Cache", f"Hit rate: {format_percentage(hit_rate)}"))
    else:
        health_indicators.append(("error", "Cache", f"Low hit rate: {format_percentage(hit_rate)}"))
    
    # Routing health
    routing_metrics = overview.get('routing_metrics', {})
    accuracy = routing_metrics.get('routing_accuracy', 0)
    if accuracy and accuracy > 0.85:
        health_indicators.append(("healthy", "Router", f"Accuracy: {format_percentage(accuracy)}"))
    elif accuracy and accuracy > 0.70:
        health_indicators.append(("warning", "Router", f"Accuracy: {format_percentage(accuracy)}"))
    elif accuracy:
        health_indicators.append(("error", "Router", f"Low accuracy: {format_percentage(accuracy)}"))
    
    # Quality health
    quality_metrics = overview.get('quality_metrics', {})
    avg_score = quality_metrics.get('avg_judge_score')
    if avg_score and avg_score > 8.5:
        health_indicators.append(("healthy", "Quality", f"Score: {format_score(avg_score)}"))
    elif avg_score and avg_score > 7.0:
        health_indicators.append(("warning", "Quality", f"Score: {format_score(avg_score)}"))
    elif avg_score:
        health_indicators.append(("error", "Quality", f"Low score: {format_score(avg_score)}"))
    
    # Latency health
    kpis = overview.get('kpis', {})
    avg_latency = kpis.get('avg_latency_ms', 0)
    if avg_latency < 2000:
        health_indicators.append(("healthy", "Latency", f"{format_latency(avg_latency)}"))
    elif avg_latency < 5000:
        health_indicators.append(("warning", "Latency", f"{format_latency(avg_latency)}"))
    else:
        health_indicators.append(("error", "Latency", f"Slow: {format_latency(avg_latency)}"))
    
    # Error health
    success_rate = kpis.get('success_rate', 1.0)
    if success_rate > 0.95:
        health_indicators.append(("healthy", "Errors", f"{format_percentage(1 - success_rate)} error rate"))
    elif success_rate > 0.90:
        health_indicators.append(("warning", "Errors", f"{format_percentage(1 - success_rate)} error rate"))
    else:
        health_indicators.append(("error", "Errors", f"High: {format_percentage(1 - success_rate)}"))
    
    return health_indicators


def detect_alerts(overview: Dict[str, Any], trends: Dict[str, Any]) -> list:
    """Detect anomalies and generate alerts."""
    alerts = []
    
    # Check cache hit rate drop
    cache_metrics = overview.get('cache_metrics', {})
    hit_rate = cache_metrics.get('hit_rate', 0)
    if hit_rate < 0.20 and cache_metrics.get('total_requests', 0) > 10:
        alerts.append(("warning", "Cache hit rate is low", f"Current: {format_percentage(hit_rate)}"))
    
    # Check cost spike
    cost_trend = trends.get('trends', {}).get('total_cost', {})
    if cost_trend.get('change_pct', 0) > 50:
        alerts.append(("warning", "Cost spike detected", f"+{cost_trend['change_pct']:.0f}% vs previous period"))
    
    # Check latency spike
    latency_trend = trends.get('trends', {}).get('avg_latency_ms', {})
    if latency_trend.get('change_pct', 0) > 25:
        alerts.append(("warning", "Latency increased", f"+{latency_trend['change_pct']:.0f}% vs previous period"))
    
    # Check hallucinations
    quality_metrics = overview.get('quality_metrics', {})
    hallucination_rate = quality_metrics.get('hallucination_rate', 0)
    if hallucination_rate > 0.05:
        alerts.append(("error", "High hallucination rate", f"{format_percentage(hallucination_rate)} of responses"))
    
    # Check routing savings
    routing_metrics = overview.get('routing_metrics', {})
    savings = routing_metrics.get('total_savings', 0)
    if savings > 1.0:
        alerts.append(("info", "Routing is saving money", f"${savings:.2f} saved in this period"))
    
    return alerts


def generate_insights(overview: Dict[str, Any]) -> list:
    """Generate AI-powered optimization insights."""
    insights = []
    
    kpis = overview.get('kpis', {})
    cache_metrics = overview.get('cache_metrics', {})
    routing_metrics = overview.get('routing_metrics', {})
    quality_metrics = overview.get('quality_metrics', {})
    
    # Cache optimization
    hit_rate = cache_metrics.get('hit_rate', 0)
    if hit_rate < 0.30 and cache_metrics.get('total_requests', 0) > 20:
        potential_savings = kpis.get('total_cost', 0) * (0.30 - hit_rate)
        insights.append(f"💾 Improving cache hit rate to 30% could save ~${potential_savings:.2f}")
    
    # Cost optimization
    by_model = overview.get('by_model', {})
    if by_model:
        most_expensive = max(by_model.items(), key=lambda x: x[1].get('total_cost', 0))
        model_name = most_expensive[0]
        model_cost = most_expensive[1].get('total_cost', 0)
        total_cost = kpis.get('total_cost', 1)
        if model_cost / total_cost > 0.60:
            insights.append(f"💰 {format_model_name(model_name)} accounts for {format_percentage(model_cost/total_cost)} of costs. Consider routing simpler tasks to cheaper models.")
    
    # Token optimization
    avg_tokens = kpis.get('avg_tokens_per_session', 0) / max(kpis.get('avg_calls_per_session', 1), 1)
    if avg_tokens > 2000:
        insights.append(f"📦 High token usage ({format_tokens(int(avg_tokens))} per call). Review prompts for compression opportunities.")
    
    # Quality optimization
    avg_score = quality_metrics.get('avg_judge_score')
    if avg_score and avg_score < 7.5:
        insights.append(f"⚖️ Quality score is {format_score(avg_score)}. Consider prompt engineering or model upgrades.")
    
    # Routing success
    if routing_metrics.get('total_savings', 0) > 0.50:
        insights.append(f"✅ Router is working well! Saved ${routing_metrics['total_savings']:.2f} through smart model selection.")
    
    # Latency optimization
    if kpis.get('avg_latency_ms', 0) > 3000:
        insights.append(f"⚡ Average latency is {format_latency(kpis['avg_latency_ms'])}. Consider parallelizing independent calls or using faster models.")
    
    return insights[:5]  # Limit to top 5 insights


def render():
    """Render the home page."""
    
    # Page header with time controls
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.title("🏠 Mission Control")
    with col2:
        time_period = render_time_period_filter(key="home_time_period", label="Time Range")
    with col3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Get selected project from session state
    selected_project = st.session_state.get('selected_project')
    
    # Last updated timestamp
    st.caption(f"Last updated: {datetime.now().strftime('%I:%M %p')}")
    
    st.divider()
    
    # Fetch all data
    try:
        with st.spinner("Loading dashboard data..."):
            overview = get_project_overview(selected_project)
            trends = get_comparative_metrics(selected_project, period=time_period)
            
            # Check if we have any data
            if overview['total_calls'] == 0:
                render_empty_state(
                    message="No data available yet",
                    icon="📊",
                    suggestion="Start tracking by running your AI agents with Observatory enabled"
                )
                return
    
    except Exception as e:
        st.error(f"Error loading dashboard data: {str(e)}")
        return
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "⚡ Performance", "⚖️ Quality", "💡 Insights"])
    
    # ========================================================================
    # TAB 1: OVERVIEW
    # ========================================================================
    with tab1:
        # Section 1: KPI Grid
        st.subheader("Key Metrics")
        
        kpis = overview.get('kpis', {})
        cache_metrics = overview.get('cache_metrics', {})
        routing_metrics = overview.get('routing_metrics', {})
        quality_metrics = overview.get('quality_metrics', {})
        
        current = trends.get('current', {})
        previous = trends.get('previous', {})
        trend_data = trends.get('trends', {})
        
        # Build metrics with trends
        metrics = []
        
        # Avg Cost per Request
        avg_cost = current.get('total_cost', 0) / max(current.get('total_calls', 1), 1)
        prev_avg_cost = previous.get('total_cost', 0) / max(previous.get('total_calls', 1), 1)
        cost_change = ((avg_cost - prev_avg_cost) / prev_avg_cost * 100) if prev_avg_cost > 0 else 0
        metrics.append({
            "label": "Avg Cost/Request",
            "value": format_cost(avg_cost),
            "delta": f"{cost_change:+.1f}%" if abs(cost_change) > 0.1 else None,
            "delta_color": "inverse" if cost_change < 0 else "normal"
        })
        
        # Avg Latency
        latency_change = trend_data.get('avg_latency_ms', {}).get('change_pct', 0)
        metrics.append({
            "label": "Avg Latency",
            "value": format_latency(kpis.get('avg_latency_ms', 0)),
            "delta": f"{latency_change:+.1f}%" if abs(latency_change) > 0.1 else None,
            "delta_color": "inverse" if latency_change < 0 else "normal"
        })
        
        # Cache Hit Rate
        metrics.append({
            "label": "Cache Hit Rate",
            "value": format_percentage(cache_metrics.get('hit_rate', 0)),
            "help_text": f"{cache_metrics.get('cache_hits', 0)} hits, {cache_metrics.get('cache_misses', 0)} misses"
        })
        
        # Routing Accuracy
        if routing_metrics.get('total_decisions', 0) > 0:
            metrics.append({
                "label": "Routing Accuracy",
                "value": format_percentage(routing_metrics.get('routing_accuracy', 0)) if routing_metrics.get('routing_accuracy') else "N/A",
                "help_text": f"{routing_metrics.get('total_decisions', 0)} routing decisions"
            })
        
        # Quality Score
        if quality_metrics.get('avg_judge_score'):
            metrics.append({
                "label": "Avg Quality Score",
                "value": format_score(quality_metrics['avg_judge_score']),
                "help_text": f"{quality_metrics.get('total_evaluated', 0)} evaluations"
            })
        
        # Success Rate
        metrics.append({
            "label": "Success Rate",
            "value": format_percentage(kpis.get('success_rate', 0)),
        })
        
        render_kpi_grid(metrics, columns=min(len(metrics), 4))
        
        st.divider()
        
        # Section 2: Activity Timeline
        st.subheader("System Activity (Last 24h)")
        
        try:
            # Get time series data for requests
            activity_data = get_time_series_data(
                selected_project,
                metric='count',
                interval='hour',
                hours=24
            )
            
            if activity_data:
                fig = create_time_series_chart(
                    activity_data,
                    metric_name="Requests",
                    title="Request Volume Over Time"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No activity data available for the selected time range")
        
        except Exception as e:
            st.warning(f"Could not load activity timeline: {str(e)}")
        
        st.divider()
        
        # Section 3: Cost Breakdown
        st.subheader("Where Is Your Money Going?")
        
        col1, col2 = st.columns(2)
        
        with col1:
            cost_breakdown = overview.get('cost_breakdown', {})
            if cost_breakdown:
                fig = create_cost_breakdown_pie(
                    cost_breakdown,
                    title="Cost by Model"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No cost data available")
        
        with col2:
            by_agent = overview.get('by_agent', {})
            if by_agent:
                agent_costs = {agent: data['total_cost'] for agent, data in by_agent.items()}
                fig = create_cost_breakdown_pie(
                    agent_costs,
                    title="Cost by Agent"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No agent data available")
    
    # ========================================================================
    # TAB 2: PERFORMANCE
    # ========================================================================
    with tab2:
        # Section 4: System Health
        st.subheader("System Health Status")
        
        health_indicators = calculate_system_health(overview)
        
        if health_indicators:
            cols = st.columns(min(len(health_indicators), 3))
            for i, (status, label, message) in enumerate(health_indicators):
                with cols[i % 3]:
                    render_status_indicator(label, status, message)
        else:
            st.info("Insufficient data to calculate system health")
        
        st.divider()
        
        # Section 5: Top Agents
        st.subheader("Top Agents by Performance")
        
        by_agent = overview.get('by_agent', {})
        if by_agent:
            render_agent_comparison_table(by_agent)
        else:
            st.info("No agent data available")
        
        st.divider()
        
        # Cache Performance Gauge
        st.subheader("Cache Performance")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if cache_metrics.get('total_requests', 0) > 0:
                fig = create_gauge_chart(
                    value=cache_metrics.get('hit_rate', 0) * 100,
                    title="Cache Hit Rate (%)",
                    min_value=0,
                    max_value=100
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No cache data available")
        
        with col2:
            st.metric("Tokens Saved", format_tokens(cache_metrics.get('tokens_saved', 0)))
            st.metric("Cost Saved", format_cost(cache_metrics.get('cost_saved', 0)))
            st.metric("Total Requests", f"{cache_metrics.get('total_requests', 0):,}")
    
    # ========================================================================
    # TAB 3: QUALITY
    # ========================================================================
    with tab3:
        # Section 6: Recent Judge Evaluations (Collapsible)
        st.subheader("Quality Evaluations")
        
        try:
            quality_analysis = get_quality_analysis(selected_project)
            best_examples = quality_analysis.get('best_examples', [])
            worst_examples = quality_analysis.get('worst_examples', [])
            
            if best_examples or worst_examples:
                with st.expander("🏆 Top 5 Best Responses", expanded=True):
                    if best_examples:
                        render_quality_scores_table(best_examples)
                    else:
                        st.info("No quality evaluations available")
                
                with st.expander("⚠️ Top 5 Worst Responses", expanded=False):
                    if worst_examples:
                        render_quality_scores_table(worst_examples)
                    else:
                        st.info("No quality evaluations available")
            else:
                st.info("No quality evaluations available yet. Enable LLM Judge to track quality.")
        
        except Exception as e:
            st.warning(f"Could not load quality data: {str(e)}")
        
        st.divider()
        
        # Section 7: Recent Routing Decisions (Collapsible)
        st.subheader("Routing Decisions")
        
        try:
            routing_analysis = get_routing_analysis(selected_project)
            recent_decisions = routing_analysis.get('recent_decisions', [])
            
            if recent_decisions:
                with st.expander(f"Recent Routing Decisions ({len(recent_decisions)})", expanded=True):
                    render_routing_decisions_table(recent_decisions[:10])
            else:
                st.info("No routing decisions available yet")
        
        except Exception as e:
            st.warning(f"Could not load routing data: {str(e)}")
        
        st.divider()
        
        # Error Analysis
        st.subheader("Error Analysis")
        
        total_calls = kpis.get('total_calls', 0)
        failed_calls = int(total_calls * (1 - kpis.get('success_rate', 1)))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Errors", f"{failed_calls:,}")
        with col2:
            st.metric("Error Rate", format_percentage(1 - kpis.get('success_rate', 1)))
        with col3:
            st.metric("Hallucinations", quality_metrics.get('hallucinations', 0))
    
    # ========================================================================
    # TAB 4: INSIGHTS
    # ========================================================================
    with tab4:
        # Section 8: Active Alerts
        st.subheader("⚠️ Active Alerts")
        
        alerts = detect_alerts(overview, trends)
        
        if alerts:
            # Show first 3 always
            for status, title, message in alerts[:3]:
                render_status_indicator(title, status, message)
            
            # Collapse the rest
            if len(alerts) > 3:
                with st.expander(f"Show {len(alerts) - 3} more alerts"):
                    for status, title, message in alerts[3:]:
                        render_status_indicator(title, status, message)
        else:
            st.success("✅ No alerts - all systems operating normally")
        
        st.divider()
        
        # Section 9: AI-Generated Insights
        st.subheader("💡 Optimization Insights")
        
        insights = generate_insights(overview)
        
        if insights:
            for insight in insights:
                st.info(insight)
        else:
            st.info("No optimization insights available yet. More data needed for analysis.")
        
        st.divider()
        
        # Section 10: Quick Stats Summary
        st.subheader("📈 Quick Stats")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Sessions", f"{kpis.get('total_sessions', 0):,}")
            st.metric("Total LLM Calls", f"{kpis.get('total_calls', 0):,}")
        
        with col2:
            st.metric("Total Cost", format_cost(kpis.get('total_cost', 0)))
            st.metric("Total Tokens", format_tokens(kpis.get('total_tokens', 0)))
        
        with col3:
            if routing_metrics.get('total_decisions', 0) > 0:
                st.metric("Routing Decisions", f"{routing_metrics['total_decisions']:,}")
                st.metric("Routing Savings", format_cost(routing_metrics.get('total_cost_savings', 0)))
            else:
                st.info("Enable routing to see savings")