/**
 * BenchmarksDisplay - Generic comparison benchmarks component
 * Location: src/components/stories/Layer3/shared/BenchmarksDisplay.jsx
 * 
 * Reusable across all stories (Latency, Quality, Cost, Token, etc.)
 * Shows how current call compares to best/similar/median for the same operation.
 * 
 * Usage:
 * <BenchmarksDisplay 
 *   benchmarks={data}
 *   config={{
 *     metricKey: 'latency_s',           // or 'score', 'cost', etc.
 *     formatValue: (v) => `${v.toFixed(1)}s`,
 *     comparisonLabel: 'faster',        // or 'better', 'cheaper', etc.
 *     higherIsBetter: false,            // true for quality scores
 *     thresholdForCallout: 2,           // Show callout if ratio > this
 *   }}
 * />
 */

export default function BenchmarksDisplay({ benchmarks, config }) {
  if (!benchmarks || !benchmarks.available) {
    return (
      <div className="bg-gray-900 rounded-lg p-5 border border-gray-700 text-center text-gray-500">
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
      // For quality: higher score = wider bar
      return Math.min((value / baseline) * 100, 100);
    } else {
      // For latency/cost: lower value = narrower bar
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
        <h3 className="text-sm font-bold text-orange-400 uppercase tracking-wide mb-2 flex items-center gap-2">
          <span className="text-lg">📊</span> COMPARISON BENCHMARKS
        </h3>
        <p className="text-gray-400 text-base mb-6">
          All performance benchmarks at a glance - see where you stand
        </p>
        
        <div className="space-y-3">
          {/* This Call (baseline - highlighted) */}
          <div className="flex items-center gap-3 p-3 bg-gray-800/50 border border-orange-500/30 rounded-lg">
            <div className="font-semibold text-orange-400 w-40 text-base">This Call</div>
            <div className="flex-1 bg-gray-800 rounded-full h-6 overflow-hidden border border-gray-700">
              <div 
                className="h-full flex items-center justify-end pr-2"
                style={{ 
                  width: '100%',
                  background: 'linear-gradient(90deg, #f97316 0%, #ea580c 100%)'
                }}
              >
                <span className="text-sm text-white font-medium">100%</span>
              </div>
            </div>
            <span className="font-bold font-mono text-orange-400 w-16 text-right text-base">
              {formatValue(current[metricKey] || 0)}
            </span>
            <span className="text-base text-gray-500 w-24 text-right">baseline</span>
          </div>

          {/* Fastest Same Operation */}
          {fastest_same_operation && (
            <div className="flex items-center gap-3 p-3 hover:bg-gray-800/30 rounded-lg transition-colors">
              <div className="font-medium text-gray-300 w-40 text-base">
                {higherIsBetter ? 'Highest Same Op' : 'Fastest Same Op'}
              </div>
              <div className="flex-1 bg-gray-800 rounded-full h-6 overflow-hidden border border-gray-700">
                <div 
                  className="h-full"
                  style={{ 
                    width: `${calculateWidth(
                      fastest_same_operation[metricKey] || 0,
                      current[metricKey] || 1
                    )}%`,
                    background: 'linear-gradient(90deg, #10b981 0%, #059669 100%)'
                  }}
                />
              </div>
              <span className="font-bold font-mono text-green-400 w-16 text-right text-base">
                {formatValue(fastest_same_operation[metricKey] || 0)}
              </span>
              <span className="text-base text-green-400 font-medium w-24 text-right">
                {formatComparison(fastest_same_operation.faster_by || fastest_same_operation.better_by || 0)}
              </span>
            </div>
          )}

          {/* Fastest Similar Context */}
          {fastest_similar_context && (
            <div className="flex items-center gap-3 p-3 hover:bg-gray-800/30 rounded-lg transition-colors">
              <div className="font-medium text-gray-300 w-40 text-base">
                {higherIsBetter ? 'Highest Similar' : 'Fastest Similar'}
              </div>
              <div className="flex-1 bg-gray-800 rounded-full h-6 overflow-hidden border border-gray-700">
                <div 
                  className="h-full"
                  style={{ 
                    width: `${calculateWidth(
                      fastest_similar_context[metricKey] || 0,
                      current[metricKey] || 1
                    )}%`,
                    background: 'linear-gradient(90deg, #06b6d4 0%, #0891b2 100%)'
                  }}
                />
              </div>
              <span className="font-bold font-mono text-cyan-400 w-16 text-right text-base">
                {formatValue(fastest_similar_context[metricKey] || 0)}
              </span>
              <span className="text-base text-cyan-400 font-medium w-24 text-right">
                {formatComparison(fastest_similar_context.faster_by || fastest_similar_context.better_by || 0)}
              </span>
            </div>
          )}

          {/* Median for Operation */}
          {median_for_operation && (
            <div className="flex items-center gap-3 p-3 hover:bg-gray-800/30 rounded-lg transition-colors">
              <div className="font-medium text-gray-300 w-40 text-base">Median</div>
              <div className="flex-1 bg-gray-800 rounded-full h-6 overflow-hidden border border-gray-700">
                <div 
                  className="h-full"
                  style={{ 
                    width: `${calculateWidth(
                      median_for_operation[metricKey] || median_for_operation.score || 0,
                      current[metricKey] || 1
                    )}%`,
                    background: 'linear-gradient(90deg, #8b5cf6 0%, #7c3aed 100%)'
                  }}
                />
              </div>
              <span className="font-bold font-mono text-purple-400 w-16 text-right text-base">
                {formatValue(median_for_operation[metricKey] || median_for_operation.score || 0)}
              </span>
              <span className={`text-base font-medium w-24 text-right ${
                median_for_operation.comparison === 'slower' || median_for_operation.comparison === 'worse'
                  ? 'text-red-400' 
                  : 'text-green-400'
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
        <div className="flex gap-5 mt-6 pt-4 border-t border-gray-700 flex-wrap text-base">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: 'linear-gradient(90deg, #f97316 0%, #ea580c 100%)' }}></div>
            <span className="text-gray-400">This Call</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: 'linear-gradient(90deg, #10b981 0%, #059669 100%)' }}></div>
            <span className="text-gray-400">{higherIsBetter ? 'Highest' : 'Fastest'}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: 'linear-gradient(90deg, #06b6d4 0%, #0891b2 100%)' }}></div>
            <span className="text-gray-400">Similar</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ background: 'linear-gradient(90deg, #8b5cf6 0%, #7c3aed 100%)' }}></div>
            <span className="text-gray-400">Median</span>
          </div>
        </div>

        {/* Optimization Potential Callout */}
        {fastest_same_operation && 
         (fastest_same_operation.faster_by || fastest_same_operation.better_by || 0) > thresholdForCallout && (
          <div className="mt-6 bg-gray-900 border-2 border-orange-500 rounded-lg p-5">
            <div className="flex items-center gap-3">
              <span className="text-3xl">💡</span>
              <div>
                <div className="text-orange-400 font-bold text-xl mb-1">
                  {higherIsBetter ? 'Quality Gap Detected' : 'Optimization Potential'}
                </div>
                <div className="text-gray-300 text-base leading-relaxed">
                  The {higherIsBetter ? 'highest' : 'fastest'} call for this operation {higherIsBetter ? 'scored' : 'completed in'}{' '}
                  <span className="font-bold text-green-400">
                    {formatValue(fastest_same_operation[metricKey] || 0)}
                  </span>
                  {' '}— that's{' '}
                  <span className="font-bold text-orange-400">
                    {formatComparison(fastest_same_operation.faster_by || fastest_same_operation.better_by || 0)}
                  </span>
                  {' '}than this call.
                  {fastest_similar_context && (
                    <> With similar context, the {higherIsBetter ? 'highest' : 'fastest'} call {higherIsBetter ? 'scored' : 'took'}{' '}
                      <span className="font-bold text-green-400">
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