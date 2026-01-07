/**
 * AddColumnDropdown - Dropdown to add columns
 *
 * Shows all available columns grouped by category.
 * Already visible columns are grayed out.
 */

import { useRef, useEffect } from 'react';
import { getColumnsByCategory } from '../../../config/columnDefinitions';
import { BASE_THEME } from '../../../utils/themeUtils';

export default function AddColumnDropdown({
  visibleColumns,
  onSelect,
  onClose,
  theme,
}) {
  const dropdownRef = useRef(null);
  const categories = getColumnsByCategory();
  
  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        onClose();
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);
  
  // Close on escape
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };
    
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);
  
  return (
    <div
      ref={dropdownRef}
      className={`absolute top-full right-0 mt-1 w-72 ${BASE_THEME.container.primary} rounded-lg border ${BASE_THEME.border.default} shadow-xl z-50 overflow-hidden`}
    >
      {/* Header */}
      <div className={`p-3 border-b ${BASE_THEME.container.secondary} flex justify-between items-center`}>
        <span className={`text-sm font-semibold ${BASE_THEME.text.secondary}`}>Add Column</span>
        <button
          onClick={onClose}
          className={`${BASE_THEME.text.muted} hover:${BASE_THEME.text.secondary}`}
        >
          ✕
        </button>
      </div>

      {/* Columns by Category */}
      <div className="max-h-96 overflow-y-auto">
        {categories.map(category => {
          // Check if any columns in this category are available (not already visible)
          const availableColumns = category.columns.filter(col => !visibleColumns.includes(col.key));

          return (
            <div key={category.name} className={`border-b ${BASE_THEME.container.secondary} last:border-0`}>
              {/* Category Header */}
              <div className={`px-3 py-2 ${BASE_THEME.container.secondary}/50`}>
                <span className={`text-xs font-semibold ${BASE_THEME.text.muted} uppercase tracking-wider`}>
                  {category.name}
                </span>
              </div>

              {/* Columns */}
              <div className="py-1">
                {category.columns.map(col => {
                  const isAlreadyVisible = visibleColumns.includes(col.key);

                  return (
                    <button
                      key={col.key}
                      onClick={() => !isAlreadyVisible && onSelect(col.key)}
                      disabled={isAlreadyVisible}
                      className={`
                        w-full text-left px-4 py-2 text-sm
                        flex items-center justify-between
                        ${isAlreadyVisible
                          ? `${BASE_THEME.text.muted} cursor-not-allowed`
                          : `${BASE_THEME.text.secondary} hover:${BASE_THEME.container.secondary} hover:${theme.text} cursor-pointer`
                        }
                      `}
                    >
                      <span>{col.label}</span>
                      {isAlreadyVisible && (
                        <span className={`text-xs ${BASE_THEME.text.muted}`}>✓ Added</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className={`p-2 border-t ${BASE_THEME.container.secondary} ${BASE_THEME.container.primary}`}>
        <span className={`text-xs ${BASE_THEME.text.muted}`}>
          {visibleColumns.length} columns visible
        </span>
      </div>
    </div>
  );
}
