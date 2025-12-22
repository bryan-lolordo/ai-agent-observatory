/**
 * useStories Hook
 * 
 * Custom React hook for fetching stories data from the Observatory API.
 * Automatically uses TimeRangeContext for the days parameter.
 * 
 * Location: src/hooks/useStories.js
 */

import { useState, useEffect, useCallback } from 'react';
import { getAllStories, getStory } from '../services/api';
import { useTimeRange } from '../context/TimeRangeContext';

/**
 * Hook to fetch all stories
 * Automatically uses timeRange from context
 */
export function useStories({ project = null, autoFetch = true } = {}) {
  const { timeRange } = useTimeRange();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchStories = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await getAllStories({ project, days: timeRange });
      setData(result);
    } catch (err) {
      setError(err.message || 'Failed to fetch stories');
      console.error('Error fetching stories:', err);
    } finally {
      setLoading(false);
    }
  }, [project, timeRange]);

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
    timeRange, // Expose for components that need it
  };
}

/**
 * Hook to fetch a single story
 * Automatically uses timeRange from context
 */
export function useStory(storyId, { project = null, autoFetch = true } = {}) {
  const { timeRange } = useTimeRange();
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
      const result = await getStory(storyId, { project, days: timeRange });
      setData(result);
    } catch (err) {
      setError(err.message || `Failed to fetch story: ${storyId}`);
      console.error(`Error fetching story ${storyId}:`, err);
    } finally {
      setLoading(false);
    }
  }, [storyId, project, timeRange]);

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
    timeRange,
  };
}

/**
 * Hook with polling support
 * Automatically uses timeRange from context
 */
export function useStoriesWithPolling(
  storyId = null,
  { project = null, interval = 30, enabled = false } = {}
) {
  const { timeRange } = useTimeRange();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isPolling, setIsPolling] = useState(enabled);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const result = storyId
        ? await getStory(storyId, { project, days: timeRange })
        : await getAllStories({ project, days: timeRange });
        
      setData(result);
    } catch (err) {
      setError(err.message || 'Failed to fetch data');
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  }, [storyId, project, timeRange]);

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
    timeRange,
  };
}

export default useStories;