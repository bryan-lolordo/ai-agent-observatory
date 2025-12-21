/**
 * Token Imbalance Story - Layer 3 Configuration
 * 
 * Defines:
 * - KPI definitions
 * - Factor detection rules (ratio analysis)
 * - Fix templates with full details
 * - Token breakdown analysis
 * 
 * FIXED:
 * - Color typo (was ##eab308, now #eab308)
 * - Added moderate ratio detection (5:1+)
 * - Lowered thresholds for better factor detection
 * - Added more factor types
 */

// ─────────────────────────────────────────────────────────────────────────────
// STORY METADATA
// ─────────────────────────────────────────────────────────────────────────────

export const TOKEN_STORY = {
  id: 'token_imbalance',
  label: 'Token Efficiency',
  icon: '⚖️',
  color: '#eab308', // Yellow - FIXED (was ##eab308)
  entityType: 'call',
};

// ─────────────────────────────────────────────────────────────────────────────
// THRESHOLDS (lowered for better detection)
// ─────────────────────────────────────────────────────────────────────────────

const THRESHOLDS = {
  ratio_severe: 15,      // >15:1 is severe (was 20)
  ratio_high: 8,         // >8:1 is high (was 10)
  ratio_moderate: 4,     // >4:1 is moderate (was 5)
  system_prompt_pct: 50, // System prompt > 50% of input (was 60)
  system_prompt_tokens: 500, // System prompt > 500 tokens
  history_pct: 30,       // History > 30% of input (was 40)
  low_output_tokens: 150, // Output < 150 tokens is low
  high_input_cost_pct: 80, // Input > 80% of cost
};

// ─────────────────────────────────────────────────────────────────────────────
// HELPER FUNCTIONS
// ─────────────────────────────────────────────────────────────────────────────

function calculateRatio(promptTokens, completionTokens) {
  if (!completionTokens || completionTokens === 0) return Infinity;
  return promptTokens / completionTokens;
}

function getRatioStatus(ratio) {
  if (ratio > THRESHOLDS.ratio_severe) {
    return { status: 'severe', emoji: '🔴', label: 'Severe Imbalance', color: 'text-red-400' };
  }
  if (ratio > THRESHOLDS.ratio_high) {
    return { status: 'high', emoji: '🔴', label: 'High Imbalance', color: 'text-red-400' };
  }
  if (ratio > THRESHOLDS.ratio_moderate) {
    return { status: 'moderate', emoji: '🟡', label: 'Moderate', color: 'text-yellow-400' };
  }
  return { status: 'balanced', emoji: '🟢', label: 'Balanced', color: 'text-green-400' };
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI DEFINITIONS
// ─────────────────────────────────────────────────────────────────────────────

export function getTokenKPIs(call, operationStats = null) {
  const ratio = calculateRatio(call.prompt_tokens, call.completion_tokens);
  const ratioStatus = getRatioStatus(ratio);
  
  // Calculate cost breakdown
  const promptCost = call.prompt_cost || (call.total_cost * (call.prompt_tokens / (call.prompt_tokens + call.completion_tokens)));
  const completionCost = call.completion_cost || (call.total_cost - promptCost);
  const inputPct = call.prompt_tokens / (call.prompt_tokens + call.completion_tokens) * 100;

  return [
    {
      label: 'Token Ratio',
      value: ratio === Infinity ? '∞:1' : `${ratio.toFixed(0)}:1`,
      subtext: `${ratioStatus.label}`,
      status: ratioStatus.status === 'severe' ? 'critical' : 
              ratioStatus.status === 'high' ? 'critical' :
              ratioStatus.status === 'moderate' ? 'warning' : 'good',
    },
    {
      label: 'Prompt Tokens',
      value: call.prompt_tokens?.toLocaleString() || '0',
      subtext: `$${(promptCost || 0).toFixed(3)} input cost`,
      status: 'neutral',
    },
    {
      label: 'Completion Tokens',
      value: call.completion_tokens?.toLocaleString() || '0',
      subtext: `$${(completionCost || 0).toFixed(3)} output cost`,
      status: call.completion_tokens < THRESHOLDS.low_output_tokens ? 'warning' : 'neutral',
    },
    {
      label: 'Total Cost',
      value: `$${(call.total_cost || 0).toFixed(3)}`,
      subtext: `${inputPct.toFixed(0)}% from input`,
      status: inputPct > THRESHOLDS.high_input_cost_pct ? 'warning' : 'neutral',
    },
  ];
}

// ─────────────────────────────────────────────────────────────────────────────
// CURRENT STATE (for comparison table)
// ─────────────────────────────────────────────────────────────────────────────

export function getTokenCurrentState(call) {
  const ratio = calculateRatio(call.prompt_tokens, call.completion_tokens);
  
  return {
    ratio: ratio === Infinity ? '∞:1' : `${ratio.toFixed(0)}:1`,
    prompt: call.prompt_tokens?.toLocaleString() || '0',
    completion: call.completion_tokens?.toLocaleString() || '0',
    cost: `$${(call.total_cost || 0).toFixed(3)}`,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// TOKEN BREAKDOWN
// ─────────────────────────────────────────────────────────────────────────────

export function getTokenBreakdown(call) {
  const systemTokens = call.system_prompt_tokens || 0;
  const userTokens = call.user_message_tokens || 0;
  const historyTokens = call.chat_history_tokens || 0;
  const totalPrompt = call.prompt_tokens || (systemTokens + userTokens + historyTokens);
  
  // Calculate percentages
  const systemPct = totalPrompt > 0 ? (systemTokens / totalPrompt) * 100 : 0;
  const userPct = totalPrompt > 0 ? (userTokens / totalPrompt) * 100 : 0;
  const historyPct = totalPrompt > 0 ? (historyTokens / totalPrompt) * 100 : 0;
  
  return {
    system: systemTokens,
    systemPct,
    user: userTokens,
    userPct,
    history: historyTokens,
    historyPct,
    total: totalPrompt,
    completion: call.completion_tokens || 0,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// FACTOR DETECTION (improved to catch more issues)
// ─────────────────────────────────────────────────────────────────────────────

export function analyzeTokenFactors(call) {
  const factors = [];
  const ratio = calculateRatio(call.prompt_tokens, call.completion_tokens);
  const breakdown = getTokenBreakdown(call);
  const inputCostPct = call.prompt_tokens / (call.prompt_tokens + call.completion_tokens) * 100;
  
  // Factor: Token imbalance (now includes moderate)
  if (ratio > THRESHOLDS.ratio_severe) {
    factors.push({
      id: 'severe_imbalance',
      severity: 'critical',
      label: `Severe Token Imbalance: ${ratio.toFixed(0)}:1`,
      impact: `Input tokens are ${ratio.toFixed(0)}x output tokens`,
      description: 'The ratio of input to output tokens is very high, indicating significant inefficiency.',
      hasFix: true,
    });
  } else if (ratio > THRESHOLDS.ratio_high) {
    factors.push({
      id: 'high_imbalance',
      severity: 'critical',
      label: `High Token Imbalance: ${ratio.toFixed(0)}:1`,
      impact: `Input tokens are ${ratio.toFixed(0)}x output tokens`,
      description: 'Input significantly exceeds output. Consider reducing prompt size or requesting more detailed responses.',
      hasFix: true,
    });
  } else if (ratio > THRESHOLDS.ratio_moderate) {
    // NEW: Now catches moderate imbalance (4:1 to 8:1)
    factors.push({
      id: 'moderate_imbalance',
      severity: 'warning',
      label: `Moderate Token Imbalance: ${ratio.toFixed(0)}:1`,
      impact: `Input tokens are ${ratio.toFixed(0)}x output tokens`,
      description: 'Token ratio is above optimal range. Minor optimizations could improve efficiency.',
      hasFix: true,
    });
  }
  
  // Factor: Oversized system prompt (by percentage OR absolute)
  if (breakdown.systemPct > THRESHOLDS.system_prompt_pct) {
    factors.push({
      id: 'large_system_prompt',
      severity: breakdown.systemPct > 70 ? 'critical' : 'warning',
      label: `Large System Prompt: ${breakdown.system.toLocaleString()} tokens (${breakdown.systemPct.toFixed(0)}%)`,
      impact: 'System prompt dominates input tokens',
      description: 'The system prompt is consuming most of your input budget. Consider simplifying.',
      hasFix: true,
    });
  } else if (breakdown.system > THRESHOLDS.system_prompt_tokens && breakdown.systemPct > 30) {
    // NEW: Catch absolute size even if percentage is moderate
    factors.push({
      id: 'large_system_prompt_absolute',
      severity: 'info',
      label: `System Prompt: ${breakdown.system.toLocaleString()} tokens`,
      impact: `System prompt is ${breakdown.systemPct.toFixed(0)}% of input`,
      description: 'System prompt is substantial. Review for optimization opportunities.',
      hasFix: true,
    });
  }
  
  // Factor: Large chat history
  if (breakdown.historyPct > THRESHOLDS.history_pct && breakdown.history > 200) {
    factors.push({
      id: 'large_history',
      severity: breakdown.historyPct > 50 ? 'critical' : 'warning',
      label: `Chat History: ${breakdown.history.toLocaleString()} tokens (${breakdown.historyPct.toFixed(0)}%)`,
      impact: 'Conversation history taking up significant space',
      description: 'Consider truncating older messages or summarizing history.',
      hasFix: true,
    });
  }
  
  // Factor: Low output tokens
  if (call.completion_tokens < THRESHOLDS.low_output_tokens) {
    factors.push({
      id: 'low_output',
      severity: call.completion_tokens < 50 ? 'critical' : 'warning',
      label: `Low Output: ${call.completion_tokens} tokens`,
      impact: 'Response may be too brief for the input provided',
      description: 'The model is generating very little output. Consider requesting more detailed responses.',
      hasFix: true,
    });
  }
  
  // Factor: High input cost percentage
  if (inputCostPct > THRESHOLDS.high_input_cost_pct) {
    factors.push({
      id: 'high_input_cost',
      severity: 'warning',
      label: `Input Cost: ${inputCostPct.toFixed(0)}% of total`,
      impact: 'Most spending is on input processing',
      description: 'You\'re paying primarily for input tokens. Output provides the value.',
      hasFix: true,
    });
  }
  
  // Factor: No max_tokens set
  if ((call.max_tokens === null || call.max_tokens === undefined) && ratio > THRESHOLDS.ratio_moderate) {
    factors.push({
      id: 'no_max_tokens',
      severity: 'info',
      label: 'No max_tokens Limit',
      impact: 'Output length is unbounded',
      description: 'Model decides when to stop generating. Consider setting a limit.',
      hasFix: true,
    });
  }

  // Sort by severity
  const severityOrder = { critical: 0, warning: 1, info: 2, ok: 3 };
  factors.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);

  return factors;
}

// ─────────────────────────────────────────────────────────────────────────────
// FIX DEFINITIONS
// ─────────────────────────────────────────────────────────────────────────────

export function getTokenFixes(call, factors) {
  const fixes = [];
  const ratio = calculateRatio(call.prompt_tokens, call.completion_tokens);
  const breakdown = getTokenBreakdown(call);
  
  // Fix 1: Simplify System Prompt (if system prompt is an issue OR ratio is bad)
  if (factors.some(f => ['large_system_prompt', 'large_system_prompt_absolute', 'severe_imbalance', 'high_imbalance', 'moderate_imbalance'].includes(f.id)) && breakdown.system > 200) {
    const newSystemTokens = Math.round(breakdown.system * 0.4);
    const newTotal = newSystemTokens + breakdown.user + breakdown.history;
    const newRatio = calculateRatio(newTotal, call.completion_tokens);
    const costReduction = ((breakdown.system - newSystemTokens) / call.prompt_tokens) * (call.total_cost || 0);
    
    fixes.push({
      id: 'simplify_system_prompt',
      title: 'Simplify System Prompt',
      subtitle: `Reduce from ${breakdown.system.toLocaleString()} to ~${newSystemTokens.toLocaleString()} tokens`,
      effort: 'Medium',
      effortColor: 'text-yellow-400',
      recommended: breakdown.systemPct > 40,
      
      metrics: [
        {
          label: 'Ratio',
          before: `${ratio.toFixed(0)}:1`,
          after: `${newRatio.toFixed(0)}:1`,
          changePercent: -Math.round((1 - newRatio / ratio) * 100),
        },
        {
          label: 'Prompt',
          before: call.prompt_tokens.toLocaleString(),
          after: `~${newTotal.toLocaleString()}`,
          changePercent: -Math.round((1 - newTotal / call.prompt_tokens) * 100),
        },
        {
          label: 'Cost',
          before: `$${(call.total_cost || 0).toFixed(3)}`,
          after: `$${((call.total_cost || 0) - costReduction).toFixed(3)}`,
          changePercent: -Math.round((costReduction / (call.total_cost || 1)) * 100),
        },
        {
          label: 'Quality',
          before: '—',
          after: 'May vary',
          changePercent: 0,
        },
      ],
      
      codeBefore: `system_prompt = """
You are an expert analyst with 20 years of experience.

DETAILED CRITERIA:
1. First criterion with extensive explanation...
2. Second criterion with multiple sub-points...
3. Third criterion covering edge cases...
[... ${breakdown.system} tokens of detailed instructions ...]
"""`,
      codeAfter: `system_prompt = """
You are an expert analyst. Evaluate based on:
1. Key criterion A
2. Key criterion B  
3. Key criterion C

Be concise and specific.
"""`,
      
      tradeoffs: [
        'May lose nuanced instructions',
        'Requires testing for quality impact',
        'Some edge cases may not be handled',
      ],
      benefits: [
        `Save ~$${costReduction.toFixed(3)} per call`,
        'Faster response times',
        'Lower token costs',
        'Easier to maintain prompts',
      ],
      bestFor: 'When system prompt has grown organically and contains redundancy',
    });
  }
  
  // Fix 2: Request Longer Output (if output is low OR ratio is bad)
  if (factors.some(f => ['low_output', 'severe_imbalance', 'high_imbalance', 'moderate_imbalance', 'high_input_cost'].includes(f.id))) {
    const targetOutput = Math.max(400, call.prompt_tokens / 4); // Target 4:1 ratio
    const newRatio = calculateRatio(call.prompt_tokens, targetOutput);
    const additionalCost = (targetOutput - call.completion_tokens) * 0.00004; // Rough estimate
    
    fixes.push({
      id: 'request_longer_output',
      title: 'Request Longer Output',
      subtitle: 'Add minimum length requirements to prompt',
      effort: 'Low',
      effortColor: 'text-green-400',
      recommended: call.completion_tokens < 200,
      
      metrics: [
        {
          label: 'Ratio',
          before: `${ratio.toFixed(0)}:1`,
          after: `${newRatio.toFixed(0)}:1`,
          changePercent: -Math.round((1 - newRatio / ratio) * 100),
        },
        {
          label: 'Output',
          before: call.completion_tokens.toLocaleString(),
          after: `~${Math.round(targetOutput).toLocaleString()}`,
          changePercent: Math.round((targetOutput / call.completion_tokens - 1) * 100),
        },
        {
          label: 'Cost',
          before: `$${(call.total_cost || 0).toFixed(3)}`,
          after: `$${((call.total_cost || 0) + additionalCost).toFixed(3)}`,
          changePercent: Math.round((additionalCost / (call.total_cost || 1)) * 100),
        },
        {
          label: 'Quality',
          before: 'Brief',
          after: 'Detailed',
          changePercent: 50,
        },
      ],
      
      codeBefore: `system_prompt = """
Analyze the candidate and provide your assessment.
"""`,
      codeAfter: `system_prompt = """
Analyze the candidate and provide your assessment.

IMPORTANT: Your response must include:
- At least 3 paragraphs of analysis
- Specific examples from the source material
- A detailed recommendation with reasoning

Minimum response length: 400 words.
"""`,
      
      tradeoffs: [
        'Higher output token cost',
        'Longer response times',
        'May include filler content',
      ],
      benefits: [
        'Better token efficiency ratio',
        'More detailed analysis',
        'Better value from large prompts',
        'Simple prompt change',
      ],
      bestFor: 'When output is too brief for the input provided',
    });
  }
  
  // Fix 3: Truncate History (if history is significant)
  if (factors.some(f => f.id === 'large_history') || (breakdown.history > 200 && breakdown.historyPct > 20)) {
    const newHistory = Math.round(breakdown.history * 0.3);
    const newTotal = breakdown.system + breakdown.user + newHistory;
    const newRatio = calculateRatio(newTotal, call.completion_tokens);
    
    fixes.push({
      id: 'truncate_history',
      title: 'Truncate Chat History',
      subtitle: 'Keep only recent messages',
      effort: 'Low',
      effortColor: 'text-green-400',
      
      metrics: [
        {
          label: 'Ratio',
          before: `${ratio.toFixed(0)}:1`,
          after: `${newRatio.toFixed(0)}:1`,
          changePercent: -Math.round((1 - newRatio / ratio) * 100),
        },
        {
          label: 'History',
          before: breakdown.history.toLocaleString(),
          after: `~${newHistory.toLocaleString()}`,
          changePercent: -70,
        },
        {
          label: 'Cost',
          before: `$${(call.total_cost || 0).toFixed(3)}`,
          after: `$${((call.total_cost || 0) * 0.6).toFixed(3)}`,
          changePercent: -40,
        },
        {
          label: 'Context',
          before: 'Full',
          after: 'Recent',
          changePercent: 0,
        },
      ],
      
      codeBefore: `messages = full_conversation_history  # ${breakdown.history} tokens`,
      codeAfter: `MAX_HISTORY = 10  # Keep last N messages

def truncate_history(messages):
    system = messages[0] if messages[0]["role"] == "system" else None
    recent = messages[-MAX_HISTORY:]
    return [system] + recent if system else recent

messages = truncate_history(full_conversation_history)`,
      
      tradeoffs: [
        'Loses older context',
        'May forget earlier instructions',
        'Not suitable for long analysis',
      ],
      benefits: [
        'Significant cost reduction',
        'Faster processing',
        'Works for most conversations',
        'Simple to implement',
      ],
      bestFor: 'Multi-turn conversations where recent context is most relevant',
    });
  }
  
  // Fix 4: Combined approach (when multiple issues)
  if (factors.length >= 2) {
    const newSystemTokens = Math.round(breakdown.system * 0.5);
    const newHistory = Math.round(breakdown.history * 0.4);
    const newTotal = newSystemTokens + breakdown.user + newHistory;
    const targetOutput = Math.max(300, call.completion_tokens * 2);
    const newRatio = calculateRatio(newTotal, targetOutput);
    
    fixes.push({
      id: 'combined_optimization',
      title: 'Combined: Simplify + Longer Output',
      subtitle: 'Best balance of input reduction and output increase',
      effort: 'Medium',
      effortColor: 'text-yellow-400',
      recommended: factors.length >= 2,
      
      metrics: [
        {
          label: 'Ratio',
          before: `${ratio.toFixed(0)}:1`,
          after: `${newRatio.toFixed(0)}:1`,
          changePercent: -Math.round((1 - newRatio / ratio) * 100),
        },
        {
          label: 'Prompt',
          before: call.prompt_tokens.toLocaleString(),
          after: `~${newTotal.toLocaleString()}`,
          changePercent: -Math.round((1 - newTotal / call.prompt_tokens) * 100),
        },
        {
          label: 'Output',
          before: call.completion_tokens.toLocaleString(),
          after: `~${Math.round(targetOutput).toLocaleString()}`,
          changePercent: Math.round((targetOutput / call.completion_tokens - 1) * 100),
        },
        {
          label: 'Cost',
          before: `$${(call.total_cost || 0).toFixed(3)}`,
          after: `$${((call.total_cost || 0) * 0.7).toFixed(3)}`,
          changePercent: -30,
        },
      ],
      
      codeBefore: `# Current: Large prompt, small output
system_prompt = "..." # ${breakdown.system} tokens
# Output: ${call.completion_tokens} tokens`,
      codeAfter: `# Optimized: Balanced prompt and output
system_prompt = "..." # ~${newSystemTokens} tokens (simplified)

# Add output requirements
system_prompt += """
Provide a detailed response with:
- Specific analysis points
- Clear recommendations
Minimum 300 words.
"""`,
      
      tradeoffs: [
        'Requires more testing',
        'Two changes to coordinate',
        'May need iteration',
      ],
      benefits: [
        'Best overall efficiency',
        'Better cost/value ratio',
        'More useful output',
        'Sustainable long-term',
      ],
      bestFor: 'Systematic optimization of imbalanced operations',
    });
  }

  return fixes.slice(0, 4); // Max 4 fixes
}

// ─────────────────────────────────────────────────────────────────────────────
// CONFIG HIGHLIGHTS
// ─────────────────────────────────────────────────────────────────────────────

export function getTokenConfigHighlights(call, factors) {
  const highlights = [];
  const ratio = calculateRatio(call.prompt_tokens, call.completion_tokens);

  if (ratio > THRESHOLDS.ratio_severe) {
    highlights.push({
      key: 'ratio',
      message: `${ratio.toFixed(0)}:1 SEVERE`,
      severity: 'critical',
    });
  } else if (ratio > THRESHOLDS.ratio_high) {
    highlights.push({
      key: 'ratio',
      message: `${ratio.toFixed(0)}:1 HIGH`,
      severity: 'critical',
    });
  } else if (ratio > THRESHOLDS.ratio_moderate) {
    highlights.push({
      key: 'ratio',
      message: `${ratio.toFixed(0)}:1 MODERATE`,
      severity: 'warning',
    });
  }

  if ((call.max_tokens === null || call.max_tokens === undefined) && ratio > THRESHOLDS.ratio_moderate) {
    highlights.push({
      key: 'max_tokens',
      message: 'NOT SET',
      severity: 'warning',
    });
  }

  return highlights;
}

// ─────────────────────────────────────────────────────────────────────────────
// SIMILAR PANEL CONFIG
// ─────────────────────────────────────────────────────────────────────────────

export const TOKEN_SIMILAR_CONFIG = {
  filterOptions: [
    { id: 'same_operation', label: 'Same Operation' },
    { id: 'severe', label: 'Severe Imbalance' },
    { id: 'balanced', label: 'Well Balanced' },
  ],
  defaultFilter: 'same_operation',
  
  columns: [
    { key: 'call_id', label: 'Call ID', format: (v) => v?.substring(0, 8) + '...' },
    { key: 'ratio', label: 'Ratio', format: (v, row) => {
      const r = calculateRatio(row.prompt_tokens, row.completion_tokens);
      return r === Infinity ? '∞:1' : `${r.toFixed(0)}:1`;
    }},
    { key: 'prompt_tokens', label: 'Input', format: (v) => v?.toLocaleString() },
    { key: 'completion_tokens', label: 'Output', format: (v) => v?.toLocaleString() },
    { key: 'total_cost', label: 'Cost', format: (v) => `$${v?.toFixed(3)}` },
  ],
};