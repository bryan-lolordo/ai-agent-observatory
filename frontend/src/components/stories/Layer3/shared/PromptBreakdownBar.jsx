/**
 * PromptBreakdownBar - Visual breakdown of prompt token composition
 *
 * UPDATED: Uses theme system - no hardcoded colors!
 */

import { BASE_THEME } from '../../../../utils/themeUtils';
import { STORY_THEMES } from '../../../../config/theme';

// Use story theme colors for the breakdown parts
const DEFAULT_PARTS = [
  { key: 'system', label: 'System', color: STORY_THEMES.routing.bg },  // Purple
  { key: 'user', label: 'User', color: STORY_THEMES.quality.bg },      // Blue (using info color)
  { key: 'history', label: 'History', color: STORY_THEMES.latency.bg }, // Orange
  { key: 'tools', label: 'Tools', color: STORY_THEMES.optimization.bg }, // Green
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
    <div className={`${BASE_THEME.container.primary} rounded-lg p-4`}>
      {/* Header */}
      <div className={`text-sm ${BASE_THEME.text.secondary} mb-3`}>
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
            <span className={BASE_THEME.text.secondary}>
              {part.label}: {part.value.toLocaleString()} ({part.percentage.toFixed(0)}%)
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
