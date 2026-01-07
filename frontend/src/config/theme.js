/**
 * Observatory Theme Configuration
 * 
 * Rainbow color scheme for all 8 stories + chart configs.
 * Each story gets a signature color with matching gradients and accents.
 * 
 * Design Pattern: 2E Header Divider
 * - Neutral gray container
 * - Glowing divider line in story color between header and table
 * - Story color on sorted column, active filter, and key metrics
 */

// =============================================================================
// STORY THEMES - Rainbow Color Palette
// =============================================================================

export const STORY_THEMES = {
  latency: {
    id: 'latency',
    name: 'Latency Analysis',
    emoji: '🌐',
    color: '#f97316', // orange-500
    colorRgb: '249, 115, 22',
    gradient: 'from-orange-900/50 to-gray-900',
    border: 'border-orange-500',
    borderLight: 'border-orange-500/30',
    borderHover: 'hover:border-orange-400',
    text: 'text-orange-400',
    textLight: 'text-orange-300',
    bg: 'bg-orange-600',
    bgHover: 'hover:bg-orange-500',
    bgLight: 'bg-orange-900/30',
    bgSubtle: 'bg-orange-500/10',
    badgeBg: 'bg-orange-500/30',
    badgeBorder: 'border-orange-500',
    // 2E specific
    dividerGlow: 'shadow-[0_0_10px_rgba(249,115,22,0.5)]',
    rowHover: 'hover:bg-orange-500/5',
  },
  cache: {
    id: 'cache',
    name: 'Caching Strategy',
    emoji: '💾',
    color: '#ec4899', // pink-500
    colorRgb: '236, 72, 153',
    gradient: 'from-pink-900/50 to-gray-900',
    border: 'border-pink-500',
    borderLight: 'border-pink-500/30',
    borderHover: 'hover:border-pink-400',
    text: 'text-pink-400',
    textLight: 'text-pink-300',
    bg: 'bg-pink-600',
    bgHover: 'hover:bg-pink-500',
    bgLight: 'bg-pink-900/30',
    bgSubtle: 'bg-pink-500/10',
    badgeBg: 'bg-pink-500/30',
    badgeBorder: 'border-pink-500',
    dividerGlow: 'shadow-[0_0_10px_rgba(236,72,153,0.5)]',
    rowHover: 'hover:bg-pink-500/5',
  },
  routing: {
    id: 'routing',
    name: 'Routing Opportunities',
    emoji: '🔀',
    color: '#8b5cf6', // purple-500
    colorRgb: '139, 92, 246',
    gradient: 'from-purple-900/50 to-gray-900',
    border: 'border-purple-500',
    borderLight: 'border-purple-500/30',
    borderHover: 'hover:border-purple-400',
    text: 'text-purple-400',
    textLight: 'text-purple-300',
    bg: 'bg-purple-600',
    bgHover: 'hover:bg-purple-500',
    bgLight: 'bg-purple-900/30',
    bgSubtle: 'bg-purple-500/10',
    badgeBg: 'bg-purple-500/30',
    badgeBorder: 'border-purple-500',
    dividerGlow: 'shadow-[0_0_10px_rgba(139,92,246,0.5)]',
    rowHover: 'hover:bg-purple-500/5',
  },
  quality: {
    id: 'quality',
    name: 'Quality Monitoring',
    emoji: '⭐',
    color: '#ef4444', // red-500
    colorRgb: '239, 68, 68',
    gradient: 'from-red-900/50 to-gray-900',
    border: 'border-red-500',
    borderLight: 'border-red-500/30',
    borderHover: 'hover:border-red-400',
    text: 'text-red-400',
    textLight: 'text-red-300',
    bg: 'bg-red-600',
    bgHover: 'hover:bg-red-500',
    bgLight: 'bg-red-900/30',
    bgSubtle: 'bg-red-500/10',
    badgeBg: 'bg-red-500/30',
    badgeBorder: 'border-red-500',
    dividerGlow: 'shadow-[0_0_10px_rgba(239,68,68,0.5)]',
    rowHover: 'hover:bg-red-500/5',
  },
  token_imbalance: {
    id: 'token_imbalance',
    name: 'Token Efficiency',
    emoji: '⚖️',
    color: '#eab308', // yellow-500
    colorRgb: '234, 179, 8',
    gradient: 'from-yellow-900/50 to-gray-900',
    border: 'border-yellow-500',
    borderLight: 'border-yellow-500/30',
    borderHover: 'hover:border-yellow-400',
    text: 'text-yellow-400',
    textLight: 'text-yellow-300',
    bg: 'bg-yellow-600',
    bgHover: 'hover:bg-yellow-500',
    bgLight: 'bg-yellow-900/30',
    bgSubtle: 'bg-yellow-500/10',
    badgeBg: 'bg-yellow-500/30',
    badgeBorder: 'border-yellow-500',
    dividerGlow: 'shadow-[0_0_10px_rgba(234,179,8,0.5)]',
    rowHover: 'hover:bg-yellow-500/5',
  },
  system_prompt: {
    id: 'system_prompt',
    name: 'Prompt Composition',
    emoji: '📝',
    color: '#06b6d4', // cyan-500
    colorRgb: '6, 182, 212',
    gradient: 'from-cyan-900/50 to-gray-900',
    border: 'border-cyan-500',
    borderLight: 'border-cyan-500/30',
    borderHover: 'hover:border-cyan-400',
    text: 'text-cyan-400',
    textLight: 'text-cyan-300',
    bg: 'bg-cyan-600',
    bgHover: 'hover:bg-cyan-500',
    bgLight: 'bg-cyan-900/30',
    bgSubtle: 'bg-cyan-500/10',
    badgeBg: 'bg-cyan-500/30',
    badgeBorder: 'border-cyan-500',
    dividerGlow: 'shadow-[0_0_10px_rgba(6,182,212,0.5)]',
    rowHover: 'hover:bg-cyan-500/5',
  },
  cost: {
    id: 'cost',
    name: 'Cost Analysis',
    emoji: '💰',
    color: '#f59e0b', // amber-500
    colorRgb: '245, 158, 11',
    gradient: 'from-amber-900/50 to-gray-900',
    border: 'border-amber-500',
    borderLight: 'border-amber-500/30',
    borderHover: 'hover:border-amber-400',
    text: 'text-amber-400',
    textLight: 'text-amber-300',
    bg: 'bg-amber-600',
    bgHover: 'hover:bg-amber-500',
    bgLight: 'bg-amber-900/30',
    bgSubtle: 'bg-amber-500/10',
    badgeBg: 'bg-amber-500/30',
    badgeBorder: 'border-amber-500',
    dividerGlow: 'shadow-[0_0_10px_rgba(245,158,11,0.5)]',
    rowHover: 'hover:bg-amber-500/5',
  },
  optimization: {
    id: 'optimization',
    name: 'Optimization Impact',
    emoji: '🎯',
    color: '#22c55e', // green-500
    colorRgb: '34, 197, 94',
    gradient: 'from-green-900/50 to-gray-900',
    border: 'border-green-500',
    borderLight: 'border-green-500/30',
    borderHover: 'hover:border-green-400',
    text: 'text-green-400',
    textLight: 'text-green-300',
    bg: 'bg-green-600',
    bgHover: 'hover:bg-green-500',
    bgLight: 'bg-green-900/30',
    bgSubtle: 'bg-green-500/10',
    badgeBg: 'bg-green-500/30',
    badgeBorder: 'border-green-500',
    dividerGlow: 'shadow-[0_0_10px_rgba(34,197,94,0.5)]',
    rowHover: 'hover:bg-green-500/5',
  },
  queue: {
    id: 'queue',
    name: 'Optimization Queue',
    emoji: '📋',
    color: '#3b82f6', // blue-500
    colorRgb: '59, 130, 246',
    gradient: 'from-blue-900/50 to-gray-900',
    border: 'border-blue-500',
    borderLight: 'border-blue-500/30',
    borderHover: 'hover:border-blue-400',
    text: 'text-blue-400',
    textLight: 'text-blue-300',
    bg: 'bg-blue-600',
    bgHover: 'hover:bg-blue-500',
    bgLight: 'bg-blue-900/30',
    bgSubtle: 'bg-blue-500/10',
    badgeBg: 'bg-blue-500/30',
    badgeBorder: 'border-blue-500',
    dividerGlow: 'shadow-[0_0_10px_rgba(59,130,246,0.5)]',
    rowHover: 'hover:bg-blue-500/5',
  },
};

// =============================================================================
// LAYER2 TABLE THEME UTILITIES
// =============================================================================

/**
 * Get the CSS for the glowing divider
 */
export const getDividerStyle = (theme) => ({
  background: `linear-gradient(to right, ${theme.color}, ${theme.color})`,
  boxShadow: `0 0 10px ${theme.color}80`,
});

/**
 * Get row hover style
 */
export const getRowHoverStyle = (theme) => ({
  backgroundColor: `${theme.color}08`,
});

// =============================================================================
// CHART CONFIGURATION - Numerro Theme
// =============================================================================

export const CHART_CONFIG = {
  // Grid styling
  grid: {
    strokeDasharray: '3 3',
    stroke: '#3A3A3A',
  },

  // Axis styling
  axis: {
    stroke: '#A1A1AA',
    tick: { fill: '#A1A1AA', fontSize: 11 },
    axisLine: { stroke: '#3A3A3A' },
  },

  // Tooltip styling
  tooltip: {
    contentStyle: {
      backgroundColor: '#2B2B2B',
      border: '1px solid #404040',
      borderRadius: '8px',
      color: '#EDEDED',
    },
    cursor: {
      stroke: '#404040',
    },
  },

  // Legend styling
  legend: {
    wrapperStyle: {
      color: '#C7C7C7',
    },
  },

  // Reference lines
  referenceLine: {
    critical: '#ef4444',
    warning: '#eab308',
    info: '#3b82f6',
  },

  // Status-based bar colors (for charts with status indicators)
  statusColors: {
    severe: '#ef4444',
    high: '#f97316',
    moderate: '#eab308',
    good: '#22c55e',
  },

  // Opportunity colors (for routing)
  opportunityColors: {
    upgrade: '#ef4444',
    downgrade: '#3b82f6',
    keep: '#22c55e',
  },
};

// =============================================================================
// GENERAL COLORS - Numerro-Inspired Palette
// =============================================================================

export const COLORS = {
  // Status colors
  success: '#22c55e',
  warning: '#f59e0b',
  error: '#ef4444',
  info: '#3b82f6',
  
  // Background (Numerro dark gray palette)
  bgPrimary: '#1E1E1E',     // main app background
  bgSecondary: '#242424',   // nav, panels
  bgTertiary: '#2B2B2B',    // cards, tables, code blocks
  
  // Text (high readability)
  textPrimary: '#EDEDED',   // main text
  textSecondary: '#C7C7C7', // labels
  textMuted: '#9CA3AF',     // helper/metadata
  
  // Borders & Dividers
  border: '#343434',
  borderLight: '#404040',
};

// =============================================================================
// DATA COLORING (for dynamic value-based colors)
// =============================================================================

export const DATA_COLORS = {
  // Latency thresholds (ms)
  latency: {
    critical: { threshold: 10000, color: '#ef4444', class: 'text-red-400' },
    slow: { threshold: 5000, color: '#f97316', class: 'text-orange-400' },
    warning: { threshold: 3000, color: '#eab308', class: 'text-yellow-400' },
    good: { threshold: 0, color: '#22c55e', class: 'text-green-400' },
  },
  
  // Quality score thresholds
  quality: {
    bad: { threshold: 5, color: '#ef4444', class: 'text-red-400' },
    medium: { threshold: 7, color: '#eab308', class: 'text-yellow-400' },
    good: { threshold: 8, color: '#22c55e', class: 'text-green-400' },
    excellent: { threshold: 10, color: '#10b981', class: 'text-emerald-400' },
  },
  
  // Cost thresholds ($)
  cost: {
    expensive: { threshold: 0.10, color: '#ef4444', class: 'text-red-400' },
    moderate: { threshold: 0.05, color: '#f97316', class: 'text-orange-400' },
    low: { threshold: 0.01, color: '#eab308', class: 'text-yellow-400' },
    cheap: { threshold: 0, color: '#22c55e', class: 'text-green-400' },
  },
  
  // Token thresholds
  tokens: {
    huge: { threshold: 8000, color: '#ef4444', class: 'text-red-400' },
    large: { threshold: 4000, color: '#f97316', class: 'text-orange-400' },
    normal: { threshold: 0, color: '#d1d5db', class: 'text-numerro-text-secondary' },
  },
};

/**
 * Get color class for a latency value
 */
export const getLatencyColor = (ms) => {
  if (ms == null) return 'text-numerro-text-muted';
  if (ms > DATA_COLORS.latency.critical.threshold) return DATA_COLORS.latency.critical.class;
  if (ms > DATA_COLORS.latency.slow.threshold) return DATA_COLORS.latency.slow.class;
  if (ms > DATA_COLORS.latency.warning.threshold) return DATA_COLORS.latency.warning.class;
  return DATA_COLORS.latency.good.class;
};

/**
 * Get color class for a quality score
 */
export const getQualityColor = (score) => {
  if (score == null) return 'text-numerro-text-muted';
  if (score < DATA_COLORS.quality.bad.threshold) return DATA_COLORS.quality.bad.class;
  if (score < DATA_COLORS.quality.medium.threshold) return DATA_COLORS.quality.medium.class;
  if (score < DATA_COLORS.quality.good.threshold) return DATA_COLORS.quality.good.class;
  return DATA_COLORS.quality.excellent.class;
};

/**
 * Get color class for a cost value
 */
export const getCostColor = (cost) => {
  if (cost == null) return 'text-numerro-text-muted';
  if (cost > DATA_COLORS.cost.expensive.threshold) return DATA_COLORS.cost.expensive.class;
  if (cost > DATA_COLORS.cost.moderate.threshold) return DATA_COLORS.cost.moderate.class;
  if (cost > DATA_COLORS.cost.low.threshold) return DATA_COLORS.cost.low.class;
  return DATA_COLORS.cost.cheap.class;
};

// =============================================================================
// UI EFFECTS - Numerro Visual Polish
// =============================================================================

export const UI_EFFECTS = {
  // Card shadow for depth
  cardShadow: '0 8px 24px rgba(0,0,0,0.35)',
  
  // Glowing divider (pass RGB string like "249, 115, 22")
  dividerGlow: (rgb) => `0 0 10px rgba(${rgb}, 0.45)`,
  
  // Subtle row hover (pass hex color)
  rowHover: (hex) => `${hex}0D`, // 5-8% opacity
};

export default STORY_THEMES;