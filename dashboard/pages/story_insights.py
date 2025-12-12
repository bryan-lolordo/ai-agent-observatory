"""
Story Insights Dashboard
Location: dashboard/pages/story_insights.py

Main entry point for story-driven optimization dashboard.
Shows 7 optimization stories with drill-down capability.

Stories:
1. 🐌 Latency Monster - Slow operations
2. 💾 Zero Cache Hits - Caching opportunities
3. 💰 Cost Concentration - Where money goes
4. 📝 System Prompt Waste - Redundant tokens
5. ⚖️ Token Imbalance - Poor ratios
6. 🔀 Model Routing - Complexity mismatches
7. ❌ Quality Issues - Errors and hallucinations
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional

from dashboard.utils.data_fetcher import (
    get_llm_calls,
    get_available_projects,
)
from dashboard.utils.story_analyzer import (
    get_story_summary,
    analyze_all_stories,
)
from dashboard.components.story_card import (
    render_story_cards_grid,
    render_health_summary,
    render_story_card,
)
from dashboard.config.story_definitions import (
    STORY_DEFINITIONS,
    get_story_recommendations,
)
from dashboard.config.filter_keys import (
    get_story_filter,
    clear_story_filter,
    has_active_story_filter,
)


def render_page():
    """Main page render function."""
    
    st.title("📊 Story Insights")
    st.caption("Data-driven optimization stories from your LLM operations")
    
    # Sidebar filters
    _render_sidebar_filters()
    
    # Get filter values
    project = st.session_state.get("story_project_filter")
    time_range = st.session_state.get("story_time_filter", "7d")
    
    # Calculate time range
    end_time = datetime.utcnow()
    if time_range == "1h":
        start_time = end_time - timedelta(hours=1)
    elif time_range == "24h":
        start_time = end_time - timedelta(hours=24)
    elif time_range == "7d":
        start_time = end_time - timedelta(days=7)
    elif time_range == "30d":
        start_time = end_time - timedelta(days=30)
    else:
        start_time = None
    
    # Load data
    with st.spinner("Analyzing LLM operations..."):
        calls = get_llm_calls(
            project_name=project if project != "All Projects" else None,
            start_time=start_time,
            end_time=end_time,
            limit=2000,
        )
    
    if not calls:
        st.warning("No LLM calls found for the selected filters.")
        st.info("Run some operations with Observatory tracking to see insights here.")
        return
    
    # Show data summary
    st.markdown(f"**Analyzing {len(calls):,} calls** from {time_range} window")
    
    # Get stories
    stories = get_story_summary(calls)
    
    # Health summary banner
    st.markdown("---")
    render_health_summary(stories)
    st.markdown("---")
    
    # View mode toggle
    view_mode = st.radio(
        "View",
        ["Cards", "Table", "Detail"],
        horizontal=True,
        label_visibility="collapsed",
    )
    
    if view_mode == "Cards":
        _render_cards_view(stories)
    elif view_mode == "Table":
        _render_table_view(stories)
    else:
        _render_detail_view(stories, calls)


def _render_sidebar_filters():
    """Render sidebar filters."""
    with st.sidebar:
        st.subheader("📊 Story Filters")
        
        # Project filter
        projects = ["All Projects"] + get_available_projects()
        st.selectbox(
            "Project",
            projects,
            key="story_project_filter",
        )
        
        # Time range filter
        st.selectbox(
            "Time Range",
            ["1h", "24h", "7d", "30d"],
            index=2,
            key="story_time_filter",
        )
        
        st.markdown("---")
        
        # Clear filters button
        if has_active_story_filter():
            if st.button("🔄 Clear Story Filter", width='stretch'):
                clear_story_filter()
                st.rerun()
            
            ctx = get_story_filter()
            if ctx.story_source:
                st.info(f"Active filter: {ctx.get_banner_text()}")


def _render_cards_view(stories: list):
    """Render stories as cards in a grid."""
    st.subheader("Optimization Stories")
    
    # Separate issues from passed
    issues = [s for s in stories if s.get("has_issues")]
    passed = [s for s in stories if not s.get("has_issues")]
    
    if issues:
        st.markdown("### 🔴 Needs Attention")
        render_story_cards_grid(issues, columns=2)
    
    if passed:
        st.markdown("### 🟢 Looking Good")
        render_story_cards_grid(passed, columns=3)


def _render_table_view(stories: list):
    """Render stories as a summary table."""
    st.subheader("Story Summary Table")
    
    # Build table data
    table_data = []
    for story in stories:
        status = "🔴" if story.get("has_issues") else "🟢"
        top_op = story.get("top_offender", {})
        top_op_str = top_op.get("agent_operation", "—") if top_op else "—"
        
        table_data.append({
            "Status": status,
            "Story": f"{story.get('icon', '')} {story.get('title', '')}",
            "Metric": story.get("summary_metric", "—"),
            "Flags": story.get("red_flag_count", 0),
            "Top Offender": top_op_str,
            "Target Page": story.get("target_page", "—"),
        })
    
    st.dataframe(
        table_data,
        width='stretch',
        hide_index=True,
        column_config={
            "Status": st.column_config.TextColumn("", width="small"),
            "Story": st.column_config.TextColumn("Story", width="medium"),
            "Metric": st.column_config.TextColumn("Metric", width="small"),
            "Flags": st.column_config.NumberColumn("Flags", width="small"),
            "Top Offender": st.column_config.TextColumn("Top Offender", width="medium"),
            "Target Page": st.column_config.TextColumn("Target", width="medium"),
        },
    )


def _render_detail_view(stories: list, calls: list):
    """Render detailed view with full analysis."""
    st.subheader("Detailed Analysis")
    
    # Get full analysis
    all_stories = analyze_all_stories(calls)
    
    # Story selector
    story_options = [f"{s.get('icon', '')} {s.get('title', '')}" for s in stories]
    story_ids = [s.get("id") for s in stories]
    
    selected_idx = st.selectbox(
        "Select Story",
        range(len(story_options)),
        format_func=lambda i: story_options[i],
    )
    
    selected_id = story_ids[selected_idx]
    story_data = all_stories.get(selected_id, {})
    story_summary = stories[selected_idx]
    
    # Show story details
    col1, col2 = st.columns([2, 1])
    
    with col1:
        render_story_card(story_summary, show_drill_down=True)
    
    with col2:
        # Recommendations
        st.markdown("#### 💡 Recommendations")
        recommendations = get_story_recommendations(selected_id)
        for rec in recommendations[:3]:
            st.markdown(f"• {rec}")
    
    # Affected operations table
    affected = story_data.get("affected_operations", [])
    if affected:
        st.markdown("#### Affected Operations")
        st.dataframe(affected, width='stretch', hide_index=True)
    
    # Detail table
    detail_table = story_data.get("detail_table", [])
    if detail_table:
        with st.expander("📋 Full Detail Table", expanded=False):
            # Filter out nested objects for display
            display_data = []
            for row in detail_table[:20]:
                filtered_row = {
                    k: v for k, v in row.items()
                    if k not in ('calls', 'duplicate_groups', 'errors')
                    and not isinstance(v, (list, dict))
                }
                display_data.append(filtered_row)
            
            if display_data:
                st.dataframe(display_data, width='stretch', hide_index=True)


# Entry point for Streamlit pages
if __name__ == "__main__":
    render_page()