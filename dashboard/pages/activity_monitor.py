"""
Activity Monitor - Real-Time System Status
Location: dashboard/pages/activity_monitor.py

Executive-focused real-time monitoring:
- System health at a glance
- Current throughput and cost burn
- Anomaly detection
- Activity log (collapsed for debugging)
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
import time

from dashboard.utils.data_fetcher import (
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
# HELPER FUNCTIONS
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
            'total_errors': 0,
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
    
    # Calculate rates
    time_span_min = max(window_minutes, 1)
    
    return {
        'requests_per_min': total / time_span_min,
        'cost_per_hour': (total_cost / time_span_min) * 60,
        'avg_latency_ms': total_latency / max(total, 1),
        'error_rate': errors / max(total, 1),
        'total_requests': total,
        'total_errors': errors,
    }


def determine_system_health(metrics: Dict[str, Any]) -> Tuple[str, str, str]:
    """
    Determine overall system health status.
    
    Returns:
        Tuple of (status, icon, message)
        status: "healthy", "degraded", "critical"
    """
    error_rate = metrics.get('error_rate', 0)
    avg_latency = metrics.get('avg_latency_ms', 0)
    
    issues = []
    
    # Check error rate
    if error_rate > 0.10:
        return ("critical", "🔴", f"High error rate: {format_percentage(error_rate)}")
    elif error_rate > 0.05:
        issues.append(f"Elevated errors: {format_percentage(error_rate)}")
    
    # Check latency
    if avg_latency > 10000:
        return ("critical", "🔴", f"Severe latency: {format_latency(avg_latency)}")
    elif avg_latency > 5000:
        issues.append(f"High latency: {format_latency(avg_latency)}")
    
    # Check if no activity
    if metrics.get('total_requests', 0) == 0:
        return ("degraded", "🟡", "No recent activity detected")
    
    if issues:
        return ("degraded", "🟡", " • ".join(issues))
    
    return ("healthy", "🟢", "All systems operational")


def detect_anomalies(calls: List[Dict], window_minutes: int = 5) -> List[Dict[str, Any]]:
    """Detect anomalies in recent activity."""
    anomalies = []
    
    if not calls:
        return anomalies
    
    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
    recent = [c for c in calls if c.get('timestamp') and c['timestamp'] >= cutoff]
    
    if len(recent) < 3:
        return anomalies
    
    # Check for latency spikes
    latencies = [c.get('latency_ms', 0) for c in recent]
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    
    if max_latency > avg_latency * 3 and max_latency > 5000:
        anomalies.append({
            "type": "warning",
            "title": "Latency Spike",
            "message": f"Max {format_latency(max_latency)} vs avg {format_latency(avg_latency)}"
        })
    
    # Check for error burst
    errors = [c for c in recent if not c.get('success', True)]
    if len(errors) >= 3:
        anomalies.append({
            "type": "error",
            "title": "Error Burst",
            "message": f"{len(errors)} errors in last {window_minutes} minutes"
        })
    
    # Check for cost spike (single expensive call)
    costs = [c.get('total_cost', 0) for c in recent]
    avg_cost = sum(costs) / len(costs)
    max_cost = max(costs)
    
    if max_cost > avg_cost * 5 and max_cost > 0.01:
        anomalies.append({
            "type": "warning",
            "title": "Expensive Request",
            "message": f"Single request cost {format_cost(max_cost)}"
        })
    
    return anomalies


def render_activity_log(calls: List[Dict], limit: int = 20):
    """Render compact activity log table."""
    if not calls:
        st.info("No recent activity")
        return
    
    # Build compact table data
    import pandas as pd
    
    table_data = []
    for call in calls[:limit]:
        timestamp = call.get('timestamp')
        time_str = timestamp.strftime("%H:%M:%S") if timestamp else "—"
        
        status = "✅" if call.get('success', True) else "❌"
        cache = "💾" if (call.get('cache_metadata') or {}).get('cache_hit') else ""
        
        table_data.append({
            "Time": time_str,
            "Agent": call.get('agent_name', 'Unknown')[:15],
            "Model": format_model_name(call.get('model_name', ''))[:12],
            "Latency": format_latency(call.get('latency_ms', 0)),
            "Cost": format_cost(call.get('total_cost', 0)),
            "": f"{status}{cache}"
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, width='stretch', hide_index=True)


def render_request_detail(call: Dict):
    """Render expandable request details."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Request Info**")
        st.write(f"ID: `{truncate_text(call.get('id', ''), 20)}`")
        st.write(f"Agent: {call.get('agent_name', 'Unknown')}")
        st.write(f"Model: {call.get('model_name', 'Unknown')}")
        st.write(f"Operation: {call.get('operation', 'N/A')}")
    
    with col2:
        st.markdown("**Metrics**")
        st.write(f"Latency: {format_latency(call.get('latency_ms', 0))}")
        st.write(f"Cost: {format_cost(call.get('total_cost', 0))}")
        st.write(f"Tokens: {format_tokens(call.get('total_tokens', 0))}")
        st.write(f"Status: {'✅ Success' if call.get('success', True) else '❌ Failed'}")
    
    # Prompt/Response (truncated)
    if call.get('prompt'):
        with st.expander("View Prompt"):
            st.code(truncate_text(call['prompt'], 500), language="text")
    
    if call.get('response_text'):
        with st.expander("View Response"):
            st.code(truncate_text(call['response_text'], 500), language="text")
    
    if call.get('error'):
        st.error(f"Error: {call['error']}")


# =============================================================================
# MAIN RENDER FUNCTION
# =============================================================================

def render():
    """Render the Activity Monitor page."""
    
    # Header
    st.title("📡 Activity Monitor")
    
    selected_project = st.session_state.get('selected_project')
    
    # Simple controls
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        auto_refresh = st.checkbox("Auto-refresh", value=True, key="monitor_refresh")
    with col2:
        refresh_rate = st.selectbox(
            "Interval",
            options=[5, 10, 30],
            format_func=lambda x: f"{x}s",
            index=0,
            key="monitor_rate",
            label_visibility="collapsed"
        )
    with col3:
        if st.button("🔄 Refresh Now", width='stretch'):
            st.cache_data.clear()
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
            
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    # Calculate metrics
    metrics = calculate_live_metrics(calls, window_minutes=5)
    health_status, health_icon, health_message = determine_system_health(metrics)
    
    # =========================================================================
    # SECTION 1: System Health Banner
    # =========================================================================
    if health_status == "healthy":
        st.success(f"{health_icon} **System Healthy** — {health_message}")
    elif health_status == "degraded":
        st.warning(f"{health_icon} **Degraded** — {health_message}")
    else:
        st.error(f"{health_icon} **Critical** — {health_message}")
    
    # =========================================================================
    # SECTION 2: Anomaly Alerts (only if issues detected)
    # =========================================================================
    anomalies = detect_anomalies(calls, window_minutes=5)
    
    if anomalies:
        st.subheader("⚠️ Anomalies Detected")
        cols = st.columns(min(len(anomalies), 3))
        for i, anomaly in enumerate(anomalies[:3]):
            with cols[i]:
                if anomaly['type'] == 'error':
                    st.error(f"**{anomaly['title']}**\n\n{anomaly['message']}")
                else:
                    st.warning(f"**{anomaly['title']}**\n\n{anomaly['message']}")
        st.divider()
    
    # =========================================================================
    # SECTION 3: Core Metrics (4 only)
    # =========================================================================
    st.subheader("Current Status")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Throughput",
            f"{metrics['requests_per_min']:.1f}/min",
            help="Requests per minute (last 5 min)"
        )
    
    with col2:
        st.metric(
            "Cost Burn",
            f"{format_cost(metrics['cost_per_hour'])}/hr",
            help="Projected hourly cost at current rate"
        )
    
    with col3:
        st.metric(
            "Avg Latency",
            format_latency(metrics['avg_latency_ms']),
            help="Average response time"
        )
    
    with col4:
        error_pct = metrics['error_rate'] * 100
        st.metric(
            "Error Rate",
            f"{error_pct:.1f}%",
            help=f"{metrics['total_errors']} errors / {metrics['total_requests']} requests"
        )
    
    st.divider()
    
    # =========================================================================
    # SECTION 4: Activity Trend Chart
    # =========================================================================
    st.subheader("Activity (Last Hour)")
    
    try:
        activity_data = get_time_series_data(
            selected_project,
            metric='count',
            interval='minute',
            hours=1
        )
        
        if activity_data:
            fig = create_time_series_chart(
                activity_data,
                metric_name="Requests",
                title=""
            )
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Insufficient data for activity chart")
    except Exception:
        st.info("Activity chart unavailable")
    
    st.divider()
    
    # =========================================================================
    # SECTION 5: Activity Log (Collapsed)
    # =========================================================================
    with st.expander(f"📋 Activity Log ({len(calls)} recent requests)", expanded=False):
        
        # Quick filters
        col1, col2 = st.columns(2)
        with col1:
            show_errors = st.checkbox("Errors only", key="log_errors")
        with col2:
            log_limit = st.selectbox(
                "Show",
                options=[10, 25, 50],
                index=0,
                key="log_limit"
            )
        
        # Filter
        filtered_calls = calls
        if show_errors:
            filtered_calls = [c for c in calls if not c.get('success', True)]
        
        if filtered_calls:
            render_activity_log(filtered_calls, limit=log_limit)
            
            # Expandable details for individual requests
            st.markdown("---")
            st.markdown("**Request Details**")
            
            request_options = [
                f"{i+1}. {c.get('agent_name', 'Unknown')[:10]} @ {c.get('timestamp').strftime('%H:%M:%S') if c.get('timestamp') else '—'}"
                for i, c in enumerate(filtered_calls[:log_limit])
            ]
            
            if request_options:
                selected_idx = st.selectbox(
                    "Select request to inspect",
                    options=range(len(request_options)),
                    format_func=lambda i: request_options[i],
                    key="request_selector"
                )
                
                if selected_idx is not None:
                    render_request_detail(filtered_calls[selected_idx])
        else:
            st.info("No matching requests")
    
    # =========================================================================
    # Auto-refresh
    # =========================================================================
    if auto_refresh:
        st.caption(f"Auto-refreshing every {refresh_rate}s...")
        time.sleep(refresh_rate)
        st.rerun()