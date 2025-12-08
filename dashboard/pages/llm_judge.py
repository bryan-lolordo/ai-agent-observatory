"""
LLM Judge - Quality Diagnostics Dashboard
Location: dashboard/pages/llm_judge.py

Developer-focused quality analysis:
1. Overview - Quality health and coverage
2. Failures - Low-quality calls with root cause
3. Hallucinations - Detected hallucinations
4. Coverage Gaps - Operations without evaluation
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
from collections import defaultdict

from dashboard.utils.data_fetcher import (
    get_project_overview,
    get_llm_calls,
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

QUALITY_THRESHOLD = 7.0
GOOD_QUALITY_THRESHOLD = 8.0


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def analyze_quality_coverage(calls: List[Dict]) -> Dict[str, Any]:
    """Analyze quality evaluation coverage."""
    
    total = len(calls)
    evaluated = [c for c in calls if (c.get('quality_evaluation') or {}).get('score') is not None]
    
    # By operation
    by_operation = defaultdict(lambda: {'total': 0, 'evaluated': 0, 'scores': [], 'issues': 0})
    
    for call in calls:
        op = call.get('operation', 'unknown')
        by_operation[op]['total'] += 1
        
        qual = call.get('quality_evaluation') or {}
        if qual.get('score') is not None:
            by_operation[op]['evaluated'] += 1
            by_operation[op]['scores'].append(qual['score'])
            
            if qual['score'] < QUALITY_THRESHOLD or qual.get('hallucination') or qual.get('factual_error'):
                by_operation[op]['issues'] += 1
    
    # Calculate averages
    operations = []
    for op, stats in by_operation.items():
        avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else None
        coverage = stats['evaluated'] / stats['total'] if stats['total'] > 0 else 0
        
        if coverage == 0:
            status = 'NOT_EVALUATED'
        elif avg_score and avg_score < QUALITY_THRESHOLD:
            status = 'LOW_QUALITY'
        elif stats['issues'] > 0:
            status = 'HAS_ISSUES'
        else:
            status = 'HEALTHY'
        
        operations.append({
            'operation': op,
            'total': stats['total'],
            'evaluated': stats['evaluated'],
            'coverage': coverage,
            'avg_score': avg_score,
            'issues': stats['issues'],
            'status': status,
        })
    
    operations.sort(key=lambda x: (x['status'] != 'NOT_EVALUATED', x['avg_score'] or 0))
    
    return {
        'total_calls': total,
        'evaluated_calls': len(evaluated),
        'coverage_rate': len(evaluated) / total if total > 0 else 0,
        'operations': operations,
    }


def find_quality_failures(calls: List[Dict]) -> List[Dict]:
    """Find calls with quality issues."""
    
    failures = []
    
    for call in calls:
        qual = call.get('quality_evaluation') or {}
        if not qual or qual.get('score') is None:
            continue
        
        score = qual.get('score', 10)
        has_hallucination = qual.get('hallucination', False)
        has_error = qual.get('factual_error', False)
        
        if score < QUALITY_THRESHOLD or has_hallucination or has_error:
            # Determine root cause
            if has_hallucination:
                root_cause = 'HALLUCINATION'
                cause_detail = 'Response contains fabricated information'
            elif has_error:
                root_cause = 'FACTUAL_ERROR'
                cause_detail = 'Response contains incorrect facts'
            elif score < 5.0:
                root_cause = 'VERY_LOW_QUALITY'
                cause_detail = 'Response failed to address the query adequately'
            elif score < QUALITY_THRESHOLD:
                root_cause = 'LOW_QUALITY'
                cause_detail = 'Response quality below threshold'
            else:
                root_cause = 'UNKNOWN'
                cause_detail = 'Quality issue detected'
            
            failures.append({
                'call': call,
                'score': score,
                'has_hallucination': has_hallucination,
                'has_error': has_error,
                'root_cause': root_cause,
                'cause_detail': cause_detail,
                'judge_feedback': qual.get('reasoning', qual.get('judge_feedback', 'No feedback available')),
                'failure_reason': qual.get('failure_reason', root_cause),
                'improvement_suggestion': qual.get('improvement_suggestion', ''),
            })
    
    # Sort by severity (lowest score first)
    failures.sort(key=lambda x: x['score'])
    
    return failures


def find_hallucinations(calls: List[Dict]) -> List[Dict]:
    """Find calls with hallucination flags."""
    
    hallucinations = []
    
    for call in calls:
        qual = call.get('quality_evaluation') or {}
        if qual.get('hallucination'):
            hallucinations.append({
                'call': call,
                'score': qual.get('score', 0),
                'judge_feedback': qual.get('reasoning', qual.get('judge_feedback', 'No details available')),
                'hallucination_details': qual.get('hallucination_details', ''),
            })
    
    return hallucinations


def find_coverage_gaps(calls: List[Dict]) -> List[Dict]:
    """Find operations without quality evaluation."""
    
    by_operation = defaultdict(lambda: {'total': 0, 'evaluated': 0, 'calls': []})
    
    for call in calls:
        op = call.get('operation', 'unknown')
        by_operation[op]['total'] += 1
        by_operation[op]['calls'].append(call)
        
        if (call.get('quality_evaluation') or {}).get('score') is not None:
            by_operation[op]['evaluated'] += 1
    
    gaps = []
    for op, stats in by_operation.items():
        coverage = stats['evaluated'] / stats['total'] if stats['total'] > 0 else 0
        
        if coverage < 0.5:  # Less than 50% coverage
            # Analyze why this should be evaluated
            sample_calls = stats['calls'][:5]
            avg_cost = sum(c.get('total_cost', 0) for c in stats['calls']) / len(stats['calls'])
            avg_tokens = sum(c.get('total_tokens', 0) for c in stats['calls']) / len(stats['calls'])
            
            # Determine importance
            if avg_cost > 0.05:
                importance = 'HIGH'
                reason = 'High cost per call — quality issues are expensive'
            elif 'sql' in op.lower() or 'code' in op.lower():
                importance = 'HIGH'
                reason = 'Code/SQL generation — errors have high impact'
            elif 'analysis' in op.lower() or 'match' in op.lower():
                importance = 'MEDIUM'
                reason = 'Analysis task — quality affects decisions'
            else:
                importance = 'MEDIUM'
                reason = 'Should monitor for quality consistency'
            
            gaps.append({
                'operation': op,
                'total_calls': stats['total'],
                'evaluated': stats['evaluated'],
                'coverage': coverage,
                'importance': importance,
                'reason': reason,
                'avg_cost': avg_cost,
                'avg_tokens': avg_tokens,
                'sample_calls': sample_calls,
            })
    
    gaps.sort(key=lambda x: (x['importance'] != 'HIGH', -x['total_calls']))
    
    return gaps


def calculate_quality_kpis(calls: List[Dict]) -> Dict[str, Any]:
    """Calculate quality KPIs."""
    
    evaluated = [c for c in calls if (c.get('quality_evaluation') or {}).get('score') is not None]
    
    if not evaluated:
        return {
            'avg_score': 0,
            'hallucination_rate': 0,
            'error_rate': 0,
            'low_quality_rate': 0,
            'total_evaluated': 0,
        }
    
    scores = [c['quality_evaluation']['score'] for c in evaluated]
    hallucinations = sum(1 for c in evaluated if c['quality_evaluation'].get('hallucination'))
    errors = sum(1 for c in evaluated if c['quality_evaluation'].get('factual_error'))
    low_quality = sum(1 for c in evaluated if c['quality_evaluation']['score'] < QUALITY_THRESHOLD)
    
    return {
        'avg_score': sum(scores) / len(scores),
        'hallucination_rate': hallucinations / len(evaluated),
        'error_rate': errors / len(evaluated),
        'low_quality_rate': low_quality / len(evaluated),
        'total_evaluated': len(evaluated),
    }


# =============================================================================
# RENDERING FUNCTIONS
# =============================================================================

def render_quality_status_banner(coverage: Dict, kpis: Dict):
    """Render quality status banner."""
    
    coverage_rate = coverage['coverage_rate']
    
    issues_count = sum(1 for op in coverage['operations'] if op['status'] in ['LOW_QUALITY', 'HAS_ISSUES'])
    gaps_count = sum(1 for op in coverage['operations'] if op['status'] == 'NOT_EVALUATED')
    
    if coverage_rate < 0.3:
        st.error(f"🔴 **Low Coverage** — Only {format_percentage(coverage_rate)} of calls evaluated. {gaps_count} operations not monitored.")
    elif issues_count > 0:
        st.warning(f"🟡 **{coverage['evaluated_calls']} calls evaluated** — {issues_count} operations have quality issues")
    else:
        st.success(f"🟢 **Quality Healthy** — {format_percentage(coverage_rate)} coverage, avg score {kpis['avg_score']:.1f}/10")


def render_failure_card(failure: Dict, index: int):
    """Render a quality failure card."""
    
    call = failure['call']
    
    severity_icon = "🔴" if failure['score'] < 5.0 else "🟡"
    
    st.markdown(f"### {severity_icon} #{index} — Score: {failure['score']:.1f}/10 — {call.get('operation', 'unknown')}")
    st.caption(f"{call.get('agent_name', 'unknown')} • {format_model_name(call.get('model_name', ''))} • {format_cost(call.get('total_cost', 0))}")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("**Root Cause:**")
        st.error(f"{failure['root_cause']}: {failure['cause_detail']}")
        
        if failure['has_hallucination']:
            st.markdown("🚨 **Hallucination detected**")
        if failure['has_error']:
            st.markdown("❌ **Factual error detected**")
    
    with col2:
        st.markdown("**Judge Feedback:**")
        st.info(failure['judge_feedback'][:300] if failure['judge_feedback'] else "No feedback available")
    
    with st.expander("📝 View Prompt & Response"):
        st.markdown("**Prompt:**")
        st.code(truncate_text(call.get('prompt', 'N/A'), 400), language="text")
        
        st.markdown("**Response:**")
        st.code(truncate_text(call.get('response_text', call.get('response', 'N/A')), 400), language="text")
    
    if failure['improvement_suggestion']:
        st.markdown("**🛠️ Suggested Fix:**")
        st.success(failure['improvement_suggestion'])


def render_hallucination_card(item: Dict, index: int):
    """Render a hallucination card."""
    
    call = item['call']
    
    st.markdown(f"### 🚨 #{index} — {call.get('operation', 'unknown')} — Score: {item['score']:.1f}/10")
    st.caption(f"{call.get('agent_name', 'unknown')} • {format_model_name(call.get('model_name', ''))}")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("**What was hallucinated:**")
        st.error(item['hallucination_details'] if item['hallucination_details'] else "Fabricated or unsupported information in response")
    
    with col2:
        st.markdown("**Judge Feedback:**")
        st.info(item['judge_feedback'][:300] if item['judge_feedback'] else "No details")
    
    with st.expander("📝 View Response"):
        st.code(truncate_text(call.get('response_text', call.get('response', 'N/A')), 500), language="text")
    
    st.markdown("**🛠️ Fix Suggestions:**")
    st.write("- Add grounding context (RAG, retrieved documents)")
    st.write("- Include source citations requirement in prompt")
    st.write("- Use a more factual model for this task")


def render_gap_card(gap: Dict, index: int):
    """Render a coverage gap card."""
    
    importance_color = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}
    
    st.markdown(f"### {importance_color.get(gap['importance'], '⚪')} #{index} — {gap['operation']} — {gap['total_calls']} calls")
    st.caption(f"{format_percentage(gap['coverage'])} coverage • {format_cost(gap['avg_cost'])}/call avg")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("**Why evaluate this?**")
        st.info(gap['reason'])
        
        st.write(f"- Total calls: {gap['total_calls']}")
        st.write(f"- Currently evaluated: {gap['evaluated']}")
        st.write(f"- Avg tokens: {format_tokens(int(gap['avg_tokens']))}")
    
    with col2:
        st.markdown("**Suggested criteria:**")
        
        op = gap['operation'].lower()
        if 'sql' in op:
            st.write("- Is SQL syntactically valid?")
            st.write("- Does it answer the question?")
            st.write("- Are table/column names correct?")
        elif 'extract' in op:
            st.write("- Are all entities found?")
            st.write("- Is formatting correct?")
            st.write("- Any false positives?")
        elif 'chat' in op:
            st.write("- Is response helpful?")
            st.write("- Is tone appropriate?")
            st.write("- Any hallucinations?")
        else:
            st.write("- Does output match intent?")
            st.write("- Is quality consistent?")
            st.write("- Any factual errors?")


def render_overview_tab(calls: List[Dict], coverage: Dict, kpis: Dict):
    """Render Overview tab."""
    
    st.subheader("📊 Quality Overview")
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Evaluated", f"{coverage['evaluated_calls']}/{coverage['total_calls']}", 
                  help=f"{format_percentage(coverage['coverage_rate'])} coverage")
    with col2:
        st.metric("Avg Score", f"{kpis['avg_score']:.1f}/10" if kpis['avg_score'] > 0 else "—")
    with col3:
        st.metric("Hallucination Rate", format_percentage(kpis['hallucination_rate']))
    with col4:
        st.metric("Error Rate", format_percentage(kpis['error_rate']))
    
    st.divider()
    
    # By operation table
    st.subheader("🎯 Quality by Operation")
    
    op_data = []
    for op in coverage['operations']:
        status_display = {
            'NOT_EVALUATED': '⚪ Not evaluated',
            'LOW_QUALITY': '🔴 Low quality',
            'HAS_ISSUES': '🟡 Has issues',
            'HEALTHY': '🟢 Healthy',
        }
        
        op_data.append({
            'Operation': op['operation'],
            'Evaluated': f"{op['evaluated']}/{op['total']}",
            'Avg Score': f"{op['avg_score']:.1f}/10" if op['avg_score'] else "—",
            'Issues': op['issues'] if op['issues'] > 0 else "—",
            'Status': status_display.get(op['status'], op['status']),
        })
    
    st.dataframe(pd.DataFrame(op_data), width='stretch', hide_index=True)


def render_failures_tab(failures: List[Dict]):
    """Render Failures tab."""
    
    if not failures:
        st.success("✅ No quality failures detected!")
        st.caption("All evaluated calls meet quality threshold")
        return
    
    st.subheader(f"🔴 {len(failures)} Quality Failures")
    st.caption(f"Calls with score < {QUALITY_THRESHOLD} or errors")
    
    for i, failure in enumerate(failures[:15], 1):
        with st.container():
            render_failure_card(failure, i)
            st.divider()
    
    if len(failures) > 15:
        st.caption(f"Showing top 15 of {len(failures)} failures")


def render_hallucinations_tab(hallucinations: List[Dict]):
    """Render Hallucinations tab."""
    
    if not hallucinations:
        st.success("✅ No hallucinations detected!")
        return
    
    st.subheader(f"🚨 {len(hallucinations)} Hallucinations Detected")
    
    for i, item in enumerate(hallucinations[:10], 1):
        with st.container():
            render_hallucination_card(item, i)
            st.divider()


def render_gaps_tab(gaps: List[Dict]):
    """Render Coverage Gaps tab."""
    
    if not gaps:
        st.success("✅ All operations have quality evaluation!")
        return
    
    st.subheader(f"📍 {len(gaps)} Operations Need Evaluation")
    st.caption("Operations with < 50% quality evaluation coverage")
    
    for i, gap in enumerate(gaps[:10], 1):
        with st.container():
            render_gap_card(gap, i)
            st.divider()


# =============================================================================
# MAIN RENDER
# =============================================================================

def render():
    """Main render function for LLM Judge page."""
    
    st.title("⚖️ Quality Diagnostics")
    st.caption("Find quality issues and how to fix them")
    
    selected_project = st.session_state.get('selected_project')
    
    col1, col2 = st.columns([3, 1])
    with col1:
        if selected_project:
            st.info(f"Analyzing: **{selected_project}**")
    with col2:
        if st.button("🔄 Refresh", width='stretch'):
            st.cache_data.clear()
            st.rerun()
    
    try:
        calls = get_llm_calls(project_name=selected_project, limit=500)
        
        if not calls:
            render_empty_state(
                message="No LLM calls found",
                icon="⚖️",
                suggestion="Start making LLM calls with Observatory tracking enabled"
            )
            return
        
        # Analyze
        with st.spinner("Analyzing quality..."):
            coverage = analyze_quality_coverage(calls)
            kpis = calculate_quality_kpis(calls)
            failures = find_quality_failures(calls)
            hallucinations = find_hallucinations(calls)
            gaps = find_coverage_gaps(calls)
        
        # Status banner
        render_quality_status_banner(coverage, kpis)
        
        st.divider()
        
        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Overview",
            f"🔴 Failures ({len(failures)})",
            f"🚨 Hallucinations ({len(hallucinations)})",
            f"📍 Gaps ({len(gaps)})"
        ])
        
        with tab1:
            render_overview_tab(calls, coverage, kpis)
        
        with tab2:
            render_failures_tab(failures)
        
        with tab3:
            render_hallucinations_tab(hallucinations)
        
        with tab4:
            render_gaps_tab(gaps)
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        import traceback
        st.code(traceback.format_exc())