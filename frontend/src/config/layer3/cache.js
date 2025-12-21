/**
 * Cache Story - Layer 3 Configuration
 * 
 * Defines:
 * - KPI definitions
 * - Factor detection rules
 * - Fix templates (cache implementations)
 * - Analysis functions
 * 
 * Note: Cache L3 operates on PROMPT PATTERNS, not individual calls
 */

// ─────────────────────────────────────────────────────────────────────────────
// STORY METADATA
// ─────────────────────────────────────────────────────────────────────────────

export const CACHE_STORY = {
  id: 'cache',
  label: 'Cache Opportunity',
  icon: '💾',
  color: '#ec4899', // Pink
  entityType: 'pattern', // This is key - we're analyzing patterns, not calls
};

// ─────────────────────────────────────────────────────────────────────────────
// KPI DEFINITIONS
// ─────────────────────────────────────────────────────────────────────────────

export function getCacheKPIs(pattern) {
  const effortLabels = { low: '🟢 Low', medium: '🟡 Medium', high: '🔴 High' };
  
  return [
    {
      label: 'Repeats',
      value: `${pattern.repeat_count}x`,
      subtext: 'Same prompt',
      status: pattern.repeat_count > 5 ? 'critical' : 'warning',
    },
    {
      label: 'Wasted Cost',
      value: `$${(pattern.wasted_cost || 0).toFixed(3)}`,
      subtext: `${pattern.repeat_count - 1} duplicate calls`,
      status: pattern.wasted_cost > 0.1 ? 'critical' : 'warning',
    },
    {
      label: 'Savable Latency',
      value: `~${((pattern.avg_latency_ms || 0) * (pattern.repeat_count - 1) / 1000).toFixed(0)}s`,
      subtext: 'Per day',
      status: 'neutral',
    },
    {
      label: 'Effort',
      value: effortLabels[pattern.effort] || '🟢 Low',
      subtext: pattern.cache_type === 'exact' ? 'Easy fix' : 'Requires setup',
      status: 'neutral',
    },
  ];
}

// ─────────────────────────────────────────────────────────────────────────────
// FACTOR DETECTION
// ─────────────────────────────────────────────────────────────────────────────

export function analyzeCacheFactors(pattern) {
  const factors = [];

  // Factor: No caching implemented
  factors.push({
    id: 'no_cache',
    severity: pattern.repeat_count > 5 ? 'critical' : 'warning',
    label: 'No Caching Implemented',
    impact: `${pattern.repeat_count} identical calls made`,
    description: 'No cache layer detected for this operation.',
    hasFix: true,
  });

  // Factor: Cache type indicator
  const cacheTypeLabels = {
    exact: 'Exact Match (100% identical)',
    prefix: 'Stable Prefix (same start, variable end)',
    semantic: 'Semantic Similarity (similar meaning)',
  };

  factors.push({
    id: `cache_type_${pattern.cache_type}`,
    severity: 'info',
    label: `Cache Type: ${pattern.cache_type_emoji || '🎯'} ${cacheTypeLabels[pattern.cache_type] || pattern.cache_type}`,
    impact: pattern.cache_type === 'exact' ? 'Simple key-value cache will work' : 'May need more sophisticated caching',
    description: pattern.cache_type === 'exact' 
      ? 'All prompts are 100% identical - easiest to cache.'
      : 'Prompts have variations - consider prefix or semantic caching.',
    hasFix: false,
  });

  // Factor: Response consistency (if available)
  if (pattern.response_similarity != null) {
    factors.push({
      id: 'response_consistency',
      severity: pattern.response_similarity === 100 ? 'ok' : 'info',
      label: `Response Consistency: ${pattern.response_similarity}%`,
      impact: pattern.response_similarity === 100 
        ? 'All responses identical - safe to cache' 
        : 'Responses vary slightly - verify cache validity',
      description: 'How similar the responses were across repeated calls.',
      hasFix: false,
    });
  }

  return factors;
}

// ─────────────────────────────────────────────────────────────────────────────
// PROMPT ANALYSIS
// ─────────────────────────────────────────────────────────────────────────────

export function analyzeCachePrompt(pattern) {
  return {
    hash: pattern.prompt_hash,
    first_seen: pattern.first_seen,
    last_seen: pattern.last_seen,
    is_static: pattern.cache_type === 'exact',
    stable_prefix: pattern.stable_prefix,
    variable_suffix: pattern.variable_suffix,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// FIX DEFINITIONS (CACHE IMPLEMENTATIONS)
// ─────────────────────────────────────────────────────────────────────────────

export function getCacheFixes(pattern) {
  const fixes = [];
  const repeatCount = pattern.repeat_count || 1;
  const wastedCost = pattern.wasted_cost || 0;
  const avgLatency = pattern.avg_latency_ms || 4000;

  // Common metrics for all cache implementations
  const baseMetrics = [
    {
      label: 'LLM Calls',
      before: `${repeatCount}`,
      after: '1',
      changePercent: -Math.round((1 - 1/repeatCount) * 100),
    },
    {
      label: 'Cost',
      before: `$${(wastedCost + (pattern.unit_cost || 0.034)).toFixed(3)}`,
      after: `$${(pattern.unit_cost || 0.034).toFixed(3)}`,
      changePercent: -Math.round((wastedCost / (wastedCost + (pattern.unit_cost || 0.034))) * 100),
    },
    {
      label: 'Avg Response Time',
      before: `${(avgLatency / 1000).toFixed(1)}s`,
      after: '~0.001s (cache hit)',
      changePercent: -99,
    },
  ];

  // Fix 1: Simple Key-Value Cache (always available for exact match)
  if (pattern.cache_type === 'exact') {
    fixes.push({
      id: 'simple_cache',
      title: 'Simple Key-Value Cache',
      effort: 'Low',
      risk: 'Low',
      tradeoff: 'In-memory only, lost on restart',
      
      metrics: baseMetrics,
      
      codeBefore: `def ${pattern.operation || 'process'}(input_data):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": input_data}
        ]
    )
    return response.choices[0].message.content`,
    
      codeAfter: `import hashlib

_cache = {}  # Simple in-memory cache

def ${pattern.operation || 'process'}(input_data):
    # Create cache key
    cache_key = hashlib.md5(
        f"{SYSTEM_PROMPT}:{input_data}".encode()
    ).hexdigest()
    
    # Return cached if exists
    if cache_key in _cache:
        return _cache[cache_key]
    
    # Call LLM
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": input_data}
        ]
    )
    result = response.choices[0].message.content
    
    # Cache and return
    _cache[cache_key] = result
    return result`,

      outputBefore: `Call 1: LLM → response (${(avgLatency/1000).toFixed(1)}s, $${(pattern.unit_cost || 0.034).toFixed(3)})
Call 2: LLM → response (${(avgLatency/1000).toFixed(1)}s, $${(pattern.unit_cost || 0.034).toFixed(3)})
Call 3: LLM → response (${(avgLatency/1000).toFixed(1)}s, $${(pattern.unit_cost || 0.034).toFixed(3)})
...
Call ${repeatCount}: LLM → response (${(avgLatency/1000).toFixed(1)}s, $${(pattern.unit_cost || 0.034).toFixed(3)})

Total: ${repeatCount} LLM calls, ~${(avgLatency * repeatCount / 1000).toFixed(0)}s, $${((pattern.unit_cost || 0.034) * repeatCount).toFixed(3)}`,

      outputAfter: `Call 1: LLM   → response (${(avgLatency/1000).toFixed(1)}s, $${(pattern.unit_cost || 0.034).toFixed(3)})
Call 2: CACHE → response (0.001s, $0)
Call 3: CACHE → response (0.001s, $0)
...
Call ${repeatCount}: CACHE → response (0.001s, $0)

Total: 1 LLM call + ${repeatCount - 1} cache hits
Time: ~${(avgLatency/1000).toFixed(1)}s, Cost: $${(pattern.unit_cost || 0.034).toFixed(3)}

✅ Same output, ${Math.round((1 - 1/repeatCount) * 100)}% less cost`,
      outputBeforeLabel: `(${repeatCount} LLM calls)`,
      outputAfterLabel: `(1 LLM + ${repeatCount - 1} cache hits)`,
    });
  }

  // Fix 2: Redis Cache (available for all types)
  fixes.push({
    id: 'redis_cache',
    title: 'Redis Cache',
    effort: 'Medium',
    risk: 'Low',
    tradeoff: 'Requires Redis setup',
    
    metrics: baseMetrics,
    
    codeBefore: `def ${pattern.operation || 'process'}(input_data):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    return response.choices[0].message.content`,
    
    codeAfter: `import redis
import hashlib
import json

redis_client = redis.Redis(host='localhost', port=6379)
CACHE_TTL = 3600  # 1 hour

def ${pattern.operation || 'process'}(input_data):
    # Create cache key
    cache_key = f"llm:{hashlib.md5(str(messages).encode()).hexdigest()}"
    
    # Check cache
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Call LLM
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    result = response.choices[0].message.content
    
    # Cache with TTL
    redis_client.setex(cache_key, CACHE_TTL, json.dumps(result))
    return result`,
  });

  // Fix 3: LRU Cache with functools (Python-specific, simple)
  if (pattern.cache_type === 'exact') {
    fixes.push({
      id: 'lru_cache',
      title: 'LRU Memory Cache',
      effort: 'Low',
      risk: 'Low',
      tradeoff: 'Limited size, in-memory only',
      
      metrics: baseMetrics,
      
      codeBefore: `def ${pattern.operation || 'process'}(input_data):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    return response.choices[0].message.content`,
    
      codeAfter: `from functools import lru_cache

@lru_cache(maxsize=1000)
def ${pattern.operation || 'process'}(input_data: str) -> str:
    """Cached LLM call - input must be hashable string."""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": input_data}
        ]
    )
    return response.choices[0].message.content

# To clear cache if needed:
# ${pattern.operation || 'process'}.cache_clear()`,
    });
  }

  return fixes.slice(0, 3); // Max 3 fixes
}

// ─────────────────────────────────────────────────────────────────────────────
// SIMILAR PANEL CONFIG
// ─────────────────────────────────────────────────────────────────────────────

export const CACHE_SIMILAR_CONFIG = {
  groupOptions: [
    { id: 'pattern', label: 'This Pattern' },
    { id: 'operation', label: 'Same Operation' },
    { id: 'agent', label: 'Same Agent' },
  ],
  defaultGroup: 'pattern',
  
  columns: [
    { key: 'call_id', label: 'Call ID', format: (v) => v?.substring(0, 8) + '...' },
    { key: 'timestamp', label: 'Timestamp' },
    { key: 'latency_ms', label: 'Latency', format: (v) => `${(v/1000).toFixed(2)}s` },
    { key: 'cost', label: 'Cost', format: (v) => `$${v?.toFixed(3)}` },
  ],
  
  issueKey: 'is_duplicate',
  issueLabel: 'Duplicate',
  okLabel: '1st Call',
};