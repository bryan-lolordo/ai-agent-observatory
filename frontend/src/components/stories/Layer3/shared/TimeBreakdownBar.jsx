/**
 * TimeBreakdownBar - Visual breakdown of time components
 * Used in Latency story to show TTFT vs Generation time
 */

export default function TimeBreakdownBar({ 
  segments = [], // [{ label, value, percentage, color, icon }]
  total,
  unit = 's',
}) {
  return (
    <div className="bg-gray-900 rounded-lg p-4">
      {/* Progress Bar */}
      <div className="flex items-center gap-2 mb-3">
        <div className="flex-1 bg-gray-700 rounded-full h-6 overflow-hidden flex">
          {segments.map((segment, idx) => (
            <div
              key={idx}
              className={`${segment.color} h-full flex items-center justify-center text-xs text-white font-medium transition-all`}
              style={{ width: `${Math.max(segment.percentage, 5)}%` }}
            >
              {segment.percentage > 15 && `${segment.percentage.toFixed(0)}%`}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex justify-between text-sm text-gray-400">
        {segments.map((segment, idx) => (
          <span key={idx}>
            {segment.icon} {segment.label}: {segment.value.toFixed(1)}{unit} ({segment.percentage.toFixed(0)}%)
          </span>
        ))}
      </div>
    </div>
  );
}

/**
 * Convenience component for Latency TTFT/Generation breakdown
 */
export function LatencyBreakdownBar({ ttft_ms, generation_ms, total_ms }) {
  const ttft_pct = (ttft_ms / total_ms) * 100;
  const generation_pct = (generation_ms / total_ms) * 100;

  return (
    <TimeBreakdownBar
      segments={[
        {
          label: 'TTFT',
          value: ttft_ms / 1000,
          percentage: ttft_pct,
          color: 'bg-green-500',
          icon: '🟢',
        },
        {
          label: 'Generation',
          value: generation_ms / 1000,
          percentage: generation_pct,
          color: 'bg-red-500',
          icon: '🔴',
        },
      ]}
      total={total_ms}
      unit="s"
    />
  );
}

/**
 * TimeAttributionTree - Detailed hierarchical time breakdown
 * Shows WHERE the time went in a tree structure
 * 
 * UPDATED: Roboto Mono font + Vibrant Rainbow color scheme
 */
export function TimeAttributionTree({ 
  total_ms, 
  ttft_ms, 
  generation_ms,
  completion_tokens,
  tokens_per_second,
  expected_tokens_per_second = 20,
}) {
  const network_ms = 500; // Rough estimate
  const ttft_pct = (ttft_ms / total_ms) * 100;
  const generation_pct = (generation_ms / total_ms) * 100;
  const network_pct = (network_ms / total_ms) * 100;

  const isProblem = tokens_per_second < expected_tokens_per_second * 0.5;

  return (
    <div className="bg-gray-900 rounded-lg p-5 text-sm" style={{ 
      fontFamily: "'Roboto Mono', 'Ubuntu Mono', monospace",
      letterSpacing: '0.5px'
    }}>
      {/* Total */}
      <div className="mb-2">
        <span className="font-bold text-base" style={{ color: '#f97316' }}>
          {(total_ms / 1000).toFixed(1)}s
        </span>
        <span style={{ color: '#d1d5db' }}> total</span>
      </div>

      {/* Tree branches */}
      <div className="ml-4 space-y-1">
        {/* Network */}
        <div className="flex items-center gap-2">
          <span style={{ color: '#4b5563' }}>├─</span>
          <span style={{ color: '#06b6d4' }}>Network:</span>
          <span className="font-bold" style={{ color: '#22d3ee' }}>
            ~{(network_ms / 1000).toFixed(1)}s
          </span>
          <span style={{ color: '#67e8f9' }}>({network_pct.toFixed(0)}%)</span>
          <span className="text-xs italic" style={{ color: '#22c55e' }}>← negligible</span>
        </div>

        {/* TTFT */}
        <div className="flex items-center gap-2">
          <span style={{ color: '#4b5563' }}>├─</span>
          <span style={{ color: '#8b5cf6' }}>TTFT:</span>
          <span className="font-bold" style={{ color: '#a78bfa' }}>
            {(ttft_ms / 1000).toFixed(1)}s
          </span>
          <span style={{ color: '#c4b5fd' }}>({ttft_pct.toFixed(0)}%)</span>
          <span className="text-xs" style={{ color: '#9ca3af' }}>← Model thinking</span>
        </div>

        {/* Generation (with sub-tree) */}
        <div>
          <div className="flex items-center gap-2">
            <span style={{ color: '#4b5563' }}>└─</span>
            <span style={{ color: '#f59e0b' }}>Generation:</span>
            <span className="font-bold" style={{ color: '#fbbf24' }}>
              {(generation_ms / 1000).toFixed(1)}s
            </span>
            <span style={{ color: '#fde047' }}>({generation_pct.toFixed(0)}%)</span>
            <span className="text-xs" style={{ color: '#9ca3af' }}>← Token output</span>
          </div>

          {/* Generation sub-items */}
          <div className="ml-6 mt-1 space-y-1">
            <div className="flex items-center gap-2">
              <span style={{ color: '#4b5563' }}>├─</span>
              <span className="font-bold" style={{ color: '#ec4899' }}>
                {completion_tokens} tokens
              </span>
              <span style={{ color: '#d1d5db' }}> @ </span>
              <span className="font-bold" style={{ 
                color: '#ef4444',
                fontSize: '15px'
              }}>
                {tokens_per_second.toFixed(1)} tok/sec
              </span>
              {isProblem && (
                <span className="text-xs font-black" style={{ color: '#ef4444' }}>
                  ← PROBLEM
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span style={{ color: '#4b5563' }}>└─</span>
              <span style={{ color: '#9ca3af' }}>Expected:</span>
              <span className="font-bold" style={{ color: '#4ade80' }}>
                ~{expected_tokens_per_second} tok/sec
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Problem callout */}
      {isProblem && (
        <div className="mt-4 p-3 bg-gray-900 border-2 border-red-500 rounded text-xs">
          <div className="text-red-400 font-semibold mb-1">⚠️ Slow Token Generation</div>
          <div className="text-gray-400">
            Generation is {(expected_tokens_per_second / tokens_per_second).toFixed(1)}x slower than expected.
            Likely cause: Large context or conversation history.
          </div>
        </div>
      )}
    </div>
  );
}