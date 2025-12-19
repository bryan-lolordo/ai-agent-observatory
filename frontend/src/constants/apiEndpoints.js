/**
 * API Endpoints
 * 
 * Centralized API endpoint definitions and URL builders.
 * Uses environment variable for base URL with local fallback.
 */

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * API Endpoints
 */
export const ENDPOINTS = {
  // Stories
  ALL_STORIES: '/api/stories',
  STORY: (id) => `/api/stories/${id}`,
  STORY_OPERATION: (storyId, operation) => `/api/stories/${storyId}/operations/${encodeURIComponent(operation)}`,
  
  // Metadata
  PROJECTS: '/api/projects',
  AGENTS: '/api/agents',
  OPERATIONS: '/api/operations',
  MODELS: '/api/models',
  
  // Calls
  CALL: (id) => `/api/calls/${id}`,
  
  // Health
  HEALTH: '/api/health',
};

/**
 * Build full URL with query parameters
 * @param {string} endpoint - Endpoint path
 * @param {object} params - Query parameters
 * @returns {string} Full URL with params
 */
export function buildUrl(endpoint, params = {}) {
  const url = new URL(API_BASE_URL + endpoint);
  
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined) {
      url.searchParams.append(key, String(value));
    }
  });
  
  return url.toString();
}

/**
 * Build query string from params object
 * @param {object} params - Query parameters
 * @returns {string} Query string (without leading ?)
 */
export function buildQueryString(params = {}) {
  const searchParams = new URLSearchParams();
  
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined) {
      searchParams.append(key, String(value));
    }
  });
  
  return searchParams.toString();
}

export default ENDPOINTS;