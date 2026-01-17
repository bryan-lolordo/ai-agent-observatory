/**
 * PhaseContext - Global phase filter state for A/B comparison
 *
 * Provides phase (null | 'baseline' | 'optimized') to all components.
 * Used to filter API calls by data phase.
 *
 * Location: src/context/PhaseContext.jsx
 *
 * Usage:
 *   import { usePhase } from '../context/PhaseContext';
 *   const { phase } = usePhase();
 *   fetch(`/api/stories/latency?phase=${phase || ''}`)
 */

import { createContext, useContext } from 'react';

// Default context value - null means "All Data"
const PhaseContext = createContext({
  phase: null,
  setPhase: () => {},
});

/**
 * Hook to access phase from any component
 * @returns {{ phase: string|null, setPhase: (phase: string|null) => void }}
 */
export const usePhase = () => {
  const context = useContext(PhaseContext);
  if (!context) {
    console.warn('usePhase must be used within PhaseContext.Provider');
    return { phase: null, setPhase: () => {} };
  }
  return context;
};

export default PhaseContext;
