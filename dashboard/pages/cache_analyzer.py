"""
Cache Analyzer - Developer Diagnostics Dashboard
Location: dashboard/pages/cache_analyzer.py

Developer-focused cache analysis:
1. Overview - Cache opportunity summary
2. Repeated Calls - Duplicate detection with fix suggestions
3. High-Value - Expensive calls worth caching
4. Cache Keys - Strategy recommendations

UPDATED: 
- New 4-tab developer layout
- Null-safe field access patterns
- Uses correct Tier 2 CacheMetadata fields
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
from collections import defaultdict
import hashlib
import re

from dashboard.utils.data_fetcher import (
    get_project_overview,
    get_llm_calls,
    get_available_agents,
    get_available_operations,
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


# =============================================================================
# CONSTANTS
# =============================================================================

HIGH_VALUE_COST_THRESHOLD = 0.10  # $0.10 per call
HIGH_VALUE_LATENCY_THRESHOLD = 5000  # 5 seconds
DUPLICATE_THRESHOLD = 2  # Minimum occurrences to be considered duplicate


# =============================================================================
# CACHE DETECTION
# =============================================================================

def detect_cache_mode(calls: List[Dict]) -> Tuple[bool, str, Dict]:
    """
    Detect if real caching is active or in discovery mode.
    
    Returns:
        Tuple of (has_real_cache, mode_description, stats)
    """
    if not calls:
        return False, "No data", {}
    
    # Check for calls with cache_metadata
    calls_with_cache = [
        c for c in calls 
        if c.get('cache_metadata') is not None
    ]
    
    stats = {
        'total_calls': len(calls),
        'calls_with_cache': len(calls_with_cache),
        'cache_hits': 0,
        'cache_misses': 0,
    }
    
    if len(calls_with_cache) == 0:
        return False, "Discovery Mode — Cache not implemented yet", stats
    
    # Count actual cache hits (null-safe)
    for c in calls_with_cache:
        cache_meta = c.get('cache_metadata') or {}
        if cache_meta.get('cache_hit'):
            stats['cache_hits'] += 1
        else:
            stats['cache_misses'] += 1
    
    if stats['cache_hits'] > 0:
        hit_rate = stats['cache_hits'] / len(calls_with_cache)
        return True, f"Cache Active — {format_percentage(hit_rate)} hit rate", stats
    else:
        return True, "Cache Enabled — Waiting for hits", stats


# =============================================================================
# PROMPT ANALYSIS
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
    
    # Remove numbers (but keep some context)
    normalized = re.sub(r'\b\d{5,}\b', '[ID]', normalized)
    
    # Normalize whitespace
    normalized = ' '.join(normalized.split())
    
    return normalized.lower()


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate Jaccard similarity between two texts."""
    if not text1 or not text2:
        return 0.0
    
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union) if union else 0.0


def extract_prompt_components(call: Dict) -> Dict[str, Any]:
    """Extract stable vs dynamic parts of a prompt."""
    prompt = call.get('prompt') or ''
    
    # Check for prompt_breakdown from Tier 2
    breakdown = call.get('prompt_breakdown') or {}
    
    if breakdown:
        return {
            'system_prompt': breakdown.get('system_prompt', '')[:500],
            'system_tokens': breakdown.get('system_prompt_tokens', 0),
            'user_message': breakdown.get('user_message', '')[:300],
            'user_tokens': breakdown.get('user_message_tokens', 0),
            'history_tokens': breakdown.get('chat_history_tokens', 0),
            'history_count': breakdown.get('chat_history_count', 0),
            'has_breakdown': True,
        }
    
    # Estimate from raw prompt
    has_history = bool(re.search(r'Human:|User:|Assistant:|AI:', prompt, re.I))
    message_count = len(re.findall(r'Human:|User:|Assistant:|AI:', prompt, re.I))
    
    return {
        'system_prompt': prompt[:500],
        'system_tokens': call.get('prompt_tokens', 0) // 3,
        'user_message': prompt[-300:] if len(prompt) > 300 else prompt,
        'user_tokens': call.get('prompt_tokens', 0) // 3,
        'history_tokens': call.get('prompt_tokens', 0) // 3 if has_history else 0,
        'history_count': message_count,
        'has_breakdown': False,
    }


# =============================================================================
# DUPLICATE DETECTION
# =============================================================================

def find_duplicates(calls: List[Dict]) -> List[Dict]:
    """
    Find duplicate/repeated calls grouped by normalized prompt.
    
    Returns list of duplicate groups with analysis.
    """
    # Group by normalized prompt
    prompt_groups = defaultdict(list)
    
    for call in calls:
        prompt = call.get('prompt') or ''
        if not prompt:
            continue
        
        normalized = normalize_prompt(prompt)
        prompt_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]
        prompt_groups[prompt_hash].append({
            'call': call,
            'normalized': normalized,
            'original': prompt,
        })
    
    # Filter to duplicates only (2+ occurrences)
    duplicates = []
    
    for prompt_hash, group in prompt_groups.items():
        if len(group) < DUPLICATE_THRESHOLD:
            continue
        
        calls_in_group = [g['call'] for g in group]
        
        # Calculate stats
        total_cost = sum(c.get('total_cost', 0) for c in calls_in_group)
        total_tokens = sum(c.get('total_tokens', 0) for c in calls_in_group)
        avg_latency = sum(c.get('latency_ms', 0) for c in calls_in_group) / len(calls_in_group)
        
        # Wasted cost = (count - 1) * avg_cost (first call is necessary)
        avg_cost = total_cost / len(calls_in_group)
        wasted_cost = (len(calls_in_group) - 1) * avg_cost
        
        # Time analysis
        timestamps = [c.get('timestamp') for c in calls_in_group if c.get('timestamp')]
        if timestamps:
            first_seen = min(timestamps)
            last_seen = max(timestamps)
            time_span = (last_seen - first_seen).total_seconds() / 3600  # hours
            frequency = len(calls_in_group) / max(time_span, 1)  # per hour
        else:
            first_seen = last_seen = None
            frequency = 0
        
        # Detect why it's repeating
        operations = list(set(c.get('operation') or 'unknown' for c in calls_in_group))
        agents = list(set(c.get('agent_name') or 'unknown' for c in calls_in_group))
        
        # Identify dynamic fields
        dynamic_fields = []
        if re.search(r'\d{4}-\d{2}-\d{2}', group[0]['original']):
            dynamic_fields.append('timestamp')
        if re.search(r'sess_', group[0]['original']):
            dynamic_fields.append('session_id')
        
        duplicates.append({
            'hash': prompt_hash,
            'count': len(calls_in_group),
            'calls': calls_in_group,
            'representative': group[0]['original'],
            'normalized': group[0]['normalized'],
            'total_cost': total_cost,
            'wasted_cost': wasted_cost,
            'avg_cost': avg_cost,
            'avg_latency': avg_latency,
            'total_tokens': total_tokens,
            'first_seen': first_seen,
            'last_seen': last_seen,
            'frequency': frequency,
            'operations': operations,
            'agents': agents,
            'dynamic_fields': dynamic_fields,
        })
    
    # Sort by wasted cost (highest first)
    duplicates.sort(key=lambda x: -x['wasted_cost'])
    
    return duplicates


# =============================================================================
# HIGH-VALUE DETECTION
# =============================================================================

def find_high_value_calls(calls: List[Dict]) -> List[Dict]:
    """
    Find expensive calls worth caching even with low duplication.
    """
    high_value = []
    
    # Group by operation for analysis
    by_operation = defaultdict(list)
    for call in calls:
        op = call.get('operation') or 'unknown'
        by_operation[op].append(call)
    
    for operation, op_calls in by_operation.items():
        avg_cost = sum(c.get('total_cost', 0) for c in op_calls) / len(op_calls)
        avg_latency = sum(c.get('latency_ms', 0) for c in op_calls) / len(op_calls)
        
        # Check if high value
        is_expensive = avg_cost >= HIGH_VALUE_COST_THRESHOLD
        is_slow = avg_latency >= HIGH_VALUE_LATENCY_THRESHOLD
        
        if not (is_expensive or is_slow):
            continue
        
        # Analyze duplicates within this operation
        prompt_hashes = defaultdict(int)
        for call in op_calls:
            normalized = normalize_prompt(call.get('prompt') or '')
            prompt_hashes[normalized] += 1
        
        exact_duplicates = sum(1 for v in prompt_hashes.values() if v > 1)
        duplicate_pct = exact_duplicates / len(prompt_hashes) if prompt_hashes else 0
        
        # Analyze semantic similarity
        prompts = [normalize_prompt(c.get('prompt', '')) for c in op_calls[:20]]
        semantic_clusters = []
        used = set()
        
        for i, p1 in enumerate(prompts):
            if i in used:
                continue
            cluster = [i]
            for j, p2 in enumerate(prompts[i+1:], i+1):
                if j in used:
                    continue
                if calculate_similarity(p1, p2) > 0.8:
                    cluster.append(j)
                    used.add(j)
            if len(cluster) > 1:
                semantic_clusters.append(cluster)
            used.add(i)
        
        semantic_similar_pct = sum(len(c) for c in semantic_clusters) / len(prompts) if prompts else 0
        
        high_value.append({
            'operation': operation,
            'call_count': len(op_calls),
            'avg_cost': avg_cost,
            'avg_latency': avg_latency,
            'total_cost': sum(c.get('total_cost', 0) for c in op_calls),
            'is_expensive': is_expensive,
            'is_slow': is_slow,
            'exact_duplicate_pct': duplicate_pct,
            'semantic_similar_pct': semantic_similar_pct,
            'potential_savings': avg_cost * len(op_calls) * max(duplicate_pct, semantic_similar_pct * 0.5),
            'models_used': list(set(c.get('model_name') or '' for c in op_calls)),
            'sample_calls': op_calls[:5],
        })
    
    # Sort by potential savings
    high_value.sort(key=lambda x: -x['potential_savings'])
    
    return high_value


# =============================================================================
# CACHE KEY ANALYSIS
# =============================================================================

def analyze_cache_keys(calls: List[Dict]) -> List[Dict]:
    """
    Analyze prompt structure to recommend cache key strategies.
    """
    # Group by operation
    by_operation = defaultdict(list)
    for call in calls:
        op = call.get('operation') or 'unknown'
        by_operation[op].append(call)
    
    strategies = []
    
    for operation, op_calls in by_operation.items():
        if len(op_calls) < 3:
            continue
        
        # Analyze prompt components
        components = defaultdict(lambda: {'values': set(), 'variance': 0})
        
        for call in op_calls[:50]:  # Sample
            prompt = (call.get('prompt') or '')
            
            # Check for common patterns
            # System prompt (usually at start)
            system_match = re.match(r'^(.*?)(Human:|User:|$)', prompt, re.S)
            if system_match:
                system = system_match.group(1)[:200]
                components['system_prompt']['values'].add(system)
            
            # Look for IDs
            ids = re.findall(r'\b[a-zA-Z_]+_id["\s:=]+([a-zA-Z0-9_-]+)', prompt, re.I)
            for id_val in ids:
                components['entity_ids']['values'].add(id_val)
            
            # Timestamps
            timestamps = re.findall(r'\d{4}-\d{2}-\d{2}', prompt)
            for ts in timestamps:
                components['timestamps']['values'].add(ts)
            
            # Check metadata for hints (null-safe)
            metadata = call.get('prompt_metadata') or {}
            dynamic_fields = metadata.get('dynamic_fields') or []
            if dynamic_fields:
                for field in dynamic_fields:
                    components[field]['values'].add('dynamic')
        
        # Calculate variance
        for comp_name, comp_data in components.items():
            total_samples = min(len(op_calls), 50)
            unique_values = len(comp_data['values'])
            comp_data['variance'] = unique_values / total_samples if total_samples > 0 else 0
        
        # Determine recommendations
        include_in_key = []
        exclude_from_key = []
        
        for comp_name, comp_data in components.items():
            if comp_data['variance'] == 0:
                exclude_from_key.append((comp_name, "0% variance - same every call"))
            elif comp_data['variance'] < 0.3:
                include_in_key.append((comp_name, f"{comp_data['variance']*100:.0f}% variance - good key candidate"))
            elif comp_data['variance'] > 0.8:
                exclude_from_key.append((comp_name, f"{comp_data['variance']*100:.0f}% variance - exclude"))
            else:
                include_in_key.append((comp_name, f"{comp_data['variance']*100:.0f}% variance - consider including"))
        
        # Calculate cacheability
        avg_cost = sum(c.get('total_cost', 0) for c in op_calls) / len(op_calls)
        
        # Determine recommended TTL
        if 'job' in operation.lower() or 'match' in operation.lower():
            recommended_ttl = "24h (job data updates daily)"
        elif 'chat' in operation.lower():
            recommended_ttl = "1h (conversation context)"
        elif 'extract' in operation.lower() or 'skill' in operation.lower():
            recommended_ttl = "7d (static content)"
        else:
            recommended_ttl = "1h (default)"
        
        strategies.append({
            'operation': operation,
            'call_count': len(op_calls),
            'avg_cost': avg_cost,
            'components': dict(components),
            'include_in_key': include_in_key,
            'exclude_from_key': exclude_from_key,
            'recommended_ttl': recommended_ttl,
            'sample_prompt': (op_calls[0].get('prompt') or '')[:500] if op_calls else '',
        })
    
    # Sort by call count
    strategies.sort(key=lambda x: -x['call_count'])
    
    return strategies


# =============================================================================
# OVERVIEW ANALYSIS
# =============================================================================

def calculate_overview_stats(calls: List[Dict], duplicates: List[Dict]) -> Dict[str, Any]:
    """Calculate overview statistics for the Overview tab."""
    
    total_calls = len(calls)
    total_cost = sum(c.get('total_cost', 0) for c in calls)
    
    # Duplicate stats
    total_duplicates = sum(d['count'] for d in duplicates)
    total_wasted = sum(d['wasted_cost'] for d in duplicates)
    
    # By operation breakdown
    by_operation = defaultdict(lambda: {
        'calls': 0,
        'duplicates': 0,
        'cost': 0,
        'wasted': 0,
    })
    
    for call in calls:
        op = call.get('operation') or 'unknown'
        by_operation[op]['calls'] += 1
        by_operation[op]['cost'] += call.get('total_cost', 0)
    
    for dup in duplicates:
        for op in dup['operations']:
            by_operation[op]['duplicates'] += dup['count']
            by_operation[op]['wasted'] += dup['wasted_cost'] / len(dup['operations'])
    
    # Calculate cacheability per operation
    operations = []
    for op, stats in by_operation.items():
        repeat_pct = stats['duplicates'] / stats['calls'] if stats['calls'] > 0 else 0
        
        if repeat_pct > 0.5:
            cacheability = '🟢 High'
        elif repeat_pct > 0.2:
            cacheability = '🟡 Partial'
        else:
            cacheability = '🔴 Low'
        
        operations.append({
            'operation': op,
            'calls': stats['calls'],
            'duplicates': stats['duplicates'],
            'repeat_pct': repeat_pct,
            'cost': stats['cost'],
            'wasted': stats['wasted'],
            'cacheability': cacheability,
        })
    
    operations.sort(key=lambda x: -x['wasted'])
    
    return {
        'total_calls': total_calls,
        'total_cost': total_cost,
        'total_duplicates': total_duplicates,
        'total_wasted': total_wasted,
        'monthly_savings': total_wasted * 30,  # Project to monthly
        'cacheable_pct': total_duplicates / total_calls if total_calls > 0 else 0,
        'operations': operations,
    }


# =============================================================================
# RENDERING FUNCTIONS
# =============================================================================

def render_cache_status_banner(has_cache: bool, mode: str, stats: Dict):
    """Render the cache status banner at top of page."""
    
    if has_cache and stats.get('cache_hits', 0) > 0:
        hit_rate = stats['cache_hits'] / stats['calls_with_cache'] if stats['calls_with_cache'] > 0 else 0
        st.success(f"🟢 **{mode}** — {stats['cache_hits']} hits, {stats['cache_misses']} misses")
    elif has_cache:
        st.warning(f"🟡 **{mode}** — Cache enabled but no hits yet")
    else:
        st.info(f"📊 **{mode}** — Analyzing prompt patterns to identify caching opportunities")


def render_overview_tab(calls: List[Dict], duplicates: List[Dict], has_cache: bool, stats: Dict):
    """Render the Overview tab."""
    
    overview = calculate_overview_stats(calls, duplicates)
    
    st.subheader("📊 Caching Opportunity Summary")
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Calls", f"{overview['total_calls']:,}")
    
    with col2:
        label = "Cacheable" if not has_cache else "Duplicates Found"
        st.metric(label, f"{overview['total_duplicates']:,}",
                  help=f"{format_percentage(overview['cacheable_pct'])} of calls")
    
    with col3:
        label = "Potential Savings" if not has_cache else "Wasted Cost"
        st.metric(label, format_cost(overview['total_wasted']))
    
    with col4:
        st.metric("Monthly Opportunity", format_cost(overview['monthly_savings']),
                  help="Projected monthly savings with caching")
    
    st.divider()
    
    # Quick Win callout
    if overview['operations']:
        top_op = overview['operations'][0]
        if top_op['wasted'] > 0:
            st.info(f"💡 **Quick Win:** Cache `{top_op['operation']}` — {format_percentage(top_op['repeat_pct'])} of calls are duplicates ({format_cost(top_op['wasted'])}/period)")
    
    st.divider()
    
    # Operations table
    st.subheader("🎯 Caching Opportunities by Operation")
    
    if overview['operations']:
        op_data = []
        for op in overview['operations']:
            op_data.append({
                'Operation': op['operation'],
                'Calls': op['calls'],
                'Duplicates': op['duplicates'],
                'Repeat %': format_percentage(op['repeat_pct']),
                'Savings': format_cost(op['wasted']),
                'Cacheable?': op['cacheability'],
            })
        
        st.dataframe(pd.DataFrame(op_data), use_container_width=True, hide_index=True)
    else:
        st.info("No operations found")


def render_repeated_tab(duplicates: List[Dict]):
    """Render the Repeated Calls tab."""
    
    if not duplicates:
        st.success("✅ No duplicate calls detected!")
        st.caption("Your prompts appear to be unique")
        return
    
    st.subheader(f"🔁 {len(duplicates)} Duplicate Patterns Found")
    st.caption("These calls are being made multiple times with same/similar input")
    
    # Summary
    total_wasted = sum(d['wasted_cost'] for d in duplicates)
    total_dups = sum(d['count'] for d in duplicates)
    
    st.warning(f"**{total_dups} duplicate calls** wasting **{format_cost(total_wasted)}** per period")
    
    st.divider()
    
    # Show each duplicate pattern
    for i, dup in enumerate(duplicates[:10], 1):
        with st.container():
            st.markdown(f"### #{i} — {dup['count']} duplicates — `{dup['operations'][0]}` — {format_cost(dup['wasted_cost'])} wasted")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Duplicate Pattern**")
                st.write(f"- First seen: {dup['first_seen'].strftime('%Y-%m-%d %H:%M') if dup['first_seen'] else 'N/A'}")
                st.write(f"- Last seen: {dup['last_seen'].strftime('%Y-%m-%d %H:%M') if dup['last_seen'] else 'N/A'}")
                st.write(f"- Frequency: ~{dup['frequency']:.1f}/hour")
                st.write(f"- Avg cost: {format_cost(dup['avg_cost'])}/call")
                st.write(f"- Avg latency: {format_latency(dup['avg_latency'])}")
            
            with col2:
                st.markdown("**Why It's Repeating**")
                if len(dup['agents']) > 1:
                    st.error(f"🔴 Multiple agents calling: {', '.join(dup['agents'][:3])}")
                elif dup['frequency'] > 10:
                    st.error("🔴 High frequency — same query repeated rapidly")
                else:
                    st.warning("🟡 Same query pattern detected")
                
                if dup['dynamic_fields']:
                    st.caption(f"Dynamic fields detected: {', '.join(dup['dynamic_fields'])}")
            
            # Show prompt
            with st.expander("📝 View Repeated Prompt"):
                st.code(truncate_text(dup['representative'], 500), language="text")
            
            # Fix suggestion
            st.markdown("**🛠️ Fix: Add Caching**")
            
            cache_key_suggestion = f"{dup['operations'][0]}:" + ":".join(
                f"[{f}]" for f in dup['dynamic_fields']
            ) if dup['dynamic_fields'] else f"hash({dup['operations'][0]}_prompt)"
            
            st.success(f"""
**Impact:** {dup['count']} calls → 1 call + {dup['count']-1} cache hits  
**Save:** {format_cost(dup['wasted_cost'])}/period ({format_cost(dup['wasted_cost'] * 30)}/month)  
**Latency:** {format_latency(dup['avg_latency'])} → <100ms for cached  

**Suggested Cache Key:** `{cache_key_suggestion}`
            """)
            
            st.divider()
    
    if len(duplicates) > 10:
        st.caption(f"Showing top 10 of {len(duplicates)} duplicate patterns")


def render_high_value_tab(high_value: List[Dict]):
    """Render the High-Value Targets tab."""
    
    if not high_value:
        st.success("✅ No high-value caching targets found")
        st.caption(f"No operations with avg cost > {format_cost(HIGH_VALUE_COST_THRESHOLD)} or latency > {format_latency(HIGH_VALUE_LATENCY_THRESHOLD)}")
        return
    
    st.subheader(f"💰 {len(high_value)} High-Value Targets")
    st.caption("Even with low duplication, these calls are expensive enough to cache")
    
    for i, hv in enumerate(high_value[:8], 1):
        with st.container():
            # Header
            tags = []
            if hv['is_expensive']:
                tags.append(f"{format_cost(hv['avg_cost'])}/call")
            if hv['is_slow']:
                tags.append(f"{format_latency(hv['avg_latency'])} avg")
            
            st.markdown(f"### #{i} — `{hv['operation']}` — {' • '.join(tags)}")
            st.caption(f"Models: {', '.join(format_model_name(m) for m in hv['models_used'][:3])}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Call Profile**")
                st.write(f"- Avg cost: {format_cost(hv['avg_cost'])}/call")
                st.write(f"- Avg latency: {format_latency(hv['avg_latency'])}")
                st.write(f"- Calls/period: {hv['call_count']}")
                st.write(f"- Total cost: {format_cost(hv['total_cost'])}/period")
                st.write(f"- Exact duplicates: {format_percentage(hv['exact_duplicate_pct'])}")
            
            with col2:
                st.markdown("**Cache Opportunity**")
                
                if hv['exact_duplicate_pct'] > 0.3:
                    st.success(f"🟢 **HIGH** — {format_percentage(hv['exact_duplicate_pct'])} exact duplicates")
                elif hv['semantic_similar_pct'] > 0.5:
                    st.warning(f"🟡 **MODERATE** — {format_percentage(hv['semantic_similar_pct'])} semantically similar")
                    st.caption("Consider semantic caching with embeddings")
                else:
                    st.info(f"🔵 **LATENCY** — High cost justifies caching even at low hit rate")
                
                st.write(f"**Potential Savings:** {format_cost(hv['potential_savings'])}/period")
            
            # Semantic analysis
            if hv['semantic_similar_pct'] > 0.3:
                with st.expander("🔬 Semantic Similarity Analysis"):
                    st.write(f"While only {format_percentage(hv['exact_duplicate_pct'])} are exact duplicates, {format_percentage(hv['semantic_similar_pct'])} are semantically similar.")
                    st.write("This suggests semantic caching with embeddings could be effective.")
                    
                    st.code("""
# Semantic caching example
async def cached_operation(prompt: str):
    embedding = await embed(prompt)
    
    # Search for similar cached queries (threshold: 0.95)
    similar = await vector_cache.search(embedding, threshold=0.95)
    if similar:
        return similar.result
    
    result = await llm.call(prompt)
    await vector_cache.store(embedding, result, ttl=3600)
    return result
                    """, language="python")
            
            st.divider()


def render_cache_keys_tab(strategies: List[Dict]):
    """Render the Cache Keys tab."""
    
    if not strategies:
        st.info("Not enough data to analyze cache key strategies")
        return
    
    st.subheader("🔑 Cache Key Strategies")
    st.caption("How to design cache keys for each operation")
    
    for strategy in strategies[:8]:
        with st.container():
            st.markdown(f"### `{strategy['operation']}` — {strategy['call_count']} calls")
            st.caption(f"Avg cost: {format_cost(strategy['avg_cost'])}/call")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Prompt Structure Analysis**")
                
                # Show what to include/exclude
                if strategy['include_in_key']:
                    st.write("**✅ Include in cache key:**")
                    for comp, reason in strategy['include_in_key'][:5]:
                        st.write(f"- `{comp}`: {reason}")
                
                if strategy['exclude_from_key']:
                    st.write("**❌ Exclude from cache key:**")
                    for comp, reason in strategy['exclude_from_key'][:5]:
                        st.write(f"- `{comp}`: {reason}")
            
            with col2:
                st.markdown("**Recommended Cache Key**")
                
                # Generate cache key pattern
                key_parts = [strategy['operation']]
                for comp, _ in strategy['include_in_key'][:3]:
                    key_parts.append(f"{{{comp}}}")
                
                key_pattern = ":".join(key_parts)
                
                st.code(f"Pattern: {key_pattern}", language="text")
                st.write(f"**TTL:** {strategy['recommended_ttl']}")
                
                # Invalidation triggers
                st.markdown("**Invalidation Triggers:**")
                if 'entity_ids' in [c[0] for c in strategy['include_in_key']]:
                    st.write("• Entity updated → invalidate keys with that ID")
                st.write("• User changes preferences → invalidate user's cached results")
            
            # Sample prompt
            with st.expander("📝 Sample Prompt"):
                st.code(truncate_text(strategy['sample_prompt'], 400), language="text")
            
            st.divider()


# =============================================================================
# MAIN RENDER
# =============================================================================

def render():
    """Main render function for Cache Analyzer page."""
    
    st.title("💾 Cache Analyzer")
    st.caption("Find repeated calls and how to cache them")
    
    # Get selected project
    selected_project = st.session_state.get('selected_project')
    
    # Controls
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        if selected_project:
            st.info(f"Analyzing: **{selected_project}**")
        else:
            st.info("Analyzing: **All Projects**")
    
    with col2:
        limit = st.selectbox(
            "Analyze",
            options=[100, 250, 500, 1000],
            index=1,
            format_func=lambda x: f"Last {x} calls",
            key="cache_limit"
        )
    
    with col3:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    st.divider()
    
    # Fetch data
    try:
        with st.spinner("Loading and analyzing calls..."):
            calls = get_llm_calls(
                project_name=selected_project,
                limit=limit
            )
            
            if not calls:
                render_empty_state(
                    message="No data available for cache analysis",
                    icon="💾",
                    suggestion="Run your AI agents with Observatory enabled to analyze caching opportunities"
                )
                return
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    # Detect cache mode
    has_cache, mode, cache_stats = detect_cache_mode(calls)
    
    # Show status banner
    render_cache_status_banner(has_cache, mode, cache_stats)
    
    st.divider()
    
    # Analyze
    with st.spinner("Analyzing prompt patterns..."):
        duplicates = find_duplicates(calls)
        high_value = find_high_value_calls(calls)
        strategies = analyze_cache_keys(calls)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview",
        f"🔁 Repeated ({len(duplicates)})",
        f"💰 High-Value ({len(high_value)})",
        "🔑 Cache Keys"
    ])
    
    with tab1:
        render_overview_tab(calls, duplicates, has_cache, cache_stats)
    
    with tab2:
        render_repeated_tab(duplicates)
    
    with tab3:
        render_high_value_tab(high_value)
    
    with tab4:
        render_cache_keys_tab(strategies)