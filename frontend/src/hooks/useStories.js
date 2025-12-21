/**
 * useStories Hook
 * 
 * Custom React hook for fetching stories data from the Observatory API.
 * Manages loading, error, and data states with automatic refetching.
 */

import { useState, useEffect, useCallback } from 'react';
import { getAllStories, getStory } from '../services/api';

/**
 * Hook to fetch all stories
 */
export function useStories({ project = null, days = 30, autoFetch = true } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchStories = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await getAllStories({ project, days });
      setData(result);
    } catch (err) {
      setError(err.message || 'Failed to fetch stories');
      console.error('Error fetching stories:', err);
    } finally {
      setLoading(false);
    }
  }, [project, days]);

  useEffect(() => {
    if (autoFetch) {
      fetchStories();
    }
  }, [autoFetch, fetchStories]);

  return {
    data,
    loading,
    error,
    refetch: fetchStories,
  };
}

/**
 * Hook to fetch a single story
 */
export function useStory(storyId, { project = null, days = 30, autoFetch = true } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchStory = useCallback(async () => {
    if (!storyId) {
      setError('Story ID is required');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const result = await getStory(storyId, { project, days });
      setData(result);
    } catch (err) {
      setError(err.message || `Failed to fetch story: ${storyId}`);
      console.error(`Error fetching story ${storyId}:`, err);
    } finally {
      setLoading(false);
    }
  }, [storyId, project, days]);

  useEffect(() => {
    if (autoFetch && storyId) {
      fetchStory();
    }
  }, [autoFetch, storyId, fetchStory]);

  return {
    data,
    loading,
    error,
    refetch: fetchStory,
  };
}

/**
 * Hook with polling support
 */
export function useStoriesWithPolling(
  storyId = null,
  { project = null, days = 30, interval = 30, enabled = false } = {}
) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isPolling, setIsPolling] = useState(enabled);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const result = storyId
        ? await getStory(storyId, { project, days })
        : await getAllStories({ project, days });
        
      setData(result);
    } catch (err) {
      setError(err.message || 'Failed to fetch data');
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  }, [storyId, project, days]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!isPolling) return;
    const intervalId = setInterval(fetchData, interval * 1000);
    return () => clearInterval(intervalId);
  }, [isPolling, interval, fetchData]);

  const startPolling = useCallback(() => setIsPolling(true), []);
  const stopPolling = useCallback(() => setIsPolling(false), []);

  return {
    data,
    loading,
    error,
    refetch: fetchData,
    isPolling,
    startPolling,
    stopPolling,
  };
}

export default useStories;