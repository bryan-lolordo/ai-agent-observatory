"""
Dashboard Components Package
Location: dashboard/components/__init__.py

Reusable UI components for the Observatory dashboard.
"""

# Metric Cards
from dashboard.components.metric_cards import (
    render_metric_card,
    render_metric_row,
    render_kpi_grid,
    render_styled_metric_card,
    render_comparison_cards,
    render_metric_with_sparkline,
    render_status_indicator,
    render_metric_summary_card,
    render_empty_state
)

# Charts
from dashboard.components.charts import (
    create_cost_breakdown_pie,
    create_time_series_chart,
    create_bar_chart,
    create_stacked_bar_chart,
    create_scatter_plot,
    create_heatmap,
    create_histogram,
    create_box_plot,
    create_multi_line_chart,
    create_funnel_chart,
    create_gauge_chart,
    create_area_chart,
    create_empty_chart
)

# Tables
from dashboard.components.tables import (
    render_dataframe,
    render_sessions_table,
    render_llm_calls_table,
    render_model_comparison_table,
    render_agent_comparison_table,
    render_routing_decisions_table,
    render_quality_scores_table,
    render_cache_clusters_table,
    render_cost_forecast_table,
    render_key_value_table,
    render_top_n_table,
    render_comparison_table,
    render_expandable_rows_table
)

# Filters
from dashboard.components.filters import (
    render_project_filter,
    render_model_filter,
    render_agent_filter,
    render_date_range_filter,
    render_time_period_filter,
    render_metric_filter,
    render_filter_sidebar,
    render_quick_filters,
    render_search_filter,
    render_slider_filter,
    render_checkbox_filter,
    render_radio_filter,
    render_clear_filters_button,
    apply_filters_to_data
)

__all__ = [
    # Metric Cards
    'render_metric_card',
    'render_metric_row',
    'render_kpi_grid',
    'render_styled_metric_card',
    'render_comparison_cards',
    'render_metric_with_sparkline',
    'render_status_indicator',
    'render_metric_summary_card',
    'render_empty_state',
    
    # Charts
    'create_cost_breakdown_pie',
    'create_time_series_chart',
    'create_bar_chart',
    'create_stacked_bar_chart',
    'create_scatter_plot',
    'create_heatmap',
    'create_histogram',
    'create_box_plot',
    'create_multi_line_chart',
    'create_funnel_chart',
    'create_gauge_chart',
    'create_area_chart',
    'create_empty_chart',
    
    # Tables
    'render_dataframe',
    'render_sessions_table',
    'render_llm_calls_table',
    'render_model_comparison_table',
    'render_agent_comparison_table',
    'render_routing_decisions_table',
    'render_quality_scores_table',
    'render_cache_clusters_table',
    'render_cost_forecast_table',
    'render_key_value_table',
    'render_top_n_table',
    'render_comparison_table',
    'render_expandable_rows_table',
    
    # Filters
    'render_project_filter',
    'render_model_filter',
    'render_agent_filter',
    'render_date_range_filter',
    'render_time_period_filter',
    'render_metric_filter',
    'render_filter_sidebar',
    'render_quick_filters',
    'render_search_filter',
    'render_slider_filter',
    'render_checkbox_filter',
    'render_radio_filter',
    'render_clear_filters_button',
    'apply_filters_to_data',
]