/**
 * Helper Utilities
 * 
 * General-purpose helper functions used throughout the application.
 */

/**
 * Safely get nested object property
 * @param {object} obj - Object to traverse
 * @param {string} path - Dot-notation path (e.g., 'user.profile.name')
 * @param {*} defaultValue - Default value if path not found
 * @returns {*} Value at path or default
 */
export function getNestedValue(obj, path, defaultValue = undefined) {
  return path
    .split('.')
    .reduce((acc, part) => acc && acc[part], obj) ?? defaultValue;
}

/**
 * Deep clone an object
 * @param {*} obj - Object to clone
 * @returns {*} Cloned object
 */
export function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') return obj;
  return JSON.parse(JSON.stringify(obj));
}

/**
 * Debounce function
 * @param {Function} func - Function to debounce
 * @param {number} wait - Milliseconds to wait
 * @returns {Function} Debounced function
 */
export function debounce(func, wait = 300) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Check if value is empty (null, undefined, empty string, empty array, empty object)
 * @param {*} value - Value to check
 * @returns {boolean} True if empty
 */
export function isEmpty(value) {
  if (value === null || value === undefined) return true;
  if (typeof value === 'string') return value.trim() === '';
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === 'object') return Object.keys(value).length === 0;
  return false;
}

/**
 * Sort array of objects by key
 * @param {Array} array - Array to sort
 * @param {string} key - Object key to sort by
 * @param {string} order - 'asc' or 'desc' (default: 'asc')
 * @returns {Array} Sorted array
 */
export function sortByKey(array, key, order = 'asc') {
  return [...array].sort((a, b) => {
    const aVal = getNestedValue(a, key);
    const bVal = getNestedValue(b, key);
    
    if (aVal < bVal) return order === 'asc' ? -1 : 1;
    if (aVal > bVal) return order === 'asc' ? 1 : -1;
    return 0;
  });
}

/**
 * Group array of objects by key
 * @param {Array} array - Array to group
 * @param {string} key - Object key to group by
 * @returns {object} Grouped object
 */
export function groupBy(array, key) {
  return array.reduce((result, item) => {
    const groupKey = getNestedValue(item, key);
    if (!result[groupKey]) {
      result[groupKey] = [];
    }
    result[groupKey].push(item);
    return result;
  }, {});
}

/**
 * Calculate percentage change between two values
 * @param {number} oldValue - Original value
 * @param {number} newValue - New value
 * @returns {number} Percentage change (e.g., 0.25 for 25% increase)
 */
export function percentageChange(oldValue, newValue) {
  if (oldValue === 0) return newValue === 0 ? 0 : 1;
  return (newValue - oldValue) / oldValue;
}

/**
 * Clamp number between min and max
 * @param {number} num - Number to clamp
 * @param {number} min - Minimum value
 * @param {number} max - Maximum value
 * @returns {number} Clamped number
 */
export function clamp(num, min, max) {
  return Math.min(Math.max(num, min), max);
}

/**
 * Generate unique ID
 * @returns {string} Unique ID
 */
export function generateId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Wait for specified milliseconds (async)
 * @param {number} ms - Milliseconds to wait
 * @returns {Promise} Promise that resolves after delay
 */
export function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>} True if successful
 */
export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    console.error('Failed to copy to clipboard:', err);
    return false;
  }
}

/**
 * Download data as JSON file
 * @param {*} data - Data to download
 * @param {string} filename - Filename
 */
export function downloadJSON(data, filename = 'data.json') {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export default {
  getNestedValue,
  deepClone,
  debounce,
  isEmpty,
  sortByKey,
  groupBy,
  percentageChange,
  clamp,
  generateId,
  sleep,
  copyToClipboard,
  downloadJSON,
};