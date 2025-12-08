"""
Optimization Impact - Impact Tracker Dashboard
Location: dashboard/pages/optimization_impact.py

Developer-focused impact analysis:
1. Summary - Headline impact with auto-detected comparison
2. Cost Impact - Before/after cost analysis
3. Performance Impact - Latency and quality changes
4. Attribution - What caused the changes
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
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
)
from dashboard.components.metric_cards import render_empty_state


# =============================================================================
# ANALYSIS FUNCTIONS
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
            'cache_hit_rate': 0,
            'routing_rate': 0,
            'model_distribution': {},
        }
    
    total_cost = sum(c.get('total_cost', 0) for c in calls)
    total_tokens = sum(c.get('total_tokens', 0) for c in calls)
    total_latency = sum(c.get('latency_ms', 0) for c in calls)
    errors = sum(1 for c in calls if c.get('error'))
    
    # Quality scores
    scores = [c['quality_evaluation']['score'] for c in calls 
              if (c.get('quality_evaluation') or {}).get('score') is not None]
    avg_quality = sum(scores) / len(scores) if scores else None
    
    # Cache metrics
    cache_calls = [c for c in calls if c.get('cache_metadata')]
    cache_hits = sum(1 for c in cache_calls if (c.get('cache_metadata') or {}).get('cache_hit'))
    cache_hit_rate = cache_hits / len(cache_calls) if cache_calls else 0
    
    # Routing metrics
    routing_calls = [c for c in calls if c.get('routing_decision')]
    routing_rate = len(routing_calls) / len(calls) if calls else 0
    
    # Model distribution
    model_dist = defaultdict(int)
    for call in calls:
        model = call.get('model_name', 'unknown')
        model_dist[model] += 1
    
    return {
        'total_calls': len(calls),
        'total_cost': total_cost,
        'total_tokens': total_tokens,
        'avg_cost': total_cost / len(calls),
        'avg_latency_ms': total_latency / len(calls),
        'avg_tokens': total_tokens / len(calls),
        'error_rate': errors / len(calls),
        'avg_quality': avg_quality,
        'cache_hit_rate': cache_hit_rate,
        'cache_hits': cache_hits,
        'routing_rate': routing_rate,
        'routing_calls': len(routing_calls),
        'model_distribution': dict(model_dist),
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
    
    return {
        'cost_change': abs_change(before['total_cost'], after['total_cost']),
        'cost_change_pct': pct_change(before['total_cost'], after['total_cost'], inverse=True),
        'latency_change': abs_change(before['avg_latency_ms'], after['avg_latency_ms']),
        'latency_change_pct': pct_change(before['avg_latency_ms'], after['avg_latency_ms'], inverse=True),
        'quality_change': abs_change(before['avg_quality'] or 0, after['avg_quality'] or 0) if after['avg_quality'] else None,
        'error_rate_change': abs_change(before['error_rate'], after['error_rate']),
        'cache_hit_change': abs_change(before['cache_hit_rate'], after['cache_hit_rate']),
        'routing_change': abs_change(before['routing_rate'], after['routing_rate']),
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
        # Calculate routing impact
        routing_savings = 0
        for call in after_calls:
            rd = call.get('routing_decision', {})
            routing_savings += rd.get('estimated_cost_savings', 0)
        
        changes.append({
            'type': 'ROUTING_ENABLED',
            'description': 'Model routing enabled',
            'detail': f"Routing rate: {format_percentage(before['routing_rate'])} → {format_percentage(after['routing_rate'])}",
            'impact': -routing_savings if routing_savings else -(after['total_cost'] - before['total_cost']) * 0.6,
            'confidence': 'HIGH' if routing_savings else 'MEDIUM',
        })
    
    # Check for cache improvement
    if after['cache_hit_rate'] > before['cache_hit_rate'] + 0.1:
        cache_savings = (after['cache_hit_rate'] - before['cache_hit_rate']) * after['total_cost']
        
        changes.append({
            'type': 'CACHE_IMPROVED',
            'description': 'Cache hit rate increased',
            'detail': f"Hit rate: {format_percentage(before['cache_hit_rate'])} → {format_percentage(after['cache_hit_rate'])}",
            'impact': -cache_savings,
            'confidence': 'HIGH',
        })
    
    # Check for token reduction (prompt optimization)
    if after['avg_tokens'] < before['avg_tokens'] * 0.85:
        token_savings = (before['avg_tokens'] - after['avg_tokens']) / before['avg_tokens'] * before['total_cost']
        
        changes.append({
            'type': 'PROMPT_OPTIMIZED',
            'description': 'Prompt tokens reduced',
            'detail': f"Avg tokens: {format_tokens(int(before['avg_tokens']))} → {format_tokens(int(after['avg_tokens']))}",
            'impact': -token_savings,
            'confidence': 'MEDIUM',
        })
    
    # Check for model mix change (cheaper models)
    premium_before = sum(v for k, v in before_models.items() if 'gpt-4' in k.lower() or 'opus' in k.lower())
    premium_after = sum(v for k, v in after_models.items() if 'gpt-4' in k.lower() or 'opus' in k.lower())
    
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
    
    # Sort by impact
    changes.sort(key=lambda x: x['impact'])
    
    return changes


# =============================================================================
# RENDERING FUNCTIONS
# =============================================================================

def render_headline_impact(impact: Dict, before: Dict, after: Dict):
    """Render headline impact banner."""
    
    cost_saved = -impact['cost_change'] if impact['cost_change'] < 0 else 0
    cost_increased = impact['cost_change'] if impact['cost_change'] > 0 else 0
    
    if cost_saved > 0:
        st.success(f"""
        💰 **You saved {format_cost(cost_saved)} this period** ({abs(impact['cost_change_pct']):.0f}% cost reduction)
        
        ⚡ Latency: {'+' if impact['latency_change_pct'] < 0 else ''}{abs(impact['latency_change_pct']):.0f}% {'faster' if impact['latency_change'] < 0 else 'slower'}
        {'✅' if impact['quality_change'] and impact['quality_change'] >= 0 else '⚠️'} Quality: {before['avg_quality']:.1f if before['avg_quality'] else '—'} → {after['avg_quality']:.1f if after['avg_quality'] else '—'}
        """)
    elif cost_increased > 0:
        st.warning(f"""
        💸 **Costs increased by {format_cost(cost_increased)} this period** ({abs(impact['cost_change_pct']):.0f}% increase)
        
        Review the Attribution tab to understand what changed.
        """)
    else:
        st.info(f"""
        📊 **Costs stable this period**
        
        Before: {format_cost(before['total_cost'])} | After: {format_cost(after['total_cost'])}
        """)


def render_summary_tab(before: Dict, after: Dict, impact: Dict):
    """Render Summary tab."""
    
    st.subheader("📊 Period Comparison")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown("### Before")
        st.metric("Calls", f"{before['total_calls']:,}")
        st.metric("Total Cost", format_cost(before['total_cost']))
        st.metric("Avg Latency", format_latency(before['avg_latency_ms']))
        if before['avg_quality']:
            st.metric("Avg Quality", f"{before['avg_quality']:.1f}/10")
    
    with col2:
        st.markdown("### After")
        st.metric("Calls", f"{after['total_calls']:,}")
        st.metric("Total Cost", format_cost(after['total_cost']))
        st.metric("Avg Latency", format_latency(after['avg_latency_ms']))
        if after['avg_quality']:
            st.metric("Avg Quality", f"{after['avg_quality']:.1f}/10")
    
    with col3:
        st.markdown("### Change")
        
        call_change = after['total_calls'] - before['total_calls']
        st.metric("Calls", f"{call_change:+,}")
        
        cost_change = impact['cost_change']
        st.metric("Cost", f"{'+' if cost_change > 0 else ''}{format_cost(cost_change)}", 
                  delta=f"{impact['cost_change_pct']:+.0f}%",
                  delta_color="inverse")
        
        latency_change = impact['latency_change']
        st.metric("Latency", f"{'+' if latency_change > 0 else ''}{latency_change:.0f}ms",
                  delta=f"{impact['latency_change_pct']:+.0f}%",
                  delta_color="inverse")
        
        if impact['quality_change'] is not None:
            st.metric("Quality", f"{impact['quality_change']:+.1f}",
                      delta_color="normal")


def render_cost_tab(before: Dict, after: Dict, impact: Dict):
    """Render Cost Impact tab."""
    
    st.subheader("💰 Cost Impact Analysis")
    
    # Cost breakdown
    data = {
        'Metric': [
            'Total Cost',
            'Avg Cost/Call',
            'Avg Tokens/Call',
            'Cost per 1K Tokens',
        ],
        'Before': [
            format_cost(before['total_cost']),
            format_cost(before['avg_cost']),
            format_tokens(int(before['avg_tokens'])),
            format_cost((before['total_cost'] / before['total_tokens'] * 1000) if before['total_tokens'] > 0 else 0),
        ],
        'After': [
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
            'Before': f"{before_count:,} ({before_pct:.0f}%)",
            'After': f"{after_count:,} ({after_pct:.0f}%)",
            'Change': f"{after_pct - before_pct:+.0f}%",
        })
    
    st.dataframe(pd.DataFrame(model_data), width='stretch', hide_index=True)


def render_performance_tab(before: Dict, after: Dict, impact: Dict):
    """Render Performance Impact tab."""
    
    st.subheader("⚡ Performance Impact Analysis")
    
    # Performance metrics
    data = {
        'Metric': [
            'Avg Latency',
            'Error Rate',
            'Avg Quality Score',
            'Cache Hit Rate',
            'Routing Coverage',
        ],
        'Before': [
            format_latency(before['avg_latency_ms']),
            format_percentage(before['error_rate']),
            f"{before['avg_quality']:.1f}/10" if before['avg_quality'] else "—",
            format_percentage(before['cache_hit_rate']),
            format_percentage(before['routing_rate']),
        ],
        'After': [
            format_latency(after['avg_latency_ms']),
            format_percentage(after['error_rate']),
            f"{after['avg_quality']:.1f}/10" if after['avg_quality'] else "—",
            format_percentage(after['cache_hit_rate']),
            format_percentage(after['routing_rate']),
        ],
        'Change': [
            f"{impact['latency_change']:+.0f}ms ({impact['latency_change_pct']:+.0f}%)",
            f"{impact['error_rate_change']*100:+.1f}%",
            f"{impact['quality_change']:+.1f}" if impact['quality_change'] is not None else "—",
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
        st.info("No significant changes detected between periods")
        return
    
    st.caption("Detected changes and their estimated impact")
    
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


# =============================================================================
# MAIN RENDER
# =============================================================================

def render():
    """Main render function for Optimization Impact page."""
    
    st.title("📈 Optimization Impact")
    st.caption("Track the impact of your optimizations")
    
    selected_project = st.session_state.get('selected_project')
    
    # Period selection
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        comparison_mode = st.selectbox(
            "Compare",
            options=["Last 7 days vs Previous 7 days", "Last 30 days vs Previous 30 days", "Custom"],
            key="comparison_mode"
        )
    
    # Calculate dates based on mode
    now = datetime.now()
    
    if comparison_mode == "Last 7 days vs Previous 7 days":
        split_date = now - timedelta(days=7)
        lookback = timedelta(days=14)
    elif comparison_mode == "Last 30 days vs Previous 30 days":
        split_date = now - timedelta(days=30)
        lookback = timedelta(days=60)
    else:
        with col2:
            split_date = st.date_input("Split date", value=now - timedelta(days=7))
            split_date = datetime.combine(split_date, datetime.min.time())
        lookback = timedelta(days=60)
    
    with col3:
        if st.button("🔄 Refresh", width='stretch'):
            st.cache_data.clear()
            st.rerun()
    
    try:
        calls = get_llm_calls(project_name=selected_project, limit=1000)
        
        if not calls:
            render_empty_state(
                message="No LLM calls found",
                icon="📈",
                suggestion="Start making LLM calls with Observatory tracking enabled"
            )
            return
        
        # Split calls
        before_calls, after_calls = split_calls_by_period(calls, split_date)
        
        if not before_calls or not after_calls:
            st.warning("Not enough data in both periods for comparison")
            st.caption(f"Before: {len(before_calls)} calls | After: {len(after_calls)} calls")
            return
        
        # Calculate metrics
        with st.spinner("Analyzing impact..."):
            before_metrics = calculate_period_metrics(before_calls)
            after_metrics = calculate_period_metrics(after_calls)
            impact = calculate_impact(before_metrics, after_metrics)
            changes = detect_changes(before_metrics, after_metrics, before_calls, after_calls)
        
        # Headline
        render_headline_impact(impact, before_metrics, after_metrics)
        
        st.divider()
        
        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Summary",
            "💰 Cost",
            "⚡ Performance",
            f"🎯 Attribution ({len(changes)})"
        ])
        
        with tab1:
            render_summary_tab(before_metrics, after_metrics, impact)
        
        with tab2:
            render_cost_tab(before_metrics, after_metrics, impact)
        
        with tab3:
            render_performance_tab(before_metrics, after_metrics, impact)
        
        with tab4:
            render_attribution_tab(changes, impact)
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        import traceback
        st.code(traceback.format_exc())