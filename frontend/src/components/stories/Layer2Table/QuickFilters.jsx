/**
 * QuickFilters - Preset filter buttons
 * 
 * Displays a row of quick filter buttons. Only one can be active at a time.
 */

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
      <span className="text-sm text-gray-500 font-semibold w-28 flex-shrink-0">
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
                  : 'bg-gray-800 text-gray-400 border border-gray-700 hover:border-gray-600 hover:text-gray-300'
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
          className="px-3 py-2 text-sm text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg transition-colors ml-2"
        >
          Clear All
        </button>
      )}
    </div>
  );
}
