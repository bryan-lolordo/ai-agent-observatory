"""
Cache Analyzer Page - Semantic Caching Analysis
Location: dashboard/pages/cache_analyzer.py

Advanced cache performance analysis with prompt clustering, semantic similarity,
cacheability scoring, and optimization recommendations.
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
    get_time_series_data,
)
from dashboard.utils.formatters import (
    format_cost,
    format_latency,
    format_tokens,
    format_percentage,
    truncate_text,
)
from dashboard.components.metric_cards import (
    render_metric_row,
    render_empty_state,
)
from dashboard.components.charts import (
    create_time_series_chart,
    create_bar_chart,
    create_heatmap,
)
from dashboard.components.tables import (
    render_dataframe,
)


def detect_cache_mode(calls: List[Dict]) -> Tuple[bool, str]:
    """
    Detect if real caching is active or not implemented.
    
    Returns:
        Tuple of (has_real_cache, mode_description)
    """
    if not calls:
        return False, "No data"
    
    # Check for cache hits in metadata
    cache_hits = sum(
        1 for c in calls
        if c.get('cache_metadata', {}).get('cache_hit', False)
    )
    
    cache_keys = sum(
        1 for c in calls
        if c.get('cache_metadata', {}).get('cache_key') is not None
    )
    
    if cache_hits > 0:
        return True, f"Cache active - {cache_hits} hits detected"
    elif cache_keys > 0:
        return True, "Cache enabled - waiting for hits"
    else:
        return False, "Cache not implemented"


def normalize_prompt(prompt: str) -> str:
    """
    Normalize prompt for clustering by removing dynamic content.
    """
    if not prompt:
        return ""
    
    # Remove timestamps
    normalized = re.sub(r'\d{4}-\d{2}-\d{2}', '[DATE]', prompt)
    normalized = re.sub(r'\d{2}:\d{2}:\d{2}', '[TIME]', normalized)
    
    # Remove numbers
    normalized = re.sub(r'\b\d+\b', '[NUM]', normalized)
    
    # Remove extra whitespace
    normalized = ' '.join(normalized.split())
    
    # Lowercase
    normalized = normalized.lower()
    
    return normalized


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate simple similarity score between two texts.
    Uses Jaccard similarity of word sets.
    """
    if not text1 or not text2:
        return 0.0
    
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    if not union:
        return 0.0
    
    return len(intersection) / len(union)


def cluster_prompts(calls: List[Dict], similarity_threshold: float = 0.7) -> List[Dict]:
    """
    Cluster similar prompts together.
    
    Returns list of clusters with metadata.
    """
    if not calls:
        return []
    
    # Extract prompts
    prompts_data = []
    for call in calls:
        prompt = call.get('prompt', '')
        if prompt:
            prompts_data.append({
                'original': prompt,
                'normalized': normalize_prompt(prompt),
                'call': call
            })
    
    if not prompts_data:
        return []
    
    # Cluster by similarity
    clusters = []
    used_indices = set()
    
    for i, prompt_data in enumerate(prompts_data):
        if i in used_indices:
            continue
        
        # Start new cluster
        cluster = {
            'representative': prompt_data['original'],
            'normalized': prompt_data['normalized'],
            'variants': [prompt_data['original']],
            'calls': [prompt_data['call']],
            'agents': set([prompt_data['call'].get('agent_name', 'Unknown')]),
        }
        used_indices.add(i)
        
        # Find similar prompts
        for j, other_data in enumerate(prompts_data):
            if j in used_indices:
                continue
            
            similarity = calculate_similarity(
                prompt_data['normalized'],
                other_data['normalized']
            )
            
            if similarity >= similarity_threshold:
                cluster['variants'].append(other_data['original'])
                cluster['calls'].append(other_data['call'])
                cluster['agents'].add(other_data['call'].get('agent_name', 'Unknown'))
                used_indices.add(j)
        
        clusters.append(cluster)
    
    # Calculate cluster stats
    for cluster in clusters:
        # Cache stats
        cache_hits = sum(
            1 for c in cluster['calls']
            if c.get('cache_metadata', {}).get('cache_hit', False)
        )
        cache_misses = len(cluster['calls']) - cache_hits
        
        # Cost and token savings
        total_tokens = sum(c.get('total_tokens', 0) for c in cluster['calls'])
        total_cost = sum(c.get('total_cost', 0) for c in cluster['calls'])
        
        # If we had cached all hits, tokens/cost saved
        tokens_saved = cache_hits * (total_tokens / len(cluster['calls'])) if cluster['calls'] else 0
        cost_saved = cache_hits * (total_cost / len(cluster['calls'])) if cluster['calls'] else 0
        
        # Generate cluster name (first few words)
        words = cluster['normalized'].split()[:5]
        cluster_name = ' '.join(words) + ('...' if len(words) == 5 else '')
        
        # Generate cache key
        cache_key = hashlib.md5(cluster['normalized'].encode()).hexdigest()[:8]
        
        cluster.update({
            'name': cluster_name,
            'variant_count': len(cluster['variants']),
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'tokens_saved': tokens_saved,
            'cost_saved': cost_saved,
            'cache_key': cache_key,
            'agent_list': list(cluster['agents'])
        })
    
    # Sort by frequency (most common first)
    clusters.sort(key=lambda x: len(x['calls']), reverse=True)
    
    return clusters


def calculate_cacheability_score(cluster: Dict) -> Tuple[float, List[str]]:
    """
    Calculate how cacheable a prompt cluster is (0-100).
    Returns score and list of reasons for score.
    """
    score = 100
    reasons = []
    
    # Check variant consistency
    if cluster['variant_count'] > 10:
        score -= 20
        reasons.append("Too many variants - inconsistent formatting")
    
    # Check for dynamic content
    representative = cluster['representative']
    
    if re.search(r'\d{4}-\d{2}-\d{2}', representative):
        score -= 15
        reasons.append("Contains timestamps")
    
    if re.search(r'\btoday\b|\bnow\b|\bcurrent\b', representative.lower()):
        score -= 10
        reasons.append("Contains temporal references")
    
    # Check length
    words = len(representative.split())
    if words > 500:
        score -= 10
        reasons.append("Very long prompt - harder to cache")
    
    # Check if prompts are similar enough
    if cluster['variant_count'] > 5:
        # Multiple variants suggest inconsistency
        score -= 15
        reasons.append("Multiple formatting variations detected")
    
    # Positive factors
    if cluster['cache_hits'] > 0:
        score += 10
        reasons.append(f"Already achieving {cluster['cache_hits']} cache hits")
    
    if cluster['variant_count'] == 1:
        reasons.append("Perfectly consistent - ideal for caching")
    
    if words < 100:
        reasons.append("Short prompt - efficient to cache")
    
    # Ensure score is in valid range
    score = max(0, min(100, score))
    
    if not reasons:
        reasons.append("Standard cacheability")
    
    return score, reasons


def estimate_cache_potential(calls: List[Dict], clusters: List[Dict]) -> Dict[str, Any]:
    """
    Estimate potential cache savings if not implemented.
    """
    if not calls:
        return {
            'enabled': False,
            'potential_hit_rate': 0,
            'potential_tokens_saved': 0,
            'potential_cost_saved': 0
        }
    
    # Analyze prompt repetition
    total_calls = len(calls)
    
    # Count prompts that appear multiple times (cacheable)
    prompt_counts = defaultdict(int)
    for call in calls:
        normalized = normalize_prompt(call.get('prompt', ''))
        if normalized:
            prompt_counts[normalized] += 1
    
    # Prompts appearing 2+ times could be cached
    cacheable_calls = sum(count for count in prompt_counts.values() if count > 1)
    potential_hits = cacheable_calls - len([c for c in prompt_counts.values() if c > 1])
    
    potential_hit_rate = potential_hits / total_calls if total_calls > 0 else 0
    
    # Calculate savings
    total_tokens = sum(c.get('total_tokens', 0) for c in calls)
    total_cost = sum(c.get('total_cost', 0) for c in calls)
    
    avg_tokens = total_tokens / total_calls
    avg_cost = total_cost / total_calls
    
    potential_tokens_saved = potential_hits * avg_tokens
    potential_cost_saved = potential_hits * avg_cost
    
    return {
        'enabled': False,
        'potential_hit_rate': potential_hit_rate,
        'potential_tokens_saved': int(potential_tokens_saved),
        'potential_cost_saved': potential_cost_saved,
        'cacheable_calls': cacheable_calls,
        'unique_prompts': len(prompt_counts)
    }


def generate_cache_recommendations(clusters: List[Dict], has_cache: bool, calls: List[Dict]) -> List[Dict]:
    """
    Generate AI-style recommendations for cache optimization.
    """
    recommendations = []
    
    if not has_cache:
        # Recommendations for implementing cache
        
        # Find highly repetitive clusters
        repetitive = [c for c in clusters if len(c['calls']) >= 5]
        if repetitive:
            top_cluster = repetitive[0]
            savings = sum(c['cost_saved'] for c in repetitive[:3])
            recommendations.append({
                'priority': 1,
                'title': 'Implement Semantic Caching for Top Clusters',
                'description': f"Top 3 repetitive prompts could save {format_cost(savings * 30)}/month",
                'impact': 'High',
                'action': 'Enable caching with TTL=60s'
            })
        
        # Check for dynamic content
        dynamic_clusters = []
        for cluster in clusters:
            if cluster['variant_count'] > 5:
                dynamic_clusters.append(cluster)
        
        if dynamic_clusters:
            recommendations.append({
                'priority': 2,
                'title': 'Normalize Prompts Before Caching',
                'description': f"{len(dynamic_clusters)} prompt clusters have inconsistent formatting",
                'impact': 'Medium',
                'action': 'Strip timestamps, numbers, and whitespace'
            })
        
        # Estimate overall opportunity
        total_cost = sum(c.get('total_cost', 0) for c in calls)
        est_savings = total_cost * 0.30  # 30% hit rate assumption
        recommendations.append({
            'priority': 3,
            'title': 'Overall Cache Opportunity',
            'description': f"Estimated {format_cost(est_savings * 30)}/month savings with 30% hit rate",
            'impact': 'High',
            'action': 'Implement cache infrastructure'
        })
    
    else:
        # Recommendations for improving existing cache
        
        # Find low-performing clusters
        low_hit_rate = [c for c in clusters if len(c['calls']) >= 3 and c['cache_hits'] < len(c['calls']) * 0.2]
        if low_hit_rate:
            recommendations.append({
                'priority': 1,
                'title': 'Improve Hit Rate for Underperforming Clusters',
                'description': f"{len(low_hit_rate)} clusters have <20% hit rate despite repetition",
                'impact': 'Medium',
                'action': 'Review normalization strategy'
            })
        
        # Check for merge opportunities
        similar_clusters = []
        for i, c1 in enumerate(clusters):
            for c2 in clusters[i+1:]:
                if calculate_similarity(c1['normalized'], c2['normalized']) > 0.85:
                    similar_clusters.append((c1, c2))
        
        if similar_clusters:
            recommendations.append({
                'priority': 2,
                'title': 'Merge Similar Prompt Templates',
                'description': f"{len(similar_clusters)} pairs of clusters are 85%+ similar",
                'impact': 'Low',
                'action': 'Consider template consolidation'
            })
        
        # Calculate actual savings and project increase
        total_hits = sum(c['cache_hits'] for c in clusters)
        total_savings = sum(c['cost_saved'] for c in clusters)
        
        # Project with higher TTL
        potential_increase = total_savings * 0.25  # 25% more with longer TTL
        recommendations.append({
            'priority': 3,
            'title': 'Optimize Cache TTL',
            'description': f"Increasing TTL to 60s could save additional {format_cost(potential_increase * 30)}/month",
            'impact': 'Medium',
            'action': 'Extend cache expiration time'
        })
    
    return recommendations


def render():
    """Render the Cache Analyzer page."""
    
    st.title("💾 Cache Analyzer - Semantic Caching")
    
    # Get selected project
    selected_project = st.session_state.get('selected_project')
    
    # Project indicator
    if selected_project:
        st.info(f"📊 Analyzing cache for: **{selected_project}**")
    else:
        st.info("📊 Analyzing cache for: **All Projects**")
    
    st.divider()
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        try:
            agents = get_available_agents(selected_project)
            filter_agent = st.selectbox(
                "Agent",
                options=["All"] + agents,
                key="cache_agent_filter"
            )
        except:
            filter_agent = "All"
    
    with col2:
        time_period = st.selectbox(
            "Time Period",
            options=["1h", "24h", "7d", "30d"],
            index=2,
            key="cache_time_period"
        )
    
    with col3:
        similarity_threshold = st.slider(
            "Similarity Threshold",
            min_value=0.5,
            max_value=0.95,
            value=0.7,
            step=0.05,
            help="How similar prompts must be to cluster together",
            key="cache_similarity"
        )
    
    with col4:
        limit = st.selectbox(
            "Max Results",
            options=[100, 200, 500, 1000],
            index=1,
            key="cache_limit"
        )
    
    st.divider()
    
    # Fetch data
    try:
        with st.spinner("Loading cache data and analyzing prompts..."):
            calls = get_llm_calls(
                project_name=selected_project,
                agent_name=None if filter_agent == "All" else filter_agent,
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
        st.error(f"Error loading cache data: {str(e)}")
        return
    
    # Detect cache mode
    has_cache, cache_mode = detect_cache_mode(calls)
    
    # Show cache status
    if has_cache:
        st.success(f"✅ {cache_mode}")
    else:
        st.warning(f"⚠️ {cache_mode} - Showing opportunity analysis")
    
    st.divider()
    
    # Cluster prompts
    with st.spinner("Clustering prompts by similarity..."):
        clusters = cluster_prompts(calls, similarity_threshold)
    
    st.caption(f"Found {len(clusters)} prompt clusters from {len(calls)} calls")
    
    # Calculate cache metrics
    if has_cache:
        # Actual cache performance
        total_hits = sum(
            1 for c in calls
            if c.get('cache_metadata', {}).get('cache_hit', False)
        )
        total_misses = len(calls) - total_hits
        hit_rate = total_hits / len(calls) if calls else 0
        
        # Tokens and cost saved
        avg_tokens = sum(c.get('total_tokens', 0) for c in calls) / len(calls)
        avg_cost = sum(c.get('total_cost', 0) for c in calls) / len(calls)
        
        tokens_saved = total_hits * avg_tokens
        cost_saved = total_hits * avg_cost
        latency_saved = total_hits * 500  # Assume 500ms saved per cache hit
    else:
        # Potential cache performance
        potential = estimate_cache_potential(calls, clusters)
        hit_rate = potential['potential_hit_rate']
        tokens_saved = potential['potential_tokens_saved']
        cost_saved = potential['potential_cost_saved']
        total_hits = int(len(calls) * hit_rate)
        total_misses = len(calls) - total_hits
        latency_saved = total_hits * 500
    
    # Section 1: High-Level KPIs
    st.subheader("📊 Cache Performance Metrics")
    
    if has_cache:
        metrics = [
            {
                "label": "Cache Hit Rate",
                "value": format_percentage(hit_rate),
                "help_text": f"{total_hits} hits / {len(calls)} total"
            },
            {
                "label": "Tokens Saved",
                "value": format_tokens(int(tokens_saved)),
            },
            {
                "label": "Cost Saved",
                "value": format_cost(cost_saved),
                "help_text": f"{format_cost(cost_saved * 30)}/month projected"
            },
            {
                "label": "Latency Saved",
                "value": format_latency(latency_saved),
                "help_text": "Estimated time savings"
            }
        ]
    else:
        metrics = [
            {
                "label": "Potential Hit Rate",
                "value": format_percentage(hit_rate),
                "help_text": "Based on prompt repetition analysis"
            },
            {
                "label": "Tokens Saveable",
                "value": format_tokens(tokens_saved),
                "help_text": "If caching enabled"
            },
            {
                "label": "Cost Saveable",
                "value": format_cost(cost_saved),
                "delta": f"{format_cost(cost_saved * 30)}/month",
                "help_text": "Projected monthly savings"
            },
            {
                "label": "Latency Reduction",
                "value": format_latency(latency_saved),
                "help_text": "Estimated improvement"
            }
        ]
    
    render_metric_row(metrics, columns=4)
    
    st.divider()
    
    # Section 2: Timeline (if has cache)
    if has_cache:
        st.subheader("📈 Cache Performance Over Time")
        
        try:
            # Get time series data
            cache_timeline = []
            
            # Group calls by hour
            hourly_data = defaultdict(lambda: {'hits': 0, 'misses': 0})
            
            for call in calls:
                timestamp = call.get('timestamp')
                if timestamp:
                    hour = timestamp.replace(minute=0, second=0, microsecond=0)
                    is_hit = call.get('cache_metadata', {}).get('cache_hit', False)
                    
                    if is_hit:
                        hourly_data[hour]['hits'] += 1
                    else:
                        hourly_data[hour]['misses'] += 1
            
            # Create timeline
            sorted_hours = sorted(hourly_data.keys())
            
            if sorted_hours:
                timeline_data = {
                    'timestamps': sorted_hours,
                    'Hits': [hourly_data[h]['hits'] for h in sorted_hours],
                    'Misses': [hourly_data[h]['misses'] for h in sorted_hours]
                }
                
                # Create multi-line chart
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=timeline_data['timestamps'],
                    y=timeline_data['Hits'],
                    mode='lines+markers',
                    name='Cache Hits',
                    line=dict(color='green', width=2)
                ))
                fig.add_trace(go.Scatter(
                    x=timeline_data['timestamps'],
                    y=timeline_data['Misses'],
                    mode='lines+markers',
                    name='Cache Misses',
                    line=dict(color='red', width=2)
                ))
                
                fig.update_layout(
                    title="Cache Hits vs Misses Over Time",
                    xaxis_title="Time",
                    yaxis_title="Request Count",
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, width='stretch')
            else:
                st.info("Not enough temporal data for timeline")
        
        except Exception as e:
            st.warning(f"Could not generate timeline: {str(e)}")
        
        st.divider()
    
    # Section 3: Prompt Cluster Explorer
    st.subheader("🔍 Prompt Cluster Explorer")
    
    if not clusters:
        st.info("No prompt clusters found - prompts may be too unique")
    else:
        st.caption(f"Showing {len(clusters)} clusters sorted by frequency")
        
        # Create cluster table
        cluster_table = []
        for cluster in clusters[:50]:  # Top 50 clusters
            cluster_table.append({
                'Cluster Name': cluster['name'],
                'Agent': ', '.join(cluster['agent_list'][:2]),
                'Variants': cluster['variant_count'],
                'Calls': len(cluster['calls']),
                'Hits': cluster['cache_hits'] if has_cache else f"~{int(len(cluster['calls']) * 0.3)}",
                'Misses': cluster['cache_misses'] if has_cache else f"~{int(len(cluster['calls']) * 0.7)}",
                'Tokens Saved': format_tokens(int(cluster['tokens_saved'])),
                'Cost Saved': format_cost(cluster['cost_saved']),
                'Cache Key': cluster['cache_key']
            })
        
        cluster_df = pd.DataFrame(cluster_table)
        
        # Display table
        st.dataframe(cluster_df, width='stretch', hide_index=True)
        
        st.divider()
        
        # Section 4: Per-Prompt Drilldown
        st.subheader("🔬 Prompt Cluster Details")
        
        selected_cluster_idx = st.selectbox(
            "Select cluster to analyze",
            options=range(len(clusters[:20])),
            format_func=lambda i: f"{i+1}. {clusters[i]['name']} ({len(clusters[i]['calls'])} calls)",
            key="selected_cluster"
        )
        
        selected_cluster = clusters[selected_cluster_idx]
        
        # Calculate cacheability
        cacheability_score, reasons = calculate_cacheability_score(selected_cluster)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write("**Cluster Overview**")
            
            st.write(f"**Cluster Name:** {selected_cluster['name']}")
            st.write(f"**Total Calls:** {len(selected_cluster['calls'])}")
            st.write(f"**Unique Variants:** {selected_cluster['variant_count']}")
            st.write(f"**Agents Using:** {', '.join(selected_cluster['agent_list'])}")
            
            if has_cache:
                st.write(f"**Cache Hits:** {selected_cluster['cache_hits']}")
                st.write(f"**Cache Misses:** {selected_cluster['cache_misses']}")
                hit_rate_cluster = selected_cluster['cache_hits'] / len(selected_cluster['calls']) if selected_cluster['calls'] else 0
                st.write(f"**Hit Rate:** {format_percentage(hit_rate_cluster)}")
            
            st.write("**Representative Prompt:**")
            st.code(selected_cluster['representative'][:300] + ('...' if len(selected_cluster['representative']) > 300 else ''), language="text")
            
            if selected_cluster['variant_count'] > 1:
                with st.expander(f"View all {selected_cluster['variant_count']} variants"):
                    for i, variant in enumerate(selected_cluster['variants'][:10], 1):
                        st.write(f"**Variant {i}:**")
                        st.code(variant[:200] + ('...' if len(variant) > 200 else ''), language="text")
        
        with col2:
            st.metric("Cacheability Score", f"{cacheability_score}/100")
            
            st.write("**Score Factors:**")
            for reason in reasons:
                st.caption(f"• {reason}")
            
            st.write("**Savings Potential:**")
            
            if has_cache:
                actual_saved = selected_cluster['cost_saved']
                potential_max = len(selected_cluster['calls']) * (sum(c.get('total_cost', 0) for c in selected_cluster['calls']) / len(selected_cluster['calls']))
                missed_opportunity = potential_max - actual_saved
                
                st.write(f"**Actual Savings:** {format_cost(actual_saved)}")
                st.write(f"**Potential Max:** {format_cost(potential_max)}")
                st.write(f"**Missed:** {format_cost(missed_opportunity)}")
            else:
                potential = len(selected_cluster['calls']) * 0.4 * (sum(c.get('total_cost', 0) for c in selected_cluster['calls']) / len(selected_cluster['calls']))
                st.write(f"**Potential Savings:** {format_cost(potential)}/day")
                st.write(f"**Monthly:** {format_cost(potential * 30)}")
        
        st.divider()
    
    # Section 5: Cache Capacity (if has cache)
    if has_cache:
        st.subheader("📦 Cache Capacity & Evictions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Estimate current cache size
            cached_clusters = [c for c in clusters if c['cache_hits'] > 0]
            st.metric("Clusters in Cache", len(cached_clusters))
        
        with col2:
            # Total cached tokens
            total_cached_tokens = sum(c['tokens_saved'] for c in cached_clusters)
            st.metric("Cached Content", format_tokens(int(total_cached_tokens)))
        
        with col3:
            # Eviction estimate (simplified)
            potential_evictions = max(0, len(clusters) - len(cached_clusters))
            st.metric("Potential Evictions", potential_evictions)
        
        st.caption("Eviction analytics require cache event logging (coming soon)")
        
        st.divider()
    
    # Section 6: AI-Generated Recommendations
    st.subheader("💡 Optimization Recommendations")
    
    recommendations = generate_cache_recommendations(clusters, has_cache, calls)
    
    if recommendations:
        for rec in recommendations:
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**{rec['priority']}. {rec['title']}** ({rec['impact']} Impact)")
                    st.caption(rec['description'])
                    st.info(f"**Action:** {rec['action']}")
                
                with col2:
                    if rec['impact'] == 'High':
                        st.markdown("🔴 **High Priority**")
                    elif rec['impact'] == 'Medium':
                        st.markdown("🟡 **Medium Priority**")
                    else:
                        st.markdown("🟢 **Low Priority**")
                
                st.divider()
    else:
        st.success("✅ Cache is well optimized! No major recommendations.")
    
    # Additional insights
    with st.expander("📊 Additional Cache Statistics"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Top Agents by Cache Potential:**")
            agent_stats = defaultdict(lambda: {'calls': 0, 'hits': 0, 'cost': 0})
            
            for call in calls:
                agent = call.get('agent_name', 'Unknown')
                agent_stats[agent]['calls'] += 1
                if call.get('cache_metadata', {}).get('cache_hit'):
                    agent_stats[agent]['hits'] += 1
                agent_stats[agent]['cost'] += call.get('total_cost', 0)
            
            agent_list = []
            for agent, stats in agent_stats.items():
                hit_rate = stats['hits'] / stats['calls'] if stats['calls'] > 0 else 0
                agent_list.append({
                    'Agent': agent,
                    'Calls': stats['calls'],
                    'Hit Rate': format_percentage(hit_rate),
                    'Potential Savings': format_cost(stats['cost'] * 0.3)
                })
            
            agent_df = pd.DataFrame(agent_list)
            st.dataframe(agent_df, width='stretch', hide_index=True)
        
        with col2:
            st.write("**Cache Key Distribution:**")
            st.caption(f"Total unique cache keys: {len(clusters)}")
            st.caption(f"Average calls per key: {len(calls) / len(clusters):.1f}")
            st.caption(f"Most frequent cluster: {clusters[0]['name'] if clusters else 'N/A'} ({len(clusters[0]['calls'])} calls)" if clusters else "")


# Import plotly for timeline
import plotly.graph_objects as go