"""
LLM Judge - Quality Evaluation Dashboard
Location: dashboard/pages/llm_judge.py

Single-scroll layout with filterable evaluations table:
1. Summary KPIs
2. Evaluations table (filterable, sortable, clickable)
3. Expansion with root cause analysis and recommended fixes
4. By Operation summary (click to filter)
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict

from dashboard.utils.data_fetcher import (
    get_llm_calls,
    get_project_overview,
)
from dashboard.utils.formatters import (
    format_cost,
    format_latency,
    format_tokens,
    format_percentage,
    format_model_name,
    truncate_text,
)
from dashboard.components.metric_cards import render_empty_state


# =============================================================================
# CONSTANTS
# =============================================================================

QUALITY_THRESHOLD_LOW = 7.0      # Below this = Low quality
QUALITY_THRESHOLD_OK = 8.0       # Below this = OK, above = Good


# =============================================================================
# STATUS HELPERS
# =============================================================================

def get_quality_status(score: float, has_hallucination: bool, has_error: bool) -> Tuple[str, str]:
    """Get status emoji and label based on quality metrics."""
    if has_hallucination:
        return "🚨", "Hallucination"
    elif has_error:
        return "❌", "Factual Error"
    elif score < QUALITY_THRESHOLD_LOW:
        return "🔴", "Low"
    elif score < QUALITY_THRESHOLD_OK:
        return "🟡", "OK"
    else:
        return "✅", "Good"


def get_operation_status(avg_score: Optional[float], issue_count: int, coverage: float) -> str:
    """Get status for operation summary."""
    if coverage == 0:
        return "⚪"  # Not evaluated
    elif avg_score is not None and avg_score < QUALITY_THRESHOLD_LOW:
        return "🔴"
    elif issue_count > 0:
        return "🟡"
    else:
        return "🟢"


# =============================================================================
# ROOT CAUSE ANALYSIS
# =============================================================================

def analyze_root_cause(call: Dict, quality_eval: Dict) -> Dict[str, Any]:
    """
    Analyze root cause of quality issue and recommend fix.
    
    Returns dict with:
        - cause: str
        - confidence: str (High/Medium/Low)
        - evidence: str
        - fix_action: str
        - fix_effort: str
        - fix_impact: str
        - code_template: str
    """
    score = quality_eval.get('judge_score') or quality_eval.get('score', 10)
    has_hallucination = quality_eval.get('hallucination_flag') or quality_eval.get('hallucination', False)
    has_error = quality_eval.get('factual_error', False)
    feedback = quality_eval.get('reasoning') or quality_eval.get('judge_feedback', '')
    
    model = call.get('model_name', 'unknown')
    prompt = call.get('prompt', '')
    prompt_tokens = call.get('prompt_tokens', 0)
    
    # Check model tier
    model_lower = model.lower()
    is_budget = any(m in model_lower for m in ['3.5', 'haiku', 'mistral', 'mini'])
    is_premium = any(m in model_lower for m in ['gpt-4o', 'gpt-4', 'opus', 'sonnet'])
    
    # Analyze based on symptoms
    
    # 1. Hallucination without grounding
    if has_hallucination:
        # Check if prompt has grounding context
        has_context = any(marker in prompt.lower() for marker in [
            'based on', 'according to', 'given the following', 'context:', 'document:'
        ])
        
        if not has_context:
            return {
                'cause': 'No grounding',
                'confidence': 'High',
                'evidence': 'Hallucination detected, no source context in prompt',
                'fix_action': 'Add RAG',
                'fix_effort': 'Medium',
                'fix_impact': 'High — grounds response in facts',
                'code_template': generate_rag_code(call),
            }
        else:
            return {
                'cause': 'Weak grounding',
                'confidence': 'Medium',
                'evidence': 'Hallucination despite context — may need stronger instructions',
                'fix_action': 'Add explicit constraints',
                'fix_effort': 'Low',
                'fix_impact': 'Medium — reduces fabrication',
                'code_template': generate_constraint_code(call),
            }
    
    # 2. Factual error
    if has_error:
        return {
            'cause': 'No verification',
            'confidence': 'Medium',
            'evidence': 'Factual errors in response',
            'fix_action': 'Add verification step',
            'fix_effort': 'Medium',
            'fix_impact': 'High — catches errors before output',
            'code_template': generate_verification_code(call),
        }
    
    # 3. Low score with budget model on complex task
    if score < QUALITY_THRESHOLD_LOW and is_budget:
        if prompt_tokens > 1000:
            return {
                'cause': 'Weak model',
                'confidence': 'High',
                'evidence': f'Budget model ({format_model_name(model)}) on complex task ({prompt_tokens} tokens)',
                'fix_action': 'Upgrade model',
                'fix_effort': 'Low',
                'fix_impact': 'High — better reasoning',
                'code_template': generate_upgrade_code(call),
            }
    
    # 4. Check for vague prompt indicators
    vague_indicators = ['unclear', 'ambiguous', 'not specific', 'missing context', 'vague']
    if any(indicator in feedback.lower() for indicator in vague_indicators):
        return {
            'cause': 'Vague prompt',
            'confidence': 'Medium',
            'evidence': 'Judge noted unclear or ambiguous instructions',
            'fix_action': 'Clarify prompt',
            'fix_effort': 'Low',
            'fix_impact': 'Medium — clearer intent',
            'code_template': generate_clarity_code(call),
        }
    
    # 5. Check for format issues
    format_indicators = ['format', 'structure', 'inconsistent', 'expected']
    if any(indicator in feedback.lower() for indicator in format_indicators):
        return {
            'cause': 'No examples',
            'confidence': 'Medium',
            'evidence': 'Output format inconsistent with expectations',
            'fix_action': 'Add few-shot examples',
            'fix_effort': 'Low',
            'fix_impact': 'Medium — consistent output',
            'code_template': generate_fewshot_code(call),
        }
    
    # 6. Default - review prompt
    return {
        'cause': 'Unknown',
        'confidence': 'Low',
        'evidence': 'No specific pattern detected',
        'fix_action': 'Review prompt',
        'fix_effort': 'Low',
        'fix_impact': 'Variable',
        'code_template': generate_review_code(call),
    }


# =============================================================================
# CODE TEMPLATES
# =============================================================================

def generate_rag_code(call: Dict) -> str:
    operation = call.get('operation', 'operation')
    return f'''# Add grounding context to prompt
def {operation}_with_rag(query, context_docs):
    prompt = f"""
Based ONLY on the following context:
{{context_docs}}

Answer this query: {{query}}

Important: Do not invent any information not present in the context above.
If the answer is not in the context, say "I don't have that information."
"""
    return call_llm(prompt)'''


def generate_constraint_code(call: Dict) -> str:
    operation = call.get('operation', 'operation')
    return f'''# Add explicit constraints to prevent hallucination
prompt = f"""
{{existing_prompt}}

CRITICAL CONSTRAINTS:
- Only use information explicitly stated in the provided context
- Do not infer, assume, or fabricate any details
- If information is missing, state "Not provided" rather than guessing
- Cite the specific source for each claim
"""'''


def generate_verification_code(call: Dict) -> str:
    operation = call.get('operation', 'operation')
    return f'''# Add verification step
async def {operation}_with_verification(query):
    # Get initial response
    response = await call_llm(query)
    
    # Verify factual claims
    verification_prompt = f"""
Review this response for factual accuracy:
{{response}}

Check each factual claim. List any errors found.
"""
    verification = await call_llm(verification_prompt)
    
    if "error" in verification.lower():
        # Regenerate with corrections
        response = await call_llm(query + f"\\nAvoid these errors: {{verification}}")
    
    return response'''


def generate_upgrade_code(call: Dict) -> str:
    operation = call.get('operation', 'operation')
    agent = call.get('agent_name', 'Agent')
    return f'''# Route complex tasks to stronger model
def route_model(operation: str, prompt_tokens: int) -> str:
    # Complex tasks need better model
    if operation == "{operation}" or prompt_tokens > 1000:
        return "gpt-4o"
    return "gpt-4o-mini"

# In your {agent} plugin:
model = route_model("{operation}", len(prompt.split()) * 1.3)'''


def generate_clarity_code(call: Dict) -> str:
    operation = call.get('operation', 'operation')
    return f'''# Clarify prompt with explicit instructions
prompt = f"""
TASK: [Specific task description]

INPUT:
{{input_data}}

REQUIREMENTS:
1. [Specific requirement 1]
2. [Specific requirement 2]
3. [Specific requirement 3]

OUTPUT FORMAT:
[Exact format expected]

EXAMPLE:
Input: [example input]
Output: [example output]
"""'''


def generate_fewshot_code(call: Dict) -> str:
    operation = call.get('operation', 'operation')
    return f'''# Add few-shot examples for consistent output
prompt = f"""
{{task_description}}

Here are examples of correct outputs:

Example 1:
Input: [example input 1]
Output: [example output 1]

Example 2:
Input: [example input 2]
Output: [example output 2]

Now process this:
Input: {{actual_input}}
Output:"""'''


def generate_review_code(call: Dict) -> str:
    operation = call.get('operation', 'operation')
    return f'''# Review and improve prompt
# Common improvements:
# 1. Be more specific about expected output
# 2. Add constraints and boundaries
# 3. Include examples
# 4. Break complex tasks into steps

# Current prompt for {operation}:
# [Review the prompt in the expansion below]

# Consider:
# - Is the task clearly defined?
# - Are all required inputs provided?
# - Is the expected output format specified?
# - Are there edge cases to handle?'''


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def get_evaluated_calls(calls: List[Dict]) -> List[Dict]:
    """Get calls that have quality evaluation."""
    evaluated = []
    
    for call in calls:
        qual = call.get('quality_evaluation') or {}
        score = qual.get('judge_score') or qual.get('score')
        
        if score is not None:
            has_hallucination = qual.get('hallucination_flag') or qual.get('hallucination', False)
            has_error = qual.get('factual_error', False)
            status_emoji, status_label = get_quality_status(score, has_hallucination, has_error)
            
            evaluated.append({
                'call': call,
                'score': score,
                'has_hallucination': has_hallucination,
                'has_error': has_error,
                'status_emoji': status_emoji,
                'status_label': status_label,
                'feedback': qual.get('reasoning') or qual.get('judge_feedback', ''),
                'agent': call.get('agent_name', 'Unknown'),
                'operation': call.get('operation', 'unknown'),
                'model': call.get('model_name', 'unknown'),
                'timestamp': call.get('timestamp'),
            })
    
    # Sort by timestamp descending
    evaluated.sort(key=lambda x: x['timestamp'] or datetime.min, reverse=True)
    
    return evaluated


def get_quality_issues(evaluated: List[Dict]) -> List[Dict]:
    """Filter to only quality issues."""
    return [
        e for e in evaluated
        if e['score'] < QUALITY_THRESHOLD_LOW or e['has_hallucination'] or e['has_error']
    ]


def get_operation_summary(calls: List[Dict]) -> List[Dict]:
    """Get quality summary by operation."""
    by_operation = defaultdict(lambda: {
        'total': 0,
        'evaluated': 0,
        'scores': [],
        'issues': 0,
    })
    
    for call in calls:
        agent = call.get('agent_name', 'Unknown')
        operation = call.get('operation', 'unknown')
        key = f"{agent}.{operation}"
        
        by_operation[key]['total'] += 1
        
        qual = call.get('quality_evaluation') or {}
        score = qual.get('judge_score') or qual.get('score')
        
        if score is not None:
            by_operation[key]['evaluated'] += 1
            by_operation[key]['scores'].append(score)
            
            has_hallucination = qual.get('hallucination_flag') or qual.get('hallucination', False)
            has_error = qual.get('factual_error', False)
            
            if score < QUALITY_THRESHOLD_LOW or has_hallucination or has_error:
                by_operation[key]['issues'] += 1
    
    summary = []
    for op_key, stats in by_operation.items():
        avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else None
        coverage = stats['evaluated'] / stats['total'] if stats['total'] > 0 else 0
        status = get_operation_status(avg_score, stats['issues'], coverage)
        
        summary.append({
            'operation': op_key,
            'total': stats['total'],
            'evaluated': stats['evaluated'],
            'coverage': coverage,
            'avg_score': avg_score,
            'issues': stats['issues'],
            'status': status,
        })
    
    # Sort: issues first, then by avg score
    summary.sort(key=lambda x: (
        x['status'] != '🔴',
        x['status'] != '🟡',
        -(x['avg_score'] or 0)
    ))
    
    return summary


def get_coverage_gaps(operation_summary: List[Dict]) -> List[Dict]:
    """Get operations with low or no coverage."""
    return [op for op in operation_summary if op['coverage'] < 0.5]


# =============================================================================
# RENDER FUNCTIONS
# =============================================================================

def render_summary_kpis(calls: List[Dict], evaluated: List[Dict], issues: List[Dict], gaps: List[Dict]):
    """Render summary KPI metrics."""
    
    total_calls = len(calls)
    evaluated_count = len(evaluated)
    issue_count = len(issues)
    gap_count = len(gaps)
    
    avg_score = sum(e['score'] for e in evaluated) / len(evaluated) if evaluated else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Evaluated",
            f"{evaluated_count}/{total_calls}",
            help=f"{format_percentage(evaluated_count/total_calls if total_calls else 0)} coverage"
        )
    
    with col2:
        st.metric("Avg Score", f"{avg_score:.1f}/10" if evaluated else "—")
    
    with col3:
        delta = f"{issue_count} need attention" if issue_count > 0 else None
        st.metric("Issues", issue_count, delta=delta, delta_color="inverse")
    
    with col4:
        st.metric("Gaps", f"{gap_count} ops", help="Operations with <50% coverage")


def render_evaluations_table(evaluated: List[Dict], operation_filter: Optional[str] = None, incoming_tab: Optional[str] = None):
    """Render main evaluations table with filters."""
    
    st.subheader("📋 Evaluations")
    
    if not evaluated:
        st.info("No quality evaluations found. Implement LLM-as-judge to see results here.")
        return
    
    # Map incoming_tab to status label
    status_from_nav = None
    if incoming_tab == "hallucinations":
        status_from_nav = "Hallucination"
    elif incoming_tab == "failures":
        status_from_nav = "Low"
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    # Get unique values for filters
    all_statuses = ["All"] + list(set(e['status_label'] for e in evaluated))
    all_operations = ["All"] + list(set(f"{e['agent']}.{e['operation']}" for e in evaluated))
    all_models = ["All"] + list(set(e['model'] for e in evaluated))
    
    with col1:
        # Pre-select status based on incoming navigation
        default_status_idx = 0
        if status_from_nav and status_from_nav in all_statuses:
            default_status_idx = all_statuses.index(status_from_nav)
        
        status_filter = st.selectbox(
            "Status",
            all_statuses,
            index=default_status_idx,
            key="judge_status_filter",
            label_visibility="collapsed"
        )
    
    with col2:
        # If operation_filter passed from By Operation click, use it
        default_op_idx = 0
        if operation_filter and operation_filter in all_operations:
            default_op_idx = all_operations.index(operation_filter)
        
        op_filter = st.selectbox(
            "Operation",
            all_operations,
            index=default_op_idx,
            key="judge_op_filter",
            label_visibility="collapsed"
        )
    
    with col3:
        model_filter = st.selectbox(
            "Model",
            all_models,
            key="judge_model_filter",
            label_visibility="collapsed"
        )
    
    # Apply filters
    filtered = evaluated
    
    if status_filter != "All":
        filtered = [e for e in filtered if e['status_label'] == status_filter]
    
    if op_filter != "All":
        filtered = [e for e in filtered if f"{e['agent']}.{e['operation']}" == op_filter]
    
    if model_filter != "All":
        filtered = [e for e in filtered if e['model'] == model_filter]
    
    if not filtered:
        st.warning("No evaluations match the selected filters.")
        return
    
    # Build table
    table_data = []
    for e in filtered:
        timestamp = e['timestamp']
        time_str = timestamp.strftime("%H:%M") if timestamp else "—"
        
        table_data.append({
            'Time': time_str,
            'Agent.Operation': f"{e['agent']}.{e['operation']}",
            'Score': f"{e['score']:.1f}",
            'Status': f"{e['status_emoji']} {e['status_label']}",
            'Model': format_model_name(e['model']),
        })
    
    df = pd.DataFrame(table_data)
    
    selection = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="judge_eval_table"
    )
    
    st.caption(f"Showing {len(filtered)} of {len(evaluated)} evaluations • Click row for details")
    
    # Show detail for selected row
    selected_rows = selection.selection.rows if selection.selection else []
    if selected_rows and selected_rows[0] < len(filtered):
        render_evaluation_detail(filtered[selected_rows[0]])


def render_evaluation_detail(item: Dict):
    """Render detailed view for a single evaluation."""
    
    st.markdown("---")
    
    call = item['call']
    timestamp = item['timestamp']
    time_str = timestamp.strftime("%H:%M:%S") if timestamp else "—"
    
    st.markdown(f"**▼ {item['agent']}.{item['operation']} @ {time_str} — {item['score']:.1f}/10**")
    
    # Check if this is an issue
    is_issue = item['score'] < QUALITY_THRESHOLD_LOW or item['has_hallucination'] or item['has_error']
    
    # Get root cause if issue
    root_cause = None
    if is_issue:
        qual_eval = call.get('quality_evaluation') or {}
        root_cause = analyze_root_cause(call, qual_eval)
    
    # Table 1: Evaluation | Root Cause | Recommended Fix (3 columns)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Evaluation**")
        eval_data = pd.DataFrame([
            {'': 'Score', ' ': f"{item['score']:.1f}/10"},
            {'': 'Status', ' ': f"{item['status_emoji']} {item['status_label']}"},
            {'': 'Hallucination', ' ': 'Yes' if item['has_hallucination'] else 'No'},
            {'': 'Factual Error', ' ': 'Yes' if item['has_error'] else 'No'},
        ])
        st.dataframe(eval_data, width='stretch', hide_index=True, column_config={
            '': st.column_config.TextColumn(width="small"),
            ' ': st.column_config.TextColumn(width="medium"),
        })
    
    with col2:
        st.markdown("**Root Cause**")
        if root_cause:
            cause_data = pd.DataFrame([
                {'': 'Cause', ' ': root_cause['cause']},
                {'': 'Confidence', ' ': root_cause['confidence']},
                {'': 'Evidence', ' ': truncate_text(root_cause['evidence'], 40)},
            ])
        else:
            cause_data = pd.DataFrame([
                {'': 'Cause', ' ': '—'},
                {'': 'Confidence', ' ': '—'},
                {'': 'Evidence', ' ': 'No issues detected'},
            ])
        st.dataframe(cause_data, width='stretch', hide_index=True, column_config={
            '': st.column_config.TextColumn(width="small"),
            ' ': st.column_config.TextColumn(width="medium"),
        })
    
    with col3:
        st.markdown("**Recommended Fix**")
        if root_cause:
            fix_data = pd.DataFrame([
                {'': 'Action', ' ': root_cause['fix_action']},
                {'': 'Effort', ' ': root_cause['fix_effort']},
                {'': 'Impact', ' ': truncate_text(root_cause['fix_impact'], 40)},
            ])
        else:
            fix_data = pd.DataFrame([
                {'': 'Action', ' ': '—'},
                {'': 'Effort', ' ': '—'},
                {'': 'Impact', ' ': 'No fix needed'},
            ])
        st.dataframe(fix_data, width='stretch', hide_index=True, column_config={
            '': st.column_config.TextColumn(width="small"),
            ' ': st.column_config.TextColumn(width="medium"),
        })
    
    # Table 2: Feedback, Prompt, Response (full content)
    feedback = item['feedback'] or "No feedback provided"
    prompt = call.get('prompt', 'No prompt recorded')
    response = call.get('response_text') or call.get('response', 'No response recorded')
    
    detail_data = pd.DataFrame([
        {'': 'Feedback', '  ': feedback},
        {'': 'Prompt', '  ': prompt},
        {'': 'Response', '  ': response},
    ])
    
    st.dataframe(detail_data, width='stretch', hide_index=True)
    
    # Only implementation code is collapsible
    if is_issue and root_cause:
        with st.expander("📋 Implementation code"):
            st.code(root_cause['code_template'], language="python")


def render_operation_summary(operation_summary: List[Dict]):
    """Render operation summary table."""
    
    st.subheader("📈 By Operation")
    st.caption("Click row to filter evaluations table")
    
    if not operation_summary:
        st.info("No operations found.")
        return
    
    table_data = []
    for op in operation_summary:
        avg_str = f"{op['avg_score']:.1f}" if op['avg_score'] is not None else "—"
        issues_str = str(op['issues']) if op['issues'] > 0 else "—"
        
        table_data.append({
            'Status': op['status'],
            'Operation': op['operation'],
            'Evaluated': f"{op['evaluated']}/{op['total']}",
            'Avg Score': avg_str,
            'Issues': issues_str,
        })
    
    df = pd.DataFrame(table_data)
    
    selection = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="judge_op_summary_table"
    )
    
    # If row selected, update the operation filter
    selected_rows = selection.selection.rows if selection.selection else []
    if selected_rows and selected_rows[0] < len(operation_summary):
        selected_op = operation_summary[selected_rows[0]]['operation']
        st.session_state['judge_op_filter'] = selected_op
        st.rerun()


def render_empty_judge_state():
    """Render state when no quality evaluation data exists."""
    
    st.info("No quality evaluations found in your data.")
    
    st.markdown("---")
    st.subheader("🛠️ How to Add Quality Evaluation")
    
    st.markdown("""
Quality evaluation uses LLM-as-judge to score your AI outputs. Here's how to implement it:
    """)
    
    code = '''# In your plugin, after getting LLM response:
async def evaluate_quality(prompt: str, response: str) -> dict:
    """Use LLM to judge response quality."""
    
    judge_prompt = f"""
Rate this AI response on a scale of 1-10.

Original prompt: {prompt}

AI Response: {response}

Evaluate:
1. Accuracy - Is the information correct?
2. Relevance - Does it answer the question?
3. Completeness - Is anything missing?
4. Hallucination - Is anything made up?

Return JSON:
{{"score": <1-10>, "hallucination": <true/false>, "reasoning": "<explanation>"}}
"""
    
    result = await call_llm(judge_prompt, model="gpt-4o-mini")
    return json.loads(result)

# Track with Observatory
track_llm_call(
    model_name=model,
    prompt_tokens=prompt_tokens,
    completion_tokens=completion_tokens,
    latency_ms=latency_ms,
    agent_name="YourAgent",
    operation="your_operation",
    quality_evaluation={
        "judge_score": eval_result["score"],
        "hallucination_flag": eval_result["hallucination"],
        "reasoning": eval_result["reasoning"],
    }
)'''
    
    st.code(code, language="python")
    
    st.markdown("""
**Tip:** Sample 10-20% of calls for evaluation to save costs:
```python
if random.random() < 0.1:  # 10% sampling
    quality_eval = await evaluate_quality(prompt, response)
```
    """)


# =============================================================================
# MAIN RENDER
# =============================================================================

def render():
    """Main render function for LLM Judge page."""
    
    st.title("⚖️ LLM Judge")
    
    # Check for incoming filter from Home
    # llm_judge_tab values: "hallucinations", "failures"
    incoming_tab = st.session_state.get('llm_judge_tab')
    
    if incoming_tab:
        filter_label = "Hallucinations" if incoming_tab == "hallucinations" else "Low Quality"
        col1, col2 = st.columns([4, 1])
        with col1:
            st.info(f"🎯 Showing: **{filter_label}**")
        with col2:
            if st.button("✕ Clear", key="clear_judge_filter"):
                del st.session_state['llm_judge_tab']
                st.rerun()
    
    selected_project = st.session_state.get('selected_project')
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        project_label = selected_project or "All Projects"
        st.caption(f"Analyzing: **{project_label}**")
    
    with col2:
        limit = st.selectbox(
            "Calls",
            options=[100, 250, 500, 1000],
            index=1,
            format_func=lambda x: f"Last {x}",
            key="judge_limit",
            label_visibility="collapsed"
        )
    
    with col3:
        if st.button("🔄 Refresh", width='stretch', key="judge_refresh"):
            st.cache_data.clear()
            st.rerun()
    
    st.divider()
    
    # Load data
    try:
        calls = get_llm_calls(project_name=selected_project, limit=limit)
        
        if not calls:
            render_empty_state(
                message="No LLM calls found",
                icon="⚖️",
                suggestion="Start making LLM calls with Observatory tracking enabled"
            )
            return
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    # Analyze data
    evaluated = get_evaluated_calls(calls)
    issues = get_quality_issues(evaluated)
    operation_summary = get_operation_summary(calls)
    gaps = get_coverage_gaps(operation_summary)
    
    # Check if any evaluations exist
    if not evaluated:
        render_empty_judge_state()
        return
    
    # Summary KPIs
    render_summary_kpis(calls, evaluated, issues, gaps)
    
    st.divider()
    
    # Main evaluations table (pass incoming filter)
    render_evaluations_table(evaluated, incoming_tab=incoming_tab)
    
    st.divider()
    
    # Operation summary
    render_operation_summary(operation_summary)