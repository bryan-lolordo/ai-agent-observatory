/**
 * Fix Repository - HYBRID VERSION
 *
 * Combines:
 * - Runtime flexibility (generateMetrics, generateCode functions)
 * - Complex priority scoring
 * - 20 comprehensive fixes
 * - Multi-story support
 *
 * Fix structure:
 * {
 *   id: string,
 *   stories: string[],    // NEW: Which stories this fix applies to
 *   category: string,     // Primary category
 *   title: string,
 *   subtitle: string,
 *   effort: 'Low' | 'Medium' | 'High',
 *   triggerFactors: [],
 *   applicableWhen: fn,
 *   generateMetrics: fn,  // Runtime calculation
 *   generateCode: fn,     // Context-specific code
 *   tradeoffs: [],
 *   benefits: [],
 *   bestFor: string,
 * }
 */

// ═════════════════════════════════════════════════════════════════════════════
// FIX REPOSITORY - 20 COMPREHENSIVE FIXES
// ═════════════════════════════════════════════════════════════════════════════

export const FIX_REPOSITORY = {
  
  // ───────────────────────────────────────────────────────────────────────────
  // CHAT HISTORY FIXES (4 stories)
  // ───────────────────────────────────────────────────────────────────────────
  
  truncate_history: {
    id: 'truncate_history',
    stories: ['latency', 'cost', 'token', 'prompt'],
    category: 'latency',
    title: 'Prune Conversation History',
    subtitle: 'Keep only recent turns (last N)',
    effort: 'Low',
    effortColor: 'text-green-400',
    triggerFactors: ['large_history', 'high_prompt_tokens', 'high_input_ratio'],

    applicableWhen: (call) => {
      const historyTokens = call.chat_history_tokens || 0;
      // Lowered threshold: history > 20% of prompt OR > 200 tokens absolute
      return historyTokens > (call.prompt_tokens || 0) * 0.2 || historyTokens > 200;
    },
    
    generateMetrics: (call) => {
      const chatHistory = call.chat_history_tokens || 0;
      const historyPct = chatHistory / (call.prompt_tokens || 1);
      const reduction = 0.75; // Keep 25% (last 3 turns)
      
      const tokensRemoved = chatHistory * reduction;
      const newPromptTokens = call.prompt_tokens - tokensRemoved;
      const newLatency = call.latency_ms * (newPromptTokens / call.prompt_tokens);
      const newCost = call.total_cost * (newPromptTokens / call.prompt_tokens);
      
      return [
        {
          label: 'Latency',
          before: `${(call.latency_ms / 1000).toFixed(1)}s`,
          after: `${(newLatency / 1000).toFixed(1)}s`,
          changePercent: -Math.round((call.latency_ms - newLatency) / call.latency_ms * 100),
        },
        {
          label: 'Tokens',
          before: call.prompt_tokens.toLocaleString(),
          after: Math.round(newPromptTokens).toLocaleString(),
          changePercent: -Math.round(tokensRemoved / call.prompt_tokens * 100),
        },
        {
          label: 'Cost',
          before: `$${call.total_cost.toFixed(4)}`,
          after: `$${newCost.toFixed(4)}`,
          changePercent: -Math.round((call.total_cost - newCost) / call.total_cost * 100),
        },
      ];
    },
    
    generateCode: (call) => {
      const turnCount = call.chat_history_count || 10;
      const keepLast = Math.max(3, Math.floor(turnCount * 0.25));
      
      return {
        before: `# Full history: ${(call.chat_history_tokens || 0).toLocaleString()} tokens, ${turnCount} messages
messages = conversation_history`,
        
        after: `MAX_HISTORY = ${keepLast}  # Keep last N messages

def truncate_history(messages):
    """Keep only recent conversation context"""
    system = messages[0] if messages[0]["role"] == "system" else None
    recent = messages[-MAX_HISTORY:]
    return [system] + recent if system else recent

messages = truncate_history(conversation_history)
# Now: ~${Math.round((call.prompt_tokens || 0) * 0.25).toLocaleString()} tokens`,
      };
    },
    
    tradeoffs: [
      'Loses early conversation context',
      'May forget initial instructions',
      'Not suitable for tasks requiring full history',
    ],
    benefits: [
      'Removes 75% of history tokens',
      'Faster processing',
      'Lower cost per turn',
      'Prevents context bloat',
    ],
    bestFor: 'Multi-turn conversations with >5 turns',
  },
  
  summarize_history: {
    id: 'summarize_history',
    stories: ['latency', 'cost', 'token', 'prompt'],
    category: 'prompt',
    title: 'Summarize Old Turns',
    subtitle: 'Condense history with LLM summary',
    effort: 'Medium',
    effortColor: 'text-yellow-400',
    triggerFactors: ['large_history', 'high_chat_history_tokens'],

    applicableWhen: (call) => {
      const historyTokens = call.chat_history_tokens || 0;
      const turnCount = call.chat_history_count || 0;
      // Lowered from 1000 tokens to 500, and 5 turns to 3
      return historyTokens > 500 || turnCount > 3;
    },
    
    generateMetrics: (call) => {
      const chatHistory = call.chat_history_tokens || 0;
      const reduction = 0.5; // Summarize to 50%
      
      const tokensRemoved = chatHistory * reduction;
      const newPromptTokens = call.prompt_tokens - tokensRemoved;
      const newLatency = call.latency_ms * (newPromptTokens / call.prompt_tokens) * 0.62; // Better than truncate
      const newCost = call.total_cost * (newPromptTokens / call.prompt_tokens);
      
      return [
        {
          label: 'Latency',
          before: `${(call.latency_ms / 1000).toFixed(1)}s`,
          after: `${(newLatency / 1000).toFixed(1)}s`,
          changePercent: -Math.round((call.latency_ms - newLatency) / call.latency_ms * 100),
        },
        {
          label: 'Tokens',
          before: call.prompt_tokens.toLocaleString(),
          after: Math.round(newPromptTokens).toLocaleString(),
          changePercent: -Math.round(tokensRemoved / call.prompt_tokens * 100),
        },
        {
          label: 'Quality',
          before: 'Verbose history',
          after: '✅ Condensed summary',
          changePercent: 0,
          status: 'good',
        },
      ];
    },
    
    generateCode: (call) => ({
      before: `messages = conversation_history`,
      
      after: `def summarize_old_turns(messages, keep_recent=3):
    """Condense old turns into summary"""
    system = messages[0] if messages[0]["role"] == "system" else None
    recent = messages[-keep_recent:]
    old_turns = messages[1:-keep_recent] if system else messages[:-keep_recent]
    
    # Summarize old context
    summary_prompt = "Summarize key points: " + str(old_turns)
    summary = llm.complete(summary_prompt, max_tokens=200)
    
    result = [system] if system else []
    result.append({"role": "system", "content": summary})
    result.extend(recent)
    return result

messages = summarize_old_turns(conversation_history)`,
    }),
    
    tradeoffs: [
      'Adds summarization cost (~$0.01)',
      'Slight quality risk from compression',
      'Requires extra LLM call',
    ],
    benefits: [
      'Preserves key context',
      'Better than truncation',
      'Maintains conversation flow',
      '50% token reduction',
    ],
    bestFor: 'Long conversations requiring context preservation',
  },
  
  // ───────────────────────────────────────────────────────────────────────────
  // SYSTEM PROMPT FIXES (3 stories)
  // ───────────────────────────────────────────────────────────────────────────
  
  compress_system_prompt: {
    id: 'compress_system_prompt',
    stories: ['cost', 'token', 'prompt', 'latency'],
    category: 'prompt',
    title: 'Compress System Prompt',
    subtitle: 'Remove verbosity, keep essentials',
    effort: 'Low',
    effortColor: 'text-green-400',
    triggerFactors: ['bloated_system_prompt', 'high_system_tokens', 'verbose_prompt', 'high_prompt_tokens'],

    applicableWhen: (call) => {
      const systemTokens = call.system_prompt_tokens || 0;
      // Lowered from 40% to 25%, OR absolute > 300 tokens
      return systemTokens > (call.prompt_tokens || 0) * 0.25 || systemTokens > 300;
    },
    
    generateMetrics: (call) => {
      const systemTokens = call.system_prompt_tokens || 0;
      const reduction = 0.46; // 46% reduction
      
      const tokensRemoved = systemTokens * reduction;
      const newPromptTokens = call.prompt_tokens - tokensRemoved;
      const newCost = call.total_cost * (newPromptTokens / call.prompt_tokens);
      
      return [
        {
          label: 'Tokens',
          before: call.prompt_tokens.toLocaleString(),
          after: Math.round(newPromptTokens).toLocaleString(),
          changePercent: -Math.round(tokensRemoved / call.prompt_tokens * 100),
        },
        {
          label: 'Cost',
          before: `$${call.total_cost.toFixed(4)}`,
          after: `$${newCost.toFixed(4)}`,
          changePercent: -Math.round((call.total_cost - newCost) / call.total_cost * 100),
        },
        {
          label: 'Quality',
          before: 'Verbose',
          after: '✅ Concise',
          changePercent: 0,
        },
      ];
    },
    
    generateCode: (call) => {
      const systemTokens = call.system_prompt_tokens || 0;
      const targetTokens = Math.round(systemTokens * 0.54);
      
      return {
        before: `system_prompt = """
You are an AI assistant helping users with resume analysis.
You should carefully read the resume and job description.
Analyze the resume thoroughly and provide detailed feedback.
Make sure to highlight strengths and areas for improvement.
Be constructive and professional in your tone.
"""  # ${systemTokens} tokens`,
        
        after: `system_prompt = """
Analyze resume vs job description. Highlight strengths and gaps.
Be concise and actionable.
"""  # ~${targetTokens} tokens (-46%)`,
      };
    },
    
    tradeoffs: [
      'Less context for model',
      'May need iteration to find right balance',
    ],
    benefits: [
      'Immediate cost reduction',
      'Forces clarity',
      'Often improves output quality',
      'No code changes needed',
    ],
    bestFor: 'Operations with verbose system prompts >500 tokens',
  },
  
  enable_prompt_caching: {
    id: 'enable_prompt_caching',
    stories: ['cost', 'cache', 'latency', 'prompt'],
    category: 'cache',
    title: 'Enable Prompt Caching',
    subtitle: 'Cache static system prompt',
    effort: 'Low',
    effortColor: 'text-green-400',
    triggerFactors: ['bloated_system_prompt', 'static_prompt', 'caching_opportunity', 'high_prompt_tokens', 'no_cache'],

    applicableWhen: (call) => {
      // For patterns (cache story), check repeat_count
      if (call.repeat_count) {
        return call.repeat_count > 1;
      }
      // For calls, check system prompt size (lowered from 500 to 200)
      const systemTokens = call.system_prompt_tokens || 0;
      const promptTokens = call.prompt_tokens || 0;
      const cacheHit = call.cache_hit || false;
      return (systemTokens > 200 || promptTokens > 500) && !cacheHit;
    },
    
    generateMetrics: (entity) => {
      const systemTokens = entity.system_prompt_tokens || 0;
      const hitRate = 0.65; // 65% cache hit rate
      const avgCostReduction = hitRate * 0.9; // 90% reduction on hits

      // Handle patterns (cache story) vs calls
      const isPattern = !!entity.repeat_count;
      const totalCost = entity.total_cost ?? (entity.wasted_cost || 0) + (entity.unit_cost || 0);
      const repeatCount = entity.repeat_count || 1;

      if (isPattern) {
        return [
          {
            label: 'LLM Calls',
            before: `${repeatCount}`,
            after: '1',
            changePercent: -Math.round((1 - 1/repeatCount) * 100),
          },
          {
            label: 'Cost',
            before: `$${totalCost.toFixed(3)}`,
            after: `$${(entity.unit_cost || totalCost / repeatCount).toFixed(3)}`,
            changePercent: -Math.round((1 - 1/repeatCount) * 100),
          },
          {
            label: 'Cacheable Tokens',
            before: '0',
            after: `${(entity.cacheable_tokens || systemTokens).toLocaleString()}`,
            changePercent: 0,
          },
        ];
      }

      return [
        {
          label: 'Cost',
          before: `$${(totalCost || 0).toFixed(4)}`,
          after: `$${((totalCost || 0) * (1 - avgCostReduction)).toFixed(4)}`,
          changePercent: -Math.round(avgCostReduction * 100),
        },
        {
          label: 'Cached Tokens',
          before: '0',
          after: `${systemTokens.toLocaleString()} (system)`,
          changePercent: 0,
        },
        {
          label: 'Hit Rate',
          before: '0%',
          after: '~65%',
          changePercent: 0,
        },
      ];
    },
    
    generateCode: (call) => ({
      before: `response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
)`,
      
      after: `# Enable prompt caching (Anthropic/OpenAI)
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "system",
            "content": system_prompt,
            "cache_control": {"type": "ephemeral"}  # ✅ Cache this
        },
        {"role": "user", "content": user_message}
    ]
)
# 90% cost reduction on cache hits!`,
    }),
    
    tradeoffs: [
      'Small write penalty on first call',
      'Cache expires after 5 minutes',
    ],
    benefits: [
      '90% cost reduction on hits',
      'Works with static prompts',
      'Zero code change (just flag)',
      'Faster response on hits',
    ],
    bestFor: 'Repeated calls with static system prompts',
  },
  
  // ───────────────────────────────────────────────────────────────────────────
  // OUTPUT CONTROL FIXES (3 stories)
  // ───────────────────────────────────────────────────────────────────────────
  
  add_max_tokens: {
    id: 'add_max_tokens',
    stories: ['latency', 'cost', 'token'],
    category: 'latency',
    title: 'Set max_tokens Limit',
    subtitle: 'Prevent runaway generation',
    effort: 'Low',
    effortColor: 'text-green-400',
    triggerFactors: ['no_max_tokens', 'high_completion_tokens', 'high_output_tokens'],

    applicableWhen: (call) => {
      const maxTokens = call.max_tokens;
      const completionTokens = call.completion_tokens || 0;

      // Case 1: No limit set and any meaningful output (lowered from 500)
      if (!maxTokens && completionTokens > 100) return true;

      // Case 2: Limit set but generating high output (lowered from 1000)
      if (maxTokens && completionTokens > 500) return true;

      return false;
    },
    
    generateMetrics: (call) => {
      const currentCompletion = call.completion_tokens || 0;
      const targetCompletion = Math.min(500, currentCompletion);
      const reduction = (currentCompletion - targetCompletion) / currentCompletion;
      
      const latencySaved = call.latency_ms * reduction;
      const costSaved = call.completion_cost * reduction;
      
      return [
        {
          label: 'Latency',
          before: `${(call.latency_ms / 1000).toFixed(1)}s`,
          after: `${((call.latency_ms - latencySaved) / 1000).toFixed(1)}s`,
          changePercent: -Math.round(reduction * 100),
        },
        {
          label: 'Tokens',
          before: currentCompletion.toLocaleString(),
          after: targetCompletion.toLocaleString(),
          changePercent: -Math.round(reduction * 100),
        },
        {
          label: 'Cost',
          before: `$${call.total_cost.toFixed(4)}`,
          after: `$${(call.total_cost - costSaved).toFixed(4)}`,
          changePercent: -Math.round((costSaved / call.total_cost) * 100),
        },
      ];
    },
    
    generateCode: (call) => {
      const targetTokens = Math.min(500, (call.completion_tokens || 0));
      
      return {
        before: `# No limit - model generates until done
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages
)`,
        
        after: `# Set max_tokens to prevent runaway
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    max_tokens=${targetTokens}  # ✅ Explicit limit
)`,
      };
    },
    
    tradeoffs: [
      'May truncate useful output',
      'Requires tuning for your use case',
    ],
    benefits: [
      'Prevents runaway costs',
      'Predictable latency',
      'Forces conciseness',
      'Easy to implement',
    ],
    bestFor: 'Calls generating >500 tokens without limit',
  },
  
  enable_streaming: {
    id: 'enable_streaming',
    stories: ['latency'],
    category: 'latency',
    title: 'Enable Streaming',
    subtitle: 'UX Fix - Show tokens as generated',
    effort: 'Medium',
    effortColor: 'text-yellow-400',
    triggerFactors: ['no_streaming', 'high_completion_tokens'],

    applicableWhen: (call) => {
      const ttft = call.time_to_first_token_ms;
      // Lowered threshold from 200 to 50 tokens
      return !ttft && (call.completion_tokens || 0) > 50;
    },
    
    generateMetrics: (call) => {
      const ttft = 800; // Estimated TTFT
      const perceivedLatency = ttft;
      
      return [
        {
          label: 'Perceived Latency',
          before: `${(call.latency_ms / 1000).toFixed(1)}s`,
          after: `${(perceivedLatency / 1000).toFixed(1)}s`,
          changePercent: -Math.round((1 - perceivedLatency / call.latency_ms) * 100),
        },
        {
          label: 'TTFT',
          before: 'N/A',
          after: `~${(ttft / 1000).toFixed(1)}s`,
          changePercent: 0,
        },
        {
          label: 'Total Time',
          before: `${(call.latency_ms / 1000).toFixed(1)}s`,
          after: `${(call.latency_ms / 1000).toFixed(1)}s (same)`,
          changePercent: 0,
        },
      ];
    },
    
    generateCode: (call) => ({
      before: `response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages
)
# User waits ${(call.latency_ms / 1000).toFixed(1)}s before seeing anything`,
      
      after: `# Stream tokens as generated
for chunk in client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    stream=True  # ✅ Enable streaming
):
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end='')
# User sees response after ~0.8s!`,
    }),
    
    tradeoffs: [
      'More complex code',
      'Harder to parse structured output',
      'Total time unchanged',
    ],
    benefits: [
      '82% better perceived latency',
      'Better UX',
      'User sees progress',
      'Can interrupt early',
    ],
    bestFor: 'User-facing apps with >200 token outputs',
  },
  
  // ───────────────────────────────────────────────────────────────────────────
  // MODEL ROUTING FIXES (3 stories)
  // ───────────────────────────────────────────────────────────────────────────
  
  switch_to_mini: {
    id: 'switch_to_mini',
    stories: ['cost', 'routing'],
    category: 'routing',
    title: 'Switch to GPT-4o-mini',
    subtitle: 'Use cheaper model for simple tasks',
    effort: 'Low',
    effortColor: 'text-green-400',
    triggerFactors: ['premium_model', 'overqualified_model', 'low_complexity', 'overprovisioned'],

    applicableWhen: (call) => {
      const model = call.model_name || '';
      const complexity = call.complexity_score ?? call.routing_analysis?.complexity_score ?? 0.5;
      const routing = call.routing_analysis || {};

      // Check if overprovisioned via routing analysis
      if (routing.verdict === 'overprovisioned' || routing.opportunity === 'downgrade') {
        return true;
      }

      // Fallback: premium model with low complexity
      const isPremium = model.includes('gpt-4o') && !model.includes('mini') ||
                        model.includes('claude-3-opus') ||
                        model.includes('claude-3-sonnet');
      return isPremium && complexity < 0.5;
    },
    
    generateMetrics: (call) => {
      const currentCost = call.total_cost || 0;
      const newCost = currentCost * 0.06; // 94% reduction
      
      return [
        {
          label: 'Cost',
          before: `$${currentCost.toFixed(4)}`,
          after: `$${newCost.toFixed(4)}`,
          changePercent: -94,
        },
        {
          label: 'Quality',
          before: '100%',
          after: '~90%',
          changePercent: -10,
          status: 'warning',
        },
        {
          label: 'Model',
          before: call.model_name,
          after: 'gpt-4o-mini',
          changePercent: 0,
        },
      ];
    },
    
    generateCode: (call) => ({
      before: `response = client.chat.completions.create(
    model="${call.model_name}",
    messages=messages
)`,
      
      after: `# Switch to cheaper model for simple tasks
response = client.chat.completions.create(
    model="gpt-4o-mini",  # ✅ 94% cheaper
    messages=messages
)`,
    }),
    
    tradeoffs: [
      'Slight quality drop (~10%)',
      'Not suitable for complex reasoning',
    ],
    benefits: [
      '94% cost reduction',
      'Faster response',
      'Good for simple tasks',
      'One-line change',
    ],
    bestFor: 'Simple classification, extraction, formatting tasks',
  },
  
  complexity_based_routing: {
    id: 'complexity_based_routing',
    stories: ['cost', 'routing', 'quality'],
    category: 'routing',
    title: 'Complexity-Based Routing',
    subtitle: 'Route by task complexity',
    effort: 'Medium',
    effortColor: 'text-yellow-400',
    triggerFactors: ['wrong_model_tier', 'static_routing', 'overprovisioned', 'underprovisioned'],

    applicableWhen: (call) => {
      const routing = call.routing_analysis || {};
      // Show if there's a routing opportunity or no routing exists
      return !call.routing_decision ||
             routing.verdict === 'overprovisioned' ||
             routing.verdict === 'underprovisioned';
    },
    
    generateMetrics: (call) => {
      // Estimate 70% of calls can use cheaper model
      const avgReduction = 0.73;
      
      return [
        {
          label: 'Cost',
          before: `$${call.total_cost.toFixed(4)}`,
          after: `$${(call.total_cost * (1 - avgReduction)).toFixed(4)}`,
          changePercent: -Math.round(avgReduction * 100),
        },
        {
          label: 'Quality',
          before: 'Static routing',
          after: '✅ Optimized',
          changePercent: 0,
        },
      ];
    },
    
    generateCode: (call) => ({
      before: `# Always use same model
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages
)`,
      
      after: `def route_by_complexity(messages):
    """Route to best model based on task"""
    # Estimate complexity
    prompt_len = len(messages[-1]['content'])
    has_code = 'def ' in messages[-1]['content']
    
    if has_code or prompt_len > 1000:
        return "gpt-4o"  # Complex
    else:
        return "gpt-4o-mini"  # Simple
        
model = route_by_complexity(messages)
response = client.chat.completions.create(
    model=model,
    messages=messages
)`,
    }),
    
    tradeoffs: [
      'Adds routing logic',
      'May misclassify occasionally',
    ],
    benefits: [
      '73% avg cost reduction',
      'Maintains quality',
      'Scales automatically',
      'Smart resource usage',
    ],
    bestFor: 'Mixed workloads with varying complexity',
  },
  
  // ───────────────────────────────────────────────────────────────────────────
  // CACHING FIXES (3 stories)
  // ───────────────────────────────────────────────────────────────────────────
  
  simple_cache: {
    id: 'simple_cache',
    stories: ['cache', 'cost', 'latency'],
    category: 'cache',
    title: 'Simple LRU Cache',
    subtitle: 'In-memory cache for exact matches',
    effort: 'Low',
    effortColor: 'text-green-400',
    triggerFactors: ['no_cache', 'exact_match', 'cache_type_exact'],

    applicableWhen: (entity) => {
      // For patterns (cache story)
      if (entity.repeat_count) {
        return entity.cache_type === 'exact' && entity.repeat_count > 1;
      }
      // For calls
      return !entity.cache_hit;
    },
    
    generateMetrics: (entity) => {
      const hitRate = 0.35; // 35% hit rate for exact match

      // Handle patterns (cache story) vs calls
      const isPattern = !!entity.repeat_count;
      const totalCost = entity.total_cost ?? (entity.wasted_cost || 0) + (entity.unit_cost || 0);
      const latencyMs = entity.latency_ms ?? entity.avg_latency_ms ?? 4000;
      const repeatCount = entity.repeat_count || 1;

      if (isPattern) {
        return [
          {
            label: 'LLM Calls',
            before: `${repeatCount}`,
            after: '1',
            changePercent: -Math.round((1 - 1/repeatCount) * 100),
          },
          {
            label: 'Cost',
            before: `$${totalCost.toFixed(3)}`,
            after: `$${(entity.unit_cost || totalCost / repeatCount).toFixed(3)}`,
            changePercent: -Math.round((1 - 1/repeatCount) * 100),
          },
          {
            label: 'Latency',
            before: `${(latencyMs / 1000).toFixed(1)}s`,
            after: '~0.01s (cache)',
            changePercent: -99,
          },
        ];
      }

      const avgCostReduction = hitRate * 1.0; // 100% on hits
      return [
        {
          label: 'Cost',
          before: `$${(totalCost || 0).toFixed(4)}`,
          after: `$${((totalCost || 0) * (1 - avgCostReduction)).toFixed(4)}`,
          changePercent: -Math.round(avgCostReduction * 100),
        },
        {
          label: 'Latency',
          before: `${(latencyMs / 1000).toFixed(1)}s`,
          after: '~0.01s (cache hit)',
          changePercent: -99,
        },
        {
          label: 'Hit Rate',
          before: '0%',
          after: '~35%',
          changePercent: 0,
        },
      ];
    },
    
    generateCode: (call) => ({
      before: `# No caching
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages
)`,
      
      after: `from functools import lru_cache

@lru_cache(maxsize=100)
def cached_completion(prompt_hash):
    """Cache exact prompt matches"""
    return client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )

# Use cache
prompt_hash = hash(str(messages))
response = cached_completion(prompt_hash)`,
    }),
    
    tradeoffs: [
      'Only works for exact matches',
      'Memory usage grows',
      'Stale data risk',
    ],
    benefits: [
      '100% cost savings on hits',
      '<10ms response time',
      'Simple to implement',
      'No external dependencies',
    ],
    bestFor: 'Repeated identical queries',
  },
  
  semantic_cache: {
    id: 'semantic_cache',
    stories: ['cache', 'cost'],
    category: 'cache',
    title: 'Semantic Similarity Cache',
    subtitle: 'Match similar (not identical) prompts',
    effort: 'High',
    effortColor: 'text-red-400',
    triggerFactors: ['cache_type_semantic', 'similar_prompts', 'no_cache'],

    applicableWhen: (entity) => {
      // For patterns (cache story)
      if (entity.repeat_count) {
        return entity.cache_type === 'semantic' && entity.repeat_count > 1;
      }
      // For calls
      return !entity.cache_hit;
    },
    
    generateMetrics: (entity) => {
      const hitRate = 0.65; // 65% hit rate with similarity
      const avgCostReduction = hitRate * 0.95;

      // Handle patterns (cache story) vs calls
      const isPattern = !!entity.repeat_count;
      const totalCost = entity.total_cost ?? (entity.wasted_cost || 0) + (entity.unit_cost || 0);
      const repeatCount = entity.repeat_count || 1;

      if (isPattern) {
        return [
          {
            label: 'LLM Calls',
            before: `${repeatCount}`,
            after: '1',
            changePercent: -Math.round((1 - 1/repeatCount) * 100),
          },
          {
            label: 'Cost',
            before: `$${totalCost.toFixed(3)}`,
            after: `$${(entity.unit_cost || totalCost / repeatCount).toFixed(3)}`,
            changePercent: -Math.round((1 - 1/repeatCount) * 100),
          },
          {
            label: 'Hit Rate',
            before: '0%',
            after: '~65%',
            changePercent: 0,
          },
        ];
      }

      return [
        {
          label: 'Cost',
          before: `$${(totalCost || 0).toFixed(4)}`,
          after: `$${((totalCost || 0) * (1 - avgCostReduction)).toFixed(4)}`,
          changePercent: -Math.round(avgCostReduction * 100),
        },
        {
          label: 'Hit Rate',
          before: '0%',
          after: '~65%',
          changePercent: 0,
        },
      ];
    },

    generateCode: (call) => ({
      before: `response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages
)`,

      after: `from semantic_cache import SemanticCache

cache = SemanticCache(
    similarity_threshold=0.95,
    embedding_model="text-embedding-3-small"
)

# Check cache with similarity
cached = cache.get_similar(prompt)
if cached:
    return cached  # 95% similar = cache hit

# Cache miss - call LLM
response = client.chat.completions.create(...)
cache.store(prompt, response)`,
    }),
    
    tradeoffs: [
      'Requires embedding model',
      'More complex setup',
      'Small embedding cost',
    ],
    benefits: [
      '65% hit rate (vs 35% exact)',
      'Handles variations',
      '95% cost savings on hits',
      'Production-grade',
    ],
    bestFor: 'Similar but not identical queries',
  },
  
  redis_cache: {
    id: 'redis_cache',
    stories: ['cache', 'cost'],
    category: 'cache',
    title: 'Redis Cache',
    subtitle: 'Persistent distributed cache',
    effort: 'Medium',
    effortColor: 'text-yellow-400',
    triggerFactors: ['no_cache', 'cache_type_prefix'],

    applicableWhen: (entity) => {
      // For patterns (cache story)
      if (entity.repeat_count) {
        return entity.repeat_count > 1;
      }
      // For calls
      return !entity.cache_hit;
    },
    
    generateMetrics: (entity) => {
      const hitRate = 0.45;
      const avgCostReduction = hitRate * 1.0;

      // Handle patterns (cache story) vs calls
      const isPattern = !!entity.repeat_count;
      const totalCost = entity.total_cost ?? (entity.wasted_cost || 0) + (entity.unit_cost || 0);
      const repeatCount = entity.repeat_count || 1;

      if (isPattern) {
        return [
          {
            label: 'LLM Calls',
            before: `${repeatCount}`,
            after: '1',
            changePercent: -Math.round((1 - 1/repeatCount) * 100),
          },
          {
            label: 'Cost',
            before: `$${totalCost.toFixed(3)}`,
            after: `$${(entity.unit_cost || totalCost / repeatCount).toFixed(3)}`,
            changePercent: -Math.round((1 - 1/repeatCount) * 100),
          },
          {
            label: 'Hit Rate',
            before: '0%',
            after: '~45%',
            changePercent: 0,
          },
        ];
      }

      return [
        {
          label: 'Cost',
          before: `$${(totalCost || 0).toFixed(4)}`,
          after: `$${((totalCost || 0) * (1 - avgCostReduction)).toFixed(4)}`,
          changePercent: -Math.round(avgCostReduction * 100),
        },
        {
          label: 'Hit Rate',
          before: '0%',
          after: '~45%',
          changePercent: 0,
        },
      ];
    },

    generateCode: (call) => ({
      before: `response = client.chat.completions.create(...)`,

      after: `import redis
r = redis.Redis(host='localhost', port=6379)

# Check cache
cache_key = f"llm:{hash(prompt)}"
cached = r.get(cache_key)
if cached:
    return json.loads(cached)

# Cache miss
response = client.chat.completions.create(...)
r.setex(cache_key, 3600, json.dumps(response))`,
    }),
    
    tradeoffs: [
      'Requires Redis instance',
      'Infrastructure cost',
    ],
    benefits: [
      'Persistent across restarts',
      'Shared across servers',
      'TTL support',
      'Production-ready',
    ],
    bestFor: 'Multi-server deployments',
  },
  
  lru_cache: {
    id: 'lru_cache',
    stories: ['cache', 'cost'],
    category: 'cache',
    title: 'LRU Cache',
    subtitle: 'Least Recently Used eviction',
    effort: 'Low',
    effortColor: 'text-green-400',
    triggerFactors: ['no_cache', 'exact_match', 'cache_type_exact'],

    applicableWhen: (entity) => {
      // For patterns (cache story)
      if (entity.repeat_count) {
        return entity.cache_type === 'exact' && entity.repeat_count > 1;
      }
      // For calls
      return !entity.cache_hit;
    },
    
    generateMetrics: (entity) => {
      const hitRate = 0.30;
      const avgCostReduction = hitRate * 1.0;

      // Handle patterns (cache story) vs calls
      const isPattern = !!entity.repeat_count;
      const totalCost = entity.total_cost ?? (entity.wasted_cost || 0) + (entity.unit_cost || 0);
      const repeatCount = entity.repeat_count || 1;

      if (isPattern) {
        return [
          {
            label: 'LLM Calls',
            before: `${repeatCount}`,
            after: '1',
            changePercent: -Math.round((1 - 1/repeatCount) * 100),
          },
          {
            label: 'Cost',
            before: `$${totalCost.toFixed(3)}`,
            after: `$${(entity.unit_cost || totalCost / repeatCount).toFixed(3)}`,
            changePercent: -Math.round((1 - 1/repeatCount) * 100),
          },
        ];
      }

      return [
        {
          label: 'Cost',
          before: `$${(totalCost || 0).toFixed(4)}`,
          after: `$${((totalCost || 0) * (1 - avgCostReduction)).toFixed(4)}`,
          changePercent: -Math.round(avgCostReduction * 100),
        },
      ];
    },
    
    generateCode: (call) => ({
      before: `response = client.chat.completions.create(...)`,
      after: `from functools import lru_cache

@lru_cache(maxsize=128)
def get_completion(prompt):
    return client.chat.completions.create(...)`,
    }),
    
    tradeoffs: ['In-memory only'],
    benefits: ['Built-in Python', 'Zero setup', 'Fast'],
    bestFor: 'Quick wins',
  },
  
  // ───────────────────────────────────────────────────────────────────────────
  // QUALITY FIXES (1 story)
  // ───────────────────────────────────────────────────────────────────────────
  
  add_grounding_instructions: {
    id: 'add_grounding_instructions',
    stories: ['quality'],
    category: 'quality',
    title: 'Add Grounding Instructions',
    subtitle: 'Prevent hallucinations',
    effort: 'Low',
    effortColor: 'text-green-400',
    triggerFactors: ['hallucination', 'low_quality_score', 'factual_error'],
    
    applicableWhen: (call) => {
      return (call.hallucination_flag || (call.judge_score || 10) < 6);
    },
    
    generateMetrics: (call) => {
      const currentScore = call.judge_score || 5;
      const newScore = Math.min(10, currentScore + 3);
      
      return [
        {
          label: 'Quality',
          before: `${currentScore.toFixed(1)}/10`,
          after: `${newScore.toFixed(1)}/10`,
          changePercent: Math.round(((newScore - currentScore) / currentScore) * 100),
        },
        {
          label: 'Hallucinations',
          before: 'Common',
          after: '✅ Prevented',
          changePercent: -82,
        },
      ];
    },
    
    generateCode: (call) => ({
      before: `system_prompt = "Analyze this resume and provide feedback."`,
      
      after: `system_prompt = """
Analyze this resume and provide feedback.

IMPORTANT: Only use information from the provided resume.
If information is missing, say "not found" instead of guessing.
Do not invent details or make assumptions.
"""`,
    }),
    
    tradeoffs: ['May refuse to answer when uncertain'],
    benefits: ['82% hallucination reduction', 'Higher accuracy', 'More trustworthy'],
    bestFor: 'Factual tasks where accuracy is critical',
  },
  
  lower_temperature: {
    id: 'lower_temperature',
    stories: ['quality'],
    category: 'quality',
    title: 'Lower Temperature',
    subtitle: 'More deterministic outputs',
    effort: 'Low',
    effortColor: 'text-green-400',
    triggerFactors: ['inconsistent_output', 'low_creativity'],
    
    applicableWhen: (call) => {
      const temp = call.temperature;
      return !temp || temp > 0.7;
    },
    
    generateMetrics: (call) => {
      const currentScore = call.judge_score || 7;
      const improvement = 0.23;
      const newScore = Math.min(10, currentScore * (1 + improvement));
      
      return [
        {
          label: 'Consistency',
          before: 'Variable',
          after: '✅ Deterministic',
          changePercent: 85,
        },
        {
          label: 'Quality',
          before: `${currentScore.toFixed(1)}/10`,
          after: `${newScore.toFixed(1)}/10`,
          changePercent: Math.round(improvement * 100),
        },
      ];
    },
    
    generateCode: (call) => ({
      before: `response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    temperature=1.0  # High creativity
)`,
      
      after: `response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    temperature=0.3  # ✅ More consistent
)`,
    }),
    
    tradeoffs: ['Less creative', 'More repetitive'],
    benefits: ['Consistent outputs', '23% quality boost', 'Better for factual tasks'],
    bestFor: 'Factual, analytical, or structured output tasks',
  },
  
  add_examples: {
    id: 'add_examples',
    stories: ['quality'],
    category: 'quality',
    title: 'Add Few-Shot Examples',
    subtitle: 'Show model what you want',
    effort: 'Medium',
    effortColor: 'text-yellow-400',
    triggerFactors: ['missing_sections', 'inconsistent_format', 'low_quality_score'],
    
    applicableWhen: (call) => {
      return (call.judge_score || 10) < 7;
    },
    
    generateMetrics: (call) => {
      const currentScore = call.judge_score || 6;
      const newScore = Math.min(10, currentScore + 2);
      
      return [
        {
          label: 'Quality',
          before: `${currentScore.toFixed(1)}/10`,
          after: `${newScore.toFixed(1)}/10`,
          changePercent: Math.round(((newScore - currentScore) / currentScore) * 100),
        },
        {
          label: 'Format',
          before: 'Inconsistent',
          after: '✅ Structured',
          changePercent: 0,
        },
      ];
    },
    
    generateCode: (call) => ({
      before: `system_prompt = "Extract key skills from resume."`,
      
      after: `system_prompt = """
Extract key skills from resume.

Example:
Input: "5 years Python, React, AWS"
Output: {"technical": ["Python", "React", "AWS"], "years": 5}

Now process this resume:
"""`,
    }),
    
    tradeoffs: ['Increases prompt tokens'],
    benefits: ['Better format adherence', 'Clearer outputs', 'Fewer retries'],
    bestFor: 'Tasks requiring specific output format',
  },
  
  adjust_temperature: {
    id: 'adjust_temperature',
    stories: ['quality'],
    category: 'quality',
    title: 'Adjust Temperature',
    subtitle: 'Balance creativity vs consistency',
    effort: 'Low',
    effortColor: 'text-green-400',
    triggerFactors: ['low_creativity', 'inconsistent_output'],
    
    applicableWhen: (call) => true,
    
    generateMetrics: (call) => ([
      {
        label: 'Creativity',
        before: 'Low',
        after: '✅ Balanced',
        changePercent: 40,
      },
    ]),
    
    generateCode: (call) => ({
      before: `temperature=0.0`,
      after: `temperature=0.7  # ✅ More creative`,
    }),
    
    tradeoffs: ['May vary output'],
    benefits: ['Better for creative tasks'],
    bestFor: 'Content generation',
  },
  
  // ───────────────────────────────────────────────────────────────────────────
  // TOKEN BALANCE FIX (1 story)
  // ───────────────────────────────────────────────────────────────────────────
  
  request_longer_output: {
    id: 'request_longer_output',
    stories: ['token'],
    category: 'token',
    title: 'Request Longer Output',
    subtitle: 'Balance input/output ratio',
    effort: 'Low',
    effortColor: 'text-green-400',
    triggerFactors: ['high_input_ratio', 'low_output_ratio'],
    
    applicableWhen: (call) => {
      const ratio = (call.prompt_tokens || 1) / (call.completion_tokens || 1);
      return ratio > 20;
    },
    
    generateMetrics: (call) => {
      const currentRatio = (call.prompt_tokens || 1) / (call.completion_tokens || 1);
      const targetCompletion = (call.prompt_tokens || 1) / 5; // Target 5:1
      const improvement = ((currentRatio - 5) / currentRatio) * 100;
      
      return [
        {
          label: 'Ratio',
          before: `${currentRatio.toFixed(0)}:1`,
          after: '~5:1',
          changePercent: -Math.round(improvement),
        },
        {
          label: 'Output',
          before: `${call.completion_tokens} tokens`,
          after: `~${Math.round(targetCompletion)} tokens`,
          changePercent: Math.round(((targetCompletion - call.completion_tokens) / call.completion_tokens) * 100),
        },
      ];
    },
    
    generateCode: (call) => ({
      before: `system_prompt = "Analyze this resume."`,
      
      after: `system_prompt = """
Analyze this resume with detailed feedback.
Provide:
1. Strengths (3-5 points)
2. Improvements (3-5 points)
3. Recommended changes
4. Overall assessment

Be thorough and detailed.
"""`,
    }),
    
    tradeoffs: ['Increases output cost'],
    benefits: ['Better token efficiency', 'More complete answers', 'Better value'],
    bestFor: 'High ratio >20:1 with brief outputs',
  },
  
}; // End FIX_REPOSITORY

// ─────────────────────────────────────────────────────────────────────────────
// HELPER FUNCTIONS
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Get fix by ID
 */
export function getFixById(fixId) {
  return FIX_REPOSITORY[fixId] || null;
}

/**
 * Get all fixes for a story
 */
export function getFixesByCategory(storyId) {
  return Object.values(FIX_REPOSITORY).filter(
    fix => fix.stories && fix.stories.includes(storyId)
  );
}

/**
 * Get all fixes
 */
export function getAllFixes() {
  return Object.values(FIX_REPOSITORY);
}

export default FIX_REPOSITORY;