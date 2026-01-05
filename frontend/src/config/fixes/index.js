/**
 * Fix System - HYBRID VERSION
 * 
 * Main API for centralized fix management
 * 
 * ARCHITECTURE:
 * - repository.js: 20 fixes with generateMetrics/generateCode functions
 * - matcher.js: FACTOR_FIX_MAP + applicableWhen runtime checks
 * - priorities.js: Multi-dimensional scoring with story adjustments
 * - index.js: Clean public API (this file)
 * 
 * USAGE:
 * ```js
 * import { getFixesForCall } from '@/config/fixes';
 * 
 * const fixes = getFixesForCall(call, 'latency', factors);
 * // Returns sorted, prioritized, instantiated fixes
 * ```
 */

import FIX_REPOSITORY, { getFixById as getTemplateById, getFixesByCategory, getAllFixes } from './repository.js';
import {
  getApplicableFixes,
  instantiateFix,
  checkIfRecommended,
  getFixById,
  getFixTemplatesByStory,
  hasFixesForFactor,
  getAllSupportedFactors,
  FACTOR_FIX_MAP,
} from './matcher.js';
import {
  calculatePriority,
  sortByPriority,
  getTopFixes,
  markRecommended,
  groupFixesByEffort,
  groupFixesByCategory,
  calculateTotalSavings,
  getFixPrioritySummary,
  PRIORITY_WEIGHTS,
  STORY_PRIORITY_ADJUSTMENTS,
} from './priorities.js';

// ═════════════════════════════════════════════════════════════════════════════
// HIGH-LEVEL API (recommended)
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Get all applicable fixes for a call, sorted by priority
 * 
 * This is the main entry point - use this in your components!
 * 
 * @param {Object} call - Call data with metrics
 * @param {string} storyId - Current story ('latency', 'cost', etc.)
 * @param {string[]} factors - Detected factors from diagnosis
 * @param {Object} options - { limit?: number, effortFilter?: string }
 * @returns {Object[]} Sorted, prioritized, instantiated fixes
 * 
 * @example
 * const fixes = getFixesForCall(call, 'latency', ['high_latency', 'no_max_tokens']);
 * // Returns: [{ id: 'add_max_tokens', priority: 95.2, metrics: [...], ... }]
 */
export function getFixesForCall(call, storyId, factors = [], options = {}) {
  const { limit, effortFilter } = options;

  // 1. Get applicable fixes (matched and instantiated)
  let fixes = getApplicableFixes(call, storyId, factors);
  
  // 2. Filter by effort if specified
  if (effortFilter) {
    fixes = fixes.filter(f => f.effort === effortFilter);
  }
  
  // 3. Sort by priority
  fixes = sortByPriority(fixes, storyId, call, factors);
  
  // 4. Mark top fix as recommended
  fixes = markRecommended(fixes);
  
  // 5. Limit results if specified
  if (limit) {
    fixes = fixes.slice(0, limit);
  }
  
  return fixes;
}

/**
 * Get fix summary with savings and groupings
 * 
 * @param {Object} call - Call data
 * @param {string} storyId - Story context
 * @param {string[]} factors - Detected factors
 * @returns {Object} Summary with recommended fix, savings, etc.
 * 
 * @example
 * const summary = getFixSummary(call, 'latency', factors);
 * // { total_fixes: 5, recommended: {...}, quick_wins: [...], total_savings: {...} }
 */
export function getFixSummary(call, storyId, factors = []) {
  const fixes = getFixesForCall(call, storyId, factors);
  return getFixPrioritySummary(fixes, storyId, call, factors);
}

/**
 * Get quick wins (Low effort fixes only)
 * 
 * @param {Object} call - Call data
 * @param {string} storyId - Story context
 * @param {string[]} factors - Detected factors
 * @returns {Object[]} Low-effort fixes sorted by priority
 */
export function getQuickWins(call, storyId, factors = []) {
  return getFixesForCall(call, storyId, factors, { effortFilter: 'Low' });
}

// ═════════════════════════════════════════════════════════════════════════════
// DIRECT ACCESS (for advanced use cases)
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Get a specific fix by ID, instantiated with call data
 */
export function getSingleFix(fixId, call) {
  return getFixById(fixId, call);
}

/**
 * Get all fix templates for a story (not instantiated)
 */
export function getStoryFixTemplates(storyId) {
  return getFixTemplatesByStory(storyId);
}

/**
 * Check if a factor has any fixes available
 */
export function canFixFactor(factor) {
  return hasFixesForFactor(factor);
}

// ═════════════════════════════════════════════════════════════════════════════
// UTILITIES
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Group fixes by effort level
 */
export { groupFixesByEffort };

/**
 * Group fixes by category
 */
export { groupFixesByCategory };

/**
 * Calculate total savings from a list of fixes
 */
export { calculateTotalSavings };

// ═════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═════════════════════════════════════════════════════════════════════════════

export { FACTOR_FIX_MAP, PRIORITY_WEIGHTS, STORY_PRIORITY_ADJUSTMENTS };

// ═════════════════════════════════════════════════════════════════════════════
// COMPLETE EXPORTS
// ═════════════════════════════════════════════════════════════════════════════

export default {
  // High-level API (USE THESE)
  getFixesForCall,
  getFixSummary,
  getQuickWins,
  
  // Direct access
  getSingleFix,
  getStoryFixTemplates,
  canFixFactor,
  
  // Utilities
  groupFixesByEffort,
  groupFixesByCategory,
  calculateTotalSavings,
  
  // Low-level (advanced)
  getApplicableFixes,
  instantiateFix,
  calculatePriority,
  sortByPriority,
  markRecommended,
  
  // Constants
  FACTOR_FIX_MAP,
  PRIORITY_WEIGHTS,
  STORY_PRIORITY_ADJUSTMENTS,
  
  // Repository access
  FIX_REPOSITORY,
  getAllFixes,
  getAllSupportedFactors,
};