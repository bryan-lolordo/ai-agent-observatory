/**
 * useCalls Hook
 * 
 * Custom React hook for fetching LLM calls from the Observatory API.
 * Automatically uses TimeRangeContext for the days parameter.
 * Used by Layer 2 pages (OperationDetail components).
 * 
 * Location: src/hooks/useCalls.js
 * 
 * Usage:
 *   const { data, loading, error, refetch } = useCalls();
 *   const { data, loading, error } = useCalls({ endpoint: '/api/stories/cache/patterns' });
 */

import { useState, useEffect, useCallback } from 'react';
import { useTimeRange } from '../context/TimeRangeContext';

/**
 * Hook to fetch calls or patterns with automatic timeRange
 * 
 * @param {Object} options
 * @param {string} options.endpoint - API endpoint (default: '/api/calls')
 * @param {boolean} options.autoFetch - Fetch on mount (default: true)
 * @param {string} options.dataKey - Key to extract from response (default: auto-detect)
 */
export function useCalls({ 
  endpoint = '/api/calls',
  autoFetch = true,
  dataKey = null,
} = {}) {
  const { timeRange } = useTimeRange();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [rawResponse, setRawResponse] = useState(null);

  const fetchCalls = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Build URL with timeRange
      const separator = endpoint.includes('?') ? '&' : '?';
      const url = `${endpoint}${separator}days=${timeRange}`;
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      setRawResponse(result);
      
      // Auto-detect data key if not provided
      if (dataKey) {
        setData(result[dataKey] || []);
      } else if (result.calls) {
        setData(result.calls);
      } else if (result.patterns) {
        setData(result.patterns);
      } else if (result.operations) {
        setData(result.operations);
      } else if (Array.isArray(result)) {
        setData(result);
      } else {
        setData([]);
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch data');
      console.error('Error fetching calls:', err);
    } finally {
      setLoading(false);
    }
  }, [endpoint, timeRange, dataKey]);

  useEffect(() => {
    if (autoFetch) {
      fetchCalls();
    }
  }, [autoFetch, fetchCalls]);

  return {
    data,
    loading,
    error,
    refetch: fetchCalls,
    rawResponse,  // Full API response for stats, etc.
    timeRange,    // Expose for components that need it
  };
}

/**
 * Hook to fetch cache patterns
 * Convenience wrapper for cache story
 */
export function useCachePatterns(options = {}) {
  return useCalls({
    endpoint: '/api/stories/cache/patterns',
    dataKey: 'patterns',
    ...options,
  });
}

/**
 * Hook to fetch routing patterns  
 * Convenience wrapper for routing story
 */
export function useRoutingPatterns(options = {}) {
  return useCalls({
    endpoint: '/api/stories/routing/patterns',
    dataKey: 'patterns',
    ...options,
  });
}

/**
 * Hook to fetch a single call detail (Layer 3)
 * Note: Does NOT use timeRange since it's a specific call
 */
export function useCallDetail(callId, { autoFetch = true } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchCall = useCallback(async () => {
    if (!callId) {
      setError('Call ID is required');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`/api/calls/${callId}`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err.message || 'Failed to fetch call');
      console.error('Error fetching call:', err);
    } finally {
      setLoading(false);
    }
  }, [callId]);

  useEffect(() => {
    if (autoFetch && callId) {
      fetchCall();
    }
  }, [autoFetch, callId, fetchCall]);

  return {
    data,
    loading,
    error,
    refetch: fetchCall,
  };
}

export default useCalls;