/**
 * Validation Functions
 * 
 * Functions to validate user inputs, API data, and configurations.
 */

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean} True if valid
 */
export function isValidEmail(email) {
  if (!email || typeof email !== 'string') return false;
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

/**
 * Validate URL format
 * @param {string} url - URL to validate
 * @returns {boolean} True if valid
 */
export function isValidUrl(url) {
  if (!url || typeof url !== 'string') return false;
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

/**
 * Validate number is within range
 * @param {number} value - Number to validate
 * @param {number} min - Minimum value (inclusive)
 * @param {number} max - Maximum value (inclusive)
 * @returns {boolean} True if in range
 */
export function isInRange(value, min, max) {
  if (typeof value !== 'number' || isNaN(value)) return false;
  return value >= min && value <= max;
}

/**
 * Validate health score (0-100)
 * @param {number} score - Health score
 * @returns {boolean} True if valid
 */
export function isValidHealthScore(score) {
  return isInRange(score, 0, 100);
}

/**
 * Validate quality score (0-10)
 * @param {number} score - Quality score
 * @returns {boolean} True if valid
 */
export function isValidQualityScore(score) {
  return isInRange(score, 0, 10);
}

/**
 * Validate time range (days)
 * @param {number} days - Number of days
 * @returns {boolean} True if valid
 */
export function isValidTimeRange(days) {
  return Number.isInteger(days) && days > 0 && days <= 365;
}

/**
 * Validate story ID
 * @param {string} storyId - Story ID to validate
 * @returns {boolean} True if valid
 */
export function isValidStoryId(storyId) {
  const validIds = [
    'latency',
    'cache',
    'routing',
    'quality',
    'token_imbalance',
    'system_prompt',
    'cost',
    'optimization',
  ];
  return validIds.includes(storyId);
}

/**
 * Validate status value
 * @param {string} status - Status to validate
 * @returns {boolean} True if valid
 */
export function isValidStatus(status) {
  const validStatuses = ['ok', 'warning', 'error'];
  return validStatuses.includes(status);
}

/**
 * Validate string is not empty
 * @param {string} str - String to validate
 * @param {number} minLength - Minimum length (default: 1)
 * @returns {boolean} True if not empty
 */
export function isNotEmpty(str, minLength = 1) {
  if (!str || typeof str !== 'string') return false;
  return str.trim().length >= minLength;
}

/**
 * Validate string length
 * @param {string} str - String to validate
 * @param {number} max - Maximum length
 * @returns {boolean} True if within length
 */
export function isValidLength(str, max) {
  if (!str || typeof str !== 'string') return false;
  return str.length <= max;
}

/**
 * Validate percentage (0-100)
 * @param {number} value - Percentage value
 * @returns {boolean} True if valid
 */
export function isValidPercentage(value) {
  return isInRange(value, 0, 100);
}

/**
 * Validate positive number
 * @param {number} value - Number to validate
 * @returns {boolean} True if positive
 */
export function isPositive(value) {
  return typeof value === 'number' && !isNaN(value) && value > 0;
}

/**
 * Validate non-negative number
 * @param {number} value - Number to validate
 * @returns {boolean} True if non-negative
 */
export function isNonNegative(value) {
  return typeof value === 'number' && !isNaN(value) && value >= 0;
}

/**
 * Validate API response has required fields
 * @param {object} response - API response
 * @param {string[]} requiredFields - Required field names
 * @returns {boolean} True if all fields present
 */
export function hasRequiredFields(response, requiredFields) {
  if (!response || typeof response !== 'object') return false;
  return requiredFields.every(field => field in response);
}

/**
 * Validate date is in the past
 * @param {string|Date} date - Date to validate
 * @returns {boolean} True if in past
 */
export function isInPast(date) {
  try {
    const d = typeof date === 'string' ? new Date(date) : date;
    return d < new Date();
  } catch {
    return false;
  }
}

/**
 * Validate ISO date string
 * @param {string} dateString - Date string to validate
 * @returns {boolean} True if valid ISO date
 */
export function isValidISODate(dateString) {
  if (!dateString || typeof dateString !== 'string') return false;
  const date = new Date(dateString);
  return !isNaN(date.getTime());
}

/**
 * Sanitize string (remove dangerous characters)
 * @param {string} str - String to sanitize
 * @returns {string} Sanitized string
 */
export function sanitizeString(str) {
  if (!str || typeof str !== 'string') return '';
  return str.replace(/[<>'"]/g, '');
}

export default {
  isValidEmail,
  isValidUrl,
  isInRange,
  isValidHealthScore,
  isValidQualityScore,
  isValidTimeRange,
  isValidStoryId,
  isValidStatus,
  isNotEmpty,
  isValidLength,
  isValidPercentage,
  isPositive,
  isNonNegative,
  hasRequiredFields,
  isInPast,
  isValidISODate,
  sanitizeString,
};