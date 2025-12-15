// Observatory Color Palette
// Extracted from original Stories.jsx - December 2024

export const COLORS = {
  // Chart colors (Recharts)
  chart: [
    '#ef4444', // red
    '#f97316', // orange  
    '#eab308', // yellow
    '#22c55e', // green
    '#3b82f6', // blue
    '#8b5cf6', // purple
    '#ec4899', // pink
  ],
  
  // Status colors
  red: '#ef4444',
  orange: '#f97316',
  yellow: '#eab308',
  green: '#22c55e',
  blue: '#3b82f6',
  purple: '#8b5cf6',
  pink: '#ec4899',
};

// Recharts configuration
export const CHART_CONFIG = {
  tooltip: {
    contentStyle: {
      backgroundColor: '#1f2937',
      border: 'none',
      borderRadius: '8px',
    },
  },
  grid: {
    stroke: '#374151',
    strokeDasharray: '3 3',
  },
  axis: {
    stroke: '#9ca3af',
  },
};

// Tailwind class names (for dark theme)
export const THEME = {
  background: {
    primary: 'bg-gray-950',   // Main background
    card: 'bg-gray-900',       // Cards
    nested: 'bg-gray-800',     // Nested elements
    hover: 'hover:bg-gray-800',
  },
  border: {
    default: 'border-gray-700',
    hover: 'hover:border-gray-600',
  },
  text: {
    primary: 'text-gray-100',
    secondary: 'text-gray-300',
    muted: 'text-gray-400',
    disabled: 'text-gray-500',
  },
};