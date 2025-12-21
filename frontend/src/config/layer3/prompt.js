/**
 * Prompt Composition Story - Layer 3 Configuration
 * Location: src/config/layer3/prompt.js
 * 
 * Defines:
 * - KPI definitions
 * - Factor detection rules
 * - Fix templates with full details (metrics, code, tradeoffs, benefits)
 * - Breakdown analysis functions
 */

// ─────────────────────────────────────────────────────────────────────────────
// STORY METADATA
// ─────────────────────────────────────────────────────────────────────────────

export const PROMPT_STORY = {
  id: 'system_prompt',
  label: 'Prompt Composition',
  icon: '📝',
  color: '#06b6d4', // cyan-500
  entityType: 'call',
};

// ─────────────────────────────────────────────────────────────────────────────
// THRESHOLDS
// ─────────────────────────────────────────────────────────────────────────────

const THRESHOLDS = {
  history_pct_warning: 40,
  history_pct_critical: 60,
  system_pct_high: 70,
  history_tokens_large: 500,
  history_tokens_very_large: 1000,
  variability_low: 5,    // <5% = static
  variability_high: 20,  // >20% = dynamic
};

// ─────────────────────────────────────────────────────────────────────────────
// HELPER FUNCTIONS
// ─────────────────────────────────────────────────────────────────────────────

function getCacheStatusInfo(status) {
  const statusMap = {
    ready: { emoji: '✅', label: 'Cache Ready', color: 'text-green-400', status: 'good' },
    partial: { emoji: '⚠️', label: 'Partial', color: 'text-yellow-400', status: 'warning' },
    not_ready: { emoji: '❌', label: 'Not Ready', color: 'text-red-400', status: 'critical' },
    none: { emoji: '➖', label: 'No System', color: 'text-gray-400', status: 'neutral' },
  };
  return statusMap[status] || statusMap.none;
}

function getHistoryStatus(historyPct, historyTokens) {
  if (historyPct > THRESHOLDS.history_pct_critical || historyTokens > THRESHOLDS.history_tokens_very_large) {
    return { status: 'critical', label: 'Excessive' };
  }
  if (historyPct > THRESHOLDS.history_pct_warning || historyTokens > THRESHOLDS.history_tokens_large) {
    return { status: 'warning', label: 'Large' };
  }
  if (historyTokens > 0) {
    return { status: 'good', label: 'Normal' };
  }
  return { status: 'neutral', label: 'None' };
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI DEFINITIONS
// ─────────────────────────────────────────────────────────────────────────────

export function getPromptKPIs(call, operationStats = null) {
  const systemTokens = call.system_prompt_tokens || 0;
  const userTokens = call.user_message_tokens || 0;
  const historyTokens = call.chat_history_tokens || 0;
  const promptTokens = call.prompt_tokens || (systemTokens + userTokens + historyTokens);
  
  const systemPct = call.system_pct || (promptTokens > 0 ? (systemTokens / promptTokens) * 100 : 0);
  const userPct = call.user_pct || (promptTokens > 0 ? (userTokens / promptTokens) * 100 : 0);
  const historyPct = call.history_pct || (promptTokens > 0 ? (historyTokens / promptTokens) * 100 : 0);
  
  const cacheStatus = call.cache_status || 'none';
  const cacheInfo = getCacheStatusInfo(cacheStatus);
  const historyStatus = getHistoryStatus(historyPct, historyTokens);

  return [
    {
      label: 'System Prompt',
      value: systemTokens.toLocaleString(),
      subtext: `${systemPct.toFixed(0)}% of prompt`,
      status: systemPct > THRESHOLDS.system_pct_high ? 'warning' : 'good',
      primary: true,
    },
    {
      label: 'User Message',
      value: userTokens.toLocaleString(),
      subtext: `${userPct.toFixed(0)}% of prompt`,
      status: 'neutral',
    },
    {
      label: 'Chat History',
      value: historyTokens.toLocaleString(),
      subtext: `${historyPct.toFixed(0)}% of prompt`,
      status: historyStatus.status,
    },
    {
      label: 'Total Prompt',
      value: promptTokens.toLocaleString(),
      subtext: 'tokens',
      status: 'neutral',
    },
    {
      label: 'Cache Status',
      value: `${cacheInfo.emoji} ${cacheInfo.label}`,
      subtext: call.cache_label || cacheInfo.label,
      status: cacheInfo.status,
    },
  ];
}

// ─────────────────────────────────────────────────────────────────────────────
// CURRENT STATE (for comparison table)
// ─────────────────────────────────────────────────────────────────────────────

export function getPromptCurrentState(call) {
  const historyTokens = call.chat_history_tokens || 0;
  const promptTokens = call.prompt_tokens || 0;
  const cacheInfo = getCacheStatusInfo(call.cache_status || 'none');
  
  return {
    history: historyTokens.toLocaleString(),
    prompt: promptTokens.toLocaleString(),
    cost: `$${(call.total_cost || 0).toFixed(3)}`,
    cache: `${cacheInfo.emoji} ${cacheInfo.label}`,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// FACTOR DETECTION
// ─────────────────────────────────────────────────────────────────────────────

export function analyzePromptFactors(call) {
  const factors = [];
  
  const systemTokens = call.system_prompt_tokens || 0;
  const historyTokens = call.chat_history_tokens || 0;
  const promptTokens = call.prompt_tokens || 0;
  
  const systemPct = call.system_pct || (promptTokens > 0 ? (systemTokens / promptTokens) * 100 : 0);
  const historyPct = call.history_pct || (promptTokens > 0 ? (historyTokens / promptTokens) * 100 : 0);
  
  const cacheStatus = call.cache_status || 'none';
  const cacheAnalysis = call.cache_analysis || {};
  const variability = cacheAnalysis.system_prompt_variability || 0;

  // Factor: Excessive chat history
  if (historyPct > THRESHOLDS.history_pct_critical) {
    factors.push({
      id: 'excessive_history',
      severity: 'critical',
      label: `Excessive Chat History: ${historyPct.toFixed(0)}%`,
      impact: 'Majority of prompt is history, blocking caching',
      description: `Chat history uses ${historyTokens.toLocaleString()} tokens (${historyPct.toFixed(0)}% of prompt). This significantly increases cost and prevents effective caching.`,
      hasFix: true,
    });
  } else if (historyPct > THRESHOLDS.history_pct_warning) {
    factors.push({
      id: 'large_history',
      severity: 'warning',
      label: `Large Chat History: ${historyPct.toFixed(0)}%`,
      impact: 'History growing, consider summarization',
      description: `Chat history uses ${historyTokens.toLocaleString()} tokens (${historyPct.toFixed(0)}% of prompt). Consider truncating or summarizing older messages.`,
      hasFix: true,
    });
  }

  // Factor: Not cache ready
  if (cacheStatus === 'not_ready') {
    factors.push({
      id: 'not_cache_ready',
      severity: 'warning',
      label: 'Not Cache Ready',
      impact: 'Cannot use prompt caching for cost savings',
      description: call.cache_issue_reason || 'Prompt structure prevents effective caching.',
      hasFix: true,
    });
  } else if (cacheStatus === 'partial') {
    factors.push({
      id: 'partial_cache_ready',
      severity: 'info',
      label: 'Partial Cache Ready',
      impact: 'System prompt cacheable but history varies',
      description: call.cache_issue_reason || 'System prompt is static but chat history prevents full caching.',
      hasFix: true,
    });
  }

  // Factor: Dynamic system prompt
  if (variability > THRESHOLDS.variability_high) {
    factors.push({
      id: 'dynamic_system_prompt',
      severity: 'warning',
      label: `Dynamic System Prompt: ${variability.toFixed(0)}% variability`,
      impact: 'System prompt changes between calls',
      description: 'Dynamic content in system prompt prevents caching. Move variables to user message.',
      hasFix: true,
    });
  }

  // Factor: No system prompt
  if (systemTokens === 0) {
    factors.push({
      id: 'no_system_prompt',
      severity: 'info',
      label: 'No System Prompt',
      impact: 'Missing opportunity for consistent behavior',
      description: 'Adding a system prompt can improve response consistency and enable caching.',
      hasFix: false,
    });
  }

  // Factor: Bloated system prompt
  if (systemPct > THRESHOLDS.system_pct_high && systemTokens > 1000) {
    factors.push({
      id: 'bloated_system_prompt',
      severity: 'info',
      label: `Large System Prompt: ${systemPct.toFixed(0)}%`,
      impact: 'System prompt dominates input tokens',
      description: `System prompt uses ${systemTokens.toLocaleString()} tokens. Consider compressing or moving examples to few-shot messages.`,
      hasFix: true,
    });
  }

  // Factor: Very large history tokens
  if (historyTokens > THRESHOLDS.history_tokens_very_large && historyPct <= THRESHOLDS.history_pct_warning) {
    factors.push({
      id: 'high_history_tokens',
      severity: 'info',
      label: `${historyTokens.toLocaleString()} History Tokens`,
      impact: 'Absolute token count is high',
      description: 'Even though percentage is reasonable, absolute token count adds cost.',
      hasFix: true,
    });
  }

  // Sort by severity
  const severityOrder = { critical: 0, warning: 1, info: 2, ok: 3 };
  factors.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);

  return factors;
}

// ─────────────────────────────────────────────────────────────────────────────
// COMPOSITION BREAKDOWN
// ─────────────────────────────────────────────────────────────────────────────

export function getPromptComposition(call) {
  const systemTokens = call.system_prompt_tokens || 0;
  const userTokens = call.user_message_tokens || 0;
  const historyTokens = call.chat_history_tokens || 0;
  const promptTokens = call.prompt_tokens || (systemTokens + userTokens + historyTokens);
  
  const systemPct = promptTokens > 0 ? (systemTokens / promptTokens) * 100 : 0;
  const userPct = promptTokens > 0 ? (userTokens / promptTokens) * 100 : 0;
  const historyPct = promptTokens > 0 ? (historyTokens / promptTokens) * 100 : 0;

  return {
    components: [
      {
        id: 'system',
        label: 'System Prompt',
        tokens: systemTokens,
        percentage: systemPct,
        color: '#8b5cf6', // purple
        bgClass: 'bg-purple-500',
        textClass: 'text-purple-400',
      },
      {
        id: 'user',
        label: 'User Message',
        tokens: userTokens,
        percentage: userPct,
        color: '#22c55e', // green
        bgClass: 'bg-green-500',
        textClass: 'text-green-400',
      },
      {
        id: 'history',
        label: 'Chat History',
        tokens: historyTokens,
        percentage: historyPct,
        color: '#f97316', // orange
        bgClass: 'bg-orange-500',
        textClass: 'text-orange-400',
      },
    ],
    total: promptTokens,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// CACHE ANALYSIS
// ─────────────────────────────────────────────────────────────────────────────

export function getCacheReadinessAnalysis(call) {
  const cacheStatus = call.cache_status || 'none';
  const cacheAnalysis = call.cache_analysis || {};
  const cacheInfo = getCacheStatusInfo(cacheStatus);
  
  return {
    status: cacheStatus,
    emoji: cacheInfo.emoji,
    label: cacheInfo.label,
    color: cacheInfo.color,
    statusClass: cacheInfo.status,
    issueReason: call.cache_issue_reason,
    recommendation: cacheAnalysis.cache_recommendation,
    details: {
      systemStatic: cacheAnalysis.system_prompt_static,
      variability: cacheAnalysis.system_prompt_variability,
      historyPresent: cacheAnalysis.history_present,
      historyTokens: cacheAnalysis.history_tokens,
      historyMessages: cacheAnalysis.history_messages,
      potentialSavings: cacheAnalysis.potential_cache_savings,
    },
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// COMPONENT ANALYSIS (for Diagnose tab)
// ─────────────────────────────────────────────────────────────────────────────

export function getComponentAnalysis(call) {
  const systemTokens = call.system_prompt_tokens || 0;
  const userTokens = call.user_message_tokens || 0;
  const historyTokens = call.chat_history_tokens || 0;
  const cacheAnalysis = call.cache_analysis || {};
  const variability = cacheAnalysis.system_prompt_variability || 0;

  const components = [];

  // System Prompt
  if (systemTokens > 0) {
    const isStatic = variability <= THRESHOLDS.variability_low;
    components.push({
      id: 'system',
      label: 'System Prompt',
      tokens: systemTokens,
      status: isStatic ? 'good' : 'warning',
      emoji: isStatic ? '✅' : '⚠️',
      statusLabel: isStatic ? 'Static' : 'Dynamic',
      description: isStatic 
        ? 'Static content with low variability. Ideal for prompt caching.'
        : `High variability (${variability.toFixed(0)}%). Contains dynamic content.`,
      color: 'purple',
    });
  }

  // User Message
  components.push({
    id: 'user',
    label: 'User Message',
    tokens: userTokens,
    status: 'good',
    emoji: '✅',
    statusLabel: 'Dynamic (expected)',
    description: 'Dynamic content containing the current request.',
    color: 'green',
  });

  // Chat History
  if (historyTokens > 0) {
    const historyStatus = getHistoryStatus(
      (historyTokens / (call.prompt_tokens || 1)) * 100,
      historyTokens
    );
    components.push({
      id: 'history',
      label: 'Chat History',
      tokens: historyTokens,
      status: historyStatus.status,
      emoji: historyStatus.status === 'good' ? '✅' : '⚠️',
      statusLabel: historyStatus.label,
      description: historyStatus.status === 'good'
        ? 'Reasonable history size for context.'
        : `${cacheAnalysis.history_messages || 0} messages using ${historyTokens.toLocaleString()} tokens. Consider summarizing.`,
      color: 'orange',
    });
  }

  return components;
}

// ─────────────────────────────────────────────────────────────────────────────
// TOKEN METRICS (for Breakdown tab)
// ─────────────────────────────────────────────────────────────────────────────

export function getTokenMetrics(call) {
  const promptTokens = call.prompt_tokens || 0;
  const completionTokens = call.completion_tokens || 0;
  const totalTokens = promptTokens + completionTokens;
  const ratio = completionTokens > 0 ? (promptTokens / completionTokens).toFixed(1) : '—';

  return [
    { label: 'Prompt Tokens', value: promptTokens.toLocaleString() },
    { label: 'Completion Tokens', value: completionTokens.toLocaleString() },
    { label: 'Total Tokens', value: totalTokens.toLocaleString() },
    { label: 'I/O Ratio', value: `${ratio}:1` },
  ];
}

// ─────────────────────────────────────────────────────────────────────────────
// COST BREAKDOWN (for Breakdown tab)
// ─────────────────────────────────────────────────────────────────────────────

export function getCostBreakdown(call) {
  const promptCost = call.prompt_cost || (call.prompt_tokens || 0) * 0.0000025;
  const completionCost = call.completion_cost || (call.completion_tokens || 0) * 0.00001;
  const historyCost = (call.chat_history_tokens || 0) * 0.0000025;
  const totalCost = call.total_cost || (promptCost + completionCost);

  return [
    { label: 'Input Cost', value: `$${promptCost.toFixed(4)}` },
    { label: 'Output Cost', value: `$${completionCost.toFixed(4)}` },
    { label: 'Total Cost', value: `$${totalCost.toFixed(4)}` },
    { 
      label: 'History Cost', 
      value: `$${historyCost.toFixed(4)}`,
      highlight: historyCost > 0.001,
      color: 'text-yellow-400',
    },
  ];
}

// ─────────────────────────────────────────────────────────────────────────────
// FIX DEFINITIONS
// ─────────────────────────────────────────────────────────────────────────────

export function getPromptFixes(call, factors) {
  const fixes = [];
  const historyTokens = call.chat_history_tokens || 0;
  const promptTokens = call.prompt_tokens || 0;
  const historyPct = promptTokens > 0 ? (historyTokens / promptTokens) * 100 : 0;
  const cacheAnalysis = call.cache_analysis || {};
  const historyMessages = cacheAnalysis.history_messages || 0;

  // Estimated values after fixes
  const summarizedHistoryTokens = Math.min(300, historyTokens * 0.25);
  const truncatedHistoryTokens = Math.min(historyTokens, 650);
  
  // Fix 1: Summarize Chat History (recommended for large history)
  if (factors.some(f => f.id === 'large_history' || f.id === 'excessive_history' || f.id === 'partial_cache_ready')) {
    const newPromptTokens = promptTokens - historyTokens + summarizedHistoryTokens;
    const costReduction = ((promptTokens - newPromptTokens) / promptTokens * 100).toFixed(0);
    
    fixes.push({
      id: 'summarize_history',
      title: 'Summarize Chat History',
      subtitle: 'Replace history with AI-generated summary',
      effort: 'Medium',
      effortColor: 'text-yellow-400',
      recommended: historyPct > 40,
      
      metrics: [
        {
          label: 'History',
          before: historyTokens.toLocaleString(),
          after: `~${summarizedHistoryTokens.toLocaleString()}`,
          changePercent: -Math.round((1 - summarizedHistoryTokens / historyTokens) * 100),
        },
        {
          label: 'Prompt',
          before: promptTokens.toLocaleString(),
          after: `~${newPromptTokens.toLocaleString()}`,
          changePercent: -Math.round((1 - newPromptTokens / promptTokens) * 100),
        },
        {
          label: 'Cost',
          before: `$${(call.total_cost || 0).toFixed(3)}`,
          after: `~$${((call.total_cost || 0) * (newPromptTokens / promptTokens)).toFixed(3)}`,
          changePercent: -parseInt(costReduction),
        },
        {
          label: 'Cache',
          before: '⚠️ Partial',
          after: '✅ Ready',
          changePercent: null,
          isStatus: true,
        },
      ],
      
      codeBefore: `messages = [
    {"role": "system", "content": system_prompt},
    *chat_history,  # ${historyMessages} messages, ${historyTokens.toLocaleString()} tokens
    {"role": "user", "content": user_message}
]`,
      codeAfter: `# Summarize older history, keep recent exchanges
def summarize_history(history, keep_last=2):
    if len(history) <= keep_last * 2:
        return history
    
    older = history[:-keep_last * 2]
    recent = history[-keep_last * 2:]
    
    summary = llm.summarize(older)  # ~50-100 tokens
    return [{"role": "system", "content": f"Previous context: {summary}"}] + recent

messages = [
    {"role": "system", "content": system_prompt},
    *summarize_history(chat_history),  # ~${summarizedHistoryTokens} tokens
    {"role": "user", "content": user_message}
]`,

      outputBefore: `{
  "analysis": "Based on our previous discussion about Python skills...",
  "context_used": "Full 8-message history referenced",
  "tokens": ${call.completion_tokens || 500}
}`,
      outputAfter: `{
  "analysis": "Based on our previous discussion about Python skills...",
  "context_used": "Summary + last 2 exchanges referenced", 
  "tokens": ${call.completion_tokens || 500}
}
// ✅ Same quality output with summarized context`,
      
      tradeoffs: [
        'Requires additional LLM call to summarize',
        'May lose nuanced details from older messages',
        'Slight latency increase for summarization',
        'More complex implementation',
      ],
      benefits: [
        'Dramatically reduces history tokens (75%+)',
        'Enables effective prompt caching',
        'Maintains conversation continuity',
        'Scales to any conversation length',
        'Lower per-call cost',
      ],
      bestFor: 'Long-running conversations where context matters',
    });
  }

  // Fix 2: Truncate History (simpler approach)
  if (factors.some(f => f.id === 'large_history' || f.id === 'excessive_history' || f.id === 'high_history_tokens')) {
    const newPromptTokens = promptTokens - historyTokens + truncatedHistoryTokens;
    const costReduction = ((promptTokens - newPromptTokens) / promptTokens * 100).toFixed(0);
    const keepMessages = Math.min(4, historyMessages);
    
    fixes.push({
      id: 'truncate_history',
      title: 'Truncate History',
      subtitle: 'Keep only the last N messages',
      effort: 'Low',
      effortColor: 'text-green-400',
      recommended: false,
      
      metrics: [
        {
          label: 'History',
          before: historyTokens.toLocaleString(),
          after: `~${truncatedHistoryTokens.toLocaleString()}`,
          changePercent: -Math.round((1 - truncatedHistoryTokens / historyTokens) * 100),
        },
        {
          label: 'Prompt',
          before: promptTokens.toLocaleString(),
          after: `~${newPromptTokens.toLocaleString()}`,
          changePercent: -Math.round((1 - newPromptTokens / promptTokens) * 100),
        },
        {
          label: 'Cost',
          before: `$${(call.total_cost || 0).toFixed(3)}`,
          after: `~$${((call.total_cost || 0) * (newPromptTokens / promptTokens)).toFixed(3)}`,
          changePercent: -parseInt(costReduction),
        },
        {
          label: 'Cache',
          before: '⚠️ Partial',
          after: '⚠️ Partial',
          changePercent: null,
          isStatus: true,
        },
      ],
      
      codeBefore: `messages = [
    {"role": "system", "content": system_prompt},
    *chat_history,  # All ${historyMessages} messages
    {"role": "user", "content": user_message}
]`,
      codeAfter: `MAX_HISTORY_MESSAGES = ${keepMessages}

messages = [
    {"role": "system", "content": system_prompt},
    *chat_history[-MAX_HISTORY_MESSAGES:],  # Last ${keepMessages} only
    {"role": "user", "content": user_message}
]`,

      outputBefore: null,  // Same output expected
      outputAfter: null,
      outputNote: '✅ Same output quality for most use cases',
      
      tradeoffs: [
        'Loses context from older messages',
        'May miss important earlier details',
        'Still has variable history (partial cache only)',
        'Could affect multi-turn reasoning',
      ],
      benefits: [
        'One line code change',
        'Immediate token reduction',
        'No additional API calls',
        'Predictable prompt size',
        'Simple to implement',
      ],
      bestFor: 'Quick fix when older context is not critical',
    });
  }

  // Fix 3: Enable Prompt Caching
  if (factors.some(f => f.id === 'partial_cache_ready' || f.id === 'not_cache_ready') || call.system_prompt_tokens > 500) {
    const systemTokens = call.system_prompt_tokens || 0;
    const cacheSavings = systemTokens * 0.5 * 0.0000025; // 50% savings on cached portion
    
    fixes.push({
      id: 'enable_caching',
      title: 'Enable Prompt Caching',
      subtitle: 'Cache static system prompt for repeat calls',
      effort: 'Low',
      effortColor: 'text-green-400',
      recommended: call.cache_status === 'ready' || (call.cache_status === 'partial' && systemTokens > 500),
      
      metrics: [
        {
          label: 'System',
          before: `${systemTokens.toLocaleString()}`,
          after: 'Cached',
          changePercent: null,
          isStatus: true,
        },
        {
          label: 'Input Cost',
          before: `$${((call.prompt_cost || 0)).toFixed(4)}`,
          after: `~$${((call.prompt_cost || 0) - cacheSavings).toFixed(4)}`,
          changePercent: -Math.round((cacheSavings / (call.prompt_cost || 0.001)) * 100),
        },
        {
          label: 'Latency',
          before: `${((call.latency_ms || 0) / 1000).toFixed(1)}s`,
          after: 'Faster',
          changePercent: -10,
        },
        {
          label: 'Cache',
          before: call.cache_status === 'ready' ? '✅ Ready' : '⚠️ Partial',
          after: '✅ Active',
          changePercent: null,
          isStatus: true,
        },
      ],
      
      codeBefore: `response = client.chat.completions.create(
    model="${call.model_name || 'gpt-4o'}",
    messages=messages
)`,
      codeAfter: `response = client.chat.completions.create(
    model="${call.model_name || 'gpt-4o'}",
    messages=messages,
    # Enable prompt caching for static content
    extra_body={
        "cache": {"type": "ephemeral"}  # OpenAI
        # OR for Anthropic:
        # "cache_control": {"type": "ephemeral"}
    }
)`,

      outputBefore: null,
      outputAfter: null,
      outputNote: '✅ Identical output, lower cost on subsequent calls',
      
      tradeoffs: [
        'Only benefits repeated calls',
        'Requires static system prompt',
        'Provider-specific implementation',
        'May have minimum token requirements',
      ],
      benefits: [
        'Up to 50% cost reduction on cached portion',
        'Faster response times',
        'No quality impact',
        'Automatic for qualifying prompts',
        'Minimal code change',
      ],
      bestFor: 'High-volume operations with consistent system prompts',
    });
  }

  // Fix 4: Extract Dynamic Content (for dynamic system prompts)
  if (factors.some(f => f.id === 'dynamic_system_prompt')) {
    fixes.push({
      id: 'extract_dynamic',
      title: 'Extract Dynamic Content',
      subtitle: 'Move variables from system to user message',
      effort: 'High',
      effortColor: 'text-red-400',
      recommended: false,
      
      metrics: [
        {
          label: 'System',
          before: 'Dynamic',
          after: 'Static',
          changePercent: null,
          isStatus: true,
        },
        {
          label: 'Variability',
          before: `${(cacheAnalysis.system_prompt_variability || 0).toFixed(0)}%`,
          after: '<5%',
          changePercent: -80,
        },
        {
          label: 'Cache',
          before: '❌ Not Ready',
          after: '✅ Ready',
          changePercent: null,
          isStatus: true,
        },
        {
          label: 'Effort',
          before: '—',
          after: 'Refactor',
          changePercent: null,
          isStatus: true,
        },
      ],
      
      codeBefore: `system_prompt = f"""
You are analyzing a resume for {job_title} position.
Company: {company_name}
Requirements: {requirements}
Focus on: {focus_areas}
"""

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": resume_text}
]`,
      codeAfter: `# Static system prompt (cacheable)
system_prompt = """
You are a resume analyst. Analyze the candidate based on 
the job requirements provided in the user message.

Always structure your response with:
1. Skills Match
2. Experience Analysis  
3. Recommendation
"""

# Dynamic content moves to user message
user_message = f"""
Job: {job_title} at {company_name}
Requirements: {requirements}
Focus: {focus_areas}

Resume:
{resume_text}
"""

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_message}
]`,

      outputBefore: null,
      outputAfter: null,
      outputNote: '✅ Same output, now with cacheable system prompt',
      
      tradeoffs: [
        'Requires prompt restructuring',
        'More complex user messages',
        'May need prompt engineering iteration',
        'Higher implementation effort',
      ],
      benefits: [
        'Enables prompt caching',
        'More consistent model behavior',
        'Cleaner separation of concerns',
        'Better for A/B testing prompts',
        'Long-term cost savings',
      ],
      bestFor: 'Optimizing frequently-called operations with templates',
    });
  }

  return fixes;
}

// ─────────────────────────────────────────────────────────────────────────────
// CONFIG HIGHLIGHTS (for Attribute panel)
// ─────────────────────────────────────────────────────────────────────────────

export function getPromptConfigHighlights(call, factors) {
  const highlights = [];
  const cacheAnalysis = call.cache_analysis || {};
  
  // Cache status highlight
  if (call.cache_status === 'ready') {
    highlights.push({
      icon: '✅',
      label: 'Cache Ready',
      description: 'System prompt is static and cacheable',
      status: 'good',
    });
  } else if (call.cache_status === 'partial') {
    highlights.push({
      icon: '⚠️',
      label: 'Partial Cache',
      description: 'System cacheable, history varies',
      status: 'warning',
    });
  } else if (call.cache_status === 'not_ready') {
    highlights.push({
      icon: '❌',
      label: 'Not Cacheable',
      description: call.cache_issue_reason || 'Dynamic content prevents caching',
      status: 'critical',
    });
  }
  
  // History messages
  if (cacheAnalysis.history_messages > 0) {
    highlights.push({
      icon: '💬',
      label: `${cacheAnalysis.history_messages} Messages`,
      description: 'In conversation history',
      status: cacheAnalysis.history_messages > 6 ? 'warning' : 'neutral',
    });
  }

  // Potential savings
  if (cacheAnalysis.potential_cache_savings > 0.1) {
    highlights.push({
      icon: '💰',
      label: `${(cacheAnalysis.potential_cache_savings * 100).toFixed(0)}% Savable`,
      description: 'Potential cost reduction with optimization',
      status: 'info',
    });
  }

  return highlights;
}

// ─────────────────────────────────────────────────────────────────────────────
// RAW PANEL CONFIG
// ─────────────────────────────────────────────────────────────────────────────

export const PROMPT_RAW_CONFIG = {
  sections: [
    'systemPrompt',
    'userMessage', 
    'response',
    'chatHistory',
    'cacheAnalysis',
    'fullData',
  ],
  defaultExpanded: ['cacheAnalysis'],
  highlights: ['cacheAnalysis'],
};

// ─────────────────────────────────────────────────────────────────────────────
// SIMILAR PANEL CONFIG
// ─────────────────────────────────────────────────────────────────────────────

export const PROMPT_SIMILAR_CONFIG = {
  columns: [
    { key: 'call_id', label: 'Call ID', format: (v) => v?.substring(0, 8) + '...' },
    { key: 'timestamp', label: 'Timestamp' },
    { key: 'system_prompt_tokens', label: 'System', format: (v) => v?.toLocaleString() || '0' },
    { key: 'chat_history_tokens', label: 'History', format: (v) => v?.toLocaleString() || '0' },
    { key: 'cache_status', label: 'Cache', format: (v) => getCacheStatusInfo(v).emoji },
  ],
  groupOptions: [
    { id: 'operation', label: 'Same Operation', filterFn: null },
    { id: 'cache_issue', label: 'Cache Issues', filterFn: (items) => items.filter(i => i.cache_status !== 'ready') },
    { id: 'large_history', label: 'Large History', filterFn: (items) => items.filter(i => (i.chat_history_tokens || 0) > 500) },
  ],
  issueKey: 'cache_status',
  issueCheck: (item) => item.cache_status !== 'ready',
  issueLabel: 'Not Cached',
  okLabel: 'Ready',
};