/**
 * Fix Prioritization - HYBRID VERSION
 *
 * Sophisticated multi-dimensional scoring from uploaded system:
 * - Impact scoring (metric-based)
 * - Effort penalties
 * - Story-specific adjustments
 * - Relevance scoring
 * - Utility functions
 */

// ═════════════════════════════════════════════════════════════════════════════
// PRIORITY WEIGHTS
// ═════════════════════════════════════════════════════════════════════════════

export const PRIORITY_WEIGHTS = {
  // Impact weights (how much each metric type matters)
  latency_reduction: 1.2,
  cost_reduction: 1.5,
  token_reduction: 0.8,
  quality_improvement: 1.3,
  
  // Effort penalties (multiply final score)
  effort_low: 1.0,
  effort_medium: 0.7,
  effort_high: 0.4,
  
  // Recommendation bonus
  recommended_bonus: 1.3,
  
  // Severity multipliers
  severity_critical: 1.5,
  severity_warning: 1.2,
  severity_info: 1.0,
};

// Story-specific priority adjustments
export const STORY_PRIORITY_ADJUSTMENTS = {
  latency: {
    // Latency story prioritizes speed fixes
    latency_reduction: 2.0,
    streaming: 1.5,
    token_reduction: 1.0,
  },
  cost: {
    // Cost story prioritizes savings
    cost_reduction: 2.0,
    model_routing: 1.5,
    caching: 1.8,
  },
  cache: {
    // Cache story prioritizes hit rate
    caching: 2.5,
    cost_reduction: 1.2,
  },
  token: {
    // Token story prioritizes token efficiency
    token_reduction: 2.0,
    ratio_improvement: 1.8,
  },
  quality: {
    // Quality story prioritizes accuracy
    quality_improvement: 2.5,
    hallucination_prevention: 2.0,
  },
  routing: {
    // Routing story prioritizes model optimization
    model_routing: 2.0,
    cost_reduction: 1.5,
  },
  prompt: {
    // Prompt story prioritizes prompt optimization
    token_reduction: 1.5,
    prompt_compression: 2.0,
  },
};

// ═════════════════════════════════════════════════════════════════════════════
// MAIN SCORING FUNCTION
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Calculate priority score for a fix
 * 
 * Multi-dimensional scoring:
 * 1. Impact score (from metrics)
 * 2. Effort penalty
 * 3. Story-specific adjustments
 * 4. Recommended bonus
 * 5. Relevance score
 * 
 * @param {Object} fix - Instantiated fix object
 * @param {string} storyId - Current story context
 * @param {Object} call - Call data
 * @param {string[]} factors - Detected factors
 * @returns {number} Priority score (higher = more important)
 */
export function calculatePriority(fix, storyId, call, factors = []) {
  // 1. Calculate impact from metrics
  let impactScore = calculateImpactScore(fix.metrics || [], storyId);
  
  // 2. Apply effort penalty
  const effortMultiplier = getEffortMultiplier(fix.effort);
  
  // 3. Story-specific adjustments
  const storyMultiplier = getStoryMultiplier(fix, storyId);
  
  // 4. Recommended bonus
  const recommendedMultiplier = fix.recommended ? PRIORITY_WEIGHTS.recommended_bonus : 1.0;
  
  // 5. Relevance score (how well factors match)
  const relevanceScore = calculateRelevanceScore(fix.triggerFactors || [], factors);
  
  // Combine all factors
  const finalScore = impactScore * effortMultiplier * storyMultiplier * recommendedMultiplier * relevanceScore;
  
  return Math.round(finalScore * 10) / 10; // Round to 1 decimal
}

// ═════════════════════════════════════════════════════════════════════════════
// IMPACT CALCULATION
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Calculate impact score from metrics
 */
function calculateImpactScore(metrics, storyId) {
  let totalImpact = 0;
  
  metrics.forEach(metric => {
    const change = Math.abs(metric.changePercent || 0);
    
    // Apply weights based on metric type
    let weight = 1.0;
    const label = metric.label.toLowerCase();
    
    if (label.includes('latency') || label.includes('time')) {
      weight = PRIORITY_WEIGHTS.latency_reduction;
      
      // Story-specific boost
      if (storyId === 'latency') {
        weight *= (STORY_PRIORITY_ADJUSTMENTS.latency?.latency_reduction || 1.0);
      }
    } 
    else if (label.includes('cost')) {
      weight = PRIORITY_WEIGHTS.cost_reduction;
      
      if (storyId === 'cost') {
        weight *= (STORY_PRIORITY_ADJUSTMENTS.cost?.cost_reduction || 1.0);
      }
    }
    else if (label.includes('token')) {
      weight = PRIORITY_WEIGHTS.token_reduction;
      
      if (storyId === 'token') {
        weight *= (STORY_PRIORITY_ADJUSTMENTS.token?.token_reduction || 1.0);
      }
    }
    else if (label.includes('quality') || label.includes('score')) {
      weight = PRIORITY_WEIGHTS.quality_improvement;
      
      if (storyId === 'quality') {
        weight *= (STORY_PRIORITY_ADJUSTMENTS.quality?.quality_improvement || 1.0);
      }
    }
    
    totalImpact += change * weight;
  });
  
  return totalImpact;
}

// ═════════════════════════════════════════════════════════════════════════════
// EFFORT MULTIPLIER
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Get effort penalty multiplier
 */
function getEffortMultiplier(effort) {
  switch (effort) {
    case 'Low':
      return PRIORITY_WEIGHTS.effort_low;
    case 'Medium':
      return PRIORITY_WEIGHTS.effort_medium;
    case 'High':
      return PRIORITY_WEIGHTS.effort_high;
    default:
      return 0.7; // Default to medium
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// STORY-SPECIFIC MULTIPLIERS
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Get story-specific priority boost
 */
function getStoryMultiplier(fix, storyId) {
  const storyBoosts = STORY_PRIORITY_ADJUSTMENTS[storyId] || {};
  
  // Check fix category/type for boosts
  const fixId = fix.id;
  
  // Caching fixes
  if (fixId.includes('cache') && storyBoosts.caching) {
    return storyBoosts.caching;
  }
  
  // Routing fixes
  if ((fixId.includes('switch') || fixId.includes('routing')) && storyBoosts.model_routing) {
    return storyBoosts.model_routing;
  }
  
  // Streaming fix
  if (fixId === 'enable_streaming' && storyBoosts.streaming) {
    return storyBoosts.streaming;
  }
  
  // Hallucination prevention
  if (fixId.includes('grounding') && storyBoosts.hallucination_prevention) {
    return storyBoosts.hallucination_prevention;
  }
  
  // Prompt compression
  if ((fixId.includes('compress') || fixId.includes('truncate')) && storyBoosts.prompt_compression) {
    return storyBoosts.prompt_compression;
  }
  
  // Default: no boost
  return 1.0;
}

// ═════════════════════════════════════════════════════════════════════════════
// RELEVANCE SCORING
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Calculate how well fix matches detected factors
 * 
 * More matched factors = higher relevance
 */
function calculateRelevanceScore(triggerFactors, detectedFactors) {
  if (!triggerFactors || triggerFactors.length === 0) return 1.0;
  if (!detectedFactors || detectedFactors.length === 0) return 0.8;
  
  // Count how many trigger factors are in detected factors
  const matchedFactors = triggerFactors.filter(f => 
    detectedFactors.includes(f)
  ).length;
  
  // Relevance = matched / total triggers
  const relevance = matchedFactors / triggerFactors.length;
  
  // Scale: 0.7 to 1.3 (some match = 0.7, all match = 1.3)
  return 0.7 + (relevance * 0.6);
}

// ═════════════════════════════════════════════════════════════════════════════
// SORTING AND FILTERING
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Sort fixes by priority (highest first)
 */
export function sortByPriority(fixes, storyId, call, factors) {
  // Calculate priority for each fix
  const fixesWithPriority = fixes.map(fix => ({
    ...fix,
    priority: calculatePriority(fix, storyId, call, factors),
  }));
  
  // Sort by priority (descending)
  return fixesWithPriority.sort((a, b) => b.priority - a.priority);
}

/**
 * Get top N fixes
 */
export function getTopFixes(fixes, storyId, call, factors, n = 3) {
  const sorted = sortByPriority(fixes, storyId, call, factors);
  return sorted.slice(0, n);
}

/**
 * Mark the highest-priority fix as recommended
 */
export function markRecommended(fixes) {
  if (fixes.length === 0) return fixes;
  
  // First fix is already sorted highest
  return fixes.map((fix, idx) => ({
    ...fix,
    recommended: idx === 0, // Only first is recommended
  }));
}

// ═════════════════════════════════════════════════════════════════════════════
// GROUPING UTILITIES
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Group fixes by effort level
 */
export function groupFixesByEffort(fixes) {
  return {
    low: fixes.filter(f => f.effort === 'Low'),
    medium: fixes.filter(f => f.effort === 'Medium'),
    high: fixes.filter(f => f.effort === 'High'),
  };
}

/**
 * Group fixes by category
 */
export function groupFixesByCategory(fixes) {
  const grouped = {};
  
  fixes.forEach(fix => {
    const category = fix.category || 'other';
    if (!grouped[category]) {
      grouped[category] = [];
    }
    grouped[category].push(fix);
  });
  
  return grouped;
}

// ═════════════════════════════════════════════════════════════════════════════
// IMPACT ANALYSIS
// ═════════════════════════════════════════════════════════════════════════════

/**
 * Calculate total potential savings from all fixes
 */
export function calculateTotalSavings(fixes) {
  const savings = {
    latency_ms: 0,
    cost: 0,
    tokens: 0,
    fixes_count: fixes.length,
  };
  
  fixes.forEach(fix => {
    (fix.metrics || []).forEach(metric => {
      const label = metric.label.toLowerCase();
      const change = Math.abs(metric.changePercent || 0);
      
      if (label.includes('latency')) {
        // Extract latency value from "after" string
        const match = metric.after?.match(/([0-9.]+)s/);
        if (match) {
          const afterLatency = parseFloat(match[1]) * 1000;
          const beforeMatch = metric.before?.match(/([0-9.]+)s/);
          if (beforeMatch) {
            const beforeLatency = parseFloat(beforeMatch[1]) * 1000;
            savings.latency_ms += (beforeLatency - afterLatency);
          }
        }
      }
      else if (label.includes('cost')) {
        // Extract cost value
        const match = metric.after?.match(/\$([0-9.]+)/);
        if (match) {
          const afterCost = parseFloat(match[1]);
          const beforeMatch = metric.before?.match(/\$([0-9.]+)/);
          if (beforeMatch) {
            const beforeCost = parseFloat(beforeMatch[1]);
            savings.cost += (beforeCost - afterCost);
          }
        }
      }
      else if (label.includes('token')) {
        // Extract token value
        const afterTokens = parseInt(metric.after?.replace(/,/g, '') || '0');
        const beforeTokens = parseInt(metric.before?.replace(/,/g, '') || '0');
        savings.tokens += (beforeTokens - afterTokens);
      }
    });
  });
  
  return savings;
}

/**
 * Get priority summary for UI display
 */
export function getFixPrioritySummary(fixes, storyId, call, factors) {
  const sorted = sortByPriority(fixes, storyId, call, factors);
  const savings = calculateTotalSavings(sorted);
  const byEffort = groupFixesByEffort(sorted);
  
  return {
    total_fixes: sorted.length,
    recommended: sorted[0] || null,
    quick_wins: byEffort.low,
    total_savings: savings,
    top_3: sorted.slice(0, 3),
    all_sorted: sorted,
  };
}

// ═════════════════════════════════════════════════════════════════════════════
// EXPORTS
// ═════════════════════════════════════════════════════════════════════════════

export default {
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
};