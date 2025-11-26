"""
Settings Page - Configuration and Preferences
Location: dashboard/pages/settings.py

Manage Observatory configuration, project settings, and user preferences.
"""

import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any, List
import pandas as pd
import json
from pathlib import Path

from dashboard.utils.data_fetcher import (
    get_project_overview,
    get_available_projects,
    get_database_stats,
)
from dashboard.utils.formatters import (
    format_cost,
    format_tokens,
)


def get_config_file_path() -> Path:
    """Get path to configuration file."""
    return Path.home() / ".observatory" / "config.json"


def load_user_config() -> Dict[str, Any]:
    """Load user configuration from file."""
    config_path = get_config_file_path()
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except:
            return get_default_config()
    else:
        return get_default_config()


def save_user_config(config: Dict[str, Any]):
    """Save user configuration to file."""
    config_path = get_config_file_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(config, indent=2, fp=f)


def get_default_config() -> Dict[str, Any]:
    """Get default configuration."""
    return {
        "display": {
            "default_time_range": "7d",
            "default_limit": 100,
            "refresh_rate": 5,
            "chart_theme": "plotly",
            "show_token_counts": True,
            "compact_mode": False,
        },
        "alerts": {
            "enabled": False,
            "cost_threshold_daily": 10.0,
            "error_rate_threshold": 0.10,
            "latency_threshold_ms": 5000,
            "quality_score_threshold": 7.0,
        },
        "performance": {
            "cache_results": True,
            "result_cache_ttl": 300,
            "max_query_limit": 1000,
            "enable_query_optimization": True,
        },
        "export": {
            "default_format": "csv",
            "include_metadata": True,
            "compress_exports": False,
        },
        "advanced": {
            "debug_mode": False,
            "verbose_logging": False,
            "enable_experimental_features": False,
        }
    }


def render_project_management():
    """Render project management section."""
    st.subheader("📁 Project Management")
    
    try:
        projects = get_available_projects()
        
        if projects:
            st.write(f"**Active Projects:** {len(projects)}")
            
            # Project list
            project_data = []
            for project in projects:
                try:
                    overview = get_project_overview(project)
                    kpis = overview.get('kpis', {})
                    
                    project_data.append({
                        'Project Name': project,
                        'Total Calls': kpis.get('total_requests', 0),
                        'Total Cost': format_cost(kpis.get('total_cost', 0)),
                        'Total Tokens': format_tokens(kpis.get('total_tokens', 0)),
                        'Agents': kpis.get('unique_agents', 0),
                        'Models': kpis.get('unique_models', 0),
                    })
                except:
                    project_data.append({
                        'Project Name': project,
                        'Total Calls': 'N/A',
                        'Total Cost': 'N/A',
                        'Total Tokens': 'N/A',
                        'Agents': 'N/A',
                        'Models': 'N/A',
                    })
            
            df = pd.DataFrame(project_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
        else:
            st.info("No projects found. Start using Observatory in your applications to create projects.")
    
    except Exception as e:
        st.error(f"Error loading projects: {str(e)}")
    
    st.divider()
    
    # Add new project (informational)
    with st.expander("➕ How to Add a New Project"):
        st.markdown("""
        **Adding a new project is automatic!**
        
        Simply initialize Observatory with a new project name in your code:
        
        ```python
        from observatory import Observatory
        
        obs = Observatory(project_name="My New Project")
        ```
        
        The project will automatically appear in the dashboard once you start tracking calls.
        
        **Project Naming Best Practices:**
        - Use descriptive names (e.g., "Customer Support Bot", "Code Review Crew")
        - Keep names consistent across your codebase
        - Use the same project name for related agents
        - Avoid special characters
        """)


def render_database_settings():
    """Render database configuration section."""
    st.subheader("💾 Database Settings")
    
    try:
        db_stats = get_database_stats()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Sessions", f"{db_stats.get('total_sessions', 0):,}")
        
        with col2:
            st.metric("Total LLM Calls", f"{db_stats.get('total_llm_calls', 0):,}")
        
        with col3:
            db_size = db_stats.get('database_size_mb', 0)
            st.metric("Database Size", f"{db_size:.2f} MB")
        
        st.divider()
        
        # Database actions
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Database Location**")
            db_path = db_stats.get('database_path', 'observatory.db')
            st.code(db_path, language="text")
        
        with col2:
            st.write("**Database Actions**")
            
            if st.button("📊 View Detailed Stats", use_container_width=True):
                with st.expander("Detailed Database Statistics", expanded=True):
                    st.json(db_stats)
            
            if st.button("🔄 Optimize Database", use_container_width=True):
                st.info("Database optimization would run here (VACUUM, ANALYZE, etc.)")
        
        st.divider()
        
        # Dangerous actions
        with st.expander("⚠️ Dangerous Actions", expanded=False):
            st.warning("These actions cannot be undone. Use with caution.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ Clear Old Data (>30 days)", type="secondary"):
                    st.error("This would delete data older than 30 days")
            
            with col2:
                if st.button("💣 Reset Database", type="secondary"):
                    st.error("This would delete ALL data in the database")
    
    except Exception as e:
        st.error(f"Error loading database settings: {str(e)}")


def render_display_preferences(config: Dict[str, Any]) -> Dict[str, Any]:
    """Render display preferences section."""
    st.subheader("🎨 Display Preferences")
    
    display_config = config.get('display', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Default Settings**")
        
        default_time_range = st.selectbox(
            "Default Time Range",
            options=["1h", "24h", "7d", "30d"],
            index=["1h", "24h", "7d", "30d"].index(display_config.get('default_time_range', '7d')),
            key="default_time_range"
        )
        
        default_limit = st.selectbox(
            "Default Result Limit",
            options=[50, 100, 200, 500],
            index=[50, 100, 200, 500].index(display_config.get('default_limit', 100)),
            key="default_limit"
        )
        
        refresh_rate = st.selectbox(
            "Auto-Refresh Rate (seconds)",
            options=[2, 5, 10, 30, 60],
            index=[2, 5, 10, 30, 60].index(display_config.get('refresh_rate', 5)),
            key="refresh_rate"
        )
    
    with col2:
        st.write("**Display Options**")
        
        show_token_counts = st.checkbox(
            "Show Token Counts",
            value=display_config.get('show_token_counts', True),
            key="show_token_counts"
        )
        
        compact_mode = st.checkbox(
            "Compact Mode",
            value=display_config.get('compact_mode', False),
            help="Reduce padding and spacing for more information density",
            key="compact_mode"
        )
        
        chart_theme = st.selectbox(
            "Chart Theme",
            options=["plotly", "plotly_white", "plotly_dark"],
            index=["plotly", "plotly_white", "plotly_dark"].index(display_config.get('chart_theme', 'plotly')),
            key="chart_theme"
        )
    
    # Update config
    updated_display = {
        "default_time_range": default_time_range,
        "default_limit": default_limit,
        "refresh_rate": refresh_rate,
        "show_token_counts": show_token_counts,
        "compact_mode": compact_mode,
        "chart_theme": chart_theme,
    }
    
    config['display'] = updated_display
    return config


def render_alert_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    """Render alert and notification settings."""
    st.subheader("🔔 Alerts & Notifications")
    
    alert_config = config.get('alerts', {})
    
    alerts_enabled = st.checkbox(
        "Enable Alerts",
        value=alert_config.get('enabled', False),
        help="Enable threshold-based alerts (currently informational only)",
        key="alerts_enabled"
    )
    
    if alerts_enabled:
        st.write("**Alert Thresholds**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            cost_threshold = st.number_input(
                "Daily Cost Threshold ($)",
                min_value=1.0,
                max_value=1000.0,
                value=alert_config.get('cost_threshold_daily', 10.0),
                step=1.0,
                key="cost_threshold"
            )
            
            error_rate_threshold = st.slider(
                "Error Rate Threshold (%)",
                min_value=0.0,
                max_value=1.0,
                value=alert_config.get('error_rate_threshold', 0.10),
                step=0.01,
                format="%.2f",
                key="error_rate_threshold"
            )
        
        with col2:
            latency_threshold = st.number_input(
                "Latency Threshold (ms)",
                min_value=100,
                max_value=30000,
                value=alert_config.get('latency_threshold_ms', 5000),
                step=100,
                key="latency_threshold"
            )
            
            quality_threshold = st.slider(
                "Quality Score Threshold",
                min_value=0.0,
                max_value=10.0,
                value=alert_config.get('quality_score_threshold', 7.0),
                step=0.1,
                key="quality_threshold"
            )
        
        st.info("💡 Alert notifications are not yet implemented. These thresholds are saved for future use.")
    
    # Update config
    updated_alerts = {
        "enabled": alerts_enabled,
        "cost_threshold_daily": cost_threshold if alerts_enabled else alert_config.get('cost_threshold_daily', 10.0),
        "error_rate_threshold": error_rate_threshold if alerts_enabled else alert_config.get('error_rate_threshold', 0.10),
        "latency_threshold_ms": latency_threshold if alerts_enabled else alert_config.get('latency_threshold_ms', 5000),
        "quality_score_threshold": quality_threshold if alerts_enabled else alert_config.get('quality_score_threshold', 7.0),
    }
    
    config['alerts'] = updated_alerts
    return config


def render_performance_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    """Render performance optimization settings."""
    st.subheader("⚡ Performance Settings")
    
    perf_config = config.get('performance', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        cache_results = st.checkbox(
            "Cache Query Results",
            value=perf_config.get('cache_results', True),
            help="Cache database query results for faster page loads",
            key="cache_results"
        )
        
        if cache_results:
            cache_ttl = st.number_input(
                "Cache TTL (seconds)",
                min_value=30,
                max_value=3600,
                value=perf_config.get('result_cache_ttl', 300),
                step=30,
                key="cache_ttl"
            )
        else:
            cache_ttl = perf_config.get('result_cache_ttl', 300)
    
    with col2:
        max_query_limit = st.selectbox(
            "Max Query Limit",
            options=[500, 1000, 2000, 5000],
            index=[500, 1000, 2000, 5000].index(perf_config.get('max_query_limit', 1000)),
            help="Maximum number of records to query at once",
            key="max_query_limit"
        )
        
        enable_optimization = st.checkbox(
            "Enable Query Optimization",
            value=perf_config.get('enable_query_optimization', True),
            help="Use database indexes and optimized queries",
            key="enable_optimization"
        )
    
    # Update config
    updated_performance = {
        "cache_results": cache_results,
        "result_cache_ttl": cache_ttl,
        "max_query_limit": max_query_limit,
        "enable_query_optimization": enable_optimization,
    }
    
    config['performance'] = updated_performance
    return config


def render_export_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    """Render export/import settings."""
    st.subheader("📤 Export & Import Settings")
    
    export_config = config.get('export', {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Export Preferences**")
        
        default_format = st.selectbox(
            "Default Export Format",
            options=["csv", "json", "excel"],
            index=["csv", "json", "excel"].index(export_config.get('default_format', 'csv')),
            key="default_format"
        )
        
        include_metadata = st.checkbox(
            "Include Metadata in Exports",
            value=export_config.get('include_metadata', True),
            key="include_metadata"
        )
        
        compress_exports = st.checkbox(
            "Compress Exports (ZIP)",
            value=export_config.get('compress_exports', False),
            key="compress_exports"
        )
    
    with col2:
        st.write("**Export Actions**")
        
        if st.button("📥 Export All Data", use_container_width=True):
            st.info("Full data export would be generated here")
        
        if st.button("📥 Export Configuration", use_container_width=True):
            config_json = json.dumps(config, indent=2)
            st.download_button(
                "Download Config",
                config_json,
                f"observatory_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "application/json",
                use_container_width=True
            )
        
        if st.button("📤 Import Configuration", use_container_width=True):
            st.info("Configuration import would be handled here")
    
    # Update config
    updated_export = {
        "default_format": default_format,
        "include_metadata": include_metadata,
        "compress_exports": compress_exports,
    }
    
    config['export'] = updated_export
    return config


def render_advanced_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    """Render advanced settings."""
    st.subheader("🔧 Advanced Settings")
    
    adv_config = config.get('advanced', {})
    
    st.warning("⚠️ Advanced settings - modify with caution")
    
    debug_mode = st.checkbox(
        "Debug Mode",
        value=adv_config.get('debug_mode', False),
        help="Enable detailed error messages and logging",
        key="debug_mode"
    )
    
    verbose_logging = st.checkbox(
        "Verbose Logging",
        value=adv_config.get('verbose_logging', False),
        help="Log all database queries and operations",
        key="verbose_logging"
    )
    
    experimental_features = st.checkbox(
        "Enable Experimental Features",
        value=adv_config.get('enable_experimental_features', False),
        help="Access beta features (may be unstable)",
        key="experimental_features"
    )
    
    # Update config
    updated_advanced = {
        "debug_mode": debug_mode,
        "verbose_logging": verbose_logging,
        "enable_experimental_features": experimental_features,
    }
    
    config['advanced'] = updated_advanced
    return config


def render_about_info():
    """Render about and information section."""
    st.subheader("ℹ️ About Observatory")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Version Information**")
        st.code("Observatory Dashboard v1.0.0", language="text")
        st.caption("Built with Streamlit")
        
        st.write("**System Info**")
        st.write(f"Python: 3.11+")
        st.write(f"Database: SQLite")
        st.write(f"Dashboard: Streamlit")
    
    with col2:
        st.write("**Resources**")
        st.markdown("""
        - [📚 Documentation](#)
        - [🐛 Report Bug](#)
        - [💡 Feature Request](#)
        - [💬 Support](#)
        """)
        
        st.write("**Credits**")
        st.caption("AI Agent Observatory")
        st.caption("© 2025 - Production Ready")


def render():
    """Render the Settings page."""
    
    st.title("⚙️ Settings - Configuration & Preferences")
    
    # Get selected project
    selected_project = st.session_state.get('selected_project')
    
    if selected_project:
        st.info(f"📊 Current Project: **{selected_project}**")
    
    st.divider()
    
    # Load current configuration
    config = load_user_config()
    
    # Create tabs for different settings sections
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Projects",
        "Database",
        "Display",
        "Alerts",
        "Performance",
        "Export",
        "Advanced"
    ])
    
    with tab1:
        render_project_management()
    
    with tab2:
        render_database_settings()
    
    with tab3:
        config = render_display_preferences(config)
    
    with tab4:
        config = render_alert_settings(config)
    
    with tab5:
        config = render_performance_settings(config)
    
    with tab6:
        config = render_export_settings(config)
    
    with tab7:
        config = render_advanced_settings(config)
    
    st.divider()
    
    # Save/Reset buttons
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("💾 Save Settings", type="primary", use_container_width=True):
            save_user_config(config)
            st.success("✅ Settings saved successfully!")
            st.rerun()
    
    with col2:
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            default_config = get_default_config()
            save_user_config(default_config)
            st.success("✅ Settings reset to defaults!")
            st.rerun()
    
    st.divider()
    
    # About section
    render_about_info()