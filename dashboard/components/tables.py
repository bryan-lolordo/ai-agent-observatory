"""
Table Components
Location: dashboard/components/tables.py

Reusable data table components for displaying structured data.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional
from dashboard.utils.formatters import (
    format_cost,
    format_latency,
    format_tokens,
    format_percentage,
    format_model_name,
    truncate_text
)


def render_dataframe(
    df: pd.DataFrame,
    width: str = 'stretch',  # Changed from use_container_width
    hide_index: bool = True,
    height: Optional[int] = None
):
    """
    Render a styled dataframe.
    
    Args:
        df: DataFrame to display
        width: Width behavior - 'stretch' (full width) or 'content' (fit content)
        hide_index: Hide row indices
        height: Optional fixed height
    """
    if df.empty:
        st.info("No data to display")
        return
    
    # Build kwargs, only include height if provided
    kwargs = {
        "width": width,  # Changed from use_container_width
        "hide_index": hide_index
    }
    if height is not None:
        kwargs["height"] = height
    
    st.dataframe(df, **kwargs)


def render_sessions_table(sessions: List[Dict[str, Any]]):
    """
    Render a table of session summaries.
    
    Args:
        sessions: List of session dictionaries with keys:
                  - id, project_name, start_time, total_cost, total_tokens,
                    total_llm_calls, total_latency_ms, success
    """
    if not sessions:
        st.info("No sessions to display")
        return
    
    # Format data for display
    table_data = []
    for session in sessions:
        table_data.append({
            "ID": truncate_text(session.get("id", ""), 10),
            "Project": session.get("project_name", "Unknown"),
            "Time": session.get("start_time", "").strftime("%Y-%m-%d %H:%M") if session.get("start_time") else "",
            "Calls": session.get("total_llm_calls", 0),
            "Cost": format_cost(session.get("total_cost", 0.0)),
            "Tokens": format_tokens(session.get("total_tokens", 0)),
            "Avg Latency": format_latency(
                session.get("total_latency_ms", 0) / max(session.get("total_llm_calls", 1), 1)
            ),
            "Status": "✅" if session.get("success", True) else "❌"
        })
    
    df = pd.DataFrame(table_data)
    render_dataframe(df)


def render_llm_calls_table(calls: List[Dict[str, Any]], include_prompts: bool = False):
    """
    Render a table of LLM call details.
    
    Args:
        calls: List of LLM call dictionaries
        include_prompts: Whether to include prompt/response text
    """
    if not calls:
        st.info("No LLM calls to display")
        return
    
    # Format data for display
    table_data = []
    for call in calls:
        row = {
            "Time": call.get("timestamp", "").strftime("%H:%M:%S") if call.get("timestamp") else "",
            "Agent": call.get("agent_name", "Unknown"),
            "Model": format_model_name(call.get("model_name", "")),
            "Tokens": format_tokens(call.get("total_tokens", 0)),
            "Cost": format_cost(call.get("total_cost", 0.0)),
            "Latency": format_latency(call.get("latency_ms", 0)),
            "Cache": "✅" if call.get("cache_metadata", {}).get("cache_hit") else "❌",
            "Status": "✅" if call.get("success", True) else "❌"
        }
        
        if include_prompts:
            row["Prompt"] = truncate_text(call.get("prompt", ""), 50)
            row["Response"] = truncate_text(call.get("response_text", ""), 50)
        
        table_data.append(row)
    
    df = pd.DataFrame(table_data)
    render_dataframe(df, height=400)


def render_model_comparison_table(model_data: Dict[str, Dict[str, Any]]):
    """
    Render a comparison table of model performance.
    
    Args:
        model_data: Dictionary mapping model_name to metrics dict
                    {model: {count, total_cost, avg_cost, avg_tokens, avg_latency_ms}}
    """
    if not model_data:
        st.info("No model data to display")
        return
    
    # Format data for display
    table_data = []
    for model, metrics in model_data.items():
        table_data.append({
            "Model": format_model_name(model),
            "Calls": f"{metrics.get('count', 0):,}",
            "Total Cost": format_cost(metrics.get('total_cost', 0.0)),
            "Avg Cost": format_cost(metrics.get('avg_cost', 0.0)),
            "Avg Tokens": format_tokens(int(metrics.get('avg_tokens', 0))),
            "Avg Latency": format_latency(metrics.get('avg_latency_ms', 0)),
            "P95 Latency": format_latency(metrics.get('p95_latency_ms', 0))
        })
    
    df = pd.DataFrame(table_data)
    # Sort by total cost descending
    df = df.sort_values("Total Cost", ascending=False)
    render_dataframe(df)


def render_agent_comparison_table(agent_data: Dict[str, Dict[str, Any]]):
    """
    Render a comparison table of agent performance.
    
    Args:
        agent_data: Dictionary mapping agent_name to metrics dict
    """
    if not agent_data:
        st.info("No agent data to display")
        return
    
    # Format data for display
    table_data = []
    for agent, metrics in agent_data.items():
        models_used = ", ".join(
            format_model_name(m) for m in metrics.get('models_used', [])[:3]
        )
        if len(metrics.get('models_used', [])) > 3:
            models_used += "..."
        
        table_data.append({
            "Agent": agent,
            "Calls": f"{metrics.get('count', 0):,}",
            "Total Cost": format_cost(metrics.get('total_cost', 0.0)),
            "Avg Cost": format_cost(metrics.get('avg_cost', 0.0)),
            "Total Tokens": format_tokens(metrics.get('total_tokens', 0)),
            "Avg Latency": format_latency(metrics.get('avg_latency_ms', 0)),
            "Models Used": models_used
        })
    
    df = pd.DataFrame(table_data)
    # Sort by total cost descending
    df = df.sort_values("Total Cost", ascending=False)
    render_dataframe(df)


def render_routing_decisions_table(decisions: List[Dict[str, Any]]):
    """
    Render a table of routing decisions.
    
    Args:
        decisions: List of routing decision dictionaries
    """
    if not decisions:
        st.info("No routing decisions to display")
        return
    
    # Format data for display
    table_data = []
    for decision in decisions:
        alternatives = ", ".join(
            format_model_name(m) for m in decision.get('alternatives', [])[:2]
        )
        
        table_data.append({
            "Time": decision.get("timestamp", "").strftime("%H:%M:%S") if decision.get("timestamp") else "",
            "Chosen": format_model_name(decision.get('chosen_model', '')),
            "Alternatives": alternatives,
            "Reason": truncate_text(decision.get('reasoning', ''), 40),
            "Cost": format_cost(decision.get('cost', 0.0)),
            "Savings": format_cost(decision.get('savings', 0.0)) if decision.get('savings') else "N/A",
            "Latency": format_latency(decision.get('latency_ms', 0))
        })
    
    df = pd.DataFrame(table_data)
    render_dataframe(df, height=400)


def render_quality_scores_table(evaluations: List[Dict[str, Any]]):
    """
    Render a table of quality evaluations.
    
    Args:
        evaluations: List of quality evaluation dictionaries
    """
    if not evaluations:
        st.info("No quality evaluations to display")
        return
    
    # Format data for display
    table_data = []
    for eval in evaluations:
        table_data.append({
            "Score": f"{eval.get('score', 0):.1f}/10",
            "Model": format_model_name(eval.get('model', '')),
            "Agent": eval.get('agent', 'Unknown'),
            "Hallucination": "⚠️" if eval.get('hallucination', False) else "✅",
            "Reasoning": truncate_text(eval.get('reasoning', ''), 60),
            "Prompt": truncate_text(eval.get('prompt', ''), 40)
        })
    
    df = pd.DataFrame(table_data)
    render_dataframe(df, height=400)


def render_cache_clusters_table(cluster_data: Dict[str, Dict[str, Any]]):
    """
    Render a table of cache cluster statistics.
    
    Args:
        cluster_data: Dictionary mapping cluster_id to stats
    """
    if not cluster_data:
        st.info("No cache clusters to display")
        return
    
    # Format data for display
    table_data = []
    for cluster_id, stats in cluster_data.items():
        total = stats.get('hits', 0) + stats.get('misses', 0)
        hit_rate = stats.get('hits', 0) / total if total > 0 else 0
        
        table_data.append({
            "Cluster ID": truncate_text(cluster_id, 15),
            "Hits": stats.get('hits', 0),
            "Misses": stats.get('misses', 0),
            "Hit Rate": format_percentage(hit_rate),
            "Total Tokens": format_tokens(stats.get('total_tokens', 0)),
            "Total Cost": format_cost(stats.get('total_cost', 0.0))
        })
    
    df = pd.DataFrame(table_data)
    # Sort by hits descending
    df = df.sort_values("Hits", ascending=False)
    render_dataframe(df)


def render_cost_forecast_table(forecast: Dict[str, Any]):
    """
    Render a table showing cost forecasts.
    
    Args:
        forecast: Forecast dictionary with hourly, daily, monthly data
    """
    table_data = [
        {
            "Period": "Hourly",
            "Requests": f"{forecast.get('hourly', {}).get('requests', 0):,}",
            "Cost": format_cost(forecast.get('hourly', {}).get('cost', 0.0))
        },
        {
            "Period": "Daily",
            "Requests": f"{forecast.get('daily', {}).get('requests', 0):,}",
            "Cost": format_cost(forecast.get('daily', {}).get('cost', 0.0))
        },
        {
            "Period": "Monthly",
            "Requests": f"{forecast.get('monthly', {}).get('requests', 0):,}",
            "Cost": format_cost(forecast.get('monthly', {}).get('cost', 0.0))
        }
    ]
    
    df = pd.DataFrame(table_data)
    render_dataframe(df, hide_index=True)


def render_key_value_table(data: Dict[str, str], title: Optional[str] = None):
    """
    Render a simple key-value table.
    
    Args:
        data: Dictionary of key-value pairs
        title: Optional table title
    """
    if title:
        st.subheader(title)
    
    table_data = [{"Property": k, "Value": v} for k, v in data.items()]
    df = pd.DataFrame(table_data)
    render_dataframe(df, hide_index=True)


def render_top_n_table(
    data: Dict[str, float],
    n: int = 10,
    title: str = "Top Items",
    value_label: str = "Value",
    formatter: Optional[callable] = None
):
    """
    Render a table showing top N items.
    
    Args:
        data: Dictionary mapping item to value
        n: Number of items to show
        title: Table title
        value_label: Label for value column
        formatter: Optional formatting function for values
    """
    st.subheader(title)
    
    if not data:
        st.info("No data to display")
        return
    
    # Sort by value descending and take top N
    sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)[:n]
    
    table_data = []
    for i, (item, value) in enumerate(sorted_items, 1):
        formatted_value = formatter(value) if formatter else str(value)
        table_data.append({
            "Rank": i,
            "Item": item,
            value_label: formatted_value
        })
    
    df = pd.DataFrame(table_data)
    render_dataframe(df, hide_index=True)


def render_comparison_table(
    data1: Dict[str, Any],
    data2: Dict[str, Any],
    label1: str = "Current",
    label2: str = "Previous",
    metrics: List[str] = None
):
    """
    Render a side-by-side comparison table.
    
    Args:
        data1: First dataset
        data2: Second dataset
        label1: Label for first dataset
        label2: Label for second dataset
        metrics: List of metric keys to compare
    """
    if not metrics:
        metrics = list(data1.keys())
    
    table_data = []
    for metric in metrics:
        val1 = data1.get(metric, 0)
        val2 = data2.get(metric, 0)
        
        # Calculate change
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            if val2 != 0:
                change = ((val1 - val2) / val2) * 100
                change_str = f"{change:+.1f}%"
            else:
                change_str = "N/A"
        else:
            change_str = "-"
        
        table_data.append({
            "Metric": metric.replace("_", " ").title(),
            label1: str(val1),
            label2: str(val2),
            "Change": change_str
        })
    
    df = pd.DataFrame(table_data)
    render_dataframe(df, hide_index=True)


def render_expandable_rows_table(data: List[Dict[str, Any]], expand_key: str = "details"):
    """
    Render a table with expandable row details.
    
    Args:
        data: List of dictionaries, each with an expand_key containing detail data
        expand_key: Key in dict containing expandable details
    """
    for i, row in enumerate(data):
        with st.expander(f"Row {i+1}: {row.get('summary', 'Details')}"):
            details = row.get(expand_key, {})
            if isinstance(details, dict):
                render_key_value_table(details)
            else:
                st.write(details)