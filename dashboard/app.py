import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from observatory import Storage
from observatory.models import ModelProvider


st.set_page_config(
    page_title="AI Agent Observatory",
    page_icon="🔭",
    layout="wide",
)


@st.cache_resource
def get_storage():
    return Storage()


def main():
    st.title("🔭 AI Agent Observatory")
    st.markdown("Monitor, evaluate, and optimize your AI agents")
    
    storage = get_storage()
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Project filter
    projects = ["All Projects"]  # TODO: Get from DB
    selected_project = st.sidebar.selectbox("Project", projects)
    
    # Time range filter
    time_range = st.sidebar.selectbox(
        "Time Range",
        ["Last Hour", "Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time"]
    )
    
    # Convert time range to datetime
    now = datetime.utcnow()
    time_filters = {
        "Last Hour": now - timedelta(hours=1),
        "Last 24 Hours": now - timedelta(days=1),
        "Last 7 Days": now - timedelta(days=7),
        "Last 30 Days": now - timedelta(days=30),
        "All Time": None,
    }
    start_time = time_filters[time_range]
    
    # Load sessions
    project_filter = None if selected_project == "All Projects" else selected_project
    sessions = storage.get_sessions(
        project_name=project_filter,
        start_time=start_time,
        limit=1000,
    )
    
    if not sessions:
        st.warning("No data available for the selected filters.")
        return
    
    # Overview metrics
    st.header("📊 Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    total_cost = sum(s.total_cost for s in sessions)
    total_calls = sum(s.total_llm_calls for s in sessions)
    avg_latency = sum(s.total_latency_ms for s in sessions) / len(sessions) if sessions else 0
    success_count = sum(1 for s in sessions if s.success)
    success_rate = success_count / len(sessions) if sessions else 0
    
    col1.metric("Total Cost", f"${total_cost:.2f}")
    col2.metric("LLM Calls", f"{total_calls:,}")
    col3.metric("Avg Latency", f"{avg_latency:.0f}ms")
    col4.metric("Success Rate", f"{success_rate:.1%}")
    
    # Cost over time
    st.header("💰 Cost Analysis")
    
    df_sessions = pd.DataFrame([
        {
            "timestamp": s.start_time,
            "cost": s.total_cost,
            "project": s.project_name,
            "operation": s.operation_type or "Unknown",
        }
        for s in sessions
    ])
    
    if not df_sessions.empty:
        fig_cost = px.line(
            df_sessions.sort_values("timestamp"),
            x="timestamp",
            y="cost",
            title="Cost Over Time",
            labels={"cost": "Cost ($)", "timestamp": "Time"},
        )
        st.plotly_chart(fig_cost, use_container_width=True)
        
        # Cost by operation
        col1, col2 = st.columns(2)
        
        with col1:
            cost_by_operation = df_sessions.groupby("operation")["cost"].sum().sort_values(ascending=False)
            fig_pie = px.pie(
                values=cost_by_operation.values,
                names=cost_by_operation.index,
                title="Cost by Operation",
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            cost_by_project = df_sessions.groupby("project")["cost"].sum().sort_values(ascending=False)
            fig_bar = px.bar(
                x=cost_by_project.index,
                y=cost_by_project.values,
                title="Cost by Project",
                labels={"x": "Project", "y": "Cost ($)"},
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    
    # Recent sessions table
    st.header("📋 Recent Sessions")
    
    df_table = pd.DataFrame([
        {
            "Time": s.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "Project": s.project_name,
            "Operation": s.operation_type or "N/A",
            "Calls": s.total_llm_calls,
            "Cost": f"${s.total_cost:.4f}",
            "Latency": f"{s.total_latency_ms:.0f}ms",
            "Status": "✅ Success" if s.success else "❌ Failed",
        }
        for s in sessions[:50]
    ])
    
    st.dataframe(df_table, use_container_width=True)


if __name__ == "__main__":
    main()