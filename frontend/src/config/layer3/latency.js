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
// FACTOR DETECTION
// ─────────────────────────────────────────────────────────────────────────────

export function analyzeLatencyFactors(call) {
  const factors = [];

  const ttft_ms = call.ttft_ms || call.latency_ms * 0.1;
  const generation_ms = call.latency_ms - ttft_ms;
  const generation_pct = (generation_ms / call.latency_ms) * 100;

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
      description: 'High token generation is driving latency.',
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
      description: 'Without a limit, the model decides generation length.',
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
      description: 'Enable streaming for better perceived performance.',
      hasFix: true,
    });
  }

  // Factor: High prompt tokens
  if (call.prompt_tokens > 2000) {
    const severity =
      call.prompt_tokens > 8000 ? 'critical' :
      call.prompt_tokens > 4000 ? 'warning' : 'info';
    
    factors.push({
      id: 'high_prompt_tokens',
      severity,
      label: `Prompt Tokens: ${call.prompt_tokens.toLocaleString()}`,
      impact: `+${(ttft_ms / 1000).toFixed(1)}s TTFT`,
      description: 'Large prompts increase time to first token.',
      hasFix: true,
    });
  }

  // Factor: Large chat history
  if (call.chat_history_tokens && call.chat_history_tokens > call.prompt_tokens * 0.4) {
    const pct = ((call.chat_history_tokens / call.prompt_tokens) * 100).toFixed(0);
    factors.push({
      id: 'large_history',
      severity: call.chat_history_tokens > call.prompt_tokens * 0.6 ? 'critical' : 'warning',
      label: `Chat History: ${call.chat_history_tokens.toLocaleString()} tokens (${pct}%)`,
      impact: 'Conversation history dominating input',
      description: 'Long history increases processing time.',
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
// FIX DEFINITIONS (Enhanced with tradeoffs, benefits, output previews)
// ─────────────────────────────────────────────────────────────────────────────

export function getLatencyFixes(call, factors) {
  const fixes = [];
  const breakdown = getLatencyBreakdown(call);

  // Fix 1: Add max_tokens
  if (factors.some(f => f.id === 'no_max_tokens' || f.id === 'high_completion_tokens')) {
    const estimatedNewLatency = Math.round(call.latency_ms * 0.25);
    const estimatedNewTokens = 500;
    
    fixes.push({
      id: 'add_max_tokens',
      title: 'Add max_tokens=500',
      subtitle: 'Quick Fix - Hard Limit',
      effort: 'Low',
      effortColor: 'text-green-400',
      recommended: true,
      
      metrics: [
        {
          label: 'Latency',
          before: `${(call.latency_ms / 1000).toFixed(1)}s`,
          after: `~${(estimatedNewLatency / 1000).toFixed(1)}s`,
          changePercent: -75,
        },
        {
          label: 'Tokens',
          before: call.completion_tokens.toLocaleString(),
          after: '500',
          changePercent: -Math.round((1 - 500 / call.completion_tokens) * 100),
        },
        {
          label: 'Cost',
          before: `$${call.total_cost.toFixed(3)}`,
          after: `$${(call.total_cost * 0.3).toFixed(3)}`,
          changePercent: -70,
        },
        {
          label: 'Quality',
          before: 'Complete',
          after: '⚠️ Truncated',
          changePercent: 0,
          status: 'warning',
        },
      ],
      
      codeBefore: `response = client.chat.completions.create(
    model="${call.model_name || 'gpt-4o'}",
    messages=messages,
    temperature=${call.temperature || 0.7}
)`,
      codeAfter: `response = client.chat.completions.create(
    model="${call.model_name || 'gpt-4o'}",
    messages=messages,
    temperature=${call.temperature || 0.7},
    max_tokens=500  # Hard limit
)`,
      
      outputPreview: `## Section 1: Skills Alignment
The candidate demonstrates strong proficiency in several key areas 
that align well with the position requirements. Specifically:
- Python Development: 6+ years experience with Django, Flask...
- Cloud Architecture: Extensive AWS and Azure experience...
[312 tokens - COMPLETE]

## Section 2: Experience Match  
Looking at the candidate's work history, we can see strong
alignment with the role requirements. Their time at Syndigo
demonstrates the ability to work with enterprise clients and
manage complex technical pro`,
      outputNote: '⚠️ STOPS HERE - Cut off mid-word at 500 tokens',
      outputNoteColor: 'text-red-400',
      outputTruncated: true,
      
      tradeoffs: [
        'Response ends abruptly mid-sentence',
        'No final score or recommendation',
        'May break downstream JSON parsing',
        'User gets incomplete analysis',
      ],
      benefits: [
        'One line code change',
        'Immediate latency reduction',
        'Predictable max cost',
      ],
      bestFor: 'Quick fix when you\'ll iterate on the prompt later',
    });
  }

  // Fix 2: Simplify Prompt
  const promptAnalysis = analyzeLatencyPrompt(call);
  if (promptAnalysis.encourages_verbosity || call.completion_tokens > 1000) {
    fixes.push({
      id: 'simplify_prompt',
      title: 'Simplify Prompt',
      subtitle: 'Better Fix - Guided Output',
      effort: 'Medium',
      effortColor: 'text-yellow-400',
      
      metrics: [
        {
          label: 'Latency',
          before: `${(call.latency_ms / 1000).toFixed(1)}s`,
          after: '~2.0s',
          changePercent: -84,
        },
        {
          label: 'Tokens',
          before: call.completion_tokens.toLocaleString(),
          after: '~200',
          changePercent: -91,
        },
        {
          label: 'Cost',
          before: `$${call.total_cost.toFixed(3)}`,
          after: '$0.03',
          changePercent: -82,
        },
        {
          label: 'Quality',
          before: 'Complete',
          after: '✅ Complete',
          changePercent: 0,
        },
      ],
      
      codeBefore: `# BEFORE - Your current prompt
system_prompt = """
Provide a COMPREHENSIVE analysis covering:
1. Skills alignment
2. Experience match  
3. Education analysis
4. Cultural fit assessment
5. Potential red flags
6. Suggested interview questions
7. Final recommendations
"""`,
      codeAfter: `# AFTER - Simplified prompt
system_prompt = """
Provide a brief assessment with:
- Match score (1-10)
- Top 3 strengths  
- Top 2 concerns
- Recommendation (proceed/pass/maybe)

Keep response under 150 words.
"""`,
      
      outputPreview: `**Match Score: 8.5/10**

**Top Strengths:**
1. Strong Python and cloud architecture experience (6+ years)
2. Proven leadership with enterprise clients at Syndigo
3. Hands-on AI/ML project experience with production systems

**Concerns:**
1. No direct machine learning model training experience
2. Relatively short tenure at most recent role (1.5 years)

**Recommendation:** Proceed to technical interview

The candidate's strong technical foundation and enterprise 
experience outweigh the concerns. Recommend focusing the 
interview on ML fundamentals and long-term career goals.`,
      outputNote: '✅ Complete, coherent, actionable response',
      outputNoteColor: 'text-green-400',
      
      tradeoffs: [
        'Requires prompt engineering effort',
        'Less detail when you need deep analysis',
        'May need iteration to get right',
      ],
      benefits: [
        'Complete, coherent output',
        'Human-readable format',
        'Actionable recommendations',
        'Natural language flexibility',
      ],
      bestFor: 'When you need readable output for humans to review',
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

  // Fix 4: Truncate history
  if (factors.some(f => f.id === 'large_history')) {
    fixes.push({
      id: 'truncate_history',
      title: 'Truncate History',
      subtitle: 'Context Management',
      effort: 'Low',
      effortColor: 'text-green-400',
      
      metrics: [
        {
          label: 'Prompt',
          before: call.prompt_tokens.toLocaleString(),
          after: Math.round(call.prompt_tokens * 0.4).toLocaleString(),
          changePercent: -60,
        },
        {
          label: 'TTFT',
          before: `${((call.ttft_ms || 0) / 1000).toFixed(1)}s`,
          after: `${(((call.ttft_ms || 0) * 0.4) / 1000).toFixed(1)}s`,
          changePercent: -60,
        },
        {
          label: 'Cost',
          before: `$${call.total_cost.toFixed(3)}`,
          after: `$${(call.total_cost * 0.6).toFixed(3)}`,
          changePercent: -40,
        },
        {
          label: 'Quality',
          before: 'Full context',
          after: 'Recent only',
          changePercent: 0,
        },
      ],
      
      codeBefore: `messages = conversation_history  # Full history: ${call.chat_history_tokens?.toLocaleString() || 0} tokens`,
      codeAfter: `MAX_HISTORY = 10  # Keep last N messages

def truncate_history(messages):
    system = messages[0] if messages[0]["role"] == "system" else None
    recent = messages[-MAX_HISTORY:]
    return [system] + recent if system else recent

messages = truncate_history(conversation_history)`,
      
      outputPreview: `Before: 50 messages in history (3,500 tokens)
After: 10 most recent messages (700 tokens)

Model still has enough context for coherent responses,
but processes 5x less input data.`,
      outputNote: '✅ Faster responses, lower cost, usually same quality',
      outputNoteColor: 'text-green-400',
      
      tradeoffs: [
        'Loses older conversation context',
        'May forget early instructions',
        'Not suitable for long-running analysis',
      ],
      benefits: [
        'Significant latency reduction',
        'Lower token costs',
        'Simple to implement',
        'Works for most chat applications',
      ],
      bestFor: 'Chat applications where recent context is most important',
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