# Chart components
"""
Chart Components
Location: dashboard/components/charts.py

Reusable Plotly chart components for visualizing metrics.
"""

import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional, Any
from datetime import datetime


def create_cost_breakdown_pie(
    cost_data: Dict[str, float],
    title: str = "Cost Breakdown"
) -> go.Figure:
    """
    Create a pie chart showing cost distribution.
    
    Args:
        cost_data: Dictionary mapping category to cost (e.g., {"GPT-4": 123.45, "Claude": 67.89})
        title: Chart title
    
    Returns:
        Plotly Figure
    """
    if not cost_data:
        return create_empty_chart("No cost data available")
    
    labels = list(cost_data.keys())
    values = list(cost_data.values())
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.3,  # Donut chart
        textinfo='label+percent',
        textposition='outside',
        marker=dict(
            line=dict(color='white', width=2)
        )
    )])
    
    fig.update_layout(
        title=title,
        showlegend=True,
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return fig


def create_time_series_chart(
    time_data: Dict[datetime, float],
    metric_name: str = "Metric",
    title: Optional[str] = None
) -> go.Figure:
    """
    Create a time series line chart.
    
    Args:
        time_data: Dictionary mapping timestamp to value
        metric_name: Name of the metric being plotted
        title: Chart title (auto-generated if None)
    
    Returns:
        Plotly Figure
    """
    if not time_data:
        return create_empty_chart("No time series data available")
    
    timestamps = list(time_data.keys())
    values = list(time_data.values())
    
    fig = go.Figure(data=[go.Scatter(
        x=timestamps,
        y=values,
        mode='lines+markers',
        name=metric_name,
        line=dict(color='#3b82f6', width=2),
        marker=dict(size=6),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.1)'
    )])
    
    fig.update_layout(
        title=title or f"{metric_name} Over Time",
        xaxis_title="Time",
        yaxis_title=metric_name,
        hovermode='x unified',
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return fig


def create_bar_chart(
    data: Dict[str, float],
    x_label: str = "Category",
    y_label: str = "Value",
    title: Optional[str] = None,
    orientation: str = "v",
    color: Optional[str] = None
) -> go.Figure:
    """
    Create a bar chart.
    
    Args:
        data: Dictionary mapping category to value
        x_label: X-axis label
        y_label: Y-axis label
        title: Chart title
        orientation: "v" for vertical, "h" for horizontal
        color: Bar color (hex or name)
    
    Returns:
        Plotly Figure
    """
    if not data:
        return create_empty_chart("No data available")
    
    categories = list(data.keys())
    values = list(data.values())
    
    if orientation == "h":
        fig = go.Figure(data=[go.Bar(
            x=values,
            y=categories,
            orientation='h',
            marker_color=color or '#3b82f6'
        )])
        fig.update_xaxes(title=y_label)
        fig.update_yaxes(title=x_label)
    else:
        fig = go.Figure(data=[go.Bar(
            x=categories,
            y=values,
            marker_color=color or '#3b82f6'
        )])
        fig.update_xaxes(title=x_label)
        fig.update_yaxes(title=y_label)
    
    fig.update_layout(
        title=title,
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
        showlegend=False
    )
    
    return fig


def create_stacked_bar_chart(
    data: Dict[str, Dict[str, float]],
    title: str = "Stacked Bar Chart",
    x_label: str = "Category",
    y_label: str = "Value"
) -> go.Figure:
    """
    Create a stacked bar chart.
    
    Args:
        data: Nested dictionary {category: {subcategory: value}}
              Example: {"Agent1": {"GPT-4": 10, "Claude": 5}, "Agent2": {...}}
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
    
    Returns:
        Plotly Figure
    """
    if not data:
        return create_empty_chart("No data available")
    
    fig = go.Figure()
    
    # Get all unique subcategories
    all_subcategories = set()
    for subdata in data.values():
        all_subcategories.update(subdata.keys())
    
    # Add a trace for each subcategory
    for subcategory in sorted(all_subcategories):
        categories = []
        values = []
        for category, subdata in data.items():
            categories.append(category)
            values.append(subdata.get(subcategory, 0))
        
        fig.add_trace(go.Bar(
            name=subcategory,
            x=categories,
            y=values
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        barmode='stack',
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return fig


def create_scatter_plot(
    x_values: List[float],
    y_values: List[float],
    labels: Optional[List[str]] = None,
    x_label: str = "X",
    y_label: str = "Y",
    title: str = "Scatter Plot",
    color_values: Optional[List[float]] = None,
    size_values: Optional[List[float]] = None
) -> go.Figure:
    """
    Create a scatter plot (e.g., cost vs quality).
    
    Args:
        x_values: X-axis values
        y_values: Y-axis values
        labels: Optional labels for hover text
        x_label: X-axis label
        y_label: Y-axis label
        title: Chart title
        color_values: Optional values for color scale
        size_values: Optional values for marker size
    
    Returns:
        Plotly Figure
    """
    if not x_values or not y_values:
        return create_empty_chart("No data available")
    
    hover_text = labels if labels else None
    
    fig = go.Figure(data=[go.Scatter(
        x=x_values,
        y=y_values,
        mode='markers',
        text=hover_text,
        marker=dict(
            size=size_values or 10,
            color=color_values or x_values,
            colorscale='Viridis',
            showscale=True if color_values else False,
            line=dict(width=1, color='white')
        ),
        hovertemplate='<b>%{text}</b><br>' +
                      f'{x_label}: %{{x}}<br>' +
                      f'{y_label}: %{{y}}<br>' +
                      '<extra></extra>'
    )])
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        height=500,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return fig


def create_heatmap(
    data: List[List[float]],
    x_labels: List[str],
    y_labels: List[str],
    title: str = "Heatmap",
    colorscale: str = "Blues"
) -> go.Figure:
    """
    Create a heatmap (e.g., routing confusion matrix).
    
    Args:
        data: 2D array of values
        x_labels: Labels for x-axis
        y_labels: Labels for y-axis
        title: Chart title
        colorscale: Plotly colorscale name
    
    Returns:
        Plotly Figure
    """
    if not data:
        return create_empty_chart("No data available")
    
    fig = go.Figure(data=go.Heatmap(
        z=data,
        x=x_labels,
        y=y_labels,
        colorscale=colorscale,
        text=data,
        texttemplate='%{text}',
        textfont={"size": 10},
        hoverongaps=False
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="",
        yaxis_title="",
        height=400,
        margin=dict(t=50, b=50, l=100, r=50)
    )
    
    return fig


def create_histogram(
    values: List[float],
    title: str = "Distribution",
    x_label: str = "Value",
    bins: int = 30,
    color: str = "#3b82f6"
) -> go.Figure:
    """
    Create a histogram showing distribution.
    
    Args:
        values: List of values
        title: Chart title
        x_label: X-axis label
        bins: Number of bins
        color: Bar color
    
    Returns:
        Plotly Figure
    """
    if not values:
        return create_empty_chart("No data available")
    
    fig = go.Figure(data=[go.Histogram(
        x=values,
        nbinsx=bins,
        marker_color=color,
        opacity=0.7
    )])
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title="Count",
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
        showlegend=False
    )
    
    return fig


def create_box_plot(
    data: Dict[str, List[float]],
    title: str = "Distribution Comparison",
    y_label: str = "Value"
) -> go.Figure:
    """
    Create a box plot showing distributions across categories.
    
    Args:
        data: Dictionary mapping category to list of values
        title: Chart title
        y_label: Y-axis label
    
    Returns:
        Plotly Figure
    """
    if not data:
        return create_empty_chart("No data available")
    
    fig = go.Figure()
    
    for category, values in data.items():
        fig.add_trace(go.Box(
            y=values,
            name=category,
            boxmean='sd'
        ))
    
    fig.update_layout(
        title=title,
        yaxis_title=y_label,
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
        showlegend=True
    )
    
    return fig


def create_multi_line_chart(
    data: Dict[str, Dict[datetime, float]],
    title: str = "Multi-Line Chart",
    y_label: str = "Value"
) -> go.Figure:
    """
    Create a line chart with multiple series.
    
    Args:
        data: Nested dictionary {series_name: {timestamp: value}}
        title: Chart title
        y_label: Y-axis label
    
    Returns:
        Plotly Figure
    """
    if not data:
        return create_empty_chart("No data available")
    
    fig = go.Figure()
    
    for series_name, time_data in data.items():
        timestamps = list(time_data.keys())
        values = list(time_data.values())
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=values,
            mode='lines+markers',
            name=series_name,
            line=dict(width=2),
            marker=dict(size=4)
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title=y_label,
        hovermode='x unified',
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def create_funnel_chart(
    stages: List[str],
    values: List[float],
    title: str = "Funnel Chart"
) -> go.Figure:
    """
    Create a funnel chart (e.g., for conversion rates).
    
    Args:
        stages: List of stage names
        values: List of values for each stage
        title: Chart title
    
    Returns:
        Plotly Figure
    """
    if not stages or not values:
        return create_empty_chart("No data available")
    
    fig = go.Figure(go.Funnel(
        y=stages,
        x=values,
        textinfo="value+percent initial"
    ))
    
    fig.update_layout(
        title=title,
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return fig


def create_gauge_chart(
    value: float,
    title: str = "Gauge",
    min_value: float = 0,
    max_value: float = 100,
    threshold_ranges: Optional[List[Dict]] = None
) -> go.Figure:
    """
    Create a gauge chart (e.g., for cache hit rate).
    
    Args:
        value: Current value
        title: Chart title
        min_value: Minimum value
        max_value: Maximum value
        threshold_ranges: Optional list of threshold configs
                          [{"range": [0, 30], "color": "red"}, ...]
    
    Returns:
        Plotly Figure
    """
    if threshold_ranges is None:
        threshold_ranges = [
            {"range": [0, 30], "color": "red"},
            {"range": [30, 70], "color": "yellow"},
            {"range": [70, 100], "color": "green"}
        ]
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        title={'text': title},
        gauge={
            'axis': {'range': [min_value, max_value]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': r['range'], 'color': r['color']}
                for r in threshold_ranges
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_value * 0.9
            }
        }
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return fig


def create_area_chart(
    time_data: Dict[datetime, Dict[str, float]],
    title: str = "Area Chart"
) -> go.Figure:
    """
    Create a stacked area chart.
    
    Args:
        time_data: Nested dict {timestamp: {category: value}}
        title: Chart title
    
    Returns:
        Plotly Figure
    """
    if not time_data:
        return create_empty_chart("No data available")
    
    fig = go.Figure()
    
    # Get all categories
    all_categories = set()
    for categories in time_data.values():
        all_categories.update(categories.keys())
    
    # Add trace for each category
    for category in sorted(all_categories):
        timestamps = []
        values = []
        for timestamp, categories in sorted(time_data.items()):
            timestamps.append(timestamp)
            values.append(categories.get(category, 0))
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=values,
            name=category,
            mode='lines',
            stackgroup='one',
            fillcolor='rgba(0,0,0,0.1)'
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title="Value",
        hovermode='x unified',
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    return fig


def create_empty_chart(message: str = "No data available") -> go.Figure:
    """
    Create an empty chart with a message.
    
    Args:
        message: Message to display
    
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16, color="gray")
    )
    
    fig.update_layout(
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False)
    )
    
    return fig