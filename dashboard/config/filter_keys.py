"""
Filter Keys - Standardized Filter Key Names
Location: dashboard/config/filter_keys.py

Defines standardized session state keys for story-to-page filtering.
Ensures consistent filter passing between story cards and drill-down pages.

Usage:
    from dashboard.config.filter_keys import FilterKeys
    
    # In story card (setting filter):
    st.session_state[FilterKeys.AGENT] = "ResumeMatching"
    st.session_state[FilterKeys.OPERATION] = "deep_analyze_job"
    st.session_state[FilterKeys.STORY_SOURCE] = "latency"
    
    # In drill-down page (reading filter):
    agent = st.session_state.get(FilterKeys.AGENT)
    operation = st.session_state.get(FilterKeys.OPERATION)
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass


# =============================================================================
# FILTER KEY CONSTANTS
# =============================================================================

class FilterKeys:
    """Standardized session state keys for filtering."""
    
    # Core filters
    AGENT = "story_filter_agent"
    OPERATION = "story_filter_operation"
    MODEL = "story_filter_model"
    
    # Story context
    STORY_SOURCE = "story_source"
    STORY_ID = "story_id"
    
    # Time filters
    START_TIME = "story_filter_start_time"
    END_TIME = "story_filter_end_time"
    
    # Specific story filters
    LATENCY_THRESHOLD = "story_filter_latency_threshold"
    CACHE_OPERATION = "story_filter_cache_operation"
    COST_THRESHOLD = "story_filter_cost_threshold"
    COMPLEXITY_THRESHOLD = "story_filter_complexity_threshold"
    QUALITY_THRESHOLD = "story_filter_quality_threshold"
    
    # Navigation
    RETURN_PAGE = "story_return_page"
    DRILL_DOWN_DATA = "story_drill_down_data"


# =============================================================================
# FILTER CONTEXT
# =============================================================================

@dataclass
class StoryFilterContext:
    """
    Context object for passing filter state between pages.
    
    Usage:
        # Create context
        ctx = StoryFilterContext(
            story_id="latency",
            agent="ResumeMatching",
            operation="deep_analyze_job"
        )
        
        # Store in session
        ctx.to_session_state()
        
        # Read from session
        ctx = StoryFilterContext.from_session_state()
    """
    story_id: Optional[str] = None
    story_source: Optional[str] = None
    agent: Optional[str] = None
    operation: Optional[str] = None
    model: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    
    def to_session_state(self) -> None:
        """Store filter context in Streamlit session state."""
        import streamlit as st
        
        if self.story_id:
            st.session_state[FilterKeys.STORY_ID] = self.story_id
        if self.story_source:
            st.session_state[FilterKeys.STORY_SOURCE] = self.story_source
        if self.agent:
            st.session_state[FilterKeys.AGENT] = self.agent
        if self.operation:
            st.session_state[FilterKeys.OPERATION] = self.operation
        if self.model:
            st.session_state[FilterKeys.MODEL] = self.model
        if self.start_time:
            st.session_state[FilterKeys.START_TIME] = self.start_time
        if self.end_time:
            st.session_state[FilterKeys.END_TIME] = self.end_time
        if self.extra_data:
            st.session_state[FilterKeys.DRILL_DOWN_DATA] = self.extra_data
    
    @classmethod
    def from_session_state(cls) -> "StoryFilterContext":
        """Read filter context from Streamlit session state."""
        import streamlit as st
        
        return cls(
            story_id=st.session_state.get(FilterKeys.STORY_ID),
            story_source=st.session_state.get(FilterKeys.STORY_SOURCE),
            agent=st.session_state.get(FilterKeys.AGENT),
            operation=st.session_state.get(FilterKeys.OPERATION),
            model=st.session_state.get(FilterKeys.MODEL),
            start_time=st.session_state.get(FilterKeys.START_TIME),
            end_time=st.session_state.get(FilterKeys.END_TIME),
            extra_data=st.session_state.get(FilterKeys.DRILL_DOWN_DATA),
        )
    
    @classmethod
    def clear_session_state(cls) -> None:
        """Clear all filter keys from session state."""
        import streamlit as st
        
        keys_to_clear = [
            FilterKeys.STORY_ID,
            FilterKeys.STORY_SOURCE,
            FilterKeys.AGENT,
            FilterKeys.OPERATION,
            FilterKeys.MODEL,
            FilterKeys.START_TIME,
            FilterKeys.END_TIME,
            FilterKeys.DRILL_DOWN_DATA,
            FilterKeys.RETURN_PAGE,
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    def has_filters(self) -> bool:
        """Check if any filters are set."""
        return any([
            self.agent,
            self.operation,
            self.model,
            self.start_time,
            self.end_time,
        ])
    
    def get_banner_text(self) -> Optional[str]:
        """Get banner text describing active filter."""
        if not self.story_source:
            return None
        
        story_titles = {
            "latency": "Latency Monster",
            "cache": "Zero Cache Hits",
            "cost": "Cost Concentration",
            "system_prompt": "System Prompt Waste",
            "token_imbalance": "Token Imbalance",
            "routing": "Model Routing",
            "quality": "Quality Issues",
        }
        
        title = story_titles.get(self.story_source, self.story_source)
        
        if self.operation:
            return f"From Story: {title} → {self.agent}.{self.operation}"
        elif self.agent:
            return f"From Story: {title} → {self.agent}"
        else:
            return f"From Story: {title}"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def set_story_filter(
    story_id: str,
    agent: Optional[str] = None,
    operation: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Set story filter in session state.
    
    Args:
        story_id: Story identifier (e.g., "latency", "cache")
        agent: Agent name to filter by
        operation: Operation name to filter by
        extra_data: Additional data for drill-down
    """
    ctx = StoryFilterContext(
        story_id=story_id,
        story_source=story_id,
        agent=agent,
        operation=operation,
        extra_data=extra_data,
    )
    ctx.to_session_state()


def get_story_filter() -> StoryFilterContext:
    """
    Get current story filter from session state.
    
    Returns:
        StoryFilterContext with current filter values
    """
    return StoryFilterContext.from_session_state()


def clear_story_filter() -> None:
    """Clear all story filters from session state."""
    StoryFilterContext.clear_session_state()


def has_active_story_filter() -> bool:
    """Check if there's an active story filter."""
    ctx = StoryFilterContext.from_session_state()
    return ctx.story_source is not None