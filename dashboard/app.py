"""
AI Agent Observatory Dashboard - Main Application
Location: dashboard/app.py

Multi-page Streamlit dashboard for monitoring and optimizing AI agents.
"""
from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import sys
import os
from pathlib import Path

# Add parent directory to path for observatory imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import Observatory for self-monitoring
from observatory import Observatory

# Import from our utilities
from dashboard.utils.data_fetcher import get_storage, get_available_projects

# Initialize self-monitoring for the Observatory system
obs_system = Observatory(
    project_name="Observatory-System",
)

# Page configuration
st.set_page_config(
    page_title="AI Agent Observatory",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-box {
        background: #fff3cd;
        border: 1px solid #ffc107;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .project-selector {
        background: #f0f8ff;
        padding: 1rem;
        border-radius: 8px;
        border: 2px solid #1f77b4;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar - Project Selector
st.sidebar.title("🔭 Observatory")
st.sidebar.markdown("---")

# Get available projects
try:
    available_projects = get_available_projects()
    
    if available_projects:
        # Add "All Projects" option
        project_options = ["All Projects"] + available_projects
        
        # Project selector with custom styling
        selected_project = st.sidebar.selectbox(
            "🎯 Select Project",
            options=project_options,
            index=0,
            help="Filter metrics by project. Select 'All Projects' to see aggregated data."
        )
        
        # Store in session state for access across pages
        st.session_state['selected_project'] = None if selected_project == "All Projects" else selected_project
        
    else:
        st.sidebar.warning("⚠️ No projects found in database")
        st.session_state['selected_project'] = None
        
except Exception as e:
    st.sidebar.error(f"❌ Error loading projects: {str(e)}")
    st.session_state['selected_project'] = None

st.sidebar.markdown("---")

# Navigation
page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Home",
        "📊 Live Demo",
        "💰 Cost Estimator",
        "🔀 Model Router",
        "💾 Cache Analyzer",
        "⚖️ LLM Judge",
        "✨ Prompt Optimizer",
        "⚙️ Settings"
    ]
)

# System status in sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("System Status")

try:
    storage = get_storage()
    
    # Get sessions filtered by selected project
    selected_project = st.session_state.get('selected_project')
    sessions = storage.get_sessions(
        project_name=selected_project,
        limit=1
    )
    
    st.sidebar.success("✅ Observatory Active")
    
    # Show project count
    if available_projects:
        st.sidebar.metric("Projects Tracked", len(available_projects))
    
except Exception as e:
    st.sidebar.error("❌ Connection Issue")
    st.sidebar.caption(f"Error: {str(e)}")

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("AI Agent Observatory v1.0")
st.sidebar.caption("Built with Streamlit")

# Page routing
if page == "🏠 Home":
    from dashboard.pages import home
    home.render()
elif page == "📊 Live Demo":
    from dashboard.pages import live_demo
    live_demo.render()
elif page == "💰 Cost Estimator":
    from dashboard.pages import cost_estimator
    cost_estimator.render()
elif page == "🔀 Model Router":
    from dashboard.pages import model_router
    model_router.render()
elif page == "💾 Cache Analyzer":
    from dashboard.pages import cache_analyzer
    cache_analyzer.render()
elif page == "⚖️ LLM Judge":
    from dashboard.pages import llm_judge
    llm_judge.render()
elif page == "✨ Prompt Optimizer":
    from dashboard.pages import prompt_optimizer
    prompt_optimizer.render()
elif page == "⚙️ Settings":
    from dashboard.pages import settings
    settings.render()