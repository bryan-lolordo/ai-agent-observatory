"""
Model Router - Discovery & Active Modes
Location: dashboard/pages/model_router.py

Two-tab layout:
1. Discovery Mode - Find model routing opportunities
2. Active Mode - Monitor routing performance (when routing_decision exists)

Focus: "Am I using the right model for each task?"
- Downgrade candidates: Expensive model + simple task
- Upgrade candidates: Cheap model + poor quality
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict
import re

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

# Model tiers for routing decisions
PREMIUM_MODELS = ['gpt-4o', 'gpt-4', 'gpt-4-turbo', 'claude-3-opus', 'claude-sonnet-4', 'claude-3-5-sonnet']
MID_TIER_MODELS = ['gpt-4o-mini', 'gpt-3.5-turbo', 'claude-3-sonnet', 'claude-3-haiku', 'claude-haiku']
BUDGET_MODELS = ['gpt-3.5-turbo', 'mistral-small', 'mistral-tiny', 'mixtral', 'claude-haiku']

# Thresholds
SIMPLE_TASK_TOKEN_THRESHOLD = 1500  # Tasks under this are "simple"
VERY_SIMPLE_TOKEN_THRESHOLD = 500   # Tasks under this are "very simple"
LOW_QUALITY_THRESHOLD = 7.0          # Quality score below this needs upgrade
HIGH_COST_THRESHOLD = 0.05           # $0.05 per call
SLOW_LATENCY_THRESHOLD = 5000        # 5 seconds


# =============================================================================
# MODEL TIER UTILITIES
# =============================================================================

def get_model_tier(model_name: str) -> str:
    """Get the tier of a model."""
    model_lower = model_name.lower()
    
    for premium in PREMIUM_MODELS:
        if premium.lower() in model_lower:
            return 'premium'
    
    for mid in MID_TIER_MODELS:
        if mid.lower() in model_lower:
            return 'mid'
    
    return 'budget'


def get_suggested_model(current_model: str, direction: str) -> str:
    """Get suggested model for up/downgrade."""
    current_tier = get_model_tier(current_model)
    
    if direction == 'downgrade':
        if current_tier == 'premium':
            return 'gpt-4o-mini'
        elif current_tier == 'mid':
            return 'gpt-3.5-turbo'
        else:
            return current_model  # Already budget
    else:  # upgrade
        if current_tier == 'budget':
            return 'gpt-4o-mini'
        elif current_tier == 'mid':
            return 'gpt-4o'
        else:
            return current_model  # Already premium


def estimate_savings(current_model: str, suggested_model: str, current_cost: float) -> float:
    """Estimate cost savings from model switch."""
    current_tier = get_model_tier(current_model)
    suggested_tier = get_model_tier(suggested_model)
    
    # Rough cost ratios
    if current_tier == 'premium' and suggested_tier == 'mid':
        return current_cost * 0.85  # Save ~85%
    elif current_tier == 'premium' and suggested_tier == 'budget':
        return current_cost * 0.95  # Save ~95%
    elif current_tier == 'mid' and suggested_tier == 'budget':
        return current_cost * 0.70  # Save ~70%
    else:
        return 0


# =============================================================================
# PROMPT COMPONENT PARSING
# =============================================================================

def parse_prompt_components(call: Dict) -> Dict[str, Any]:
    """Parse prompt into components: system prompt, chat history, user message."""
    metadata = call.get('metadata', {}) or {}
    prompt_text = call.get('prompt', '') or ''
    prompt_tokens = call.get('prompt_tokens', 0)
    
    # Try to get from metadata first
    if metadata.get('system_prompt_tokens'):
        return {
            'system_prompt_tokens': metadata.get('system_prompt_tokens', 0),
            'chat_history_tokens': metadata.get('chat_history_tokens', 0),
            'chat_history_count': metadata.get('chat_history_count', 0),
            'user_message_tokens': metadata.get('user_message_tokens', 0),
            'parsed_from': 'metadata'
        }
    
    # Estimate from prompt text
    return estimate_prompt_components(prompt_text, prompt_tokens)


def estimate_prompt_components(prompt_text: str, total_prompt_tokens: int) -> Dict[str, Any]:
    """Estimate prompt components when not available in metadata."""
    
    if not prompt_text:
        return {
            'system_prompt_tokens': 0,
            'chat_history_tokens': 0,
            'chat_history_count': 0,
            'user_message_tokens': total_prompt_tokens,
            'parsed_from': 'estimated_no_prompt'
        }
    
    # Count message patterns to estimate chat history
    message_patterns = [
        r'Human:|User:|Assistant:|AI:|\[User\]|\[Assistant\]',
        r'Message \d+:',
        r'<human>|<assistant>|<user>',
    ]
    
    message_count = 0
    for pattern in message_patterns:
        matches = re.findall(pattern, prompt_text, re.IGNORECASE)
        message_count = max(message_count, len(matches))
    
    # Look for system prompt markers
    system_markers = ['You are', 'System:', '<system>', 'Instructions:']
    has_system = any(marker in prompt_text[:1000] for marker in system_markers)
    
    if message_count > 1:
        # Has chat history
        system_pct = 0.25 if has_system else 0.10
        history_pct = min(0.60, message_count * 0.08)
        user_pct = 1 - system_pct - history_pct
        
        system_tokens = int(total_prompt_tokens * system_pct)
        history_tokens = int(total_prompt_tokens * history_pct)
        user_tokens = int(total_prompt_tokens * user_pct)
    else:
        # No chat history detected
        system_tokens = int(total_prompt_tokens * 0.30) if has_system else 0
        history_tokens = 0
        user_tokens = total_prompt_tokens - system_tokens
    
    return {
        'system_prompt_tokens': system_tokens,
        'chat_history_tokens': history_tokens,
        'chat_history_count': message_count,
        'user_message_tokens': user_tokens,
        'parsed_from': 'estimated'
    }


# =============================================================================
# ROUTING DETECTION
# =============================================================================

def detect_routing_mode(calls: List[Dict]) -> Tuple[bool, Dict]:
    """Detect if routing is active based on routing_decision presence."""
    if not calls:
        return False, {}
    
    calls_with_routing = [c for c in calls if c.get('routing_decision')]
    
    stats = {
        'total_calls': len(calls),
        'routed_calls': len(calls_with_routing),
        'routing_rate': len(calls_with_routing) / len(calls) if calls else 0,
    }
    
    is_active = len(calls_with_routing) >= 5
    
    return is_active, stats


# =============================================================================
# DISCOVERY MODE - ANALYSIS
# =============================================================================

def analyze_routing_opportunities(calls: List[Dict]) -> Dict:
    """Analyze calls to find routing opportunities."""
    
    # Group by operation
    by_operation = defaultdict(list)
    
    for call in calls:
        agent = call.get('agent_name', 'Unknown')
        operation = call.get('operation', 'unknown')
        key = f"{agent}.{operation}"
        by_operation[key].append(call)
    
    downgrade_candidates = []
    upgrade_candidates = []
    optimal = []
    
    for op_key, op_calls in by_operation.items():
        analysis = analyze_operation(op_key, op_calls)
        
        if analysis['recommendation'] == 'downgrade':
            downgrade_candidates.append(analysis)
        elif analysis['recommendation'] == 'upgrade':
            upgrade_candidates.append(analysis)
        else:
            optimal.append(analysis)
    
    # Sort by savings potential
    downgrade_candidates.sort(key=lambda x: -x['potential_savings'])
    upgrade_candidates.sort(key=lambda x: -x['call_count'])  # Most calls first
    
    return {
        'downgrade': downgrade_candidates,
        'upgrade': upgrade_candidates,
        'optimal': optimal,
        'total_savings': sum(d['potential_savings'] for d in downgrade_candidates),
    }


def analyze_operation(op_key: str, calls: List[Dict]) -> Dict:
    """Analyze a single operation for routing opportunities."""
    
    parts = op_key.split('.', 1)
    agent = parts[0] if parts else 'Unknown'
    operation = parts[1] if len(parts) > 1 else 'unknown'
    
    # Aggregate metrics
    total_cost = sum(c.get('total_cost', 0) for c in calls)
    avg_cost = total_cost / len(calls) if calls else 0
    avg_tokens = sum(c.get('total_tokens', 0) for c in calls) / len(calls) if calls else 0
    avg_prompt_tokens = sum(c.get('prompt_tokens', 0) for c in calls) / len(calls) if calls else 0
    avg_latency = sum(c.get('latency_ms', 0) for c in calls) / len(calls) if calls else 0
    
    # Get quality scores if available
    quality_scores = []
    for c in calls:
        qual_eval = c.get('quality_evaluation') or {}
        score = qual_eval.get('judge_score') or qual_eval.get('score')
        if score is not None:
            quality_scores.append(score)
    
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
    
    # Get most common model
    model_counts = defaultdict(int)
    for c in calls:
        model = c.get('model_name', 'unknown')
        model_counts[model] += 1
    
    primary_model = max(model_counts.keys(), key=lambda m: model_counts[m]) if model_counts else 'unknown'
    model_tier = get_model_tier(primary_model)
    
    # Parse prompt components (use first call as sample)
    components = parse_prompt_components(calls[0]) if calls else {}
    
    # Determine recommendation
    recommendation = 'optimal'
    issue_type = None
    issue_reason = None
    suggested_model = primary_model
    potential_savings = 0
    risk = 'Low'
    
    # Check for downgrade opportunities
    if model_tier == 'premium':
        if avg_tokens < VERY_SIMPLE_TOKEN_THRESHOLD:
            recommendation = 'downgrade'
            issue_type = '💸 Costly'
            issue_reason = 'Very simple'
            suggested_model = 'gpt-3.5-turbo'
            potential_savings = estimate_savings(primary_model, suggested_model, total_cost)
            risk = 'Low'
        elif avg_tokens < SIMPLE_TASK_TOKEN_THRESHOLD:
            recommendation = 'downgrade'
            issue_type = '💸 Costly'
            issue_reason = 'Simple task'
            suggested_model = 'gpt-4o-mini'
            potential_savings = estimate_savings(primary_model, suggested_model, total_cost)
            risk = 'Low'
        elif avg_latency > SLOW_LATENCY_THRESHOLD:
            recommendation = 'downgrade'
            issue_type = '🐌 Slow'
            issue_reason = 'High latency'
            suggested_model = 'gpt-4o-mini'
            potential_savings = estimate_savings(primary_model, suggested_model, total_cost)
            risk = 'Medium'
    elif model_tier == 'mid':
        if avg_tokens < VERY_SIMPLE_TOKEN_THRESHOLD:
            recommendation = 'downgrade'
            issue_type = '💸 Costly'
            issue_reason = 'Very simple'
            suggested_model = 'gpt-3.5-turbo'
            potential_savings = estimate_savings(primary_model, suggested_model, total_cost)
            risk = 'Low'
    
    # Check for upgrade opportunities
    if avg_quality is not None and avg_quality < LOW_QUALITY_THRESHOLD:
        if model_tier in ['budget', 'mid']:
            recommendation = 'upgrade'
            issue_type = '⚠️ Quality'
            issue_reason = f'Low quality ({avg_quality:.1f})'
            suggested_model = get_suggested_model(primary_model, 'upgrade')
            potential_savings = 0  # Upgrade costs more
            risk = 'Low'
    
    # Check for failures
    failure_count = sum(1 for c in calls if not c.get('success', True))
    if failure_count > len(calls) * 0.1:  # >10% failures
        if model_tier in ['budget', 'mid']:
            recommendation = 'upgrade'
            issue_type = '❌ Failures'
            issue_reason = f'{failure_count} failures'
            suggested_model = get_suggested_model(primary_model, 'upgrade')
            potential_savings = 0
            risk = 'Low'
    
    return {
        'agent': agent,
        'operation': operation,
        'agent_operation': op_key,
        'call_count': len(calls),
        'primary_model': primary_model,
        'model_tier': model_tier,
        'avg_tokens': avg_tokens,
        'avg_prompt_tokens': avg_prompt_tokens,
        'avg_latency': avg_latency,
        'avg_cost': avg_cost,
        'total_cost': total_cost,
        'avg_quality': avg_quality,
        'failure_count': failure_count,
        'recommendation': recommendation,
        'issue_type': issue_type,
        'issue_reason': issue_reason,
        'suggested_model': suggested_model,
        'potential_savings': potential_savings,
        'risk': risk,
        'components': components,
        'calls': calls,
    }


# =============================================================================
# ACTIVE MODE - ANALYSIS
# =============================================================================

def analyze_routing_performance(calls: List[Dict]) -> Dict:
    """Analyze routing performance when routing_decision exists."""
    
    routed_calls = [c for c in calls if c.get('routing_decision')]
    unrouted_calls = [c for c in calls if not c.get('routing_decision')]
    
    # Analyze rules
    rule_performance = defaultdict(lambda: {
        'fired': 0,
        'total_cost': 0,
        'baseline_cost': 0,
        'quality_scores': [],
        'calls': [],
    })
    
    for call in routed_calls:
        routing = call.get('routing_decision') or {}
        rule = routing.get('rule', routing.get('reasoning', 'unknown'))
        chosen_model = routing.get('chosen_model', call.get('model_name', 'unknown'))
        
        rule_performance[rule]['fired'] += 1
        rule_performance[rule]['total_cost'] += call.get('total_cost', 0)
        rule_performance[rule]['calls'].append(call)
        
        # Estimate baseline cost (if premium model was used)
        if get_model_tier(chosen_model) != 'premium':
            baseline = call.get('total_cost', 0) / 0.15  # Reverse estimate
            rule_performance[rule]['baseline_cost'] += baseline
        else:
            rule_performance[rule]['baseline_cost'] += call.get('total_cost', 0)
        
        # Track quality
        qual_eval = call.get('quality_evaluation') or {}
        score = qual_eval.get('judge_score') or qual_eval.get('score')
        if score is not None:
            rule_performance[rule]['quality_scores'].append(score)
    
    # Calculate savings and status for each rule
    rules = []
    for rule, data in rule_performance.items():
        savings = data['baseline_cost'] - data['total_cost']
        avg_quality = sum(data['quality_scores']) / len(data['quality_scores']) if data['quality_scores'] else None
        
        # Determine status
        if avg_quality is not None and avg_quality < LOW_QUALITY_THRESHOLD:
            status = '🔴'
        elif avg_quality is not None and avg_quality < 7.5:
            status = '🟡'
        else:
            status = '🟢'
        
        rules.append({
            'rule': rule,
            'fired': data['fired'],
            'total_cost': data['total_cost'],
            'savings': savings,
            'avg_quality': avg_quality,
            'status': status,
            'calls': data['calls'],
        })
    
    rules.sort(key=lambda x: -x['fired'])
    
    # Find routing mistakes
    mistakes = []
    for call in routed_calls:
        qual_eval = call.get('quality_evaluation') or {}
        score = qual_eval.get('judge_score') or qual_eval.get('score')
        
        if score is not None and score < LOW_QUALITY_THRESHOLD:
            routing = call.get('routing_decision') or {}
            chosen_model = routing.get('chosen_model', call.get('model_name', 'unknown'))
            
            if get_model_tier(chosen_model) != 'premium':
                mistakes.append({
                    'call': call,
                    'model': chosen_model,
                    'quality': score,
                    'issue': 'Task too complex',
                    'agent': call.get('agent_name', 'Unknown'),
                    'operation': call.get('operation', 'unknown'),
                })
    
    # Analyze unrouted high-value calls
    unrouted_opportunities = analyze_routing_opportunities(unrouted_calls) if unrouted_calls else {'downgrade': [], 'upgrade': []}
    
    total_savings = sum(r['savings'] for r in rules)
    
    return {
        'rules': rules,
        'mistakes': mistakes,
        'unrouted_opportunities': unrouted_opportunities,
        'total_routed': len(routed_calls),
        'total_unrouted': len(unrouted_calls),
        'routing_rate': len(routed_calls) / len(calls) if calls else 0,
        'total_savings': total_savings,
    }


# =============================================================================
# DISCOVERY MODE - RENDER
# =============================================================================

def render_discovery_mode(calls: List[Dict]):
    """Render Discovery Mode tab content."""
    
    analysis = analyze_routing_opportunities(calls)
    
    downgrade_count = len(analysis['downgrade'])
    upgrade_count = len(analysis['upgrade'])
    optimal_count = len(analysis['optimal'])
    total_savings = analysis['total_savings']
    monthly_savings = (total_savings / 7) * 30  # Assume 7-day period
    
    # Summary KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("⬇️ Downgrades", downgrade_count)
    with col2:
        st.metric("⬆️ Upgrades", upgrade_count)
    with col3:
        st.metric("✅ Optimal", optimal_count)
    with col4:
        st.metric("💰 Potential", f"{format_cost(monthly_savings)}/mo")
    
    st.divider()
    
    # Combined opportunities table
    render_opportunities_table(analysis)
    
    st.divider()
    
    # Suggested rules
    render_suggested_rules(analysis)


def render_opportunities_table(analysis: Dict):
    """Render combined routing opportunities table."""
    
    st.subheader("📋 Routing Opportunities")
    st.caption("Click a row to see details and implementation")
    
    # Combine downgrade and upgrade candidates
    all_opportunities = []
    
    for item in analysis['downgrade']:
        all_opportunities.append({
            'type': '⬇️',
            'data': item,
        })
    
    for item in analysis['upgrade']:
        all_opportunities.append({
            'type': '⬆️',
            'data': item,
        })
    
    if not all_opportunities:
        st.success("✅ All operations are using optimal models!")
        return
    
    # Check for highlighted row from incoming filter
    highlight_key = st.session_state.get('_router_highlight')
    highlight_idx = None
    if highlight_key:
        for i, opp in enumerate(all_opportunities):
            if opp['data']['agent_operation'] == highlight_key:
                highlight_idx = i
                break
    
    # Build table data
    table_data = []
    for opp in all_opportunities:
        item = opp['data']
        savings_str = format_cost(item['potential_savings']) if item['potential_savings'] > 0 else '—'
        
        table_data.append({
            'Type': opp['type'],
            'Issue': item['issue_type'] or '—',
            'Agent.Operation': item['agent_operation'],
            'Model': format_model_name(item['primary_model']),
            'Reason': item['issue_reason'] or '—',
            'Calls': item['call_count'],
            'Save': savings_str,
        })
    
    df = pd.DataFrame(table_data)
    
    selection = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="routing_opp_table"
    )
    
    total_savings = sum(o['data']['potential_savings'] for o in all_opportunities)
    st.caption(f"Total: {len(all_opportunities)} opportunities • {format_cost(total_savings)} potential savings")
    
    # Show detail for selected row OR auto-highlighted row
    selected_rows = selection.selection.rows if selection.selection else []
    
    # Use highlighted row if no manual selection
    if not selected_rows and highlight_idx is not None:
        selected_rows = [highlight_idx]
    
    if selected_rows and selected_rows[0] < len(all_opportunities):
        render_opportunity_detail(all_opportunities[selected_rows[0]]['data'])


def render_opportunity_detail(item: Dict):
    """Render detail view for a routing opportunity."""
    
    st.markdown("---")
    st.markdown(f"**▼ {item['agent_operation']} — {item['call_count']} calls**")
    
    # Token Breakdown table
    st.markdown("**📊 Token Breakdown**")
    
    components = item.get('components', {})
    total_prompt = item.get('avg_prompt_tokens', 0)
    
    system_tokens = components.get('system_prompt_tokens', 0)
    history_tokens = components.get('chat_history_tokens', 0)
    history_count = components.get('chat_history_count', 0)
    user_tokens = components.get('user_message_tokens', 0)
    
    system_pct = (system_tokens / total_prompt * 100) if total_prompt > 0 else 0
    history_pct = (history_tokens / total_prompt * 100) if total_prompt > 0 else 0
    user_pct = (user_tokens / total_prompt * 100) if total_prompt > 0 else 0
    
    token_data = pd.DataFrame([
        {'Component': 'System Prompt', 'Avg Tokens': int(system_tokens), '%': f"{system_pct:.0f}%"},
        {'Component': f'Chat History ({history_count} msgs)', 'Avg Tokens': int(history_tokens), '%': f"{history_pct:.0f}%"},
        {'Component': 'User Message', 'Avg Tokens': int(user_tokens), '%': f"{user_pct:.0f}%"},
    ])
    
    st.dataframe(token_data, width='stretch', hide_index=True)
    
    # Performance table
    st.markdown("**📈 Performance**")
    
    quality_str = f"{item['avg_quality']:.1f}/10" if item['avg_quality'] is not None else '—'
    
    perf_data = pd.DataFrame([{
        'Avg Latency': format_latency(item['avg_latency']),
        'Avg Cost': format_cost(item['avg_cost']),
        'Avg Quality': quality_str,
        'Total Cost': format_cost(item['total_cost']),
    }])
    
    st.dataframe(perf_data, width='stretch', hide_index=True)
    
    # Recommendation table
    st.markdown("**🛠️ Recommendation**")
    
    rec_data = pd.DataFrame([{
        'Current': format_model_name(item['primary_model']),
        'Suggested': format_model_name(item['suggested_model']),
        'Savings': format_cost(item['potential_savings']) if item['potential_savings'] > 0 else '—',
        'Risk': item['risk'],
    }])
    
    st.dataframe(rec_data, width='stretch', hide_index=True)
    
    # Routing code
    agent = item['agent']
    operation = item['operation']
    suggested = item['suggested_model']
    current = item['primary_model']
    
    code = f'''# Route {operation} to {suggested}
if agent == "{agent}" and operation == "{operation}":
    model = "{suggested}"
    
    track_llm_call(
        agent_name="{agent}",
        operation="{operation}",
        routing_decision={{
            "chosen_model": "{suggested}",
            "rule": "{agent}.{operation} → {suggested}",
            "reasoning": "Simple task, downgraded from {current}"
        }}
    )'''
    
    with st.expander("📋 Routing code"):
        st.code(code, language="python")


def render_suggested_rules(analysis: Dict):
    """Render suggested routing rules section."""
    
    st.subheader("📋 Suggested Rules")
    st.caption("Auto-generated based on your usage patterns")
    
    rules = []
    
    # Generate rules from downgrade candidates
    for item in analysis['downgrade'][:5]:
        rules.append({
            'pattern': f"{item['agent']}.{item['operation']}",
            'target': item['suggested_model'],
            'savings': item['potential_savings'],
            'type': 'downgrade',
        })
    
    # Generate rules from upgrade candidates
    for item in analysis['upgrade'][:3]:
        rules.append({
            'pattern': f"{item['agent']}.{item['operation']}",
            'target': item['suggested_model'],
            'savings': 0,
            'type': 'upgrade',
        })
    
    if not rules:
        st.info("No routing rules suggested — your current model usage looks optimal!")
        return
    
    # Rules table
    table_data = []
    for i, rule in enumerate(rules, 1):
        type_icon = '⬇️' if rule['type'] == 'downgrade' else '⬆️'
        savings_str = format_cost(rule['savings']) if rule['savings'] > 0 else '—'
        
        table_data.append({
            '#': i,
            'Type': type_icon,
            'Pattern': rule['pattern'],
            'Target Model': rule['target'],
            'Savings': savings_str,
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, width='stretch', hide_index=True)
    
    # Generate complete config button
    with st.expander("📋 Generate complete routing config"):
        config_code = generate_routing_config(rules)
        st.code(config_code, language="python")


def generate_routing_config(rules: List[Dict]) -> str:
    """Generate complete routing configuration code."""
    
    code = '''# Routing Configuration
# Generated by Observatory

ROUTING_RULES = [
'''
    
    for rule in rules:
        code += f'''    {{
        "pattern": "{rule['pattern']}",
        "target_model": "{rule['target']}",
        "type": "{rule['type']}",
    }},
'''
    
    code += ''']

def route_request(agent: str, operation: str, tokens: int) -> str:
    """Route request to appropriate model."""
    
    key = f"{agent}.{operation}"
    
    for rule in ROUTING_RULES:
        if key == rule["pattern"] or key.startswith(rule["pattern"].replace("*", "")):
            return rule["target_model"]
    
    # Default fallback
    return "gpt-4o-mini"
'''
    
    return code


# =============================================================================
# ACTIVE MODE - RENDER
# =============================================================================

def render_active_mode(calls: List[Dict]):
    """Render Active Mode tab content."""
    
    analysis = analyze_routing_performance(calls)
    
    # Summary KPIs
    st.markdown("🟢 **Routing Active**")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Rules Active", len(analysis['rules']))
    with col2:
        rate_pct = format_percentage(analysis['routing_rate'])
        st.metric("Calls Routed", f"{analysis['total_routed']} ({rate_pct})")
    with col3:
        st.metric("Cost Saved", format_cost(analysis['total_savings']))
    with col4:
        st.metric("Mistakes", len(analysis['mistakes']))
    
    st.divider()
    
    # Rule performance
    render_rule_performance(analysis['rules'])
    
    st.divider()
    
    # Routing mistakes
    render_routing_mistakes(analysis['mistakes'])
    
    st.divider()
    
    # Unrouted opportunities
    render_unrouted_opportunities(analysis['unrouted_opportunities'])


def render_rule_performance(rules: List[Dict]):
    """Render rule performance table."""
    
    st.subheader("📋 Rule Performance")
    
    if not rules:
        st.info("No routing rules have fired yet.")
        return
    
    table_data = []
    for rule in rules:
        quality_str = f"{rule['avg_quality']:.1f}/10" if rule['avg_quality'] is not None else '—'
        savings_str = format_cost(rule['savings']) if rule['savings'] != 0 else '—'
        
        table_data.append({
            'Status': rule['status'],
            'Rule': truncate_text(rule['rule'], 35),
            'Fired': rule['fired'],
            'Saved': savings_str,
            'Avg Qual': quality_str,
        })
    
    df = pd.DataFrame(table_data)
    
    st.dataframe(df, width='stretch', hide_index=True)
    
    total_saved = sum(r['savings'] for r in rules)
    st.caption(f"Total saved: {format_cost(total_saved)}")


def render_routing_mistakes(mistakes: List[Dict]):
    """Render routing mistakes section."""
    
    st.subheader("⚠️ Routing Mistakes")
    
    if not mistakes:
        st.success("✅ No routing mistakes detected")
        return
    
    st.write("Calls where cheap model was chosen but quality suffered:")
    
    table_data = []
    for m in mistakes[:10]:
        call = m['call']
        timestamp = call.get('timestamp')
        time_str = timestamp.strftime("%H:%M") if timestamp else "—"
        
        table_data.append({
            'Time': time_str,
            'Agent.Operation': f"{m['agent']}.{m['operation']}",
            'Model': format_model_name(m['model']),
            'Quality': f"{m['quality']:.1f}/10",
            'Issue': m['issue'],
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, width='stretch', hide_index=True)
    
    if len(mistakes) > 10:
        st.caption(f"Showing 10 of {len(mistakes)} mistakes")
    
    st.markdown("💡 **Consider:** Add complexity check before routing to cheap model")


def render_unrouted_opportunities(opportunities: Dict):
    """Render unrouted high-value opportunities."""
    
    st.subheader("📋 Unrouted Opportunities")
    
    downgrade = opportunities.get('downgrade', [])
    upgrade = opportunities.get('upgrade', [])
    
    if not downgrade and not upgrade:
        st.success("✅ All high-value operations have routing rules")
        return
    
    st.write("Operations without routing rules that could benefit:")
    
    table_data = []
    for item in downgrade[:5]:
        table_data.append({
            'Type': '⬇️',
            'Agent.Operation': item['agent_operation'],
            'Model': format_model_name(item['primary_model']),
            'Calls': item['call_count'],
            'Potential': format_cost(item['potential_savings']),
        })
    
    for item in upgrade[:3]:
        table_data.append({
            'Type': '⬆️',
            'Agent.Operation': item['agent_operation'],
            'Model': format_model_name(item['primary_model']),
            'Calls': item['call_count'],
            'Potential': '—',
        })
    
    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df, width='stretch', hide_index=True)
    
    st.caption("Add routing rules for these operations to improve efficiency")


# =============================================================================
# MAIN RENDER
# =============================================================================

def render():
    """Main render function for Model Router page."""
    
    st.title("🔀 Model Router")
    
    # Check for incoming filters from other pages
    # From Home: router_tab (values: "cost", "latency")
    # From Cost Estimator: router_filter (dict with agent, operation)
    incoming_tab = st.session_state.get('router_tab')
    incoming_filter = st.session_state.get('router_filter')
    
    if incoming_filter:
        filter_agent = incoming_filter.get('agent', '')
        filter_op = incoming_filter.get('operation', '')
        filter_key = f"{filter_agent}.{filter_op}"
        
        col1, col2 = st.columns([4, 1])
        with col1:
            st.info(f"🎯 Filtered: **{filter_key}**")
        with col2:
            if st.button("✕ Clear", key="clear_router_filter"):
                del st.session_state['router_filter']
                st.rerun()
        
        # Store for table to use
        st.session_state['_router_highlight'] = filter_key
    else:
        st.session_state['_router_highlight'] = None
    
    # Handle tab filter from Home (clear after use)
    if incoming_tab:
        del st.session_state['router_tab']
    
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
            key="router_limit",
            label_visibility="collapsed"
        )
    
    with col3:
        if st.button("🔄 Refresh", width='stretch', key="router_refresh"):
            st.cache_data.clear()
            st.rerun()
    
    st.divider()
    
    # Load data
    try:
        calls = get_llm_calls(project_name=selected_project, limit=limit)
        
        if not calls:
            render_empty_state(
                message="No LLM calls found",
                icon="🔀",
                suggestion="Start making LLM calls with Observatory tracking enabled"
            )
            return
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    # Detect routing mode
    is_active, routing_stats = detect_routing_mode(calls)
    
    # Tabs with session state persistence
    mode = st.radio(
        "Mode",
        ["🔍 Discovery", "⚡ Active"],
        horizontal=True,
        key="router_mode",
        label_visibility="collapsed"
    )
    
    st.divider()
    
    if mode == "🔍 Discovery":
        if is_active:
            st.info("Routing is active! Check the Active tab for performance metrics.")
        render_discovery_mode(calls)
    else:
        if not is_active:
            st.warning("Routing not detected. Implement routing using Discovery suggestions, then return here to monitor.")
            st.caption("Active Mode requires routing_decision to be populated in your LLM calls.")
        else:
            render_active_mode(calls)