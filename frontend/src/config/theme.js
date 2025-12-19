/**
 * Observatory Theme Configuration
 * 
 * Rainbow color scheme for all 8 stories + chart configs.
 * Each story gets a signature color with matching gradients and accents.
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
    gradient: 'from-orange-900/50 to-gray-900',
    border: 'border-orange-500',
    borderHover: 'hover:border-orange-400',
    text: 'text-orange-400',
    textLight: 'text-orange-300',
    bg: 'bg-orange-600',
    bgHover: 'hover:bg-orange-500',
    bgLight: 'bg-orange-900/30',
    badgeBg: 'bg-orange-500/30',
    badgeBorder: 'border-orange-500',
  },
  cache: {
    id: 'cache',
    name: 'Caching Strategy',
    emoji: '💾',
    color: '#ec4899', // pink-500
    gradient: 'from-pink-900/50 to-gray-900',
    border: 'border-pink-500',
    borderHover: 'hover:border-pink-400',
    text: 'text-pink-400',
    textLight: 'text-pink-300',
    bg: 'bg-pink-600',
    bgHover: 'hover:bg-pink-500',
    bgLight: 'bg-pink-900/30',
    badgeBg: 'bg-pink-500/30',
    badgeBorder: 'border-pink-500',
  },
  routing: {
    id: 'routing',
    name: 'Routing Opportunities',
    emoji: '🔀',
    color: '#8b5cf6', // purple-500
    gradient: 'from-purple-900/50 to-gray-900',
    border: 'border-purple-500',
    borderHover: 'hover:border-purple-400',
    text: 'text-purple-400',
    textLight: 'text-purple-300',
    bg: 'bg-purple-600',
    bgHover: 'hover:bg-purple-500',
    bgLight: 'bg-purple-900/30',
    badgeBg: 'bg-purple-500/30',
    badgeBorder: 'border-purple-500',
  },
  quality: {
    id: 'quality',
    name: 'Quality Monitoring',
    emoji: '❌',
    color: '#ef4444', // red-500
    gradient: 'from-red-900/50 to-gray-900',
    border: 'border-red-500',
    borderHover: 'hover:border-red-400',
    text: 'text-red-400',
    textLight: 'text-red-300',
    bg: 'bg-red-600',
    bgHover: 'hover:bg-red-500',
    bgLight: 'bg-red-900/30',
    badgeBg: 'bg-red-500/30',
    badgeBorder: 'border-red-500',
  },
  token_imbalance: {
    id: 'token_imbalance',
    name: 'Token Efficiency',
    emoji: '⚖️',
    color: '#eab308', // yellow-500
    gradient: 'from-yellow-900/50 to-gray-900',
    border: 'border-yellow-500',
    borderHover: 'hover:border-yellow-400',
    text: 'text-yellow-400',
    textLight: 'text-yellow-300',
    bg: 'bg-yellow-600',
    bgHover: 'hover:bg-yellow-500',
    bgLight: 'bg-yellow-900/30',
    badgeBg: 'bg-yellow-500/30',
    badgeBorder: 'border-yellow-500',
  },
  system_prompt: {
    id: 'system_prompt',
    name: 'Prompt Composition',
    emoji: '📝',
    color: '#06b6d4', // cyan-500
    gradient: 'from-cyan-900/50 to-gray-900',
    border: 'border-cyan-500',
    borderHover: 'hover:border-cyan-400',
    text: 'text-cyan-400',
    textLight: 'text-cyan-300',
    bg: 'bg-cyan-600',
    bgHover: 'hover:bg-cyan-500',
    bgLight: 'bg-cyan-900/30',
    badgeBg: 'bg-cyan-500/30',
    badgeBorder: 'border-cyan-500',
  },
  cost: {
    id: 'cost',
    name: 'Cost Analysis',
    emoji: '💰',
    color: '#facc15', // amber-400
    gradient: 'from-amber-900/50 to-gray-900',
    border: 'border-amber-500',
    borderHover: 'hover:border-amber-400',
    text: 'text-amber-400',
    textLight: 'text-amber-300',
    bg: 'bg-amber-600',
    bgHover: 'hover:bg-amber-500',
    bgLight: 'bg-amber-900/30',
    badgeBg: 'bg-amber-500/30',
    badgeBorder: 'border-amber-500',
  },
  optimization: {
    id: 'optimization',
    name: 'Optimization Impact',
    emoji: '🎯',
    color: '#22c55e', // green-500
    gradient: 'from-green-900/50 to-gray-900',
    border: 'border-green-500',
    borderHover: 'hover:border-green-400',
    text: 'text-green-400',
    textLight: 'text-green-300',
    bg: 'bg-green-600',
    bgHover: 'hover:bg-green-500',
    bgLight: 'bg-green-900/30',
    badgeBg: 'bg-green-500/30',
    badgeBorder: 'border-green-500',
  },
};

// =============================================================================
// CHART CONFIGURATION
// =============================================================================

export const CHART_CONFIG = {
  // Grid styling
  grid: {
    strokeDasharray: '3 3',
    stroke: '#374151', // gray-700
  },
  
  // Axis styling
  axis: {
    stroke: '#9ca3af', // gray-400
    fontSize: 12,
  },
  
  // Tooltip styling
  tooltip: {
    contentStyle: {
      backgroundColor: '#1f2937', // gray-800
      border: '1px solid #374151', // gray-700
      borderRadius: '8px',
      color: '#f3f4f6', // gray-100
    },
    cursor: {
      stroke: '#6b7280', // gray-500
    },
  },
  
  // Legend styling
  legend: {
    wrapperStyle: {
      color: '#9ca3af', // gray-400
    },
  },
};

// =============================================================================
// GENERAL COLORS
// =============================================================================

export const COLORS = {
  // Status colors
  success: '#22c55e', // green-500
  warning: '#eab308', // yellow-500
  error: '#ef4444', // red-500
  info: '#3b82f6', // blue-500
  
  // Background
  bgPrimary: '#030712', // gray-950
  bgSecondary: '#111827', // gray-900
  bgTertiary: '#1f2937', // gray-800
  
  // Text
  textPrimary: '#f9fafb', // gray-50
  textSecondary: '#d1d5db', // gray-300
  textMuted: '#9ca3af', // gray-400
  
  // Borders
  border: '#374151', // gray-700
  borderLight: '#4b5563', // gray-600
};

export default STORY_THEMES;