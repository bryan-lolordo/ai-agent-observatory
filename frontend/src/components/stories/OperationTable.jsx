/**
 * OperationTable Component
 * 
 * Reusable themed table for displaying operation data across story pages.
 * Supports rainbow theming and custom columns.
 */

import { useNavigate } from 'react-router-dom';
import { truncateText, formatNumber } from '../../utils/formatters';

/**
 * @param {object} props
 * @param {object} props.theme - Story theme from STORY_THEMES
 * @param {string} props.storyId - Story ID for navigation
 * @param {Array} props.data - Table data rows
 * @param {Array} props.columns - Column definitions
 * @param {Function} props.onRowClick - Optional row click handler
 * @param {number} props.maxHeight - Optional max height in pixels
 */
export default function OperationTable({
  theme,
  storyId,
  data = [],
  columns = [],
  onRowClick,
  maxHeight = 384, // 96 * 4 = 384px default
}) {
  const navigate = useNavigate();

  const handleRowClick = (row) => {
    if (onRowClick) {
      onRowClick(row);
    } else if (row.operation && storyId) {
      navigate(`/stories/${storyId}/operations/${row.operation}`);
    }
  };

  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No operations data available
      </div>
    );
  }

  return (
    <div 
      className="overflow-x-auto overflow-y-auto"
      style={{ maxHeight: `${maxHeight}px` }}
    >
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-gray-900 z-10">
          <tr className={`border-b-2 ${theme ? theme.border : 'border-gray-700'}`}>
            {columns.map((col, idx) => (
              <th 
                key={idx}
                className={`text-left py-3 px-4 font-medium ${
                  col.highlight && theme ? theme.textLight : 'text-gray-400'
                } ${col.align === 'right' ? 'text-right' : ''}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIdx) => (
            <tr 
              key={rowIdx}
              onClick={() => handleRowClick(row)}
              className={`
                border-b border-gray-800 cursor-pointer transition-all
                ${theme 
                  ? `hover:bg-gradient-to-r hover:${theme.gradient} hover:border-l-4 hover:${theme.border}` 
                  : 'hover:bg-gray-800'
                }
              `}
            >
              {columns.map((col, colIdx) => (
                <td 
                  key={colIdx}
                  className={`py-3 px-4 ${col.align === 'right' ? 'text-right' : ''}`}
                >
                  {col.render ? col.render(row) : row[col.field]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Common column renderers
 */
export const columnRenderers = {
  // Status emoji
  status: (row) => {
    if (row.is_critical) return '🔴';
    if (row.is_slow || row.is_warning) return '🟡';
    return '🟢';
  },

  // Operation name (truncated, themed)
  operation: (theme) => (row) => (
    <span className={`font-mono ${theme ? theme.text : 'text-blue-400'} font-semibold`}>
      {truncateText(row.operation, 40)}
    </span>
  ),

  // Agent name
  agent: (row) => (
    <span className="text-gray-400">
      {row.agent || row.agent_name || '—'}
    </span>
  ),

  // Latency with color coding
  latency: (theme) => (row) => {
    const latency = (row.avg_latency_ms || 0) / 1000;
    const colorClass = row.is_critical 
      ? 'text-red-400' 
      : row.is_slow 
        ? 'text-yellow-400' 
        : theme ? theme.text : 'text-green-400';
    
    return (
      <span className={`font-bold ${colorClass}`}>
        {latency.toFixed(1)}s
      </span>
    );
  },

  // Generic number formatter
  number: (row, field) => (
    <span className="text-gray-300">
      {formatNumber(row[field] || 0)}
    </span>
  ),

  // Generic themed text
  themedText: (theme) => (row, field) => (
    <span className={theme ? theme.textLight : 'text-gray-300'}>
      {row[field] || '—'}
    </span>
  ),
};