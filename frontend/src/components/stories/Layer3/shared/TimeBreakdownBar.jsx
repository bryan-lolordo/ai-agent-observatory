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
    <div className="bg-slate-900 rounded-lg p-4">
      {/* Progress Bar */}
      <div className="flex items-center gap-2 mb-3">
        <div className="flex-1 bg-slate-700 rounded-full h-6 overflow-hidden flex">
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
      <div className="flex justify-between text-sm text-slate-400">
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