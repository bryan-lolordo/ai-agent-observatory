"""
Live Demo Page - Real-Time Monitoring
Location: dashboard/pages/live_demo.py

Real-time dashboard showing live agent activity, costs, and performance.
Auto-refreshes to show the latest LLM calls and system activity.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import time

from dashboard.utils.data_fetcher import (
    get_project_overview,
    get_llm_calls,
    get_available_agents,
    get_available_models,
)
from dashboard.utils.formatters import (
    format_cost,
    format_latency,
    format_tokens,
    format_percentage,
    format_model_name,
    truncate_text,
)
from dashboard.components.metric_cards import (
    render_metric_row,
    render_empty_state,
)
from dashboard.components.charts import (
    create_cost_breakdown_pie,
    create_bar_chart,
)
from dashboard.components.filters import (
    render_checkbox_filter,
    render_radio_filter,
)


def calculate_live_kpis(calls: List[Dict], time_window_minutes: int = 1) -> Dict[str, Any]:
    """Calculate real-time KPIs from recent calls."""
    if not calls:
        return {
            'requests_per_minute': 0,
            'avg_latency_ms': 0,
            'avg_cost_per_request': 0,
            'total_tokens': 0,
            'active_agents': 0,
            'cache_hit_rate': 0
        }
    
    # Filter to time window
    cutoff = datetime.utcnow() - timedelta(minutes=time_window_minutes)
    recent_calls = [
        c for c in calls 
        if c.get('timestamp') and c['timestamp'] >= cutoff
    ]
    
    if not recent_calls:
        recent_calls = calls  # Fallback to all calls
    
    # Calculate metrics
    total_calls = len(recent_calls)
    total_cost = sum(c.get('total_cost', 0) for c in recent_calls)
    total_latency = sum(c.get('latency_ms', 0) for c in recent_calls)
    total_tokens = sum(c.get('total_tokens', 0) for c in recent_calls)
    
    # Cache hits
    cache_hits = sum(
        1 for c in recent_calls 
        if c.get('cache_metadata', {}).get('cache_hit', False)
    )
    
    # Active agents
    active_agents = len(set(c.get('agent_name') for c in recent_calls if c.get('agent_name')))
    
    return {
        'requests_per_minute': total_calls / max(time_window_minutes, 1),
        'avg_latency_ms': total_latency / max(total_calls, 1),
        'avg_cost_per_request': total_cost / max(total_calls, 1),
        'total_tokens': total_tokens,
        'active_agents': active_agents,
        'cache_hit_rate': cache_hits / max(total_calls, 1) if total_calls > 0 else 0
    }


def calculate_hourly_rate(calls: List[Dict]) -> Dict[str, Any]:
    """Calculate projected hourly rates based on recent activity."""
    if not calls:
        return {'cost_per_hour': 0, 'tokens_per_hour': 0, 'requests_per_hour': 0}
    
    # Get calls from last hour
    cutoff = datetime.utcnow() - timedelta(hours=1)
    recent_calls = [
        c for c in calls 
        if c.get('timestamp') and c['timestamp'] >= cutoff
    ]
    
    if not recent_calls:
        return {'cost_per_hour': 0, 'tokens_per_hour': 0, 'requests_per_hour': 0}
    
    # Calculate actual time span
    timestamps = [c['timestamp'] for c in recent_calls if c.get('timestamp')]
    if not timestamps:
        return {'cost_per_hour': 0, 'tokens_per_hour': 0, 'requests_per_hour': 0}
    
    time_span_hours = (max(timestamps) - min(timestamps)).total_seconds() / 3600
    if time_span_hours == 0:
        time_span_hours = 1  # Assume 1 hour if all calls at same time
    
    total_cost = sum(c.get('total_cost', 0) for c in recent_calls)
    total_tokens = sum(c.get('total_tokens', 0) for c in recent_calls)
    
    return {
        'cost_per_hour': total_cost / time_span_hours,
        'tokens_per_hour': int(total_tokens / time_span_hours),
        'requests_per_hour': int(len(recent_calls) / time_span_hours)
    }


def render_event_stream(calls: List[Dict], limit: int = 20):
    """Render live event stream of LLM calls."""
    if not calls:
        st.info("🕐 No recent activity. Waiting for requests...")
        return
    
    st.subheader(f"📡 Live Event Stream (Last {limit})")
    
    # Create event table
    events = []
    for call in calls[:limit]:
        timestamp = call.get('timestamp')
        time_str = timestamp.strftime("%H:%M:%S") if timestamp else "N/A"
        
        agent = call.get('agent_name', 'Unknown')
        model = format_model_name(call.get('model_name', ''))
        latency = format_latency(call.get('latency_ms', 0))
        cost = format_cost(call.get('total_cost', 0))
        tokens = format_tokens(call.get('total_tokens', 0))
        
        # Cache status
        cache_hit = call.get('cache_metadata', {}).get('cache_hit', False)
        cache_icon = "✅ HIT" if cache_hit else "❌ MISS"
        
        # Success status
        success = call.get('success', True)
        status_icon = "✅" if success else "🔴"
        
        # Build event string
        event_str = f"`{time_str}` | **{agent}** → {model} | {latency} | {cost} | {tokens} | {cache_icon} {status_icon}"
        
        events.append({
            'event': event_str,
            'call': call
        })
    
    # Display events
    for i, event in enumerate(events):
        with st.container():
            st.markdown(event['event'])
            
            # Expandable details
            with st.expander(f"🔍 View Request Details #{i+1}"):
                call = event['call']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Basic Info**")
                    st.write(f"**ID:** `{truncate_text(call.get('id', ''), 20)}`")
                    st.write(f"**Agent:** {call.get('agent_name', 'Unknown')}")
                    st.write(f"**Model:** {call.get('model_name', 'Unknown')}")
                    st.write(f"**Operation:** {call.get('operation', 'N/A')}")
                    
                    st.write("**Metrics**")
                    st.write(f"**Latency:** {format_latency(call.get('latency_ms', 0))}")
                    st.write(f"**Cost:** {format_cost(call.get('total_cost', 0))}")
                    st.write(f"**Tokens:** {format_tokens(call.get('total_tokens', 0))}")
                
                with col2:
                    st.write("**Routing**")
                    routing = call.get('routing_decision', {})
                    if routing and isinstance(routing, dict):
                        st.write(f"**Chosen:** {routing.get('chosen_model', 'N/A')}")
                        alternatives = routing.get('alternative_models', [])
                        if alternatives:
                            st.write(f"**Alternatives:** {', '.join(alternatives[:2])}")
                        st.write(f"**Reasoning:** {truncate_text(routing.get('reasoning', 'N/A'), 50)}")
                    else:
                        st.write("No routing data")
                    
                    st.write("**Cache**")
                    cache = call.get('cache_metadata', {})
                    if cache and isinstance(cache, dict):
                        st.write(f"**Hit:** {'✅ Yes' if cache.get('cache_hit') else '❌ No'}")
                        if cache.get('cache_key'):
                            st.write(f"**Key:** `{truncate_text(cache.get('cache_key', ''), 20)}`")
                    else:
                        st.write("No cache data")
                
                # Prompt and response
                if call.get('prompt'):
                    st.write("**Prompt**")
                    st.code(truncate_text(call['prompt'], 200), language="text")
                
                if call.get('response_text'):
                    st.write("**Response**")
                    st.code(truncate_text(call['response_text'], 200), language="text")
            
            st.divider()


def render_agent_activity(calls: List[Dict]):
    """Render agent activity breakdown."""
    if not calls:
        return
    
    st.subheader("👥 Agent Activity")
    
    # Aggregate by agent
    agent_stats = {}
    for call in calls:
        agent = call.get('agent_name', 'Unknown')
        if agent not in agent_stats:
            agent_stats[agent] = {
                'calls': 0,
                'cost': 0,
                'tokens': 0,
                'avg_latency': []
            }
        
        agent_stats[agent]['calls'] += 1
        agent_stats[agent]['cost'] += call.get('total_cost', 0)
        agent_stats[agent]['tokens'] += call.get('total_tokens', 0)
        agent_stats[agent]['avg_latency'].append(call.get('latency_ms', 0))
    
    # Create table
    table_data = []
    for agent, stats in agent_stats.items():
        avg_latency = sum(stats['avg_latency']) / len(stats['avg_latency']) if stats['avg_latency'] else 0
        
        table_data.append({
            'Agent': agent,
            'Calls': stats['calls'],
            'Cost': format_cost(stats['cost']),
            'Tokens': format_tokens(stats['tokens']),
            'Avg Latency': format_latency(avg_latency)
        })
    
    # Sort by calls
    table_data.sort(key=lambda x: x['Calls'], reverse=True)
    
    # Display as columns with metrics
    for data in table_data[:5]:  # Top 5 agents
        with st.container():
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Agent", data['Agent'])
            with col2:
                st.metric("Calls", data['Calls'])
            with col3:
                st.metric("Cost", data['Cost'])
            with col4:
                st.metric("Avg Latency", data['Avg Latency'])


def render_request_timeline(call: Dict):
    """Render detailed timeline of a single request."""
    st.subheader("⏱️ Last Request Timeline")
    
    if not call:
        st.info("No requests yet")
        return
    
    timestamp = call.get('timestamp')
    if timestamp:
        st.write(f"**Request Time:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Build timeline
    latency_ms = call.get('latency_ms', 0)
    
    st.write("**Timeline:**")
    st.markdown(f"""
    ```
    0ms      → Request received
    10ms     → Agent started: {call.get('agent_name', 'Unknown')}
    20ms     → Model selected: {call.get('model_name', 'Unknown')}
    30ms     → LLM call initiated
    {int(latency_ms - 10)}ms     → LLM response received
    {int(latency_ms)}ms     → Response processed
    
    Total: {format_latency(latency_ms)}
    Cost: {format_cost(call.get('total_cost', 0))}
    Tokens: {format_tokens(call.get('total_tokens', 0))}
    ```
    """)
    
    # Show routing decision if available
    routing = call.get('routing_decision', {})
    if routing and isinstance(routing, dict):
        st.write("**Routing Decision:**")
        st.info(f"✓ Chose {routing.get('chosen_model', 'N/A')}: {routing.get('reasoning', 'No reasoning provided')}")


def render():
    """Render the Live Demo page."""
    
    # Page header
    st.title("🎥 Live Demo - Real-Time Monitoring")
    
    # Get selected project
    selected_project = st.session_state.get('selected_project')
    
    # Controls row
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        auto_refresh = st.checkbox("🔄 Auto-refresh", value=True, key="live_demo_refresh")
    
    with col2:
        refresh_rate = st.selectbox(
            "Refresh Rate",
            options=[2, 5, 10, 30],
            format_func=lambda x: f"{x}s",
            index=1,
            key="live_demo_rate"
        )
    
    with col3:
        limit = st.selectbox(
            "Show Events",
            options=[10, 20, 50, 100],
            index=1,
            key="live_demo_limit"
        )
    
    with col4:
        time_window = st.selectbox(
            "KPI Window",
            options=[1, 5, 15, 60],
            format_func=lambda x: f"{x}m",
            index=0,
            key="live_demo_window"
        )
    
    st.divider()
    
    # Filters
    with st.expander("🔍 Filters", expanded=False):
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            # Get available agents
            try:
                available_agents = get_available_agents(selected_project)
                filter_agent = st.selectbox(
                    "Agent",
                    options=["All"] + available_agents,
                    key="live_demo_agent_filter"
                )
            except:
                filter_agent = "All"
        
        with filter_col2:
            # Get available models
            try:
                available_models = get_available_models(selected_project)
                filter_model = st.selectbox(
                    "Model",
                    options=["All"] + available_models,
                    key="live_demo_model_filter"
                )
            except:
                filter_model = "All"
        
        with filter_col3:
            show_errors_only = st.checkbox("Show errors only", key="live_demo_errors")
    
    # Fetch recent calls
    try:
        with st.spinner("Loading live data..."):
            calls = get_llm_calls(
                project_name=selected_project,
                agent_name=None if filter_agent == "All" else filter_agent,
                model_name=None if filter_model == "All" else filter_model,
                limit=limit
            )
            
            # Filter by errors if requested
            if show_errors_only:
                calls = [c for c in calls if not c.get('success', True)]
            
            # Check if we have data
            if not calls:
                render_empty_state(
                    message="No live activity detected",
                    icon="🕐",
                    suggestion="Run your AI agents with Observatory enabled to see real-time monitoring"
                )
                return
    
    except Exception as e:
        st.error(f"Error loading live data: {str(e)}")
        return
    
    # Calculate KPIs
    kpis = calculate_live_kpis(calls, time_window)
    hourly_rate = calculate_hourly_rate(calls)
    
    # Section 1: At-a-Glance KPIs
    st.subheader(f"📊 Live Metrics (Last {time_window}m)")
    
    metrics = [
        {
            "label": "Requests/Min",
            "value": f"{kpis['requests_per_minute']:.1f}",
            "help_text": f"≈ {hourly_rate['requests_per_hour']}/hour"
        },
        {
            "label": "Avg Latency",
            "value": format_latency(kpis['avg_latency_ms']),
        },
        {
            "label": "Avg Cost/Req",
            "value": format_cost(kpis['avg_cost_per_request']),
            "help_text": f"≈ {format_cost(hourly_rate['cost_per_hour'])}/hour"
        },
        {
            "label": "Total Tokens",
            "value": format_tokens(kpis['total_tokens']),
            "help_text": f"≈ {format_tokens(hourly_rate['tokens_per_hour'])}/hour"
        },
        {
            "label": "Active Agents",
            "value": str(kpis['active_agents']),
        },
        {
            "label": "Cache Hit Rate",
            "value": format_percentage(kpis['cache_hit_rate']),
        }
    ]
    
    render_metric_row(metrics, columns=3)
    
    st.divider()
    
    # Section 2: Cumulative Stats
    st.subheader("📈 Cumulative Stats")
    
    total_cost = sum(c.get('total_cost', 0) for c in calls)
    total_tokens = sum(c.get('total_tokens', 0) for c in calls)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Requests", len(calls))
    with col2:
        st.metric("Total Cost", format_cost(total_cost))
    with col3:
        st.metric("Total Tokens", format_tokens(total_tokens))
    
    st.divider()
    
    # Section 3: Live Event Stream
    render_event_stream(calls, limit)
    
    st.divider()
    
    # Section 4: Agent Activity & Model Distribution
    col1, col2 = st.columns(2)
    
    with col1:
        render_agent_activity(calls)
    
    with col2:
        st.subheader("🤖 Model Distribution")
        
        # Aggregate by model
        model_counts = {}
        for call in calls:
            model = call.get('model_name', 'Unknown')
            model_counts[model] = model_counts.get(model, 0) + 1
        
        if model_counts:
            fig = create_cost_breakdown_pie(
                model_counts,
                title="Requests by Model"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No model data")
    
    st.divider()
    
    # Section 5: Last Request Timeline
    if calls:
        render_request_timeline(calls[0])
    
    # Auto-refresh logic
    if auto_refresh:
        st.caption(f"🔄 Auto-refreshing every {refresh_rate}s...")
        time.sleep(refresh_rate)
        st.rerun()