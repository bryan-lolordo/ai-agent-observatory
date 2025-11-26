# Metrics components
"""
Metric Card Components
Location: dashboard/components/metric_cards.py

Reusable KPI card components for displaying metrics with trends.
"""

import streamlit as st
from typing import Optional, List, Tuple
from dashboard.utils.formatters import format_trend


def render_metric_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    delta_color: str = "normal",
    help_text: Optional[str] = None
):
    """
    Render a single metric card with optional trend.
    
    Args:
        label: Metric label (e.g., "Total Cost")
        value: Formatted value (e.g., "$1,234.56")
        delta: Change indicator (e.g., "↑ 12.3%")
        delta_color: "normal", "inverse", or "off"
        help_text: Optional tooltip text
    """
    st.metric(
        label=label,
        value=value,
        delta=delta,
        delta_color=delta_color,
        help=help_text
    )


def render_metric_row(metrics: List[dict], columns: Optional[int] = None):
    """
    Render a row of metric cards.
    
    Args:
        metrics: List of metric dictionaries with keys:
                 - label: Metric label
                 - value: Formatted value
                 - delta: Optional change indicator
                 - delta_color: Optional color ("normal", "inverse", "off")
                 - help_text: Optional tooltip
        columns: Number of columns (default: len(metrics))
    
    Example:
        >>> metrics = [
        ...     {"label": "Total Cost", "value": "$1,234.56", "delta": "↑ 12%"},
        ...     {"label": "Avg Latency", "value": "1.2s", "delta": "↓ 5%", "delta_color": "inverse"}
        ... ]
        >>> render_metric_row(metrics)
    """
    num_cols = columns or len(metrics)
    cols = st.columns(num_cols)
    
    for i, metric in enumerate(metrics):
        with cols[i % num_cols]:
            render_metric_card(
                label=metric.get('label', ''),
                value=metric.get('value', ''),
                delta=metric.get('delta'),
                delta_color=metric.get('delta_color', 'normal'),
                help_text=metric.get('help_text')
            )


def render_kpi_grid(
    metrics: List[dict],
    columns: int = 4,
    title: Optional[str] = None
):
    """
    Render a grid of KPI cards with optional title.
    
    Args:
        metrics: List of metric dictionaries
        columns: Number of columns in grid (default: 4)
        title: Optional section title
    
    Example:
        >>> metrics = [
        ...     {"label": "Total Sessions", "value": "1,234"},
        ...     {"label": "Total Cost", "value": "$567.89"},
        ...     {"label": "Cache Hit Rate", "value": "45.2%"},
        ...     {"label": "Avg Quality Score", "value": "8.5/10"}
        ... ]
        >>> render_kpi_grid(metrics, columns=4, title="Overview Metrics")
    """
    if title:
        st.subheader(title)
    
    # Split metrics into rows
    for i in range(0, len(metrics), columns):
        row_metrics = metrics[i:i + columns]
        render_metric_row(row_metrics, columns=columns)


def render_styled_metric_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    delta_color: str = "green",
    icon: Optional[str] = None,
    background_color: str = "#f0f2f6"
):
    """
    Render a metric card with custom styling.
    
    Args:
        label: Metric label
        value: Formatted value
        delta: Change indicator
        delta_color: Color for delta ("green", "red", "gray")
        icon: Optional emoji icon
        background_color: Card background color
    """
    # Map color names to hex
    color_map = {
        "green": "#10b981",
        "red": "#ef4444",
        "gray": "#6b7280"
    }
    
    delta_html = ""
    if delta:
        color = color_map.get(delta_color, "#6b7280")
        delta_html = f'<p style="color: {color}; font-size: 0.9rem; margin: 0;">{delta}</p>'
    
    icon_html = f'<span style="font-size: 1.5rem;">{icon}</span> ' if icon else ""
    
    st.markdown(f"""
    <div style="
        background: {background_color};
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    ">
        <p style="color: #6b7280; font-size: 0.875rem; margin: 0;">
            {icon_html}{label}
        </p>
        <p style="font-size: 2rem; font-weight: 700; margin: 0.5rem 0;">
            {value}
        </p>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def render_comparison_cards(
    current_metrics: dict,
    previous_metrics: dict,
    period: str = "24h"
):
    """
    Render comparison cards showing current vs previous period.
    
    Args:
        current_metrics: Current period metrics (dict with keys matching metric names)
        previous_metrics: Previous period metrics
        period: Time period label (e.g., "24h", "7d")
    
    Example:
        >>> current = {"cost": 123.45, "tokens": 50000, "latency": 1200}
        >>> previous = {"cost": 110.0, "tokens": 45000, "latency": 1300}
        >>> render_comparison_cards(current, previous, period="24h")
    """
    st.write(f"**Current vs Previous {period}**")
    
    metrics = []
    for key, current_value in current_metrics.items():
        previous_value = previous_metrics.get(key, 0)
        
        # Calculate trend
        if previous_value > 0:
            is_cost = "cost" in key.lower()
            trend_text, trend_color = format_trend(current_value, previous_value, is_cost=is_cost)
        else:
            trend_text = "N/A"
            trend_color = "off"
        
        # Determine delta_color for st.metric
        if trend_color == "green":
            delta_color = "normal"
        elif trend_color == "red":
            delta_color = "inverse"
        else:
            delta_color = "off"
        
        metrics.append({
            "label": key.replace("_", " ").title(),
            "value": str(current_value),
            "delta": trend_text,
            "delta_color": delta_color
        })
    
    render_metric_row(metrics)


def render_metric_with_sparkline(
    label: str,
    value: str,
    sparkline_data: List[float],
    delta: Optional[str] = None
):
    """
    Render a metric card with a sparkline chart.
    
    Args:
        label: Metric label
        value: Current value
        sparkline_data: List of values for sparkline
        delta: Change indicator
    
    Note: Uses st.line_chart for sparkline
    """
    st.markdown(f"**{label}**")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.metric(label="", value=value, delta=delta, label_visibility="collapsed")
    
    with col2:
        st.line_chart(sparkline_data, height=60)


def render_status_indicator(
    label: str,
    status: str,
    message: Optional[str] = None
):
    """
    Render a status indicator card.
    
    Args:
        label: Status label
        status: Status type ("healthy", "warning", "error", "info")
        message: Optional status message
    """
    status_config = {
        "healthy": {"icon": "🟢", "color": "#10b981", "text": "Healthy"},
        "warning": {"icon": "🟡", "color": "#f59e0b", "text": "Warning"},
        "error": {"icon": "🔴", "color": "#ef4444", "text": "Error"},
        "info": {"icon": "🔵", "color": "#3b82f6", "text": "Info"}
    }
    
    config = status_config.get(status, status_config["info"])
    msg = message or config["text"]
    
    st.markdown(f"""
    <div style="
        padding: 1rem;
        border-left: 4px solid {config['color']};
        background: #f9fafb;
        border-radius: 4px;
    ">
        <p style="margin: 0; font-weight: 600;">
            {config['icon']} {label}
        </p>
        <p style="margin: 0.25rem 0 0 0; color: #6b7280; font-size: 0.875rem;">
            {msg}
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_metric_summary_card(
    title: str,
    metrics: dict,
    icon: Optional[str] = None
):
    """
    Render a summary card with multiple metrics.
    
    Args:
        title: Card title
        metrics: Dictionary of label: value pairs
        icon: Optional emoji icon
    
    Example:
        >>> metrics = {
        ...     "Total Cost": "$1,234.56",
        ...     "Total Tokens": "12.4K",
        ...     "Avg Latency": "1.2s",
        ...     "Success Rate": "98.5%"
        ... }
        >>> render_metric_summary_card("Session Summary", metrics, icon="📊")
    """
    icon_html = f'{icon} ' if icon else ''
    
    metrics_html = ""
    for label, value in metrics.items():
        metrics_html += f"""
        <div style="display: flex; justify-content: space-between; margin: 0.5rem 0;">
            <span style="color: #6b7280;">{label}:</span>
            <span style="font-weight: 600;">{value}</span>
        </div>
        """
    
    st.markdown(f"""
    <div style="
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    ">
        <h3 style="margin: 0 0 1rem 0; font-size: 1.25rem;">
            {icon_html}{title}
        </h3>
        {metrics_html}
    </div>
    """, unsafe_allow_html=True)


def render_empty_state(
    message: str = "No data available",
    icon: str = "📊",
    suggestion: Optional[str] = None
):
    """
    Render an empty state card when no data is available.
    
    Args:
        message: Main message to display
        icon: Emoji icon
        suggestion: Optional suggestion text
    """
    suggestion_html = ""
    if suggestion:
        suggestion_html = f'<p style="color: #6b7280; margin: 0.5rem 0 0 0;">{suggestion}</p>'
    
    st.markdown(f"""
    <div style="
        text-align: center;
        padding: 3rem 2rem;
        background: #f9fafb;
        border-radius: 8px;
        border: 2px dashed #d1d5db;
    ">
        <p style="font-size: 3rem; margin: 0;">{icon}</p>
        <p style="font-size: 1.25rem; font-weight: 600; margin: 1rem 0 0 0;">
            {message}
        </p>
        {suggestion_html}
    </div>
    """, unsafe_allow_html=True)