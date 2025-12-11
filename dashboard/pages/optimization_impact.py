"""
Optimization Impact - Impact Tracker Dashboard
Location: dashboard/pages/optimization_impact.py

Developer-focused impact analysis:
1. Summary - Headline impact with auto-detected comparison
2. Cost Impact - Before/after cost analysis
3. Performance Impact - Latency and quality changes
4. Attribution - What caused the changes

Supports two comparison modes:
- Phase-based: Compare baseline vs optimized phases (via metadata.phase)
- Time-based: Compare periods (last 7 days vs previous 7 days)
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict
import json

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
)
from dashboard.components.metric_cards import render_empty_state


# =============================================================================
# PHASE EXTRACTION
# =============================================================================

def extract_phase(call: Dict) -> Optional[str]:
    """Extract phase from call metadata."""
    metadata = call.get('metadata')
    if metadata:
        # Handle both dict and JSON string
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                return None
        return metadata.get('phase')
    return None


def split_calls_by_phase(calls: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """Split calls into baseline and optimized phases."""
    
    baseline = []
    optimized = []
    untagged = []
    
    for call in calls:
        phase = extract_phase(call)
        if phase == 'baseline':
            baseline.append(call)
        elif phase == 'optimized':
            optimized.append(call)
        else:
            untagged.append(call)
    
    return baseline, optimized, untagged


def get_phase_stats(calls: List[Dict]) -> Dict[str, int]:
    """Get count of calls per phase."""
    baseline, optimized, untagged = split_calls_by_phase(calls)
    return {
        'baseline': len(baseline),
        'optimized': len(optimized),
        'untagged': len(untagged),
    }


# =============================================================================
# TIME-BASED SPLITTING
# =============================================================================

def split_calls_by_period(calls: List[Dict], split_date: datetime) -> Tuple[List[Dict], List[Dict]]:
    """Split calls into before and after periods."""
    
    before = []
    after = []
    
    for call in calls:
        ts = call.get('timestamp')
        if ts:
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            
            if ts.replace(tzinfo=None) < split_date.replace(tzinfo=None):
                before.append(call)
            else:
                after.append(call)
    
    return before, after


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def calculate_period_metrics(calls: List[Dict]) -> Dict[str, Any]:
    """Calculate comprehensive metrics for a period."""
    
    if not calls:
        return {
            'total_calls': 0,
            'total_cost': 0,
            'total_tokens': 0,
            'avg_cost': 0,
            'avg_latency_ms': 0,
            'avg_tokens': 0,
            'error_rate': 0,
            'avg_quality': None,
            'quality_count': 0,
            'cache_hit_rate': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'routing_rate': 0,
            'routing_calls': 0,
            'routing_savings': 0,
            'model_distribution': {},
            'operation_distribution': {},
            'hallucination_count': 0,
        }
    
    total_cost = sum(c.get('total_cost', 0) or 0 for c in calls)
    total_tokens = sum(c.get('total_tokens', 0) or 0 for c in calls)
    total_latency = sum(c.get('latency_ms', 0) or 0 for c in calls)
    errors = sum(1 for c in calls if c.get('error'))
    
    # Quality scores
    quality_evals = []
    hallucination_count = 0
    for c in calls:
        qe = c.get('quality_evaluation')
        if qe:
            if isinstance(qe, str):
                try:
                    qe = json.loads(qe)
                except:
                    continue
            if qe.get('score') is not None:
                quality_evals.append(qe)
                if qe.get('hallucination') or qe.get('hallucination_flag'):
                    hallucination_count += 1
    
    scores = [q['score'] for q in quality_evals]
    avg_quality = sum(scores) / len(scores) if scores else None
    
    # Cache metrics
    cache_hits = 0
    cache_misses = 0
    for c in calls:
        cm = c.get('cache_metadata')
        if cm:
            if isinstance(cm, str):
                try:
                    cm = json.loads(cm)
                except:
                    continue
            if cm.get('cache_hit'):
                cache_hits += 1
            else:
                cache_misses += 1
    
    total_cache = cache_hits + cache_misses
    cache_hit_rate = cache_hits / total_cache if total_cache > 0 else 0
    
    # Routing metrics
    routing_calls = 0
    total_routing_savings = 0
    for c in calls:
        rd = c.get('routing_decision')
        if rd:
            if isinstance(rd, str):
                try:
                    rd = json.loads(rd)
                except:
                    continue
            routing_calls += 1
            total_routing_savings += rd.get('estimated_cost_savings', 0) or 0
    
    routing_rate = routing_calls / len(calls) if calls else 0
    
    # Model distribution
    model_dist = defaultdict(int)
    for call in calls:
        model = call.get('model_name', 'unknown')
        model_dist[model] += 1
    
    # Operation distribution
    op_dist = defaultdict(int)
    for call in calls:
        op = call.get('operation', 'unknown')
        op_dist[op] += 1
    
    return {
        'total_calls': len(calls),
        'total_cost': total_cost,
        'total_tokens': total_tokens,
        'avg_cost': total_cost / len(calls),
        'avg_latency_ms': total_latency / len(calls),
        'avg_tokens': total_tokens / len(calls),
        'error_rate': errors / len(calls),
        'avg_quality': avg_quality,
        'quality_count': len(quality_evals),
        'cache_hit_rate': cache_hit_rate,
        'cache_hits': cache_hits,
        'cache_misses': cache_misses,
        'routing_rate': routing_rate,
        'routing_calls': routing_calls,
        'routing_savings': total_routing_savings,
        'model_distribution': dict(model_dist),
        'operation_distribution': dict(op_dist),
        'hallucination_count': hallucination_count,
    }


def calculate_impact(before: Dict, after: Dict) -> Dict[str, Any]:
    """Calculate impact between two periods."""
    
    def pct_change(old, new, inverse=False):
        if old == 0:
            return 0 if new == 0 else 100
        change = ((new - old) / old) * 100
        return -change if inverse else change
    
    def abs_change(old, new):
        return new - old
    
    # Estimate cache savings (cache hits × avg cost per call from baseline)
    cache_savings = 0
    if after['cache_hits'] > 0 and before['avg_cost'] > 0:
        cache_savings = after['cache_hits'] * before['avg_cost']
    
    return {
        'cost_change': abs_change(before['total_cost'], after['total_cost']),
        'cost_change_pct': pct_change(before['total_cost'], after['total_cost'], inverse=True),
        'latency_change': abs_change(before['avg_latency_ms'], after['avg_latency_ms']),
        'latency_change_pct': pct_change(before['avg_latency_ms'], after['avg_latency_ms'], inverse=True),
        'quality_change': abs_change(before['avg_quality'] or 0, after['avg_quality'] or 0) if after['avg_quality'] else None,
        'error_rate_change': abs_change(before['error_rate'], after['error_rate']),
        'cache_hit_change': abs_change(before['cache_hit_rate'], after['cache_hit_rate']),
        'cache_savings': cache_savings,
        'routing_change': abs_change(before['routing_rate'], after['routing_rate']),
        'routing_savings': after.get('routing_savings', 0),
        'tokens_change': abs_change(before['avg_tokens'], after['avg_tokens']),
        'tokens_change_pct': pct_change(before['avg_tokens'], after['avg_tokens'], inverse=True),
    }


def detect_changes(before: Dict, after: Dict, before_calls: List[Dict], after_calls: List[Dict]) -> List[Dict]:
    """Detect what changes occurred between periods."""
    
    changes = []
    
    # Model distribution change
    before_models = before['model_distribution']
    after_models = after['model_distribution']
    
    # Check for routing implementation
    if before['routing_rate'] < 0.1 and after['routing_rate'] > 0.2:
        routing_savings = after.get('routing_savings', 0)
        
        changes.append({
            'type': 'ROUTING_ENABLED',
            'description': 'Model routing enabled',
            'detail': f"Routing rate: {format_percentage(before['routing_rate'])} → {format_percentage(after['routing_rate'])} ({after['routing_calls']} routed calls)",
            'impact': -routing_savings if routing_savings else -(before['total_cost'] - after['total_cost']) * 0.4,
            'confidence': 'HIGH' if routing_savings else 'MEDIUM',
        })
    
    # Check for cache implementation
    if before['cache_hit_rate'] < 0.05 and after['cache_hit_rate'] > 0.1:
        cache_savings = after['cache_hits'] * before['avg_cost'] if before['avg_cost'] > 0 else 0
        
        changes.append({
            'type': 'CACHE_ENABLED',
            'description': 'Response caching enabled',
            'detail': f"Cache hits: {after['cache_hits']} ({format_percentage(after['cache_hit_rate'])} hit rate)",
            'impact': -cache_savings,
            'confidence': 'HIGH',
        })
    elif after['cache_hit_rate'] > before['cache_hit_rate'] + 0.1:
        cache_savings = (after['cache_hit_rate'] - before['cache_hit_rate']) * after['total_cost']
        
        changes.append({
            'type': 'CACHE_IMPROVED',
            'description': 'Cache hit rate increased',
            'detail': f"Hit rate: {format_percentage(before['cache_hit_rate'])} → {format_percentage(after['cache_hit_rate'])}",
            'impact': -cache_savings,
            'confidence': 'HIGH',
        })
    
    # Check for quality monitoring enabled
    if before['quality_count'] < 5 and after['quality_count'] > 10:
        changes.append({
            'type': 'QUALITY_MONITORING_ENABLED',
            'description': 'Quality monitoring enabled',
            'detail': f"Evaluations: {before['quality_count']} → {after['quality_count']} ({after['hallucination_count']} hallucinations caught)",
            'impact': 0,
            'confidence': 'HIGH',
        })
    
    # Check for token reduction (prompt optimization)
    if before['avg_tokens'] > 0 and after['avg_tokens'] < before['avg_tokens'] * 0.85:
        token_savings = (before['avg_tokens'] - after['avg_tokens']) / before['avg_tokens'] * before['total_cost']
        
        changes.append({
            'type': 'PROMPT_OPTIMIZED',
            'description': 'Prompt tokens reduced',
            'detail': f"Avg tokens: {format_tokens(int(before['avg_tokens']))} → {format_tokens(int(after['avg_tokens']))}",
            'impact': -token_savings,
            'confidence': 'MEDIUM',
        })
    
    # Check for model mix change (cheaper models)
    premium_before = sum(v for k, v in before_models.items() if 'gpt-4o' in k.lower() and 'mini' not in k.lower())
    premium_after = sum(v for k, v in after_models.items() if 'gpt-4o' in k.lower() and 'mini' not in k.lower())
    
    total_before = sum(before_models.values())
    total_after = sum(after_models.values())
    
    premium_pct_before = premium_before / total_before if total_before > 0 else 0
    premium_pct_after = premium_after / total_after if total_after > 0 else 0
    
    if premium_pct_after < premium_pct_before - 0.15:
        model_savings = (premium_pct_before - premium_pct_after) * after['total_cost'] * 0.7
        
        changes.append({
            'type': 'MODEL_MIX_OPTIMIZED',
            'description': 'Shifted to cheaper models',
            'detail': f"Premium model usage: {format_percentage(premium_pct_before)} → {format_percentage(premium_pct_after)}",
            'impact': -model_savings,
            'confidence': 'MEDIUM',
        })
    
    # Check for quality degradation (warning)
    if before['avg_quality'] and after['avg_quality']:
        if after['avg_quality'] < before['avg_quality'] - 0.5:
            changes.append({
                'type': 'QUALITY_DECREASED',
                'description': '⚠️ Quality decreased',
                'detail': f"Avg score: {before['avg_quality']:.1f} → {after['avg_quality']:.1f}",
                'impact': 0,
                'confidence': 'HIGH',
            })
        elif after['avg_quality'] > before['avg_quality'] + 0.3:
            changes.append({
                'type': 'QUALITY_IMPROVED',
                'description': '✅ Quality improved',
                'detail': f"Avg score: {before['avg_quality']:.1f} → {after['avg_quality']:.1f}",
                'impact': 0,
                'confidence': 'HIGH',
            })
    
    # Check for error rate change
    if after['error_rate'] < before['error_rate'] - 0.05:
        changes.append({
            'type': 'ERRORS_REDUCED',
            'description': 'Error rate decreased',
            'detail': f"Error rate: {format_percentage(before['error_rate'])} → {format_percentage(after['error_rate'])}",
            'impact': 0,
            'confidence': 'HIGH',
        })
    elif after['error_rate'] > before['error_rate'] + 0.05:
        changes.append({
            'type': 'ERRORS_INCREASED',
            'description': '⚠️ Error rate increased',
            'detail': f"Error rate: {format_percentage(before['error_rate'])} → {format_percentage(after['error_rate'])}",
            'impact': 0,
            'confidence': 'HIGH',
        })
    
    # Sort by impact (biggest savings first)
    changes.sort(key=lambda x: x['impact'])
    
    return changes


# =============================================================================
# RENDERING FUNCTIONS
# =============================================================================

def render_headline_impact(impact: Dict, before: Dict, after: Dict, before_label: str = "Before", after_label: str = "After"):
    """Render headline impact banner."""
    
    cost_saved = -impact['cost_change'] if impact['cost_change'] < 0 else 0
    cost_increased = impact['cost_change'] if impact['cost_change'] > 0 else 0
    
    if cost_saved > 0:
        st.success(f"""
        💰 **You saved {format_cost(cost_saved)}** ({abs(impact['cost_change_pct']):.0f}% cost reduction)
        
        ⚡ Latency: {abs(impact['latency_change_pct']):.0f}% {'faster' if impact['latency_change'] < 0 else 'slower'} ({format_latency(before['avg_latency_ms'])} → {format_latency(after['avg_latency_ms'])})
        📊 Cache Hit Rate: {format_percentage(after['cache_hit_rate'])} ({after['cache_hits']} cache hits)
        🔀 Routing: {after['routing_calls']} calls routed
        {'✅' if impact['quality_change'] and impact['quality_change'] >= 0 else '📈'} Quality: {before['avg_quality']:.1f if before['avg_quality'] else '—'} → {after['avg_quality']:.1f if after['avg_quality'] else '—'}
        """)
    elif cost_increased > 0:
        st.warning(f"""
        💸 **Costs increased by {format_cost(cost_increased)}** ({abs(impact['cost_change_pct']):.0f}% increase)
        
        Review the Attribution tab to understand what changed.
        """)
    else:
        st.info(f"""
        📊 **Costs stable**
        
        {before_label}: {format_cost(before['total_cost'])} | {after_label}: {format_cost(after['total_cost'])}
        """)


def render_summary_tab(before: Dict, after: Dict, impact: Dict, before_label: str = "Before", after_label: str = "After"):
    """Render Summary tab."""
    
    st.subheader("📊 Period Comparison")
    
    # Main comparison table
    data = {
        'Metric': [
            'Total Calls',
            'Total Cost',
            'Avg Cost/Call',
            'Avg Latency',
            'Avg Tokens/Call',
            'Cache Hit Rate',
            'Routing Coverage',
            'Avg Quality Score',
            'Error Rate',
        ],
        before_label: [
            f"{before['total_calls']:,}",
            format_cost(before['total_cost']),
            format_cost(before['avg_cost']),
            format_latency(before['avg_latency_ms']),
            format_tokens(int(before['avg_tokens'])),
            format_percentage(before['cache_hit_rate']),
            format_percentage(before['routing_rate']),
            f"{before['avg_quality']:.1f}/10" if before['avg_quality'] else "—",
            format_percentage(before['error_rate']),
        ],
        after_label: [
            f"{after['total_calls']:,}",
            format_cost(after['total_cost']),
            format_cost(after['avg_cost']),
            format_latency(after['avg_latency_ms']),
            format_tokens(int(after['avg_tokens'])),
            format_percentage(after['cache_hit_rate']),
            format_percentage(after['routing_rate']),
            f"{after['avg_quality']:.1f}/10" if after['avg_quality'] else "—",
            format_percentage(after['error_rate']),
        ],
        'Change': [
            f"{after['total_calls'] - before['total_calls']:+,}",
            f"{format_cost(impact['cost_change'])} ({impact['cost_change_pct']:+.0f}%)" if impact['cost_change'] != 0 else "—",
            f"{format_cost(after['avg_cost'] - before['avg_cost'])}",
            f"{impact['latency_change']:+.0f}ms ({impact['latency_change_pct']:+.0f}%)",
            f"{impact['tokens_change']:+.0f} ({impact['tokens_change_pct']:+.0f}%)",
            f"{impact['cache_hit_change']*100:+.1f}%",
            f"{impact['routing_change']*100:+.1f}%",
            f"{impact['quality_change']:+.1f}" if impact['quality_change'] is not None else "—",
            f"{impact['error_rate_change']*100:+.1f}%",
        ],
    }
    
    st.dataframe(pd.DataFrame(data), width='stretch', hide_index=True)


def render_cost_tab(before: Dict, after: Dict, impact: Dict, before_label: str = "Before", after_label: str = "After"):
    """Render Cost Impact tab."""
    
    st.subheader("💰 Cost Impact Analysis")
    
    # Savings breakdown
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_savings = -impact['cost_change'] if impact['cost_change'] < 0 else 0
        st.metric(
            "Total Savings",
            format_cost(total_savings),
            delta=f"{abs(impact['cost_change_pct']):.0f}% reduction" if total_savings > 0 else None,
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            "Cache Savings",
            format_cost(impact['cache_savings']),
            delta=f"{after['cache_hits']} cache hits" if after['cache_hits'] > 0 else None,
        )
    
    with col3:
        st.metric(
            "Routing Savings",
            format_cost(impact['routing_savings']),
            delta=f"{after['routing_calls']} routed calls" if after['routing_calls'] > 0 else None,
        )
    
    st.divider()
    
    # Cost breakdown table
    data = {
        'Metric': [
            'Total Cost',
            'Avg Cost/Call',
            'Avg Tokens/Call',
            'Cost per 1K Tokens',
        ],
        before_label: [
            format_cost(before['total_cost']),
            format_cost(before['avg_cost']),
            format_tokens(int(before['avg_tokens'])),
            format_cost((before['total_cost'] / before['total_tokens'] * 1000) if before['total_tokens'] > 0 else 0),
        ],
        after_label: [
            format_cost(after['total_cost']),
            format_cost(after['avg_cost']),
            format_tokens(int(after['avg_tokens'])),
            format_cost((after['total_cost'] / after['total_tokens'] * 1000) if after['total_tokens'] > 0 else 0),
        ],
        'Change': [
            f"{'+' if impact['cost_change'] > 0 else ''}{format_cost(impact['cost_change'])}",
            f"{'+' if impact['cost_change'] > 0 else ''}{format_cost(after['avg_cost'] - before['avg_cost'])}",
            f"{'+' if impact['tokens_change'] > 0 else ''}{format_tokens(int(impact['tokens_change']))}",
            f"{impact['tokens_change_pct']:+.0f}%",
        ],
    }
    
    st.dataframe(pd.DataFrame(data), width='stretch', hide_index=True)
    
    st.divider()
    
    # Model distribution comparison
    st.subheader("🤖 Model Usage Change")
    
    all_models = set(list(before['model_distribution'].keys()) + list(after['model_distribution'].keys()))
    
    model_data = []
    for model in sorted(all_models):
        before_count = before['model_distribution'].get(model, 0)
        after_count = after['model_distribution'].get(model, 0)
        before_pct = before_count / before['total_calls'] * 100 if before['total_calls'] > 0 else 0
        after_pct = after_count / after['total_calls'] * 100 if after['total_calls'] > 0 else 0
        
        model_data.append({
            'Model': format_model_name(model),
            before_label: f"{before_count:,} ({before_pct:.0f}%)",
            after_label: f"{after_count:,} ({after_pct:.0f}%)",
            'Change': f"{after_pct - before_pct:+.0f}%",
        })
    
    st.dataframe(pd.DataFrame(model_data), width='stretch', hide_index=True)


def render_performance_tab(before: Dict, after: Dict, impact: Dict, before_label: str = "Before", after_label: str = "After"):
    """Render Performance Impact tab."""
    
    st.subheader("⚡ Performance Impact Analysis")
    
    # Performance metrics
    data = {
        'Metric': [
            'Avg Latency',
            'Error Rate',
            'Avg Quality Score',
            'Quality Evaluations',
            'Hallucinations Caught',
            'Cache Hit Rate',
            'Routing Coverage',
        ],
        before_label: [
            format_latency(before['avg_latency_ms']),
            format_percentage(before['error_rate']),
            f"{before['avg_quality']:.1f}/10" if before['avg_quality'] else "—",
            f"{before['quality_count']:,}",
            f"{before['hallucination_count']:,}",
            format_percentage(before['cache_hit_rate']),
            format_percentage(before['routing_rate']),
        ],
        after_label: [
            format_latency(after['avg_latency_ms']),
            format_percentage(after['error_rate']),
            f"{after['avg_quality']:.1f}/10" if after['avg_quality'] else "—",
            f"{after['quality_count']:,}",
            f"{after['hallucination_count']:,}",
            format_percentage(after['cache_hit_rate']),
            format_percentage(after['routing_rate']),
        ],
        'Change': [
            f"{impact['latency_change']:+.0f}ms ({impact['latency_change_pct']:+.0f}%)",
            f"{impact['error_rate_change']*100:+.1f}%",
            f"{impact['quality_change']:+.1f}" if impact['quality_change'] is not None else "—",
            f"{after['quality_count'] - before['quality_count']:+,}",
            f"{after['hallucination_count'] - before['hallucination_count']:+,}",
            f"{impact['cache_hit_change']*100:+.1f}%",
            f"{impact['routing_change']*100:+.1f}%",
        ],
    }
    
    st.dataframe(pd.DataFrame(data), width='stretch', hide_index=True)
    
    # Warnings
    if impact['quality_change'] is not None and impact['quality_change'] < -0.5:
        st.warning("⚠️ **Quality Degradation Detected** — Review prompt changes or model selections")
    
    if impact['error_rate_change'] > 0.05:
        st.warning("⚠️ **Error Rate Increased** — Check for system issues or prompt problems")


def render_attribution_tab(changes: List[Dict], impact: Dict):
    """Render Attribution tab."""
    
    st.subheader("🎯 What Caused the Changes?")
    
    if not changes:
        st.info("No significant changes detected between periods. Try running more operations in each phase.")
        return
    
    st.caption("Detected optimizations and their estimated impact")
    
    total_attributed = sum(c['impact'] for c in changes if c['impact'] < 0)
    
    for change in changes:
        confidence_badge = {
            'HIGH': '🟢',
            'MEDIUM': '🟡',
            'LOW': '🔴',
        }
        
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**{change['description']}**")
                st.caption(change['detail'])
            
            with col2:
                if change['impact'] < 0:
                    st.success(f"**{format_cost(abs(change['impact']))}** saved")
                elif change['impact'] > 0:
                    st.error(f"**{format_cost(change['impact'])}** added")
                else:
                    st.info("No cost impact")
            
            with col3:
                st.write(f"{confidence_badge.get(change['confidence'], '⚪')} {change['confidence']}")
            
            st.divider()
    
    if total_attributed < 0:
        st.success(f"**Total Attributed Savings:** {format_cost(abs(total_attributed))}")


def render_operations_tab(before: Dict, after: Dict, before_label: str = "Before", after_label: str = "After"):
    """Render Operations breakdown tab."""
    
    st.subheader("🔧 Operations Breakdown")
    
    all_ops = set(list(before['operation_distribution'].keys()) + list(after['operation_distribution'].keys()))
    
    if not all_ops:
        st.info("No operation data available")
        return
    
    op_data = []
    for op in sorted(all_ops):
        before_count = before['operation_distribution'].get(op, 0)
        after_count = after['operation_distribution'].get(op, 0)
        
        op_data.append({
            'Operation': op,
            before_label: f"{before_count:,}",
            after_label: f"{after_count:,}",
            'Change': f"{after_count - before_count:+,}",
        })
    
    st.dataframe(pd.DataFrame(op_data), width='stretch', hide_index=True)


# =============================================================================
# MAIN RENDER
# =============================================================================

def render():
    """Main render function for Optimization Impact page."""
    
    st.title("📈 Optimization Impact")
    st.caption("Track the impact of your optimizations — Compare baseline vs optimized or time periods")
    
    selected_project = st.session_state.get('selected_project')
    
    # Load data first to check for phases
    try:
        calls = get_llm_calls(project_name=selected_project, limit=5000)
        
        if not calls:
            render_empty_state(
                message="No LLM calls found",
                icon="📈",
                suggestion="Start making LLM calls with Observatory tracking enabled"
            )
            return
        
        # Check for phase data
        phase_stats = get_phase_stats(calls)
        has_phases = phase_stats['baseline'] > 0 or phase_stats['optimized'] > 0
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    # Comparison mode selection
    st.markdown("### 🔀 Comparison Mode")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        comparison_options = ["📊 By Phase (Baseline vs Optimized)", "📅 By Time Period"]
        if not has_phases:
            comparison_options = ["📅 By Time Period"]  # Only time if no phases
            st.caption("💡 Add `metadata={'phase': 'baseline'}` to enable phase comparison")
        
        comparison_mode = st.selectbox(
            "Compare by",
            options=comparison_options,
            key="comparison_mode"
        )
    
    # Phase stats display
    if has_phases:
        with col2:
            st.caption(f"📊 Phase data: {phase_stats['baseline']} baseline | {phase_stats['optimized']} optimized | {phase_stats['untagged']} untagged")
    
    with col3:
        if st.button("🔄 Refresh", width='stretch'):
            st.cache_data.clear()
            st.rerun()
    
    # Split data based on mode
    if "Phase" in comparison_mode:
        # Phase-based comparison
        baseline_calls, optimized_calls, untagged_calls = split_calls_by_phase(calls)
        
        if not baseline_calls:
            st.warning("⚠️ No **baseline** phase data found. Run your app with `OBSERVATORY_PHASE=baseline`")
            return
        
        if not optimized_calls:
            st.warning("⚠️ No **optimized** phase data found. Run your app with `OBSERVATORY_PHASE=optimized`")
            st.info(f"You have {len(baseline_calls)} baseline calls ready for comparison.")
            return
        
        before_calls = baseline_calls
        after_calls = optimized_calls
        before_label = "Baseline"
        after_label = "Optimized"
        
        st.success(f"✅ Comparing **{len(before_calls)} baseline** calls vs **{len(after_calls)} optimized** calls")
        
    else:
        # Time-based comparison
        col1, col2 = st.columns(2)
        
        with col1:
            time_mode = st.selectbox(
                "Time range",
                options=["Last 7 days vs Previous 7 days", "Last 30 days vs Previous 30 days", "Custom"],
                key="time_mode"
            )
        
        now = datetime.now()
        
        if time_mode == "Last 7 days vs Previous 7 days":
            split_date = now - timedelta(days=7)
            before_label = "Previous 7 days"
            after_label = "Last 7 days"
        elif time_mode == "Last 30 days vs Previous 30 days":
            split_date = now - timedelta(days=30)
            before_label = "Previous 30 days"
            after_label = "Last 30 days"
        else:
            with col2:
                split_date = st.date_input("Split date", value=now - timedelta(days=7))
                split_date = datetime.combine(split_date, datetime.min.time())
            before_label = "Before"
            after_label = "After"
        
        before_calls, after_calls = split_calls_by_period(calls, split_date)
        
        if not before_calls or not after_calls:
            st.warning("Not enough data in both periods for comparison")
            st.caption(f"{before_label}: {len(before_calls)} calls | {after_label}: {len(after_calls)} calls")
            return
    
    # Calculate metrics
    with st.spinner("Analyzing impact..."):
        before_metrics = calculate_period_metrics(before_calls)
        after_metrics = calculate_period_metrics(after_calls)
        impact = calculate_impact(before_metrics, after_metrics)
        changes = detect_changes(before_metrics, after_metrics, before_calls, after_calls)
    
    st.divider()
    
    # Headline
    render_headline_impact(impact, before_metrics, after_metrics, before_label, after_label)
    
    st.divider()
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Summary",
        "💰 Cost",
        "⚡ Performance",
        f"🎯 Attribution ({len(changes)})",
        "🔧 Operations",
    ])
    
    with tab1:
        render_summary_tab(before_metrics, after_metrics, impact, before_label, after_label)
    
    with tab2:
        render_cost_tab(before_metrics, after_metrics, impact, before_label, after_label)
    
    with tab3:
        render_performance_tab(before_metrics, after_metrics, impact, before_label, after_label)
    
    with tab4:
        render_attribution_tab(changes, impact)
    
    with tab5:
        render_operations_tab(before_metrics, after_metrics, before_label, after_label)