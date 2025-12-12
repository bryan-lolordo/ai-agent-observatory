"""
Story Card Component
Location: dashboard/components/story_card.py

Reusable component for rendering optimization story cards.
Each card shows a story summary with drill-down capability.

Usage:
    from dashboard.components.story_card import render_story_card
    
    render_story_card(story_data, on_click_callback)
"""

import streamlit as st
from typing import Dict, Any, Optional, Callable

from dashboard.config.story_definitions import get_story_definition
from dashboard.config.filter_keys import set_story_filter


def render_story_card(
    story: Dict[str, Any],
    show_top_offender: bool = True,
    show_drill_down: bool = True,
) -> Optional[str]:
    """
    Render a single story card.
    
    Args:
        story: Story data from get_story_summary()
        show_top_offender: Whether to show top offender details
        show_drill_down: Whether to show drill-down button
    
    Returns:
        Clicked operation (agent.operation) if drill-down clicked, else None
    """
    story_id = story.get("id")
    definition = get_story_definition(story_id) or {}
    
    has_issues = story.get("has_issues", False)
    icon = story.get("icon", "📊")
    title = story.get("title", "Unknown Story")
    metric = story.get("summary_metric", "—")
    red_flag_count = story.get("red_flag_count", 0)
    top_offender = story.get("top_offender")
    target_page = story.get("target_page", "")
    
    # Colors
    if has_issues:
        border_color = definition.get("color", {}).get("issue", "#FF6B6B")
        status_icon = "🔴"
    else:
        border_color = definition.get("color", {}).get("ok", "#51CF66")
        status_icon = "🟢"
    
    # Card container
    with st.container():
        # Card styling
        st.markdown(f"""
        <div style="
            border: 2px solid {border_color};
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 12px;
            background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 1.4em;">{icon} {title}</span>
                <span>{status_icon}</span>
            </div>
            <div style="font-size: 1.8em; font-weight: bold; margin-bottom: 8px;">
                {metric}
            </div>
            {"<div style='color: #FF6B6B; font-size: 0.9em;'>⚠️ " + str(red_flag_count) + " operations affected</div>" if has_issues and red_flag_count > 0 else ""}
        </div>
        """, unsafe_allow_html=True)
        
        # Top offender details
        if show_top_offender and top_offender and has_issues:
            agent_op = top_offender.get("agent_operation", "")
            with st.expander(f"Top: {agent_op}", expanded=False):
                _render_top_offender_details(story_id, top_offender)
        
        # Drill-down button
        clicked_op = None
        if show_drill_down and has_issues:
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("View →", key=f"drill_{story_id}", width='stretch'):
                    # Set filter and return target
                    if top_offender:
                        set_story_filter(
                            story_id=story_id,
                            agent=top_offender.get("agent"),
                            operation=top_offender.get("operation"),
                        )
                        clicked_op = top_offender.get("agent_operation")
                    else:
                        set_story_filter(story_id=story_id)
                        clicked_op = story_id
            with col1:
                st.caption(f"→ {target_page}")
        
        return clicked_op


def _render_top_offender_details(story_id: str, top_offender: Dict[str, Any]) -> None:
    """Render details for the top offender."""
    
    if story_id == "latency":
        st.markdown(f"""
        | Metric | Value |
        |--------|-------|
        | Agent | `{top_offender.get('agent', '—')}` |
        | Operation | `{top_offender.get('operation', '—')}` |
        | Avg Latency | **{top_offender.get('avg_latency_ms', 0)/1000:.1f}s** |
        | Calls | {top_offender.get('call_count', 0)} |
        | Avg Completion Tokens | {top_offender.get('avg_completion_tokens', 0):,} |
        """)
        if top_offender.get('diagnosis'):
            st.info(f"💡 {top_offender['diagnosis']}")
    
    elif story_id == "cache":
        st.markdown(f"""
        | Metric | Value |
        |--------|-------|
        | Agent | `{top_offender.get('agent', '—')}` |
        | Operation | `{top_offender.get('operation', '—')}` |
        | Total Calls | {top_offender.get('total_calls', 0)} |
        | Unique Prompts | {top_offender.get('unique_prompts', 0)} |
        | Redundancy | **{top_offender.get('redundancy_pct', 0):.0%}** |
        | Wasted Cost | ${top_offender.get('wasted_cost', 0):.4f} |
        """)
    
    elif story_id == "cost":
        st.markdown(f"""
        | Metric | Value |
        |--------|-------|
        | Agent | `{top_offender.get('agent', '—')}` |
        | Operation | `{top_offender.get('operation', '—')}` |
        | Total Cost | **${top_offender.get('total_cost', 0):.4f}** |
        | Cost Share | {top_offender.get('cost_share', 0):.1%} |
        | Calls | {top_offender.get('call_count', 0)} |
        """)
    
    elif story_id == "system_prompt":
        st.markdown(f"""
        | Metric | Value |
        |--------|-------|
        | Agent | `{top_offender.get('agent', '—')}` |
        | Operation | `{top_offender.get('operation', '—')}` |
        | Avg System Tokens | {top_offender.get('avg_system_tokens', 0):,} |
        | System % | **{top_offender.get('system_pct', 0):.0%}** |
        | Redundant Tokens | {top_offender.get('redundant_tokens', 0):,} |
        """)
        if top_offender.get('recommendation'):
            st.info(f"💡 {top_offender['recommendation']}")
    
    elif story_id == "token_imbalance":
        ratio = top_offender.get('ratio', 0)
        ratio_str = f"{ratio:.0f}:1" if ratio < 1000 else "Very high"
        st.markdown(f"""
        | Metric | Value |
        |--------|-------|
        | Agent | `{top_offender.get('agent', '—')}` |
        | Operation | `{top_offender.get('operation', '—')}` |
        | Avg Prompt Tokens | {top_offender.get('avg_prompt_tokens', 0):,} |
        | Avg Completion Tokens | {top_offender.get('avg_completion_tokens', 0):,} |
        | Ratio | **{ratio_str}** |
        """)
        if top_offender.get('diagnosis'):
            st.info(f"💡 {top_offender['diagnosis']}")
    
    elif story_id == "routing":
        complexity = top_offender.get('avg_complexity')
        complexity_str = f"{complexity:.2f}" if complexity else "—"
        st.markdown(f"""
        | Metric | Value |
        |--------|-------|
        | Agent | `{top_offender.get('agent', '—')}` |
        | Operation | `{top_offender.get('operation', '—')}` |
        | Avg Complexity | **{complexity_str}** |
        | Primary Model | `{top_offender.get('primary_model', '—')}` |
        | Calls | {top_offender.get('call_count', 0)} |
        """)
        if top_offender.get('recommendation'):
            st.info(f"💡 {top_offender['recommendation']}")
    
    elif story_id == "quality":
        st.markdown(f"""
        | Metric | Value |
        |--------|-------|
        | Agent | `{top_offender.get('agent', '—')}` |
        | Operation | `{top_offender.get('operation', '—')}` |
        | Error Count | **{top_offender.get('error_count', 0)}** |
        """)
        if top_offender.get('sample_error'):
            st.error(f"Sample: {top_offender['sample_error'][:100]}")
    
    else:
        # Generic display
        for key, value in top_offender.items():
            if key not in ('calls', 'duplicate_groups', 'call'):
                st.text(f"{key}: {value}")


def render_story_cards_grid(
    stories: list,
    columns: int = 2,
) -> Optional[str]:
    """
    Render story cards in a grid layout.
    
    Args:
        stories: List of story data from get_story_summary()
        columns: Number of columns in grid
    
    Returns:
        Clicked story target if any drill-down clicked
    """
    clicked = None
    
    # Create rows of cards
    for i in range(0, len(stories), columns):
        cols = st.columns(columns)
        for j, col in enumerate(cols):
            if i + j < len(stories):
                with col:
                    result = render_story_card(stories[i + j])
                    if result:
                        clicked = result
    
    return clicked


def render_health_summary(stories: list) -> None:
    """
    Render a health summary banner showing overall status.
    
    Args:
        stories: List of story data from get_story_summary()
    """
    issues_count = sum(1 for s in stories if s.get("has_issues"))
    total_count = len(stories)
    ok_count = total_count - issues_count
    
    if issues_count == 0:
        st.success(f"✅ All {total_count} checks passed! Your LLM operations are well optimized.")
    elif issues_count <= 2:
        st.warning(f"⚠️ {issues_count} of {total_count} checks need attention. {ok_count} checks passed.")
    else:
        st.error(f"🔴 {issues_count} of {total_count} checks flagged issues. Review recommended.")
    
    # Quick stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Issues Found", issues_count, delta=None)
    with col2:
        st.metric("Checks Passed", ok_count, delta=None)
    with col3:
        health_pct = (ok_count / total_count * 100) if total_count > 0 else 0
        st.metric("Health Score", f"{health_pct:.0f}%", delta=None)