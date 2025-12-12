/**
 * Observatory API Service
 * Location: frontend/src/api.js
 */

const API_BASE = '/api';

export async function fetchStories(project = null, days = 7) {
  const params = new URLSearchParams();
  if (project) params.append('project', project);
  params.append('days', days);
  
  const response = await fetch(`${API_BASE}/stories?${params}`);
  if (!response.ok) throw new Error('Failed to fetch stories');
  return response.json();
}

export async function fetchStoryDetail(storyId, project = null, days = 7) {
  const params = new URLSearchParams();
  if (project) params.append('project', project);
  params.append('days', days);
  
  const response = await fetch(`${API_BASE}/stories/${storyId}?${params}`);
  if (!response.ok) throw new Error('Failed to fetch story detail');
  return response.json();
}

export async function fetchProjects() {
  const response = await fetch(`${API_BASE}/projects`);
  if (!response.ok) throw new Error('Failed to fetch projects');
  return response.json();
}

export async function fetchCalls(filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.append(key, value);
  });
  
  const response = await fetch(`${API_BASE}/calls?${params}`);
  if (!response.ok) throw new Error('Failed to fetch calls');
  return response.json();
}

export async function fetchCodeLocation(agent, operation) {
  const params = new URLSearchParams({ agent, operation });
  const response = await fetch(`${API_BASE}/code-location?${params}`);
  if (!response.ok) throw new Error('Failed to fetch code location');
  return response.json();
}

export async function healthCheck() {
  const response = await fetch(`${API_BASE}/health`);
  return response.ok;
}