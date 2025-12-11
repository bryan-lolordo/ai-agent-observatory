"""
Prompt Optimizer - Token Analysis & Optimization
Location: dashboard/pages/prompt_optimizer.py

Single-scroll layout:
1. Summary KPIs
2. Prompts by Operation (System/History/User breakdown)
3. Expansion with issue detection and fixes
4. Prompt Versions (auto-detected via hash)
5. A/B Testing setup guide
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict
import hashlib
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

LONG_PROMPT_THRESHOLD = 4000      # tokens
VERY_LONG_PROMPT_THRESHOLD = 6000 # tokens
LONG_HISTORY_PCT = 0.40           # 40% of tokens in history
LONG_SYSTEM_THRESHOLD = 3000      # tokens


# =============================================================================
# PROMPT PARSING
# =============================================================================

def parse_prompt_components(call: Dict) -> Dict[str, Any]:
    """Parse prompt into System/History/User components."""
    
    metadata = call.get('metadata', {}) or {}
    prompt = call.get('prompt', '') or ''
    prompt_tokens = call.get('prompt_tokens', 0)
    
    # Try metadata first (if properly instrumented)
    if metadata.get('system_prompt_tokens'):
        return {
            'system_tokens': metadata.get('system_prompt_tokens', 0),
            'history_tokens': metadata.get('chat_history_tokens', 0),
            'history_count': metadata.get('chat_history_count', 0),
            'user_tokens': metadata.get('user_message_tokens', 0),
            'system_text': metadata.get('system_prompt', '')[:500],
            'history_text': metadata.get('chat_history', '')[:500],
            'user_text': metadata.get('user_message', '')[:300],
            'has_breakdown': True,
        }
    
    # Estimate from prompt text
    return estimate_prompt_components(prompt, prompt_tokens)


def estimate_prompt_components(prompt: str, total_tokens: int) -> Dict[str, Any]:
    """Estimate prompt components when not available in metadata."""
    
    if not prompt or total_tokens == 0:
        return {
            'system_tokens': 0,
            'history_tokens': 0,
            'history_count': 0,
            'user_tokens': total_tokens,
            'system_text': '',
            'history_text': '',
            'user_text': prompt[:300] if prompt else '',
            'has_breakdown': False,
        }
    
    # Detect chat history patterns
    history_patterns = [
        r'Human:|User:|Assistant:|AI:',
        r'\[User\]|\[Assistant\]',
        r'<human>|<assistant>',
    ]
    
    message_count = 0
    for pattern in history_patterns:
        matches = re.findall(pattern, prompt, re.IGNORECASE)
        message_count = max(message_count, len(matches))
    
    # Detect system prompt markers
    system_markers = ['You are', 'System:', 'Instructions:', '## ', '### ']
    has_system = any(marker in prompt[:1000] for marker in system_markers)
    
    # Estimate percentages
    if message_count > 2:
        system_pct = 0.25 if has_system else 0.10
        history_pct = min(0.60, message_count * 0.08)
        user_pct = max(0.10, 1 - system_pct - history_pct)
    else:
        system_pct = 0.40 if has_system else 0.20
        history_pct = 0
        user_pct = 1 - system_pct
    
    system_tokens = int(total_tokens * system_pct)
    history_tokens = int(total_tokens * history_pct)
    user_tokens = int(total_tokens * user_pct)
    
    # Extract text samples
    system_text = prompt[:500] if has_system else ''
    user_text = prompt[-300:]
    
    return {
        'system_tokens': system_tokens,
        'history_tokens': history_tokens,
        'history_count': message_count,
        'user_tokens': user_tokens,
        'system_text': system_text,
        'history_text': f'[{message_count} messages estimated]',
        'user_text': user_text,
        'has_breakdown': False,
    }


def generate_prompt_hash(prompt: str) -> str:
    """Generate hash of prompt prefix for version detection."""
    if not prompt:
        return ''
    # Hash first 500 chars (captures system prompt changes)
    return hashlib.md5(prompt[:500].encode()).hexdigest()[:8]


# =============================================================================
# ISSUE DETECTION
# =============================================================================

def detect_prompt_issue(components: Dict, total_tokens: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Detect prompt optimization issue.
    
    Returns: (issue_type, component, problem_description)
    """
    system_tokens = components.get('system_tokens', 0)
    history_tokens = components.get('history_tokens', 0)
    history_count = components.get('history_count', 0)
    user_tokens = components.get('user_tokens', 0)
    
    # Check for long history
    if total_tokens > 0 and history_tokens / total_tokens > LONG_HISTORY_PCT:
        return 'Long history', 'History', f'{history_count} messages, {int(history_tokens/total_tokens*100)}% of tokens'
    
    # Check for too many messages
    if history_count > 6:
        return 'Many messages', 'History', f'{history_count} messages in context'
    
    # Check for long system prompt
    if system_tokens > LONG_SYSTEM_THRESHOLD:
        return 'Long system', 'System', f'{format_tokens(system_tokens)} in system prompt'
    
    # Check for context bloat (high total, low user)
    if total_tokens > VERY_LONG_PROMPT_THRESHOLD:
        if user_tokens / total_tokens < 0.15:
            return 'Context bloat', 'Overall', f'User message only {int(user_tokens/total_tokens*100)}% of tokens'
        return 'Very long', 'Overall', f'{format_tokens(total_tokens)} total'
    
    # Check for long prompt
    if total_tokens > LONG_PROMPT_THRESHOLD:
        return 'Long prompt', 'Overall', f'{format_tokens(total_tokens)} total'
    
    return None, None, None


def get_recommended_fix(issue_type: Optional[str], components: Dict) -> Dict[str, Any]:
    """Get recommended fix for detected issue."""
    
    if not issue_type:
        return {
            'action': '—',
            'savings_tokens': 0,
            'savings_pct': 0,
            'cost_savings': 0,
            'code_template': '',
        }
    
    history_tokens = components.get('history_tokens', 0)
    history_count = components.get('history_count', 0)
    system_tokens = components.get('system_tokens', 0)
    
    if issue_type in ['Long history', 'Many messages']:
        # Sliding window fix
        keep_messages = 6
        reduction = max(0, history_tokens * (1 - keep_messages / max(history_count, 1)))
        return {
            'action': 'Sliding window',
            'savings_tokens': int(reduction),
            'savings_pct': int(reduction / (components.get('system_tokens', 0) + history_tokens + components.get('user_tokens', 0)) * 100) if reduction > 0 else 0,
            'code_template': generate_sliding_window_code(keep_messages),
        }
    
    if issue_type == 'Long system':
        # Compress system prompt
        reduction = system_tokens * 0.4  # 40% reduction possible
        return {
            'action': 'Compress system',
            'savings_tokens': int(reduction),
            'savings_pct': 40,
            'code_template': generate_compress_system_code(),
        }
    
    if issue_type == 'Context bloat':
        # Externalize to RAG
        reduction = (system_tokens + history_tokens) * 0.5
        return {
            'action': 'Externalize (RAG)',
            'savings_tokens': int(reduction),
            'savings_pct': 50,
            'code_template': generate_rag_code(),
        }
    
    if issue_type in ['Long prompt', 'Very long']:
        # General compression
        total = components.get('system_tokens', 0) + history_tokens + components.get('user_tokens', 0)
        reduction = total * 0.25
        return {
            'action': 'Review & compress',
            'savings_tokens': int(reduction),
            'savings_pct': 25,
            'code_template': generate_review_code(),
        }
    
    return {
        'action': '—',
        'savings_tokens': 0,
        'savings_pct': 0,
        'code_template': '',
    }


# =============================================================================
# CODE TEMPLATES
# =============================================================================

def generate_sliding_window_code(keep_messages: int) -> str:
    return f'''# Implement sliding window for chat history
def trim_chat_history(messages: list, max_messages: int = {keep_messages}) -> list:
    """Keep only the most recent messages."""
    if len(messages) <= max_messages:
        return messages
    
    # Always keep system message if present
    system_msgs = [m for m in messages if m.get('role') == 'system']
    chat_msgs = [m for m in messages if m.get('role') != 'system']
    
    # Keep last N messages
    trimmed = chat_msgs[-max_messages:]
    
    return system_msgs + trimmed

# Alternative: Summarize old messages
def summarize_old_messages(messages: list, keep_recent: int = 4) -> list:
    """Summarize older messages, keep recent ones verbatim."""
    if len(messages) <= keep_recent + 1:
        return messages
    
    old_messages = messages[:-keep_recent]
    recent_messages = messages[-keep_recent:]
    
    # Summarize old messages with LLM
    summary = summarize_conversation(old_messages)
    
    return [{{"role": "system", "content": f"Previous conversation summary: {{summary}}"}}] + recent_messages'''


def generate_compress_system_code() -> str:
    return '''# Compress system prompt
# Before: Long, verbose instructions
SYSTEM_PROMPT_OLD = """
You are a helpful career advisor assistant. Your role is to help users 
with their job search, resume optimization, and career planning. You should
always be professional, supportive, and provide actionable advice. When 
analyzing resumes, look for key skills, experience gaps, and areas for 
improvement. When matching jobs, consider both hard skills and soft skills...
[continues for 2000+ tokens]
"""

# After: Concise, structured instructions
SYSTEM_PROMPT_NEW = """
Role: Career advisor
Tasks: Job search, resume optimization, career planning

Guidelines:
- Be professional and supportive
- Provide actionable advice
- For resumes: identify skills, gaps, improvements
- For job matching: consider hard and soft skills

Output format: [specify expected format]
"""

# Reduction: ~60-70% fewer tokens'''


def generate_rag_code() -> str:
    return '''# Externalize context to RAG
# Instead of including all context in prompt, retrieve only relevant parts

from your_vector_store import search_similar

def build_prompt_with_rag(query: str, max_context_tokens: int = 1000) -> str:
    """Build prompt with only relevant context."""
    
    # Retrieve relevant documents
    relevant_docs = search_similar(query, top_k=3)
    
    # Build focused context
    context = "\\n".join([doc.content for doc in relevant_docs])
    
    prompt = f"""
Based on this context:
{context[:max_context_tokens]}

Answer: {query}
"""
    return prompt

# Benefits:
# - Only include relevant context
# - Reduce token usage by 50-80%
# - Improve response quality (less noise)'''


def generate_review_code() -> str:
    return '''# Prompt optimization checklist

# 1. Remove redundant instructions
# Before: "Please make sure to always remember to..."
# After: "Always..."

# 2. Use structured format
# Before: Paragraph of instructions
# After: Numbered list or YAML-like structure

# 3. Remove examples if model understands task
# Before: 5 examples of expected output
# After: 1-2 examples (or zero-shot)

# 4. Externalize static content
# Before: Full document in prompt
# After: Document ID + retrieval

# 5. Use references instead of repetition
# Before: Repeat context in each turn
# After: "As mentioned above..." or context IDs'''


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def analyze_prompts_by_operation(calls: List[Dict]) -> List[Dict]:
    """Analyze prompts aggregated by operation."""
    
    by_operation = defaultdict(lambda: {
        'calls': [],
        'total_system': 0,
        'total_history': 0,
        'total_user': 0,
        'total_tokens': 0,
    })
    
    for call in calls:
        agent = call.get('agent_name', 'Unknown')
        operation = call.get('operation', 'unknown')
        key = f"{agent}.{operation}"
        
        prompt_tokens = call.get('prompt_tokens', 0)
        components = parse_prompt_components(call)
        
        by_operation[key]['calls'].append({
            'call': call,
            'components': components,
        })
        by_operation[key]['total_system'] += components['system_tokens']
        by_operation[key]['total_history'] += components['history_tokens']
        by_operation[key]['total_user'] += components['user_tokens']
        by_operation[key]['total_tokens'] += prompt_tokens
    
    results = []
    for op_key, stats in by_operation.items():
        call_count = len(stats['calls'])
        avg_system = stats['total_system'] / call_count if call_count > 0 else 0
        avg_history = stats['total_history'] / call_count if call_count > 0 else 0
        avg_user = stats['total_user'] / call_count if call_count > 0 else 0
        avg_total = stats['total_tokens'] / call_count if call_count > 0 else 0
        
        # Build average components for issue detection
        avg_components = {
            'system_tokens': avg_system,
            'history_tokens': avg_history,
            'history_count': sum(c['components']['history_count'] for c in stats['calls']) / call_count,
            'user_tokens': avg_user,
        }
        
        issue_type, component, problem = detect_prompt_issue(avg_components, avg_total)
        fix = get_recommended_fix(issue_type, avg_components)
        
        # Determine status
        if avg_total > VERY_LONG_PROMPT_THRESHOLD:
            status = '🔴'
        elif avg_total > LONG_PROMPT_THRESHOLD or issue_type:
            status = '🟡'
        else:
            status = '🟢'
        
        # Get sample prompt for display
        sample_call = stats['calls'][0]['call'] if stats['calls'] else {}
        sample_components = stats['calls'][0]['components'] if stats['calls'] else {}
        
        results.append({
            'operation': op_key,
            'call_count': call_count,
            'avg_system': int(avg_system),
            'avg_history': int(avg_history),
            'avg_user': int(avg_user),
            'avg_total': int(avg_total),
            'status': status,
            'issue_type': issue_type,
            'issue_component': component,
            'issue_problem': problem,
            'fix': fix,
            'sample_call': sample_call,
            'sample_components': sample_components,
            'all_calls': stats['calls'],
        })
    
    # Sort by total tokens descending
    results.sort(key=lambda x: -x['avg_total'])
    
    return results


def analyze_prompt_versions(calls: List[Dict]) -> List[Dict]:
    """Detect prompt versions via hash."""
    
    by_operation_hash = defaultdict(lambda: {
        'calls': [],
        'total_tokens': 0,
        'total_latency': 0,
        'total_cost': 0,
        'first_seen': None,
    })
    
    for call in calls:
        agent = call.get('agent_name', 'Unknown')
        operation = call.get('operation', 'unknown')
        prompt = call.get('prompt', '')
        
        if not prompt:
            continue
        
        # Check for explicit version in metadata first
        metadata = call.get('metadata', {}) or {}
        prompt_hash = metadata.get('prompt_hash') or generate_prompt_hash(prompt)
        
        key = (f"{agent}.{operation}", prompt_hash)
        
        by_operation_hash[key]['calls'].append(call)
        by_operation_hash[key]['total_tokens'] += call.get('prompt_tokens', 0)
        by_operation_hash[key]['total_latency'] += call.get('latency_ms', 0)
        by_operation_hash[key]['total_cost'] += call.get('total_cost', 0)
        
        timestamp = call.get('timestamp')
        if timestamp:
            if by_operation_hash[key]['first_seen'] is None:
                by_operation_hash[key]['first_seen'] = timestamp
            else:
                by_operation_hash[key]['first_seen'] = min(by_operation_hash[key]['first_seen'], timestamp)
    
    # Group by operation to find multiple versions
    by_operation = defaultdict(list)
    
    for (operation, hash_val), stats in by_operation_hash.items():
        call_count = len(stats['calls'])
        by_operation[operation].append({
            'hash': hash_val,
            'call_count': call_count,
            'avg_tokens': stats['total_tokens'] / call_count if call_count > 0 else 0,
            'avg_latency': stats['total_latency'] / call_count if call_count > 0 else 0,
            'avg_cost': stats['total_cost'] / call_count if call_count > 0 else 0,
            'first_seen': stats['first_seen'],
            'sample_prompt': stats['calls'][0].get('prompt', '')[:500] if stats['calls'] else '',
        })
    
    # Build results - only include operations with prompts
    results = []
    for operation, versions in by_operation.items():
        # Sort versions by first_seen
        versions.sort(key=lambda x: x['first_seen'] or datetime.min)
        
        for i, v in enumerate(versions):
            is_latest = (i == len(versions) - 1)
            results.append({
                'operation': operation,
                'hash': v['hash'],
                'call_count': v['call_count'],
                'avg_tokens': int(v['avg_tokens']),
                'avg_latency': v['avg_latency'],
                'avg_cost': v['avg_cost'],
                'first_seen': v['first_seen'],
                'is_latest': is_latest,
                'version_count': len(versions),
                'sample_prompt': v['sample_prompt'],
            })
    
    # Sort by operation, then by first_seen
    results.sort(key=lambda x: (x['operation'], x['first_seen'] or datetime.min))
    
    return results


def calculate_summary_kpis(operation_analysis: List[Dict], calls: List[Dict]) -> Dict[str, Any]:
    """Calculate summary KPIs."""
    
    total_calls = len(calls)
    
    if total_calls == 0:
        return {
            'avg_tokens': 0,
            'long_count': 0,
            'very_long_count': 0,
            'total_reducible': 0,
            'potential_savings': 0,
        }
    
    total_tokens = sum(c.get('prompt_tokens', 0) for c in calls)
    avg_tokens = total_tokens / total_calls
    
    long_count = sum(1 for c in calls if c.get('prompt_tokens', 0) > LONG_PROMPT_THRESHOLD)
    very_long_count = sum(1 for c in calls if c.get('prompt_tokens', 0) > VERY_LONG_PROMPT_THRESHOLD)
    
    # Calculate total reducible tokens
    total_reducible = sum(op['fix']['savings_tokens'] * op['call_count'] for op in operation_analysis)
    
    # Estimate cost savings (rough: $0.01 per 1K tokens)
    potential_savings = (total_reducible / 1000) * 0.01
    
    return {
        'avg_tokens': int(avg_tokens),
        'long_count': long_count,
        'very_long_count': very_long_count,
        'total_reducible': total_reducible,
        'potential_savings': potential_savings,
    }


# =============================================================================
# RENDER FUNCTIONS
# =============================================================================

def render_summary_kpis(kpis: Dict):
    """Render summary KPI metrics."""
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Avg Tokens", format_tokens(kpis['avg_tokens']))
    
    with col2:
        st.metric("Long (>4K)", kpis['long_count'])
    
    with col3:
        st.metric("Reducible", f"-{format_tokens(kpis['total_reducible'])} avg")
    
    with col4:
        st.metric("💰 Potential", f"{format_cost(kpis['potential_savings'])}/mo")


def render_prompts_table(operation_analysis: List[Dict]):
    """Render main prompts by operation table."""
    
    st.subheader("📋 Prompts by Operation")
    
    if not operation_analysis:
        st.info("No prompt data found.")
        return
    
    # Check for highlighted row from incoming filter
    highlight_key = st.session_state.get('_prompt_highlight')
    
    # Filter
    status_filter = st.selectbox(
        "Status",
        ["All", "🔴 Very Long", "🟡 Long/Issues", "🟢 Optimal"],
        key="prompt_status_filter",
        label_visibility="collapsed"
    )
    
    # Apply filter
    filtered = operation_analysis
    if status_filter == "🔴 Very Long":
        filtered = [op for op in operation_analysis if op['status'] == '🔴']
    elif status_filter == "🟡 Long/Issues":
        filtered = [op for op in operation_analysis if op['status'] == '🟡']
    elif status_filter == "🟢 Optimal":
        filtered = [op for op in operation_analysis if op['status'] == '🟢']
    
    if not filtered:
        st.warning("No operations match the selected filter.")
        return
    
    # Find highlight index
    highlight_idx = None
    if highlight_key:
        for i, op in enumerate(filtered):
            if op['operation'] == highlight_key:
                highlight_idx = i
                break
    
    # Build table
    table_data = []
    for op in filtered:
        table_data.append({
            'Status': op['status'],
            'Agent.Operation': op['operation'],
            'System': format_tokens(op['avg_system']),
            'History': format_tokens(op['avg_history']),
            'User': format_tokens(op['avg_user']),
            'Total': format_tokens(op['avg_total']),
        })
    
    df = pd.DataFrame(table_data)
    
    selection = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="prompts_table"
    )
    
    st.caption("Click row for breakdown + optimization")
    
    # Show detail for selected row OR auto-highlighted row
    selected_rows = selection.selection.rows if selection.selection else []
    
    # Use highlighted row if no manual selection
    if not selected_rows and highlight_idx is not None:
        selected_rows = [highlight_idx]
    
    if selected_rows and selected_rows[0] < len(filtered):
        render_prompt_detail(filtered[selected_rows[0]])


def render_prompt_detail(op: Dict):
    """Render detailed view for a prompt operation."""
    
    st.markdown("---")
    st.markdown(f"**▼ {op['operation']} — {format_tokens(op['avg_total'])} tokens avg ({op['call_count']} calls)**")
    
    # 3 columns: Token Breakdown | Issue | Recommended Fix
    col1, col2, col3 = st.columns(3)
    
    total = op['avg_total'] or 1
    system_pct = int(op['avg_system'] / total * 100) if total > 0 else 0
    history_pct = int(op['avg_history'] / total * 100) if total > 0 else 0
    user_pct = int(op['avg_user'] / total * 100) if total > 0 else 0
    
    with col1:
        st.markdown("**Token Breakdown**")
        breakdown_data = pd.DataFrame([
            {'': 'System', '  ': f"{format_tokens(op['avg_system'])} ({system_pct}%)"},
            {'': 'History', '  ': f"{format_tokens(op['avg_history'])} ({history_pct}%)"},
            {'': 'User', '  ': f"{format_tokens(op['avg_user'])} ({user_pct}%)"},
        ])
        st.dataframe(breakdown_data, width='stretch', hide_index=True)
    
    with col2:
        st.markdown("**Issue**")
        if op['issue_type']:
            issue_data = pd.DataFrame([
                {'': 'Type', '  ': op['issue_type']},
                {'': 'Component', '  ': op['issue_component']},
                {'': 'Problem', '  ': op['issue_problem']},
            ])
        else:
            issue_data = pd.DataFrame([
                {'': 'Type', '  ': '—'},
                {'': 'Component', '  ': '—'},
                {'': 'Problem', '  ': 'No issues detected'},
            ])
        st.dataframe(issue_data, width='stretch', hide_index=True)
    
    with col3:
        st.markdown("**Recommended Fix**")
        fix = op['fix']
        if fix['action'] != '—':
            fix_data = pd.DataFrame([
                {'': 'Action', '  ': fix['action']},
                {'': 'Savings', '  ': f"{format_tokens(fix['savings_tokens'])} ({fix['savings_pct']}%)"},
            ])
        else:
            fix_data = pd.DataFrame([
                {'': 'Action', '  ': '—'},
                {'': 'Savings', '  ': 'N/A'},
            ])
        st.dataframe(fix_data, width='stretch', hide_index=True)
    
    # Prompt content table
    components = op['sample_components']
    prompt_data = pd.DataFrame([
        {'': 'System', '  ': truncate_text(components.get('system_text', ''), 200) or '[Not detected]'},
        {'': 'History', '  ': truncate_text(components.get('history_text', ''), 200) or '[No history]'},
        {'': 'User', '  ': truncate_text(components.get('user_text', ''), 200) or '[Not detected]'},
    ])
    st.dataframe(prompt_data, width='stretch', hide_index=True)
    
    # Implementation code (collapsed)
    if fix['code_template']:
        with st.expander("📋 Implementation code"):
            st.code(fix['code_template'], language="python")


def render_versions_table(versions: List[Dict]):
    """Render prompt versions table."""
    
    st.subheader("📊 Prompt Versions")
    st.caption("Auto-detected via prompt hash • Multiple versions = prompt changed")
    
    if not versions:
        st.info("No prompt version data. Prompts are hashed to detect changes.")
        return
    
    # Only show operations with multiple versions, or all if filter selected
    multi_version_ops = set(v['operation'] for v in versions if v['version_count'] > 1)
    
    if not multi_version_ops:
        st.success("✅ All operations have consistent prompts (single version)")
        
        # Show single version summary
        table_data = []
        seen_ops = set()
        for v in versions:
            if v['operation'] not in seen_ops:
                seen_ops.add(v['operation'])
                table_data.append({
                    'Agent.Operation': v['operation'],
                    'Hash': v['hash'],
                    'Calls': v['call_count'],
                    'Avg Tokens': format_tokens(v['avg_tokens']),
                })
        
        if table_data:
            df = pd.DataFrame(table_data)
            st.dataframe(df, width='stretch', hide_index=True)
        return
    
    # Show operations with multiple versions
    st.info(f"📌 {len(multi_version_ops)} operation(s) have multiple prompt versions")
    
    table_data = []
    for v in versions:
        if v['operation'] in multi_version_ops:
            first_seen = v['first_seen'].strftime("%b %d") if v['first_seen'] else "—"
            new_marker = " ✨ New" if v['is_latest'] and v['version_count'] > 1 else ""
            
            table_data.append({
                'Agent.Operation': v['operation'],
                'Hash': v['hash'],
                'Calls': v['call_count'],
                'Avg Tokens': format_tokens(v['avg_tokens']),
                'First Seen': f"{first_seen}{new_marker}",
            })
    
    df = pd.DataFrame(table_data)
    
    selection = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="versions_table"
    )
    
    # Show version comparison if row selected
    selected_rows = selection.selection.rows if selection.selection else []
    if selected_rows and selected_rows[0] < len(table_data):
        selected_op = table_data[selected_rows[0]]['Agent.Operation']
        render_version_comparison(versions, selected_op)


def render_version_comparison(versions: List[Dict], operation: str):
    """Render side-by-side version comparison."""
    
    op_versions = [v for v in versions if v['operation'] == operation]
    
    if len(op_versions) < 2:
        return
    
    st.markdown("---")
    st.markdown(f"**▼ {operation} — {len(op_versions)} versions detected**")
    
    # Build comparison table
    headers = [''] + [f"{v['hash']} ({'new' if v['is_latest'] else 'old'})" for v in op_versions]
    
    rows = [
        ['Calls'] + [str(v['call_count']) for v in op_versions],
        ['Avg Tokens'] + [format_tokens(v['avg_tokens']) for v in op_versions],
        ['Avg Latency'] + [format_latency(v['avg_latency']) for v in op_versions],
        ['Avg Cost'] + [format_cost(v['avg_cost']) for v in op_versions],
    ]
    
    # Add comparison indicators
    if len(op_versions) == 2:
        old, new = op_versions[0], op_versions[1]
        token_diff = new['avg_tokens'] - old['avg_tokens']
        token_pct = int(token_diff / old['avg_tokens'] * 100) if old['avg_tokens'] > 0 else 0
        
        if token_diff < 0:
            rows[1][2] += f" ✓ {token_pct}%"
        elif token_diff > 0:
            rows[1][2] += f" ↑ +{token_pct}%"
    
    comparison_df = pd.DataFrame(rows, columns=headers)
    st.dataframe(comparison_df, width='stretch', hide_index=True)
    
    st.caption("Quality comparison available when LLM Judge is implemented")
    
    # Prompt diff (collapsed)
    with st.expander("📋 View prompt diff"):
        if len(op_versions) >= 2:
            st.markdown("**Old version:**")
            st.code(truncate_text(op_versions[0]['sample_prompt'], 500), language="text")
            st.markdown("**New version:**")
            st.code(truncate_text(op_versions[1]['sample_prompt'], 500), language="text")


def render_ab_setup_guide():
    """Render A/B testing setup guide."""
    
    with st.expander("🛠️ Setup: Enable A/B Testing"):
        st.markdown("""
**Current:** Prompts are auto-detected via hash (first 500 chars).

**For explicit A/B testing**, add version tracking to your plugins:
        """)
        
        st.code('''# In your plugin
track_llm_call(
    model_name=model,
    prompt_tokens=prompt_tokens,
    completion_tokens=completion_tokens,
    latency_ms=latency_ms,
    agent_name="ResumeMatching",
    operation="score",
    prompt=prompt,
    metadata={
        "prompt_version": "v2-compressed",      # Your version label
        "experiment_id": "resume_match_test",   # Group experiments
    }
)''', language="python")
        
        st.markdown("""
**Benefits of explicit versioning:**
- Clear A/B test labels
- Track experiments across deploys
- Compare quality scores by version (requires LLM Judge)
        """)


# =============================================================================
# MAIN RENDER
# =============================================================================

def render():
    """Main render function for Prompt Optimizer page."""
    
    st.title("✨ Prompt Optimizer")
    
    # Check for incoming filter from Cost Estimator
    # prompt_filter (dict with agent, operation)
    incoming_filter = st.session_state.get('prompt_filter')
    
    if incoming_filter:
        filter_agent = incoming_filter.get('agent', '')
        filter_op = incoming_filter.get('operation', '')
        filter_key = f"{filter_agent}.{filter_op}"
        
        col1, col2 = st.columns([4, 1])
        with col1:
            st.info(f"🎯 Filtered: **{filter_key}**")
        with col2:
            if st.button("✕ Clear", key="clear_prompt_filter"):
                del st.session_state['prompt_filter']
                st.rerun()
        
        # Store for table to use
        st.session_state['_prompt_highlight'] = filter_key
    else:
        st.session_state['_prompt_highlight'] = None
    
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
            key="prompt_limit",
            label_visibility="collapsed"
        )
    
    with col3:
        if st.button("🔄 Refresh", width='stretch', key="prompt_refresh"):
            st.cache_data.clear()
            st.rerun()
    
    st.divider()
    
    # Load data
    try:
        calls = get_llm_calls(project_name=selected_project, limit=limit)
        
        if not calls:
            render_empty_state(
                message="No LLM calls found",
                icon="✨",
                suggestion="Start making LLM calls with Observatory tracking enabled"
            )
            return
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    # Analyze
    operation_analysis = analyze_prompts_by_operation(calls)
    versions = analyze_prompt_versions(calls)
    kpis = calculate_summary_kpis(operation_analysis, calls)
    
    # Summary KPIs
    render_summary_kpis(kpis)
    
    st.divider()
    
    # Main prompts table
    render_prompts_table(operation_analysis)
    
    st.divider()
    
    # Prompt versions
    render_versions_table(versions)
    
    st.divider()
    
    # A/B setup guide
    render_ab_setup_guide()