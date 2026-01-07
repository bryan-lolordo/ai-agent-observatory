/**
 * QuickFilters - Preset filter buttons
 *
 * Displays a row of quick filter buttons. Only one can be active at a time.
 */

import { BASE_THEME } from '../../../utils/themeUtils';

export default function QuickFilters({
  filters = [],
  activeFilter,
  onChange,
  onClearAll,
  hasActiveFilters,
  theme,
}) {
  if (!filters.length) return null;

  return (
    <div className="flex items-center gap-3 mb-3">
      <span className={`text-sm ${BASE_THEME.text.muted} font-semibold w-28 flex-shrink-0`}>
        QUICK FILTERS
      </span>
      <div className="flex flex-wrap gap-2">
        {filters.map(filter => {
          const isActive = activeFilter === filter.id;

          return (
            <button
              key={filter.id}
              onClick={() => onChange(filter.id)}
              className={`
                px-4 py-2 rounded-lg text-sm font-semibold
                flex items-center gap-2 transition-all
                ${isActive
                  ? `${theme.bg} text-white shadow-[0_0_10px_var(--glow-color)]`
                  : `${BASE_THEME.container.secondary} ${BASE_THEME.text.muted} border ${BASE_THEME.border.default} hover:${BASE_THEME.border.light} hover:${BASE_THEME.text.secondary}`
                }
              `}
              style={{ '--glow-color': `${theme.color}40` }}
              title={filter.description}
            >
              <span className="text-base">{filter.icon}</span>
              <span>{filter.label}</span>
            </button>
          );
        })}
      </div>

      {hasActiveFilters && activeFilter !== 'all' && (
        <button
          onClick={onClearAll}
          className={`px-3 py-2 text-sm ${BASE_THEME.text.muted} hover:text-white ${BASE_THEME.container.secondary} hover:${BASE_THEME.border.light} border ${BASE_THEME.border.default} rounded-lg transition-colors ml-2`}
        >
          Clear All
        </button>
      )}
    </div>
  );
}
