/**
 * Observatory API Service
 * 
 * Handles all API calls to the FastAPI backend.
 * Base URL configured for local development with Vite proxy.
 */

const API_BASE_URL = '/api';

/**
 * Generic fetch wrapper with error handling
 * @param {string} endpoint - API endpoint (e.g., '/stories')
 * @param {object} options - Fetch options
 * @returns {Promise<object>} JSON response
 */
async function fetchAPI(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `API Error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error);
    throw error;
  }
}

// =============================================================================
// STORIES API
// =============================================================================

/**
 * Get all stories summary
 * @param {object} params - Query parameters
 * @param {string} params.project - Filter by project
 * @param {number} params.days - Number of days (default: 7)
 * @returns {Promise<object>} All stories response
 */
export async function getAllStories({ project = null, days = 7 } = {}) {
  const params = new URLSearchParams();
  if (project) params.append('project', project);
  params.append('days', days);
  
  return fetchAPI(`/stories?${params}`);
}

/**
 * Get individual story by ID
 * @param {string} storyId - Story ID (latency, cache, cost, etc.)
 * @param {object} params - Query parameters
 * @returns {Promise<object>} Story response
 */
export async function getStory(storyId, { project = null, days = 7 } = {}) {
  const params = new URLSearchParams();
  if (project) params.append('project', project);
  params.append('days', days);
  
  return fetchAPI(`/stories/${storyId}?${params}`);
}

// =============================================================================
// METADATA API
// =============================================================================

/**
 * Get all projects
 * @returns {Promise<object>} Projects list
 */
export async function getProjects() {
  return fetchAPI('/projects');
}

/**
 * Get all agents
 * @param {string} project - Filter by project
 * @returns {Promise<object>} Agents list
 */
export async function getAgents(project = null) {
  const params = project ? `?project=${project}` : '';
  return fetchAPI(`/agents${params}`);
}

/**
 * Get all operations
 * @param {string} project - Filter by project
 * @param {string} agent - Filter by agent
 * @returns {Promise<object>} Operations list
 */
export async function getOperations({ project = null, agent = null } = {}) {
  const params = new URLSearchParams();
  if (project) params.append('project', project);
  if (agent) params.append('agent', agent);
  
  return fetchAPI(`/operations?${params}`);
}

/**
 * Get all models
 * @returns {Promise<object>} Models list
 */
export async function getModels() {
  return fetchAPI('/models');
}

// =============================================================================
// LAYER 2 & 3 ENDPOINTS
// =============================================================================

/**
 * Get operation detail (Layer 2)
 * @param {string} storyId - Story ID
 * @param {string} operation - Operation name
 * @param {object} params - Query parameters
 * @returns {Promise<object>} Operation detail
 */
export async function getOperationDetail(storyId, operation, params = {}) {
  const queryParams = new URLSearchParams(params);
  return fetchAPI(`/stories/${storyId}/operations/${encodeURIComponent(operation)}?${queryParams}`);
}

/**
 * Get call detail (Layer 3)
 * @param {string} callId - Call ID
 * @returns {Promise<object>} Call detail
 */
export async function getCallDetail(callId) {
  return fetchAPI(`/calls/${callId}`);
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Health check
 * @returns {Promise<object>} Health status
 */
export async function healthCheck() {
  return fetchAPI('/health');
}

export default {
  getAllStories,
  getStory,
  getProjects,
  getAgents,
  getOperations,
  getModels,
  getOperationDetail,
  getCallDetail,
  healthCheck,
};