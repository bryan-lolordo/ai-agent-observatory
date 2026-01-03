/**
 * Component Theme Utilities
 * 
 * Helper functions to ensure components properly integrate with
 * the Observatory theme system (config/theme.js)
 * 
 * Use these utilities when you need to:
 * - Get theme-aware classes programmatically
 * - Validate theme objects
 * - Apply dynamic theme colors
 */

import { STORY_THEMES } from '../config/theme';

// =============================================================================
// BASE THEME - Neutral Colors for Components
// =============================================================================
// These are the "gray" colors used across all components
// Change these once to update your entire app's base color scheme

export const BASE_THEME = {
  // Container colors
  container: {
    primary: 'bg-gray-900',      // Main card backgrounds
    secondary: 'bg-gray-800',    // Nested/hover backgrounds
    tertiary: 'bg-gray-950',     // Page background
  },
  
  // Border colors
  border: {
    default: 'border-gray-700',  // Standard borders
    light: 'border-gray-600',    // Lighter variant
    hover: 'border-gray-600',    // Hover state
  },
  
  // Text colors
  text: {
    primary: 'text-gray-100',    // Main text
    secondary: 'text-gray-300',  // Secondary text
    muted: 'text-gray-500',      // Muted/helper text
  },
  
  // State colors
  state: {
    hover: 'hover:bg-gray-800/50',
    active: 'bg-gray-800',
    disabled: 'bg-gray-800/30',
  },
  
  // Status colors (for alerts, badges, notifications)
  status: {
    error: {
      bg: 'bg-red-900/20',
      border: 'border-red-500',
      text: 'text-red-400',
      textBold: 'text-red-400',
      hover: 'hover:bg-red-900/30',
    },
    warning: {
      bg: 'bg-yellow-900/20',
      border: 'border-yellow-500',
      text: 'text-yellow-400',
      textBold: 'text-yellow-400',
      hover: 'hover:bg-yellow-900/30',
    },
    success: {
      bg: 'bg-green-900/20',
      border: 'border-green-500',
      text: 'text-green-400',
      textBold: 'text-green-400',
      hover: 'hover:bg-green-900/30',
    },
    info: {
      bg: 'bg-blue-900/20',
      border: 'border-blue-500',
      text: 'text-blue-400',
      textBold: 'text-blue-400',
      hover: 'hover:bg-blue-900/30',
    },
  },
};

/**
 * Get theme object for a story ID
 * 
 * @param {string} storyId - Story identifier (e.g., 'quality', 'latency')
 * @returns {object} Theme object with all properties
 */
export const getStoryTheme = (storyId) => {
  return STORY_THEMES[storyId] || STORY_THEMES.latency; // Default to latency
};

/**
 * Get theme from STORY_THEMES by story ID
 * 
 * @param {string} storyId 
 * @returns {object} Theme object
 */
export const useStoryTheme = (storyId) => {
  const theme = STORY_THEMES[storyId];
  if (!theme) {
    console.warn(`Theme not found for story: ${storyId}, using latency theme as fallback`);
    return STORY_THEMES.latency;
  }
  return theme;
};

/**
 * Validate that a theme object has required properties
 * 
 * @param {object} theme - Theme object to validate
 * @returns {boolean} True if valid
 */
export const isValidTheme = (theme) => {
  if (!theme) return false;
  
  const requiredProps = ['id', 'name', 'emoji', 'color', 'text', 'bg'];
  return requiredProps.every(prop => theme.hasOwnProperty(prop));
};

/**
 * Get dynamic status colors based on severity
 * Useful for alerts, badges, and status indicators
 * 
 * @param {string} severity - 'critical' | 'warning' | 'info' | 'ok'
 * @returns {object} Color classes
 */
export const getSeverityColors = (severity) => {
  const colors = {
    critical: {
      text: 'text-red-400',
      bg: 'bg-red-900/30',
      border: 'border-red-500',
      icon: '🔴',
    },
    warning: {
      text: 'text-yellow-400',
      bg: 'bg-yellow-900/30',
      border: 'border-yellow-500',
      icon: '⚠️',
    },
    info: {
      text: 'text-blue-400',
      bg: 'bg-blue-900/30',
      border: 'border-blue-500',
      icon: 'ℹ️',
    },
    ok: {
      text: 'text-green-400',
      bg: 'bg-green-900/30',
      border: 'border-green-500',
      icon: '✅',
    },
  };
  
  return colors[severity] || colors.info;
};

/**
 * Generate dynamic CSS for glowing divider
 * 
 * @param {object} theme - Theme object
 * @returns {object} Style object for inline styles
 */
export const getDividerStyle = (theme) => {
  if (!theme?.color) return {};
  
  return {
    background: `linear-gradient(to right, ${theme.color}, ${theme.color})`,
    boxShadow: `0 0 10px ${theme.color}80`,
  };
};

/**
 * Generate row hover background color
 * 
 * @param {object} theme - Theme object
 * @returns {object} Style object for inline styles
 */
export const getRowHoverStyle = (theme) => {
  if (!theme?.color) return {};
  
  return {
    backgroundColor: `${theme.color}08`, // 3% opacity
  };
};

/**
 * Get all available story themes as array
 * Useful for dropdowns, menus, etc.
 * 
 * @returns {array} Array of theme objects
 */
export const getAllThemes = () => {
  return Object.values(STORY_THEMES);
};

/**
 * Get theme color with opacity
 * 
 * @param {object} theme - Theme object
 * @param {number} opacity - Opacity value 0-1
 * @returns {string} rgba color string
 */
export const getThemeColorWithOpacity = (theme, opacity = 0.5) => {
  if (!theme?.colorRgb) return 'rgba(255, 255, 255, 0.5)';
  
  return `rgba(${theme.colorRgb}, ${opacity})`;
};

/**
 * Check if theme is a "warm" color (useful for text contrast)
 * 
 * @param {object} theme 
 * @returns {boolean}
 */
export const isWarmColor = (theme) => {
  const warmThemes = ['latency', 'cost', 'quality', 'token_imbalance'];
  return warmThemes.includes(theme?.id);
};

/**
 * Check if theme is a "cool" color
 * 
 * @param {object} theme 
 * @returns {boolean}
 */
export const isCoolColor = (theme) => {
  const coolThemes = ['cache', 'routing', 'system_prompt', 'optimization'];
  return coolThemes.includes(theme?.id);
};

export default {
  BASE_THEME,
  getStoryTheme,
  useStoryTheme,
  isValidTheme,
  getSeverityColors,
  getDividerStyle,
  getRowHoverStyle,
  getAllThemes,
  getThemeColorWithOpacity,
  isWarmColor,
  isCoolColor,
};