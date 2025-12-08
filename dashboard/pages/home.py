"""
Home Page - Executive Dashboard
Location: dashboard/pages/home.py

Executive-level overview focused on:
- What requires attention NOW (alerts)
- Financial impact (cost + savings ROI)
- Quality and risk status
- Prioritized actions
"""

import streamlit as st
import os
from datetime import datetime
from typing import Dict, Any, List, Tuple

from observatory import Observatory
from observatory.models import ModelProvider

from dashboard.utils.data_fetcher import (
    get_project_overview,
    get_comparative_metrics,
    get_time_series_data,
    get_quality_analysis,
    get_llm_calls,
)
from dashboard.utils.formatters import (
    format_cost,
    format_latency,
    format_tokens,
    format_percentage,
    format_score,
    format_model_name,
)
from dashboard.components.metric_cards import (
    render_kpi_grid,
    render_status_indicator,
    render_empty_state,
)
from dashboard.components.charts import (
    create_cost_breakdown_pie,
    create_time_series_chart,
    create_bar_chart,
)
from dashboard.components.tables import render_quality_scores_table
from dashboard.components.filters import render_time_period_filter


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_total_savings(overview: Dict[str, Any]) -> Tuple[float, float, float]:
    """
    Calculate combined optimization savings.
    
    Returns:
        Tuple of (total_savings, routing_savings, cache_savings)
    """
    routing_savings = overview.get('routing_metrics', {}).get('total_savings', 0) or 0
    cache_savings = overview.get('cache_metrics', {}).get('cost_saved', 0) or 0
    return (routing_savings + cache_savings, routing_savings, cache_savings)


def detect_critical_alerts(overview: Dict[str, Any], trends: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """
    Detect only critical/warning alerts that require executive attention.
    Returns list of (severity, title, message) tuples.
    """
    alerts = []
    
    # HIGH PRIORITY: Hallucination rate > 5%
    quality_metrics = overview.get('quality_metrics', {})
    hallucination_rate = quality_metrics.get('hallucination_rate', 0)
    if hallucination_rate > 0.05:
        alerts.append(("error", "High Hallucination Rate", 
                      f"{format_percentage(hallucination_rate)} of responses flagged"))
    
    # HIGH PRIORITY: Success rate dropped below 90%
    kpis = overview.get('kpis', {})
    success_rate = kpis.get('success_rate', 1.0)
    if success_rate < 0.90:
        alerts.append(("error", "High Error Rate", 
                      f"{format_percentage(1 - success_rate)} of requests failing"))
    
    # MEDIUM: Cost spike > 50%
    cost_trend = trends.get('trends', {}).get('total_cost', {})
    if cost_trend.get('change_pct', 0) > 50:
        alerts.append(("warning", "Cost Spike", 
                      f"+{cost_trend['change_pct']:.0f}% vs previous period"))
    
    # MEDIUM: Latency spike > 30%
    latency_trend = trends.get('trends', {}).get('avg_latency_ms', {})
    if latency_trend.get('change_pct', 0) > 30:
        alerts.append(("warning", "Latency Degradation", 
                      f"+{latency_trend['change_pct']:.0f}% slower than previous period"))
    
    # MEDIUM: Cache performing poorly
    cache_metrics = overview.get('cache_metrics', {})
    hit_rate = cache_metrics.get('hit_rate', 0)
    if hit_rate < 0.15 and cache_metrics.get('total_requests', 0) > 20:
        alerts.append(("warning", "Cache Underperforming", 
                      f"Only {format_percentage(hit_rate)} hit rate"))
    
    # MEDIUM: Quality score dropped
    avg_score = quality_metrics.get('avg_judge_score')
    if avg_score and avg_score < 6.5:
        alerts.append(("warning", "Low Quality Score", 
                      f"Average score: {format_score(avg_score)}"))
    
    return alerts


def generate_prioritized_actions(overview: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate top prioritized actions with estimated $ impact.
    Returns list of action dicts with keys: priority, action, impact, effort
    """
    actions = []
    
    kpis = overview.get('kpis', {})
    cache_metrics = overview.get('cache_metrics', {})
    routing_metrics = overview.get('routing_metrics', {})
    quality_metrics = overview.get('quality_metrics', {})
    by_model = overview.get('by_model', {})
    
    total_cost = kpis.get('total_cost', 0)
    
    # Action 1: Cache optimization
    hit_rate = cache_metrics.get('hit_rate', 0)
    if hit_rate < 0.30 and cache_metrics.get('total_requests', 0) > 10:
        potential = total_cost * (0.30 - hit_rate)
        actions.append({
            "priority": "high" if potential > 1.0 else "medium",
            "action": "Improve cache hit rate to 30%",
            "impact": f"Save ~{format_cost(potential)}/period",
            "effort": "Low",
            "category": "cost"
        })
    
    # Action 2: Model routing optimization
    if by_model:
        expensive_model = max(by_model.items(), key=lambda x: x[1].get('total_cost', 0))
        model_name, model_data = expensive_model
        model_cost = model_data.get('total_cost', 0)
        if total_cost > 0 and model_cost / total_cost > 0.60:
            potential = model_cost * 0.3  # Assume 30% could be routed cheaper
            actions.append({
                "priority": "high",
                "action": f"Route simpler tasks away from {format_model_name(model_name)}",
                "impact": f"Save ~{format_cost(potential)}/period",
                "effort": "Medium",
                "category": "cost"
            })
    
    # Action 3: Quality improvement
    avg_score = quality_metrics.get('avg_judge_score')
    if avg_score and avg_score < 7.5:
        actions.append({
            "priority": "high" if avg_score < 6.5 else "medium",
            "action": "Review and improve low-scoring prompts",
            "impact": f"Improve quality from {format_score(avg_score)}",
            "effort": "Medium",
            "category": "quality"
        })
    
    # Action 4: Latency optimization
    avg_latency = kpis.get('avg_latency_ms', 0)
    if avg_latency > 3000:
        actions.append({
            "priority": "medium",
            "action": "Optimize high-latency operations",
            "impact": f"Reduce from {format_latency(avg_latency)}",
            "effort": "Medium",
            "category": "performance"
        })
    
    # Action 5: Error reduction
    success_rate = kpis.get('success_rate', 1.0)
    if success_rate < 0.95:
        error_cost = total_cost * (1 - success_rate)
        actions.append({
            "priority": "high" if success_rate < 0.90 else "medium",
            "action": "Investigate and fix error patterns",
            "impact": f"Recover ~{format_cost(error_cost)} in failed requests",
            "effort": "High",
            "category": "reliability"
        })
    
    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    actions.sort(key=lambda x: priority_order.get(x['priority'], 2))
    
    return actions[:5]


def generate_ai_insights(overview_data: Dict[str, Any]) -> str:
    """Generate AI-powered analysis of metrics."""
    import time
    from openai import OpenAI
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    kpis = overview_data.get('kpis', {})
    cache = overview_data.get('cache_metrics', {})
    quality = overview_data.get('quality_metrics', {})
    
    prompt = f"""You are an AI operations analyst. Analyze these metrics and provide 3 specific, actionable executive recommendations:

CURRENT METRICS:
- Total Spend: ${kpis.get('total_cost', 0):.2f}
- Total Requests: {kpis.get('total_calls', 0):,}
- Avg Cost/Request: ${kpis.get('total_cost', 0) / max(kpis.get('total_calls', 1), 1):.4f}
- Avg Latency: {kpis.get('avg_latency_ms', 0):.0f}ms
- Success Rate: {kpis.get('success_rate', 0):.1%}
- Cache Hit Rate: {cache.get('hit_rate', 0):.1%}
- Quality Score: {quality.get('avg_judge_score', 'N/A')}

Focus on:
1. Biggest cost optimization opportunity with $ estimate
2. Most critical quality/reliability risk
3. Quick win that can be implemented this week

Be specific with numbers. Format as 3 numbered recommendations, 2-3 sentences each."""

    start = time.time()
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.7
    )
    
    return response.choices[0].message.content


# =============================================================================
# MAIN RENDER FUNCTION
# =============================================================================

def render():
    """Render the executive home page."""
    
    # Header
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.title("📊 Executive Dashboard")
    with col2:
        time_period = render_time_period_filter(key="home_time_period", label="Period")
    with col3:
        if st.button("🔄 Refresh", width='stretch'):
            st.cache_data.clear()
            st.rerun()
    
    selected_project = st.session_state.get('selected_project')
    project_label = selected_project or "All Projects"
    st.caption(f"**{project_label}** • Updated {datetime.now().strftime('%I:%M %p')}")
    
    # Load data
    try:
        overview = get_project_overview(selected_project)
        trends = get_comparative_metrics(selected_project, period=time_period)
        
        if overview.get('kpis', {}).get('total_calls', 0) == 0:
            render_empty_state(
                message="No data available",
                icon="📊",
                suggestion="Start tracking by running AI agents with Observatory enabled"
            )
            return
            
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    # Extract common data
    kpis = overview.get('kpis', {})
    cache_metrics = overview.get('cache_metrics', {})
    routing_metrics = overview.get('routing_metrics', {})
    quality_metrics = overview.get('quality_metrics', {})
    trend_data = trends.get('trends', {})
    
    # Calculate headline savings
    total_savings, routing_savings, cache_savings = calculate_total_savings(overview)
    
    # ==========================================================================
    # TABS
    # ==========================================================================
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Summary", 
        "💰 Cost & Savings", 
        "⚠️ Quality & Risk", 
        "🎯 Actions"
    ])
    
    # ==========================================================================
    # TAB 1: SUMMARY
    # ==========================================================================
    with tab1:
        # Headline savings callout
        if total_savings > 0:
            st.success(f"💰 **You saved {format_cost(total_savings)} this period** through routing ({format_cost(routing_savings)}) and caching ({format_cost(cache_savings)})")
        
        # Critical Alerts (executives see these FIRST)
        alerts = detect_critical_alerts(overview, trends)
        
        if alerts:
            st.subheader("🚨 Requires Attention")
            cols = st.columns(min(len(alerts), 3))
            for i, (severity, title, message) in enumerate(alerts[:3]):
                with cols[i % 3]:
                    render_status_indicator(title, severity, message)
            
            if len(alerts) > 3:
                with st.expander(f"+{len(alerts) - 3} more alerts"):
                    for severity, title, message in alerts[3:]:
                        render_status_indicator(title, severity, message)
            st.divider()
        
        # KPIs
        st.subheader("Key Metrics")
        
        current = trends.get('current', {})
        previous = trends.get('previous', {})
        
        # Calculate trends
        avg_cost = current.get('total_cost', 0) / max(current.get('total_calls', 1), 1)
        prev_avg_cost = previous.get('total_cost', 0) / max(previous.get('total_calls', 1), 1)
        cost_change = ((avg_cost - prev_avg_cost) / prev_avg_cost * 100) if prev_avg_cost > 0 else 0
        
        latency_change = trend_data.get('avg_latency_ms', {}).get('change_pct', 0)
        
        metrics = [
            {
                "label": "Total Spend",
                "value": format_cost(kpis.get('total_cost', 0)),
                "delta": f"{trend_data.get('total_cost', {}).get('change_pct', 0):+.0f}%" if trend_data.get('total_cost', {}).get('change_pct') else None,
                "delta_color": "inverse"
            },
            {
                "label": "Total Savings",
                "value": format_cost(total_savings),
                "help": f"Routing: {format_cost(routing_savings)} | Cache: {format_cost(cache_savings)}"
            },
            {
                "label": "Avg Latency",
                "value": format_latency(kpis.get('avg_latency_ms', 0)),
                "delta": f"{latency_change:+.0f}%" if abs(latency_change) > 1 else None,
                "delta_color": "inverse"
            },
            {
                "label": "Success Rate",
                "value": format_percentage(kpis.get('success_rate', 0)),
            },
        ]
        
        # Add quality if available
        if quality_metrics.get('avg_judge_score'):
            metrics.append({
                "label": "Quality Score",
                "value": format_score(quality_metrics['avg_judge_score']),
            })
        
        render_kpi_grid(metrics, columns=min(len(metrics), 5))
        
        st.divider()
        
        # Activity trend
        st.subheader("Activity Trend")
        try:
            activity_data = get_time_series_data(selected_project, metric='count', interval='hour', hours=24)
            if activity_data:
                fig = create_time_series_chart(activity_data, metric_name="Requests", title="")
                st.plotly_chart(fig, width='stretch')
        except Exception:
            st.info("Activity data unavailable")
    
    # ==========================================================================
    # TAB 2: COST & SAVINGS
    # ==========================================================================
    with tab2:
        # ROI Summary
        st.subheader("Optimization ROI")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Spend", format_cost(kpis.get('total_cost', 0)))
        with col2:
            st.metric("Total Saved", format_cost(total_savings), 
                     help="Combined routing + cache savings")
        with col3:
            st.metric("Routing Savings", format_cost(routing_savings),
                     help=f"{routing_metrics.get('total_decisions', 0)} routing decisions")
        with col4:
            st.metric("Cache Savings", format_cost(cache_savings),
                     help=f"{format_percentage(cache_metrics.get('hit_rate', 0))} hit rate")
        
        # Net cost calculation
        net_cost = kpis.get('total_cost', 0) - total_savings
        if total_savings > 0:
            roi_pct = (total_savings / kpis.get('total_cost', 1)) * 100
            st.info(f"📈 **Net effective cost: {format_cost(net_cost)}** — Optimizations saved {roi_pct:.1f}% of spend")
        
        st.divider()
        
        # Cost breakdown
        st.subheader("Spend Breakdown")
        
        col1, col2 = st.columns(2)
        
        with col1:
            cost_breakdown = overview.get('cost_breakdown', {})
            if cost_breakdown:
                fig = create_cost_breakdown_pie(cost_breakdown, title="By Model")
                st.plotly_chart(fig, width='stretch')
            else:
                st.info("No model cost data")
        
        with col2:
            by_agent = overview.get('by_agent', {})
            if by_agent:
                agent_costs = {agent: data['total_cost'] for agent, data in by_agent.items()}
                fig = create_cost_breakdown_pie(agent_costs, title="By Agent")
                st.plotly_chart(fig, width='stretch')
            else:
                st.info("No agent cost data")
        
        st.divider()
        
        # Cost over time
        st.subheader("Spend Over Time")
        try:
            cost_data = get_time_series_data(selected_project, metric='cost', interval='hour', hours=24)
            if cost_data:
                fig = create_time_series_chart(cost_data, metric_name="Cost ($)", title="")
                st.plotly_chart(fig, width='stretch')
        except Exception:
            st.info("Cost trend unavailable")
    
    # ==========================================================================
    # TAB 3: QUALITY & RISK
    # ==========================================================================
    with tab3:
        # Quality overview
        st.subheader("Quality Status")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            score = quality_metrics.get('avg_judge_score')
            st.metric("Quality Score", format_score(score) if score else "N/A")
        with col2:
            st.metric("Success Rate", format_percentage(kpis.get('success_rate', 0)))
        with col3:
            st.metric("Hallucination Rate", 
                     format_percentage(quality_metrics.get('hallucination_rate', 0)))
        with col4:
            total_calls = kpis.get('total_calls', 0)
            errors = int(total_calls * (1 - kpis.get('success_rate', 1)))
            st.metric("Total Errors", f"{errors:,}")
        
        st.divider()
        
        # Risk indicators
        st.subheader("Risk Assessment")
        
        risks = []
        
        # Evaluate risks
        success_rate = kpis.get('success_rate', 1.0)
        if success_rate >= 0.98:
            risks.append(("healthy", "Error Rate", f"{format_percentage(1 - success_rate)}"))
        elif success_rate >= 0.95:
            risks.append(("warning", "Error Rate", f"{format_percentage(1 - success_rate)}"))
        else:
            risks.append(("error", "Error Rate", f"{format_percentage(1 - success_rate)} - needs attention"))
        
        hall_rate = quality_metrics.get('hallucination_rate', 0)
        if hall_rate <= 0.02:
            risks.append(("healthy", "Hallucinations", format_percentage(hall_rate)))
        elif hall_rate <= 0.05:
            risks.append(("warning", "Hallucinations", format_percentage(hall_rate)))
        else:
            risks.append(("error", "Hallucinations", f"{format_percentage(hall_rate)} - critical"))
        
        avg_score = quality_metrics.get('avg_judge_score')
        if avg_score:
            if avg_score >= 8.0:
                risks.append(("healthy", "Quality", format_score(avg_score)))
            elif avg_score >= 7.0:
                risks.append(("warning", "Quality", format_score(avg_score)))
            else:
                risks.append(("error", "Quality", f"{format_score(avg_score)} - below target"))
        
        cols = st.columns(len(risks))
        for i, (status, label, msg) in enumerate(risks):
            with cols[i]:
                render_status_indicator(label, status, msg)
        
        st.divider()
        
        # Worst performers
        st.subheader("Responses Needing Review")
        
        try:
            quality_analysis = get_quality_analysis(selected_project)
            worst = quality_analysis.get('worst_examples', [])
            
            if worst:
                render_quality_scores_table(worst[:5])
            else:
                st.info("No quality evaluations available. Enable LLM Judge to track quality.")
        except Exception as e:
            st.warning(f"Could not load quality data: {e}")
    
    # ==========================================================================
    # TAB 4: ACTIONS
    # ==========================================================================
    with tab4:
        st.subheader("Recommended Actions")
        
        actions = generate_prioritized_actions(overview)
        
        if actions:
            for i, action in enumerate(actions, 1):
                priority_emoji = "🔴" if action['priority'] == 'high' else "🟡" if action['priority'] == 'medium' else "🟢"
                
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"{priority_emoji} **{action['action']}**")
                    with col2:
                        st.caption(f"Impact: {action['impact']}")
                    with col3:
                        st.caption(f"Effort: {action['effort']}")
                st.divider()
        else:
            st.success("✅ No critical actions needed. System is performing well.")
        
        # AI Analysis
        st.subheader("🤖 AI Deep Analysis")
        st.markdown("Get AI-powered recommendations based on your current metrics.")
        
        if st.button("Run AI Analysis", type="primary"):
            with st.spinner("Analyzing with GPT-4o-mini..."):
                try:
                    insights = generate_ai_insights(overview)
                    st.markdown("### Recommendations")
                    st.success(insights)
                    st.caption("Analysis cost: ~$0.001")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    if "OPENAI_API_KEY" in str(e):
                        st.info("Set OPENAI_API_KEY to enable AI analysis")