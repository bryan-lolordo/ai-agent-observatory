/**
 * Layer1Table - Simplified operations table for Layer 1 story pages
 *
 * Features:
 * - Agent/Operation dropdown filters
 * - Consistent columns across all stories
 * - Click row to navigate to operation detail
 * - Story-themed styling
 *
 * Does NOT include:
 * - Column sorting
 * - Column reordering/adding/removing
 * - Quick filters
 */

import { useState, useMemo } from 'react';
import { BASE_THEME } from '../../../utils/themeUtils';
import { formatNumber, truncateText } from '../../../utils/formatters';

export default function Layer1Table({
  data = [],
  theme,
  storyId,
  onRowClick,
  // Column configuration - which metric columns to show
  columns = [],
  // Optional: custom row renderer for the metric columns
  renderMetricCells,
}) {
  // Filter state
  const [agentFilter, setAgentFilter] = useState('all');
  const [operationFilter, setOperationFilter] = useState('all');

  // Get unique agents and operations for filters
  const uniqueAgents = useMemo(() => {
    const agents = [...new Set(data.map(row => row.agent_name).filter(Boolean))];
    return agents.sort();
  }, [data]);

  const uniqueOperations = useMemo(() => {
    const ops = [...new Set(data.map(row => row.operation || row.operation_name).filter(Boolean))];
    return ops.sort();
  }, [data]);

  // Filter the table data
  const filteredData = useMemo(() => {
    return data.filter(row => {
      const matchesAgent = agentFilter === 'all' || row.agent_name === agentFilter;
      const opName = row.operation || row.operation_name;
      const matchesOp = operationFilter === 'all' || opName === operationFilter;
      return matchesAgent && matchesOp;
    });
  }, [data, agentFilter, operationFilter]);

  const clearFilters = () => {
    setAgentFilter('all');
    setOperationFilter('all');
  };

  const hasActiveFilters = agentFilter !== 'all' || operationFilter !== 'all';

  // Get operation name from row (handles both naming conventions)
  const getOperationName = (row) => row.operation || row.operation_name || '—';

  return (
    <div className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} overflow-hidden`}>
      <div className={`h-1 ${theme.bg}`} />

      {/* Header with Filters */}
      <div className={`p-4 border-b ${BASE_THEME.border.default}`}>
        <div className="flex items-center justify-between mb-3">
          <h3 className={`text-sm font-medium ${theme.text} uppercase tracking-wide`}>
            📊 Operations
            <span className={`${BASE_THEME.text.muted} normal-case ml-2 font-normal`}>Click row to drill down</span>
          </h3>
          {hasActiveFilters && (
            <span className={`text-sm ${theme.text}`}>
              Showing {filteredData.length} of {data.length}
            </span>
          )}
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <label className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide`}>Agent:</label>
            <select
              value={agentFilter}
              onChange={(e) => setAgentFilter(e.target.value)}
              className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded px-3 py-1.5 text-sm ${BASE_THEME.text.secondary} focus:outline-none focus:${theme.border}`}
              style={{ '--tw-ring-color': theme.color }}
            >
              <option value="all">All Agents</option>
              {uniqueAgents.map(agent => (
                <option key={agent} value={agent}>{agent}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide`}>Operation:</label>
            <select
              value={operationFilter}
              onChange={(e) => setOperationFilter(e.target.value)}
              className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded px-3 py-1.5 text-sm ${BASE_THEME.text.secondary} focus:outline-none focus:${theme.border}`}
            >
              <option value="all">All Operations</option>
              {uniqueOperations.map(op => (
                <option key={op} value={op}>{truncateText(op, 40)}</option>
              ))}
            </select>
          </div>

          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className={`px-3 py-1.5 text-sm ${BASE_THEME.text.muted} hover:${BASE_THEME.text.primary} transition-colors`}
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto overflow-y-auto max-h-96">
        <table className="w-full text-sm" style={{ tableLayout: 'fixed' }}>
          <thead className={`${BASE_THEME.container.secondary}/50`}>
            <tr className={`border-b ${BASE_THEME.border.default}`}>
              <th style={{ width: '5%' }} className={`text-left py-3 px-4 ${BASE_THEME.text.muted} font-medium`}>Status</th>
              <th style={{ width: '18%' }} className={`text-left py-3 px-4 ${BASE_THEME.text.muted} font-medium`}>Agent</th>
              <th style={{ width: '32%' }} className={`text-left py-3 px-4 ${BASE_THEME.text.muted} font-medium`}>Operation</th>
              {columns.map(col => (
                <th
                  key={col.key}
                  style={{ width: col.width || '15%' }}
                  className={`text-right py-3 px-4 ${BASE_THEME.text.muted} font-medium`}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredData.length > 0 ? (
              filteredData.map((row, idx) => {
                const statusEmoji = row.status_emoji || (row.is_slow ? '🟡' : '🟢');
                const operationName = getOperationName(row);

                return (
                  <tr
                    key={row.call_id || idx}
                    onClick={() => onRowClick?.(row)}
                    className="border-b border-numerro-border/20 cursor-pointer transition-colors"
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = `${theme.color}08`}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = ''}
                  >
                    <td className="py-3 px-4 text-lg">{statusEmoji}</td>
                    <td className="py-3 px-4 font-semibold text-purple-400">
                      {row.agent_name || '—'}
                    </td>
                    <td className={`py-3 px-4 font-mono ${theme.text}`}>
                      {truncateText(operationName, 30)}
                    </td>
                    {renderMetricCells ? (
                      renderMetricCells(row, columns)
                    ) : (
                      columns.map(col => (
                        <td
                          key={col.key}
                          className={`py-3 px-4 text-right ${col.className || BASE_THEME.text.secondary}`}
                        >
                          {col.formatter ? col.formatter(row[col.key], row) : (row[col.key] ?? '—')}
                        </td>
                      ))
                    )}
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan={3 + columns.length} className={`py-12 text-center ${BASE_THEME.text.muted}`}>
                  {hasActiveFilters ? 'No operations match the current filters' : 'No data available'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className={`${BASE_THEME.container.secondary}/50 px-4 py-2 text-sm ${BASE_THEME.text.muted} border-t ${BASE_THEME.border.default}`}>
        <span>
          {filteredData.length} operation{filteredData.length !== 1 ? 's' : ''}
          {hasActiveFilters && ` (filtered from ${data.length})`}
        </span>
      </div>
    </div>
  );
}
