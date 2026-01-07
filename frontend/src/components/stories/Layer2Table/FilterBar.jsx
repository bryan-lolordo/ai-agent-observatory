/**
 * FilterBar - Column filter dropdowns
 *
 * Shows Operation and Agent (or other configurable) filter dropdowns
 * with a single "Clear" button to clear column filters.
 */

import { useState, useRef, useEffect } from 'react';
import { getColumn } from '../../../config/columnDefinitions';
import { BASE_THEME } from '../../../utils/themeUtils';

export default function FilterBar({
  columns = [],
  columnFilters = {},
  uniqueValues = {},
  onChange,
  theme,
}) {
  // Check if any column filters are active
  const hasColumnFilters = columns.some(colKey => (columnFilters[colKey] || []).length > 0);
  
  // Clear all column filters
  const handleClearColumnFilters = () => {
    columns.forEach(colKey => {
      onChange(colKey, []);
    });
  };
  
  return (
    <div className="flex items-center gap-3">
      <span className={`text-sm ${BASE_THEME.text.muted} font-semibold w-28 flex-shrink-0`}>
        FILTERS
      </span>
      <div className="flex items-center gap-2">
        {columns.map(colKey => {
          const colDef = getColumn(colKey);
          if (!colDef) return null;

          return (
            <FilterDropdown
              key={colKey}
              column={colDef}
              selectedValues={columnFilters[colKey] || []}
              uniqueValues={uniqueValues[colKey] || []}
              onChange={(values) => onChange(colKey, values)}
              theme={theme}
            />
          );
        })}

        {/* Single Clear button for column filters */}
        {hasColumnFilters && (
          <button
            onClick={handleClearColumnFilters}
            className={`px-3 py-2 text-sm ${BASE_THEME.text.muted} hover:text-white ${BASE_THEME.container.secondary} hover:${BASE_THEME.border.light} border ${BASE_THEME.border.default} rounded-lg transition-colors`}
          >
            Clear
          </button>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// FilterDropdown - Individual multi-select dropdown
// ─────────────────────────────────────────────────────────────────────────────

function FilterDropdown({
  column,
  selectedValues,
  uniqueValues,
  onChange,
  theme,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  
  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);
  
  // Toggle a value in selection
  const toggleValue = (value) => {
    if (selectedValues.includes(value)) {
      onChange(selectedValues.filter(v => v !== value));
    } else {
      onChange([...selectedValues, value]);
    }
  };
  
  // Select all / deselect all
  const selectAll = () => onChange([...uniqueValues]);
  const deselectAll = () => onChange([]);
  
  const hasSelection = selectedValues.length > 0;
  const emoji = column.key === 'operation' ? '⚙️' : 
                column.key === 'agent_name' ? '🤖' : 
                column.key === 'model_name' ? '🧠' : '📋';
  
  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`
          px-4 py-2 rounded-lg text-sm
          flex items-center gap-2 transition-all
          ${hasSelection
            ? `${theme.bgLight} ${theme.text} border ${theme.border}`
            : `${BASE_THEME.container.secondary} ${BASE_THEME.text.muted} border ${BASE_THEME.border.default} hover:${BASE_THEME.border.light}`
          }
        `}
      >
        <span className="text-base">{emoji}</span>
        <span>{column.label}</span>
        {hasSelection && (
          <span className={`px-1.5 py-0.5 rounded text-xs ${theme.bg} text-white ml-1`}>
            {selectedValues.length}
          </span>
        )}
        <span className={`${BASE_THEME.text.muted} ml-1`}>▼</span>
      </button>

      {isOpen && (
        <div className={`absolute top-full left-0 mt-1 w-64 ${BASE_THEME.container.primary} rounded-lg border ${BASE_THEME.border.default} shadow-xl z-50 overflow-hidden`}>
          {/* Header */}
          <div className={`p-2 border-b ${BASE_THEME.container.secondary} flex justify-between items-center`}>
            <span className={`text-xs ${BASE_THEME.text.muted} font-semibold`}>{column.label}</span>
            <div className="flex gap-2">
              <button
                onClick={selectAll}
                className={`text-xs ${BASE_THEME.text.muted} hover:${BASE_THEME.text.secondary}`}
              >
                All
              </button>
              <button
                onClick={deselectAll}
                className={`text-xs ${BASE_THEME.text.muted} hover:${BASE_THEME.text.secondary}`}
              >
                None
              </button>
            </div>
          </div>

          {/* Options */}
          <div className="max-h-64 overflow-y-auto">
            {uniqueValues.length > 0 ? (
              uniqueValues.map(value => {
                const isSelected = selectedValues.includes(value);
                return (
                  <label
                    key={value}
                    className={`flex items-center gap-2 px-3 py-2 hover:${BASE_THEME.container.secondary} cursor-pointer`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleValue(value)}
                      className={`w-4 h-4 rounded ${BASE_THEME.border.light} ${BASE_THEME.container.secondary} text-orange-500 focus:ring-0 focus:ring-offset-0`}
                      style={{ accentColor: theme.color }}
                    />
                    <span className={`text-sm ${isSelected ? BASE_THEME.text.primary : BASE_THEME.text.muted}`}>
                      {value}
                    </span>
                  </label>
                );
              })
            ) : (
              <div className={`px-3 py-4 text-center ${BASE_THEME.text.muted} text-sm`}>
                No values available
              </div>
            )}
          </div>

          {/* Footer with apply button */}
          <div className={`p-2 border-t ${BASE_THEME.container.secondary}`}>
            <button
              onClick={() => setIsOpen(false)}
              className={`w-full py-1.5 rounded-lg text-xs font-semibold ${theme.bg} text-white hover:opacity-90`}
            >
              Apply
            </button>
          </div>
        </div>
      )}
    </div>
  );
}