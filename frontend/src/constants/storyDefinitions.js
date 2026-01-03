/**
 * Story Definitions
 * 
 * Centralized metadata for all 8 Observatory stories.
 * Used across Dashboard, story pages, and routing.
 * Aligned with STORY_THEMES from theme.js
 */

export const STORY_IDS = {
  LATENCY: 'latency',
  CACHE: 'cache',
  ROUTING: 'routing',
  QUALITY: 'quality',
  TOKEN: 'token_imbalance',
  PROMPT: 'system_prompt',
  COST: 'cost',
  OPTIMIZATION: 'optimization',
  QUEUE: 'queue',
};

export const STORY_METADATA = {
  [STORY_IDS.LATENCY]: {
    id: 'latency',
    title: 'Latency Analysis',
    emoji: '🌐',
    description: 'Identify slow operations and optimize response times',
    color: 'orange',
    gradient: 'from-orange-500 to-orange-600',
    route: '/stories/latency',
    priority: 1,
    question: 'Where are my slow operations and how do I fix them?',
  },
  [STORY_IDS.CACHE]: {
    id: 'cache',
    title: 'Caching Strategy',
    emoji: '💾',
    description: 'Find duplicate prompts and caching opportunities',
    color: 'pink',
    gradient: 'from-pink-500 to-pink-600',
    route: '/stories/cache',
    priority: 2,
    question: 'Where are my caching opportunities and how much can I save?',
  },
  [STORY_IDS.ROUTING]: {
    id: 'routing',
    title: 'Routing Opportunities',
    emoji: '🔀',
    description: 'Optimize model selection for cost and quality',
    color: 'purple',
    gradient: 'from-purple-500 to-purple-600',
    route: '/stories/routing',
    priority: 3,
    question: 'Am I using the right models for each task?',
  },
  [STORY_IDS.QUALITY]: {
    id: 'quality',
    title: 'Quality Monitoring',
    emoji: '❌',
    description: 'Track errors, hallucinations, and quality scores',
    color: 'red',
    gradient: 'from-red-500 to-red-600',
    route: '/stories/quality',
    priority: 4,
    question: 'Where are my quality problems and what\'s causing them?',
  },
  [STORY_IDS.TOKEN]: {
    id: 'token_imbalance',
    title: 'Token Efficiency',
    emoji: '⚖️',
    description: 'Balance prompt-to-completion token ratios',
    color: 'yellow',
    gradient: 'from-yellow-500 to-yellow-600',
    route: '/stories/token_imbalance',
    priority: 5,
    question: 'Are my prompts generating too much or too little output?',
  },
  [STORY_IDS.PROMPT]: {
    id: 'system_prompt',
    title: 'Prompt Composition',
    emoji: '📝',
    description: 'Analyze system prompt token usage and efficiency',
    color: 'cyan',
    gradient: 'from-cyan-500 to-cyan-600',
    route: '/stories/system_prompt',
    priority: 6,
    question: 'How much of my prompt is system instructions vs. user content?',
  },
  [STORY_IDS.COST]: {
    id: 'cost',
    title: 'Cost Analysis',
    emoji: '💰',
    description: 'Identify cost concentration and savings opportunities',
    color: 'amber',
    gradient: 'from-amber-500 to-amber-600',
    route: '/stories/cost',
    priority: 7,
    question: 'Where is my money going and how can I reduce costs?',
  },
  [STORY_IDS.OPTIMIZATION]: {
    id: 'optimization',
    title: 'Optimization Impact',
    emoji: '🎯',
    description: 'Measure before/after optimization results',
    color: 'green',
    gradient: 'from-green-500 to-green-600',
    route: '/stories/optimization',
    priority: 8,
    question: 'Did my optimizations work? What\'s the before/after comparison?',
  },
  [STORY_IDS.QUEUE]: {
    id: 'queue',
    title: 'Optimization Queue',
    emoji: '📋',
    description: 'View pending optimizations from all stories',
    color: 'blue',
    gradient: 'from-blue-500 to-blue-600',
    route: '/optimization',
    priority: 9,
    question: 'What optimizations are pending and what should I fix next?',
  },
};

/**
 * Get story metadata by ID
 */
export function getStoryMetadata(storyId) {
  return STORY_METADATA[storyId] || null;
}

/**
 * Get all stories sorted by priority
 */
export function getAllStories() {
  return Object.values(STORY_METADATA).sort((a, b) => a.priority - b.priority);
}

/**
 * Get story route by ID
 */
export function getStoryRoute(storyId) {
  return STORY_METADATA[storyId]?.route || '/';
}

/**
 * Health score thresholds
 */
export const HEALTH_THRESHOLDS = {
  EXCELLENT: 90,
  GOOD: 80,
  WARNING: 50,
  CRITICAL: 0,
};

/**
 * Get health status from score
 */
export function getHealthStatus(score) {
  if (score >= HEALTH_THRESHOLDS.GOOD) return 'ok';
  if (score >= HEALTH_THRESHOLDS.WARNING) return 'warning';
  return 'error';
}

export default STORY_METADATA;