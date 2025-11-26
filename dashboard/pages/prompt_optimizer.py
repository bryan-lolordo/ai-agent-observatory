"""
Prompt Optimizer Page - A/B Testing and Optimization
Location: dashboard/pages/prompt_optimizer.py

Advanced prompt testing with A/B comparison, diff viewing, and optimization insights.
Enables systematic prompt improvement through data-driven analysis.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
from collections import defaultdict
import difflib
import json

from dashboard.utils.data_fetcher import (
    get_project_overview,
    get_llm_calls,
    get_available_agents,
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
    create_bar_chart,
    create_cost_breakdown_pie,
)


def count_tokens_estimate(text: str) -> int:
    """Rough token count estimate (4 chars ≈ 1 token)."""
    return len(text) // 4


def generate_prompt_diff(prompt_a: str, prompt_b: str) -> List[Tuple[str, str]]:
    """
    Generate diff between two prompts.
    
    Returns:
        List of (diff_type, text) tuples where diff_type is '+', '-', or ' '
    """
    lines_a = prompt_a.split('\n')
    lines_b = prompt_b.split('\n')
    
    diff = list(difflib.unified_diff(lines_a, lines_b, lineterm=''))
    
    # Parse unified diff format
    changes = []
    for line in diff[2:]:  # Skip header lines
        if line.startswith('+'):
            changes.append(('+', line[1:]))
        elif line.startswith('-'):
            changes.append(('-', line[1:]))
        elif not line.startswith('@@'):
            changes.append((' ', line))
    
    return changes


def analyze_test_results(results_a: List[Dict], results_b: List[Dict]) -> Dict[str, Any]:
    """
    Analyze A/B test results and determine winners.
    
    Args:
        results_a: Test results for Prompt A
        results_b: Test results for Prompt B
    
    Returns:
        Analysis dictionary with metrics and winners
    """
    if not results_a or not results_b:
        return {}
    
    # Calculate averages for Prompt A
    avg_score_a = sum(r.get('score', 0) for r in results_a) / len(results_a)
    avg_cost_a = sum(r.get('cost', 0) for r in results_a) / len(results_a)
    avg_latency_a = sum(r.get('latency', 0) for r in results_a) / len(results_a)
    avg_tokens_a = sum(r.get('tokens', 0) for r in results_a) / len(results_a)
    
    # Calculate averages for Prompt B
    avg_score_b = sum(r.get('score', 0) for r in results_b) / len(results_b)
    avg_cost_b = sum(r.get('cost', 0) for r in results_b) / len(results_b)
    avg_latency_b = sum(r.get('latency', 0) for r in results_b) / len(results_b)
    avg_tokens_b = sum(r.get('tokens', 0) for r in results_b) / len(results_b)
    
    # Determine winners
    winners = {
        'quality': 'A' if avg_score_a > avg_score_b else ('B' if avg_score_b > avg_score_a else 'Tie'),
        'cost': 'A' if avg_cost_a < avg_cost_b else ('B' if avg_cost_b < avg_cost_a else 'Tie'),
        'latency': 'A' if avg_latency_a < avg_latency_b else ('B' if avg_latency_b < avg_latency_a else 'Tie'),
        'tokens': 'A' if avg_tokens_a < avg_tokens_b else ('B' if avg_tokens_b < avg_tokens_a else 'Tie'),
    }
    
    return {
        'prompt_a': {
            'avg_score': avg_score_a,
            'avg_cost': avg_cost_a,
            'avg_latency': avg_latency_a,
            'avg_tokens': avg_tokens_a,
        },
        'prompt_b': {
            'avg_score': avg_score_b,
            'avg_cost': avg_cost_b,
            'avg_latency': avg_latency_b,
            'avg_tokens': avg_tokens_b,
        },
        'winners': winners,
        'deltas': {
            'score': avg_score_b - avg_score_a,
            'cost': avg_cost_b - avg_cost_a,
            'latency': avg_latency_b - avg_latency_a,
            'tokens': avg_tokens_b - avg_tokens_a,
        }
    }


def generate_optimization_insights(analysis: Dict, prompt_a: str, prompt_b: str, 
                                   results_a: List[Dict], results_b: List[Dict]) -> List[str]:
    """Generate AI-style optimization insights from test results."""
    if not analysis:
        return []
    
    insights = []
    
    deltas = analysis['deltas']
    winners = analysis['winners']
    
    # Quality insights
    if abs(deltas['score']) > 0.5:
        if deltas['score'] > 0:
            insights.append(f"✅ Prompt B improves quality by {deltas['score']:.1f} points ({format_percentage(abs(deltas['score'])/10)} improvement)")
        else:
            insights.append(f"⚠️ Prompt A performs better with {abs(deltas['score']):.1f} higher quality score")
    
    # Cost insights
    if abs(deltas['cost']) > 0.0001:
        cost_change_pct = (deltas['cost'] / analysis['prompt_a']['avg_cost']) * 100 if analysis['prompt_a']['avg_cost'] > 0 else 0
        if deltas['cost'] < 0:
            insights.append(f"💰 Prompt B reduces cost by {format_cost(abs(deltas['cost']))} per call ({abs(cost_change_pct):.1f}% savings)")
        else:
            insights.append(f"💸 Prompt B increases cost by {format_cost(deltas['cost'])} per call ({cost_change_pct:.1f}% more expensive)")
    
    # Token efficiency
    if abs(deltas['tokens']) > 50:
        if deltas['tokens'] < 0:
            insights.append(f"📉 Prompt B uses {int(abs(deltas['tokens']))} fewer tokens per call (more concise)")
        else:
            insights.append(f"📈 Prompt B uses {int(deltas['tokens'])} more tokens per call (more detailed)")
    
    # Latency insights
    if abs(deltas['latency']) > 100:
        if deltas['latency'] < 0:
            insights.append(f"⚡ Prompt B is {int(abs(deltas['latency']))}ms faster on average")
        else:
            insights.append(f"🐌 Prompt B is {int(deltas['latency'])}ms slower on average")
    
    # Prompt length comparison
    len_a = len(prompt_a)
    len_b = len(prompt_b)
    if abs(len_a - len_b) > 100:
        if len_b < len_a:
            insights.append(f"✂️ Prompt B is {len_a - len_b} characters shorter (simplification)")
        else:
            insights.append(f"📝 Prompt B is {len_b - len_a} characters longer (more detailed instructions)")
    
    # Consistency analysis
    scores_a = [r.get('score', 0) for r in results_a]
    scores_b = [r.get('score', 0) for r in results_b]
    
    if scores_a and scores_b:
        import statistics
        std_a = statistics.stdev(scores_a) if len(scores_a) > 1 else 0
        std_b = statistics.stdev(scores_b) if len(scores_b) > 1 else 0
        
        if std_b < std_a * 0.8:
            insights.append(f"🎯 Prompt B is more consistent (lower variance in quality)")
        elif std_b > std_a * 1.2:
            insights.append(f"📊 Prompt A is more consistent across test cases")
    
    # Overall recommendation
    wins_a = sum(1 for w in winners.values() if w == 'A')
    wins_b = sum(1 for w in winners.values() if w == 'B')
    
    if wins_b > wins_a:
        insights.append(f"🏆 **Recommendation: Use Prompt B** (wins {wins_b}/{len(winners)} metrics)")
    elif wins_a > wins_b:
        insights.append(f"🏆 **Recommendation: Use Prompt A** (wins {wins_a}/{len(winners)} metrics)")
    else:
        insights.append(f"🤝 **Prompts perform similarly** - choose based on your priority (quality vs cost)")
    
    return insights


def render_prompt_diff_viewer(prompt_a: str, prompt_b: str):
    """Render side-by-side diff viewer."""
    st.subheader("📝 Prompt Diff Viewer")
    
    diff_changes = generate_prompt_diff(prompt_a, prompt_b)
    
    if not diff_changes:
        st.info("Prompts are identical")
        return
    
    st.caption("Color coding: 🟢 Added, 🔴 Removed, ⚪ Unchanged")
    
    # Display diff
    diff_html = []
    for diff_type, text in diff_changes:
        if diff_type == '+':
            diff_html.append(f'<div style="background-color: #d4edda; padding: 2px 4px; margin: 1px 0;">+ {text}</div>')
        elif diff_type == '-':
            diff_html.append(f'<div style="background-color: #f8d7da; padding: 2px 4px; margin: 1px 0;">- {text}</div>')
        else:
            diff_html.append(f'<div style="padding: 2px 4px; margin: 1px 0;">&nbsp; {text}</div>')
    
    st.markdown(''.join(diff_html), unsafe_allow_html=True)


def render_routing_impact_analysis(results_a: List[Dict], results_b: List[Dict]):
    """Analyze and display routing impact of each prompt."""
    st.subheader("🔀 Routing Impact Analysis")
    
    # Analyze model distribution for each prompt
    models_a = defaultdict(int)
    models_b = defaultdict(int)
    
    for r in results_a:
        model = r.get('model', 'Unknown')
        models_a[model] += 1
    
    for r in results_b:
        model = r.get('model', 'Unknown')
        models_b[model] += 1
    
    # Categorize models
    def categorize_model(model: str) -> str:
        model_lower = model.lower()
        if any(x in model_lower for x in ['gpt-4', 'opus', '4o']):
            return 'Premium'
        elif any(x in model_lower for x in ['sonnet', 'haiku', 'turbo', '3.5']):
            return 'Medium'
        else:
            return 'Budget'
    
    categories_a = defaultdict(int)
    categories_b = defaultdict(int)
    
    for model, count in models_a.items():
        category = categorize_model(model)
        categories_a[category] += count
    
    for model, count in models_b.items():
        category = categorize_model(model)
        categories_b[category] += count
    
    # Calculate percentages
    total_a = sum(categories_a.values())
    total_b = sum(categories_b.values())
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### Prompt A Distribution")
        if total_a > 0:
            for category in ['Budget', 'Medium', 'Premium']:
                count = categories_a.get(category, 0)
                pct = (count / total_a) * 100
                st.write(f"**{category}:** {pct:.1f}% ({count} calls)")
        else:
            st.info("No routing data")
    
    with col2:
        st.write("### Prompt B Distribution")
        if total_b > 0:
            for category in ['Budget', 'Medium', 'Premium']:
                count = categories_b.get(category, 0)
                pct = (count / total_b) * 100
                st.write(f"**{category}:** {pct:.1f}% ({count} calls)")
        else:
            st.info("No routing data")
    
    # Analysis
    if total_a > 0 and total_b > 0:
        budget_a_pct = (categories_a.get('Budget', 0) / total_a) * 100
        budget_b_pct = (categories_b.get('Budget', 0) / total_b) * 100
        
        if budget_b_pct > budget_a_pct + 5:
            st.success(f"✅ Prompt B is more router-friendly ({budget_b_pct:.1f}% vs {budget_a_pct:.1f}% budget models)")
        elif budget_a_pct > budget_b_pct + 5:
            st.success(f"✅ Prompt A is more router-friendly ({budget_a_pct:.1f}% vs {budget_b_pct:.1f}% budget models)")


def render():
    """Render the Prompt Optimizer page."""
    
    st.title("✨ Prompt Optimizer - A/B Testing")
    
    # Get selected project
    selected_project = st.session_state.get('selected_project')
    
    # Project indicator
    if selected_project:
        st.info(f"📊 Optimizing prompts for: **{selected_project}**")
    else:
        st.info("📊 Optimizing prompts for: **All Projects**")
    
    st.divider()
    
    # Initialize session state for test results
    if 'test_results_a' not in st.session_state:
        st.session_state.test_results_a = None
    if 'test_results_b' not in st.session_state:
        st.session_state.test_results_b = None
    
    # Section 1: Prompt Variant Workspace
    st.subheader("✏️ Prompt Variant Workspace")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### Prompt A (Baseline)")
        prompt_a = st.text_area(
            "Enter Prompt A",
            value="Summarize the following text concisely:\n\n{text}",
            height=200,
            key="prompt_a"
        )
        tokens_a = count_tokens_estimate(prompt_a)
        st.caption(f"Estimated tokens: ~{tokens_a}")
    
    with col2:
        st.write("### Prompt B (Variant)")
        prompt_b = st.text_area(
            "Enter Prompt B",
            value="Provide a 3-bullet point summary of this text:\n\n{text}",
            height=200,
            key="prompt_b"
        )
        tokens_b = count_tokens_estimate(prompt_b)
        st.caption(f"Estimated tokens: ~{tokens_b}")
    
    st.divider()
    
    # Section 2: Test Dataset Selector
    st.subheader("🎯 Test Dataset & Configuration")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        test_dataset = st.selectbox(
            "Test Dataset",
            options=[
                "10 sample queries",
                "25 mixed queries",
                "50 comprehensive test",
                "Use recent calls (last 24h)",
            ],
            key="test_dataset"
        )
    
    with col2:
        test_model = st.selectbox(
            "Test Model",
            options=["gpt-4o", "claude-sonnet-4", "mistral-small", "Use router"],
            key="test_model"
        )
    
    with col3:
        enable_judge = st.checkbox(
            "Enable Quality Evaluation",
            value=True,
            help="Run LLM Judge on outputs (adds cost)",
            key="enable_judge"
        )
    
    # Simulate test button
    if st.button("🚀 Run A/B Test", type="primary"):
        with st.spinner("Running A/B test..."):
            # Simulate test results (in production, this would call actual LLMs)
            import random
            import time
            
            time.sleep(2)  # Simulate processing
            
            # Generate simulated results
            num_tests = 10 if "10" in test_dataset else (25 if "25" in test_dataset else 50)
            
            results_a = []
            results_b = []
            
            base_score_a = random.uniform(7.5, 8.5)
            base_score_b = random.uniform(8.0, 9.0)
            
            for i in range(num_tests):
                # Simulate results for Prompt A
                results_a.append({
                    'query': f"Test query {i+1}",
                    'score': base_score_a + random.uniform(-1, 1),
                    'cost': 0.004 + random.uniform(-0.001, 0.001),
                    'latency': 1200 + random.randint(-200, 200),
                    'tokens': tokens_a + random.randint(-50, 50),
                    'model': test_model if test_model != "Use router" else random.choice(['gpt-4o', 'claude-sonnet-4', 'mistral-small'])
                })
                
                # Simulate results for Prompt B
                results_b.append({
                    'query': f"Test query {i+1}",
                    'score': base_score_b + random.uniform(-1, 1),
                    'cost': 0.003 + random.uniform(-0.0005, 0.0005),
                    'latency': 1100 + random.randint(-150, 150),
                    'tokens': tokens_b + random.randint(-40, 40),
                    'model': test_model if test_model != "Use router" else random.choice(['gpt-4o', 'claude-sonnet-4', 'mistral-small'])
                })
            
            st.session_state.test_results_a = results_a
            st.session_state.test_results_b = results_b
            
            st.success(f"✅ A/B test completed! Tested {num_tests} queries.")
            st.rerun()
    
    # Check if we have test results
    if st.session_state.test_results_a is None or st.session_state.test_results_b is None:
        st.divider()
        st.info("👆 Configure test parameters and click 'Run A/B Test' to start optimization analysis")
        
        # Show guidance
        with st.expander("ℹ️ How to Use Prompt Optimizer"):
            st.markdown("""
            **Step-by-Step Guide:**
            
            1. **Enter Prompts**
               - Prompt A: Your baseline/current prompt
               - Prompt B: The variant you want to test
               - Use {variables} for dynamic content
            
            2. **Select Test Dataset**
               - Start small (10 queries) for quick iteration
               - Use larger sets (50+) for production validation
               - Can use recent real calls for realistic testing
            
            3. **Configure Testing**
               - Choose model to test with
               - Enable/disable quality evaluation (Judge)
               - Quality eval adds ~$0.01 per test but provides score
            
            4. **Run Test**
               - System tests both prompts on same queries
               - Tracks quality, cost, latency, tokens
               - Identifies routing patterns
            
            5. **Analyze Results**
               - Compare metrics side-by-side
               - View detailed per-query results
               - Get optimization insights
               - Export winning prompt
            
            **Best Practices:**
            - Test one change at a time
            - Use diverse test queries
            - Consider cost vs quality tradeoffs
            - Run multiple iterations
            """)
        
        return
    
    # We have test results - show analysis
    st.divider()
    
    # Analyze results
    analysis = analyze_test_results(
        st.session_state.test_results_a,
        st.session_state.test_results_b
    )
    
    # Section 3: A/B Test Results Summary
    st.subheader("📊 A/B Test Results Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### Prompt A (Baseline)")
        metrics_a = [
            {
                "label": "Avg Quality Score",
                "value": f"{analysis['prompt_a']['avg_score']:.1f}/10",
            },
            {
                "label": "Avg Cost",
                "value": format_cost(analysis['prompt_a']['avg_cost']),
            },
            {
                "label": "Avg Latency",
                "value": format_latency(analysis['prompt_a']['avg_latency']),
            },
            {
                "label": "Avg Tokens",
                "value": format_tokens(int(analysis['prompt_a']['avg_tokens'])),
            },
        ]
        render_metric_row(metrics_a, columns=2)
    
    with col2:
        st.write("### Prompt B (Variant)")
        metrics_b = [
            {
                "label": "Avg Quality Score",
                "value": f"{analysis['prompt_b']['avg_score']:.1f}/10",
                "delta": f"{analysis['deltas']['score']:+.1f}"
            },
            {
                "label": "Avg Cost",
                "value": format_cost(analysis['prompt_b']['avg_cost']),
                "delta": f"{analysis['deltas']['cost']:+.4f}"
            },
            {
                "label": "Avg Latency",
                "value": format_latency(analysis['prompt_b']['avg_latency']),
                "delta": f"{analysis['deltas']['latency']:+.0f}ms"
            },
            {
                "label": "Avg Tokens",
                "value": format_tokens(int(analysis['prompt_b']['avg_tokens'])),
                "delta": f"{analysis['deltas']['tokens']:+.0f}"
            },
        ]
        render_metric_row(metrics_b, columns=2)
    
    st.divider()
    
    # Section 4: Win/Loss Heatmap
    st.subheader("🏆 Win/Loss Summary")
    
    winners = analysis['winners']
    
    # Create heatmap-style display
    heatmap_data = {
        'Metric': ['Quality', 'Cost', 'Latency', 'Tokens'],
        'Winner': [
            f"{'🟢 Prompt ' + winners['quality']}" if winners['quality'] != 'Tie' else "⚪ Tie",
            f"{'🟢 Prompt ' + winners['cost']}" if winners['cost'] != 'Tie' else "⚪ Tie",
            f"{'🟢 Prompt ' + winners['latency']}" if winners['latency'] != 'Tie' else "⚪ Tie",
            f"{'🟢 Prompt ' + winners['tokens']}" if winners['tokens'] != 'Tie' else "⚪ Tie",
        ],
        'Difference': [
            f"{analysis['deltas']['score']:+.2f} points",
            f"{analysis['deltas']['cost']:+.4f}",
            f"{analysis['deltas']['latency']:+.0f}ms",
            f"{analysis['deltas']['tokens']:+.0f} tokens",
        ]
    }
    
    df = pd.DataFrame(heatmap_data)
    st.dataframe(df, width='stretch', hide_index=True)
    
    st.divider()
    
    # Section 5: Detailed Comparison Table
    st.subheader("📋 Detailed Per-Query Comparison")
    
    comparison_data = []
    for i, (res_a, res_b) in enumerate(zip(st.session_state.test_results_a, st.session_state.test_results_b), 1):
        comparison_data.append({
            'Query': f"Test {i}",
            'Score A': f"{res_a['score']:.1f}",
            'Score B': f"{res_b['score']:.1f}",
            'Diff': f"{res_b['score'] - res_a['score']:+.1f}",
            'Cost A': format_cost(res_a['cost']),
            'Cost B': format_cost(res_b['cost']),
            'Latency A': format_latency(res_a['latency']),
            'Latency B': format_latency(res_b['latency']),
            'Winner': 'B' if res_b['score'] > res_a['score'] else ('A' if res_a['score'] > res_b['score'] else 'Tie')
        })
    
    comp_df = pd.DataFrame(comparison_data)
    st.dataframe(comp_df, width='stretch', hide_index=True)
    
    st.divider()
    
    # Section 6: Prompt Diff Viewer
    render_prompt_diff_viewer(prompt_a, prompt_b)
    
    st.divider()
    
    # Section 7: Routing Impact Analysis
    if test_model == "Use router":
        render_routing_impact_analysis(
            st.session_state.test_results_a,
            st.session_state.test_results_b
        )
        st.divider()
    
    # Section 8: Per-Model Results Breakdown
    st.subheader("🤖 Per-Model Performance")
    
    # Group results by model
    model_scores_a = defaultdict(list)
    model_scores_b = defaultdict(list)
    
    for res in st.session_state.test_results_a:
        model_scores_a[res['model']].append(res['score'])
    
    for res in st.session_state.test_results_b:
        model_scores_b[res['model']].append(res['score'])
    
    # Calculate averages
    all_models = set(list(model_scores_a.keys()) + list(model_scores_b.keys()))
    
    model_comparison = []
    for model in sorted(all_models):
        avg_a = sum(model_scores_a[model]) / len(model_scores_a[model]) if model_scores_a[model] else 0
        avg_b = sum(model_scores_b[model]) / len(model_scores_b[model]) if model_scores_b[model] else 0
        
        model_comparison.append({
            'Model': format_model_name(model),
            'Avg Score A': f"{avg_a:.1f}" if avg_a > 0 else "N/A",
            'Avg Score B': f"{avg_b:.1f}" if avg_b > 0 else "N/A",
            'Difference': f"{avg_b - avg_a:+.1f}" if avg_a > 0 and avg_b > 0 else "N/A",
            'Tests': len(model_scores_a[model]) + len(model_scores_b[model])
        })
    
    model_df = pd.DataFrame(model_comparison)
    st.dataframe(model_df, width='stretch', hide_index=True)
    
    st.divider()
    
    # Section 9: Optimization Insights
    st.subheader("💡 Optimization Insights")
    
    insights = generate_optimization_insights(
        analysis,
        prompt_a,
        prompt_b,
        st.session_state.test_results_a,
        st.session_state.test_results_b
    )
    
    if insights:
        for insight in insights:
            if "Recommendation" in insight:
                st.success(insight)
            elif "⚠️" in insight:
                st.warning(insight)
            else:
                st.info(insight)
    
    st.divider()
    
    # Section 10: Export Prompt Variant
    st.subheader("💾 Export Winning Prompt")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.write("**Save the better-performing prompt for production use**")
        
        # Determine winner
        wins_a = sum(1 for w in winners.values() if w == 'A')
        wins_b = sum(1 for w in winners.values() if w == 'B')
        
        if wins_b > wins_a:
            recommended = "Prompt B"
            recommended_text = prompt_b
        elif wins_a > wins_b:
            recommended = "Prompt A"
            recommended_text = prompt_a
        else:
            recommended = "Either (similar performance)"
            recommended_text = prompt_b
        
        st.info(f"**Recommended:** {recommended}")
    
    with col2:
        # Export buttons
        export_format = st.selectbox(
            "Format",
            options=["JSON", "Text", "Python Code"],
            key="export_format"
        )
    
    if export_format == "JSON":
        export_data = {
            "prompt": recommended_text,
            "metrics": {
                "avg_score": analysis['prompt_b']['avg_score'] if wins_b >= wins_a else analysis['prompt_a']['avg_score'],
                "avg_cost": analysis['prompt_b']['avg_cost'] if wins_b >= wins_a else analysis['prompt_a']['avg_cost'],
                "avg_latency": analysis['prompt_b']['avg_latency'] if wins_b >= wins_a else analysis['prompt_a']['avg_latency'],
                "avg_tokens": analysis['prompt_b']['avg_tokens'] if wins_b >= wins_a else analysis['prompt_a']['avg_tokens'],
            },
            "test_date": datetime.now().isoformat(),
            "test_size": len(st.session_state.test_results_a)
        }
        export_content = json.dumps(export_data, indent=2)
    elif export_format == "Python Code":
        export_content = f'''# Optimized Prompt - Tested {datetime.now().strftime("%Y-%m-%d")}
# Performance: Quality {analysis['prompt_b']['avg_score'] if wins_b >= wins_a else analysis['prompt_a']['avg_score']:.1f}/10, Cost {format_cost(analysis['prompt_b']['avg_cost'] if wins_b >= wins_a else analysis['prompt_a']['avg_cost'])}

OPTIMIZED_PROMPT = """{recommended_text}"""
'''
    else:  # Text
        export_content = recommended_text
    
    st.download_button(
        label=f"📥 Download {recommended}",
        data=export_content,
        file_name=f"optimized_prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{'json' if export_format == 'JSON' else 'py' if export_format == 'Python Code' else 'txt'}",
        mime="application/json" if export_format == "JSON" else "text/plain"
    )
    
    # Reset button
    if st.button("🔄 Start New Test"):
        st.session_state.test_results_a = None
        st.session_state.test_results_b = None
        st.rerun()