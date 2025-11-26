"""
LLM Judge Page - Quality Evaluation Analysis
Location: dashboard/pages/llm_judge.py

Analyzes quality evaluations, hallucinations, and model performance.
Works with both actual evaluations and provides guidance when not implemented.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
from collections import defaultdict

from dashboard.utils.data_fetcher import (
    get_project_overview,
    get_llm_calls,
    get_available_agents,
    get_available_models,
    get_quality_analysis,
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
    create_time_series_chart,
    create_bar_chart,
    create_cost_breakdown_pie,
)
from dashboard.components.tables import (
    render_dataframe,
)


def detect_quality_mode(calls: List[Dict]) -> Tuple[bool, str, int]:
    """
    Detect if quality evaluation is active.
    
    Returns:
        Tuple of (has_quality_eval, mode_description, eval_count)
    """
    if not calls:
        return False, "No data", 0
    
    # Check for quality evaluations
    evaluations = [
        c.get('quality_evaluation', {})
        for c in calls
        if c.get('quality_evaluation') and isinstance(c.get('quality_evaluation'), dict)
    ]
    
    # Filter out empty dicts
    valid_evaluations = [
        e for e in evaluations
        if e.get('score') is not None
    ]
    
    if valid_evaluations:
        return True, f"Quality evaluation active", len(valid_evaluations)
    else:
        return False, "Quality evaluation not implemented", 0


def calculate_quality_kpis(calls: List[Dict]) -> Dict[str, Any]:
    """Calculate quality performance KPIs."""
    evaluations = []
    
    for call in calls:
        qual_eval = call.get('quality_evaluation', {})
        if isinstance(qual_eval, dict) and qual_eval.get('score') is not None:
            evaluations.append({
                'score': qual_eval.get('score', 0),
                'hallucination': qual_eval.get('hallucination', False),
                'factual_error': qual_eval.get('factual_error', False),
                'confidence': qual_eval.get('confidence', 0),
                'call': call
            })
    
    if not evaluations:
        return {
            'avg_score': 0,
            'hallucination_rate': 0,
            'factual_error_rate': 0,
            'confidence_gap': 0,
            'total_evaluated': 0
        }
    
    total = len(evaluations)
    avg_score = sum(e['score'] for e in evaluations) / total
    hallucinations = sum(1 for e in evaluations if e['hallucination'])
    factual_errors = sum(1 for e in evaluations if e['factual_error'])
    
    # Confidence gap: difference between model confidence and actual score
    confidence_gaps = []
    for e in evaluations:
        if e['confidence'] > 0:
            # Normalize score to 0-1 range for comparison
            normalized_score = e['score'] / 10
            gap = abs(e['confidence'] - normalized_score)
            confidence_gaps.append(gap)
    
    avg_confidence_gap = sum(confidence_gaps) / len(confidence_gaps) if confidence_gaps else 0
    
    return {
        'avg_score': avg_score,
        'hallucination_rate': hallucinations / total,
        'factual_error_rate': factual_errors / total,
        'confidence_gap': avg_confidence_gap,
        'total_evaluated': total
    }


def calculate_model_leaderboard(calls: List[Dict]) -> List[Dict]:
    """Calculate performance leaderboard by model."""
    model_stats = defaultdict(lambda: {
        'scores': [],
        'hallucinations': 0,
        'factual_errors': 0,
        'total_cost': 0,
        'total_latency': 0,
        'total_tokens': 0,
        'count': 0
    })
    
    for call in calls:
        qual_eval = call.get('quality_evaluation', {})
        if not isinstance(qual_eval, dict) or qual_eval.get('score') is None:
            continue
        
        model = call.get('model_name', 'Unknown')
        stats = model_stats[model]
        
        stats['scores'].append(qual_eval.get('score', 0))
        stats['hallucinations'] += 1 if qual_eval.get('hallucination') else 0
        stats['factual_errors'] += 1 if qual_eval.get('factual_error') else 0
        stats['total_cost'] += call.get('total_cost', 0)
        stats['total_latency'] += call.get('latency_ms', 0)
        stats['total_tokens'] += call.get('total_tokens', 0)
        stats['count'] += 1
    
    leaderboard = []
    for model, stats in model_stats.items():
        if stats['count'] == 0:
            continue
        
        leaderboard.append({
            'model': model,
            'avg_score': sum(stats['scores']) / len(stats['scores']),
            'hallucination_rate': stats['hallucinations'] / stats['count'],
            'factual_error_rate': stats['factual_errors'] / stats['count'],
            'avg_cost': stats['total_cost'] / stats['count'],
            'avg_latency': stats['total_latency'] / stats['count'],
            'avg_tokens': stats['total_tokens'] / stats['count'],
            'count': stats['count']
        })
    
    # Sort by avg score descending
    leaderboard.sort(key=lambda x: x['avg_score'], reverse=True)
    
    return leaderboard


def calculate_agent_leaderboard(calls: List[Dict]) -> List[Dict]:
    """Calculate performance leaderboard by agent."""
    agent_stats = defaultdict(lambda: {
        'scores': [],
        'hallucinations': 0,
        'factual_errors': 0,
        'total_cost': 0,
        'total_latency': 0,
        'total_tokens': 0,
        'count': 0
    })
    
    for call in calls:
        qual_eval = call.get('quality_evaluation', {})
        if not isinstance(qual_eval, dict) or qual_eval.get('score') is None:
            continue
        
        agent = call.get('agent_name', 'Unknown')
        stats = agent_stats[agent]
        
        stats['scores'].append(qual_eval.get('score', 0))
        stats['hallucinations'] += 1 if qual_eval.get('hallucination') else 0
        stats['factual_errors'] += 1 if qual_eval.get('factual_error') else 0
        stats['total_cost'] += call.get('total_cost', 0)
        stats['total_latency'] += call.get('latency_ms', 0)
        stats['total_tokens'] += call.get('total_tokens', 0)
        stats['count'] += 1
    
    leaderboard = []
    for agent, stats in agent_stats.items():
        if stats['count'] == 0:
            continue
        
        leaderboard.append({
            'agent': agent,
            'avg_score': sum(stats['scores']) / len(stats['scores']),
            'hallucination_rate': stats['hallucinations'] / stats['count'],
            'factual_error_rate': stats['factual_errors'] / stats['count'],
            'avg_cost': stats['total_cost'] / stats['count'],
            'avg_latency': stats['total_latency'] / stats['count'],
            'avg_tokens': stats['total_tokens'] / stats['count'],
            'count': stats['count']
        })
    
    # Sort by avg score descending
    leaderboard.sort(key=lambda x: x['avg_score'], reverse=True)
    
    return leaderboard


def get_error_category_breakdown(calls: List[Dict]) -> Dict[str, int]:
    """Get breakdown of error categories."""
    categories = defaultdict(int)
    
    for call in calls:
        qual_eval = call.get('quality_evaluation', {})
        if not isinstance(qual_eval, dict):
            continue
        
        # Check for various error types
        if qual_eval.get('hallucination'):
            categories['Hallucination'] += 1
        if qual_eval.get('factual_error'):
            categories['Factual Error'] += 1
        
        # Category from evaluation
        category = qual_eval.get('error_category') or qual_eval.get('category')
        if category:
            categories[category] += 1
        
        # If no errors, mark as good
        if not qual_eval.get('hallucination') and not qual_eval.get('factual_error'):
            score = qual_eval.get('score', 0)
            if score >= 9:
                categories['Excellent'] += 1
            elif score >= 7:
                categories['Good'] += 1
            elif score >= 5:
                categories['Acceptable'] += 1
            else:
                categories['Poor Quality'] += 1
    
    return dict(categories)


def get_best_and_worst_examples(calls: List[Dict], count: int = 5) -> Tuple[List[Dict], List[Dict]]:
    """Get best and worst evaluated examples."""
    evaluated_calls = []
    
    for call in calls:
        qual_eval = call.get('quality_evaluation', {})
        if isinstance(qual_eval, dict) and qual_eval.get('score') is not None:
            evaluated_calls.append(call)
    
    if not evaluated_calls:
        return [], []
    
    # Sort by score
    sorted_calls = sorted(evaluated_calls, key=lambda c: c['quality_evaluation']['score'], reverse=True)
    
    best = sorted_calls[:count]
    worst = sorted_calls[-count:][::-1]  # Reverse to show worst first
    
    return best, worst


def render_evaluation_drilldown(call: Dict, index: int):
    """Render detailed drilldown for a single evaluation."""
    qual_eval = call.get('quality_evaluation', {})
    
    if not isinstance(qual_eval, dict) or qual_eval.get('score') is None:
        st.warning("No quality evaluation data")
        return
    
    with st.expander(f"📋 Evaluation #{index} - Score: {qual_eval.get('score', 0):.1f}/10", expanded=False):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write("**1. Prompt**")
            prompt = call.get('prompt', 'N/A')
            st.code(truncate_text(prompt, 300), language="text")
            
            st.write("**2. Model Output**")
            response = call.get('response_text', 'N/A')
            st.code(truncate_text(response, 400), language="text")
            
            st.write("**3. Judge Evaluation**")
            
            score = qual_eval.get('score', 0)
            if score >= 9:
                st.success(f"**Score:** {score}/10 - Excellent")
            elif score >= 7:
                st.info(f"**Score:** {score}/10 - Good")
            elif score >= 5:
                st.warning(f"**Score:** {score}/10 - Acceptable")
            else:
                st.error(f"**Score:** {score}/10 - Poor")
            
            reasoning = qual_eval.get('reasoning', 'No reasoning provided')
            st.write(f"**Reasoning:** {reasoning}")
            
            # Flags
            if qual_eval.get('hallucination'):
                st.error("🚨 **Hallucination Detected**")
            if qual_eval.get('factual_error'):
                st.error("❌ **Factual Error Detected**")
            
            # Error category
            category = qual_eval.get('error_category') or qual_eval.get('category')
            if category:
                st.write(f"**Error Category:** {category}")
            
            # Suggestions
            suggestions = qual_eval.get('suggestions', [])
            if suggestions:
                st.write("**Suggestions for Improvement:**")
                for suggestion in suggestions:
                    st.write(f"• {suggestion}")
        
        with col2:
            st.write("**4. Metadata**")
            
            st.metric("Model", format_model_name(call.get('model_name', 'Unknown')))
            st.metric("Agent", call.get('agent_name', 'Unknown'))
            st.metric("Cost", format_cost(call.get('total_cost', 0)))
            st.metric("Latency", format_latency(call.get('latency_ms', 0)))
            st.metric("Tokens", format_tokens(call.get('total_tokens', 0)))
            
            confidence = qual_eval.get('confidence', 0)
            if confidence > 0:
                st.metric("Judge Confidence", f"{confidence:.2f}")
            
            timestamp = call.get('timestamp')
            if timestamp:
                st.write(f"**Timestamp:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")


def render_ab_comparison(call_a: Dict, call_b: Dict):
    """Render A/B comparison between two evaluated calls."""
    st.subheader("🔀 A/B Comparison")
    
    qual_a = call_a.get('quality_evaluation', {})
    qual_b = call_b.get('quality_evaluation', {})
    
    if not qual_a.get('score') or not qual_b.get('score'):
        st.info("Select two evaluated calls to compare")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### Option A")
        st.write(f"**Model:** {format_model_name(call_a.get('model_name', 'Unknown'))}")
        st.write(f"**Agent:** {call_a.get('agent_name', 'Unknown')}")
        
        st.write("**Output:**")
        st.code(truncate_text(call_a.get('response_text', 'N/A'), 200), language="text")
        
        st.metric("Judge Score", f"{qual_a.get('score', 0):.1f}/10")
        st.metric("Tokens", format_tokens(call_a.get('total_tokens', 0)))
        st.metric("Cost", format_cost(call_a.get('total_cost', 0)))
        st.metric("Latency", format_latency(call_a.get('latency_ms', 0)))
        
        if qual_a.get('hallucination'):
            st.error("🚨 Hallucination")
        if qual_a.get('factual_error'):
            st.error("❌ Factual Error")
    
    with col2:
        st.write("### Option B")
        st.write(f"**Model:** {format_model_name(call_b.get('model_name', 'Unknown'))}")
        st.write(f"**Agent:** {call_b.get('agent_name', 'Unknown')}")
        
        st.write("**Output:**")
        st.code(truncate_text(call_b.get('response_text', 'N/A'), 200), language="text")
        
        st.metric("Judge Score", f"{qual_b.get('score', 0):.1f}/10")
        st.metric("Tokens", format_tokens(call_b.get('total_tokens', 0)))
        st.metric("Cost", format_cost(call_b.get('total_cost', 0)))
        st.metric("Latency", format_latency(call_b.get('latency_ms', 0)))
        
        if qual_b.get('hallucination'):
            st.error("🚨 Hallucination")
        if qual_b.get('factual_error'):
            st.error("❌ Factual Error")
    
    # Winner determination
    score_a = qual_a.get('score', 0)
    score_b = qual_b.get('score', 0)
    
    st.divider()
    
    if score_a > score_b:
        st.success(f"✅ **Winner: Option A** (Score: {score_a:.1f} vs {score_b:.1f})")
    elif score_b > score_a:
        st.success(f"✅ **Winner: Option B** (Score: {score_b:.1f} vs {score_a:.1f})")
    else:
        st.info(f"🤝 **Tie** (Both scored {score_a:.1f})")


def render():
    """Render the LLM Judge page."""
    
    st.title("⚖️ LLM Judge - Quality Evaluation")
    
    # Get selected project
    selected_project = st.session_state.get('selected_project')
    
    # Project indicator
    if selected_project:
        st.info(f"📊 Analyzing quality for: **{selected_project}**")
    else:
        st.info("📊 Analyzing quality for: **All Projects**")
    
    st.divider()
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        try:
            agents = get_available_agents(selected_project)
            filter_agent = st.selectbox(
                "Agent",
                options=["All"] + agents,
                key="judge_agent_filter"
            )
        except:
            filter_agent = "All"
    
    with col2:
        try:
            models = get_available_models(selected_project)
            filter_model = st.selectbox(
                "Model",
                options=["All"] + models,
                key="judge_model_filter"
            )
        except:
            filter_model = "All"
    
    with col3:
        time_period = st.selectbox(
            "Time Period",
            options=["1h", "24h", "7d", "30d"],
            index=2,
            key="judge_time_period"
        )
    
    with col4:
        limit = st.selectbox(
            "Max Results",
            options=[50, 100, 200, 500],
            index=1,
            key="judge_limit"
        )
    
    st.divider()
    
    # Fetch data
    try:
        with st.spinner("Loading quality evaluation data..."):
            calls = get_llm_calls(
                project_name=selected_project,
                agent_name=None if filter_agent == "All" else filter_agent,
                model_name=None if filter_model == "All" else filter_model,
                limit=limit
            )
            
            if not calls:
                render_empty_state(
                    message="No data available for quality analysis",
                    icon="⚖️",
                    suggestion="Run your AI agents with Observatory enabled to track quality"
                )
                return
    
    except Exception as e:
        st.error(f"Error loading quality data: {str(e)}")
        return
    
    # Detect quality mode
    has_quality, quality_mode, eval_count = detect_quality_mode(calls)
    
    # Show quality status
    if has_quality:
        st.success(f"✅ {quality_mode} - {eval_count} evaluations analyzed")
    else:
        st.warning(f"⚠️ {quality_mode} - Implementation guidance below")
    
    if not has_quality:
        # Show implementation guidance
        st.divider()
        
        st.subheader("💡 How to Enable Quality Evaluation")
        
        st.markdown("""
        Quality evaluation requires implementing an LLM-as-a-Judge system.
        
        **Steps to Implement:**
        
        1. **Create Judge Prompt**
        ```python
        judge_prompt = f'''
        Evaluate the following AI response for quality, accuracy, and safety.
        
        Prompt: {original_prompt}
        Response: {ai_response}
        
        Provide:
        - Score (0-10)
        - Reasoning for score
        - Hallucination detection (true/false)
        - Factual error detection (true/false)
        - Suggestions for improvement
        
        Return as JSON.
        '''
        ```
        
        2. **Call Judge Model**
        ```python
        judge_response = call_llm(judge_prompt, model="gpt-4o")
        evaluation = parse_json(judge_response)
        ```
        
        3. **Create QualityEvaluation Object**
        ```python
        from observatory.models import QualityEvaluation
        
        quality_eval = QualityEvaluation(
            score=evaluation['score'],
            reasoning=evaluation['reasoning'],
            hallucination=evaluation['hallucination'],
            factual_error=evaluation['factual_error'],
            confidence=0.85,
            suggestions=evaluation['suggestions']
        )
        ```
        
        4. **Track with Observatory**
        ```python
        track_llm_call(
            model_name=model,
            ...,
            quality_evaluation=quality_eval
        )
        ```
        
        **Benefits:**
        - Detect hallucinations automatically
        - Track quality trends over time
        - Compare model/agent performance
        - Identify problematic patterns
        - A/B test prompts and models
        
        **Cost Consideration:**
        - Judge calls add ~$0.002-0.01 per evaluation
        - Use sampling (evaluate 10-20% of calls)
        - Use cheaper models for judging when appropriate
        
        [→ View Full Implementation Guide]
        """)
        
        return
    
    st.divider()
    
    # Calculate KPIs
    kpis = calculate_quality_kpis(calls)
    
    # Section 1: KPI Cards
    st.subheader("📊 Quality Metrics")
    
    metrics = [
        {
            "label": "Avg Judge Score",
            "value": f"{kpis['avg_score']:.1f}/10",
            "help_text": f"{kpis['total_evaluated']} evaluations"
        },
        {
            "label": "Hallucination Rate",
            "value": format_percentage(kpis['hallucination_rate']),
            "delta": "🚨" if kpis['hallucination_rate'] > 0.05 else "✅"
        },
        {
            "label": "Factual Error Rate",
            "value": format_percentage(kpis['factual_error_rate']),
            "delta": "⚠️" if kpis['factual_error_rate'] > 0.10 else "✅"
        },
        {
            "label": "Confidence Gap",
            "value": f"{kpis['confidence_gap']:.2f}",
            "help_text": "Difference between model confidence and actual score"
        }
    ]
    
    render_metric_row(metrics, columns=4)
    
    st.divider()
    
    # Section 2: Quality Trend Chart
    st.subheader("📈 Quality Trends Over Time")
    
    try:
        # Group by time
        hourly_data = defaultdict(lambda: {'scores': [], 'hallucinations': 0, 'total': 0})
        
        for call in calls:
            qual_eval = call.get('quality_evaluation', {})
            if not isinstance(qual_eval, dict) or qual_eval.get('score') is None:
                continue
            
            timestamp = call.get('timestamp')
            if timestamp:
                hour = timestamp.replace(minute=0, second=0, microsecond=0)
                hourly_data[hour]['scores'].append(qual_eval.get('score', 0))
                hourly_data[hour]['hallucinations'] += 1 if qual_eval.get('hallucination') else 0
                hourly_data[hour]['total'] += 1
        
        if hourly_data:
            sorted_hours = sorted(hourly_data.keys())
            
            avg_scores = [sum(hourly_data[h]['scores']) / len(hourly_data[h]['scores']) for h in sorted_hours]
            hall_rates = [hourly_data[h]['hallucinations'] / hourly_data[h]['total'] * 100 for h in sorted_hours]
            
            # Create chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=sorted_hours,
                y=avg_scores,
                mode='lines+markers',
                name='Avg Score',
                yaxis='y',
                line=dict(color='blue', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=sorted_hours,
                y=hall_rates,
                mode='lines+markers',
                name='Hallucination Rate (%)',
                yaxis='y2',
                line=dict(color='red', width=2)
            ))
            
            fig.update_layout(
                title="Quality Score and Hallucination Rate Over Time",
                xaxis_title="Time",
                yaxis=dict(title="Avg Score (0-10)", side='left'),
                yaxis2=dict(title="Hallucination Rate (%)", side='right', overlaying='y'),
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("Not enough temporal data for trend analysis")
    
    except Exception as e:
        st.warning(f"Could not generate trend chart: {str(e)}")
    
    st.divider()
    
    # Section 3: Leaderboard
    st.subheader("🏆 Performance Leaderboard")
    
    tab1, tab2 = st.tabs(["By Model", "By Agent"])
    
    with tab1:
        model_leaderboard = calculate_model_leaderboard(calls)
        
        if model_leaderboard:
            leaderboard_data = []
            for entry in model_leaderboard:
                leaderboard_data.append({
                    'Model': format_model_name(entry['model']),
                    'Avg Score': f"{entry['avg_score']:.1f}/10",
                    'Hallucinations': format_percentage(entry['hallucination_rate']),
                    'Errors': format_percentage(entry['factual_error_rate']),
                    'Avg Cost': format_cost(entry['avg_cost']),
                    'Avg Latency': format_latency(entry['avg_latency']),
                    'Avg Tokens': format_tokens(int(entry['avg_tokens'])),
                    'Evaluations': entry['count']
                })
            
            df = pd.DataFrame(leaderboard_data)
            st.dataframe(df, width='stretch', hide_index=True)
        else:
            st.info("No model leaderboard data")
    
    with tab2:
        agent_leaderboard = calculate_agent_leaderboard(calls)
        
        if agent_leaderboard:
            leaderboard_data = []
            for entry in agent_leaderboard:
                leaderboard_data.append({
                    'Agent': entry['agent'],
                    'Avg Score': f"{entry['avg_score']:.1f}/10",
                    'Hallucinations': format_percentage(entry['hallucination_rate']),
                    'Errors': format_percentage(entry['factual_error_rate']),
                    'Avg Cost': format_cost(entry['avg_cost']),
                    'Avg Latency': format_latency(entry['avg_latency']),
                    'Avg Tokens': format_tokens(int(entry['avg_tokens'])),
                    'Evaluations': entry['count']
                })
            
            df = pd.DataFrame(leaderboard_data)
            st.dataframe(df, width='stretch', hide_index=True)
        else:
            st.info("No agent leaderboard data")
    
    st.divider()
    
    # Section 4: Error Category Breakdown
    st.subheader("📊 Error Category Breakdown")
    
    error_categories = get_error_category_breakdown(calls)
    
    if error_categories:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = create_cost_breakdown_pie(error_categories, "Error Distribution")
            st.plotly_chart(fig, width='stretch')
        
        with col2:
            fig = create_bar_chart(
                error_categories,
                x_label="Category",
                y_label="Count",
                title="Error Categories"
            )
            st.plotly_chart(fig, width='stretch')
    else:
        st.info("No error category data")
    
    st.divider()
    
    # Section 5: Best vs Worst Examples
    st.subheader("⭐ Best vs Worst Examples")
    
    best_examples, worst_examples = get_best_and_worst_examples(calls, count=5)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### 🌟 Top 5 Best Outputs")
        
        if best_examples:
            for i, call in enumerate(best_examples, 1):
                qual_eval = call.get('quality_evaluation', {})
                score = qual_eval.get('score', 0)
                
                with st.expander(f"#{i} - Score: {score:.1f}/10", expanded=(i==1)):
                    st.write(f"**Model:** {format_model_name(call.get('model_name', 'Unknown'))}")
                    st.write(f"**Agent:** {call.get('agent_name', 'Unknown')}")
                    
                    st.write("**Output:**")
                    st.code(truncate_text(call.get('response_text', 'N/A'), 200), language="text")
                    
                    st.write("**Why it's good:**")
                    st.info(qual_eval.get('reasoning', 'No reasoning provided'))
        else:
            st.info("No best examples available")
    
    with col2:
        st.write("### 🔻 Top 5 Worst Outputs")
        
        if worst_examples:
            for i, call in enumerate(worst_examples, 1):
                qual_eval = call.get('quality_evaluation', {})
                score = qual_eval.get('score', 0)
                
                with st.expander(f"#{i} - Score: {score:.1f}/10", expanded=(i==1)):
                    st.write(f"**Model:** {format_model_name(call.get('model_name', 'Unknown'))}")
                    st.write(f"**Agent:** {call.get('agent_name', 'Unknown')}")
                    
                    st.write("**Output:**")
                    st.code(truncate_text(call.get('response_text', 'N/A'), 200), language="text")
                    
                    st.write("**Issues:**")
                    st.warning(qual_eval.get('reasoning', 'No reasoning provided'))
                    
                    if qual_eval.get('hallucination'):
                        st.error("🚨 Hallucination detected")
                    if qual_eval.get('factual_error'):
                        st.error("❌ Factual error detected")
        else:
            st.info("No worst examples available")
    
    st.divider()
    
    # Section 6: LLM Judge Event Log
    st.subheader("📋 Evaluation Event Log")
    
    # Filter to evaluated calls only
    evaluated_calls = [
        c for c in calls
        if c.get('quality_evaluation', {}).get('score') is not None
    ]
    
    if evaluated_calls:
        st.caption(f"Showing {len(evaluated_calls)} evaluated calls")
        
        # Create event table
        event_data = []
        for call in evaluated_calls[:50]:  # Show top 50
            qual_eval = call.get('quality_evaluation', {})
            
            event_data.append({
                'Prompt': truncate_text(call.get('prompt', 'N/A'), 50),
                'Model': format_model_name(call.get('model_name', 'Unknown')),
                'Agent': call.get('agent_name', 'Unknown'),
                'Score': f"{qual_eval.get('score', 0):.1f}/10",
                'Hallucinated': '🚨' if qual_eval.get('hallucination') else '✅',
                'Error': '❌' if qual_eval.get('factual_error') else '✅',
                'Category': qual_eval.get('error_category', 'N/A'),
                'Tokens': format_tokens(call.get('total_tokens', 0)),
                'Cost': format_cost(call.get('total_cost', 0))
            })
        
        df = pd.DataFrame(event_data)
        st.dataframe(df, width='stretch', hide_index=True)
        
        # Drilldown section
        st.divider()
        st.subheader("🔍 Detailed Evaluation Drilldown")
        
        for i, call in enumerate(evaluated_calls[:20], 1):  # Top 20 for drilldown
            render_evaluation_drilldown(call, i)
    else:
        st.info("No evaluated calls to display")
    
    # Section 7: A/B Comparison (Optional)
    if len(evaluated_calls) >= 2:
        st.divider()
        
        with st.expander("🔀 A/B Comparison Tool", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                call_a_idx = st.selectbox(
                    "Select Option A",
                    options=range(len(evaluated_calls[:20])),
                    format_func=lambda i: f"Call #{i+1} - {format_model_name(evaluated_calls[i].get('model_name', 'Unknown'))} - Score: {evaluated_calls[i].get('quality_evaluation', {}).get('score', 0):.1f}",
                    key="ab_call_a"
                )
            
            with col2:
                call_b_idx = st.selectbox(
                    "Select Option B",
                    options=range(len(evaluated_calls[:20])),
                    format_func=lambda i: f"Call #{i+1} - {format_model_name(evaluated_calls[i].get('model_name', 'Unknown'))} - Score: {evaluated_calls[i].get('quality_evaluation', {}).get('score', 0):.1f}",
                    key="ab_call_b"
                )
            
            if call_a_idx != call_b_idx:
                render_ab_comparison(evaluated_calls[call_a_idx], evaluated_calls[call_b_idx])


# Import plotly for charts
import plotly.graph_objects as go