"""
Filter Components
Location: dashboard/components/filters.py

Reusable filter UI components for filtering dashboard data.
"""

import streamlit as st
from typing import List, Optional, Tuple
from datetime import datetime, timedelta, date


def render_project_filter(
    available_projects: List[str],
    key: str = "project_filter",
    include_all: bool = True,
    label: str = "Select Project"
) -> Optional[str]:
    """
    Render a project selection filter.
    
    Args:
        available_projects: List of available project names
        key: Unique key for the widget
        include_all: Whether to include "All Projects" option
        label: Label for the selectbox
    
    Returns:
        Selected project name or None if "All Projects" selected
    """
    options = ["All Projects"] + available_projects if include_all else available_projects
    
    selected = st.selectbox(
        label,
        options=options,
        key=key,
        help="Filter data by project"
    )
    
    return None if selected == "All Projects" else selected


def render_model_filter(
    available_models: List[str],
    key: str = "model_filter",
    multiselect: bool = False
) -> Optional[List[str]]:
    """
    Render a model selection filter.
    
    Args:
        available_models: List of available model names
        key: Unique key for the widget
        multiselect: If True, allow multiple selections
    
    Returns:
        Selected model(s) or None if "All" selected (for single select)
    """
    if not available_models:
        st.info("No models available")
        return None
    
    if multiselect:
        selected = st.multiselect(
            "Filter by Model",
            options=available_models,
            key=key,
            help="Select one or more models"
        )
        return selected if selected else None
    else:
        options = ["All Models"] + available_models
        selected = st.selectbox(
            "Filter by Model",
            options=options,
            key=key,
            help="Filter by model"
        )
        return None if selected == "All Models" else [selected]


def render_agent_filter(
    available_agents: List[str],
    key: str = "agent_filter",
    multiselect: bool = False
) -> Optional[List[str]]:
    """
    Render an agent selection filter.
    
    Args:
        available_agents: List of available agent names
        key: Unique key for the widget
        multiselect: If True, allow multiple selections
    
    Returns:
        Selected agent(s) or None if "All" selected
    """
    if not available_agents:
        st.info("No agents available")
        return None
    
    if multiselect:
        selected = st.multiselect(
            "Filter by Agent",
            options=available_agents,
            key=key,
            help="Select one or more agents"
        )
        return selected if selected else None
    else:
        options = ["All Agents"] + available_agents
        selected = st.selectbox(
            "Filter by Agent",
            options=options,
            key=key,
            help="Filter by agent"
        )
        return None if selected == "All Agents" else [selected]


def render_date_range_filter(
    key: str = "date_range_filter",
    default_days: int = 7,
    max_days: int = 90
) -> Tuple[datetime, datetime]:
    """
    Render a date range filter.
    
    Args:
        key: Unique key for the widget
        default_days: Default number of days to look back
        max_days: Maximum number of days allowed
    
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=date.today() - timedelta(days=default_days),
            max_value=date.today(),
            key=f"{key}_start",
            help="Select start date"
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=date.today(),
            max_value=date.today(),
            key=f"{key}_end",
            help="Select end date"
        )
    
    # Convert to datetime
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # Validate range
    if (end_datetime - start_datetime).days > max_days:
        st.warning(f"Date range exceeds {max_days} days. Using last {max_days} days.")
        start_datetime = end_datetime - timedelta(days=max_days)
    
    return start_datetime, end_datetime


def render_time_period_filter(
    key: str = "time_period_filter",
    label: str = "Time Period"
) -> str:
    """
    Render a preset time period filter.
    
    Args:
        key: Unique key for the widget
        label: Label for the selectbox
    
    Returns:
        Selected time period string ("1h", "24h", "7d", "30d")
    """
    periods = {
        "Last Hour": "1h",
        "Last 24 Hours": "24h",
        "Last 7 Days": "7d",
        "Last 30 Days": "30d"
    }
    
    selected = st.selectbox(
        label,
        options=list(periods.keys()),
        index=1,  # Default to "Last 24 Hours"
        key=key,
        help="Select time period for analysis"
    )
    
    return periods[selected]


def render_metric_filter(
    key: str = "metric_filter",
    metrics: Optional[List[str]] = None
) -> str:
    """
    Render a metric selection filter.
    
    Args:
        key: Unique key for the widget
        metrics: List of available metrics (default: cost, tokens, latency)
    
    Returns:
        Selected metric
    """
    if metrics is None:
        metrics = ["Cost", "Tokens", "Latency", "Count"]
    
    selected = st.selectbox(
        "Select Metric",
        options=metrics,
        key=key,
        help="Choose metric to visualize"
    )
    
    return selected.lower()


def render_filter_sidebar(
    available_projects: List[str],
    available_models: List[str],
    available_agents: List[str],
    show_date_filter: bool = True,
    show_time_period: bool = True
) -> dict:
    """
    Render a complete filter sidebar with all common filters.
    
    Args:
        available_projects: List of projects
        available_models: List of models
        available_agents: List of agents
        show_date_filter: Whether to show date range filter
        show_time_period: Whether to show time period filter
    
    Returns:
        Dictionary of all selected filter values
    """
    with st.sidebar:
        st.header("Filters")
        
        filters = {}
        
        # Project filter
        filters['project'] = render_project_filter(available_projects)
        
        # Model filter
        if available_models:
            filters['models'] = render_model_filter(available_models, multiselect=True)
        
        # Agent filter
        if available_agents:
            filters['agents'] = render_agent_filter(available_agents, multiselect=True)
        
        st.divider()
        
        # Time filters
        if show_time_period:
            filters['time_period'] = render_time_period_filter()
        
        if show_date_filter:
            filters['start_date'], filters['end_date'] = render_date_range_filter()
        
        return filters


def render_quick_filters(
    available_projects: List[str],
    show_models: bool = True,
    show_agents: bool = True,
    show_time_period: bool = True
) -> dict:
    """
    Render quick filters in a horizontal layout (for main content area).
    
    Args:
        available_projects: List of projects
        show_models: Whether to show model filter
        show_agents: Whether to show agent filter
        show_time_period: Whether to show time period filter
    
    Returns:
        Dictionary of selected filter values
    """
    filters = {}
    
    # Create columns based on which filters to show
    num_cols = 1 + sum([show_models, show_agents, show_time_period])
    cols = st.columns(num_cols)
    
    col_idx = 0
    
    # Project filter (always shown)
    with cols[col_idx]:
        filters['project'] = render_project_filter(
            available_projects,
            key="quick_project_filter"
        )
    col_idx += 1
    
    # Optional filters
    if show_time_period:
        with cols[col_idx]:
            filters['time_period'] = render_time_period_filter(
                key="quick_time_period_filter"
            )
        col_idx += 1
    
    if show_models:
        # Get models based on selected project
        from dashboard.utils.data_fetcher import get_available_models
        models = get_available_models(filters.get('project'))
        if models:
            with cols[col_idx]:
                filters['models'] = render_model_filter(
                    models,
                    key="quick_model_filter",
                    multiselect=False
                )
        col_idx += 1
    
    if show_agents:
        # Get agents based on selected project
        from dashboard.utils.data_fetcher import get_available_agents
        agents = get_available_agents(filters.get('project'))
        if agents:
            with cols[col_idx]:
                filters['agents'] = render_agent_filter(
                    agents,
                    key="quick_agent_filter",
                    multiselect=False
                )
    
    return filters


def render_search_filter(
    key: str = "search_filter",
    placeholder: str = "Search...",
    label: Optional[str] = None
) -> str:
    """
    Render a text search filter.
    
    Args:
        key: Unique key for the widget
        placeholder: Placeholder text
        label: Optional label (hidden if None)
    
    Returns:
        Search query string
    """
    search_query = st.text_input(
        label or "Search",
        placeholder=placeholder,
        key=key,
        label_visibility="collapsed" if not label else "visible"
    )
    
    return search_query.strip()


def render_slider_filter(
    min_value: float,
    max_value: float,
    default_value: Optional[Tuple[float, float]] = None,
    label: str = "Range",
    key: str = "slider_filter",
    step: float = 1.0
) -> Tuple[float, float]:
    """
    Render a range slider filter.
    
    Args:
        min_value: Minimum value
        max_value: Maximum value
        default_value: Default selected range
        label: Label for slider
        key: Unique key for widget
        step: Step size
    
    Returns:
        Tuple of (min_selected, max_selected)
    """
    if default_value is None:
        default_value = (min_value, max_value)
    
    selected_range = st.slider(
        label,
        min_value=min_value,
        max_value=max_value,
        value=default_value,
        step=step,
        key=key
    )
    
    return selected_range


def render_checkbox_filter(
    label: str,
    key: str = "checkbox_filter",
    default: bool = False,
    help_text: Optional[str] = None
) -> bool:
    """
    Render a simple checkbox filter.
    
    Args:
        label: Checkbox label
        key: Unique key for widget
        default: Default checked state
        help_text: Optional help text
    
    Returns:
        Checkbox state (True/False)
    """
    return st.checkbox(
        label,
        value=default,
        key=key,
        help=help_text
    )


def render_radio_filter(
    label: str,
    options: List[str],
    key: str = "radio_filter",
    horizontal: bool = True,
    default_index: int = 0
) -> str:
    """
    Render a radio button filter.
    
    Args:
        label: Label for radio group
        options: List of options
        key: Unique key for widget
        horizontal: Whether to display horizontally
        default_index: Default selected index
    
    Returns:
        Selected option
    """
    return st.radio(
        label,
        options=options,
        key=key,
        horizontal=horizontal,
        index=default_index
    )


def render_clear_filters_button(key: str = "clear_filters") -> bool:
    """
    Render a button to clear all filters.
    
    Args:
        key: Unique key for button
    
    Returns:
        True if button was clicked
    """
    return st.button("🔄 Clear All Filters", key=key, type="secondary")


def apply_filters_to_data(data: List[dict], filters: dict) -> List[dict]:
    """
    Apply filters to a list of data dictionaries.
    
    Args:
        data: List of data dictionaries
        filters: Dictionary of filter conditions
    
    Returns:
        Filtered data list
    """
    filtered_data = data
    
    # Apply each filter
    for key, value in filters.items():
        if value is None or value == [] or value == "":
            continue
        
        if key == 'project' and value:
            filtered_data = [d for d in filtered_data if d.get('project_name') == value]
        
        elif key == 'models' and value:
            filtered_data = [d for d in filtered_data if d.get('model_name') in value]
        
        elif key == 'agents' and value:
            filtered_data = [d for d in filtered_data if d.get('agent_name') in value]
        
        elif key == 'start_date' and value:
            filtered_data = [d for d in filtered_data if d.get('timestamp', datetime.min) >= value]
        
        elif key == 'end_date' and value:
            filtered_data = [d for d in filtered_data if d.get('timestamp', datetime.max) <= value]
    
    return filtered_data