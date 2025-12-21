/**
 * Cost Story - Layer 3 Configuration
 * 
 * UPDATED:
 * - Lower thresholds for factor detection
 * - More fix recommendations (always show at least 2-3)
 * - Better detection for non-premium models
 */

// ─────────────────────────────────────────────────────────────────────────────
// STORY METADATA
// ─────────────────────────────────────────────────────────────────────────────

export const COST_STORY = {
  id: 'cost',
  label: 'Cost Analysis',
  icon: '💰',
  color: '#10b981', // Emerald green
  entityType: 'call',
};

// ─────────────────────────────────────────────────────────────────────────────
// THRESHOLDS (lowered for better detection)
// ─────────────────────────────────────────────────────────────────────────────

const THRESHOLDS = {
  high_cost: 0.05,           // $0.05+ is high (was implicit)
  medium_cost: 0.02,         // $0.02+ is medium
  high_input_pct: 60,        // Input > 60% of total tokens (was 70)
  high_output_tokens: 1000,  // Output > 1000 tokens (was 1500)
  large_prompt: 1500,        // Prompt > 1500 tokens (was 2000)
  above_average_ratio: 1.2,  // 20% above average (was 1.5)
};

// ─────────────────────────────────────────────────────────────────────────────
// MODEL PRICING (per 1K tokens)
// ─────────────────────────────────────────────────────────────────────────────

const MODEL_PRICING = {
  'gpt-4o': { input: 0.0025, output: 0.01, tier: 'premium' },
  'gpt-4o-mini': { input: 0.00015, output: 0.0006, tier: 'budget' },
  'gpt-4-turbo': { input: 0.01, output: 0.03, tier: 'premium' },
  'gpt-3.5-turbo': { input: 0.0005, output: 0.0015, tier: 'budget' },
  'claude-3-opus': { input: 0.015, output: 0.075, tier: 'premium' },
  'claude-3-sonnet': { input: 0.003, output: 0.015, tier: 'standard' },
  'claude-3-haiku': { input: 0.00025, output: 0.00125, tier: 'budget' },
};

// ─────────────────────────────────────────────────────────────────────────────
// HELPER FUNCTIONS
// ─────────────────────────────────────────────────────────────────────────────

function getModelTier(modelName) {
  const name = modelName?.toLowerCase() || '';
  
  // Check for premium models
  if (name.includes('gpt-4o') && !name.includes('mini')) return 'premium';
  if (name.includes('gpt-4-turbo')) return 'premium';
  if (name.includes('claude-3-opus')) return 'premium';
  if (name.includes('claude-3-sonnet')) return 'standard';
  
  // Budget models
  if (name.includes('mini') || name.includes('haiku') || name.includes('3.5')) return 'budget';
  
  return 'standard';
}

function getCostStatus(cost, avgCost = null) {
  if (avgCost && cost > avgCost * 1.5) {
    return { status: 'high', emoji: '🔴', label: 'High', color: 'text-red-400' };
  }
  if (cost > THRESHOLDS.high_cost) {
    return { status: 'high', emoji: '🔴', label: 'High', color: 'text-red-400' };
  }
  if (cost > THRESHOLDS.medium_cost) {
    return { status: 'medium', emoji: '🟡', label: 'Medium', color: 'text-yellow-400' };
  }
  return { status: 'low', emoji: '🟢', label: 'Low', color: 'text-green-400' };
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI DEFINITIONS
// ─────────────────────────────────────────────────────────────────────────────

export function getCostKPIs(call, operationStats = null) {
  const totalCost = call.total_cost || 0;
  const promptCost = call.prompt_cost || (totalCost * 0.6); // Estimate if not provided
  const completionCost = call.completion_cost || (totalCost - promptCost);
  const costStatus = getCostStatus(totalCost, operationStats?.avg_cost);
  
  // Calculate vs average
  let vsAvg = null;
  let vsAvgStatus = 'neutral';
  if (operationStats?.avg_cost) {
    vsAvg = ((totalCost - operationStats.avg_cost) / operationStats.avg_cost) * 100;
    vsAvgStatus = vsAvg > 20 ? 'critical' : vsAvg > 0 ? 'warning' : 'good';
  }

  return [
    {
      label: 'Total Cost',
      value: `$${totalCost.toFixed(3)}`,
      subtext: costStatus.label,
      status: costStatus.status === 'high' ? 'critical' : 
              costStatus.status === 'medium' ? 'warning' : 'good',
    },
    {
      label: 'Input Cost',
      value: `$${promptCost.toFixed(3)}`,
      subtext: `${call.prompt_tokens?.toLocaleString() || 0} tokens`,
      status: 'neutral',
    },
    {
      label: 'Output Cost',
      value: `$${completionCost.toFixed(3)}`,
      subtext: `${call.completion_tokens?.toLocaleString() || 0} tokens`,
      status: 'neutral',
    },
    {
      label: 'vs Op. Avg',
      value: vsAvg !== null ? `${vsAvg >= 0 ? '+' : ''}${vsAvg.toFixed(0)}%` : '—',
      subtext: operationStats ? `Avg: $${operationStats.avg_cost?.toFixed(3)}` : 'No data',
      status: vsAvgStatus,
    },
  ];
}

// ─────────────────────────────────────────────────────────────────────────────
// CURRENT STATE (for comparison table)
// ─────────────────────────────────────────────────────────────────────────────

export function getCostCurrentState(call) {
  return {
    cost: `$${(call.total_cost || 0).toFixed(3)}`,
    input: `$${(call.prompt_cost || 0).toFixed(3)}`,
    output: `$${(call.completion_cost || 0).toFixed(3)}`,
    tokens: (call.prompt_tokens + call.completion_tokens)?.toLocaleString() || '0',
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// COST BREAKDOWN
// ─────────────────────────────────────────────────────────────────────────────

export function getCostBreakdown(call) {
  const totalCost = call.total_cost || 0;
  const promptCost = call.prompt_cost || (totalCost * 0.6);
  const completionCost = call.completion_cost || (totalCost - promptCost);
  const totalTokens = (call.prompt_tokens || 0) + (call.completion_tokens || 0);
  
  return {
    prompt: promptCost,
    promptPct: totalCost > 0 ? (promptCost / totalCost) * 100 : 0,
    completion: completionCost,
    completionPct: totalCost > 0 ? (completionCost / totalCost) * 100 : 0,
    total: totalCost,
    promptTokens: call.prompt_tokens || 0,
    completionTokens: call.completion_tokens || 0,
    totalTokens,
    inputTokenPct: totalTokens > 0 ? (call.prompt_tokens / totalTokens) * 100 : 0,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// ALTERNATIVE MODELS
// ─────────────────────────────────────────────────────────────────────────────

export function getAlternativeModels(call) {
  const currentModel = call.model_name?.toLowerCase() || '';
  const currentTier = getModelTier(currentModel);
  const alternatives = [];
  
  // Always suggest cheaper alternatives
  if (currentTier === 'premium' || currentTier === 'standard') {
    // GPT-4o-mini
    if (!currentModel.includes('gpt-4o-mini')) {
      const estCost = (call.prompt_tokens * 0.00015 + call.completion_tokens * 0.0006) / 1000;
      alternatives.push({
        name: 'gpt-4o-mini',
        estimated_cost: estCost,
        savings_pct: call.total_cost > 0 ? ((call.total_cost - estCost) / call.total_cost) * 100 : 0,
        quality: '~90%',
        tier: 'budget',
      });
    }
    
    // Claude Haiku
    if (!currentModel.includes('haiku')) {
      const estCost = (call.prompt_tokens * 0.00025 + call.completion_tokens * 0.00125) / 1000;
      alternatives.push({
        name: 'claude-3-haiku',
        estimated_cost: estCost,
        savings_pct: call.total_cost > 0 ? ((call.total_cost - estCost) / call.total_cost) * 100 : 0,
        quality: '~85%',
        tier: 'budget',
      });
    }
  }
  
  // Even budget models can suggest alternatives
  if (currentTier === 'budget' && currentModel.includes('gpt')) {
    const estCost = (call.prompt_tokens * 0.00025 + call.completion_tokens * 0.00125) / 1000;
    if (!currentModel.includes('haiku')) {
      alternatives.push({
        name: 'claude-3-haiku',
        estimated_cost: estCost,
        savings_pct: call.total_cost > 0 ? ((call.total_cost - estCost) / call.total_cost) * 100 : 0,
        quality: '~95%',
        tier: 'budget',
      });
    }
  }
  
  return alternatives.sort((a, b) => b.savings_pct - a.savings_pct);
}

// ─────────────────────────────────────────────────────────────────────────────
// FACTOR DETECTION (improved with lower thresholds)
// ─────────────────────────────────────────────────────────────────────────────

export function analyzeCostFactors(call, operationStats = null) {
  const factors = [];
  const modelTier = getModelTier(call.model_name);
  const breakdown = getCostBreakdown(call);
  const totalTokens = breakdown.totalTokens;
  
  // Factor: Premium model usage
  if (modelTier === 'premium') {
    factors.push({
      id: 'premium_model',
      severity: 'warning',
      label: `Premium Model: ${call.model_name}`,
      impact: 'Higher cost per token',
      description: 'Premium models cost significantly more. Consider if this task requires premium capabilities.',
      hasFix: true,
    });
  }
  
  // Factor: High input cost percentage
  if (breakdown.inputTokenPct > THRESHOLDS.high_input_pct) {
    factors.push({
      id: 'high_input_cost',
      severity: 'warning',
      label: `High Input Ratio: ${breakdown.inputTokenPct.toFixed(0)}%`,
      impact: `${breakdown.promptTokens.toLocaleString()} input vs ${breakdown.completionTokens.toLocaleString()} output tokens`,
      description: 'Most tokens are going to input. Consider reducing prompt size.',
      hasFix: true,
    });
  }
  
  // Factor: High output tokens
  if (call.completion_tokens > THRESHOLDS.high_output_tokens) {
    factors.push({
      id: 'high_output_tokens',
      severity: 'info',
      label: `High Output: ${call.completion_tokens.toLocaleString()} tokens`,
      impact: 'Response may be longer than needed',
      description: 'Consider if all output content is necessary. Setting max_tokens can limit cost.',
      hasFix: true,
    });
  }
  
  // Factor: Large prompt
  if (call.prompt_tokens > THRESHOLDS.large_prompt) {
    factors.push({
      id: 'large_prompt',
      severity: 'warning',
      label: `Large Prompt: ${call.prompt_tokens.toLocaleString()} tokens`,
      impact: 'Prompt size driving cost',
      description: 'Consider simplifying system prompt or truncating context.',
      hasFix: true,
    });
  }
  
  // Factor: Above average cost
  if (operationStats?.avg_cost) {
    const ratio = call.total_cost / operationStats.avg_cost;
    if (ratio > THRESHOLDS.above_average_ratio) {
      factors.push({
        id: 'above_average',
        severity: ratio > 1.5 ? 'warning' : 'info',
        label: `${((ratio - 1) * 100).toFixed(0)}% Above Average`,
        impact: `Avg: $${operationStats.avg_cost.toFixed(3)}, This: $${call.total_cost.toFixed(3)}`,
        description: 'This call costs more than typical calls for this operation.',
        hasFix: true,
      });
    }
  }
  
  // Factor: No caching (always a potential optimization)
  if (call.prompt_tokens > 500 && !call.cache_hit) {
    factors.push({
      id: 'caching_opportunity',
      severity: 'info',
      label: 'Caching Opportunity',
      impact: 'Similar prompts could be cached',
      description: 'If this operation has repeated prompts, caching could reduce costs.',
      hasFix: true,
    });
  }
  
  // Factor: High cost (absolute)
  if (call.total_cost > THRESHOLDS.high_cost) {
    factors.push({
      id: 'high_absolute_cost',
      severity: 'warning',
      label: `High Cost: $${call.total_cost.toFixed(3)}`,
      impact: 'Single call cost is elevated',
      description: 'This call is expensive. Review if optimizations are possible.',
      hasFix: true,
    });
  }
  
  // Factor: No max_tokens set
  if ((call.max_tokens === null || call.max_tokens === undefined) && call.completion_tokens > 500) {
    factors.push({
      id: 'no_max_tokens',
      severity: 'info',
      label: 'No Output Limit',
      impact: 'Output length unbounded',
      description: 'Setting max_tokens can prevent unexpectedly long (and costly) responses.',
      hasFix: true,
    });
  }

  // Sort by severity
  const severityOrder = { critical: 0, warning: 1, info: 2, ok: 3 };
  factors.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);

  return factors;
}

// ─────────────────────────────────────────────────────────────────────────────
// FIX DEFINITIONS (more fixes available)
// ─────────────────────────────────────────────────────────────────────────────

export function getCostFixes(call, factors) {
  const fixes = [];
  const breakdown = getCostBreakdown(call);
  const alternatives = getAlternativeModels(call);
  const modelTier = getModelTier(call.model_name);
  
  // Fix 1: Switch to cheaper model (always show if alternatives exist)
  if (alternatives.length > 0) {
    const bestAlt = alternatives[0];
    
    fixes.push({
      id: 'switch_model',
      title: `Switch to ${bestAlt.name}`,
      subtitle: `${bestAlt.savings_pct.toFixed(0)}% cheaper with ${bestAlt.quality} quality`,
      effort: 'Low',
      effortColor: 'text-green-400',
      recommended: modelTier === 'premium',
      
      metrics: [
        {
          label: 'Cost',
          before: `$${call.total_cost.toFixed(3)}`,
          after: `$${bestAlt.estimated_cost.toFixed(4)}`,
          changePercent: -Math.round(bestAlt.savings_pct),
        },
        {
          label: 'Quality',
          before: '100%',
          after: bestAlt.quality,
          changePercent: -parseInt(bestAlt.quality) + 100,
          status: 'warning',
        },
        {
          label: 'Latency',
          before: `${((call.latency_ms || 0) / 1000).toFixed(1)}s`,
          after: 'Faster',
          changePercent: -30,
        },
        {
          label: 'Tokens',
          before: breakdown.totalTokens.toLocaleString(),
          after: 'Same',
          changePercent: 0,
        },
      ],
      
      codeBefore: `response = client.chat.completions.create(
    model="${call.model_name}",
    messages=messages
)`,
      codeAfter: `response = client.chat.completions.create(
    model="${bestAlt.name}",  # ${bestAlt.savings_pct.toFixed(0)}% cheaper
    messages=messages
)`,
      
      tradeoffs: [
        `Quality may reduce to ${bestAlt.quality}`,
        'May need prompt adjustments',
        'Test before production use',
      ],
      benefits: [
        `Save $${(call.total_cost - bestAlt.estimated_cost).toFixed(4)} per call`,
        'Faster response times',
        'Same token capacity',
        'Easy one-line change',
      ],
      bestFor: 'Tasks that don\'t require premium model capabilities',
    });
  }
  
  // Fix 2: Reduce output tokens (if output is high)
  if (call.completion_tokens > 300) {
    const targetTokens = Math.min(500, Math.round(call.completion_tokens * 0.5));
    const tokenSavings = call.completion_tokens - targetTokens;
    const costSavings = tokenSavings * 0.00004; // Rough estimate
    
    fixes.push({
      id: 'reduce_output',
      title: 'Limit Output Length',
      subtitle: `Set max_tokens=${targetTokens} to cap response`,
      effort: 'Low',
      effortColor: 'text-green-400',
      recommended: call.completion_tokens > THRESHOLDS.high_output_tokens,
      
      metrics: [
        {
          label: 'Cost',
          before: `$${call.total_cost.toFixed(3)}`,
          after: `$${(call.total_cost - costSavings).toFixed(3)}`,
          changePercent: -Math.round((costSavings / call.total_cost) * 100),
        },
        {
          label: 'Output',
          before: call.completion_tokens.toLocaleString(),
          after: targetTokens.toLocaleString(),
          changePercent: -Math.round((tokenSavings / call.completion_tokens) * 100),
        },
        {
          label: 'Latency',
          before: `${((call.latency_ms || 0) / 1000).toFixed(1)}s`,
          after: '-30%',
          changePercent: -30,
        },
        {
          label: 'Quality',
          before: '—',
          after: 'Truncated',
          changePercent: 0,
          status: 'warning',
        },
      ],
      
      codeBefore: `response = client.chat.completions.create(
    model="${call.model_name}",
    messages=messages
)`,
      codeAfter: `response = client.chat.completions.create(
    model="${call.model_name}",
    max_tokens=${targetTokens},  # Limit output
    messages=messages
)`,
      
      tradeoffs: [
        'Response may be truncated',
        'May cut off important content',
        'Need to verify completeness',
      ],
      benefits: [
        'Predictable response length',
        'Lower output token cost',
        'Faster response times',
        'Simple one-line change',
      ],
      bestFor: 'Tasks where concise responses are acceptable',
    });
  }
  
  // Fix 3: Simplify prompt (if prompt is large)
  if (call.prompt_tokens > 500) {
    const targetPrompt = Math.round(call.prompt_tokens * 0.5);
    const tokenSavings = call.prompt_tokens - targetPrompt;
    const costSavings = tokenSavings * 0.000015; // Rough estimate for input
    
    fixes.push({
      id: 'simplify_prompt',
      title: 'Simplify System Prompt',
      subtitle: `Reduce prompt from ${call.prompt_tokens.toLocaleString()} to ~${targetPrompt.toLocaleString()} tokens`,
      effort: 'Medium',
      effortColor: 'text-yellow-400',
      recommended: call.prompt_tokens > THRESHOLDS.large_prompt,
      
      metrics: [
        {
          label: 'Cost',
          before: `$${call.total_cost.toFixed(3)}`,
          after: `$${(call.total_cost - costSavings).toFixed(3)}`,
          changePercent: -Math.round((costSavings / call.total_cost) * 100),
        },
        {
          label: 'Prompt',
          before: call.prompt_tokens.toLocaleString(),
          after: `~${targetPrompt.toLocaleString()}`,
          changePercent: -50,
        },
        {
          label: 'Latency',
          before: `${((call.latency_ms || 0) / 1000).toFixed(1)}s`,
          after: '-20%',
          changePercent: -20,
        },
        {
          label: 'Quality',
          before: '—',
          after: 'May vary',
          changePercent: 0,
          status: 'warning',
        },
      ],
      
      codeBefore: `system_prompt = """
You are an expert analyst with decades of experience.

DETAILED INSTRUCTIONS:
1. First, carefully review all materials...
2. Then, analyze each criterion...
3. Finally, provide comprehensive recommendations...
[... ${call.prompt_tokens} tokens of instructions ...]
"""`,
      codeAfter: `system_prompt = """
You are an expert analyst.

Analyze the provided materials and give:
1. Key findings
2. Concerns
3. Recommendation

Be specific and concise.
"""`,
      
      tradeoffs: [
        'May lose detailed instructions',
        'Requires testing',
        'Could affect edge cases',
      ],
      benefits: [
        `Save ~$${costSavings.toFixed(4)} per call`,
        'Faster processing',
        'Easier to maintain',
        'Often improves focus',
      ],
      bestFor: 'Prompts that have grown complex over time',
    });
  }
  
  // Fix 4: Enable caching
  if (factors.some(f => f.id === 'caching_opportunity') || call.prompt_tokens > 500) {
    fixes.push({
      id: 'enable_caching',
      title: 'Enable Response Caching',
      subtitle: 'Cache identical prompts to avoid repeat calls',
      effort: 'Medium',
      effortColor: 'text-yellow-400',
      
      metrics: [
        {
          label: 'Cost',
          before: `$${call.total_cost.toFixed(3)}`,
          after: '$0 (hit)',
          changePercent: -100,
        },
        {
          label: 'Latency',
          before: `${((call.latency_ms || 0) / 1000).toFixed(1)}s`,
          after: '<50ms',
          changePercent: -99,
        },
        {
          label: 'Tokens',
          before: breakdown.totalTokens.toLocaleString(),
          after: '0 (hit)',
          changePercent: -100,
        },
        {
          label: 'Quality',
          before: '—',
          after: 'Same',
          changePercent: 0,
        },
      ],
      
      codeBefore: `response = client.chat.completions.create(
    model="${call.model_name}",
    messages=messages
)`,
      codeAfter: `from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def cached_completion(prompt_hash):
    return client.chat.completions.create(
        model="${call.model_name}",
        messages=messages
    )

# Hash the prompt for cache key
cache_key = hashlib.md5(str(messages).encode()).hexdigest()
response = cached_completion(cache_key)`,
      
      tradeoffs: [
        'Memory usage for cache',
        'Cache invalidation complexity',
        'Only helps with repeated prompts',
      ],
      benefits: [
        'Zero cost for cache hits',
        'Instant responses',
        'Reduces API rate limit usage',
        'Great for repeated queries',
      ],
      bestFor: 'Operations with repeated identical prompts',
    });
  }

  return fixes.slice(0, 4); // Max 4 fixes
}

// ─────────────────────────────────────────────────────────────────────────────
// CONFIG HIGHLIGHTS
// ─────────────────────────────────────────────────────────────────────────────

export function getCostConfigHighlights(call, factors) {
  const highlights = [];
  const modelTier = getModelTier(call.model_name);

  if (modelTier === 'premium') {
    highlights.push({
      key: 'model',
      message: 'PREMIUM',
      severity: 'warning',
    });
  }

  if (call.total_cost > THRESHOLDS.high_cost) {
    highlights.push({
      key: 'cost',
      message: 'HIGH COST',
      severity: 'warning',
    });
  }

  return highlights;
}

// ─────────────────────────────────────────────────────────────────────────────
// SIMILAR PANEL CONFIG
// ─────────────────────────────────────────────────────────────────────────────

export const COST_SIMILAR_CONFIG = {
  filterOptions: [
    { id: 'same_operation', label: 'Same Operation' },
    { id: 'expensive', label: 'Most Expensive' },
    { id: 'cheapest', label: 'Cheapest' },
  ],
  defaultFilter: 'same_operation',
  
  columns: [
    { key: 'call_id', label: 'Call ID', format: (v) => v?.substring(0, 8) + '...' },
    { key: 'model_name', label: 'Model', format: (v) => v?.split('/').pop() },
    { key: 'total_cost', label: 'Cost', format: (v) => `$${v?.toFixed(3)}` },
    { key: 'prompt_tokens', label: 'Input', format: (v) => v?.toLocaleString() },
    { key: 'completion_tokens', label: 'Output', format: (v) => v?.toLocaleString() },
  ],
};