/**
 * DiagnosePanel - Universal diagnosis view for Layer 3
 *
 * UPDATED:
 * - Removed PRIMARY ISSUE section (redundant with Root Causes)
 * - Reordered: Root Causes → Time Attribution → Comparison Benchmarks
 * - Uses BenchmarksDisplay component for dynamic metric display
 * - Uses theme system - no hardcoded colors!
 */

import { SeverityBadge } from './shared';
import { TimeAttributionTree } from './shared/TimeBreakdownBar';
import RootCausesTable from './shared/RootCausesTable';
import ChatHistoryBreakdown from './shared/ChatHistoryBreakdown';
import BenchmarksDisplay from './shared/BenchmarksDisplay';
import { BASE_THEME } from '../../../utils/themeUtils';
import { STORY_THEMES } from '../../../config/theme';

export default function DiagnosePanel({
  // Primary diagnosis data
  factors = [],
  primaryFactor = null,
  
  // Health state
  isHealthy = false,
  healthyMessage = 'Performing within normal parameters.',
  
  // Time attribution (for latency)
  timeAttribution = null,
  
  // Breakdown components (DEPRECATED)
  breakdownComponent = null,
  breakdownTitle = 'Breakdown',
  breakdownSubtext = null,
  
  // Additional breakdown (e.g., prompt composition)
  additionalBreakdown = null,
  additionalBreakdownTitle = null,
  
  // Chat history breakdown (for multi-turn conversations)
  chatHistoryBreakdown = null,
  
  // Comparison benchmarks (NEW: supports dynamic metrics)
  comparisonBenchmarks = null,
  benchmarkConfig = null, // Config for BenchmarksDisplay
  
  // Actions
  onViewFix,
  
  // Theme
  theme = STORY_THEMES.latency,
}) {
  const primary = primaryFactor || factors[0];
  // Use passed theme or default to latency theme for accent colors
  const accentTheme = theme || STORY_THEMES.latency;

  // Default benchmark config for Latency story
  const defaultBenchmarkConfig = {
    metricKey: 'latency_s',
    formatValue: (v) => `${v.toFixed(1)}s`,
    comparisonLabel: 'faster',
    higherIsBetter: false,
    thresholdForCallout: 2,
  };

  return (
    <div className="space-y-10">
      
      {/* HEALTHY STATE (if no issues) */}
      {isHealthy && (
        <div className={`${BASE_THEME.container.primary} border ${BASE_THEME.border.default} rounded-lg p-6`}>
          <h3 className={`text-sm font-bold ${accentTheme.text} uppercase tracking-wide mb-4 flex items-center gap-2`}>
            <span className="text-lg">✅</span> HEALTH STATUS
          </h3>
          <div className={`${BASE_THEME.status.success.bg} border-l-4 ${BASE_THEME.status.success.border} rounded-lg p-5`}>
            <h4 className={`text-xl font-semibold ${BASE_THEME.status.success.text} mb-2`}>
              No Issues Detected
            </h4>
            <p className={`text-base ${BASE_THEME.text.secondary}`}>{healthyMessage}</p>
          </div>
        </div>
      )}

      {/* 1. ROOT CAUSES TABLE (FIRST - Most Important) */}
      {!isHealthy && factors.length > 0 && (
        <div className={`${BASE_THEME.container.primary} border ${BASE_THEME.border.default} rounded-lg p-6`}>
          <h3 className={`text-sm font-bold ${accentTheme.text} uppercase tracking-wide mb-4 flex items-center gap-2`}>
            <span className="text-lg">🔍</span> ROOT CAUSES ({factors.length})
          </h3>
          <RootCausesTable causes={factors} onViewFix={onViewFix} theme={accentTheme} />
        </div>
      )}

      {/* 2. TIME ATTRIBUTION TREE (for latency) */}
      {timeAttribution && (
        <div className={`${BASE_THEME.container.primary} border ${BASE_THEME.border.default} rounded-lg p-6`}>
          <h3 className={`text-sm font-bold ${accentTheme.text} uppercase tracking-wide mb-6 flex items-center gap-2`}>
            <span className="text-lg">⏱️</span> TIME ATTRIBUTION
          </h3>
          <TimeAttributionTree {...timeAttribution} theme={accentTheme} />
        </div>
      )}

      {/* Legacy Breakdown (if provided) */}
      {breakdownComponent && !timeAttribution && (
        <div className={`${BASE_THEME.container.primary} border ${BASE_THEME.border.default} rounded-lg p-6`}>
          <h3 className={`text-xs font-bold ${accentTheme.text} uppercase tracking-wide mb-4`}>
            {breakdownTitle}
          </h3>
          {breakdownComponent}
          {breakdownSubtext && (
            <div className={`mt-4 text-sm ${BASE_THEME.text.muted}`}>{breakdownSubtext}</div>
          )}
        </div>
      )}

      {/* Chat History Breakdown (for multi-turn conversations) */}
      {chatHistoryBreakdown && chatHistoryBreakdown.messages && chatHistoryBreakdown.messages.length > 0 && (
        <div className={`${BASE_THEME.container.primary} border ${BASE_THEME.border.default} rounded-lg p-6`}>
          <h3 className={`text-sm font-bold ${accentTheme.text} uppercase tracking-wide mb-4 flex items-center gap-2`}>
            <span className="text-lg">💬</span> CHAT HISTORY BREAKDOWN
          </h3>
          <p className={`text-base ${BASE_THEME.text.secondary} mb-4`}>
            Visualization of how conversation history accumulates across turns, highlighting optimization opportunities.
          </p>
          <ChatHistoryBreakdown {...chatHistoryBreakdown} />
        </div>
      )}

      {/* Additional Breakdown (e.g., Prompt composition) */}
      {additionalBreakdown && (
        <div className={`${BASE_THEME.container.primary} border ${BASE_THEME.border.default} rounded-lg p-6`}>
          {additionalBreakdownTitle && (
            <h3 className={`text-xs font-bold ${accentTheme.text} uppercase tracking-wide mb-4`}>
              {additionalBreakdownTitle}
            </h3>
          )}
          {additionalBreakdown}
        </div>
      )}

      {/* 3. COMPARISON BENCHMARKS - DYNAMIC (LAST) */}
      {comparisonBenchmarks && comparisonBenchmarks.available && (
        <div className={`${BASE_THEME.container.primary} border ${BASE_THEME.border.default} rounded-lg p-6`}>
          <BenchmarksDisplay
            benchmarks={comparisonBenchmarks}
            config={benchmarkConfig || defaultBenchmarkConfig}
            theme={accentTheme}
          />
        </div>
      )}
    </div>
  );
}