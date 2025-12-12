"""
Story Analyzer - Data-Driven Story Detection
Location: dashboard/utils/story_analyzer.py

Analyzes LLM call data to generate optimization stories.
Each story identifies a specific problem, quantifies the impact,
and provides data for drill-down views.

Stories:
1. Latency Monster - Operations with excessive latency
2. Zero Cache Hits - Caching opportunities (duplicate prompts)
3. Cost Concentration - Where money is going
4. System Prompt Waste - Redundant system prompt tokens
5. Token Imbalance - Poor prompt:completion ratios
6. Model Routing - Complexity mismatches
7. Quality Issues - Errors and hallucinations
"""

from typing import Dict, Any, List, Optional
from collections import defaultdict
import hashlib
import json

# Import existing formatters - DO NOT DUPLICATE
from dashboard.utils.formatters import (
    format_cost,
    format_latency,
    format_tokens,
    format_percentage,
)


# =============================================================================
# CONSTANTS & THRESHOLDS
# =============================================================================

# Story 1: Latency
LATENCY_WARNING_MS = 5000       # 5 seconds
LATENCY_CRITICAL_MS = 10000     # 10 seconds

# Story 2: Cache
DUPLICATE_THRESHOLD = 2          # Minimum occurrences to count as duplicate
CACHE_OPPORTUNITY_PCT = 0.20     # 20% duplicates = opportunity

# Story 3: Cost
COST_CONCENTRATION_THRESHOLD = 0.70  # Top 3 ops > 70% = concentration issue

# Story 4: System Prompt
SYSTEM_PROMPT_WASTE_PCT = 0.30   # >30% of tokens in system prompt = waste
SYSTEM_PROMPT_HIGH_TOKENS = 1000 # >1000 tokens in system prompt = flagged

# Story 5: Token Imbalance
TOKEN_RATIO_WARNING = 10         # >10:1 prompt:completion ratio
TOKEN_RATIO_CRITICAL = 20        # >20:1 ratio

# Story 6: Routing
HIGH_COMPLEXITY_THRESHOLD = 0.7  # Complexity score >= 0.7
CHEAP_MODELS = ['gpt-4o-mini', 'gpt-3.5-turbo', 'claude-3-haiku', 'claude-3-5-haiku']

# Story 7: Quality
ERROR_RATE_WARNING = 0.02        # 2% error rate
ERROR_RATE_CRITICAL = 0.05       # 5% error rate


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def parse_json_field(field: Any) -> Dict:
    """Parse a field that might be JSON string or dict."""
    if field is None:
        return {}
    if isinstance(field, dict):
        return field
    if isinstance(field, str):
        try:
            return json.loads(field)
        except:
            return {}
    return {}


def normalize_prompt(prompt: str) -> str:
    """Normalize prompt for duplicate detection."""
    if not prompt:
        return ""
    return ' '.join(prompt.lower().split())


def get_prompt_hash(prompt: str) -> str:
    """Generate hash for prompt grouping."""
    normalized = normalize_prompt(prompt)
    return hashlib.md5(normalized.encode()).hexdigest()[:12]


# =============================================================================
# STORY 1: LATENCY MONSTER
# =============================================================================

def analyze_latency_story(calls: List[Dict]) -> Dict[str, Any]:
    """
    Analyze calls for latency issues.
    
    Identifies operations with excessive latency and provides
    breakdown of what's causing the slowness.
    """
    if not calls:
        return _empty_story_result("No latency data")
    
    # Group by agent.operation
    by_operation = defaultdict(list)
    for call in calls:
        agent = call.get('agent_name') or 'Unknown'
        operation = call.get('operation') or 'unknown'
        key = f"{agent}.{operation}"
        by_operation[key].append(call)
    
    # Analyze each operation
    operation_stats = []
    for op_key, op_calls in by_operation.items():
        latencies = [c.get('latency_ms') or 0 for c in op_calls]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        max_latency = max(latencies) if latencies else 0
        
        # Get token info for context
        avg_completion = sum(c.get('completion_tokens') or 0 for c in op_calls) / len(op_calls)
        avg_prompt = sum(c.get('prompt_tokens') or 0 for c in op_calls) / len(op_calls)
        total_cost = sum(c.get('total_cost') or 0 for c in op_calls)
        
        # Determine if this is a problem
        is_slow = avg_latency > LATENCY_WARNING_MS
        is_critical = avg_latency > LATENCY_CRITICAL_MS
        
        agent, operation = op_key.split('.', 1) if '.' in op_key else ('Unknown', op_key)
        
        operation_stats.append({
            'agent': agent,
            'operation': operation,
            'agent_operation': op_key,
            'call_count': len(op_calls),
            'avg_latency_ms': avg_latency,
            'max_latency_ms': max_latency,
            'avg_completion_tokens': int(avg_completion),
            'avg_prompt_tokens': int(avg_prompt),
            'total_cost': total_cost,
            'is_slow': is_slow,
            'is_critical': is_critical,
            'calls': op_calls,
        })
    
    # Sort by average latency (slowest first)
    operation_stats.sort(key=lambda x: -x['avg_latency_ms'])
    
    # Find slow operations
    slow_ops = [op for op in operation_stats if op['is_slow']]
    
    if not slow_ops:
        return {
            "has_issues": False,
            "summary_metric": "All fast",
            "red_flag_count": 0,
            "total_slow_calls": 0,
            "affected_operations": [],
            "top_offender": None,
            "detail_table": operation_stats[:10],
        }
    
    top_offender = slow_ops[0]
    total_slow_calls = sum(op['call_count'] for op in slow_ops)
    
    return {
        "has_issues": True,
        "summary_metric": f"{top_offender['avg_latency_ms']/1000:.1f}s avg",
        "red_flag_count": len(slow_ops),
        "total_slow_calls": total_slow_calls,
        "affected_operations": [
            {
                "agent_operation": op['agent_operation'],
                "avg_latency": format_latency(op['avg_latency_ms']),
                "max_latency": format_latency(op['max_latency_ms']),
                "calls": op['call_count'],
                "avg_completion_tokens": op['avg_completion_tokens'],
                "is_critical": op['is_critical'],
            }
            for op in slow_ops[:5]
        ],
        "top_offender": {
            "agent": top_offender['agent'],
            "operation": top_offender['operation'],
            "agent_operation": top_offender['agent_operation'],
            "avg_latency_ms": top_offender['avg_latency_ms'],
            "avg_completion_tokens": top_offender['avg_completion_tokens'],
            "call_count": top_offender['call_count'],
            "diagnosis": _diagnose_latency(top_offender),
        },
        "detail_table": operation_stats,
    }


def _diagnose_latency(op_stats: Dict) -> str:
    """Diagnose the cause of latency for an operation."""
    avg_completion = op_stats.get('avg_completion_tokens', 0)
    avg_prompt = op_stats.get('avg_prompt_tokens', 0)
    
    if avg_completion > 1500:
        return f"High completion tokens ({avg_completion:,}) - constrain output format"
    elif avg_prompt > 4000:
        return f"Large prompt ({avg_prompt:,} tokens) - reduce context or use caching"
    else:
        return "Consider faster model or optimize prompt"


# =============================================================================
# STORY 2: ZERO CACHE HITS (CACHING OPPORTUNITIES)
# =============================================================================

def analyze_cache_story(calls: List[Dict]) -> Dict[str, Any]:
    """
    Analyze calls for caching opportunities.
    
    Identifies duplicate prompts that could be cached.
    """
    if not calls:
        return _empty_story_result("No cache data")
    
    # Check current cache status
    cache_hits = 0
    cache_misses = 0
    for call in calls:
        cache_meta = parse_json_field(call.get('cache_metadata'))
        if cache_meta.get('cache_hit'):
            cache_hits += 1
        elif cache_meta:
            cache_misses += 1
    
    total_with_cache = cache_hits + cache_misses
    cache_hit_rate = cache_hits / total_with_cache if total_with_cache > 0 else 0
    
    # Group by agent.operation
    by_operation = defaultdict(list)
    for call in calls:
        agent = call.get('agent_name') or 'Unknown'
        operation = call.get('operation') or 'unknown'
        key = f"{agent}.{operation}"
        by_operation[key].append(call)
    
    # Analyze duplicates within each operation
    operation_stats = []
    total_duplicates = 0
    total_wasted_cost = 0
    
    for op_key, op_calls in by_operation.items():
        # Group by prompt hash
        prompt_groups = defaultdict(list)
        for call in op_calls:
            prompt = call.get('prompt') or ''
            if prompt:
                prompt_hash = get_prompt_hash(prompt)
                prompt_groups[prompt_hash].append(call)
        
        # Count duplicates (groups with 2+ calls)
        duplicate_count = 0
        unique_prompts = len(prompt_groups)
        wasted_cost = 0
        duplicate_groups = []
        
        for prompt_hash, group_calls in prompt_groups.items():
            if len(group_calls) >= DUPLICATE_THRESHOLD:
                duplicate_count += len(group_calls)
                avg_cost = sum(c.get('total_cost') or 0 for c in group_calls) / len(group_calls)
                group_wasted = (len(group_calls) - 1) * avg_cost
                wasted_cost += group_wasted
                
                duplicate_groups.append({
                    'hash': prompt_hash,
                    'count': len(group_calls),
                    'wasted_cost': group_wasted,
                    'prompt_preview': (group_calls[0].get('prompt') or '')[:100],
                    'calls': group_calls,
                })
        
        duplicate_groups.sort(key=lambda x: -x['wasted_cost'])
        
        total_calls = len(op_calls)
        redundancy_pct = duplicate_count / total_calls if total_calls > 0 else 0
        
        agent, operation = op_key.split('.', 1) if '.' in op_key else ('Unknown', op_key)
        
        operation_stats.append({
            'agent': agent,
            'operation': operation,
            'agent_operation': op_key,
            'total_calls': total_calls,
            'unique_prompts': unique_prompts,
            'duplicate_count': duplicate_count,
            'redundancy_pct': redundancy_pct,
            'wasted_cost': wasted_cost,
            'has_opportunity': redundancy_pct >= CACHE_OPPORTUNITY_PCT,
            'duplicate_groups': duplicate_groups[:5],
            'calls': op_calls,
        })
        
        total_duplicates += duplicate_count
        total_wasted_cost += wasted_cost
    
    # Sort by wasted cost
    operation_stats.sort(key=lambda x: -x['wasted_cost'])
    
    # Find operations with caching opportunities
    ops_with_opportunity = [op for op in operation_stats if op['has_opportunity']]
    
    if not ops_with_opportunity and cache_hit_rate > 0.3:
        return {
            "has_issues": False,
            "summary_metric": f"{cache_hit_rate:.0%} hit rate",
            "red_flag_count": 0,
            "cache_hit_rate": cache_hit_rate,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "total_duplicates": total_duplicates,
            "potential_savings": total_wasted_cost,
            "affected_operations": [],
            "top_offender": None,
            "detail_table": operation_stats,
        }
    
    top_offender = ops_with_opportunity[0] if ops_with_opportunity else (operation_stats[0] if operation_stats else None)
    
    if not top_offender:
        return _empty_story_result("No cache data")
    
    return {
        "has_issues": True,
        "summary_metric": f"{cache_misses} misses" if cache_misses > 0 else f"{total_duplicates} duplicates",
        "red_flag_count": len(ops_with_opportunity),
        "cache_hit_rate": cache_hit_rate,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "total_duplicates": total_duplicates,
        "potential_savings": total_wasted_cost,
        "affected_operations": [
            {
                "agent_operation": op['agent_operation'],
                "total_calls": op['total_calls'],
                "unique_prompts": op['unique_prompts'],
                "redundancy_pct": f"{op['redundancy_pct']:.0%}",
                "wasted_cost": format_cost(op['wasted_cost']),
            }
            for op in ops_with_opportunity[:5]
        ],
        "top_offender": {
            "agent": top_offender['agent'],
            "operation": top_offender['operation'],
            "agent_operation": top_offender['agent_operation'],
            "total_calls": top_offender['total_calls'],
            "unique_prompts": top_offender['unique_prompts'],
            "redundancy_pct": top_offender['redundancy_pct'],
            "wasted_cost": top_offender['wasted_cost'],
            "duplicate_groups": top_offender['duplicate_groups'],
        },
        "detail_table": operation_stats,
    }


# =============================================================================
# STORY 3: COST CONCENTRATION
# =============================================================================

def analyze_cost_story(calls: List[Dict]) -> Dict[str, Any]:
    """
    Analyze cost distribution across operations.
    
    Identifies where money is being spent and concentration issues.
    """
    if not calls:
        return _empty_story_result("No cost data")
    
    total_cost = sum(c.get('total_cost') or 0 for c in calls)
    
    if total_cost == 0:
        return _empty_story_result("No cost data")
    
    # Group by agent.operation
    by_operation = defaultdict(lambda: {'calls': [], 'cost': 0})
    by_agent = defaultdict(lambda: {'calls': [], 'cost': 0})
    
    for call in calls:
        agent = call.get('agent_name') or 'Unknown'
        operation = call.get('operation') or 'unknown'
        cost = call.get('total_cost') or 0
        
        op_key = f"{agent}.{operation}"
        by_operation[op_key]['calls'].append(call)
        by_operation[op_key]['cost'] += cost
        
        by_agent[agent]['calls'].append(call)
        by_agent[agent]['cost'] += cost
    
    # Build operation stats
    operation_stats = []
    for op_key, data in by_operation.items():
        cost_share = data['cost'] / total_cost if total_cost > 0 else 0
        avg_cost = data['cost'] / len(data['calls']) if data['calls'] else 0
        
        agent, operation = op_key.split('.', 1) if '.' in op_key else ('Unknown', op_key)
        
        operation_stats.append({
            'agent': agent,
            'operation': operation,
            'agent_operation': op_key,
            'total_cost': data['cost'],
            'cost_share': cost_share,
            'call_count': len(data['calls']),
            'avg_cost': avg_cost,
            'calls': data['calls'],
        })
    
    # Sort by cost
    operation_stats.sort(key=lambda x: -x['total_cost'])
    
    # Calculate top 3 concentration
    top_3_cost = sum(op['total_cost'] for op in operation_stats[:3])
    top_3_concentration = top_3_cost / total_cost if total_cost > 0 else 0
    
    # Build agent stats
    agent_stats = []
    for agent, data in by_agent.items():
        cost_share = data['cost'] / total_cost if total_cost > 0 else 0
        agent_stats.append({
            'agent': agent,
            'total_cost': data['cost'],
            'cost_share': cost_share,
            'call_count': len(data['calls']),
        })
    agent_stats.sort(key=lambda x: -x['total_cost'])
    
    has_concentration = top_3_concentration > COST_CONCENTRATION_THRESHOLD
    top_offender = operation_stats[0] if operation_stats else None
    
    return {
        "has_issues": has_concentration,
        "summary_metric": f"{top_3_concentration:.0%} in 3 ops",
        "red_flag_count": 3 if has_concentration else 0,
        "total_cost": total_cost,
        "top_3_concentration": top_3_concentration,
        "affected_operations": [
            {
                "agent_operation": op['agent_operation'],
                "total_cost": format_cost(op['total_cost']),
                "cost_share": f"{op['cost_share']:.1%}",
                "call_count": op['call_count'],
                "avg_cost": format_cost(op['avg_cost']),
            }
            for op in operation_stats[:5]
        ],
        "top_offender": {
            "agent": top_offender['agent'],
            "operation": top_offender['operation'],
            "agent_operation": top_offender['agent_operation'],
            "total_cost": top_offender['total_cost'],
            "cost_share": top_offender['cost_share'],
            "call_count": top_offender['call_count'],
        } if top_offender else None,
        "by_agent": agent_stats,
        "detail_table": operation_stats,
    }


# =============================================================================
# STORY 4: SYSTEM PROMPT WASTE
# =============================================================================

def analyze_system_prompt_story(calls: List[Dict]) -> Dict[str, Any]:
    """
    Analyze system prompt redundancy.
    
    Identifies operations sending large system prompts repeatedly.
    """
    if not calls:
        return _empty_story_result("No prompt data")
    
    # Group by agent.operation
    by_operation = defaultdict(list)
    for call in calls:
        agent = call.get('agent_name') or 'Unknown'
        operation = call.get('operation') or 'unknown'
        key = f"{agent}.{operation}"
        by_operation[key].append(call)
    
    # Analyze system prompt usage per operation
    operation_stats = []
    total_redundant_tokens = 0
    
    for op_key, op_calls in by_operation.items():
        system_tokens_list = []
        total_prompt_tokens = 0
        
        for call in op_calls:
            prompt_tokens = call.get('prompt_tokens') or 0
            total_prompt_tokens += prompt_tokens
            
            # Try to get from prompt_breakdown
            breakdown = parse_json_field(call.get('prompt_breakdown'))
            system_tokens = breakdown.get('system_prompt_tokens') or 0
            
            # If not available, try metadata
            if not system_tokens:
                metadata = parse_json_field(call.get('metadata'))
                system_tokens = metadata.get('system_prompt_tokens') or 0
            
            # If still not available, estimate (40% of prompt for operations with system prompts)
            if not system_tokens and prompt_tokens > 500:
                system_tokens = int(prompt_tokens * 0.4)
            
            system_tokens_list.append(system_tokens)
        
        avg_system_tokens = sum(system_tokens_list) / len(system_tokens_list) if system_tokens_list else 0
        total_system_tokens = sum(system_tokens_list)
        
        # Calculate waste: if same system prompt sent N times, (N-1) are redundant
        call_count = len(op_calls)
        if call_count > 1 and avg_system_tokens > 100:
            redundant_tokens = int(avg_system_tokens * (call_count - 1))
        else:
            redundant_tokens = 0
        
        avg_prompt_tokens = total_prompt_tokens / call_count if call_count > 0 else 0
        system_pct = avg_system_tokens / avg_prompt_tokens if avg_prompt_tokens > 0 else 0
        
        agent, operation = op_key.split('.', 1) if '.' in op_key else ('Unknown', op_key)
        
        has_waste = (system_pct > SYSTEM_PROMPT_WASTE_PCT or 
                     avg_system_tokens > SYSTEM_PROMPT_HIGH_TOKENS)
        
        operation_stats.append({
            'agent': agent,
            'operation': operation,
            'agent_operation': op_key,
            'call_count': call_count,
            'avg_system_tokens': int(avg_system_tokens),
            'total_system_tokens': total_system_tokens,
            'avg_prompt_tokens': int(avg_prompt_tokens),
            'system_pct': system_pct,
            'redundant_tokens': redundant_tokens,
            'has_waste': has_waste,
            'calls': op_calls,
        })
        
        total_redundant_tokens += redundant_tokens
    
    # Sort by redundant tokens
    operation_stats.sort(key=lambda x: -x['redundant_tokens'])
    
    ops_with_waste = [op for op in operation_stats if op['has_waste']]
    
    if not ops_with_waste:
        return {
            "has_issues": False,
            "summary_metric": "Efficient",
            "red_flag_count": 0,
            "total_redundant_tokens": 0,
            "affected_operations": [],
            "top_offender": None,
            "detail_table": operation_stats,
        }
    
    top_offender = ops_with_waste[0]
    
    # Format tokens for display
    if total_redundant_tokens >= 1000:
        token_display = f"{total_redundant_tokens/1000:.0f}K redundant"
    else:
        token_display = f"{total_redundant_tokens} redundant"
    
    return {
        "has_issues": True,
        "summary_metric": token_display,
        "red_flag_count": len(ops_with_waste),
        "total_redundant_tokens": total_redundant_tokens,
        "affected_operations": [
            {
                "agent_operation": op['agent_operation'],
                "avg_system_tokens": format_tokens(op['avg_system_tokens']),
                "system_pct": f"{op['system_pct']:.0%}",
                "redundant_tokens": format_tokens(op['redundant_tokens']),
                "call_count": op['call_count'],
            }
            for op in ops_with_waste[:5]
        ],
        "top_offender": {
            "agent": top_offender['agent'],
            "operation": top_offender['operation'],
            "agent_operation": top_offender['agent_operation'],
            "avg_system_tokens": top_offender['avg_system_tokens'],
            "system_pct": top_offender['system_pct'],
            "redundant_tokens": top_offender['redundant_tokens'],
            "call_count": top_offender['call_count'],
            "recommendation": _get_system_prompt_recommendation(top_offender),
        },
        "detail_table": operation_stats,
    }


def _get_system_prompt_recommendation(op_stats: Dict) -> str:
    """Get recommendation for system prompt optimization."""
    avg_tokens = op_stats.get('avg_system_tokens', 0)
    call_count = op_stats.get('call_count', 0)
    
    if avg_tokens > 1500:
        return "Compress system prompt (can often reduce by 60-70%)"
    elif call_count > 10:
        return "Enable prompt caching for repeated system prompts"
    else:
        return "Consider prompt caching or compression"


# =============================================================================
# STORY 5: TOKEN IMBALANCE
# =============================================================================

def analyze_token_imbalance_story(calls: List[Dict]) -> Dict[str, Any]:
    """
    Analyze prompt:completion token ratios.
    
    Identifies operations with extreme ratios (sending lots, getting little back).
    """
    if not calls:
        return _empty_story_result("No token data")
    
    # Group by agent.operation
    by_operation = defaultdict(list)
    for call in calls:
        agent = call.get('agent_name') or 'Unknown'
        operation = call.get('operation') or 'unknown'
        key = f"{agent}.{operation}"
        by_operation[key].append(call)
    
    operation_stats = []
    
    for op_key, op_calls in by_operation.items():
        total_prompt = sum(c.get('prompt_tokens') or 0 for c in op_calls)
        total_completion = sum(c.get('completion_tokens') or 0 for c in op_calls)
        total_cost = sum(c.get('total_cost') or 0 for c in op_calls)
        
        avg_prompt = total_prompt / len(op_calls) if op_calls else 0
        avg_completion = total_completion / len(op_calls) if op_calls else 0
        
        ratio = avg_prompt / avg_completion if avg_completion > 0 else float('inf')
        
        agent, operation = op_key.split('.', 1) if '.' in op_key else ('Unknown', op_key)
        
        is_imbalanced = ratio > TOKEN_RATIO_WARNING
        is_critical = ratio > TOKEN_RATIO_CRITICAL
        
        operation_stats.append({
            'agent': agent,
            'operation': operation,
            'agent_operation': op_key,
            'call_count': len(op_calls),
            'avg_prompt_tokens': int(avg_prompt),
            'avg_completion_tokens': int(avg_completion),
            'ratio': ratio,
            'total_cost': total_cost,
            'is_imbalanced': is_imbalanced,
            'is_critical': is_critical,
            'calls': op_calls,
        })
    
    # Sort by ratio (highest first)
    operation_stats.sort(key=lambda x: -x['ratio'] if x['ratio'] != float('inf') else -999999)
    
    imbalanced_ops = [op for op in operation_stats if op['is_imbalanced']]
    
    if not imbalanced_ops:
        return {
            "has_issues": False,
            "summary_metric": "Balanced",
            "red_flag_count": 0,
            "affected_operations": [],
            "top_offender": None,
            "detail_table": operation_stats,
        }
    
    top_offender = imbalanced_ops[0]
    ratio_display = f"{top_offender['ratio']:.0f}:1" if top_offender['ratio'] < 1000 else "High"
    
    return {
        "has_issues": True,
        "summary_metric": f"{ratio_display} ratio",
        "red_flag_count": len(imbalanced_ops),
        "affected_operations": [
            {
                "agent_operation": op['agent_operation'],
                "avg_prompt": format_tokens(op['avg_prompt_tokens']),
                "avg_completion": format_tokens(op['avg_completion_tokens']),
                "ratio": f"{op['ratio']:.0f}:1" if op['ratio'] < 1000 else "Very high",
                "call_count": op['call_count'],
                "is_critical": op['is_critical'],
            }
            for op in imbalanced_ops[:5]
        ],
        "top_offender": {
            "agent": top_offender['agent'],
            "operation": top_offender['operation'],
            "agent_operation": top_offender['agent_operation'],
            "avg_prompt_tokens": top_offender['avg_prompt_tokens'],
            "avg_completion_tokens": top_offender['avg_completion_tokens'],
            "ratio": top_offender['ratio'],
            "diagnosis": _diagnose_imbalance(top_offender),
        },
        "detail_table": operation_stats,
    }


def _diagnose_imbalance(op_stats: Dict) -> str:
    """Diagnose the cause of token imbalance."""
    avg_prompt = op_stats.get('avg_prompt_tokens', 0)
    avg_completion = op_stats.get('avg_completion_tokens', 0)
    
    if avg_prompt > 3000 and avg_completion < 200:
        return "Large context with minimal output - likely chat history bloat. Implement sliding window."
    elif avg_prompt > 1500:
        return "Consider summarizing history or reducing context."
    else:
        return "Review if all context is necessary for this operation."


# =============================================================================
# STORY 6: MODEL ROUTING
# =============================================================================

def analyze_routing_story(calls: List[Dict]) -> Dict[str, Any]:
    """
    Analyze model routing opportunities.
    
    Identifies complexity mismatches (high complexity on cheap models).
    """
    if not calls:
        return _empty_story_result("No routing data")
    
    # Group by agent.operation
    by_operation = defaultdict(list)
    for call in calls:
        agent = call.get('agent_name') or 'Unknown'
        operation = call.get('operation') or 'unknown'
        key = f"{agent}.{operation}"
        by_operation[key].append(call)
    
    operation_stats = []
    upgrade_candidates = []
    downgrade_candidates = []
    
    for op_key, op_calls in by_operation.items():
        complexity_scores = []
        models_used = defaultdict(int)
        
        for call in op_calls:
            routing = parse_json_field(call.get('routing_decision'))
            complexity = routing.get('complexity_score')
            
            if complexity is None:
                metadata = parse_json_field(call.get('metadata'))
                complexity = metadata.get('complexity_score')
            
            if complexity is not None:
                complexity_scores.append(complexity)
            
            model = call.get('model_name') or 'unknown'
            models_used[model] += 1
        
        avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else None
        primary_model = max(models_used, key=models_used.get) if models_used else 'unknown'
        is_cheap_model = any(cheap in primary_model.lower() for cheap in CHEAP_MODELS)
        
        agent, operation = op_key.split('.', 1) if '.' in op_key else ('Unknown', op_key)
        
        is_upgrade_candidate = (avg_complexity is not None and 
                                avg_complexity >= HIGH_COMPLEXITY_THRESHOLD and 
                                is_cheap_model)
        
        total_cost = sum(c.get('total_cost') or 0 for c in op_calls)
        
        op_stat = {
            'agent': agent,
            'operation': operation,
            'agent_operation': op_key,
            'call_count': len(op_calls),
            'avg_complexity': avg_complexity,
            'primary_model': primary_model,
            'is_cheap_model': is_cheap_model,
            'is_upgrade_candidate': is_upgrade_candidate,
            'total_cost': total_cost,
            'models_used': dict(models_used),
            'calls': op_calls,
        }
        
        operation_stats.append(op_stat)
        
        if is_upgrade_candidate:
            upgrade_candidates.append(op_stat)
    
    operation_stats.sort(key=lambda x: -(x['avg_complexity'] or 0))
    
    total_misrouted = len(upgrade_candidates) + len(downgrade_candidates)
    
    if total_misrouted == 0:
        return {
            "has_issues": False,
            "summary_metric": "Well routed",
            "red_flag_count": 0,
            "affected_operations": [],
            "top_offender": None,
            "upgrade_candidates": [],
            "downgrade_candidates": [],
            "detail_table": operation_stats,
        }
    
    top_offender = upgrade_candidates[0] if upgrade_candidates else downgrade_candidates[0]
    
    return {
        "has_issues": True,
        "summary_metric": f"{total_misrouted} misrouted",
        "red_flag_count": total_misrouted,
        "affected_operations": [
            {
                "agent_operation": op['agent_operation'],
                "avg_complexity": f"{op['avg_complexity']:.2f}" if op['avg_complexity'] else "—",
                "primary_model": op['primary_model'],
                "call_count": op['call_count'],
                "issue": "⬆️ Upgrade" if op['is_upgrade_candidate'] else "⬇️ Downgrade",
            }
            for op in (upgrade_candidates + downgrade_candidates)[:5]
        ],
        "top_offender": {
            "agent": top_offender['agent'],
            "operation": top_offender['operation'],
            "agent_operation": top_offender['agent_operation'],
            "avg_complexity": top_offender['avg_complexity'],
            "primary_model": top_offender['primary_model'],
            "call_count": top_offender['call_count'],
            "recommendation": "Route to gpt-4o for better quality on complex tasks",
        },
        "upgrade_candidates": upgrade_candidates,
        "downgrade_candidates": downgrade_candidates,
        "detail_table": operation_stats,
    }


# =============================================================================
# STORY 7: QUALITY ISSUES
# =============================================================================

def analyze_quality_story(calls: List[Dict]) -> Dict[str, Any]:
    """
    Analyze quality issues (errors and hallucinations).
    """
    if not calls:
        return _empty_story_result("No quality data")
    
    errors = []
    hallucinations = []
    
    for call in calls:
        success = call.get('success', True)
        error = call.get('error') or ''
        
        if not success or error:
            errors.append({
                'agent': call.get('agent_name') or 'Unknown',
                'operation': call.get('operation') or 'unknown',
                'error': error or 'Unknown error',
                'timestamp': call.get('timestamp'),
                'call': call,
            })
        
        quality_eval = parse_json_field(call.get('quality_evaluation'))
        # FIXED: Only check hallucination_flag (correct field name)
        if quality_eval.get('hallucination_flag'):
            hallucinations.append({
                'agent': call.get('agent_name') or 'Unknown',
                'operation': call.get('operation') or 'unknown',
                'details': quality_eval.get('hallucination_details') or 'Hallucination detected',
                # FIXED: Only use judge_score (correct field name)
                'score': quality_eval.get('judge_score'),
                'call': call,
            })
    
    total_calls = len(calls)
    error_rate = len(errors) / total_calls if total_calls > 0 else 0
    
    # Group errors by operation
    error_by_op = defaultdict(list)
    for err in errors:
        key = f"{err['agent']}.{err['operation']}"
        error_by_op[key].append(err)
    
    op_error_counts = [(op, len(errs)) for op, errs in error_by_op.items()]
    op_error_counts.sort(key=lambda x: -x[1])
    
    has_issues = len(errors) > 0 or len(hallucinations) > 0
    
    if not has_issues:
        return {
            "has_issues": False,
            "summary_metric": "All good",
            "red_flag_count": 0,
            "error_rate": 0,
            "error_count": 0,
            "hallucination_count": 0,
            "affected_operations": [],
            "top_offender": None,
            "errors": [],
            "hallucinations": [],
            "detail_table": [],
        }
    
    affected_ops = []
    for op, count in op_error_counts[:5]:
        agent, operation = op.split('.', 1) if '.' in op else ('Unknown', op)
        affected_ops.append({
            "agent_operation": op,
            "error_count": count,
            "errors": error_by_op[op],
        })
    
    top_offender = None
    if op_error_counts:
        top_op, top_count = op_error_counts[0]
        agent, operation = top_op.split('.', 1) if '.' in top_op else ('Unknown', top_op)
        top_offender = {
            "agent": agent,
            "operation": operation,
            "agent_operation": top_op,
            "error_count": top_count,
            "sample_error": error_by_op[top_op][0]['error'] if error_by_op[top_op] else None,
        }
    
    issue_count = len(errors) + len(hallucinations)
    
    return {
        "has_issues": True,
        "summary_metric": f"{issue_count} issues",
        "red_flag_count": issue_count,
        "error_rate": error_rate,
        "error_count": len(errors),
        "hallucination_count": len(hallucinations),
        "affected_operations": affected_ops,
        "top_offender": top_offender,
        "errors": errors,
        "hallucinations": hallucinations,
        "detail_table": op_error_counts,
    }


# =============================================================================
# AGGREGATE FUNCTIONS
# =============================================================================

def analyze_all_stories(calls: List[Dict]) -> Dict[str, Dict[str, Any]]:
    """
    Run all story analyses and return combined results.
    """
    return {
        "latency": analyze_latency_story(calls),
        "cache": analyze_cache_story(calls),
        "cost": analyze_cost_story(calls),
        "system_prompt": analyze_system_prompt_story(calls),
        "token_imbalance": analyze_token_imbalance_story(calls),
        "routing": analyze_routing_story(calls),
        "quality": analyze_quality_story(calls),
    }


def get_story_summary(calls: List[Dict]) -> List[Dict[str, Any]]:
    """
    Get summary of all stories for dashboard cards.
    
    Returns list of story summaries ordered by severity.
    """
    all_stories = analyze_all_stories(calls)
    
    story_cards = [
        {
            "id": "latency",
            "title": "Latency Monster",
            "icon": "🐌",
            "target_page": "🔀 Model Router",
            **_extract_card_data(all_stories["latency"]),
        },
        {
            "id": "cache",
            "title": "Zero Cache Hits",
            "icon": "💾",
            "target_page": "💾 Cache Analyzer",
            **_extract_card_data(all_stories["cache"]),
        },
        {
            "id": "cost",
            "title": "Cost Concentration",
            "icon": "💰",
            "target_page": "💰 Cost Estimator",
            **_extract_card_data(all_stories["cost"]),
        },
        {
            "id": "system_prompt",
            "title": "System Prompt Waste",
            "icon": "📝",
            "target_page": "✨ Prompt Optimizer",
            **_extract_card_data(all_stories["system_prompt"]),
        },
        {
            "id": "token_imbalance",
            "title": "Token Imbalance",
            "icon": "⚖️",
            "target_page": "✨ Prompt Optimizer",
            **_extract_card_data(all_stories["token_imbalance"]),
        },
        {
            "id": "routing",
            "title": "Model Routing",
            "icon": "🔀",
            "target_page": "🔀 Model Router",
            **_extract_card_data(all_stories["routing"]),
        },
        {
            "id": "quality",
            "title": "Quality Issues",
            "icon": "❌",
            "target_page": "⚖️ LLM Judge",
            **_extract_card_data(all_stories["quality"]),
        },
    ]
    
    # Sort by has_issues (issues first), then by red_flag_count
    story_cards.sort(key=lambda x: (-int(x['has_issues']), -x['red_flag_count']))
    
    return story_cards


def _extract_card_data(story_result: Dict) -> Dict:
    """Extract data needed for story card display."""
    return {
        "has_issues": story_result.get("has_issues", False),
        "summary_metric": story_result.get("summary_metric", "—"),
        "red_flag_count": story_result.get("red_flag_count", 0),
        "top_offender": story_result.get("top_offender"),
    }


def _empty_story_result(message: str) -> Dict[str, Any]:
    """Return empty story result."""
    return {
        "has_issues": False,
        "summary_metric": message,
        "red_flag_count": 0,
        "affected_operations": [],
        "top_offender": None,
        "detail_table": [],
    }