"""
LLM Judge Dashboard Page
Location: ai-agent-observatory/dashboard/pages/llm_judge.py

Quality evaluation analytics with root cause analysis and fix recommendations.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json

# =============================================================================
# DATABASE CONNECTION
# =============================================================================

@st.cache_resource
def get_connection():
    """Get database connection."""
    import sqlite3
    import os
    
    db_path = os.environ.get('OBSERVATORY_DB_PATH', 
        os.path.join(os.path.dirname(__file__), '..', '..', 'observatory.db'))
    
    if not os.path.exists(db_path):
        st.error(f"Database not found: {db_path}")
        return None
    
    return sqlite3.connect(db_path, check_same_thread=False)


# =============================================================================
# DATA LOADING
# =============================================================================

@st.cache_data(ttl=60)
def load_judge_data(start_date: str, end_date: str) -> pd.DataFrame:
    """Load LLM calls that have quality evaluations."""
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    
    query = """
        SELECT 
            id,
            timestamp,
            agent_name,
            operation,
            model_name,
            prompt,
            response_text,
            quality_evaluation,
            prompt_tokens,
            completion_tokens,
            latency_ms,
            success
        FROM llm_calls
        WHERE quality_evaluation IS NOT NULL 
          AND quality_evaluation != ''
          AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp DESC
    """
    
    try:
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        
        # Parse quality_evaluation JSON
        if not df.empty:
            df['eval_data'] = df['quality_evaluation'].apply(parse_quality_eval)
            df['judge_score'] = df['eval_data'].apply(lambda x: x.get('judge_score', 0) if x else 0)
            df['hallucination'] = df['eval_data'].apply(lambda x: x.get('hallucination_flag', False) if x else False)
            df['factual_error'] = df['eval_data'].apply(lambda x: x.get('factual_error', False) if x else False)
            df['reasoning'] = df['eval_data'].apply(lambda x: x.get('reasoning', '') if x else '')
            df['confidence'] = df['eval_data'].apply(lambda x: x.get('confidence', 0) if x else 0)
            df['root_cause'] = df['eval_data'].apply(lambda x: x.get('root_cause', {}) if x else {})
            df['recommended_fix'] = df['eval_data'].apply(lambda x: x.get('recommended_fix', {}) if x else {})
            
            # Derive status
            df['status'] = df.apply(derive_status, axis=1)
            df['has_issue'] = df['status'].isin(['🚨 Hallucination', '⚠️ Factual Error', '📉 Low Score'])
            
            # Format display columns
            df['agent_operation'] = df['agent_name'] + '.' + df['operation']
            df['time'] = pd.to_datetime(df['timestamp']).dt.strftime('%H:%M')
            df['date'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d')
            
        return df
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()


def parse_quality_eval(eval_str: str) -> Optional[Dict]:
    """Parse quality evaluation JSON string."""
    if not eval_str:
        return None
    try:
        return json.loads(eval_str)
    except:
        return None


def derive_status(row) -> str:
    """Derive status from evaluation data."""
    if row.get('hallucination'):
        return '🚨 Hallucination'
    if row.get('factual_error'):
        return '⚠️ Factual Error'
    if row.get('judge_score', 10) < 5:
        return '📉 Low Score'
    if row.get('judge_score', 0) >= 8:
        return '✅ Good'
    return '➖ Acceptable'


# =============================================================================
# ROOT CAUSE → FIX MAPPING
# =============================================================================

ROOT_CAUSE_FIX_MAP = {
    'no_grounding': {
        'cause': 'No grounding',
        'evidence': 'Hallucination, no context in prompt',
        'fix': 'Add RAG retrieval',
        'action': 'Implement RAG pipeline to ground responses',
        'effort': 'Medium',
        'impact': 'High — eliminates hallucinations',
        'code_template': '''# Add RAG grounding
from your_rag_module import retrieve_context

async def grounded_call(query: str, kernel):
    # Retrieve relevant context
    context = await retrieve_context(query, top_k=5)
    
    # Build grounded prompt
    prompt = f"""Use ONLY the following context to answer.
If the answer is not in the context, say "I don't know."

CONTEXT:
{context}

QUESTION: {query}
"""
    return await kernel.invoke_prompt(prompt)
'''
    },
    'weak_grounding': {
        'cause': 'Weak grounding',
        'evidence': 'Hallucination with context provided',
        'fix': 'Add constraints',
        'action': 'Add explicit grounding constraints to prompt',
        'effort': 'Low',
        'impact': 'Medium — reduces hallucinations',
        'code_template': '''# Add grounding constraints
CONSTRAINED_PROMPT = """CRITICAL RULES:
1. ONLY use information from the provided context
2. If information is not in context, say "Not found in provided data"
3. NEVER invent or assume facts
4. Quote exact text when possible

CONTEXT:
{context}

TASK: {task}
"""
'''
    },
    'no_verification': {
        'cause': 'No verification',
        'evidence': 'Factual errors in response',
        'fix': 'Add verification step',
        'action': 'Add fact-checking pass after generation',
        'effort': 'Medium',
        'impact': 'High — catches factual errors',
        'code_template': '''# Add verification step
async def verified_response(prompt: str, response: str, kernel):
    verify_prompt = f"""Fact-check this response against the source.
    
SOURCE PROMPT:
{prompt[:2000]}

RESPONSE TO VERIFY:
{response}

List any factual errors or unsupported claims.
Return JSON: {{"errors": [...], "verified": true/false}}
"""
    result = await kernel.invoke_prompt(verify_prompt)
    verification = json.loads(str(result))
    
    if not verification.get('verified'):
        # Regenerate with corrections
        return await regenerate_with_feedback(prompt, verification['errors'])
    
    return response
'''
    },
    'weak_model': {
        'cause': 'Weak model',
        'evidence': 'Budget model on complex task',
        'fix': 'Upgrade model',
        'action': 'Route complex tasks to stronger model',
        'effort': 'Low',
        'impact': 'High — improves reasoning quality',
        'code_template': '''# Model routing based on complexity
def select_model(operation: str, complexity_score: float) -> str:
    if complexity_score > 0.7 or operation in COMPLEX_OPS:
        return "gpt-4o"  # Stronger model
    return "gpt-4o-mini"  # Budget model

COMPLEX_OPS = {
    "deep_analyze_job",
    "self_improving_match", 
    "complex_reasoning"
}
'''
    },
    'vague_prompt': {
        'cause': 'Vague prompt',
        'evidence': 'Judge noted unclear instructions',
        'fix': 'Clarify prompt',
        'action': 'Add specific instructions and format requirements',
        'effort': 'Low',
        'impact': 'Medium — improves consistency',
        'code_template': '''# Clarify prompt structure
CLEAR_PROMPT = """## Task
{specific_task_description}

## Requirements
- Requirement 1: {detail}
- Requirement 2: {detail}

## Output Format
Return a JSON object with:
- field1: description
- field2: description

## Example
{example_input} → {example_output}

## Input
{actual_input}
"""
'''
    },
    'no_examples': {
        'cause': 'No examples',
        'evidence': 'Format issues in response',
        'fix': 'Add few-shot examples',
        'action': 'Include examples in prompt',
        'effort': 'Low',
        'impact': 'Medium — improves format compliance',
        'code_template': '''# Add few-shot examples
FEW_SHOT_PROMPT = """Score how well this resume matches the job.

## Example 1
Resume: Python developer with 5 years AWS experience
Job: Senior Cloud Engineer
Output: {"score": 85, "reason": "Strong cloud alignment"}

## Example 2  
Resume: Marketing coordinator
Job: Senior Cloud Engineer
Output: {"score": 15, "reason": "No technical background"}

## Your Task
Resume: {resume}
Job: {job}
Output:"""
'''
    },
}


def infer_root_cause(row: pd.Series) -> Dict[str, Any]:
    """Infer root cause from evaluation data."""
    eval_data = row.get('eval_data', {}) or {}
    
    # Check if root cause already provided
    if eval_data.get('root_cause'):
        return eval_data['root_cause']
    
    # Infer from signals
    hallucination = row.get('hallucination', False)
    factual_error = row.get('factual_error', False)
    reasoning = row.get('reasoning', '').lower()
    prompt = str(row.get('prompt', '')).lower()
    
    # Check for grounding issues
    has_context = any(x in prompt for x in ['context:', 'resume:', 'document:', 'source:'])
    
    if hallucination and not has_context:
        return ROOT_CAUSE_FIX_MAP['no_grounding']
    
    if hallucination and has_context:
        return ROOT_CAUSE_FIX_MAP['weak_grounding']
    
    if factual_error:
        return ROOT_CAUSE_FIX_MAP['no_verification']
    
    # Check reasoning for clues
    if 'unclear' in reasoning or 'vague' in reasoning:
        return ROOT_CAUSE_FIX_MAP['vague_prompt']
    
    if 'format' in reasoning or 'structure' in reasoning:
        return ROOT_CAUSE_FIX_MAP['no_examples']
    
    # Default for low scores
    if row.get('judge_score', 10) < 5:
        return ROOT_CAUSE_FIX_MAP['weak_model']
    
    return {}


# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_kpi_cards(df: pd.DataFrame):
    """Render summary KPI cards."""
    col1, col2, col3, col4 = st.columns(4)
    
    total_evaluated = len(df)
    avg_score = df['judge_score'].mean() if not df.empty else 0
    issues_count = df['has_issue'].sum() if not df.empty else 0
    
    # Gaps = operations with no evaluations (would need separate query)
    unique_ops = df['operation'].nunique() if not df.empty else 0
    
    with col1:
        st.metric("📊 Evaluated", f"{total_evaluated:,}")
    
    with col2:
        color = "normal" if avg_score >= 7 else "off" if avg_score >= 5 else "inverse"
        st.metric("⭐ Avg Score", f"{avg_score:.1f}/10")
    
    with col3:
        st.metric("🚨 Issues", f"{issues_count:,}", 
                  delta=f"{issues_count/total_evaluated*100:.0f}%" if total_evaluated > 0 else "0%",
                  delta_color="inverse")
    
    with col4:
        st.metric("📋 Operations", f"{unique_ops}")


def render_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Render filter controls and return filtered dataframe."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_options = ['All'] + sorted(df['status'].unique().tolist()) if not df.empty else ['All']
        selected_status = st.selectbox("Status", status_options)
    
    with col2:
        op_options = ['All'] + sorted(df['operation'].unique().tolist()) if not df.empty else ['All']
        selected_op = st.selectbox("Operation", op_options)
    
    with col3:
        model_options = ['All'] + sorted(df['model_name'].unique().tolist()) if not df.empty else ['All']
        selected_model = st.selectbox("Model", model_options)
    
    # Apply filters
    filtered = df.copy()
    if selected_status != 'All':
        filtered = filtered[filtered['status'] == selected_status]
    if selected_op != 'All':
        filtered = filtered[filtered['operation'] == selected_op]
    if selected_model != 'All':
        filtered = filtered[filtered['model_name'] == selected_model]
    
    return filtered


def render_evaluations_table(df: pd.DataFrame):
    """Render main evaluations table with expandable rows."""
    if df.empty:
        st.info("No evaluations found for the selected filters.")
        return
    
    st.markdown("### 📋 Evaluations")
    
    # Display columns
    display_df = df[['time', 'agent_operation', 'judge_score', 'status', 'model_name']].copy()
    display_df.columns = ['Time', 'Agent.Operation', 'Score', 'Status', 'Model']
    
    # Show as dataframe with selection
    for idx, row in df.iterrows():
        with st.expander(
            f"**{row['time']}** — {row['agent_operation']} — "
            f"**{row['judge_score']:.1f}/10** {row['status']}"
        ):
            render_evaluation_detail(row)


def render_evaluation_detail(row: pd.Series):
    """Render expanded evaluation detail."""
    has_issue = row.get('has_issue', False)
    
    # 1. 📊 Evaluation Table
    st.markdown("#### 📊 Evaluation")
    eval_data = {
        'Metric': ['Score', 'Status', 'Hallucination', 'Factual Error'],
        'Value': [
            f"{row['judge_score']:.1f}/10",
            row['status'],
            '⚠️ Yes' if row['hallucination'] else '✅ No',
            '⚠️ Yes' if row['factual_error'] else '✅ No'
        ]
    }
    st.table(pd.DataFrame(eval_data))
    
    # 2. 🔍 Root Cause Analysis (only for issues)
    if has_issue:
        root_cause = infer_root_cause(row)
        if root_cause:
            st.markdown("#### 🔍 Root Cause Analysis")
            cause_data = {
                'Cause': [root_cause.get('cause', 'Unknown')],
                'Confidence': ['High' if row['confidence'] > 0.7 else 'Medium'],
                'Evidence': [root_cause.get('evidence', 'See judge feedback')]
            }
            st.table(pd.DataFrame(cause_data))
            
            # 3. 🛠️ Recommended Fix (only for issues)
            st.markdown("#### 🛠️ Recommended Fix")
            fix_data = {
                'Action': [root_cause.get('action', root_cause.get('fix', 'Review prompt'))],
                'Effort': [root_cause.get('effort', 'Medium')],
                'Impact': [root_cause.get('impact', 'Medium')]
            }
            st.table(pd.DataFrame(fix_data))
    
    # 4. 💬 Judge Feedback (always visible)
    st.markdown("#### 💬 Judge Feedback")
    st.info(row['reasoning'] or "No feedback provided")
    
    # 5. 📝 Prompt (always visible)
    st.markdown("#### 📝 Prompt")
    prompt_text = row.get('prompt', 'No prompt recorded')
    if len(str(prompt_text)) > 500:
        st.text_area("", prompt_text[:2000] + "..." if len(str(prompt_text)) > 2000 else prompt_text, 
                     height=150, disabled=True, label_visibility="collapsed")
    else:
        st.code(prompt_text, language=None)
    
    # 6. 📝 Response (always visible)
    st.markdown("#### 📝 Response")
    response_text = row.get('response_text', 'No response recorded')
    if len(str(response_text)) > 500:
        st.text_area("", response_text[:2000] + "..." if len(str(response_text)) > 2000 else response_text,
                     height=150, disabled=True, label_visibility="collapsed")
    else:
        st.code(response_text, language=None)
    
    # 7. 📋 Implementation Code (collapsed, only for issues)
    if has_issue:
        root_cause = infer_root_cause(row)
        if root_cause and root_cause.get('code_template'):
            with st.expander("📋 Implementation Code"):
                st.code(root_cause['code_template'], language='python')


def render_by_operation_table(df: pd.DataFrame):
    """Render summary by operation."""
    if df.empty:
        return
    
    st.markdown("### 📊 By Operation")
    
    op_summary = df.groupby('operation').agg({
        'id': 'count',
        'judge_score': 'mean',
        'has_issue': 'sum'
    }).reset_index()
    
    op_summary.columns = ['Operation', 'Evaluated', 'Avg Score', 'Issues']
    op_summary['Status'] = op_summary.apply(
        lambda r: '🚨' if r['Issues'] > 0 else '✅', axis=1
    )
    op_summary['Avg Score'] = op_summary['Avg Score'].round(1)
    op_summary = op_summary[['Status', 'Operation', 'Evaluated', 'Avg Score', 'Issues']]
    op_summary = op_summary.sort_values('Issues', ascending=False)
    
    st.dataframe(op_summary, width='stretch', hide_index=True)


def render_root_cause_mapping():
    """Render the root cause → fix mapping reference."""
    st.markdown("### 🗺️ Root Cause → Fix Mapping")
    
    mapping_data = []
    for key, data in ROOT_CAUSE_FIX_MAP.items():
        mapping_data.append({
            'Cause': data['cause'],
            'Evidence': data['evidence'],
            'Fix': data['fix'],
            'Effort': data['effort'],
            'Impact': data['impact'].split('—')[0].strip()
        })
    
    st.dataframe(pd.DataFrame(mapping_data), width='stretch', hide_index=True)


def render_score_distribution(df: pd.DataFrame):
    """Render score distribution chart."""
    if df.empty:
        return
    
    st.markdown("### 📈 Score Distribution")
    
    fig = px.histogram(
        df, 
        x='judge_score', 
        nbins=10,
        color='status',
        title='Quality Score Distribution',
        labels={'judge_score': 'Judge Score', 'count': 'Count'}
    )
    fig.update_layout(
        xaxis_range=[0, 10],
        bargap=0.1,
        height=300
    )
    st.plotly_chart(fig, width='stretch')


def render_issues_over_time(df: pd.DataFrame):
    """Render issues trend over time."""
    if df.empty:
        return
    
    daily = df.groupby('date').agg({
        'id': 'count',
        'has_issue': 'sum',
        'judge_score': 'mean'
    }).reset_index()
    daily.columns = ['Date', 'Total', 'Issues', 'Avg Score']
    daily['Issue Rate'] = (daily['Issues'] / daily['Total'] * 100).round(1)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily['Date'], y=daily['Avg Score'],
        mode='lines+markers', name='Avg Score',
        yaxis='y'
    ))
    fig.add_trace(go.Bar(
        x=daily['Date'], y=daily['Issues'],
        name='Issues', yaxis='y2',
        opacity=0.5
    ))
    fig.update_layout(
        title='Quality Trend',
        yaxis=dict(title='Avg Score', range=[0, 10]),
        yaxis2=dict(title='Issues', overlaying='y', side='right'),
        height=300,
        legend=dict(orientation='h', yanchor='bottom', y=1.02)
    )
    st.plotly_chart(fig, width='stretch')


# =============================================================================
# MAIN RENDER FUNCTION
# =============================================================================

def render():
    """Main render function called by dashboard app.py."""
    st.title("⚖️ LLM Judge")
    st.markdown("Quality evaluation analytics with root cause analysis")
    
    # Date range selector
    col1, col2 = st.columns([1, 3])
    with col1:
        date_range = st.selectbox(
            "Time Range",
            ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "Custom"],
            index=1
        )
    
    # Calculate dates
    now = datetime.now()
    if date_range == "Last 24 Hours":
        start_date = (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    elif date_range == "Last 7 Days":
        start_date = (now - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    elif date_range == "Last 30 Days":
        start_date = (now - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    else:
        with col2:
            start_date = st.date_input("Start", now - timedelta(days=7))
            start_date = start_date.strftime('%Y-%m-%d 00:00:00')
    
    end_date = now.strftime('%Y-%m-%d 23:59:59')
    
    # Load data
    df = load_judge_data(start_date, end_date)
    
    # Summary KPIs
    render_kpi_cards(df)
    
    st.divider()
    
    # Filters
    filtered_df = render_filters(df)
    
    # Main content in tabs
    tab1, tab2, tab3 = st.tabs(["📋 Evaluations", "📊 Analytics", "🗺️ Fix Guide"])
    
    with tab1:
        render_evaluations_table(filtered_df)
    
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            render_score_distribution(filtered_df)
        with col2:
            render_issues_over_time(filtered_df)
        
        render_by_operation_table(filtered_df)
    
    with tab3:
        render_root_cause_mapping()
        
        st.markdown("---")
        st.markdown("""
        ### How It Works
        
        1. **Evaluation** — Each LLM response is scored by a judge model
        2. **Issue Detection** — Hallucinations, factual errors, and low scores are flagged
        3. **Root Cause** — System infers why the issue occurred
        4. **Fix Recommendation** — Actionable fix with implementation code
        
        ### Interpreting Scores
        
        | Score | Meaning |
        |-------|---------|
        | 8-10 | ✅ Good — Response is accurate and complete |
        | 5-7 | ➖ Acceptable — Minor issues, usable |
        | 3-5 | 📉 Low — Significant quality issues |
        | 0-3 | 🚨 Critical — Major errors, unusable |
        """)


# Allow standalone running for testing
if __name__ == "__main__":
    render()