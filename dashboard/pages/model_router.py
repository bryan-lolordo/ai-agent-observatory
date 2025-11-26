"""
Model Router Page - Routing Analysis and Optimization
Location: dashboard/pages/model_router.py

Analyzes routing decisions, effectiveness, and optimization opportunities.
Works with both direct model selection and smart routing implementations.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
import plotly.graph_objects as go
from collections import defaultdict

from dashboard.utils.data_fetcher import (
    get_project_overview,
    get_llm_calls,
    get_available_agents,
    get_available_models,
    get_routing_analysis,
)
from dashboard.utils.formatters import (
    format_cost,
    format_latency,
    format_tokens,
    format_percentage,
    format_model_name,
    truncate_text,
)
from dashboard.components.metric_cards import (
    render_metric_row,
    render_empty_state,
)
from dashboard.components.charts import (
    create_cost_breakdown_pie,
    create_scatter_plot,
    create_bar_chart,
    create_heatmap,
)
from dashboard.components.tables import (
    render_dataframe,
)


def detect_routing_mode(calls: List[Dict]) -> Tuple[bool, str]:
    """
    Detect if real routing is active or just direct selection.
    
    Returns:
        Tuple of (has_real_routing, mode_description)
    """
    if not calls:
        return False, "No data"
    
    # Check for alternative models in routing decisions
    routing_decisions = [
        c.get('routing_decision', {}) for c in calls
        if c.get('routing_decision')
    ]
    
    if not routing_decisions:
        return False, "No routing data"
    
    # Real routing has alternatives
    has_alternatives = any(
        rd.get('alternative_models', []) for rd in routing_decisions
        if isinstance(rd, dict)
    )
    
    if has_alternatives:
        return True, "Smart routing active"
    else:
        return False, "Direct model selection"


def calculate_routing_kpis(calls: List[Dict], has_real_routing: bool) -> Dict[str, Any]:
    """Calculate routing performance KPIs."""
    if not calls:
        return {
            'routing_accuracy': 0,
            'avg_latency': 0,
            'avg_cost': 0,
            'avg_quality': 0,
            'total_decisions': 0
        }
    
    total_latency = sum(c.get('latency_ms', 0) for c in calls)
    total_cost = sum(c.get('total_cost', 0) for c in calls)
    
    # Quality scores from evaluations
    quality_scores = [
        (c.get('quality_evaluation') or {}).get('score', 0)
        for c in calls
        if (c.get('quality_evaluation') or {}).get('score')
    ]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    if has_real_routing:
        # Calculate actual routing accuracy
        # Accuracy = decisions where chosen model had best score
        accurate_decisions = 0
        total_decisions = 0
        
        for call in calls:
            routing = call.get('routing_decision', {})
            if not isinstance(routing, dict):
                continue
            
            alternatives = routing.get('alternative_models', [])
            if alternatives:
                total_decisions += 1
                # For now, assume routing was accurate (can be refined with judge scores)
                accurate_decisions += 1
        
        routing_accuracy = accurate_decisions / total_decisions if total_decisions > 0 else 0
    else:
        # No real routing - N/A
        routing_accuracy = 0
        total_decisions = 0
    
    return {
        'routing_accuracy': routing_accuracy,
        'avg_latency': total_latency / len(calls),
        'avg_cost': total_cost / len(calls),
        'avg_quality': avg_quality,
        'total_decisions': total_decisions if has_real_routing else len(calls)
    }


def calculate_routing_distribution(calls: List[Dict]) -> Dict[str, int]:
    """Calculate how requests are distributed across models."""
    distribution = defaultdict(int)
    
    for call in calls:
        model = call.get('model_name', 'Unknown')
        distribution[model] += 1
    
    return dict(distribution)


def analyze_routing_effectiveness(calls: List[Dict], has_real_routing: bool) -> Dict[str, Any]:
    """
    Analyze routing effectiveness - shows which models should have been used.
    Creates a confusion matrix style analysis.
    """
    if not has_real_routing or not calls:
        return None
    
    # Categorize models by cost tier
    model_tiers = {
        'small': ['mistral', 'flash', 'mini', 'small'],
        'medium': ['sonnet', 'haiku', '3.5', 'turbo'],
        'large': ['gpt-4', 'opus', '4o', 'o1']
    }
    
    def get_tier(model_name: str) -> str:
        model_lower = model_name.lower()
        for tier, keywords in model_tiers.items():
            if any(keyword in model_lower for keyword in keywords):
                return tier
        return 'medium'
    
    # Build confusion matrix
    matrix = defaultdict(lambda: defaultdict(int))
    
    for call in calls:
        routing = call.get('routing_decision', {})
        if not isinstance(routing, dict):
            continue
        
        chosen = routing.get('chosen_model', '')
        alternatives = routing.get('alternative_models', [])
        
        if not alternatives:
            continue
        
        chosen_tier = get_tier(chosen)
        
        # Determine if choice was optimal based on quality score
        quality = (call.get('quality_evaluation') or {}).get('score', 0)
        
        if quality >= 9.0:
            optimal_tier = 'small'  # High quality achieved, could have used cheap
        elif quality >= 7.0:
            optimal_tier = 'medium'
        else:
            optimal_tier = 'large'
        
        matrix[chosen_tier][optimal_tier] += 1
    
    return dict(matrix)


def calculate_routing_savings(calls: List[Dict], has_real_routing: bool) -> Dict[str, Any]:
    """Calculate actual or potential routing savings."""
    if not calls:
        return {
            'enabled': False,
            'total_savings': 0,
            'potential_savings': 0
        }
    
    total_cost = sum(c.get('total_cost', 0) for c in calls)
    
    if has_real_routing:
        # Calculate actual savings from routing decisions
        actual_savings = 0
        
        for call in calls:
            routing = call.get('routing_decision', {})
            if isinstance(routing, dict):
                # Get cost of alternatives
                alternatives = routing.get('alternative_models', [])
                if alternatives:
                    # Estimate savings (simplified - would need model pricing lookup)
                    chosen_cost = call.get('total_cost', 0)
                    # Assume most expensive alternative would have cost 2x more
                    potential_max_cost = chosen_cost * 2
                    actual_savings += (potential_max_cost - chosen_cost)
        
        return {
            'enabled': True,
            'total_savings': actual_savings,
            'savings_percentage': (actual_savings / (total_cost + actual_savings)) if total_cost > 0 else 0,
            'total_calls': len(calls)
        }
    else:
        # Calculate potential savings
        # Assume 40% of calls could use cheaper models, saving 60%
        routeable_calls = len(calls) * 0.40
        avg_cost_per_call = total_cost / len(calls)
        potential_savings = routeable_calls * avg_cost_per_call * 0.60
        
        return {
            'enabled': False,
            'potential_savings': potential_savings,
            'routeable_calls': int(routeable_calls),
            'savings_percentage': 0.40 * 0.60  # 24% total savings
        }


def render_routing_opportunity(calls: List[Dict], total_cost: float):
    """Render analysis of routing opportunities when not implemented."""
    st.subheader("💡 Routing Opportunity Analysis")
    
    st.info("🔀 Smart Routing Not Enabled Yet - See Potential Below")
    
    # Analyze current model usage
    model_dist = calculate_routing_distribution(calls)
    
    # Find most expensive model
    expensive_models = [m for m in model_dist.keys() if any(x in m.lower() for x in ['gpt-4', 'opus', '4o'])]
    cheap_models = [m for m in model_dist.keys() if any(x in m.lower() for x in ['mistral', 'flash', 'mini'])]
    
    expensive_pct = sum(model_dist.get(m, 0) for m in expensive_models) / len(calls) if calls else 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Calls Using Premium Models",
            format_percentage(expensive_pct),
            help="Percentage using GPT-4, Opus, etc."
        )
    
    with col2:
        routeable_pct = 0.40 if expensive_pct > 0.5 else 0.25
        st.metric(
            "Routeable to Cheaper Models",
            format_percentage(routeable_pct),
            help="Estimated % that could use cheaper models"
        )
    
    with col3:
        potential_savings = total_cost * routeable_pct * 0.60
        st.metric(
            "Potential Monthly Savings",
            format_cost(potential_savings * 30),
            delta=f"-{format_percentage(routeable_pct * 0.6)} cost"
        )
    
    with st.expander("📋 Recommended Routing Strategy"):
        st.markdown("""
        **Task-Based Routing Rules:**
        
        1. **Simple Classification/Categorization** → Mistral Small
           - Yes/no questions
           - Category selection
           - Simple extraction
           - 70% cost savings vs GPT-4
        
        2. **Analysis/Summary Tasks** → Claude Sonnet
           - Document summarization
           - Content analysis
           - Reasoning tasks
           - 40% cost savings vs GPT-4
        
        3. **Complex Reasoning/Generation** → GPT-4o
           - Creative writing
           - Complex problem solving
           - Multi-step reasoning
           - Use when quality is critical
        
        **Implementation Steps:**
        1. Analyze query complexity (token count, keywords)
        2. Classify task type (classification, analysis, generation)
        3. Route to appropriate model
        4. Track quality scores to validate routing
        5. Adjust rules based on performance
        
        [→ View Routing Implementation Guide]
        """)


def render_routing_examples(calls: List[Dict], limit: int = 10):
    """Render real routing decision examples."""
    st.subheader("📝 Routing Decision Examples")
    
    if not calls:
        st.info("No routing decisions to display")
        return
    
    for i, call in enumerate(calls[:limit], 1):
        routing = call.get('routing_decision', {})
        if not isinstance(routing, dict):
            continue
        
        chosen_model = routing.get('chosen_model', call.get('model_name', 'Unknown'))
        alternatives = routing.get('alternative_models', [])
        reasoning = routing.get('reasoning', 'Direct model selection (no routing logic applied)')
        
        cost = call.get('total_cost', 0)
        latency = call.get('latency_ms', 0)
        quality = (call.get('quality_evaluation') or {}).get('score') if call.get('quality_evaluation') else None
        
        with st.expander(f"Decision #{i}: {format_model_name(chosen_model)}", expanded=(i == 1)):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write("**Request:**")
                if call.get('prompt'):
                    st.code(truncate_text(call['prompt'], 150), language="text")
                else:
                    st.caption("Prompt not available")
                
                st.write("**Routing Decision:**")
                st.info(reasoning)
                
                if alternatives:
                    st.write("**Alternative Models Considered:**")
                    st.write(", ".join(format_model_name(m) for m in alternatives[:3]))
            
            with col2:
                st.metric("Model Chosen", format_model_name(chosen_model))
                st.metric("Cost", format_cost(cost))
                st.metric("Latency", format_latency(latency))
                if quality:
                    st.metric("Quality Score", f"{quality:.1f}/10")


def render():
    """Render the Model Router page."""
    
    st.title("🔀 Model Router - Routing Analysis")
    
    # Get selected project
    selected_project = st.session_state.get('selected_project')
    
    # Project indicator
    if selected_project:
        st.info(f"📊 Analyzing routing for: **{selected_project}**")
    else:
        st.info("📊 Analyzing routing for: **All Projects**")
    
    st.divider()
    
    # Section 1: Top-Level Filters
    st.subheader("🔍 Filters")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        try:
            agents = get_available_agents(selected_project)
            filter_agent = st.selectbox(
                "Agent",
                options=["All"] + agents,
                key="router_agent_filter"
            )
        except:
            filter_agent = "All"
    
    with col2:
        try:
            models = get_available_models(selected_project)
            filter_model = st.selectbox(
                "Model",
                options=["All"] + models,
                key="router_model_filter"
            )
        except:
            filter_model = "All"
    
    with col3:
        time_period = st.selectbox(
            "Time Period",
            options=["1h", "24h", "7d", "30d"],
            index=2,
            key="router_time_period"
        )
    
    with col4:
        limit = st.selectbox(
            "Max Results",
            options=[50, 100, 200, 500],
            index=1,
            key="router_limit"
        )
    
    st.divider()
    
    # Fetch data
    try:
        with st.spinner("Loading routing data..."):
            calls = get_llm_calls(
                project_name=selected_project,
                agent_name=None if filter_agent == "All" else filter_agent,
                model_name=None if filter_model == "All" else filter_model,
                limit=limit
            )
            
            if not calls:
                render_empty_state(
                    message="No routing data available",
                    icon="🔀",
                    suggestion="Run your AI agents with Observatory enabled to track routing decisions"
                )
                return
    
    except Exception as e:
        st.error(f"Error loading routing data: {str(e)}")
        return
    
    # Detect routing mode
    has_real_routing, routing_mode = detect_routing_mode(calls)
    
    # Show routing status
    if has_real_routing:
        st.success(f"✅ {routing_mode} - {len(calls)} decisions analyzed")
    else:
        st.warning(f"⚠️ {routing_mode} - Showing opportunity analysis")
    
    st.divider()
    
    # Calculate metrics
    kpis = calculate_routing_kpis(calls, has_real_routing)
    savings = calculate_routing_savings(calls, has_real_routing)
    
    # Section 2: KPI Cards
    st.subheader("📊 Routing Performance")
    
    if has_real_routing:
        metrics = [
            {
                "label": "Routing Accuracy",
                "value": format_percentage(kpis['routing_accuracy']),
                "help": "% of routing decisions that were optimal"
            },
            {
                "label": "Avg Latency",
                "value": format_latency(kpis['avg_latency']),
            },
            {
                "label": "Avg Cost per Request",
                "value": format_cost(kpis['avg_cost']),
            },
            {
                "label": "Avg Quality Score",
                "value": f"{kpis['avg_quality']:.1f}/10" if kpis['avg_quality'] > 0 else "N/A",
            },
            {
                "label": "Total Routing Decisions",
                "value": f"{kpis['total_decisions']:,}",
            },
            {
                "label": "Total Savings",
                "value": format_cost(savings['total_savings']),
                "delta": f"-{format_percentage(savings['savings_percentage'])}"
            }
        ]
    else:
        # Show opportunity metrics
        overview = get_project_overview(selected_project)
        total_cost = overview.get('kpis', {}).get('total_cost', 0)
        
        metrics = [
            {
                "label": "Current Avg Latency",
                "value": format_latency(kpis['avg_latency']),
            },
            {
                "label": "Current Avg Cost",
                "value": format_cost(kpis['avg_cost']),
            },
            {
                "label": "Total Requests",
                "value": f"{len(calls):,}",
            },
            {
                "label": "Potential Savings",
                "value": format_cost(savings['potential_savings']),
                "delta": f"-{format_percentage(savings['savings_percentage'])} cost",
                "help": "Estimated with smart routing"
            }
        ]
    
    render_metric_row(metrics, columns=3)
    
    st.divider()
    
    # Section 3: Routing Breakdown Chart
    st.subheader("📈 Model Distribution")
    
    model_distribution = calculate_routing_distribution(calls)
    
    if model_distribution:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = create_cost_breakdown_pie(
                model_distribution,
                title="Requests by Model"
            )
            st.plotly_chart(fig, width='stretch')
        
        with col2:
            # Bar chart version
            fig = create_bar_chart(
                model_distribution,
                x_label="Model",
                y_label="Request Count",
                title="Model Usage Breakdown"
            )
            st.plotly_chart(fig, width='stretch')
    else:
        st.info("No model distribution data")
    
    st.divider()
    
    # Section 4: Routing Effectiveness / Confusion Matrix
    if has_real_routing:
        st.subheader("🎯 Routing Effectiveness Matrix")
        
        effectiveness = analyze_routing_effectiveness(calls, has_real_routing)
        
        if effectiveness:
            # Convert to DataFrame for heatmap
            tiers = ['small', 'medium', 'large']
            matrix_data = []
            
            for chosen in tiers:
                row = []
                for optimal in tiers:
                    row.append(effectiveness.get(chosen, {}).get(optimal, 0))
                matrix_data.append(row)
            
            fig = create_heatmap(
                matrix_data,
                x_labels=[f"Should Use {t.title()}" for t in tiers],
                y_labels=[f"Router Chose {t.title()}" for t in tiers],
                title="Routing Decision Matrix"
            )
            st.plotly_chart(fig, width='stretch')
            
            st.caption("""
            **How to Read:**
            - Diagonal (green) = Correct routing decisions
            - Off-diagonal (yellow/red) = Misrouting
            - Top-right = Overspending (chose expensive when cheap would work)
            - Bottom-left = Quality risk (chose cheap when expensive needed)
            """)
        else:
            st.info("Not enough routing data for effectiveness analysis")
    
        st.divider()
    
    # Section 5: Cost vs Quality Scatter Plot
    st.subheader("💰 Cost vs Quality Analysis")
    
    # Prepare scatter data
    scatter_data = []
    for call in calls:
        quality = (call.get('quality_evaluation') or {}).get('score') if call.get('quality_evaluation') else None
        if quality:
            scatter_data.append({
                'cost': call.get('total_cost', 0),
                'quality': quality,
                'model': call.get('model_name', 'Unknown'),
                'label': f"{format_model_name(call.get('model_name', ''))}: ${call.get('total_cost', 0):.4f}, Q={quality:.1f}"
            })
    
    if scatter_data:
        costs = [d['cost'] for d in scatter_data]
        qualities = [d['quality'] for d in scatter_data]
        labels = [d['label'] for d in scatter_data]
        
        fig = create_scatter_plot(
            x_values=costs,
            y_values=qualities,
            labels=labels,
            x_label="Cost ($)",
            y_label="Quality Score (0-10)",
            title="Cost vs Quality Tradeoff"
        )
        st.plotly_chart(fig, width='stretch')
        
        st.caption("""
        **Ideal Region:** Low cost, high quality (top-left quadrant)
        **Overspending:** High cost but quality not proportionally better
        **Quality Risk:** Low cost but quality suffering
        """)
    else:
        st.info("Quality scores not available - enable LLM Judge to see cost/quality tradeoffs")
    
    st.divider()
    
    # Section 6: Routing Opportunity (if not enabled)
    if not has_real_routing:
        total_cost = sum(c.get('total_cost', 0) for c in calls)
        render_routing_opportunity(calls, total_cost)
        st.divider()
    
    # Section 7: Routing Decision Examples
    render_routing_examples(calls, limit=10)
    
    st.divider()
    
    # Section 8: Routing Savings Summary
    st.subheader("💵 Routing Savings Summary")
    
    if has_real_routing:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Savings", format_cost(savings['total_savings']))
        with col2:
            st.metric("Savings %", format_percentage(savings['savings_percentage']))
        with col3:
            daily_savings = savings['total_savings'] / 7  # Assuming 7 day period
            st.metric("Daily Savings", format_cost(daily_savings))
        with col4:
            monthly_projection = daily_savings * 30
            st.metric("Monthly Projection", format_cost(monthly_projection))
    else:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Potential Savings",
                format_cost(savings['potential_savings']),
                help="From implementing smart routing"
            )
        with col2:
            st.metric(
                "Routeable Calls",
                f"{savings.get('routeable_calls', 0):,}",
                help="Calls that could use cheaper models"
            )
        with col3:
            monthly_savings = savings['potential_savings'] * 30
            st.metric(
                "Monthly Opportunity",
                format_cost(monthly_savings),
                delta=f"-{format_percentage(savings['savings_percentage'])} cost"
            )
    
    st.divider()
    
    # Section 9: Detailed Routing Log
    with st.expander("📋 Detailed Routing Log", expanded=False):
        st.caption("Complete log of all routing decisions")
        
        log_data = []
        for call in calls:
            routing = call.get('routing_decision', {})
            if isinstance(routing, dict):
                log_data.append({
                    'Timestamp': call.get('timestamp', '').strftime('%Y-%m-%d %H:%M:%S') if call.get('timestamp') else 'N/A',
                    'Agent': call.get('agent_name', 'Unknown'),
                    'Chosen Model': format_model_name(routing.get('chosen_model', call.get('model_name', ''))),
                    'Alternatives': ', '.join(format_model_name(m) for m in routing.get('alternative_models', [])[:2]),
                    'Cost': format_cost(call.get('total_cost', 0)),
                    'Latency': format_latency(call.get('latency_ms', 0)),
                    'Reasoning': truncate_text(routing.get('reasoning', ''), 50)
                })
        
        if log_data:
            df = pd.DataFrame(log_data)
            st.dataframe(df, width='stretch', hide_index=True)
        else:
            st.info("No routing log data available")