/**
 * Formatting Utilities
 * 
 * Functions to format numbers, currency, dates, latency, and other data
 * for consistent display across the Observatory UI.
 */

/**
 * Format number with commas (e.g., 1234567 → "1,234,567")
 * @param {number} num - Number to format
 * @returns {string} Formatted number
 */
export function formatNumber(num) {
  if (num === null || num === undefined) return '0';
  return num.toLocaleString('en-US');
}

/**
 * Format currency (e.g., 1.234 → "$1.23")
 * @param {number} amount - Dollar amount
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted currency
 */
export function formatCurrency(amount, decimals = 2) {
  if (amount === null || amount === undefined) return '$0.00';
  
  // For very small amounts, show more precision
  if (amount > 0 && amount < 0.01 && decimals === 2) {
    decimals = 4;
  }
  
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(amount);
}

/**
 * Format latency in milliseconds to human-readable format
 * @param {number} ms - Latency in milliseconds
 * @returns {string} Formatted latency (e.g., "1.23s" or "456ms")
 */
export function formatLatency(ms) {
  if (ms === null || ms === undefined) return '0ms';
  
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  }
  
  return `${(ms / 1000).toFixed(2)}s`;
}

/**
 * Format percentage (e.g., 0.1234 → "12.34%" or 12.34 → "12.34%")
 * @param {number} value - Percentage as decimal (0.1234) or whole number (12.34)
 * @param {number} decimals - Number of decimal places (default: 1)
 * @returns {string} Formatted percentage
 */
export function formatPercentage(value, decimals = 1) {
  if (value === null || value === undefined) return '0%';
  
  // If value is between 0-1, treat as decimal (0.1234 = 12.34%)
  // If value is > 1, treat as whole number (12.34 = 12.34%)
  const percentage = value <= 1 ? value * 100 : value;
  
  return `${percentage.toFixed(decimals)}%`;
}

/**
 * Format large numbers with K/M/B suffix
 * @param {number} num - Number to format
 * @param {number} decimals - Number of decimal places (default: 1)
 * @returns {string} Formatted number (e.g., "1.2K", "3.4M")
 */
export function formatCompactNumber(num, decimals = 1) {
  if (num === null || num === undefined) return '0';
  
  const absNum = Math.abs(num);
  
  if (absNum >= 1_000_000_000) {
    return `${(num / 1_000_000_000).toFixed(decimals)}B`;
  }
  if (absNum >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(decimals)}M`;
  }
  if (absNum >= 1_000) {
    return `${(num / 1_000).toFixed(decimals)}K`;
  }
  
  return num.toString();
}

/**
 * Format token count with commas
 * @param {number} tokens - Token count
 * @returns {string} Formatted token count
 */
export function formatTokens(tokens) {
  if (tokens === null || tokens === undefined) return '0';
  return formatNumber(tokens);
}

/**
 * Format date to readable string
 * @param {string|Date} date - Date to format
 * @param {boolean} includeTime - Include time in output (default: false)
 * @returns {string} Formatted date
 */
export function formatDate(date, includeTime = false) {
  if (!date) return '';
  
  const d = typeof date === 'string' ? new Date(date) : date;
  
  const options = {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    ...(includeTime && {
      hour: 'numeric',
      minute: '2-digit',
    }),
  };
  
  return d.toLocaleDateString('en-US', options);
}

/**
 * Format relative time (e.g., "2 hours ago")
 * @param {string|Date} date - Date to format
 * @returns {string} Relative time string
 */
export function formatRelativeTime(date) {
  if (!date) return '';
  
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffMs = now - d;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  
  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  
  return formatDate(d);
}

/**
 * Format duration in seconds to human-readable format
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration (e.g., "2h 30m", "45s")
 */
export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return '0s';
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  }
  return `${secs}s`;
}

/**
 * Format quality score (0-10 scale)
 * @param {number} score - Quality score
 * @param {number} decimals - Decimal places (default: 1)
 * @returns {string} Formatted score (e.g., "8.5/10")
 */
export function formatQualityScore(score, decimals = 1) {
  if (score === null || score === undefined) return '0.0/10';
  return `${score.toFixed(decimals)}/10`;
}

/**
 * Truncate text to max length with ellipsis
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text
 */
export function truncateText(text, maxLength = 50) {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return `${text.substring(0, maxLength)}...`;
}

/**
 * Format error rate as percentage with color coding
 * @param {number} rate - Error rate (0-1 decimal)
 * @returns {object} { text: string, color: string }
 */
export function formatErrorRate(rate) {
  const percentage = formatPercentage(rate);
  
  let color = 'text-green-600 dark:text-green-400'; // < 1%
  if (rate >= 0.05) color = 'text-red-600 dark:text-red-400'; // >= 5%
  else if (rate >= 0.02) color = 'text-yellow-600 dark:text-yellow-400'; // >= 2%
  
  return { text: percentage, color };
}

/**
 * Format cache hit rate as percentage with color coding
 * @param {number} rate - Cache hit rate (0-1 decimal)
 * @returns {object} { text: string, color: string }
 */
export function formatCacheHitRate(rate) {
  const percentage = formatPercentage(rate);
  
  let color = 'text-red-600 dark:text-red-400'; // < 30%
  if (rate >= 0.7) color = 'text-green-600 dark:text-green-400'; // >= 70%
  else if (rate >= 0.3) color = 'text-yellow-600 dark:text-yellow-400'; // >= 30%
  
  return { text: percentage, color };
}

export default {
  formatNumber,
  formatCurrency,
  formatLatency,
  formatPercentage,
  formatCompactNumber,
  formatTokens,
  formatDate,
  formatRelativeTime,
  formatDuration,
  formatQualityScore,
  truncateText,
  formatErrorRate,
  formatCacheHitRate,
};