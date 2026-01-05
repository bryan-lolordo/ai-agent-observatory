/**
 * ColumnHeader - Individual column header
 *
 * Features:
 * - Drag handle (⠿) for reordering
 * - Click name to sort
 * - Filter dropdown (▼) for multi-select
 * - Delete button (✕) on hover
 * - Resize handle for adjustable column widths
 */

import { useState, useRef, useEffect } from 'react';

export default function ColumnHeader({
  column,
  isSorted,
  sortDirection,
  isFirst,
  isLast,
  canRemove,
  isDragging,
  isDragOver,
  onSort,
  onRemove,
  onDragStart,
  onDragOver,
  onDragEnd,
  onFilterChange,
  filterValues = [],
  uniqueValues = [],
  theme,
  storyId,
  primaryMetric,
  columnWidth,
  onResize,
}) {
  const [isHovered, setIsHovered] = useState(false);
  const [showFilter, setShowFilter] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const filterRef = useRef(null);
  const resizeStartX = useRef(0);
  const resizeStartWidth = useRef(0);

  // Close filter on click outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (filterRef.current && !filterRef.current.contains(e.target)) {
        setShowFilter(false);
      }
    };

    if (showFilter) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showFilter]);

  // Handle resize mouse events
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;
      const diff = e.clientX - resizeStartX.current;
      const newWidth = Math.max(80, resizeStartWidth.current + diff);
      onResize?.(column.key, newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, column.key, onResize]);

  const handleResizeStart = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsResizing(true);
    resizeStartX.current = e.clientX;
    resizeStartWidth.current = columnWidth || 150;
  };

  // Toggle value in filter
  const toggleFilterValue = (value) => {
    if (filterValues.includes(value)) {
      onFilterChange(filterValues.filter(v => v !== value));
    } else {
      onFilterChange([...filterValues, value]);
    }
  };

  // Is this the primary metric column for the story?
  const isPrimaryMetric = column.key === primaryMetric;

  // Header text color
  const textColor = isSorted || isPrimaryMetric ? theme.text : 'text-gray-500';

  return (
    <th
      draggable
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', column.key);
        onDragStart();
      }}
      onDragOver={(e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        onDragOver();
      }}
      onDragEnd={onDragEnd}
      onDrop={(e) => {
        e.preventDefault();
        onDragEnd();
      }}
      className={`
        py-3 px-4 text-center text-sm font-semibold relative select-none transition-all duration-150 cursor-grab active:cursor-grabbing
        ${isDragging ? 'opacity-40 scale-95 bg-gray-900' : ''}
        ${isDragOver ? 'bg-gray-700/50' : ''}
      `}
      style={{
        width: columnWidth ? `${columnWidth}px` : 'auto',
        minWidth: '80px',
        boxShadow: isDragOver ? `inset 4px 0 0 ${theme.color}` : 'none',
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Drop indicator line */}
      {isDragOver && (
        <div
          className="absolute left-0 top-0 bottom-0 w-1"
          style={{ backgroundColor: theme.color }}
        />
      )}

      <div className="flex items-center justify-center gap-1">
        {/* Drag Handle indicator */}
        <span
          className="text-gray-600 hover:text-gray-400"
          title="Drag to reorder"
        >
          ⋮⋮
        </span>

        {/* Column Name (click to sort) */}
        <button
          onClick={onSort}
          className={`flex items-center gap-1 hover:text-gray-300 ${textColor}`}
        >
          <span>{column.label}</span>
          {column.sortable && (
            <span className={isSorted ? theme.text : 'text-gray-600'}>
              {isSorted
                ? (sortDirection === 'desc' ? '↓' : '↑')
                : '↕'
              }
            </span>
          )}
        </button>

        {/* Filter Button (if filterable) */}
        {column.filterable && (
          <div className="relative" ref={filterRef}>
            <button
              onClick={() => setShowFilter(!showFilter)}
              className={`
                text-xs ml-1 px-1 rounded
                ${filterValues.length > 0 ? theme.text : 'text-gray-600 hover:text-gray-400'}
              `}
              title="Filter column"
            >
              ▼
              {filterValues.length > 0 && (
                <span className={`absolute -top-1 -right-1 w-2 h-2 rounded-full ${theme.bg}`} />
              )}
            </button>

            {/* Filter Dropdown */}
            {showFilter && (
              <div className="absolute top-full left-0 mt-1 w-48 bg-gray-900 rounded-lg border border-gray-700 shadow-xl z-50 overflow-hidden">
                <div className="p-2 border-b border-gray-800">
                  <span className="text-xs text-gray-400">Filter {column.label}</span>
                </div>
                <div className="max-h-48 overflow-y-auto">
                  {uniqueValues.length > 0 ? (
                    uniqueValues.map(value => (
                      <label
                        key={value}
                        className="flex items-center gap-2 px-3 py-1.5 hover:bg-gray-800 cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={filterValues.includes(value)}
                          onChange={() => toggleFilterValue(value)}
                          className="w-3 h-3 rounded border-gray-600 bg-gray-800"
                          style={{ accentColor: theme.color }}
                        />
                        <span className="text-xs text-gray-300 truncate">{value}</span>
                      </label>
                    ))
                  ) : (
                    <div className="px-3 py-2 text-xs text-gray-500">No values</div>
                  )}
                </div>
                <div className="p-2 border-t border-gray-800 flex justify-between">
                  <button
                    onClick={() => onFilterChange([])}
                    className="text-xs text-gray-500 hover:text-gray-300"
                  >
                    Clear
                  </button>
                  <button
                    onClick={() => setShowFilter(false)}
                    className={`text-xs ${theme.text}`}
                  >
                    Done
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Delete Button (on hover) - positioned far right */}
      {canRemove && (
        <button
          onClick={onRemove}
          className={`
            absolute top-1/2 -translate-y-1/2 right-4
            text-gray-600 hover:text-red-400 transition-opacity
            ${isHovered ? 'opacity-100' : 'opacity-0'}
          `}
          title="Remove column"
        >
          ✕
        </button>
      )}

      {/* Resize Handle */}
      <div
        onMouseDown={handleResizeStart}
        className={`
          absolute top-0 right-0 w-2 h-full cursor-col-resize
          group flex items-center justify-center
          ${isResizing ? 'bg-blue-500/50' : 'hover:bg-gray-600'}
        `}
        title="Drag to resize"
      >
        <div className={`w-0.5 h-4 rounded ${isResizing ? 'bg-blue-400' : 'bg-gray-500 group-hover:bg-gray-400'}`} />
      </div>
    </th>
  );
}
