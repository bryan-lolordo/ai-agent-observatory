/**
 * Column Definitions for Layer2Table
 * 
 * All available columns from the database, organized by category.
 * Each column includes: key, label, sortable, filterable, width, formatter, category
 * 
 * MUST MATCH field names returned by API (llm_call_service.get_calls)
 */

// =============================================================================
// FORMATTERS
// =============================================================================

export const formatters = {
  // Identity
  callId: (value) => value ? `${value.substring(0, 8)}...` : '—',
  text: (value) => value || '—',
  truncate: (value, max = 40) => {
    if (!value) return '—';
    return value.length > max ? `${value.substring(0, max)}...` : value;
  },
  
  // Time & Latency
  latency: (ms) => {
    if (ms == null) return '—';
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  },
  timestamp: (value) => {
    if (!value) return '—';
    const date = new Date(value);
    return date.toLocaleString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  },
  date: (value) => {
    if (!value) return '—';
    return new Date(value).toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric' 
    });
  },
  
  // Numbers
  number: (value) => {
    if (value == null) return '—';
    return value.toLocaleString();
  },
  tokens: (value) => {
    if (value == null) return '—';
    return value.toLocaleString();
  },
  count: (value) => {
    if (value == null) return '—';
    return `${value}x`;
  },
  
  // Ratio (prompt:completion)
  ratio: (value) => {
    if (value == null) return '—';
    return `${value.toFixed(1)}:1`;
  },
  
  // Cost
  currency: (value) => {
    if (value == null) return '—';
    if (value === 0) return '$0.00';
    if (value < 0.001) return `$${value.toFixed(5)}`;
    if (value < 0.01) return `$${value.toFixed(4)}`;
    if (value < 1) return `$${value.toFixed(3)}`;
    return `$${value.toFixed(2)}`;
  },
  
  // Quality
  score: (value) => {
    if (value == null) return '—';
    return `${value.toFixed(1)}/10`;
  },
  percentage: (value) => {
    if (value == null) return '—';
    return `${(value * 100).toFixed(1)}%`;
  },
  confidence: (value) => {
    if (value == null) return '—';
    return `${(value * 100).toFixed(0)}%`;
  },
  
  // Boolean
  boolean: (value) => value ? '✓ Yes' : '—',
  cached: (value) => value ? '✓ Hit' : '✗ Miss',
  
  // Status
  status: (value) => {
    if (!value) return '—';
    if (value === 'success' || value === 'completed') return '✓ Success';
    if (value === 'error' || value === 'failed') return '✗ Error';
    return value;
  },
  
  // Cache effort
  effort: (value) => {
    if (!value) return '—';
    if (value === 'low') return '🟢';
    if (value === 'medium') return '🟡';
    return '🔴';
  },
};

// =============================================================================
// DYNAMIC VALUE COLORIZERS
// =============================================================================

export const colorizers = {
  // Latency: red > orange > yellow > green
  latency: (ms) => {
    if (ms == null) return 'text-gray-400';
    if (ms > 10000) return 'text-red-400 font-bold';
    if (ms > 5000) return 'text-orange-400 font-semibold';
    if (ms > 3000) return 'text-yellow-400';
    return 'text-green-400';
  },
  
  // Quality score: reversed (low is bad)
  quality: (score) => {
    if (score == null) return 'text-gray-400';
    if (score < 5) return 'text-red-400 font-bold';
    if (score < 7) return 'text-yellow-400';
    if (score < 8) return 'text-green-400';
    return 'text-emerald-400 font-semibold';
  },
  
  // Cost: high cost = red
  cost: (value) => {
    if (value == null) return 'text-gray-400';
    if (value > 0.10) return 'text-red-400 font-bold';
    if (value > 0.05) return 'text-orange-400 font-semibold';
    if (value > 0.01) return 'text-yellow-400';
    return 'text-green-400';
  },
  
  // Tokens: high = yellow/red
  tokens: (value) => {
    if (value == null) return 'text-gray-400';
    if (value > 4000) return 'text-red-400 font-bold';
    if (value > 2000) return 'text-orange-400';
    if (value > 1000) return 'text-yellow-400';
    return 'text-gray-300';
  },
  
  // Token ratio: imbalanced = red
  ratio: (value) => {
    if (value == null) return 'text-gray-400';
    if (value > 10) return 'text-red-400 font-bold';
    if (value > 5) return 'text-orange-400 font-semibold';
    if (value > 3) return 'text-yellow-400';
    return 'text-green-400';
  },
  
  // Status
  status: (value) => {
    if (value === 'success' || value === 'completed') return 'text-green-400';
    if (value === 'error' || value === 'failed') return 'text-red-400';
    return 'text-gray-400';
  },
  
  // Cached
  cached: (value) => value ? 'text-green-400' : 'text-gray-500',
  
  // Hallucination
  hallucination: (value) => value ? 'text-yellow-400' : 'text-gray-500',
  
  // Retry count
  retry: (value) => {
    if (value == null || value === 0) return 'text-gray-500';
    if (value > 2) return 'text-red-400';
    return 'text-yellow-400';
  },
  
  // Wasted cost (for cache)
  wastedCost: (value) => {
    if (value == null) return 'text-gray-400';
    if (value > 0.05) return 'text-red-400 font-bold';
    if (value > 0.01) return 'text-orange-400 font-semibold';
    if (value > 0.001) return 'text-yellow-400';
    return 'text-pink-400';
  },
  
  // Repeat count (for cache)
  repeatCount: (value) => {
    if (value == null) return 'text-gray-400';
    if (value > 10) return 'text-red-400 font-bold';
    if (value > 5) return 'text-orange-400 font-semibold';
    if (value > 2) return 'text-yellow-400';
    return 'text-pink-400';
  },
};

// =============================================================================
// COLUMN DEFINITIONS
// =============================================================================

export const ALL_COLUMNS = {
  // ─────────────────────────────────────────────────────────────────────────────
  // IDENTITY
  // ─────────────────────────────────────────────────────────────────────────────
  call_id: {
    key: 'call_id',
    label: 'Call ID',
    category: 'Identity',
    sortable: true,
    filterable: false,
    width: 'min-w-[100px]',
    align: 'left',
    formatter: formatters.callId,
    className: 'text-gray-500 font-mono',
  },
  agent_name: {
    key: 'agent_name',
    label: 'Agent',
    category: 'Identity',
    sortable: true,
    filterable: true,
    width: 'min-w-[120px]',
    align: 'left',
    formatter: formatters.text,
    className: 'text-purple-400 font-semibold',
  },
  operation: {
    key: 'operation',
    label: 'Operation',
    category: 'Identity',
    sortable: true,
    filterable: true,
    width: 'min-w-[150px]',
    align: 'left',
    formatter: (v) => formatters.truncate(v, 35),
    // className is dynamic based on story - set in component
    classNameBase: 'font-mono',
  },
  session_id: {
  key: 'session_id',
  label: 'Session',
  category: 'Identity',
  sortable: true,
  filterable: true,
  width: 'min-w-[100px]',
  align: 'left',
  formatter: formatters.callId,
  className: 'text-gray-500 font-mono',
  },
  call_type: {
    key: 'call_type',
    label: 'Type',
    category: 'Identity',
    sortable: true,
    filterable: true,
    width: 'min-w-[90px]',
    align: 'left',
    formatter: (v) => {
      const icons = { llm: '🤖', api: '🔌', database: '🗄️', tool: '🔧' };
      return `${icons[v] || '📦'} ${v || '—'}`;
    },
    className: 'text-gray-300 capitalize',
  },
  
  // ─────────────────────────────────────────────────────────────────────────────
  // PERFORMANCE
  // ─────────────────────────────────────────────────────────────────────────────
  latency_ms: {
    key: 'latency_ms',
    label: 'Latency',
    category: 'Performance',
    sortable: true,
    filterable: false,
    width: 'min-w-[90px]',
    align: 'right',
    formatter: formatters.latency,
    colorizer: colorizers.latency,
  },
  time_to_first_token_ms: {
    key: 'time_to_first_token_ms',
    label: 'TTFT',
    category: 'Performance',
    sortable: true,
    filterable: false,
    width: 'min-w-[80px]',
    align: 'right',
    formatter: formatters.latency,
    colorizer: colorizers.latency,
  },
  
  // ─────────────────────────────────────────────────────────────────────────────
  // TOKENS - BASIC
  // ─────────────────────────────────────────────────────────────────────────────
  prompt_tokens: {
    key: 'prompt_tokens',
    label: 'Prompt Tokens',
    category: 'Tokens',
    sortable: true,
    filterable: false,
    width: 'min-w-[110px]',
    align: 'right',
    formatter: formatters.tokens,
    className: 'text-blue-400',
  },
  completion_tokens: {
    key: 'completion_tokens',
    label: 'Completion',
    category: 'Tokens',
    sortable: true,
    filterable: false,
    width: 'min-w-[100px]',
    align: 'right',
    formatter: formatters.tokens,
    className: 'text-green-400',
  },
  total_tokens: {
    key: 'total_tokens',
    label: 'Total Tokens',
    category: 'Tokens',
    sortable: true,
    filterable: false,
    width: 'min-w-[100px]',
    align: 'right',
    formatter: formatters.tokens,
    colorizer: colorizers.tokens,
  },
  token_ratio: {
    key: 'token_ratio',
    label: 'Ratio',
    category: 'Tokens',
    sortable: true,
    filterable: false,
    width: 'min-w-[80px]',
    align: 'right',
    formatter: formatters.ratio,
    colorizer: colorizers.ratio,
  },
  
  // ─────────────────────────────────────────────────────────────────────────────
  // TOKENS - BREAKDOWN (Prompt Composition)
  // ─────────────────────────────────────────────────────────────────────────────
  system_prompt_tokens: {
    key: 'system_prompt_tokens',
    label: 'System Tokens',
    category: 'Tokens',
    sortable: true,
    filterable: false,
    width: 'min-w-[110px]',
    align: 'right',
    formatter: formatters.tokens,
    className: 'text-purple-400',
  },
  user_message_tokens: {
    key: 'user_message_tokens',
    label: 'User Tokens',
    category: 'Tokens',
    sortable: true,
    filterable: false,
    width: 'min-w-[100px]',
    align: 'right',
    formatter: formatters.tokens,
    className: 'text-cyan-400',
  },
  chat_history_tokens: {
    key: 'chat_history_tokens',
    label: 'History Tokens',
    category: 'Tokens',
    sortable: true,
    filterable: false,
    width: 'min-w-[110px]',
    align: 'right',
    formatter: formatters.tokens,
    className: 'text-amber-400',
  },
  conversation_context_tokens: {
    key: 'conversation_context_tokens',
    label: 'Context Tokens',
    category: 'Tokens',
    sortable: true,
    filterable: false,
    width: 'min-w-[110px]',
    align: 'right',
    formatter: formatters.tokens,
    className: 'text-orange-400',
  },
  tool_definitions_tokens: {
    key: 'tool_definitions_tokens',
    label: 'Tool Tokens',
    category: 'Tokens',
    sortable: true,
    filterable: false,
    width: 'min-w-[100px]',
    align: 'right',
    formatter: formatters.tokens,
    className: 'text-pink-400',
  },
  
  // ─────────────────────────────────────────────────────────────────────────────
  // COST
  // ─────────────────────────────────────────────────────────────────────────────
  total_cost: {
    key: 'total_cost',
    label: 'Cost',
    category: 'Cost',
    sortable: true,
    filterable: false,
    width: 'min-w-[90px]',
    align: 'right',
    formatter: formatters.currency,
    colorizer: colorizers.cost,
  },
  prompt_cost: {
    key: 'prompt_cost',
    label: 'Prompt Cost',
    category: 'Cost',
    sortable: true,
    filterable: false,
    width: 'min-w-[100px]',
    align: 'right',
    formatter: formatters.currency,
    className: 'text-gray-300',
  },
  completion_cost: {
    key: 'completion_cost',
    label: 'Completion Cost',
    category: 'Cost',
    sortable: true,
    filterable: false,
    width: 'min-w-[120px]',
    align: 'right',
    formatter: formatters.currency,
    className: 'text-gray-300',
  },
  
  // ─────────────────────────────────────────────────────────────────────────────
  // QUALITY
  // ─────────────────────────────────────────────────────────────────────────────
  judge_score: {
    key: 'judge_score',
    label: 'Quality Score',
    category: 'Quality',
    sortable: true,
    filterable: false,
    width: 'min-w-[100px]',
    align: 'right',
    formatter: formatters.score,
    colorizer: colorizers.quality,
  },
  hallucination_flag: {
    key: 'hallucination_flag',
    label: 'Hallucination',
    category: 'Quality',
    sortable: true,
    filterable: true,
    width: 'min-w-[110px]',
    align: 'center',
    formatter: (v) => v ? '⚠️ Yes' : '—',
    colorizer: colorizers.hallucination,
  },
  confidence_score: {
    key: 'confidence_score',
    label: 'Confidence',
    category: 'Quality',
    sortable: true,
    filterable: false,
    width: 'min-w-[100px]',
    align: 'right',
    formatter: formatters.confidence,
    colorizer: colorizers.quality,
  },
  
  // ─────────────────────────────────────────────────────────────────────────────
  // STATUS
  // ─────────────────────────────────────────────────────────────────────────────
  status: {
    key: 'status',
    label: 'Status',
    category: 'Status',
    sortable: true,
    filterable: true,
    width: 'min-w-[100px]',
    align: 'left',
    formatter: formatters.status,
    colorizer: colorizers.status,
  },
  error: {
    key: 'error',
    label: 'Error',
    category: 'Status',
    sortable: false,
    filterable: false,
    width: 'min-w-[150px]',
    align: 'left',
    formatter: (v) => formatters.truncate(v, 40),
    className: 'text-red-400',
  },
  error_type: {
    key: 'error_type',
    label: 'Error Type',
    category: 'Status',
    sortable: true,
    filterable: true,
    width: 'min-w-[120px]',
    align: 'left',
    formatter: formatters.text,
    className: 'text-red-400',
  },
  retry_count: {
    key: 'retry_count',
    label: 'Retries',
    category: 'Status',
    sortable: true,
    filterable: false,
    width: 'min-w-[80px]',
    align: 'right',
    formatter: formatters.number,
    colorizer: colorizers.retry,
  },
  
  // ─────────────────────────────────────────────────────────────────────────────
  // MODEL
  // ─────────────────────────────────────────────────────────────────────────────
  model_name: {
    key: 'model_name',
    label: 'Model',
    category: 'Model',
    sortable: true,
    filterable: true,
    width: 'min-w-[120px]',
    align: 'left',
    formatter: formatters.text,
    className: 'text-blue-400',
  },
  provider: {
    key: 'provider',
    label: 'Provider',
    category: 'Model',
    sortable: true,
    filterable: true,
    width: 'min-w-[100px]',
    align: 'left',
    formatter: formatters.text,
    className: 'text-gray-400',
  },
  temperature: {
    key: 'temperature',
    label: 'Temperature',
    category: 'Model',
    sortable: true,
    filterable: false,
    width: 'min-w-[100px]',
    align: 'right',
    formatter: (v) => v != null ? v.toFixed(2) : '—',
    className: 'text-gray-400',
  },
  
  // ─────────────────────────────────────────────────────────────────────────────
  // ROUTING
  // ─────────────────────────────────────────────────────────────────────────────
  complexity_score: {
    key: 'complexity_score',
    label: 'Complexity',
    category: 'Routing',
    sortable: true,
    filterable: false,
    width: 'min-w-[100px]',
    align: 'right',
    formatter: (v) => v != null ? v.toFixed(1) : '—',
    colorizer: colorizers.quality,
  },
  chosen_model: {
    key: 'chosen_model',
    label: 'Chosen Model',
    category: 'Routing',
    sortable: true,
    filterable: true,
    width: 'min-w-[120px]',
    align: 'left',
    formatter: formatters.text,
    className: 'text-purple-400',
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // CACHE (Individual Calls)
  // ─────────────────────────────────────────────────────────────────────────────
  cached: {
    key: 'cached',
    label: 'Cached',
    category: 'Cache',
    sortable: true,
    filterable: true,
    width: 'min-w-[80px]',
    align: 'center',
    formatter: formatters.cached,
    colorizer: colorizers.cached,
  },
  cache_hit: {
    key: 'cache_hit',
    label: 'Cache Hit',
    category: 'Cache',
    sortable: true,
    filterable: true,
    width: 'min-w-[90px]',
    align: 'center',
    formatter: formatters.boolean,
    colorizer: colorizers.cached,
  },
  cache_key: {
    key: 'cache_key',
    label: 'Cache Key',
    category: 'Cache',
    sortable: false,
    filterable: false,
    width: 'min-w-[120px]',
    align: 'left',
    formatter: formatters.callId,
    className: 'text-gray-500 font-mono',
  },
  cached_prompt_tokens: {
    key: 'cached_prompt_tokens',
    label: 'Cached Tokens',
    category: 'Cache',
    sortable: true,
    filterable: false,
    width: 'min-w-[110px]',
    align: 'right',
    formatter: formatters.tokens,
    className: 'text-green-400',
  },
  
  // ─────────────────────────────────────────────────────────────────────────────
  // CACHE PATTERNS (For Layer 2 Cache Opportunities)
  // ─────────────────────────────────────────────────────────────────────────────
  cache_type: {
    key: 'cache_type',
    label: 'Cache Type',
    category: 'Cache Patterns',
    sortable: true,
    filterable: true,
    width: 'min-w-[100px]',
    align: 'left',
    formatter: formatters.text,
    className: 'text-pink-400',
  },
  cache_type_emoji: {
    key: 'cache_type_emoji',
    label: 'Type',
    category: 'Cache Patterns',
    sortable: false,
    filterable: false,
    width: 'w-16',
    align: 'center',
    formatter: (v) => v || '📦',
    className: 'text-xl',
  },
  prompt_preview: {
    key: 'prompt_preview',
    label: 'Prompt Pattern',
    category: 'Cache Patterns',
    sortable: true,
    filterable: false,
    width: 'min-w-[250px]',
    align: 'left',
    formatter: (v) => v ? `"${formatters.truncate(v, 50)}"` : '—',
    className: 'font-mono text-base text-pink-400',
  },
  repeat_count: {
    key: 'repeat_count',
    label: 'Repeats',
    category: 'Cache Patterns',
    sortable: true,
    filterable: false,
    width: 'min-w-[80px]',
    align: 'right',
    formatter: formatters.count,
    colorizer: colorizers.repeatCount,
  },
  wasted_cost: {
    key: 'wasted_cost',
    label: 'Wasted',
    category: 'Cache Patterns',
    sortable: true,
    filterable: false,
    width: 'min-w-[90px]',
    align: 'right',
    formatter: formatters.currency,
    colorizer: colorizers.wastedCost,
  },
  savable_time: {
    key: 'savable_time',
    label: 'Savable',
    category: 'Cache Patterns',
    sortable: true,
    filterable: false,
    width: 'min-w-[90px]',
    align: 'right',
    formatter: (v) => v ? `~${v}` : '—',
    className: 'text-gray-400',
  },
  savable_time_formatted: {
    key: 'savable_time_formatted',
    label: 'Savable',
    category: 'Cache Patterns',
    sortable: true,
    filterable: false,
    width: 'min-w-[90px]',
    align: 'right',
    formatter: formatters.text,
    className: 'text-gray-400',
  },
  effort: {
    key: 'effort',
    label: 'Effort',
    category: 'Cache Patterns',
    sortable: true,
    filterable: true,
    width: 'min-w-[70px]',
    align: 'center',
    formatter: formatters.effort,
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // ROUTING PATTERNS
  // ─────────────────────────────────────────────────────────────────────────────
  type: {
    key: 'type',
    label: 'Type',
    category: 'Routing Patterns',
    sortable: true,
    filterable: true,
    width: 'min-w-[120px]',
    align: 'center',
    // Uses type_label for display
    formatter: (v, row) => row?.type_label || v || '—',
    colorizer: (v) => {
      if (v === 'downgrade') return 'text-blue-400';
      if (v === 'upgrade') return 'text-red-400';
      return 'text-green-400';
    },
  },
  model: {
    key: 'model',
    label: 'Model',
    category: 'Routing Patterns',
    sortable: true,
    filterable: true,
    width: 'min-w-[140px]',
    align: 'center',
    formatter: formatters.text,
    className: 'text-gray-300',
  },
  complexity_avg: {
    key: 'complexity_avg',
    label: 'Complexity',
    category: 'Routing Patterns',
    sortable: true,
    filterable: false,
    width: 'min-w-[100px]',
    align: 'center',
    formatter: (v) => v != null ? v.toFixed(2) : '—',
    colorizer: (v) => {
      if (v == null) return 'text-gray-400';
      if (v >= 0.7) return 'text-red-400 font-semibold';
      if (v >= 0.4) return 'text-yellow-400';
      return 'text-green-400';
    },
  },
  avg_quality: {
    key: 'avg_quality',
    label: 'Quality',
    category: 'Routing Patterns',
    sortable: true,
    filterable: false,
    width: 'min-w-[80px]',
    align: 'center',
    formatter: (v, row) => row?.avg_quality_formatted || (v != null ? v.toFixed(1) : '—'),
    colorizer: (v) => {
      if (v == null) return 'text-gray-400';
      if (v >= 8) return 'text-emerald-400 font-semibold';
      if (v >= 7) return 'text-green-400';
      if (v >= 5) return 'text-yellow-400';
      return 'text-red-400';
    },
  },
  call_count: {
    key: 'call_count',
    label: 'Calls',
    category: 'Routing Patterns',
    sortable: true,
    filterable: false,
    width: 'min-w-[80px]',
    align: 'center',
    formatter: formatters.number,
    colorizer: (v) => {
      if (v == null) return 'text-gray-400';
      if (v >= 100) return 'text-purple-400 font-semibold';
      if (v >= 50) return 'text-blue-400';
      if (v >= 10) return 'text-cyan-400';
      return 'text-gray-400';
    },
  },
  savable: {
    key: 'savable',
    label: 'Savable',
    category: 'Routing Patterns',
    sortable: true,
    filterable: false,
    width: 'min-w-[90px]',
    align: 'center',
    formatter: (v) => {
      if (v == null) return '—';
      if (v > 0) return `$${v.toFixed(2)}`;
      if (v < 0) return `+$${Math.abs(v).toFixed(2)}`;
      return '—';
    },
    colorizer: (v) => {
      if (v > 0) return 'text-green-400 font-semibold';
      if (v < 0) return 'text-red-400 font-semibold';
      return 'text-gray-500';
    },
  },
  safe_pct: {
    key: 'safe_pct',
    label: 'Safe %',
    category: 'Routing Patterns',
    sortable: true,
    filterable: false,
    width: 'min-w-[80px]',
    align: 'center',
    formatter: (v) => v != null ? `${v}%` : '—',
    colorizer: (v) => {
      if (v >= 90) return 'text-green-400';
      if (v >= 70) return 'text-yellow-400';
      return 'text-red-400';
    },
  },

  // ─────────────────────────────────────────────────────────────────────────────
  // CONTEXT / TIME
  // ─────────────────────────────────────────────────────────────────────────────
  timestamp: {
    key: 'timestamp',
    label: 'Time',
    category: 'Context',
    sortable: true,
    filterable: false,
    width: 'min-w-[140px]',
    align: 'left',
    formatter: formatters.timestamp,
    className: 'text-gray-400',
  },
  user_id: {
    key: 'user_id',
    label: 'User',
    category: 'Context',
    sortable: true,
    filterable: true,
    width: 'min-w-[100px]',
    align: 'left',
    formatter: formatters.text,
    className: 'text-gray-400',
  },
};

// =============================================================================
// COLUMN CATEGORIES (for Add Column dropdown)
// =============================================================================

export const COLUMN_CATEGORIES = [
  {
    name: 'Identity',
    columns: ['call_id', 'agent_name', 'operation', 'session_id', 'call_type'],
  },
  {
    name: 'Performance',
    columns: ['latency_ms', 'time_to_first_token_ms'],
  },
  {
    name: 'Tokens',
    columns: [
      'prompt_tokens', 'completion_tokens', 'total_tokens', 'token_ratio',
      'system_prompt_tokens', 'user_message_tokens', 'chat_history_tokens',
      'conversation_context_tokens', 'tool_definitions_tokens',
    ],
  },
  {
    name: 'Cost',
    columns: ['total_cost', 'prompt_cost', 'completion_cost'],
  },
  {
    name: 'Quality',
    columns: ['judge_score', 'hallucination_flag', 'confidence_score'],
  },
  {
    name: 'Status',
    columns: ['status', 'error', 'error_type', 'retry_count'],
  },
  {
    name: 'Model',
    columns: ['model_name', 'provider', 'temperature'],
  },
  {
    name: 'Routing',
    columns: ['complexity_score', 'chosen_model'],
  },
  {
    name: 'Cache',
    columns: ['cached', 'cache_hit', 'cache_key', 'cached_prompt_tokens'],
  },
  {
    name: 'Cache Patterns',
    columns: ['cache_type', 'cache_type_emoji', 'prompt_preview', 'repeat_count', 'wasted_cost', 'savable_time', 'savable_time_formatted', 'effort'],
  },
  {
    name: 'Context',
    columns: ['timestamp', 'user_id'],
  },
];

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Get column definition by key
 */
export const getColumn = (key) => ALL_COLUMNS[key] || null;

/**
 * Get multiple column definitions by keys
 */
export const getColumns = (keys) => keys.map(key => ALL_COLUMNS[key]).filter(Boolean);

/**
 * Get all column keys
 */
export const getAllColumnKeys = () => Object.keys(ALL_COLUMNS);

/**
 * Get columns grouped by category
 */
export const getColumnsByCategory = () => {
  return COLUMN_CATEGORIES.map(cat => ({
    ...cat,
    columns: cat.columns.map(key => ALL_COLUMNS[key]).filter(Boolean),
  }));
};

/**
 * Get columns NOT in the given list (for Add Column dropdown)
 */
export const getAddableColumns = (currentColumns) => {
  const current = new Set(currentColumns);
  return COLUMN_CATEGORIES.map(cat => ({
    ...cat,
    columns: cat.columns
      .filter(key => !current.has(key))
      .map(key => ALL_COLUMNS[key])
      .filter(Boolean),
  })).filter(cat => cat.columns.length > 0);
};

export default ALL_COLUMNS;