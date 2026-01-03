/**
 * PromptBreakdownBar - Visual breakdown of prompt token composition
 */

const DEFAULT_PARTS = [
  { key: 'system', label: 'System', color: 'bg-purple-500' },
  { key: 'user', label: 'User', color: 'bg-blue-500' },
  { key: 'history', label: 'History', color: 'bg-orange-500' },
  { key: 'tools', label: 'Tools', color: 'bg-green-500' },
];

export default function PromptBreakdownBar({ breakdown, parts = DEFAULT_PARTS }) {
  const total = breakdown.total || Object.values(breakdown).reduce((a, b) => a + (b || 0), 0);
  
  if (!total) return null;

  const activeParts = parts
    .map(p => ({
      ...p,
      value: breakdown[p.key] || 0,
      percentage: ((breakdown[p.key] || 0) / total) * 100,
    }))
    .filter(p => p.value > 0);

  return (
    <div className="bg-gray-900 rounded-lg p-4">
      {/* Header */}
      <div className="text-sm text-gray-400 mb-3">
        Prompt Composition ({total.toLocaleString()} tokens)
      </div>

      {/* Progress Bar */}
      <div className="flex rounded-full h-5 overflow-hidden mb-3">
        {activeParts.map(part => (
          <div
            key={part.key}
            className={`${part.color} h-full transition-all`}
            style={{ width: `${part.percentage}%` }}
            title={`${part.label}: ${part.value.toLocaleString()}`}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-sm">
        {activeParts.map(part => (
          <span key={part.key} className="flex items-center gap-2">
            <span className={`w-3 h-3 rounded-full ${part.color}`} />
            <span className="text-gray-400">
              {part.label}: {part.value.toLocaleString()} ({part.percentage.toFixed(0)}%)
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}