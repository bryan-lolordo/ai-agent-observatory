/**
 * Layer2Table - Main Component
 * 
 * Full-featured data table with:
 * - 2E Header Divider design (glowing divider line)
 * - Quick filters (preset filter buttons)
 * - Column filters (multi-select dropdowns)
 * - Add column (grouped dropdown with all available columns)
 * - Drag to reorder columns
 * - Click to sort
 * - Hover to reveal delete button
 * - Active filters display
 */

import { useState, useMemo, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { STORY_THEMES } from '../../../config/theme';
import { ALL_COLUMNS, getColumn, getColumnsByCategory } from '../../../config/columnDefinitions';
import { getLayer2Config } from '../../../config/storyDefinitions';

// Sub-components
import QuickFilters from './QuickFilters';
import FilterBar from './FilterBar';
import ColumnHeader from './ColumnHeader';
import AddColumnDropdown from './AddColumnDropdown';
import TableRow from './TableRow';

export default function Layer2Table({
  storyId,
  data = [],
  initialFilters = {},
  initialQuickFilter = 'all',
  onRowClick,
  loading = false,
}) {
  const navigate = useNavigate();
  const theme = STORY_THEMES[storyId];
  const config = getLayer2Config(storyId);
  
  // ─────────────────────────────────────────────────────────────────────────────
  // STATE
  // ─────────────────────────────────────────────────────────────────────────────
  
  // Columns state (order and visibility)
  const [visibleColumns, setVisibleColumns] = useState(config?.defaultColumns || []);
  
  // Sort state
  const [sortConfig, setSortConfig] = useState(config?.defaultSort || { key: null, direction: 'desc' });
  
  // Quick filter state (only one active at a time)
  const [activeQuickFilter, setActiveQuickFilter] = useState(initialQuickFilter);
  
  // Column filters state (multi-select per column)
  const [columnFilters, setColumnFilters] = useState(initialFilters);
  
  // Drag state
  const [draggedColumn, setDraggedColumn] = useState(null);
  const [dragOverColumn, setDragOverColumn] = useState(null);

  // Add column dropdown state
  const [showAddColumn, setShowAddColumn] = useState(false);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Column widths state (for resizable columns)
  const [columnWidths, setColumnWidths] = useState({});

  // Handle column resize
  const handleColumnResize = useCallback((columnKey, newWidth) => {
    setColumnWidths(prev => ({
      ...prev,
      [columnKey]: newWidth,
    }));
  }, []);

  // ─────────────────────────────────────────────────────────────────────────────
  // COLUMN MANAGEMENT
  // ─────────────────────────────────────────────────────────────────────────────
  
  // Add a column
  const handleAddColumn = useCallback((columnKey) => {
    if (!visibleColumns.includes(columnKey)) {
      setVisibleColumns(prev => [...prev, columnKey]);
    }
    setShowAddColumn(false);
  }, [visibleColumns]);
  
  // Remove a column
  const handleRemoveColumn = useCallback((columnKey) => {
    if (visibleColumns.length > 1) {
      setVisibleColumns(prev => prev.filter(k => k !== columnKey));
      // Also remove any filters for this column
      setColumnFilters(prev => {
        const next = { ...prev };
        delete next[columnKey];
        return next;
      });
    }
  }, [visibleColumns]);
  
  // Drag and drop
  const handleDragStart = useCallback((columnKey) => {
    setDraggedColumn(columnKey);
  }, []);
  
  const handleDragOver = useCallback((columnKey) => {
    if (draggedColumn && columnKey !== draggedColumn) {
      setDragOverColumn(columnKey);
    }
  }, [draggedColumn]);
  
  const handleDragEnd = useCallback(() => {
    if (draggedColumn && dragOverColumn) {
      setVisibleColumns(prev => {
        const newOrder = [...prev];
        const draggedIdx = newOrder.indexOf(draggedColumn);
        const targetIdx = newOrder.indexOf(dragOverColumn);
        newOrder.splice(draggedIdx, 1);
        newOrder.splice(targetIdx, 0, draggedColumn);
        return newOrder;
      });
    }
    setDraggedColumn(null);
    setDragOverColumn(null);
  }, [draggedColumn, dragOverColumn]);
  
  // ─────────────────────────────────────────────────────────────────────────────
  // SORTING
  // ─────────────────────────────────────────────────────────────────────────────
  
  const handleSort = useCallback((columnKey) => {
    setSortConfig(prev => {
      // Cycle: unsorted → desc → asc → unsorted
      if (prev.key !== columnKey) {
        // New column: start with descending
        return { key: columnKey, direction: 'desc' };
      } else if (prev.direction === 'desc') {
        // Same column, was desc: switch to asc
        return { key: columnKey, direction: 'asc' };
      } else {
        // Same column, was asc: clear sort
        return { key: null, direction: 'desc' };
      }
    });
  }, []);
  
  // ─────────────────────────────────────────────────────────────────────────────
  // FILTERING
  // ─────────────────────────────────────────────────────────────────────────────
  
  const handleQuickFilterChange = useCallback((filterId) => {
    setActiveQuickFilter(filterId);
  }, []);
  
  const handleColumnFilterChange = useCallback((columnKey, values) => {
    setColumnFilters(prev => {
      if (!values || values.length === 0) {
        const next = { ...prev };
        delete next[columnKey];
        return next;
      }
      return { ...prev, [columnKey]: values };
    });
  }, []);
  
  const handleClearAllFilters = useCallback(() => {
    setActiveQuickFilter('all');
    setColumnFilters({});
  }, []);
  
  const handleRemoveFilter = useCallback((columnKey, value) => {
    setColumnFilters(prev => {
      const currentValues = prev[columnKey] || [];
      const newValues = currentValues.filter(v => v !== value);
      if (newValues.length === 0) {
        const next = { ...prev };
        delete next[columnKey];
        return next;
      }
      return { ...prev, [columnKey]: newValues };
    });
  }, []);
  
  // ─────────────────────────────────────────────────────────────────────────────
  // DATA PROCESSING
  // ─────────────────────────────────────────────────────────────────────────────
  
  // Get unique values for filterable columns
  const uniqueColumnValues = useMemo(() => {
    const values = {};
    visibleColumns.forEach(colKey => {
      const colDef = getColumn(colKey);
      if (colDef?.filterable) {
        const unique = [...new Set(data.map(row => row[colKey]).filter(Boolean))];
        values[colKey] = unique.sort();
      }
    });
    return values;
  }, [data, visibleColumns]);
  
  // Apply filters and sorting
  const processedData = useMemo(() => {
    let result = [...data];
    
    // Apply quick filter
    const quickFilter = config?.quickFilters?.find(f => f.id === activeQuickFilter);
    if (quickFilter?.logic) {
      const { field, op, value, type, filters } = quickFilter.logic;
      
      if (type === 'max') {
        const maxVal = Math.max(...result.map(r => r[field] || 0));
        result = result.filter(r => r[field] === maxVal);
      } else if (type === 'min') {
        const minVal = Math.min(...result.filter(r => r[field] != null).map(r => r[field]));
        result = result.filter(r => r[field] === minVal);
      } else if (type === 'compound' && filters) {
        filters.forEach(f => {
          result = applyFilter(result, f);
        });
      } else {
        result = applyFilter(result, quickFilter.logic);
      }
    }
    
    // Apply column filters
    Object.entries(columnFilters).forEach(([colKey, values]) => {
      if (values && values.length > 0) {
        result = result.filter(row => values.includes(row[colKey]));
      }
    });
    
    // Apply sorting
    if (sortConfig.key) {
      result.sort((a, b) => {
        const aVal = a[sortConfig.key];
        const bVal = b[sortConfig.key];
        
        if (aVal == null) return 1;
        if (bVal == null) return -1;
        
        let comparison = 0;
        if (typeof aVal === 'number' && typeof bVal === 'number') {
          comparison = aVal - bVal;
        } else {
          comparison = String(aVal).localeCompare(String(bVal));
        }
        
        return sortConfig.direction === 'desc' ? -comparison : comparison;
      });
    }
    
    return result;
  }, [data, activeQuickFilter, columnFilters, sortConfig, config]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [activeQuickFilter, columnFilters]);

  // Paginated data
  const paginatedData = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return processedData.slice(startIndex, endIndex);
  }, [processedData, currentPage, pageSize]);

  // Total pages
  const totalPages = useMemo(() => {
    return Math.ceil(processedData.length / pageSize);
  }, [processedData.length, pageSize]);

  // Generate page numbers to display
  const getPageNumbers = () => {
    const pages = [];
    const maxVisible = 5;

    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      // Always show first page
      pages.push(1);

      // Calculate range around current page
      let start = Math.max(2, currentPage - 1);
      let end = Math.min(totalPages - 1, currentPage + 1);

      // Adjust if at edges
      if (currentPage <= 2) {
        end = 4;
      } else if (currentPage >= totalPages - 1) {
        start = totalPages - 3;
      }

      // Add ellipsis if needed before
      if (start > 2) pages.push('...');

      // Add middle pages
      for (let i = start; i <= end; i++) pages.push(i);

      // Add ellipsis if needed after
      if (end < totalPages - 1) pages.push('...');

      // Always show last page
      if (totalPages > 1) pages.push(totalPages);
    }

    return pages;
  };

  // Helper function to apply a single filter
  function applyFilter(data, filter) {
    const { field, op, value } = filter;
    return data.filter(row => {
      const rowVal = row[field];
      switch (op) {
        case '=': return rowVal === value;
        case '!=': return rowVal !== value;
        case '>': return rowVal > value;
        case '>=': return rowVal >= value;
        case '<': return rowVal < value;
        case '<=': return rowVal <= value;
        case 'between': return rowVal >= value[0] && rowVal <= value[1];
        default: return true;
      }
    });
  }
  
  // ─────────────────────────────────────────────────────────────────────────────
  // ROW CLICK
  // ─────────────────────────────────────────────────────────────────────────────
  
  const handleRowClick = useCallback((row) => {
    if (onRowClick) {
      onRowClick(row);
    } else if (row.call_id) {
      // Default: navigate to call detail
      navigate(`/stories/${storyId}/calls/${row.call_id}`);
    }
  }, [onRowClick, navigate, storyId]);
  
  // ─────────────────────────────────────────────────────────────────────────────
  // GET ACTIVE FILTERS FOR DISPLAY
  // ─────────────────────────────────────────────────────────────────────────────
  
  const activeFilters = useMemo(() => {
    const filters = [];
    
    // Add column filters
    Object.entries(columnFilters).forEach(([colKey, values]) => {
      const colDef = getColumn(colKey);
      values.forEach(value => {
        filters.push({
          columnKey: colKey,
          columnLabel: colDef?.label || colKey,
          value,
          displayValue: String(value),
        });
      });
    });
    
    return filters;
  }, [columnFilters]);
  
  // Check if any filters are active
  const hasActiveFilters = activeQuickFilter !== 'all' || activeFilters.length > 0;
  
  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────────────
  
  const columnDefs = visibleColumns.map(key => getColumn(key)).filter(Boolean);
  
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-700 overflow-hidden shadow-[0_0_20px_rgba(0,0,0,0.3)]">
      
      {/* ═══════════════════════════════════════════════════════════════════════
          HEADER SECTION
          ═══════════════════════════════════════════════════════════════════════ */}
      <div className="p-4">
        
        {/* Quick Filters */}
        <QuickFilters
          filters={config?.quickFilters || []}
          activeFilter={activeQuickFilter}
          onChange={handleQuickFilterChange}
          onClearAll={handleClearAllFilters}
          hasActiveFilters={hasActiveFilters}
          theme={theme}
        />
        
        {/* Filter Bar */}
        <FilterBar
          columns={config?.filterBarColumns || ['operation', 'agent_name']}
          columnFilters={columnFilters}
          uniqueValues={uniqueColumnValues}
          onChange={handleColumnFilterChange}
          onClearAll={handleClearAllFilters}
          hasActiveFilters={hasActiveFilters}
          theme={theme}
        />
        
        {/* Active Filters Display */}
        <div className="flex items-center gap-2 mt-3 min-h-[32px]">
          <span className="text-xs text-gray-500">Active:</span>
          {activeFilters.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {activeFilters.map((filter, idx) => (
                <span
                  key={`${filter.columnKey}-${filter.value}-${idx}`}
                  className="px-2 py-1 rounded-lg text-xs bg-gray-800 text-gray-300 border border-gray-700 flex items-center gap-1"
                >
                  <span className="text-gray-500">{filter.columnLabel}:</span>
                  <span>{filter.displayValue}</span>
                  <button
                    onClick={() => handleRemoveFilter(filter.columnKey, filter.value)}
                    className="ml-1 text-gray-500 hover:text-gray-300"
                  >
                    ✕
                  </button>
                </span>
              ))}
            </div>
          ) : (
            <span className="text-xs text-gray-600 italic">No filters applied</span>
          )}
        </div>
      </div>
      
      {/* ═══════════════════════════════════════════════════════════════════════
          GLOWING DIVIDER (2E Style)
          ═══════════════════════════════════════════════════════════════════════ */}
      <div 
        className="h-1 shadow-[0_0_10px_var(--glow-color)]"
        style={{ 
          background: `linear-gradient(to right, ${theme.color}, ${theme.color})`,
          '--glow-color': `${theme.color}80`,
        }}
      />
      
      {/* ═══════════════════════════════════════════════════════════════════════
          TABLE
          ═══════════════════════════════════════════════════════════════════════ */}
      <div className={`overflow-x-auto min-h-[400px] story-scrollbar-thin ${storyId}`}>
        <table className="w-full text-lg">
          
          {/* Table Header */}
          <thead className="bg-gray-800">
            {/* Drag mode indicator */}
            {draggedColumn && (
              <tr>
                <td
                  colSpan={columnDefs.length + 1}
                  className="py-1 text-center text-xs text-gray-400 border-b border-gray-700"
                  style={{ backgroundColor: `${theme.color}15` }}
                >
                  <span className="animate-pulse">
                    Dragging <span style={{ color: theme.color }} className="font-semibold">{getColumn(draggedColumn)?.label}</span> — drop on another column to reorder
                  </span>
                </td>
              </tr>
            )}
            <tr className="border-b border-gray-700">
              {columnDefs.map((col, idx) => (
                <ColumnHeader
                  key={col.key}
                  column={col}
                  isSorted={sortConfig.key === col.key}
                  sortDirection={sortConfig.direction}
                  isFirst={idx === 0}
                  isLast={idx === columnDefs.length - 1}
                  canRemove={visibleColumns.length > 1}
                  isDragging={draggedColumn === col.key}
                  isDragOver={dragOverColumn === col.key}
                  onSort={() => handleSort(col.key)}
                  onRemove={() => handleRemoveColumn(col.key)}
                  onDragStart={() => handleDragStart(col.key)}
                  onDragOver={() => handleDragOver(col.key)}
                  onDragEnd={handleDragEnd}
                  onFilterChange={(values) => handleColumnFilterChange(col.key, values)}
                  filterValues={columnFilters[col.key] || []}
                  uniqueValues={uniqueColumnValues[col.key] || []}
                  theme={theme}
                  storyId={storyId}
                  primaryMetric={config?.primaryMetric}
                  columnWidth={columnWidths[col.key]}
                  onResize={handleColumnResize}
                />
              ))}
              
              {/* Add Column Button */}
              <th className="py-3 px-2 w-12 relative">
                <button
                  onClick={() => setShowAddColumn(!showAddColumn)}
                  className="w-8 h-8 rounded-lg bg-gray-700 text-gray-400 hover:text-white hover:bg-gray-600 flex items-center justify-center text-lg font-bold transition-colors"
                >
                  +
                </button>
                
                {showAddColumn && (
                  <AddColumnDropdown
                    visibleColumns={visibleColumns}
                    onSelect={handleAddColumn}
                    onClose={() => setShowAddColumn(false)}
                    theme={theme}
                  />
                )}
              </th>
            </tr>
          </thead>
          
          {/* Table Body */}
          <tbody>
            {loading ? (
              // Loading skeleton
              Array.from({ length: 5 }).map((_, idx) => (
                <tr key={idx} className="border-b border-gray-800">
                  {columnDefs.map(col => (
                    <td key={col.key} className="py-3 px-4">
                      <div className="h-4 bg-gray-800 rounded animate-pulse" />
                    </td>
                  ))}
                  <td className="py-3 px-2" />
                </tr>
              ))
            ) : paginatedData.length > 0 ? (
              paginatedData.map((row, idx) => (
                <TableRow
                  key={row.call_id || idx}
                  row={row}
                  columns={columnDefs}
                  onClick={() => handleRowClick(row)}
                  theme={theme}
                  storyId={storyId}
                  primaryMetric={config?.primaryMetric}
                  columnWidths={columnWidths}
                />
              ))
            ) : (
              <tr>
                <td colSpan={columnDefs.length + 1} className="py-12 text-center text-gray-500">
                  No data matching current filters
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      
      {/* ═══════════════════════════════════════════════════════════════════════
          FOOTER WITH PAGINATION
          ═══════════════════════════════════════════════════════════════════════ */}
      <div className="bg-gray-800/50 px-4 py-3 text-sm text-gray-500 flex justify-between items-center border-t border-gray-700">
        {/* Left: Count info */}
        <span>
          Showing <span className={`font-semibold ${theme.text}`}>
            {Math.min((currentPage - 1) * pageSize + 1, processedData.length)}
          </span>
          {processedData.length > 0 && (
            <>
              –<span className={`font-semibold ${theme.text}`}>
                {Math.min(currentPage * pageSize, processedData.length)}
              </span>
            </>
          )}
          {' '}of <span className="text-gray-300">{processedData.length}</span>
          {processedData.length !== data.length && (
            <> (filtered from {data.length})</>
          )} calls
        </span>

        {/* Center: Pagination controls */}
        {totalPages > 1 && (
          <div className="flex items-center gap-1">
            {/* Previous button */}
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className={`px-3 py-1.5 rounded-lg transition-colors ${
                currentPage === 1
                  ? 'text-gray-600 cursor-not-allowed'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }`}
            >
              ← Prev
            </button>

            {/* Page numbers */}
            <div className="flex items-center gap-1 mx-2">
              {getPageNumbers().map((page, idx) => (
                page === '...' ? (
                  <span key={`ellipsis-${idx}`} className="px-2 text-gray-600">...</span>
                ) : (
                  <button
                    key={page}
                    onClick={() => setCurrentPage(page)}
                    className={`min-w-[36px] px-2 py-1.5 rounded-lg transition-colors ${
                      currentPage === page
                        ? `${theme.bg} text-white font-semibold`
                        : 'text-gray-400 hover:text-white hover:bg-gray-700'
                    }`}
                  >
                    {page}
                  </button>
                )
              ))}
            </div>

            {/* Next button */}
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className={`px-3 py-1.5 rounded-lg transition-colors ${
                currentPage === totalPages
                  ? 'text-gray-600 cursor-not-allowed'
                  : 'text-gray-400 hover:text-white hover:bg-gray-700'
              }`}
            >
              Next →
            </button>
          </div>
        )}

        {/* Right: Page size selector and column info */}
        <div className="flex items-center gap-4">
          {/* Page size selector */}
          <div className="flex items-center gap-2">
            <span className="text-gray-500">Show:</span>
            {[20, 50, 100].map(size => (
              <button
                key={size}
                onClick={() => {
                  setPageSize(size);
                  setCurrentPage(1);
                }}
                className={`px-2 py-1 rounded transition-colors ${
                  pageSize === size
                    ? `${theme.bg} text-white font-semibold`
                    : 'text-gray-400 hover:text-white hover:bg-gray-700'
                }`}
              >
                {size}
              </button>
            ))}
          </div>

          <span className="text-gray-600">|</span>
          <span>{visibleColumns.length} columns</span>
          {sortConfig.key && (
            <>
              <span className="text-gray-600">|</span>
              <span>
                Sort: {getColumn(sortConfig.key)?.label} {sortConfig.direction === 'desc' ? '↓' : '↑'}
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
