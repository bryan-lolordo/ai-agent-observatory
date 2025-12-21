/**
 * SimilarPanel - Universal similar items view for Layer 3
 * 
 * Shows:
 * - Group by selector (operation, template, issue, pattern)
 * - Aggregate stats
 * - Table of similar items (calls or patterns)
 * - Click routing to individual Layer 3 views
 */

import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';

export default function SimilarPanel({
  // Story context for routing
  storyId = 'latency',
  
  // Group options
  groupOptions = [
    { id: 'operation', label: 'Same Operation', filterFn: null },
    { id: 'template', label: 'Same Template', filterFn: (items) => items.filter(i => i.sameTemplate) },
    { id: 'issue', label: 'Same Issue', filterFn: (items) => items.filter(i => i.hasIssue) },
  ],
  defaultGroup = 'operation',
  
  // Data
  items = [],
  currentItemId = null,
  
  // Columns to display
  columns = [
    { key: 'id', label: 'ID', format: (v) => v?.substring(0, 8) + '...' },
    { key: 'timestamp', label: 'Timestamp' },
    { key: 'latency_ms', label: 'Latency', format: (v) => `${(v/1000).toFixed(2)}s` },
    { key: 'cost', label: 'Cost', format: (v) => `$${v?.toFixed(3)}` },
  ],
  
  // Aggregate stats to show
  aggregateStats = [], // [{ label, value, icon, color }]
  
  // Issue indicator
  issueKey = 'hasIssue',
  issueLabel = 'Same Issue',
  okLabel = 'OK',
  
  // Actions
  onSelectItem,
  onExport,
  
  // Theme
  theme = {},
}) {
  const navigate = useNavigate();
  const [activeGroup, setActiveGroup] = useState(defaultGroup);

  // Filter items based on active group
  const filteredItems = useMemo(() => {
    const activeOption = groupOptions.find(opt => opt.id === activeGroup);
    if (activeOption?.filterFn) {
      return activeOption.filterFn(items);
    }
    return items;
  }, [items, activeGroup, groupOptions]);

  // Calculate counts for each group
  const groupCounts = useMemo(() => {
    const counts = {};
    groupOptions.forEach(opt => {
      if (opt.filterFn) {
        counts[opt.id] = opt.filterFn(items).length;
      } else {
        counts[opt.id] = items.length;
      }
    });
    return counts;
  }, [items, groupOptions]);

  // Handle row click - navigate to that item's Layer 3
  const handleRowClick = (item) => {
    if (item.current || item.id === currentItemId) {
      return; // Don't navigate to current item
    }
    
    if (onSelectItem) {
      onSelectItem(item);
    } else {
      // Default navigation based on story
      const itemId = item.call_id || item.id;
      navigate(`/stories/${storyId}/calls/${itemId}`);
    }
  };

  // Calculate dynamic aggregate stats if not provided
  const displayStats = aggregateStats.length > 0 ? aggregateStats : [
    { 
      label: 'Total Calls', 
      value: filteredItems.length, 
      color: 'text-orange-400' 
    },
    { 
      label: 'With Issue', 
      value: filteredItems.filter(i => i[issueKey]).length, 
      color: 'text-red-400' 
    },
  ];

  return (
    <div className="space-y-6">
      {/* Group By Selector */}
      <div className="flex gap-2">
        {groupOptions.map(option => (
          <button
            key={option.id}
            onClick={() => setActiveGroup(option.id)}
            className={`px-4 py-2 rounded-lg text-sm transition-colors ${
              activeGroup === option.id
                ? 'bg-orange-600/30 text-orange-400 border border-orange-600'
                : 'bg-slate-800 text-slate-400 border border-slate-700 hover:text-slate-200'
            }`}
          >
            {option.label} ({groupCounts[option.id] || 0})
          </button>
        ))}
      </div>

      {/* Aggregate Stats */}
      {displayStats.length > 0 && (
        <div 
          className="grid gap-4"
          style={{ gridTemplateColumns: `repeat(${Math.min(displayStats.length, 4)}, 1fr)` }}
        >
          {displayStats.map((stat, idx) => (
            <div
              key={idx}
              className="bg-slate-800 border border-slate-700 rounded-lg p-4 text-center"
            >
              <div className={`text-2xl font-bold ${stat.color || 'text-orange-400'}`}>
                {stat.value}
              </div>
              <div className="text-xs text-slate-500">
                {stat.icon && <span className="mr-1">{stat.icon}</span>}
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Items Table */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
        <div className="flex justify-between items-center p-4 border-b border-slate-700">
          <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wide">
            {filteredItems.length} Similar Calls
          </h3>
          {onExport && (
            <button
              onClick={onExport}
              className="text-xs px-3 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded"
            >
              Export CSV
            </button>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-900">
              <tr className="text-left text-slate-500">
                {columns.map(col => (
                  <th key={col.key} className="px-4 py-3">
                    {col.label}
                  </th>
                ))}
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.length > 0 ? (
                filteredItems.map((item, idx) => {
                  const isCurrent = item.id === currentItemId || item.call_id === currentItemId || item.current;
                  const itemId = item.call_id || item.id;
                  
                  return (
                    <tr
                      key={itemId || idx}
                      onClick={() => handleRowClick(item)}
                      className={`border-t border-slate-700 transition-colors ${
                        isCurrent
                          ? 'bg-orange-900/20'
                          : 'hover:bg-slate-700/50 cursor-pointer'
                      }`}
                    >
                      {columns.map(col => (
                        <td key={col.key} className="px-4 py-3 text-slate-300">
                          {isCurrent && col.key === 'id' && (
                            <span className="text-orange-400 mr-2">●</span>
                          )}
                          {col.format ? col.format(item[col.key]) : item[col.key]}
                        </td>
                      ))}
                      <td className="px-4 py-3">
                        {item[issueKey] ? (
                          <span className="px-2 py-1 bg-red-900/50 text-red-300 rounded text-xs">
                            {issueLabel}
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-green-900/50 text-green-300 rounded text-xs">
                            {okLabel}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={columns.length + 1} className="px-4 py-8 text-center text-slate-500">
                    No items match the current filter
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="p-3 border-t border-slate-700 text-center text-sm text-slate-500">
          <span className="text-orange-400">●</span> = Current call • Click any row to view details
        </div>
      </div>
    </div>
  );
}