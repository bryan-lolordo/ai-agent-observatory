/**
 * Latency Story - Layer 3 Configuration
 * 
 * Defines:
 * - KPI definitions
 * - Factor detection rules
 * - Fix templates with full details (tradeoffs, benefits, output previews)
 * - Analysis functions
 */

// ─────────────────────────────────────────────────────────────────────────────
// STORY METADATA
// ─────────────────────────────────────────────────────────────────────────────

export const LATENCY_STORY = {
  id: 'latency',
  label: 'Latency Analysis',
  icon: '🌐',
  color: '#f97316', // Orange
  entityType: 'call',
};

// ─────────────────────────────────────────────────────────────────────────────
// KPI DEFINITIONS
// ─────────────────────────────────────────────────────────────────────────────

export function getLatencyKPIs(call) {
  const latencyStatus =
    call.latency_ms > 10000 ? 'critical' :
    call.latency_ms > 5000 ? 'warning' : 'good';

  const tokenStatus =
    call.completion_tokens > 1500 ? 'critical' :
    call.completion_tokens > 500 ? 'warning' : 'good';

  return [
    {
      label: 'Latency',
      value: `${(call.latency_ms / 1000).toFixed(1)}s`,
      subtext: 'Total time',
      status: latencyStatus,
    },
    {
      label: 'TTFT',
      value: `${((call.ttft_ms || 0) / 1000).toFixed(1)}s`,
      subtext: 'First token',
      status: 'neutral',
    },
    {
      label: 'Completion',
      value: call.completion_tokens?.toLocaleString() || '0',
      subtext: 'Tokens out',
      status: tokenStatus,
    },
    {
      label: 'Cost',
      value: `$${(call.total_cost || 0).toFixed(3)}`,
      subtext: 'Total',
      status: 'neutral',
    },
  ];
}

// ─────────────────────────────────────────────────────────────────────────────
// CURRENT STATE (for comparison table)
// ─────────────────────────────────────────────────────────────────────────────

export function getLatencyCurrentState(call) {
  return {
    latency: `${(call.latency_ms / 1000).toFixed(1)}s`,
    tokens: call.completion_tokens?.toLocaleString() || '0',
    cost: `$${(call.total_cost || 0).toFixed(3)}`,
    quality: 'Complete',
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// TIME ATTRIBUTION (NEW)
// ─────────────────────────────────────────────────────────────────────────────

export function getTimeAttribution(call) {
  const ttft_ms = call.ttft_ms || call.time_to_first_token_ms || (call.latency_ms * 0.1);
  const generation_ms = call.latency_ms - ttft_ms;
  const tokens_per_second = call.completion_tokens / (generation_ms / 1000);

  return {
    total_ms: call.latency_ms,
    ttft_ms,
    generation_ms,
    completion_tokens: call.completion_tokens,
    tokens_per_second,
    expected_tokens_per_second: 20, // Expected baseline
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// FACTOR DETECTION (ENHANCED)
// ─────────────────────────────────────────────────────────────────────────────

export function analyzeLatencyFactors(call) {
  const factors = [];

  const ttft_ms = call.ttft_ms || call.latency_ms * 0.1;
  const generation_ms = call.latency_ms - ttft_ms;
  const generation_pct = (generation_ms / call.latency_ms) * 100;

  // Factor: Large chat history (PRIORITIZED for multi-turn)
  if (call.chat_history_tokens && call.chat_history_tokens > call.prompt_tokens * 0.4) {
    const pct = ((call.chat_history_tokens / call.prompt_tokens) * 100).toFixed(0);
    const estimated_latency_impact = (call.chat_history_tokens / call.prompt_tokens) * call.latency_ms;
    
    factors.push({
      id: 'large_history',
      severity: call.chat_history_tokens > call.prompt_tokens * 0.6 ? 'critical' : 'warning',
      label: `Chat History: ${call.chat_history_tokens.toLocaleString()} tokens (${pct}%)`,
      impact: `+${(estimated_latency_impact / 1000).toFixed(0)}s (${((estimated_latency_impact / call.latency_ms) * 100).toFixed(0)}%)`,
      description: `Conversation history accumulation is the primary driver of latency. Old turns from earlier in the conversation are still being processed but may not be necessary for the current response.`, // ✅ DETAILED
      hasFix: true,
    });
  }

  // Factor: High completion tokens
  if (call.completion_tokens > 500) {
    const severity =
      call.completion_tokens > 1500 ? 'critical' :
      call.completion_tokens > 800 ? 'warning' : 'info';
    
    factors.push({
      id: 'high_completion_tokens',
      severity,
      label: `Completion Tokens: ${call.completion_tokens.toLocaleString()}`,
      impact: `+${(generation_ms / 1000).toFixed(1)}s (${generation_pct.toFixed(0)}% of latency)`,
      description: 'High token generation is driving latency. The model is producing a very long response which takes significant time to generate.', // ✅ DETAILED
      hasFix: true,
    });
  }

  // Factor: No max_tokens
  if (call.max_tokens === null && call.completion_tokens > 200) {
    factors.push({
      id: 'no_max_tokens',
      severity: call.completion_tokens > 500 ? 'warning' : 'info',
      label: 'No max_tokens Limit',
      impact: 'Output length is unbounded',
      description: 'Without a limit, the model decides generation length. This can lead to unexpectedly long responses and unpredictable latency. Setting max_tokens provides control over response length.', // ✅ DETAILED
      hasFix: true,
    });
  }

  // Factor: No streaming
  if (!call.streaming && call.latency_ms > 2000) {
    factors.push({
      id: 'no_streaming',
      severity: call.latency_ms > 5000 ? 'warning' : 'info',
      label: 'Streaming Disabled',
      impact: `User waits ${(call.latency_ms / 1000).toFixed(1)}s for response`,
      description: 'Enable streaming for better perceived performance. Users can start reading the response immediately instead of waiting for the entire generation to complete.', // ✅ DETAILED
      hasFix: true,
    });
  }

  // Factor: High prompt tokens (only if NOT from chat history)
  if (call.prompt_tokens > 2000 && (!call.chat_history_tokens || call.chat_history_tokens < call.prompt_tokens * 0.3)) {
    const severity =
      call.prompt_tokens > 8000 ? 'critical' :
      call.prompt_tokens > 4000 ? 'warning' : 'info';
    
    factors.push({
      id: 'high_prompt_tokens',
      severity,
      label: `Prompt Tokens: ${call.prompt_tokens.toLocaleString()}`,
      impact: `+${(ttft_ms / 1000).toFixed(1)}s TTFT`,
      description: 'Large prompts increase time to first token. The model needs to process all input tokens before generating the first output token, leading to higher perceived latency.', // ✅ DETAILED
      hasFix: true,
    });
  }

  // Sort by severity
  const severityOrder = { critical: 0, warning: 1, info: 2, ok: 3 };
  factors.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);

  return factors;
}

// ─────────────────────────────────────────────────────────────────────────────
// TIME BREAKDOWN
// ─────────────────────────────────────────────────────────────────────────────

export function getLatencyBreakdown(call) {
  const ttft_ms = call.ttft_ms || call.latency_ms * 0.1;
  const generation_ms = call.latency_ms - ttft_ms;
  const ttft_pct = (ttft_ms / call.latency_ms) * 100;
  const generation_pct = (generation_ms / call.latency_ms) * 100;
  const tokens_per_second = call.completion_tokens / (generation_ms / 1000);

  return {
    total_ms: call.latency_ms,
    ttft_ms,
    ttft_pct,
    generation_ms,
    generation_pct,
    tokens_per_second: tokens_per_second.toFixed(0),
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// RESPONSE ANALYSIS
// ─────────────────────────────────────────────────────────────────────────────

export function analyzeLatencyResponse(call) {
  const response = call.response_text || '';
  
  // Detect response type
  let type = 'prose';
  if (response.trim().startsWith('{') || response.trim().startsWith('[')) {
    type = 'json';
  } else if (response.includes('```')) {
    type = 'code';
  } else if (/^##?\s/m.test(response)) {
    type = 'markdown';
  }

  // Extract sections if markdown
  const sections = [];
  if (type === 'markdown') {
    const matches = response.match(/^##?\s+.+$/gm) || [];
    sections.push(...matches.map(h => h.replace(/^#+\s+/, '')));
  }

  return {
    type,
    sections,
    sectionCount: sections.length,
    tokenCount: call.completion_tokens,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// PROMPT ANALYSIS
// ─────────────────────────────────────────────────────────────────────────────

export function analyzeLatencyPrompt(call) {
  const prompt = (call.system_prompt || '').toLowerCase();
  const verbose_indicators = [];

  if (prompt.includes('comprehensive')) verbose_indicators.push("'comprehensive'");
  if (prompt.includes('detailed')) verbose_indicators.push("'detailed'");
  if (prompt.includes('thorough')) verbose_indicators.push("'thorough'");
  if (prompt.includes('in-depth')) verbose_indicators.push("'in-depth'");

  return {
    verbose_indicators,
    encourages_verbosity: verbose_indicators.length > 0,
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// FIX DEFINITIONS (ENHANCED with Conversation Pruning)
// ─────────────────────────────────────────────────────────────────────────────

export function getLatencyFixes(call, factors) {
  const fixes = [];
  const breakdown = getLatencyBreakdown(call);

  // Fix 1: Truncate/Prune Conversation History (NEW - HIGH PRIORITY)
  if (factors.some(f => f.id === 'large_history')) {
    const chatHistory = call.chat_history_tokens || 0;
    const pct = chatHistory > 0 ? (chatHistory / call.prompt_tokens) * 100 : 0;
    const estimatedNewTokens = call.prompt_tokens - (chatHistory * 0.6); // Remove 60% of history
    const estimatedNewLatency = call.latency_ms * (estimatedNewTokens / call.prompt_tokens);
    const latencySavings = call.latency_ms - estimatedNewLatency;

    fixes.push({
      id: 'truncate_history',
      title: 'Prune Conversation History',
      subtitle: 'Remove old turns (keep last 2)',
      effort: 'Low',
      effortColor: 'text-green-400',
      recommended: true,
      
      metrics: [
        {
          label: 'Latency',
          before: `${(call.latency_ms / 1000).toFixed(1)}s`,
          after: `~${(estimatedNewLatency / 1000).toFixed(1)}s`,
          changePercent: -Math.round((latencySavings / call.latency_ms) * 100),
        },
        {
          label: 'Tokens',
          before: call.prompt_tokens.toLocaleString(),
          after: Math.round(estimatedNewTokens).toLocaleString(),
          changePercent: -Math.round(((chatHistory * 0.6) / call.prompt_tokens) * 100),
        },
        {
          label: 'Cost',
          before: `$${call.total_cost.toFixed(3)}`,
          after: `$${(call.total_cost * (estimatedNewTokens / call.prompt_tokens)).toFixed(3)}`,
          changePercent: -Math.round(((chatHistory * 0.6) / call.prompt_tokens) * 100),
        },
        {
          label: 'Quality',
          before: 'Full context',
          after: '✅ Recent only',
          changePercent: 0,
        },
      ],
      
      codeBefore: `# Full history: ${chatHistory.toLocaleString()} tokens across ${call.chat_history_count || '?'} messages
messages = conversation_history`,
      
      codeAfter: `MAX_HISTORY = 10  # Keep last N messages

def truncate_history(messages):
    system = messages[0] if messages[0]["role"] == "system" else None
    recent = messages[-MAX_HISTORY:]
    return [system] + recent if system else recent

messages = truncate_history(conversation_history)
# Now: ~${Math.round(chatHistory * 0.4).toLocaleString()} tokens`,
      
      outputPreview: call.response_text?.substring(0, 500) || 'Same quality output with less input context',
      outputNote: '✅ Same output quality, ${Math.round(chatHistory * 0.6).toLocaleString()} fewer input tokens',
      outputNoteColor: 'text-green-400',
      
      tradeoffs: [
        'Loses early conversation context',
        'May forget initial instructions from Turn 1-2',
        'Not suitable for tasks requiring full conversation history',
      ],
      benefits: [
        `Removes ${Math.round(chatHistory * 0.6).toLocaleString()} unnecessary tokens`,
        'Significantly faster processing',
        'Lower token costs',
        'Simple to implement',
      ],
      bestFor: 'Multi-turn chats where recent context is most important',
    });
  }

  // Fix 3: Enable streaming
  if (factors.some(f => f.id === 'no_streaming')) {
    const isAnthropic = call.provider === 'anthropic';
    
    fixes.push({
      id: 'enable_streaming',
      title: 'Enable Streaming',
      subtitle: 'UX Fix - Perceived Performance',
      effort: 'Medium',
      effortColor: 'text-yellow-400',
      
      metrics: [
        {
          label: 'Latency',
          before: `${(call.latency_ms / 1000).toFixed(1)}s`,
          after: `${(call.latency_ms / 1000).toFixed(1)}s`,
          changePercent: 0,
        },
        {
          label: 'Perceived',
          before: `${(call.latency_ms / 1000).toFixed(1)}s`,
          after: `~${((call.ttft_ms || 1200) / 1000).toFixed(1)}s`,
          changePercent: -90,
        },
        {
          label: 'Cost',
          before: `$${call.total_cost.toFixed(3)}`,
          after: `$${call.total_cost.toFixed(3)}`,
          changePercent: 0,
        },
        {
          label: 'Quality',
          before: 'Complete',
          after: '✅ Same',
          changePercent: 0,
        },
      ],
      
      codeBefore: `response = client.chat.completions.create(
    model="${call.model_name || 'gpt-4o'}",
    messages=messages
)
result = response.choices[0].message.content`,
      
      codeAfter: isAnthropic
        ? `with client.messages.stream(
    model="${call.model_name || 'claude-3-sonnet'}",
    messages=messages,
    max_tokens=${call.max_tokens || 1000}
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)`
        : `response = client.chat.completions.create(
    model="${call.model_name || 'gpt-4o'}",
    messages=messages,
    stream=True  # Enable streaming
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)`,
      
      outputPreview: `[Tokens appear one by one as generated]

## Section 1: Skills... ← User sees this immediately
...Alignment ← Then this
The candidate... ← And so on

User starts reading while LLM is still generating.
Total time is same, but feels instant.`,
      outputNote: '✅ Same output, dramatically better UX',
      outputNoteColor: 'text-green-400',
      
      tradeoffs: [
        'Requires streaming handler in UI',
        'More complex error handling',
        'Some libraries don\'t support well',
      ],
      benefits: [
        'User sees first token in ~1s instead of 12s',
        'Can start reading immediately',
        'Feels much faster',
        'No quality/cost trade-off',
      ],
      bestFor: 'User-facing applications where perceived speed matters',
    });
  }

    return fixes.slice(0, 4); // Max 4 fixes
}

// ─────────────────────────────────────────────────────────────────────────────
// CONFIG HIGHLIGHTS
// ─────────────────────────────────────────────────────────────────────────────

export function getLatencyConfigHighlights(call, factors) {
  const highlights = [];

  if (call.max_tokens === null && factors.some(f => f.id === 'no_max_tokens')) {
    highlights.push({
      key: 'max_tokens',
      message: 'NOT SET',
      severity: 'critical',
    });
  }

  if (!call.streaming && factors.some(f => f.id === 'no_streaming')) {
    highlights.push({
      key: 'stream',
      message: 'DISABLED',
      severity: 'warning',
    });
  }

  return highlights;
}