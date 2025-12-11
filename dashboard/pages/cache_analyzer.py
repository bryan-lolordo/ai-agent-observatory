"""
Cache Analyzer - Discovery & Active Modes
Location: dashboard/pages/cache_analyzer.py

Two-tab layout:
1. Discovery Mode - Find caching opportunities (when cache not implemented)
2. Active Mode - Monitor cache performance (when cache implemented)

Four cache pattern types:
1. Exact Match - Identical prompts
2. Semantic Similarity - Similar prompts (near-duplicates)
3. Stable Outputs - Same response every time
4. High-Value - Expensive/slow calls worth caching
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict, Counter
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

HIGH_VALUE_COST_THRESHOLD = 0.10  # $0.10 per call
HIGH_VALUE_LATENCY_THRESHOLD = 5000  # 5 seconds
DUPLICATE_THRESHOLD = 2  # Minimum occurrences to be duplicate
SIMILARITY_THRESHOLD = 0.7  # Jaccard similarity for near-duplicates
STABILITY_THRESHOLD = 0.6  # Minimum % same response for stable output


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def normalize_prompt(prompt: str) -> str:
    """Normalize prompt for comparison by removing dynamic content."""
    if not prompt:
        return ""
    
    normalized = prompt
    
    # Remove timestamps
    normalized = re.sub(r'\d{4}-\d{2}-\d{2}', '[DATE]', normalized)
    normalized = re.sub(r'\d{2}:\d{2}:\d{2}', '[TIME]', normalized)
    
    # Remove UUIDs
    normalized = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '[UUID]', normalized, flags=re.I)
    
    # Remove session IDs
    normalized = re.sub(r'sess_[a-zA-Z0-9]+', '[SESSION]', normalized)
    
    # Remove large numbers (IDs)
    normalized = re.sub(r'\b\d{5,}\b', '[ID]', normalized)
    
    # Normalize whitespace
    normalized = ' '.join(normalized.split())
    
    return normalized.lower()


def calculate_jaccard_similarity(text1: str, text2: str) -> float:
    """Calculate Jaccard similarity between two texts."""
    if not text1 or not text2:
        return 0.0
    
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0


def extract_cache_key_pattern(calls: List[Dict]) -> Tuple[str, str]:
    """Analyze calls to suggest a cache key pattern."""
    if not calls:
        return "", ""
    
    operation = calls[0].get('operation', 'unknown')
    prompts = [c.get('prompt', '') for c in calls if c.get('prompt')]
    
    if not prompts:
        return "Unable to detect pattern", f'f"{operation}:{{hash(prompt)}}"'
    
    # Check for ID patterns
    id_patterns = []
    for prompt in prompts[:5]:
        if re.search(r'job[_\s]?(?:id)?[:\s]+(\d+)', prompt, re.I):
            id_patterns.append('job_id')
        if re.search(r'resume[_\s]?(?:id)?[:\s]+(\d+)', prompt, re.I):
            id_patterns.append('resume_id')
        if re.search(r'user[_\s]?(?:id)?[:\s]+(\d+)', prompt, re.I):
            id_patterns.append('user_id')
    
    if 'job_id' in id_patterns and 'resume_id' in id_patterns:
        return "Same job_id + resume_id = same result", f'f"{operation}:{{job_id}}:{{resume_id}}"'
    elif 'job_id' in id_patterns:
        return "Same job_id = same result", f'f"{operation}:{{job_id}}"'
    elif 'resume_id' in id_patterns:
        return "Same resume_id = same result", f'f"{operation}:{{resume_id}}"'
    elif 'user_id' in id_patterns:
        return "Same user_id = same result", f'f"{operation}:{{user_id}}"'
    else:
        return "Same prompt content = same result", f'f"{operation}:{{hash(prompt)}}"'


def get_ttl_recommendation(operation: str) -> Tuple[str, str]:
    """Get TTL and invalidation recommendation based on operation type."""
    operation_lower = operation.lower()
    
    if 'analysis' in operation_lower or 'analyze' in operation_lower:
        return "24 hours", "When job or resume updated"
    elif 'query' in operation_lower or 'sql' in operation_lower:
        return "24 hours", "When schema changes"
    elif 'tailor' in operation_lower or 'rewrite' in operation_lower:
        return "1 hour", "When user requests fresh version"
    elif 'match' in operation_lower or 'score' in operation_lower:
        return "24 hours", "When job or resume updated"
    elif 'search' in operation_lower or 'find' in operation_lower:
        return "1 hour", "When new jobs added"
    elif 'schema' in operation_lower or 'config' in operation_lower:
        return "7 days", "On deployment or schema change"
    else:
        return "24 hours", "When source data changes"


def format_time_ago(timestamp: datetime) -> str:
    """Format timestamp as time ago string."""
    if not timestamp:
        return "—"
    
    now = datetime.now()
    if timestamp.tzinfo:
        now = datetime.now(timestamp.tzinfo)
    
    diff = now - timestamp
    
    if diff.total_seconds() < 60:
        return f"{int(diff.total_seconds())}s ago"
    elif diff.total_seconds() < 3600:
        return f"{int(diff.total_seconds() / 60)}m ago"
    elif diff.total_seconds() < 86400:
        return f"{int(diff.total_seconds() / 3600)}h ago"
    else:
        return f"{int(diff.total_seconds() / 86400)}d ago"


def format_ttl_remaining(hours: float) -> str:
    """Format TTL remaining as string."""
    if hours <= 0:
        return "Expired"
    elif hours < 1:
        return f"{int(hours * 60)}m"
    elif hours < 24:
        return f"{int(hours)}h"
    else:
        days = int(hours / 24)
        remaining_hours = int(hours % 24)
        return f"{days}d {remaining_hours}h"


# =============================================================================
# CACHE STATUS DETECTION
# =============================================================================

def detect_cache_mode(calls: List[Dict]) -> Tuple[bool, Dict]:
    """
    Detect if caching is active based on cache_metadata presence.
    
    Returns:
        Tuple of (is_active, stats)
    """
    if not calls:
        return False, {}
    
    calls_with_cache = [c for c in calls if c.get('cache_metadata')]
    
    stats = {
        'total_calls': len(calls),
        'calls_with_cache': len(calls_with_cache),
        'cache_hits': 0,
        'cache_misses': 0,
        'hit_rate': 0,
        'cost_saved': 0,
        'time_saved_ms': 0,
    }
    
    if not calls_with_cache:
        return False, stats
    
    # Calculate cache stats
    avg_cost = sum(c.get('total_cost', 0) for c in calls) / len(calls) if calls else 0
    avg_latency = sum(c.get('latency_ms', 0) for c in calls) / len(calls) if calls else 0
    
    for c in calls_with_cache:
        cache_meta = c.get('cache_metadata') or {}
        if cache_meta.get('cache_hit'):
            stats['cache_hits'] += 1
            stats['cost_saved'] += avg_cost  # Saved the cost of a full call
            stats['time_saved_ms'] += avg_latency
        else:
            stats['cache_misses'] += 1
    
    if calls_with_cache:
        stats['hit_rate'] = stats['cache_hits'] / len(calls_with_cache)
    
    is_active = len(calls_with_cache) >= 5  # Need enough data to consider "active"
    
    return is_active, stats


# =============================================================================
# DISCOVERY MODE - DETECTION FUNCTIONS
# =============================================================================

def find_duplicates(calls: List[Dict]) -> List[Dict]:
    """Find exact duplicate prompts."""
    prompt_groups = defaultdict(list)
    
    for call in calls:
        prompt = call.get('prompt') or ''
        if not prompt:
            continue
        
        normalized = normalize_prompt(prompt)
        prompt_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]
        prompt_groups[prompt_hash].append(call)
    
    duplicates = []
    
    for prompt_hash, group_calls in prompt_groups.items():
        if len(group_calls) < DUPLICATE_THRESHOLD:
            continue
        
        total_cost = sum(c.get('total_cost', 0) for c in group_calls)
        avg_cost = total_cost / len(group_calls) if group_calls else 0
        wasted_cost = (len(group_calls) - 1) * avg_cost
        avg_latency = sum(c.get('latency_ms', 0) for c in group_calls) / len(group_calls)
        
        agent = group_calls[0].get('agent_name', 'Unknown')
        operation = group_calls[0].get('operation', 'unknown')
        
        duplicates.append({
            'hash': prompt_hash,
            'agent': agent,
            'operation': operation,
            'agent_operation': f"{agent}.{operation}",
            'count': len(group_calls),
            'total_cost': total_cost,
            'avg_cost': avg_cost,
            'wasted_cost': wasted_cost,
            'avg_latency': avg_latency,
            'prompt_sample': group_calls[0].get('prompt', '')[:100],
            'prompt_full': group_calls[0].get('prompt', ''),
            'calls': group_calls,
        })
    
    duplicates.sort(key=lambda x: -x['wasted_cost'])
    return duplicates


def find_near_duplicates(calls: List[Dict]) -> List[Dict]:
    """Find semantically similar prompts (not exact matches)."""
    by_operation = defaultdict(list)
    
    for call in calls:
        prompt = call.get('prompt', '')
        if not prompt:
            continue
        agent = call.get('agent_name', 'Unknown')
        operation = call.get('operation', 'unknown')
        key = f"{agent}.{operation}"
        by_operation[key].append(call)
    
    near_duplicates = []
    
    for op_key, op_calls in by_operation.items():
        if len(op_calls) < 3:
            continue
        
        normalized = [(c, normalize_prompt(c.get('prompt', ''))) for c in op_calls]
        
        # Find exact duplicate hashes to exclude
        exact_hashes = set()
        hash_counts = defaultdict(int)
        for _, norm in normalized:
            h = hashlib.md5(norm.encode()).hexdigest()[:12]
            hash_counts[h] += 1
        for h, count in hash_counts.items():
            if count >= 2:
                exact_hashes.add(h)
        
        # Cluster by similarity
        clustered = []
        used = set()
        
        for i, (call1, norm1) in enumerate(normalized):
            if i in used:
                continue
            
            h1 = hashlib.md5(norm1.encode()).hexdigest()[:12]
            if h1 in exact_hashes:
                continue
            
            cluster = [call1]
            cluster_prompts = [call1.get('prompt', '')[:100]]
            
            for j, (call2, norm2) in enumerate(normalized):
                if j <= i or j in used:
                    continue
                
                h2 = hashlib.md5(norm2.encode()).hexdigest()[:12]
                if h2 in exact_hashes:
                    continue
                
                similarity = calculate_jaccard_similarity(norm1, norm2)
                if similarity >= SIMILARITY_THRESHOLD and similarity < 1.0:
                    cluster.append(call2)
                    cluster_prompts.append(call2.get('prompt', '')[:100])
                    used.add(j)
            
            if len(cluster) >= 2:
                used.add(i)
                
                parts = op_key.split('.', 1)
                agent = parts[0] if parts else 'Unknown'
                operation = parts[1] if len(parts) > 1 else 'unknown'
                
                total_cost = sum(c.get('total_cost', 0) for c in cluster)
                avg_cost = total_cost / len(cluster)
                potential_savings = (len(cluster) - 1) * avg_cost * 0.8
                
                near_duplicates.append({
                    'agent': agent,
                    'operation': operation,
                    'agent_operation': op_key,
                    'count': len(cluster),
                    'total_cost': total_cost,
                    'potential_savings': potential_savings,
                    'prompt_variations': cluster_prompts[:5],
                    'calls': cluster,
                })
    
    near_duplicates.sort(key=lambda x: -x['potential_savings'])
    return near_duplicates


def find_stable_outputs(calls: List[Dict]) -> List[Dict]:
    """Find operations that return the same output every time."""
    by_operation = defaultdict(list)
    
    for call in calls:
        response = call.get('response_text', '')
        if not response:
            continue
        agent = call.get('agent_name', 'Unknown')
        operation = call.get('operation', 'unknown')
        key = f"{agent}.{operation}"
        by_operation[key].append(call)
    
    stable_outputs = []
    
    for op_key, op_calls in by_operation.items():
        if len(op_calls) < 3:
            continue
        
        responses = [c.get('response_text', '') for c in op_calls if c.get('response_text')]
        if len(responses) < 3:
            continue
        
        normalized_responses = [' '.join(r.lower().split())[:500] for r in responses]
        unique_responses = set(normalized_responses)
        
        if len(unique_responses) / len(normalized_responses) > 0.5:
            continue
        
        response_counts = Counter(normalized_responses)
        most_common_count = response_counts.most_common(1)[0][1]
        stability_rate = most_common_count / len(normalized_responses)
        
        if stability_rate < STABILITY_THRESHOLD:
            continue
        
        parts = op_key.split('.', 1)
        agent = parts[0] if parts else 'Unknown'
        operation = parts[1] if len(parts) > 1 else 'unknown'
        
        total_cost = sum(c.get('total_cost', 0) for c in op_calls)
        avg_cost = total_cost / len(op_calls)
        potential_savings = (len(op_calls) - 1) * avg_cost * stability_rate
        
        stable_outputs.append({
            'agent': agent,
            'operation': operation,
            'agent_operation': op_key,
            'call_count': len(op_calls),
            'stability_rate': stability_rate,
            'unique_responses': len(unique_responses),
            'total_cost': total_cost,
            'potential_savings': potential_savings,
            'sample_response': responses[0][:300] if responses else '',
            'calls': op_calls,
        })
    
    stable_outputs.sort(key=lambda x: -x['potential_savings'])
    return stable_outputs


def find_high_value_calls(calls: List[Dict]) -> List[Dict]:
    """Find expensive/slow operations worth caching."""
    by_operation = defaultdict(list)
    
    for call in calls:
        agent = call.get('agent_name', 'Unknown')
        operation = call.get('operation', 'unknown')
        key = f"{agent}.{operation}"
        by_operation[key].append(call)
    
    high_value = []
    
    for key, op_calls in by_operation.items():
        avg_cost = sum(c.get('total_cost', 0) for c in op_calls) / len(op_calls)
        avg_latency = sum(c.get('latency_ms', 0) for c in op_calls) / len(op_calls)
        total_cost = sum(c.get('total_cost', 0) for c in op_calls)
        
        is_expensive = avg_cost >= HIGH_VALUE_COST_THRESHOLD
        is_slow = avg_latency >= HIGH_VALUE_LATENCY_THRESHOLD
        
        if not (is_expensive or is_slow):
            continue
        
        parts = key.split('.', 1)
        agent = parts[0] if parts else 'Unknown'
        operation = parts[1] if len(parts) > 1 else 'unknown'
        
        high_value.append({
            'agent': agent,
            'operation': operation,
            'agent_operation': key,
            'call_count': len(op_calls),
            'avg_cost': avg_cost,
            'avg_latency': avg_latency,
            'total_cost': total_cost,
            'is_expensive': is_expensive,
            'is_slow': is_slow,
            'calls': op_calls,
        })
    
    high_value.sort(key=lambda x: -x['total_cost'])
    return high_value


# =============================================================================
# ACTIVE MODE - ANALYSIS FUNCTIONS
# =============================================================================

def analyze_cache_performance(calls: List[Dict]) -> Dict:
    """Analyze cache performance by cache type."""
    
    exact_match = {'hits': [], 'misses': [], 'should_have_hit': []}
    semantic = {'hits': [], 'misses': [], 'could_generalize': []}
    stable = {'entries': [], 'expiring_soon': []}
    
    calls_with_cache = [c for c in calls if c.get('cache_metadata')]
    calls_without_cache = [c for c in calls if not c.get('cache_metadata')]
    
    for call in calls_with_cache:
        cache_meta = call.get('cache_metadata') or {}
        cache_type = cache_meta.get('cache_type', 'exact')
        is_hit = cache_meta.get('cache_hit', False)
        
        if cache_type == 'semantic':
            if is_hit:
                semantic['hits'].append(call)
            else:
                semantic['misses'].append(call)
        elif cache_type == 'stable':
            stable['entries'].append(call)
            ttl_remaining = cache_meta.get('ttl_remaining_hours', 999)
            if ttl_remaining < 1:
                stable['expiring_soon'].append(call)
        else:
            if is_hit:
                exact_match['hits'].append(call)
            else:
                exact_match['misses'].append(call)
    
    exact_match['should_have_hit'] = find_missed_cache_opportunities(calls_with_cache)
    semantic['could_generalize'] = find_generalizable_prompts(calls_with_cache)
    
    return {
        'exact_match': exact_match,
        'semantic': semantic,
        'stable': stable,
        'uncached_high_value': find_high_value_calls(calls_without_cache),
    }


def find_missed_cache_opportunities(calls: List[Dict]) -> List[Dict]:
    """Find cache misses that should have been hits."""
    missed = []
    
    by_key = defaultdict(list)
    for call in calls:
        cache_meta = call.get('cache_metadata') or {}
        cache_key = cache_meta.get('cache_key', '')
        if cache_key:
            by_key[cache_key].append(call)
    
    for cache_key, key_calls in by_key.items():
        hits = [c for c in key_calls if (c.get('cache_metadata') or {}).get('cache_hit')]
        misses = [c for c in key_calls if not (c.get('cache_metadata') or {}).get('cache_hit')]
        
        if hits and misses:
            for miss in misses:
                cache_meta = miss.get('cache_metadata') or {}
                
                reason = "Unknown"
                if cache_meta.get('ttl_expired'):
                    reason = "TTL expired"
                elif cache_meta.get('key_mismatch'):
                    reason = "Key mismatch"
                elif cache_meta.get('cache_cold'):
                    reason = "Cache cold (first call)"
                else:
                    reason = "TTL expired (inferred)"
                
                missed.append({
                    'call': miss,
                    'cache_key': cache_key,
                    'reason': reason,
                    'cost': miss.get('total_cost', 0),
                    'agent': miss.get('agent_name', 'Unknown'),
                    'operation': miss.get('operation', 'unknown'),
                })
    
    return missed


def find_generalizable_prompts(calls: List[Dict]) -> List[Dict]:
    """Find prompts that could be generalized for better cache hits."""
    generalizable = []
    
    semantic_misses = [
        c for c in calls 
        if (c.get('cache_metadata') or {}).get('cache_type') == 'semantic'
        and not (c.get('cache_metadata') or {}).get('cache_hit')
    ]
    
    by_operation = defaultdict(list)
    for call in semantic_misses:
        agent = call.get('agent_name', 'Unknown')
        operation = call.get('operation', 'unknown')
        key = f"{agent}.{operation}"
        by_operation[key].append(call)
    
    for op_key, op_calls in by_operation.items():
        if len(op_calls) < 2:
            continue
        
        prompts = [c.get('prompt', '') for c in op_calls]
        issue = detect_prompt_variation_issue(prompts)
        
        if issue:
            parts = op_key.split('.', 1)
            generalizable.append({
                'agent': parts[0] if parts else 'Unknown',
                'operation': parts[1] if len(parts) > 1 else 'unknown',
                'agent_operation': op_key,
                'variant_count': len(op_calls),
                'issue': issue,
                'prompt_samples': prompts[:5],
                'calls': op_calls,
            })
    
    return generalizable


def detect_prompt_variation_issue(prompts: List[str]) -> Optional[str]:
    """Detect what's causing prompt variations."""
    if len(prompts) < 2:
        return None
    
    location_patterns = [
        r'\bSF\b', r'\bSan Francisco\b', r'\bSan Fran\b', r'\bBay Area\b',
        r'\bNYC\b', r'\bNew York\b', r'\bLA\b', r'\bLos Angeles\b',
    ]
    location_matches = sum(1 for p in prompts for pat in location_patterns if re.search(pat, p, re.I))
    if location_matches >= len(prompts):
        return "Location format varies"
    
    word_sets = [set(p.lower().split()) for p in prompts]
    if len(word_sets) >= 2:
        intersection = word_sets[0].intersection(word_sets[1])
        union = word_sets[0].union(word_sets[1])
        if len(intersection) / len(union) < 0.8:
            return "Synonyms not matching"
    
    if any('and' in p.lower() or ',' in p for p in prompts):
        return "Filter order varies"
    
    return "Wording differs"


def analyze_stable_cache_entries(calls: List[Dict]) -> List[Dict]:
    """Analyze stable cache entries and their TTL status."""
    entries = []
    
    stable_calls = [
        c for c in calls 
        if (c.get('cache_metadata') or {}).get('cache_type') == 'stable'
    ]
    
    by_key = defaultdict(list)
    for call in stable_calls:
        cache_meta = call.get('cache_metadata') or {}
        cache_key = cache_meta.get('cache_key', f"{call.get('operation', 'unknown')}:static")
        by_key[cache_key].append(call)
    
    for cache_key, key_calls in by_key.items():
        hits = sum(1 for c in key_calls if (c.get('cache_metadata') or {}).get('cache_hit'))
        
        latest = max(key_calls, key=lambda c: c.get('timestamp') or datetime.min)
        cache_meta = latest.get('cache_metadata') or {}
        ttl_remaining = cache_meta.get('ttl_remaining_hours', 168)
        
        if ttl_remaining <= 0:
            status = "🔴"
        elif ttl_remaining < 1:
            status = "🟡"
        else:
            status = "🟢"
        
        entries.append({
            'cache_key': cache_key,
            'hits': hits,
            'ttl_remaining': ttl_remaining,
            'status': status,
            'calls': key_calls,
        })
    
    entries.sort(key=lambda x: x['ttl_remaining'])
    return entries


# =============================================================================
# DISCOVERY MODE - RENDER FUNCTIONS
# =============================================================================

def render_discovery_mode(calls: List[Dict], cache_stats: Dict):
    """Render Discovery Mode tab content."""
    
    duplicates = find_duplicates(calls)
    near_duplicates = find_near_duplicates(calls)
    stable_outputs = find_stable_outputs(calls)
    high_value = find_high_value_calls(calls)
    
    total_wasted = sum(d['wasted_cost'] for d in duplicates)
    near_dupe_savings = sum(nd['potential_savings'] for nd in near_duplicates)
    stable_savings = sum(so['potential_savings'] for so in stable_outputs)
    total_potential = total_wasted + near_dupe_savings + stable_savings
    potential_monthly = (total_potential / 7) * 30
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Exact Duplicates", len(duplicates))
    with col2:
        st.metric("Wasted Cost", format_cost(total_wasted))
    with col3:
        st.metric("Near-Duplicates", len(near_duplicates))
    with col4:
        st.metric("Potential Savings", f"{format_cost(potential_monthly)}/mo")
    
    st.divider()
    
    render_discovery_exact_match(duplicates)
    st.divider()
    render_discovery_semantic(near_duplicates)
    st.divider()
    render_discovery_stable(stable_outputs)
    st.divider()
    render_discovery_high_value(high_value)


def render_discovery_exact_match(duplicates: List[Dict]):
    """Render exact match discovery section."""
    
    st.subheader("1️⃣ Exact Match Patterns")
    st.caption("Identical prompts called multiple times — click a row to see details")
    
    if not duplicates:
        st.success("✅ No exact duplicates found")
        return
    
    table_data = []
    for d in duplicates:
        table_data.append({
            'Agent.Operation': d['agent_operation'],
            'Count': d['count'],
            'Wasted': format_cost(d['wasted_cost']),
            'Avg Cost': format_cost(d['avg_cost']),
            'Sample': truncate_text(d['prompt_sample'], 40),
        })
    
    df = pd.DataFrame(table_data)
    
    selection = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="discovery_exact_table"
    )
    
    total_wasted = sum(d['wasted_cost'] for d in duplicates)
    st.caption(f"Total: {len(duplicates)} groups • {format_cost(total_wasted)} wasted")
    
    selected_rows = selection.selection.rows if selection.selection else []
    if selected_rows and selected_rows[0] < len(duplicates):
        render_discovery_detail(duplicates[selected_rows[0]], "exact")


def render_discovery_semantic(near_duplicates: List[Dict]):
    """Render semantic similarity discovery section."""
    
    st.subheader("2️⃣ Semantic Similarity Patterns")
    st.caption("Similar prompts (not exact) that could use semantic caching")
    
    if not near_duplicates:
        st.success("✅ No near-duplicate patterns found")
        return
    
    table_data = []
    for nd in near_duplicates:
        table_data.append({
            'Agent.Operation': nd['agent_operation'],
            'Variants': nd['count'],
            'Potential': format_cost(nd['potential_savings']),
            'Total Cost': format_cost(nd['total_cost']),
        })
    
    df = pd.DataFrame(table_data)
    
    selection = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="discovery_semantic_table"
    )
    
    total_potential = sum(nd['potential_savings'] for nd in near_duplicates)
    st.caption(f"Total potential: {format_cost(total_potential)} with semantic caching")
    
    selected_rows = selection.selection.rows if selection.selection else []
    if selected_rows and selected_rows[0] < len(near_duplicates):
        render_discovery_detail(near_duplicates[selected_rows[0]], "semantic")


def render_discovery_stable(stable_outputs: List[Dict]):
    """Render stable outputs discovery section."""
    
    st.subheader("3️⃣ Stable Output Patterns")
    st.caption("Operations returning same response — cache with long TTL")
    
    if not stable_outputs:
        st.success("✅ No stable output patterns found")
        return
    
    table_data = []
    for so in stable_outputs:
        table_data.append({
            'Agent.Operation': so['agent_operation'],
            'Calls': so['call_count'],
            'Stability': format_percentage(so['stability_rate']),
            'Unique': so['unique_responses'],
            'Potential': format_cost(so['potential_savings']),
        })
    
    df = pd.DataFrame(table_data)
    
    selection = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="discovery_stable_table"
    )
    
    total_potential = sum(so['potential_savings'] for so in stable_outputs)
    st.caption(f"Total potential: {format_cost(total_potential)} with long-TTL caching")
    
    selected_rows = selection.selection.rows if selection.selection else []
    if selected_rows and selected_rows[0] < len(stable_outputs):
        render_discovery_detail(stable_outputs[selected_rows[0]], "stable")


def render_discovery_high_value(high_value: List[Dict]):
    """Render high-value discovery section."""
    
    st.subheader("4️⃣ High-Value Patterns")
    st.caption("Expensive/slow calls worth caching")
    
    if not high_value:
        st.success(f"✅ No high-value targets (>${HIGH_VALUE_COST_THRESHOLD:.2f}/call or >{HIGH_VALUE_LATENCY_THRESHOLD/1000:.0f}s)")
        return
    
    table_data = []
    for hv in high_value:
        flags = []
        if hv['is_expensive']:
            flags.append("💰")
        if hv['is_slow']:
            flags.append("🐌")
        
        table_data.append({
            '': ' '.join(flags),
            'Agent.Operation': hv['agent_operation'],
            'Calls': hv['call_count'],
            'Avg Cost': format_cost(hv['avg_cost']),
            'Avg Time': format_latency(hv['avg_latency']),
            'Total': format_cost(hv['total_cost']),
        })
    
    df = pd.DataFrame(table_data)
    
    selection = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="discovery_highvalue_table"
    )
    
    total_cost = sum(hv['total_cost'] for hv in high_value)
    st.caption(f"Total: {len(high_value)} operations • {format_cost(total_cost)}")
    
    selected_rows = selection.selection.rows if selection.selection else []
    if selected_rows and selected_rows[0] < len(high_value):
        render_discovery_detail(high_value[selected_rows[0]], "high_value")


def render_discovery_detail(item: Dict, pattern_type: str):
    """Render detail view for discovery mode item."""
    
    st.markdown("---")
    
    agent = item.get('agent', 'Unknown')
    operation = item.get('operation', 'unknown')
    
    if pattern_type == "exact":
        st.markdown(f"**▼ {item['agent_operation']} — {item['count']} identical calls**")
    elif pattern_type == "semantic":
        st.markdown(f"**▼ {item['agent_operation']} — {item['count']} similar prompts**")
    elif pattern_type == "stable":
        st.markdown(f"**▼ {item['agent_operation']} — {format_percentage(item['stability_rate'])} stable**")
    else:
        flags = []
        if item.get('is_expensive'):
            flags.append(f"💰 {format_cost(item['avg_cost'])}/call")
        if item.get('is_slow'):
            flags.append(f"🐌 {format_latency(item['avg_latency'])}")
        st.markdown(f"**▼ {item['agent_operation']} — {' • '.join(flags)}**")
    
    calls = item.get('calls', [])
    calls_data = []
    for call in calls[:15]:
        timestamp = call.get('timestamp')
        time_str = timestamp.strftime("%H:%M:%S") if timestamp else "—"
        
        row = {
            'Time': time_str,
            'Latency': format_latency(call.get('latency_ms', 0)),
            'Cost': format_cost(call.get('total_cost', 0)),
            'Tokens': call.get('total_tokens', 0),
        }
        
        if pattern_type == "semantic":
            row['Prompt'] = truncate_text(call.get('prompt', ''), 40)
        elif pattern_type == "stable":
            row['Response'] = truncate_text(call.get('response_text', ''), 40)
        else:
            row['Model'] = format_model_name(call.get('model_name', ''))
        
        calls_data.append(row)
    
    df = pd.DataFrame(calls_data)
    st.dataframe(df, width='stretch', hide_index=True)
    
    if len(calls) > 15:
        st.caption(f"Showing 15 of {len(calls)} calls")
    
    if pattern_type == "semantic":
        st.markdown("**Prompt variations:**")
        for i, prompt in enumerate(item.get('prompt_variations', [])[:5], 1):
            st.code(f"{i}. {prompt}...", language="text")
    elif pattern_type == "stable":
        with st.expander("📝 Sample Response"):
            st.code(item.get('sample_response', 'N/A'), language="text")
    else:
        with st.expander("📝 Prompt"):
            prompt = item.get('prompt_full', '') or (calls[0].get('prompt', '') if calls else '')
            st.code(prompt[:1000], language="text")
    
    st.markdown("---")
    st.markdown("**🛠️ Implementation**")
    
    if pattern_type == "semantic":
        ttl, invalidation = get_ttl_recommendation(operation)
        st.markdown(f"""
**Cache key:** `f"{operation}:{{embedding_hash}}"`  
**File:** `agents/plugins/{agent}Plugin.py`  
**Method:** `{operation}()`  
**Pattern:** Semantic similarity — same intent, different wording  
**TTL:** {ttl}  
**Invalidate:** {invalidation}  
**Requires:** Embedding model + vector similarity search
""")
        
        code = f'''# Semantic caching with embeddings
embedding = await embed(prompt)
embedding_hash = hash_embedding(embedding)

similar = await vector_cache.search(embedding, threshold=0.95)
if similar:
    track_llm_call(
        agent_name="{agent}",
        operation="{operation}",
        cache_metadata={{"cache_hit": True, "cache_type": "semantic"}}
    )
    return similar.result

# ... your existing LLM call ...

await vector_cache.store(embedding, response, ttl_hours={ttl.split()[0]})'''
    
    elif pattern_type == "stable":
        st.markdown(f"""
**Cache key:** `f"{operation}:static"` or `f"{operation}:{{schema_version}}"`  
**File:** `agents/plugins/{agent}Plugin.py`  
**Method:** `{operation}()`  
**Pattern:** Output rarely changes — use long TTL  
**TTL:** 7 days  
**Invalidate:** On deployment, schema change, or manual trigger
""")
        
        code = f'''# Long-TTL caching for stable outputs
cache_key = f"{operation}:static"

cached = self.cache.get(cache_key)
if cached:
    track_llm_call(
        agent_name="{agent}",
        operation="{operation}",
        cache_metadata={{"cache_hit": True, "cache_type": "stable"}}
    )
    return cached

# ... your existing LLM call ...

self.cache.set(cache_key, response, ttl_hours=168)  # 7 days'''
    
    else:
        pattern, cache_key = extract_cache_key_pattern(calls)
        ttl, invalidation = get_ttl_recommendation(operation)
        
        savings_note = ""
        if pattern_type == "high_value":
            savings_note = f"\n**If 50% hit rate:** Save ~{format_cost(item['total_cost'] * 0.5)}/period"
        
        st.markdown(f"""
**Cache key:** `{cache_key}`  
**File:** `agents/plugins/{agent}Plugin.py`  
**Method:** `{operation}()`  
**Pattern:** {pattern}  
**TTL:** {ttl}  
**Invalidate:** {invalidation}{savings_note}
""")
        
        code = f'''# Check cache first
cache_key = {cache_key}
cached = self.cache.get(cache_key)
if cached:
    track_llm_call(
        agent_name="{agent}",
        operation="{operation}",
        cache_metadata={{"cache_hit": True, "cache_key": cache_key}}
    )
    return cached

# ... your existing LLM call ...

self.cache.set(cache_key, response, ttl_hours={ttl.split()[0]})'''
    
    with st.expander("📋 Code snippet"):
        st.code(code, language="python")


# =============================================================================
# ACTIVE MODE - RENDER FUNCTIONS
# =============================================================================

def render_active_mode(calls: List[Dict], cache_stats: Dict):
    """Render Active Mode tab content."""
    
    st.markdown("🟢 **Cache Active**")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        delta = "+5% vs last" if cache_stats['hit_rate'] > 0.5 else None
        st.metric("Hit Rate", format_percentage(cache_stats['hit_rate']), delta=delta)
    with col2:
        st.metric("Cost Saved", format_cost(cache_stats['cost_saved']))
    with col3:
        time_saved_min = cache_stats['time_saved_ms'] / 60000
        st.metric("Time Saved", f"{time_saved_min:.1f} min")
    with col4:
        perf = analyze_cache_performance(calls)
        missed_count = len(perf['exact_match']['should_have_hit'])
        st.metric("Missed Opps", missed_count, delta="⚠️ fixable" if missed_count > 0 else None)
    
    st.divider()
    
    perf = analyze_cache_performance(calls)
    
    render_active_exact_match(perf['exact_match'], calls)
    st.divider()
    render_active_semantic(perf['semantic'], calls)
    st.divider()
    render_active_stable(perf['stable'], calls)
    st.divider()
    render_active_uncached(perf['uncached_high_value'])


def render_active_exact_match(exact_data: Dict, calls: List[Dict]):
    """Render exact match cache performance."""
    
    st.subheader("1️⃣ Exact Match Cache")
    
    hits = len(exact_data['hits'])
    misses = len(exact_data['misses'])
    total = hits + misses
    hit_rate = hits / total if total > 0 else 0
    cost_saved = sum(c.get('total_cost', 0) for c in exact_data['hits'])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Hits", hits)
    with col2:
        st.metric("Misses", misses)
    with col3:
        st.metric("Hit Rate", format_percentage(hit_rate))
    with col4:
        st.metric("Cost Saved", format_cost(cost_saved))
    
    should_have_hit = exact_data['should_have_hit']
    
    if should_have_hit:
        st.markdown(f"⚠️ **{len(should_have_hit)} Missed Opportunities** — click to see why")
        
        by_reason = defaultdict(list)
        for item in should_have_hit:
            key = f"{item['agent']}.{item['operation']}"
            by_reason[(key, item['reason'])].append(item)
        
        table_data = []
        for (op, reason), items in by_reason.items():
            table_data.append({
                'Agent.Operation': op,
                'Count': len(items),
                'Reason': reason,
                'Cost Lost': format_cost(sum(i['cost'] for i in items)),
            })
        
        df = pd.DataFrame(table_data)
        
        selection = st.dataframe(
            df,
            width='stretch',
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="active_exact_missed_table"
        )
        
        selected_rows = selection.selection.rows if selection.selection else []
        if selected_rows:
            selected_key = list(by_reason.keys())[selected_rows[0]]
            render_missed_opportunity_detail(by_reason[selected_key], selected_key[1])
    else:
        st.success("✅ No missed cache opportunities")


def render_missed_opportunity_detail(items: List[Dict], reason: str):
    """Render detail for missed cache opportunities."""
    
    st.markdown("---")
    
    op = items[0]['agent'] + "." + items[0]['operation']
    st.markdown(f"**▼ {op} — {len(items)} {reason}**")
    
    if reason == "TTL expired" or reason == "TTL expired (inferred)":
        st.write("These calls missed cache because TTL expired. Consider longer TTL.")
    elif reason == "Key mismatch":
        st.write("Cache key didn't match due to whitespace or formatting differences.")
    elif reason == "Cache cold (first call)":
        st.write("First call for this key — expected, no action needed.")
    
    table_data = []
    for item in items[:10]:
        call = item['call']
        timestamp = call.get('timestamp')
        time_str = timestamp.strftime("%H:%M:%S") if timestamp else "—"
        
        table_data.append({
            'Time': time_str,
            'Cache Key': truncate_text(item['cache_key'], 40),
            'Cost': format_cost(item['cost']),
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, width='stretch', hide_index=True)
    
    if "TTL" in reason:
        st.markdown("💡 **Fix:** Increase TTL for this operation")
        
        with st.expander("📋 Code change"):
            st.code('''# Change TTL from 1 hour to 24 hours
self.cache.set(cache_key, response, ttl_hours=24)  # was ttl_hours=1''', language="python")


def render_active_semantic(semantic_data: Dict, calls: List[Dict]):
    """Render semantic cache performance."""
    
    st.subheader("2️⃣ Semantic Cache")
    
    hits = len(semantic_data['hits'])
    misses = len(semantic_data['misses'])
    total = hits + misses
    hit_rate = hits / total if total > 0 else 0
    cost_saved = sum(c.get('total_cost', 0) for c in semantic_data['hits'])
    
    if total == 0:
        st.info("No semantic caching detected. Enable semantic caching for better hit rates on similar prompts.")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Hits", hits)
    with col2:
        st.metric("Misses", misses)
    with col3:
        st.metric("Hit Rate", format_percentage(hit_rate))
    with col4:
        st.metric("Cost Saved", format_cost(cost_saved))
    
    could_generalize = semantic_data['could_generalize']
    
    if could_generalize:
        st.markdown(f"⚠️ **{len(could_generalize)} Prompts Could Be Generalized**")
        
        table_data = []
        for item in could_generalize:
            table_data.append({
                'Agent.Operation': item['agent_operation'],
                'Variants': item['variant_count'],
                'Issue': item['issue'],
            })
        
        df = pd.DataFrame(table_data)
        
        selection = st.dataframe(
            df,
            width='stretch',
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="active_semantic_generalize_table"
        )
        
        selected_rows = selection.selection.rows if selection.selection else []
        if selected_rows and selected_rows[0] < len(could_generalize):
            render_generalize_detail(could_generalize[selected_rows[0]])
    else:
        st.success("✅ No prompts need generalization")


def render_generalize_detail(item: Dict):
    """Render detail for prompts that could be generalized."""
    
    st.markdown("---")
    st.markdown(f"**▼ {item['agent_operation']} — {item['variant_count']} variants**")
    st.write(f"These prompts ask the same thing but don't hit cache due to: **{item['issue']}**")
    
    st.markdown("**Prompt variations:**")
    for prompt in item.get('prompt_samples', [])[:5]:
        st.code(f"❌ {prompt[:80]}...", language="text")
    
    st.markdown("💡 **Fix:** Normalize before cache lookup")
    
    if item['issue'] == "Location format varies":
        code = '''# Normalize location before cache lookup
location = normalize_location(raw_location)  # "SF" → "San Francisco, CA"
cache_key = f"salary:{job_title}:{location}"'''
    elif item['issue'] == "Synonyms not matching":
        code = '''# Use canonical terms
job_title = canonicalize_title(raw_title)  # "Dev" → "Developer"
cache_key = f"query:{job_title}"'''
    else:
        code = '''# Normalize prompt structure
normalized = normalize_prompt(raw_prompt)
cache_key = f"query:{hash(normalized)}"'''
    
    with st.expander("📋 Code change"):
        st.code(code, language="python")


def render_active_stable(stable_data: Dict, calls: List[Dict]):
    """Render stable output cache performance."""
    
    st.subheader("3️⃣ Stable Output Cache")
    
    entries = analyze_stable_cache_entries(calls)
    
    if not entries:
        st.info("No stable output caching detected.")
        return
    
    total_hits = sum(e['hits'] for e in entries)
    expiring_soon = [e for e in entries if e['ttl_remaining'] < 1]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Cached Items", len(entries))
    with col2:
        st.metric("Total Hits", total_hits)
    with col3:
        avg_hit_rate = total_hits / (len(entries) * 10) if entries else 0
        st.metric("Avg Hit Rate", format_percentage(min(avg_hit_rate, 1)))
    with col4:
        st.metric("Expiring Soon", len(expiring_soon))
    
    st.markdown("**📋 Cached Entries**")
    
    table_data = []
    for entry in entries:
        table_data.append({
            'Status': entry['status'],
            'Cache Key': truncate_text(entry['cache_key'], 35),
            'Hits': entry['hits'],
            'TTL Left': format_ttl_remaining(entry['ttl_remaining']),
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, width='stretch', hide_index=True)
    
    if expiring_soon:
        st.warning(f"⚠️ {len(expiring_soon)} entries expiring soon — will cause cache misses")
        st.markdown("💡 **Fix:** Increase TTL or set up background refresh")


def render_active_uncached(uncached_high_value: List[Dict]):
    """Render high-value calls that aren't cached yet."""
    
    st.subheader("4️⃣ High-Value (Not Yet Cached)")
    
    if not uncached_high_value:
        st.success("✅ All high-value operations have caching enabled")
        return
    
    st.write("These expensive operations don't have caching enabled yet:")
    
    table_data = []
    for hv in uncached_high_value:
        table_data.append({
            'Agent.Operation': hv['agent_operation'],
            'Calls': hv['call_count'],
            'Avg Cost': format_cost(hv['avg_cost']),
            'Avg Time': format_latency(hv['avg_latency']),
            'Potential': format_cost(hv['total_cost'] * 0.5) + "/wk",
        })
    
    df = pd.DataFrame(table_data)
    
    selection = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="active_uncached_table"
    )
    
    st.caption("Click row for implementation guide →")
    
    selected_rows = selection.selection.rows if selection.selection else []
    if selected_rows and selected_rows[0] < len(uncached_high_value):
        render_discovery_detail(uncached_high_value[selected_rows[0]], "high_value")


# =============================================================================
# FILTERED VIEW (from Cost Estimator)
# =============================================================================

def render_filtered_view(calls: List[Dict], agent: str, operation: str):
    """Render filtered view when coming from Cost Estimator."""
    
    filtered_calls = [
        c for c in calls 
        if c.get('agent_name') == agent and c.get('operation') == operation
    ]
    
    if not filtered_calls:
        st.warning(f"No calls found for {agent}.{operation}")
        return
    
    prompt_groups = defaultdict(list)
    
    for call in filtered_calls:
        prompt = call.get('prompt') or ''
        if not prompt:
            continue
        
        normalized = normalize_prompt(prompt)
        prompt_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]
        prompt_groups[prompt_hash].append(call)
    
    groups = []
    group_num = 1
    
    for prompt_hash, group_calls in sorted(prompt_groups.items(), key=lambda x: -len(x[1])):
        if len(group_calls) < DUPLICATE_THRESHOLD:
            continue
        
        total_cost = sum(c.get('total_cost', 0) for c in group_calls)
        avg_cost = total_cost / len(group_calls) if group_calls else 0
        wasted_cost = (len(group_calls) - 1) * avg_cost
        
        groups.append({
            'group_num': group_num,
            'count': len(group_calls),
            'wasted_cost': wasted_cost,
            'avg_cost': avg_cost,
            'prompt_sample': group_calls[0].get('prompt', '')[:80],
            'prompt_full': group_calls[0].get('prompt', ''),
            'calls': group_calls,
        })
        group_num += 1
    
    total_calls = sum(g['count'] for g in groups)
    total_wasted = sum(g['wasted_cost'] for g in groups)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Duplicate Groups", len(groups))
    with col2:
        st.metric("Total Calls", total_calls)
    with col3:
        st.metric("Wasted Cost", format_cost(total_wasted))
    
    st.divider()
    
    st.subheader(f"🔁 {len(groups)} Duplicate Groups")
    
    if not groups:
        st.success("✅ No duplicates found for this operation")
        return
    
    table_data = []
    for g in groups:
        table_data.append({
            'Group': g['group_num'],
            'Count': g['count'],
            'Wasted': format_cost(g['wasted_cost']),
            'Sample': truncate_text(g['prompt_sample'], 50),
        })
    
    df = pd.DataFrame(table_data)
    
    selection = st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="filtered_groups_table"
    )
    
    selected_rows = selection.selection.rows if selection.selection else []
    if selected_rows and selected_rows[0] < len(groups):
        group = groups[selected_rows[0]]
        
        st.markdown("---")
        st.markdown(f"**▼ Group {group['group_num']} — {group['count']} calls**")
        
        calls_data = []
        for call in group['calls'][:20]:
            timestamp = call.get('timestamp')
            time_str = timestamp.strftime("%H:%M:%S") if timestamp else "—"
            
            calls_data.append({
                'Time': time_str,
                'Latency': format_latency(call.get('latency_ms', 0)),
                'Cost': format_cost(call.get('total_cost', 0)),
                'Tokens': call.get('total_tokens', 0),
            })
        
        df = pd.DataFrame(calls_data)
        st.dataframe(df, width='stretch', hide_index=True)
        
        with st.expander("📝 Prompt"):
            st.code(group['prompt_full'], language="text")
        
        st.markdown(f"**Wasted:** {format_cost(group['wasted_cost'])} ({group['count'] - 1} unnecessary × {format_cost(group['avg_cost'])})")
    
    st.markdown("---")
    st.markdown("**🛠️ Implementation**")
    
    all_calls = []
    for g in groups:
        all_calls.extend(g['calls'])
    
    pattern, cache_key = extract_cache_key_pattern(all_calls)
    ttl, invalidation = get_ttl_recommendation(operation)
    
    st.markdown(f"""
**Cache key:** `{cache_key}`  
**File:** `agents/plugins/{agent}Plugin.py`  
**Method:** `{operation}()`  
**Pattern:** {pattern}  
**TTL:** {ttl}  
**Invalidate:** {invalidation}
""")
    
    code = f'''# Check cache first
cache_key = {cache_key}
cached = self.cache.get(cache_key)
if cached:
    track_llm_call(
        agent_name="{agent}",
        operation="{operation}",
        cache_metadata={{"cache_hit": True, "cache_key": cache_key}}
    )
    return cached

# ... your existing LLM call ...

self.cache.set(cache_key, response, ttl_hours={ttl.split()[0]})'''
    
    with st.expander("📋 Code snippet"):
        st.code(code, language="python")


# =============================================================================
# MAIN RENDER
# =============================================================================

def render():
    """Main render function for Cache Analyzer page."""
    
    st.title("💾 Cache Analyzer")
    
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
            key="cache_limit",
            label_visibility="collapsed"
        )
    
    with col3:
        if st.button("🔄 Refresh", width='stretch'):
            st.cache_data.clear()
            st.rerun()
    
    # Check for incoming filters
    # From Home: cache_tab (value: "repeated") 
    # From Cost Estimator: cache_filter (dict with agent, operation)
    incoming_tab = st.session_state.get('cache_tab')
    incoming_filter = st.session_state.get('cache_filter')
    
    # Clear tab filter after use (just a navigation hint)
    if incoming_tab:
        del st.session_state['cache_tab']
    
    if incoming_filter:
        agent = incoming_filter.get('agent', '')
        operation = incoming_filter.get('operation', '')
        
        col1, col2 = st.columns([4, 1])
        with col1:
            st.info(f"🎯 Filtered: **{agent}.{operation}**")
        with col2:
            if st.button("✕ Clear", key="clear_cache_filter"):
                del st.session_state['cache_filter']
                st.rerun()
    
    st.divider()
    
    try:
        calls = get_llm_calls(project_name=selected_project, limit=limit)
        
        if not calls:
            render_empty_state(
                message="No data available for cache analysis",
                icon="💾",
                suggestion="Run AI agents with Observatory tracking to analyze caching opportunities"
            )
            return
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    is_active, cache_stats = detect_cache_mode(calls)
    
    if incoming_filter:
        agent = incoming_filter.get('agent', '')
        operation = incoming_filter.get('operation', '')
        render_filtered_view(calls, agent, operation)
        return
    
    mode = st.radio(
        "Mode",
        ["🔍 Discovery", "⚡ Active"],
        horizontal=True,
        key="cache_mode"
    )

    if mode == "🔍 Discovery":
        if is_active:
            st.info("Cache is active! Check Active Mode for performance metrics.")
        render_discovery_mode(calls, cache_stats)
    else:
        if not is_active:
            st.warning("Cache not detected. Implement caching using Discovery Mode suggestions first.")
        else:
            render_active_mode(calls, cache_stats)