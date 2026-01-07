/**
 * SimilarPanel - Universal similar items view for Layer 3
 *
 * Shows:
 * - Group by selector (operation, template, issue, pattern)
 * - Aggregate stats
 * - Table of similar items (calls or patterns)
 * - Click routing to individual Layer 3 views
 *
 * UPDATED: Uses theme system - no hardcoded colors!
 */

import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { BASE_THEME } from '../../../utils/themeUtils';
import { STORY_THEMES } from '../../../config/theme';

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
  theme = STORY_THEMES.latency,
}) {
  const navigate = useNavigate();
  const [activeGroup, setActiveGroup] = useState(defaultGroup);

  // Use passed theme or default to latency theme
  const accentTheme = theme || STORY_THEMES.latency;

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
      color: accentTheme.text
    },
    {
      label: 'With Issue',
      value: filteredItems.filter(i => i[issueKey]).length,
      color: BASE_THEME.status.error.text
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
                ? `${accentTheme.bgLight} ${accentTheme.text} border ${accentTheme.border}`
                : `${BASE_THEME.container.secondary} ${BASE_THEME.text.secondary} border ${BASE_THEME.border.default} hover:${BASE_THEME.text.primary}`
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
              className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-4 text-center`}
            >
              <div className={`text-2xl font-bold ${stat.color || accentTheme.text}`}>
                {stat.value}
              </div>
              <div className={`text-xs ${BASE_THEME.text.muted}`}>
                {stat.icon && <span className="mr-1">{stat.icon}</span>}
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Items Table */}
      <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg overflow-hidden`}>
        <div className={`flex justify-between items-center p-4 border-b ${BASE_THEME.border.default}`}>
          <h3 className={`text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide`}>
            {filteredItems.length} Similar Calls
          </h3>
          {onExport && (
            <button
              onClick={onExport}
              className={`text-xs px-3 py-1 ${BASE_THEME.container.primary} hover:${BASE_THEME.container.tertiary} ${BASE_THEME.text.secondary} rounded`}
            >
              Export CSV
            </button>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className={BASE_THEME.container.primary}>
              <tr className={`text-left ${BASE_THEME.text.muted}`}>
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
                      className={`border-t ${BASE_THEME.border.default} transition-colors ${
                        isCurrent
                          ? accentTheme.bgSubtle
                          : `${BASE_THEME.state.hover} cursor-pointer`
                      }`}
                    >
                      {columns.map(col => (
                        <td key={col.key} className={`px-4 py-3 ${BASE_THEME.text.secondary}`}>
                          {isCurrent && col.key === 'id' && (
                            <span className={`${accentTheme.text} mr-2`}>●</span>
                          )}
                          {col.format ? col.format(item[col.key]) : item[col.key]}
                        </td>
                      ))}
                      <td className="px-4 py-3">
                        {item[issueKey] ? (
                          <span className={`px-2 py-1 ${BASE_THEME.status.error.bg} ${BASE_THEME.status.error.text} rounded text-xs`}>
                            {issueLabel}
                          </span>
                        ) : (
                          <span className={`px-2 py-1 ${BASE_THEME.status.success.bg} ${BASE_THEME.status.success.text} rounded text-xs`}>
                            {okLabel}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={columns.length + 1} className={`px-4 py-8 text-center ${BASE_THEME.text.muted}`}>
                    No items match the current filter
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className={`p-3 border-t ${BASE_THEME.border.default} text-center text-sm ${BASE_THEME.text.muted}`}>
          <span className={accentTheme.text}>●</span> = Current call • Click any row to view details
        </div>
      </div>
    </div>
  );
}
