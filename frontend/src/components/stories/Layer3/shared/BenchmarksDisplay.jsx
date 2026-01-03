/**
 * BenchmarksDisplay - Generic comparison benchmarks component
 * Location: src/components/stories/Layer3/shared/BenchmarksDisplay.jsx
 *
 * Reusable across all stories (Latency, Quality, Cost, Token, etc.)
 * Shows how current call compares to best/similar/median for the same operation.
 *
 * UPDATED: Uses theme system - no hardcoded colors!
 *
 * Usage:
 * <BenchmarksDisplay
 *   benchmarks={data}
 *   theme={theme}
 *   config={{
 *     metricKey: 'latency_s',
 *     formatValue: (v) => `${v.toFixed(1)}s`,
 *     comparisonLabel: 'faster',
 *     higherIsBetter: false,
 *     thresholdForCallout: 2,
 *   }}
 * />
 */

import { BASE_THEME } from '../../../../utils/themeUtils';
import { STORY_THEMES, COLORS } from '../../../../config/theme';

// Benchmark bar colors using theme values (static colors for non-current benchmarks)
const STATIC_BENCHMARK_COLORS = {
  fastest: {
    gradient: `linear-gradient(90deg, ${COLORS.success} 0%, #059669 100%)`,
    text: 'text-green-400',
  },
  similar: {
    gradient: `linear-gradient(90deg, ${STORY_THEMES.system_prompt.color} 0%, #0891b2 100%)`,
    text: STORY_THEMES.system_prompt.text,
  },
  median: {
    gradient: `linear-gradient(90deg, ${STORY_THEMES.routing.color} 0%, #7c3aed 100%)`,
    text: STORY_THEMES.routing.text,
  },
};

export default function BenchmarksDisplay({ benchmarks, config, theme }) {
  // Use passed theme or default to latency theme for accent colors
  const accentTheme = theme || STORY_THEMES.latency;

  // Dynamic "current" benchmark color based on story theme
  const BENCHMARK_COLORS = {
    current: {
      gradient: `linear-gradient(90deg, ${accentTheme.color} 0%, ${accentTheme.color}cc 100%)`,
      text: accentTheme.text,
      borderLight: accentTheme.borderLight,
    },
    ...STATIC_BENCHMARK_COLORS,
  };

  if (!benchmarks || !benchmarks.available) {
    return (
      <div className={`${BASE_THEME.container.primary} rounded-lg p-5 border ${BASE_THEME.border.default} text-center ${BASE_THEME.text.muted}`}>
        Not enough data for comparison (need at least 2 calls for same operation)
      </div>
    );
  }

  const {
    metricKey = 'latency_s',
    formatValue = (v) => `${v.toFixed(1)}s`,
    comparisonLabel = 'faster',
    higherIsBetter = false,
    thresholdForCallout = 2,
  } = config;

  const { current, fastest_same_operation, fastest_similar_context, median_for_operation } = benchmarks;

  // Calculate bar widths based on metric
  const calculateWidth = (value, baseline) => {
    if (!value || !baseline) return 0;
    if (higherIsBetter) {
      return Math.min((value / baseline) * 100, 100);
    } else {
      return Math.min((value / baseline) * 100, 100);
    }
  };

  // Format comparison text (e.g., "2.5x faster" or "3.0x better")
  const formatComparison = (ratio, comparison) => {
    const label = comparison === 'slower' || comparison === 'worse'
      ? (higherIsBetter ? 'worse' : 'slower')
      : comparisonLabel;
    return `${Math.abs(ratio).toFixed(1)}x ${label}`;
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className={`text-sm font-bold ${accentTheme.text} uppercase tracking-wide mb-2 flex items-center gap-2`}>
          <span className="text-lg">📊</span> COMPARISON BENCHMARKS
        </h3>
        <p className={`${BASE_THEME.text.secondary} text-base mb-6`}>
          All performance benchmarks at a glance - see where you stand
        </p>

        <div className="space-y-3">
          {/* This Call (baseline - highlighted) */}
          <div className={`flex items-center gap-3 p-3 ${BASE_THEME.container.secondary}/50 border ${accentTheme.borderLight} rounded-lg`}>
            <div className={`font-semibold ${accentTheme.text} w-40 text-base`}>This Call</div>
            <div className={`flex-1 ${BASE_THEME.container.secondary} rounded-full h-6 overflow-hidden border ${BASE_THEME.border.default}`}>
              <div
                className="h-full flex items-center justify-end pr-2"
                style={{
                  width: '100%',
                  background: BENCHMARK_COLORS.current.gradient
                }}
              >
                <span className="text-sm text-white font-medium">100%</span>
              </div>
            </div>
            <span className={`font-bold font-mono ${accentTheme.text} w-16 text-right text-base`}>
              {formatValue(current[metricKey] || 0)}
            </span>
            <span className={`text-base ${BASE_THEME.text.muted} w-24 text-right`}>baseline</span>
          </div>

          {/* Fastest Same Operation */}
          {fastest_same_operation && (
            <div className={`flex items-center gap-3 p-3 ${BASE_THEME.state.hover} rounded-lg transition-colors`}>
              <div className={`font-medium ${BASE_THEME.text.secondary} w-40 text-base`}>
                {higherIsBetter ? 'Highest Same Op' : 'Fastest Same Op'}
              </div>
              <div className={`flex-1 ${BASE_THEME.container.secondary} rounded-full h-6 overflow-hidden border ${BASE_THEME.border.default}`}>
                <div
                  className="h-full"
                  style={{
                    width: `${calculateWidth(
                      fastest_same_operation[metricKey] || 0,
                      current[metricKey] || 1
                    )}%`,
                    background: BENCHMARK_COLORS.fastest.gradient
                  }}
                />
              </div>
              <span className={`font-bold font-mono ${BENCHMARK_COLORS.fastest.text} w-16 text-right text-base`}>
                {formatValue(fastest_same_operation[metricKey] || 0)}
              </span>
              <span className={`text-base ${BENCHMARK_COLORS.fastest.text} font-medium w-24 text-right`}>
                {formatComparison(fastest_same_operation.faster_by || fastest_same_operation.better_by || 0)}
              </span>
            </div>
          )}

          {/* Fastest Similar Context */}
          {fastest_similar_context && (
            <div className={`flex items-center gap-3 p-3 ${BASE_THEME.state.hover} rounded-lg transition-colors`}>
              <div className={`font-medium ${BASE_THEME.text.secondary} w-40 text-base`}>
                {higherIsBetter ? 'Highest Similar' : 'Fastest Similar'}
              </div>
              <div className={`flex-1 ${BASE_THEME.container.secondary} rounded-full h-6 overflow-hidden border ${BASE_THEME.border.default}`}>
                <div
                  className="h-full"
                  style={{
                    width: `${calculateWidth(
                      fastest_similar_context[metricKey] || 0,
                      current[metricKey] || 1
                    )}%`,
                    background: BENCHMARK_COLORS.similar.gradient
                  }}
                />
              </div>
              <span className={`font-bold font-mono ${BENCHMARK_COLORS.similar.text} w-16 text-right text-base`}>
                {formatValue(fastest_similar_context[metricKey] || 0)}
              </span>
              <span className={`text-base ${BENCHMARK_COLORS.similar.text} font-medium w-24 text-right`}>
                {formatComparison(fastest_similar_context.faster_by || fastest_similar_context.better_by || 0)}
              </span>
            </div>
          )}

          {/* Median for Operation */}
          {median_for_operation && (
            <div className={`flex items-center gap-3 p-3 ${BASE_THEME.state.hover} rounded-lg transition-colors`}>
              <div className={`font-medium ${BASE_THEME.text.secondary} w-40 text-base`}>Median</div>
              <div className={`flex-1 ${BASE_THEME.container.secondary} rounded-full h-6 overflow-hidden border ${BASE_THEME.border.default}`}>
                <div
                  className="h-full"
                  style={{
                    width: `${calculateWidth(
                      median_for_operation[metricKey] || median_for_operation.score || 0,
                      current[metricKey] || 1
                    )}%`,
                    background: BENCHMARK_COLORS.median.gradient
                  }}
                />
              </div>
              <span className={`font-bold font-mono ${BENCHMARK_COLORS.median.text} w-16 text-right text-base`}>
                {formatValue(median_for_operation[metricKey] || median_for_operation.score || 0)}
              </span>
              <span className={`text-base font-medium w-24 text-right ${
                median_for_operation.comparison === 'slower' || median_for_operation.comparison === 'worse'
                  ? BASE_THEME.status.error.text
                  : BENCHMARK_COLORS.fastest.text
              }`}>
                {formatComparison(
                  median_for_operation.faster_by || median_for_operation.ratio || 0,
                  median_for_operation.comparison
                )}
              </span>
            </div>
          )}
        </div>

        {/* Color Legend */}
        <div className={`flex gap-5 mt-6 pt-4 border-t ${BASE_THEME.border.default} flex-wrap text-base`}>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: BENCHMARK_COLORS.current.gradient }}></div>
            <span className={BASE_THEME.text.secondary}>This Call</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: BENCHMARK_COLORS.fastest.gradient }}></div>
            <span className={BASE_THEME.text.secondary}>{higherIsBetter ? 'Highest' : 'Fastest'}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: BENCHMARK_COLORS.similar.gradient }}></div>
            <span className={BASE_THEME.text.secondary}>Similar</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: BENCHMARK_COLORS.median.gradient }}></div>
            <span className={BASE_THEME.text.secondary}>Median</span>
          </div>
        </div>

        {/* Optimization Potential Callout */}
        {fastest_same_operation &&
         (fastest_same_operation.faster_by || fastest_same_operation.better_by || 0) > thresholdForCallout && (
          <div className={`mt-6 ${BASE_THEME.container.primary} border-2 ${accentTheme.border} rounded-lg p-5`}>
            <div className="flex items-center gap-3">
              <span className="text-3xl">💡</span>
              <div>
                <div className={`${accentTheme.text} font-bold text-xl mb-1`}>
                  {higherIsBetter ? 'Quality Gap Detected' : 'Optimization Potential'}
                </div>
                <div className={`${BASE_THEME.text.secondary} text-base leading-relaxed`}>
                  The {higherIsBetter ? 'highest' : 'fastest'} call for this operation {higherIsBetter ? 'scored' : 'completed in'}{' '}
                  <span className={`font-bold ${BENCHMARK_COLORS.fastest.text}`}>
                    {formatValue(fastest_same_operation[metricKey] || 0)}
                  </span>
                  {' '}— that's{' '}
                  <span className={`font-bold ${accentTheme.text}`}>
                    {formatComparison(fastest_same_operation.faster_by || fastest_same_operation.better_by || 0)}
                  </span>
                  {' '}than this call.
                  {fastest_similar_context && (
                    <> With similar context, the {higherIsBetter ? 'highest' : 'fastest'} call {higherIsBetter ? 'scored' : 'took'}{' '}
                      <span className={`font-bold ${BENCHMARK_COLORS.fastest.text}`}>
                        {formatValue(fastest_similar_context[metricKey] || 0)}
                      </span>.
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
