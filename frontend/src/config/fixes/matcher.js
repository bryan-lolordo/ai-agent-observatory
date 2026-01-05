/**
 * Fix Matcher - HYBRID VERSION
 *
 * Combines uploaded architecture with 20-fix coverage:
 * - FACTOR_FIX_MAP explicit mappings
 * - applicableWhen() runtime checks
 * - instantiateFix() for context-specific generation
 * - Multi-story support
 */

import FIX_REPOSITORY from './repository.js';

// ═════════════════════════════════════════════════════════════════════════════
// FACTOR → FIX MAPPINGS (20 fixes)
// ═════════════════════════════════════════════════════════════════════════════

export const FACTOR_FIX_MAP = {
  // ═══════════════════════════════════════════════════════════════════════════
  // LATENCY FACTORS
  // ═══════════════════════════════════════════════════════════════════════════
  high_latency: ['add_max_tokens', 'enable_streaming', 'truncate_history', 'switch_to_mini', 'compress_system_prompt', 'enable_prompt_caching'],
  slow_generation: ['add_max_tokens', 'truncate_history', 'compress_system_prompt', 'enable_streaming'],
  high_completion_tokens: ['add_max_tokens', 'enable_streaming'],
  no_max_tokens: ['add_max_tokens'],
  no_streaming: ['enable_streaming', 'add_max_tokens'],

  // ═══════════════════════════════════════════════════════════════════════════
  // TOKEN / PROMPT FACTORS
  // ═══════════════════════════════════════════════════════════════════════════
  high_input_ratio: ['truncate_history', 'compress_system_prompt', 'request_longer_output'],
  high_output_ratio: ['add_max_tokens'],
  low_output_ratio: ['request_longer_output'],
  low_output: ['request_longer_output'],
  high_prompt_tokens: ['truncate_history', 'compress_system_prompt', 'enable_prompt_caching', 'summarize_history'],
  large_prompt: ['compress_system_prompt', 'truncate_history', 'enable_prompt_caching'],

  // ═══════════════════════════════════════════════════════════════════════════
  // HISTORY FACTORS
  // ═══════════════════════════════════════════════════════════════════════════
  large_history: ['truncate_history', 'summarize_history'],
  high_chat_history_tokens: ['truncate_history', 'summarize_history'],

  // ═══════════════════════════════════════════════════════════════════════════
  // SYSTEM PROMPT FACTORS
  // ═══════════════════════════════════════════════════════════════════════════
  bloated_system_prompt: ['compress_system_prompt', 'enable_prompt_caching'],
  high_system_tokens: ['compress_system_prompt', 'enable_prompt_caching'],
  large_system_prompt: ['compress_system_prompt', 'enable_prompt_caching'],
  large_system_prompt_absolute: ['compress_system_prompt', 'enable_prompt_caching'],
  verbose_prompt: ['compress_system_prompt'],
  static_prompt: ['enable_prompt_caching'],

  // ═══════════════════════════════════════════════════════════════════════════
  // CACHE FACTORS (for patterns AND calls)
  // ═══════════════════════════════════════════════════════════════════════════
  no_cache: ['simple_cache', 'lru_cache', 'redis_cache', 'semantic_cache', 'enable_prompt_caching'],
  cache_miss: ['simple_cache', 'lru_cache', 'redis_cache'],
  exact_match: ['simple_cache', 'lru_cache'],
  cache_type_exact: ['simple_cache', 'lru_cache'],
  cache_type_semantic: ['semantic_cache'],
  cache_type_prefix: ['redis_cache', 'enable_prompt_caching'],
  similar_prompts: ['semantic_cache'],
  caching_opportunity: ['enable_prompt_caching', 'simple_cache', 'lru_cache'],

  // ═══════════════════════════════════════════════════════════════════════════
  // COST FACTORS
  // ═══════════════════════════════════════════════════════════════════════════
  premium_model: ['switch_to_mini', 'complexity_based_routing'],
  overqualified_model: ['switch_to_mini', 'complexity_based_routing'],
  low_complexity: ['switch_to_mini'],
  wrong_model_tier: ['complexity_based_routing'],
  static_routing: ['complexity_based_routing'],
  high_input_cost: ['compress_system_prompt', 'truncate_history', 'enable_prompt_caching'],
  high_output_tokens: ['add_max_tokens'],
  high_absolute_cost: ['switch_to_mini', 'compress_system_prompt', 'add_max_tokens', 'enable_prompt_caching'],
  above_average: ['switch_to_mini', 'compress_system_prompt'],

  // ═══════════════════════════════════════════════════════════════════════════
  // QUALITY FACTORS
  // ═══════════════════════════════════════════════════════════════════════════
  hallucination: ['add_grounding_instructions', 'lower_temperature'],
  low_quality_score: ['add_grounding_instructions', 'add_examples', 'adjust_temperature'],
  factual_error: ['add_grounding_instructions', 'lower_temperature'],
  missing_sections: ['add_examples'],
  inconsistent_format: ['add_examples'],
  inconsistent_output: ['lower_temperature', 'adjust_temperature'],
  low_creativity: ['adjust_temperature'],

  // ═══════════════════════════════════════════════════════════════════════════
  // TOKEN IMBALANCE FACTORS
  // ═══════════════════════════════════════════════════════════════════════════
  severe_imbalance: ['compress_system_prompt', 'truncate_history', 'request_longer_output'],
  high_imbalance: ['compress_system_prompt', 'truncate_history', 'request_longer_output'],
  moderate_imbalance: ['compress_system_prompt', 'request_longer_output'],

  // ═══════════════════════════════════════════════════════════════════════════
  // ROUTING FACTORS (from routing_analysis)
  // ═══════════════════════════════════════════════════════════════════════════
  overprovisioned: ['switch_to_mini', 'complexity_based_routing'],
  underprovisioned: ['complexity_based_routing'],
  model_overprovisioned: ['switch_to_mini', 'complexity_based_routing'],
  model_underprovisioned: ['complexity_based_routing'],
  cost_reduction_available: ['switch_to_mini'],

  // ═══════════════════════════════════════════════════════════════════════════
  // PROMPT COMPOSITION FACTORS
  // ═══════════════════════════════════════════════════════════════════════════
  history_bloat: ['truncate_history', 'summarize_history'],
  excessive_history: ['truncate_history', 'summarize_history'],
  cache_not_ready: ['enable_prompt_caching'],
  not_cache_ready: ['enable_prompt_caching'],  // Alternate naming
  partial_cache_ready: ['enable_prompt_caching'],
  dynamic_system_prompt: ['enable_prompt_caching'],
  high_history_tokens: ['truncate_history', 'summarize_history'],
};

// ═════════════════════════════════════════════════════════════════════════════
// MAIN MATCHING FUNCTION
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Get applicable fixes for a call based on factors and story
 * 
 * @param {Object} call - Call data with factors and metrics
 * @param {string} storyId - Current story context
 * @param {string[]} factors - Detected factors for this call
 * @returns {Object[]} Array of instantiated fix objects
 */
export function getApplicableFixes(call, storyId, factors = []) {
  const applicableFixes = [];
  const seenFixIds = new Set();
  
  // 1. Map factors to potential fixes
  const potentialFixIds = new Set();
  factors.forEach(factor => {
    // Extract factor ID (handle both objects and strings)
    const factorId = typeof factor === 'string' ? factor : factor.id;
    const fixIds = FACTOR_FIX_MAP[factorId] || [];
    fixIds.forEach(id => potentialFixIds.add(id));
  });
  
  // 2. Filter and instantiate fixes
  for (const fixId of potentialFixIds) {
    const fixTemplate = FIX_REPOSITORY[fixId];
    
    if (!fixTemplate) {
      console.warn(`Fix not found: ${fixId}`);
      continue;
    }
    
    // Skip if already added
    if (seenFixIds.has(fixId)) continue;
    
    // Check story applicability
    if (!fixTemplate.stories || !fixTemplate.stories.includes(storyId)) {
      continue;
    }
    
    // Check applicability condition
    if (fixTemplate.applicableWhen && !fixTemplate.applicableWhen(call)) {
      continue;
    }
    
    // Instantiate fix with runtime data
    const instantiatedFix = instantiateFix(fixTemplate, call);
    
    if (instantiatedFix) {
      applicableFixes.push(instantiatedFix);
      seenFixIds.add(fixId);
    }
  }
  
  return applicableFixes;
}

// ═════════════════════════════════════════════════════════════════════════════
// FIX INSTANTIATION
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Instantiate a fix template with actual call data
 * 
 * Calls generateMetrics() and generateCode() to create context-specific fix
 */
export function instantiateFix(fixTemplate, call) {
  try {
    // Generate runtime metrics
    const metrics = fixTemplate.generateMetrics 
      ? fixTemplate.generateMetrics(call)
      : [];
    
    // Generate context-specific code
    const code = fixTemplate.generateCode
      ? fixTemplate.generateCode(call)
      : { before: '', after: '' };
    
    // Check if fix is recommended (primary recommendation)
    const recommended = checkIfRecommended(fixTemplate, call, metrics);
    
    // Build complete fix object
    return {
      id: fixTemplate.id,
      stories: fixTemplate.stories,
      category: fixTemplate.category,
      title: fixTemplate.title,
      subtitle: fixTemplate.subtitle,
      effort: fixTemplate.effort,
      effortColor: fixTemplate.effortColor,
      
      // Runtime-generated data
      metrics,
      codeBefore: code.before,
      codeAfter: code.after,
      
      // Static data
      tradeoffs: fixTemplate.tradeoffs || [],
      benefits: fixTemplate.benefits || [],
      bestFor: fixTemplate.bestFor,
      
      // Metadata
      recommended,
      triggerFactors: fixTemplate.triggerFactors,
    };
  } catch (error) {
    console.error(`Error instantiating fix ${fixTemplate.id}:`, error);
    return null;
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// RECOMMENDATION LOGIC
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Determine if this fix should be the primary recommendation
 * 
 * Based on:
 * - Impact (from metrics)
 * - Effort (Low effort preferred)
 * - Context (severity, call characteristics)
 */
export function checkIfRecommended(fixTemplate, call, metrics) {
  // Get total impact from metrics
  const totalImpact = metrics.reduce((sum, m) => {
    const change = Math.abs(m.changePercent || 0);
    return sum + change;
  }, 0);
  
  // Effort penalty
  const effortScore = fixTemplate.effort === 'Low' ? 1.0 : 
                      fixTemplate.effort === 'Medium' ? 0.7 : 0.4;
  
  // Calculate recommendation score
  const score = totalImpact * effortScore;
  
  // Threshold for recommendation (will be compared with other fixes later)
  return score > 30;
}

// ═════════════════════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Get fix by ID (instantiated with call data)
 */
export function getFixById(fixId, call) {
  const template = FIX_REPOSITORY[fixId];
  if (!template) return null;
  
  return instantiateFix(template, call);
}

/**
 * Get all fixes for a story (not instantiated)
 */
export function getFixTemplatesByStory(storyId) {
  return Object.values(FIX_REPOSITORY).filter(
    fix => fix.stories && fix.stories.includes(storyId)
  );
}

/**
 * Check if a factor has any fixes
 */
export function hasFixesForFactor(factor) {
  return FACTOR_FIX_MAP[factor] && FACTOR_FIX_MAP[factor].length > 0;
}

/**
 * Get all unique factors that have fixes
 */
export function getAllSupportedFactors() {
  return Object.keys(FACTOR_FIX_MAP);
}

export default {
  getApplicableFixes,
  instantiateFix,
  checkIfRecommended,
  getFixById,
  getFixTemplatesByStory,
  hasFixesForFactor,
  getAllSupportedFactors,
  FACTOR_FIX_MAP,
};