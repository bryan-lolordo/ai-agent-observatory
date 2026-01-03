/**
 * Optimization Queue - Central dashboard for all fix opportunities
 *
 * Shows all Layer 3 issues across all stories in one filterable table.
 * Click any row to go directly to that item's Layer 3 view.
 */

import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTimeRange } from '../context/TimeRangeContext';
import { BASE_THEME } from '../utils/themeUtils';
import PageContainer from '../components/layout/PageContainer';
import StoryNavTabs from '../components/stories/StoryNavTabs';

// Story configuration
const STORIES = [
  { id: 'latency', label: 'Latency', icon: '🌐', color: '#f97316' },
  { id: 'cache', label: 'Cache', icon: '💾', color: '#ec4899' },
  { id: 'cost', label: 'Cost', icon: '💰', color: '#10b981' },
  { id: 'quality', label: 'Quality', icon: '📊', color: '#8b5cf6' },
  { id: 'routing', label: 'Routing', icon: '🔀', color: '#3b82f6' },
  { id: 'token', label: 'Token', icon: '🔢', color: '#f59e0b' },
];

// Quick filter presets
const QUICK_FILTERS = [
  { id: 'all', label: 'All', filter: () => true },
  { id: 'quick_wins', label: '⚡ Quick Wins', filter: (item) => item.effort === 'Low' && parseFloat(item.impact.replace('$', '')) > 0.05 },
  { id: 'high_impact', label: '📈 High Impact', filter: (item) => parseFloat(item.impact.replace('$', '')) > 0.10 },
  { id: 'low_effort', label: '🟢 Low Effort', filter: (item) => item.effort === 'Low' },
];

export default function OptimizationQueue() {
  const navigate = useNavigate();
  const { timeRange } = useTimeRange();
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeStoryFilter, setActiveStoryFilter] = useState('all');
  const [activeQuickFilter, setActiveQuickFilter] = useState('all');
  const [sortConfig, setSortConfig] = useState({ key: 'impact', direction: 'desc' });

  // Fetch opportunities from all stories
  useEffect(() => {
    async function fetchOpportunities() {
      setLoading(true);
      try {
        const params = new URLSearchParams({ days: String(timeRange), limit: '100' });
        const response = await fetch(`/api/optimization/opportunities?${params}`);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        setOpportunities(data.opportunities || []);
      } catch (err) {
        console.error('Failed to load opportunities:', err);
        // Fallback to empty state
        setOpportunities([]);
      } finally {
        setLoading(false);
      }
    }
    fetchOpportunities();
  }, [timeRange]);

  // Filter and sort opportunities
  const processedOpportunities = useMemo(() => {
    let result = [...opportunities];

    // Story filter
    if (activeStoryFilter !== 'all') {
      result = result.filter(opp => opp.storyId === activeStoryFilter);
    }

    // Quick filter
    const quickFilter = QUICK_FILTERS.find(f => f.id === activeQuickFilter);
    if (quickFilter && quickFilter.id !== 'all') {
      result = result.filter(quickFilter.filter);
    }

    // Sort
    if (sortConfig.key) {
      result.sort((a, b) => {
        let aVal = a[sortConfig.key];
        let bVal = b[sortConfig.key];
        
        // Handle impact as number
        if (sortConfig.key === 'impact') {
          aVal = a.impactValue;
          bVal = b.impactValue;
        }
        
        // Handle callCount as number
        if (sortConfig.key === 'callCount') {
          aVal = a.callCount || 1;
          bVal = b.callCount || 1;
        }
        
        // Handle effort as priority
        if (sortConfig.key === 'effort') {
          const effortOrder = { Low: 1, Medium: 2, High: 3 };
          aVal = effortOrder[aVal] || 99;
          bVal = effortOrder[bVal] || 99;
        }

        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }

    return result;
  }, [opportunities, activeStoryFilter, activeQuickFilter, sortConfig]);

  // Handle sort click
  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc',
    }));
  };

  // Handle row click - navigate to appropriate Layer 3
  const handleRowClick = (opp) => {
    if (opp.storyId === 'cache' && opp.groupId) {
      navigate(`/stories/cache/operations/${encodeURIComponent(opp.agent)}/${encodeURIComponent(opp.operation)}/groups/${opp.groupId}`);
    } else {
      navigate(`/stories/${opp.storyId}/calls/${opp.callId}`);
    }
  };

  // Calculate summary stats
  const stats = useMemo(() => {
    const total = processedOpportunities.length;
    const totalSavings = processedOpportunities.reduce((sum, opp) => sum + opp.impactValue, 0);
    const quickWins = processedOpportunities.filter(opp => opp.effort === 'Low').length;
    const byStory = STORIES.map(story => ({
      ...story,
      count: processedOpportunities.filter(opp => opp.storyId === story.id).length,
    })).filter(s => s.count > 0);

    return { total, totalSavings, quickWins, byStory };
  }, [processedOpportunities]);

  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} ${BASE_THEME.text.primary}`}>
      <StoryNavTabs activeStory="queue" />

      <PageContainer className="p-6">

        {/* Header */}
        <div className="mb-8">
          <h1 className={`text-3xl font-bold text-blue-400 flex items-center gap-3`}>
            <span className="text-4xl">📋</span>
            Optimization Queue
          </h1>
          <p className={`${BASE_THEME.text.muted} mt-2`}>
            All optimization opportunities across your LLM operations
          </p>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-4 text-center`}>
            <div className="text-3xl font-bold text-orange-400">{stats.total}</div>
            <div className={`text-sm ${BASE_THEME.text.muted}`}>Total Opportunities</div>
          </div>
          <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-4 text-center`}>
            <div className="text-3xl font-bold text-green-400">${stats.totalSavings.toFixed(2)}</div>
            <div className={`text-sm ${BASE_THEME.text.muted}`}>Potential Savings</div>
          </div>
          <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-4 text-center`}>
            <div className="text-3xl font-bold text-emerald-400">{stats.quickWins}</div>
            <div className={`text-sm ${BASE_THEME.text.muted}`}>Quick Wins (Low Effort)</div>
          </div>
          <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-4`}>
            <div className={`text-sm ${BASE_THEME.text.muted} mb-2`}>By Story</div>
            <div className="flex flex-wrap gap-2">
              {stats.byStory.map(story => (
                <span
                  key={story.id}
                  className="px-2 py-1 rounded text-xs"
                  style={{ backgroundColor: `${story.color}20`, color: story.color }}
                >
                  {story.icon} {story.count}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-4 mb-6`}>
          <div className="flex flex-wrap gap-6">
            {/* Story Filter */}
            <div>
              <div className={`text-xs ${BASE_THEME.text.muted} uppercase mb-2`}>Story</div>
              <div className="flex gap-2">
                <button
                  onClick={() => setActiveStoryFilter('all')}
                  className={`px-3 py-1.5 rounded text-sm transition-colors ${
                    activeStoryFilter === 'all'
                      ? 'bg-orange-600/30 text-orange-400 border border-orange-600'
                      : `${BASE_THEME.container.tertiary} ${BASE_THEME.text.muted} border ${BASE_THEME.border.default} hover:${BASE_THEME.text.primary}`
                  }`}
                >
                  All
                </button>
                {STORIES.map(story => (
                  <button
                    key={story.id}
                    onClick={() => setActiveStoryFilter(story.id)}
                    className={`px-3 py-1.5 rounded text-sm transition-colors ${
                      activeStoryFilter === story.id
                        ? 'border'
                        : `${BASE_THEME.container.tertiary} ${BASE_THEME.text.muted} border ${BASE_THEME.border.default} hover:${BASE_THEME.text.primary}`
                    }`}
                    style={activeStoryFilter === story.id ? {
                      backgroundColor: `${story.color}20`,
                      color: story.color,
                      borderColor: story.color,
                    } : {}}
                  >
                    {story.icon} {story.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Quick Filters */}
            <div>
              <div className={`text-xs ${BASE_THEME.text.muted} uppercase mb-2`}>Quick Filters</div>
              <div className="flex gap-2">
                {QUICK_FILTERS.map(filter => (
                  <button
                    key={filter.id}
                    onClick={() => setActiveQuickFilter(filter.id)}
                    className={`px-3 py-1.5 rounded text-sm transition-colors ${
                      activeQuickFilter === filter.id
                        ? 'bg-orange-600/30 text-orange-400 border border-orange-600'
                        : `${BASE_THEME.container.tertiary} ${BASE_THEME.text.muted} border ${BASE_THEME.border.default} hover:${BASE_THEME.text.primary}`
                    }`}
                  >
                    {filter.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Opportunities Table */}
        <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg overflow-hidden`}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className={BASE_THEME.container.primary}>
                <tr className={`text-left ${BASE_THEME.text.muted}`}>
                  <th className="px-4 py-3">Story</th>
                  <th className="px-4 py-3">Agent</th>
                  <th className="px-4 py-3">Operation</th>
                  <th className="px-4 py-3">Issue</th>
                  <th 
                    className="px-4 py-3 cursor-pointer hover:text-gray-300"
                    onClick={() => handleSort('callCount')}
                  >
                    Calls {sortConfig.key === 'callCount' && (sortConfig.direction === 'desc' ? '↓' : '↑')}
                  </th>
                  <th 
                    className="px-4 py-3 cursor-pointer hover:text-gray-300"
                    onClick={() => handleSort('impact')}
                  >
                    Impact {sortConfig.key === 'impact' && (sortConfig.direction === 'desc' ? '↓' : '↑')}
                  </th>
                  <th 
                    className="px-4 py-3 cursor-pointer hover:text-gray-300"
                    onClick={() => handleSort('effort')}
                  >
                    Effort {sortConfig.key === 'effort' && (sortConfig.direction === 'desc' ? '↓' : '↑')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  Array.from({ length: 5 }).map((_, idx) => (
                    <tr key={idx} className={`border-t ${BASE_THEME.border.default}`}>
                      {Array.from({ length: 7 }).map((_, colIdx) => (
                        <td key={colIdx} className="px-4 py-3">
                          <div className={`h-4 ${BASE_THEME.container.tertiary} rounded animate-pulse`} />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : processedOpportunities.length > 0 ? (
                  processedOpportunities.map(opp => {
                    const story = STORIES.find(s => s.id === opp.storyId);
                    return (
                      <tr
                        key={opp.id}
                        onClick={() => handleRowClick(opp)}
                        className={`border-t ${BASE_THEME.border.default} hover:${BASE_THEME.container.tertiary}/50 cursor-pointer transition-colors`}
                      >
                        <td className="px-4 py-3">
                          <span
                            className="px-2 py-1 rounded text-xs"
                            style={{ backgroundColor: `${story?.color}20`, color: story?.color }}
                          >
                            {opp.storyIcon}
                          </span>
                        </td>
                        <td className={`px-4 py-3 ${BASE_THEME.text.secondary}`}>{opp.agent}</td>
                        <td className={`px-4 py-3 ${BASE_THEME.text.muted} font-mono`}>{opp.operation}</td>
                        <td className={`px-4 py-3 ${BASE_THEME.text.secondary}`}>{opp.issue}</td>
                        <td className={`px-4 py-3 ${BASE_THEME.text.muted}`}>{opp.callCount || 1}</td>
                        <td className="px-4 py-3">
                          <span className={opp.impactValue > 0.1 ? 'text-green-400 font-medium' : BASE_THEME.text.muted}>
                            {opp.impact}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded text-xs ${
                            opp.effort === 'Low' ? 'bg-green-900/50 text-green-400' :
                            opp.effort === 'Medium' ? 'bg-yellow-900/50 text-yellow-400' :
                            'bg-red-900/50 text-red-400'
                          }`}>
                            {opp.effort}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={7} className={`px-4 py-12 text-center ${BASE_THEME.text.muted}`}>
                      No opportunities match the current filters
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className={`px-4 py-3 border-t ${BASE_THEME.border.default} text-sm ${BASE_THEME.text.muted} flex justify-between`}>
            <span>
              Showing {processedOpportunities.length} of {opportunities.length} opportunities
            </span>
            <span>Click any row to view details and fix</span>
          </div>
        </div>

      </PageContainer>
    </div>
  );
}