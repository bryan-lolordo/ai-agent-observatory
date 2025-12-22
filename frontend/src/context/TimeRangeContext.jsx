/**
 * TimeRangeContext - Global time range filter state
 * 
 * Provides timeRange (in days) to all components.
 * Used by Layer 2 pages to dynamically filter API calls.
 * 
 * Location: src/context/TimeRangeContext.jsx
 * 
 * Usage:
 *   import { useTimeRange } from '../context/TimeRangeContext';
 *   const { timeRange } = useTimeRange();
 *   fetch(`/api/calls?days=${timeRange}`)
 */

import { createContext, useContext } from 'react';

// Default context value
const TimeRangeContext = createContext({
  timeRange: 30,
  setTimeRange: () => {},
});

/**
 * Hook to access time range from any component
 * @returns {{ timeRange: number, setTimeRange: (days: number) => void }}
 */
export const useTimeRange = () => {
  const context = useContext(TimeRangeContext);
  if (!context) {
    console.warn('useTimeRange must be used within TimeRangeContext.Provider');
    return { timeRange: 30, setTimeRange: () => {} };
  }
  return context;
};

export default TimeRangeContext;
