/**
 * Story Definitions - Layer 2 Configurations
 * 
 * Each story has:
 * - Quick filters (preset filter buttons)
 * - Default columns (initial visible columns)
 * - Available columns (can be added via Add Column)
 * - Default sort (initial sort order)
 * - Filter bar columns (Operation, Agent by default)
 */

// =============================================================================
// STORY IDS
// =============================================================================

export const STORY_IDS = {
  LATENCY: 'latency',
  COST: 'cost',
  QUALITY: 'quality',
  TOKEN: 'token_imbalance',
  PROMPT: 'system_prompt',
  CACHE: 'cache',
  ROUTING: 'routing',
  OPTIMIZATION: 'optimization',
};

// =============================================================================
// COLUMN DEFINITIONS (shared across stories)
// =============================================================================

export const COLUMN_DEFINITIONS = {
  // Identity
  call_id: { key: 'call_id', label: 'Call ID', type: 'id' },
  timestamp: { key: 'timestamp', label: 'Timestamp', type: 'datetime' },
  agent_name: { key: 'agent_name', label: 'Agent', type: 'category' },
  operation: { key: 'operation', label: 'Operation', type: 'category' },
  session_id: { key: 'session_id', label: 'Session ID', type: 'id' },
  
  // Model
  model_name: { key: 'model_name', label: 'Model', type: 'category' },
  provider: { key: 'provider', label: 'Provider', type: 'category' },
  temperature: { key: 'temperature', label: 'Temperature', type: 'number', decimals: 2 },
  
  // Performance
  latency_ms: { key: 'latency_ms', label: 'Latency', type: 'duration', format: 'seconds' },
  time_to_first_token_ms: { key: 'time_to_first_token_ms', label: 'TTFT', type: 'duration', format: 'ms' },
  
  // Tokens - Basic
  prompt_tokens: { key: 'prompt_tokens', label: 'Prompt Tokens', type: 'number' },
  completion_tokens: { key: 'completion_tokens', label: 'Completion', type: 'number' },
  total_tokens: { key: 'total_tokens', label: 'Total Tokens', type: 'number' },
  token_ratio: { key: 'token_ratio', label: 'Ratio', type: 'ratio' },
  
  // Tokens - Breakdown
  system_prompt_tokens: { key: 'system_prompt_tokens', label: 'System Tokens', type: 'number' },
  user_message_tokens: { key: 'user_message_tokens', label: 'User Tokens', type: 'number' },
  chat_history_tokens: { key: 'chat_history_tokens', label: 'History Tokens', type: 'number' },
  conversation_context_tokens: { key: 'conversation_context_tokens', label: 'Context Tokens', type: 'number' },
  tool_definitions_tokens: { key: 'tool_definitions_tokens', label: 'Tool Tokens', type: 'number' },
  
  // Cost
  prompt_cost: { key: 'prompt_cost', label: 'Prompt Cost', type: 'currency' },
  completion_cost: { key: 'completion_cost', label: 'Completion Cost', type: 'currency' },
  total_cost: { key: 'total_cost', label: 'Cost', type: 'currency' },
  
  // Status
  status: { key: 'status', label: 'Status', type: 'status' },
  success: { key: 'success', label: 'Success', type: 'boolean' },
  error: { key: 'error', label: 'Error', type: 'text' },
  error_type: { key: 'error_type', label: 'Error Type', type: 'category' },
  retry_count: { key: 'retry_count', label: 'Retries', type: 'number' },
  
  // Cache
  cached: { key: 'cached', label: 'Cached', type: 'boolean' },
  cache_hit: { key: 'cache_hit', label: 'Cache Hit', type: 'boolean' },
  cache_key: { key: 'cache_key', label: 'Cache Key', type: 'text' },
  cached_prompt_tokens: { key: 'cached_prompt_tokens', label: 'Cached Tokens', type: 'number' },
  
  // Quality
  judge_score: { key: 'judge_score', label: 'Quality Score', type: 'score', max: 10 },
  hallucination_flag: { key: 'hallucination_flag', label: 'Hallucination', type: 'boolean' },
  confidence_score: { key: 'confidence_score', label: 'Confidence', type: 'score', max: 1 },
  
  // Routing
  complexity_score: { key: 'complexity_score', label: 'Complexity', type: 'score' },
  chosen_model: { key: 'chosen_model', label: 'Chosen Model', type: 'category' },
};

// =============================================================================
// QUICK FILTER HELPER
// =============================================================================

const createQuickFilter = (id, label, icon, logic, description = '') => ({
  id,
  label,
  icon,
  logic,
  description,
});

// =============================================================================
// STORY LAYER 2 CONFIGURATIONS
// =============================================================================

export const STORY_LAYER2_CONFIG = {
  // ─────────────────────────────────────────────────────────────────────────────
  // LATENCY
  // ─────────────────────────────────────────────────────────────────────────────
  [STORY_IDS.LATENCY]: {
    id: STORY_IDS.LATENCY,
    name: 'Latency Analysis',
    emoji: '🌐',
    
    quickFilters: [
      createQuickFilter('all', 'All Calls', '🎯', null, 'Show all calls'),
      createQuickFilter('slow', 'Slow >5s', '🐌', { field: 'latency_ms', op: '>', value: 5000 }),
      createQuickFilter('critical', 'Critical >10s', '⚡', { field: 'latency_ms', op: '>', value: 10000 }),
      createQuickFilter('max', 'Max Latency', '🔴', { type: 'max', field: 'latency_ms' }),
      createQuickFilter('recent', 'Recent 24h', '⏱️', { field: 'timestamp', op: '>', value: 'now-24h' }),
      createQuickFilter('errors', 'Errors', '❌', { field: 'status', op: '=', value: 'error' }),
    ],
    
    defaultColumns: ['call_id', 'agent_name', 'operation', 'latency_ms', 'total_tokens', 'status'],
    
    availableColumns: [
      'call_id', 'timestamp', 'agent_name', 'operation', 'model_name', 'provider',
      'latency_ms', 'time_to_first_token_ms',
      'prompt_tokens', 'completion_tokens', 'total_tokens',
      'total_cost', 'status', 'error_type', 'retry_count',
      'judge_score', 'cached',
    ],
    
    defaultSort: { key: 'latency_ms', direction: 'desc' },
    
    filterBarColumns: ['operation', 'agent_name'],
    
    primaryMetric: 'latency_ms',
  },
  
  // ─────────────────────────────────────────────────────────────────────────────
  // COST
  // ─────────────────────────────────────────────────────────────────────────────
  [STORY_IDS.COST]: {
    id: STORY_IDS.COST,
    name: 'Cost Analysis',
    emoji: '💰',
    hasInsights: true,
    
    quickFilters: [
      createQuickFilter('all', 'All Calls', '🎯', null),
      createQuickFilter('expensive1', '>$0.01', '💵', { field: 'total_cost', op: '>', value: 0.01 }),
      createQuickFilter('expensive2', '>$0.05', '💸', { field: 'total_cost', op: '>', value: 0.05 }),
      createQuickFilter('expensive3', '>$0.10', '🔥', { field: 'total_cost', op: '>', value: 0.10 }),
      createQuickFilter('max', 'Max Cost', '🔴', { type: 'max', field: 'total_cost' }),
      createQuickFilter('errors', 'Errors', '❌', { field: 'status', op: '=', value: 'error' }),
    ],
    
    defaultColumns: ['call_id', 'agent_name', 'operation', 'total_cost', 'prompt_cost', 'completion_cost', 'model_name'],
    
    availableColumns: [
      'call_id', 'timestamp', 'agent_name', 'operation', 'model_name', 'provider',
      'total_cost', 'prompt_cost', 'completion_cost',
      'prompt_tokens', 'completion_tokens', 'total_tokens',
      'latency_ms', 'status', 'cached',
    ],
    
    defaultSort: { key: 'total_cost', direction: 'desc' },
    
    filterBarColumns: ['operation', 'agent_name'],
    
    primaryMetric: 'total_cost',
  },
  
  // ─────────────────────────────────────────────────────────────────────────────
  // QUALITY
  // ─────────────────────────────────────────────────────────────────────────────
  [STORY_IDS.QUALITY]: {
    id: STORY_IDS.QUALITY,
    name: 'Quality Monitoring',
    emoji: '⭐',
    
    quickFilters: [
      createQuickFilter('all', 'All Calls', '🎯', null),
      createQuickFilter('low', 'Low <5', '😟', { field: 'judge_score', op: '<', value: 5 }),
      createQuickFilter('medium', 'Medium 5-7', '😐', { field: 'judge_score', op: 'between', value: [5, 7] }),
      createQuickFilter('hallucinations', 'Hallucinations', '🌀', { field: 'hallucination_flag', op: '=', value: true }),
      createQuickFilter('worst', 'Worst', '🔴', { type: 'min', field: 'judge_score' }),
      createQuickFilter('errors', 'Errors', '❌', { field: 'status', op: '=', value: 'error' }),
    ],
    
    defaultColumns: ['call_id', 'agent_name', 'operation', 'judge_score', 'hallucination_flag', 'status'],
    
    availableColumns: [
      'call_id', 'timestamp', 'agent_name', 'operation', 'model_name',
      'judge_score', 'hallucination_flag', 'confidence_score',
      'status', 'error', 'error_type', 'retry_count',
      'latency_ms', 'total_tokens', 'total_cost',
    ],
    
    defaultSort: { key: 'judge_score', direction: 'asc' }, // Worst first
    
    filterBarColumns: ['operation', 'agent_name'],
    
    primaryMetric: 'judge_score',
  },
  
  // ─────────────────────────────────────────────────────────────────────────────
  // TOKEN EFFICIENCY
  // ─────────────────────────────────────────────────────────────────────────────
  [STORY_IDS.TOKEN]: {
    id: STORY_IDS.TOKEN,
    name: 'Token Efficiency',
    emoji: '⚖️',
    
    quickFilters: [
      createQuickFilter('all', 'All Calls', '🎯', null),
      createQuickFilter('large', 'Large >1k', '📊', { field: 'total_tokens', op: '>', value: 1000 }),
      createQuickFilter('huge', 'Huge >2k', '🔥', { field: 'total_tokens', op: '>', value: 2000 }),
      createQuickFilter('max', 'Max Tokens', '🔴', { type: 'max', field: 'total_tokens' }),
      createQuickFilter('verbose', 'Verbose', '📝', { field: 'completion_tokens', op: '>', value: 1000 }),
      createQuickFilter('imbalanced', 'Imbalanced', '⚖️', { field: 'token_ratio', op: '>', value: 5 }),
    ],
    
    defaultColumns: ['call_id', 'agent_name', 'operation', 'prompt_tokens', 'completion_tokens', 'total_tokens', 'token_ratio'],
    
    availableColumns: [
      'call_id', 'timestamp', 'agent_name', 'operation', 'model_name',
      'prompt_tokens', 'completion_tokens', 'total_tokens', 'token_ratio',
      'system_prompt_tokens', 'user_message_tokens',
      'total_cost', 'latency_ms', 'status',
    ],
    
    defaultSort: { key: 'total_tokens', direction: 'desc' },
    
    filterBarColumns: ['operation', 'agent_name'],
    
    primaryMetric: 'total_tokens',
  },
  
  // ─────────────────────────────────────────────────────────────────────────────
  // PROMPT COMPOSITION
  // ─────────────────────────────────────────────────────────────────────────────
  [STORY_IDS.PROMPT]: {
    id: STORY_IDS.PROMPT,
    name: 'Prompt Composition',
    emoji: '📝',
    hasInsights: true,
    
    quickFilters: [
      createQuickFilter('all', 'All Calls', '🎯', null),
      createQuickFilter('large_system', 'Large System >1k', '📜', { field: 'system_prompt_tokens', op: '>', value: 1000 }),
      createQuickFilter('huge_system', 'Huge System >2k', '🔥', { field: 'system_prompt_tokens', op: '>', value: 2000 }),
      createQuickFilter('max', 'Max System', '🔴', { type: 'max', field: 'system_prompt_tokens' }),
      createQuickFilter('no_system', 'No System', '❓', { field: 'system_prompt_tokens', op: '=', value: 0 }),
      createQuickFilter('errors', 'Errors', '❌', { field: 'status', op: '=', value: 'error' }),
    ],
    
    defaultColumns: ['call_id', 'agent_name', 'operation', 'system_prompt_tokens', 'user_message_tokens', 'prompt_tokens'],
    
    availableColumns: [
      'call_id', 'timestamp', 'agent_name', 'operation', 'model_name',
      'system_prompt_tokens', 'user_message_tokens', 'chat_history_tokens',
      'conversation_context_tokens', 'tool_definitions_tokens',
      'prompt_tokens', 'completion_tokens', 'total_tokens',
      'total_cost', 'latency_ms', 'status', 'cached',
    ],
    
    defaultSort: { key: 'system_prompt_tokens', direction: 'desc' },
    
    filterBarColumns: ['operation', 'agent_name'],
    
    primaryMetric: 'system_prompt_tokens',
  },
  
  // ─────────────────────────────────────────────────────────────────────────────
  // CACHING
  // ─────────────────────────────────────────────────────────────────────────────
  [STORY_IDS.CACHE]: {
    id: STORY_IDS.CACHE,
    name: 'Caching Strategy',
    emoji: '💾',
    hasInsights: true,
    
    quickFilters: [
      createQuickFilter('all', 'All Calls', '🎯', null),
      createQuickFilter('miss', 'Cache Miss', '❌', { field: 'cached', op: '=', value: false }),
      createQuickFilter('hit', 'Cache Hit', '✅', { field: 'cached', op: '=', value: true }),
      createQuickFilter('cacheable', 'Cacheable', '💡', { type: 'compound', filters: [
        { field: 'cached', op: '=', value: false },
        { field: 'prompt_tokens', op: '>', value: 500 },
      ]}),
      createQuickFilter('slow_miss', 'Slow + Miss', '🐌', { type: 'compound', filters: [
        { field: 'latency_ms', op: '>', value: 3000 },
        { field: 'cached', op: '=', value: false },
      ]}),
      createQuickFilter('errors', 'Errors', '❌', { field: 'status', op: '=', value: 'error' }),
    ],
    
    defaultColumns: ['call_id', 'agent_name', 'operation', 'cached', 'prompt_tokens', 'latency_ms', 'total_cost'],
    
    availableColumns: [
      'call_id', 'timestamp', 'agent_name', 'operation', 'model_name',
      'cached', 'cache_hit', 'cache_key', 'cached_prompt_tokens',
      'prompt_tokens', 'completion_tokens', 'total_tokens',
      'total_cost', 'latency_ms', 'status',
    ],
    
    defaultSort: { key: 'total_cost', direction: 'desc' },
    
    filterBarColumns: ['operation', 'agent_name'],
    
    primaryMetric: 'cached',
  },
  
  // ─────────────────────────────────────────────────────────────────────────────
  // ROUTING
  // ─────────────────────────────────────────────────────────────────────────────
  [STORY_IDS.ROUTING]: {
    id: STORY_IDS.ROUTING,
    name: 'Routing Opportunities',
    emoji: '🔀',
    
    quickFilters: [
      createQuickFilter('all', 'All Calls', '🎯', null),
      createQuickFilter('high_quality', 'High Quality ≥8', '⭐', { field: 'judge_score', op: '>=', value: 8 }),
      createQuickFilter('low_quality', 'Low Quality <5', '😟', { field: 'judge_score', op: '<', value: 5 }),
      createQuickFilter('simple', 'Simple Tasks', '📋', { type: 'compound', filters: [
        { field: 'total_tokens', op: '<', value: 1000 },
        { field: 'completion_tokens', op: '<', value: 300 },
      ]}),
      createQuickFilter('expensive', 'Expensive >$0.05', '💸', { field: 'total_cost', op: '>', value: 0.05 }),
      createQuickFilter('errors', 'Errors', '❌', { field: 'status', op: '=', value: 'error' }),
    ],
    
    defaultColumns: ['call_id', 'agent_name', 'operation', 'model_name', 'total_cost', 'latency_ms', 'judge_score'],
    
    availableColumns: [
      'call_id', 'timestamp', 'agent_name', 'operation', 'model_name', 'provider',
      'complexity_score', 'chosen_model',
      'total_cost', 'latency_ms', 'total_tokens',
      'judge_score', 'status',
    ],
    
    defaultSort: { key: 'total_cost', direction: 'desc' },
    
    filterBarColumns: ['operation', 'agent_name', 'model_name'],
    
    primaryMetric: 'total_cost',
  },
  
  // ─────────────────────────────────────────────────────────────────────────────
  // OPTIMIZATION
  // ─────────────────────────────────────────────────────────────────────────────
  [STORY_IDS.OPTIMIZATION]: {
    id: STORY_IDS.OPTIMIZATION,
    name: 'Optimization Impact',
    emoji: '🎯',
    hasInsights: true,
    
    quickFilters: [
      createQuickFilter('all', 'All Calls', '🎯', null),
      createQuickFilter('today', 'Today', '📅', { field: 'timestamp', op: '>=', value: 'today' }),
      createQuickFilter('week', 'This Week', '📆', { field: 'timestamp', op: '>', value: 'now-7d' }),
      createQuickFilter('success', 'Successful', '✅', { field: 'status', op: '=', value: 'success' }),
      createQuickFilter('fast', 'Fast <2s', '⚡', { field: 'latency_ms', op: '<', value: 2000 }),
      createQuickFilter('cheap', 'Cheap <$0.01', '💰', { field: 'total_cost', op: '<', value: 0.01 }),
    ],
    
    defaultColumns: ['call_id', 'agent_name', 'operation', 'total_cost', 'latency_ms', 'total_tokens', 'timestamp'],
    
    availableColumns: [
      'call_id', 'timestamp', 'agent_name', 'operation', 'model_name',
      'total_cost', 'latency_ms', 'total_tokens',
      'judge_score', 'cached', 'status',
    ],
    
    defaultSort: { key: 'timestamp', direction: 'desc' },
    
    filterBarColumns: ['operation', 'agent_name'],
    
    primaryMetric: 'timestamp',
  },
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Get Layer2 config for a story
 */
export const getLayer2Config = (storyId) => {
  return STORY_LAYER2_CONFIG[storyId] || null;
};

/**
 * Get quick filters for a story
 */
export const getQuickFilters = (storyId) => {
  const config = STORY_LAYER2_CONFIG[storyId];
  return config?.quickFilters || [];
};

/**
 * Get default columns for a story
 */
export const getDefaultColumns = (storyId) => {
  const config = STORY_LAYER2_CONFIG[storyId];
  return config?.defaultColumns || ['call_id', 'agent_name', 'operation', 'status'];
};

/**
 * Get available columns for a story (for Add Column dropdown)
 */
export const getAvailableColumns = (storyId) => {
  const config = STORY_LAYER2_CONFIG[storyId];
  return config?.availableColumns || Object.keys(COLUMN_DEFINITIONS);
};

/**
 * Get column definition by key
 */
export const getColumnDefinition = (key) => {
  return COLUMN_DEFINITIONS[key] || { key, label: key, type: 'text' };
};

/**
 * Get default sort for a story
 */
export const getDefaultSort = (storyId) => {
  const config = STORY_LAYER2_CONFIG[storyId];
  return config?.defaultSort || { key: 'timestamp', direction: 'desc' };
};

/**
 * Check if story has specialized insights
 */
export const hasInsights = (storyId) => {
  const config = STORY_LAYER2_CONFIG[storyId];
  return config?.hasInsights || false;
};

export default STORY_LAYER2_CONFIG;