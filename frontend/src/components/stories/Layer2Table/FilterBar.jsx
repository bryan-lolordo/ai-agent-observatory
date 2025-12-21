/**
 * FilterBar - Column filter dropdowns
 * 
 * Shows Operation and Agent (or other configurable) filter dropdowns
 * with a single "Clear" button to clear column filters.
 */

import { useState, useRef, useEffect } from 'react';
import { getColumn } from '../../../config/columnDefinitions';

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
      <span className="text-xs text-gray-500 font-semibold w-24 flex-shrink-0">
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
            className="px-2 py-1.5 text-xs text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg transition-colors"
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
          px-3 py-1.5 rounded-lg text-xs
          flex items-center gap-1.5 transition-all
          ${hasSelection 
            ? `${theme.bgLight} ${theme.text} border ${theme.border}` 
            : 'bg-gray-800 text-gray-400 border border-gray-700 hover:border-gray-600'
          }
        `}
      >
        <span>{emoji}</span>
        <span>{column.label}</span>
        {hasSelection && (
          <span className={`px-1.5 py-0.5 rounded text-xs ${theme.bg} text-white ml-1`}>
            {selectedValues.length}
          </span>
        )}
        <span className="text-gray-600 ml-1">▼</span>
      </button>
      
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-64 bg-gray-900 rounded-lg border border-gray-700 shadow-xl z-50 overflow-hidden">
          {/* Header */}
          <div className="p-2 border-b border-gray-800 flex justify-between items-center">
            <span className="text-xs text-gray-400 font-semibold">{column.label}</span>
            <div className="flex gap-2">
              <button
                onClick={selectAll}
                className="text-xs text-gray-500 hover:text-gray-300"
              >
                All
              </button>
              <button
                onClick={deselectAll}
                className="text-xs text-gray-500 hover:text-gray-300"
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
                    className="flex items-center gap-2 px-3 py-2 hover:bg-gray-800 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleValue(value)}
                      className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-orange-500 focus:ring-0 focus:ring-offset-0"
                      style={{ accentColor: theme.color }}
                    />
                    <span className={`text-sm ${isSelected ? 'text-gray-200' : 'text-gray-400'}`}>
                      {value}
                    </span>
                  </label>
                );
              })
            ) : (
              <div className="px-3 py-4 text-center text-gray-500 text-sm">
                No values available
              </div>
            )}
          </div>
          
          {/* Footer with apply button */}
          <div className="p-2 border-t border-gray-800">
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