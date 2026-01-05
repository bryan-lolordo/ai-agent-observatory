/**
 * Layer 1: Cache Analysis - Overview (2E Design)
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES, CHART_CONFIG, COLORS } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, formatCurrency, truncateText } from '../../../utils/formatters';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, PieChart, Pie } from 'recharts';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';

export default function Cache() {
  const navigate = useNavigate();
  const { data, loading, error } = useStory('cache');
  const theme = STORY_THEMES.cache;

  if (loading) return <StoryPageSkeleton />;
  
  if (error) {
    return (
      <div className={`min-h-screen ${BASE_THEME.container.tertiary} p-8`}>
        <PageContainer>
          <div className={`${BASE_THEME.status.error.bg} border ${BASE_THEME.status.error.border} rounded-lg p-6`}>
            <h2 className={`text-xl font-bold ${BASE_THEME.status.error.textBold} mb-2`}>Error Loading Data</h2>
            <p className={BASE_THEME.text.secondary}>{error}</p>
          </div>
        </PageContainer>
      </div>
    );
  }

  const { 
    health_score = 0, 
    summary = {}, 
    top_offender = null,
    detail_table = [],
    chart_data = [],
  } = data || {};

  const {
    total_calls = 0,
    potential_savings = 0,
    duplicate_prompts = 0,
    hit_rate = 0,
    hit_rate_formatted = '0%',
  } = summary;

  // Prepare pie chart data
  const pieData = [
    { name: 'Cacheable', value: duplicate_prompts, color: theme.color },
    { name: 'Unique', value: Math.max(0, total_calls - duplicate_prompts), color: COLORS.border },
  ].filter(d => d.value > 0);

  // Navigation handlers
  const handleOperationClick = (row) => {
    navigate(`/stories/cache/calls?operation=${encodeURIComponent(row.operation_name)}&agent=${encodeURIComponent(row.agent_name)}`);
  };

  const handleTopOffenderClick = () => {
    if (top_offender) {
      navigate(`/stories/cache/calls?operation=${encodeURIComponent(top_offender.operation)}&agent=${encodeURIComponent(top_offender.agent)}`);
    }
  };

  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} ${BASE_THEME.text.primary}`}>
      <StoryNavTabs activeStory="cache" />

      <PageContainer>
        
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <h1 className={`text-3xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-4xl">💾</span>
              Caching Strategy
            </h1>
            <div className="px-4 py-2 rounded-full border border-gray-700 bg-gray-900">
              <span className={`text-sm font-semibold ${theme.text}`}>
                {Math.round(health_score)}% Health
              </span>
            </div>
          </div>
          <p className="text-gray-500 text-sm">
            Dashboard › Caching Strategy
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {/* Potential Savings - No click (summary stat) */}
          <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Potential Savings</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{formatCurrency(potential_savings)}</div>
            <div className="text-xs text-gray-500 mt-1">Per day from duplicates</div>
          </div>
          
          {/* Cacheable Calls - Clickable → Layer 2 All Types */}
          <div 
            onClick={() => navigate('/stories/cache/calls')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Cacheable Calls</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{formatNumber(duplicate_prompts)} / {formatNumber(total_calls)}</div>
            <div className="text-xs text-gray-500 mt-1">{total_calls ? Math.round((duplicate_prompts / total_calls) * 100) : 0}% cacheable</div>
          </div>
          
          {/* Cache Hit Rate - No click (summary stat) */}
          <div className="rounded-lg border border-gray-700 bg-gray-900 p-4">
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Cache Hit Rate</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{hit_rate_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">Current efficiency</div>
          </div>
          
          {/* Top Offender - Clickable → OperationDetail */}
          <div 
            onClick={handleTopOffenderClick}
            className={`rounded-lg border border-gray-700 bg-gray-900 p-4 ${top_offender ? 'cursor-pointer hover:bg-gray-800/50 transition-colors' : ''}`}
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Top Offender</div>
            <div className={`text-2xl font-bold ${theme.text} truncate`}>{top_offender?.operation || '—'}</div>
            <div className="text-xs text-gray-500 mt-1">{top_offender ? `${top_offender.value_formatted} wasted` : 'No issues'}</div>
          </div>
        </div>

        {/* Top Offender Card */}
        {top_offender && (
          <div 
            onClick={handleTopOffenderClick}
            className="mb-8 rounded-lg border border-gray-700 bg-gray-900 overflow-hidden cursor-pointer hover:border-gray-600 transition-all"
          >
            <div className={`h-1 ${theme.bg}`} />
            <div className="p-5">
              <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">
                🎯 Top Offender
              </h3>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl font-bold text-purple-400">{top_offender.agent}</span>
                <span className="text-gray-500">.</span>
                <span className={`text-xl font-bold ${theme.text} font-mono`}>{top_offender.operation}</span>
              </div>
              <div className="flex gap-6 text-sm text-gray-400">
                <span>Wasted: <span className="text-red-400">{top_offender.value_formatted}</span></span>
                <span>Calls: <span className="text-gray-200">{formatNumber(top_offender.call_count)}</span></span>
              </div>
              {top_offender.diagnosis && (
                <p className="text-sm text-gray-500 mt-3">
                  💡 {top_offender.diagnosis}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Operations Table */}
        <div className="mb-8 rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
          <div className={`h-1 ${theme.bg}`} />
          <div className="p-4 border-b border-gray-700">
            <h3 className={`text-sm font-medium ${theme.text} uppercase tracking-wide`}>
              📊 Operations by Cache Opportunity
              <span className="text-gray-500 normal-case ml-2 font-normal">Click row to drill down</span>
            </h3>
          </div>
          
          <div className="overflow-x-auto overflow-y-auto max-h-80">
            <table className="w-full text-sm" style={{ tableLayout: 'fixed' }}>
              <thead className="bg-gray-800/50">
                <tr className="border-b border-gray-700">
                  <th style={{ width: '4%' }} className="text-left py-3 px-4 text-gray-400 font-medium">Status</th>
                  <th style={{ width: '14%' }} className="text-left py-3 px-4 text-gray-400 font-medium">Agent</th>
                  <th style={{ width: '30%' }} className="text-left py-3 px-4 text-gray-400 font-medium">Operation</th>
                  <th style={{ width: '10%' }} className="text-right py-3 px-4 text-gray-400 font-medium">Calls</th>
                  <th style={{ width: '10%' }} className="text-right py-3 px-4 text-gray-400 font-medium">Cacheable</th>
                  <th style={{ width: '14%' }} className="text-right py-3 px-4 text-gray-400 font-medium">Redundancy</th>
                  <th style={{ width: '10%' }} className="text-right py-3 px-4 text-gray-400 font-medium">Waste</th>
                  <th style={{ width: '8%' }} className="text-center py-3 px-4 text-gray-400 font-medium">Type</th>
                </tr>
              </thead>
              <tbody>
                {detail_table.length > 0 ? (
                  detail_table.map((row, idx) => (
                    <tr
                      key={`${row.agent_name}-${row.operation_name}-${idx}`}
                      onClick={() => handleOperationClick(row)}
                      className="border-b border-gray-800 cursor-pointer hover:bg-gray-800/50 transition-colors"
                    >
                      <td className="py-3 px-4">
                        <span className={`inline-block w-3 h-3 rounded-full ${
                          (row.redundancy_pct || 0) > 0.5 ? 'bg-red-500' : 
                          (row.redundancy_pct || 0) > 0.2 ? 'bg-yellow-500' : 'bg-green-500'
                        }`} />
                      </td>
                      <td className="py-3 px-4 text-purple-400 font-medium">
                        {row.agent_name}
                      </td>
                      <td className={`py-3 px-4 font-mono ${theme.text}`}>
                        {truncateText(row.operation_name, 30)}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        {formatNumber(row.total_calls)}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        {formatNumber(row.cacheable_count)}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-12 h-2 bg-gray-700 rounded-full overflow-hidden">
                            <div 
                              className={theme.bg}
                              style={{ width: `${Math.min((row.redundancy_pct || 0) * 100, 100)}%`, height: '100%' }}
                            />
                          </div>
                          <span className="text-gray-300 text-xs w-10 text-right">
                            {row.redundancy_formatted}
                          </span>
                        </div>
                      </td>
                      <td className={`py-3 px-4 text-right font-semibold text-red-400`}>
                        {row.wasted_cost_formatted}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="text-lg" title={row.top_type_name}>
                          {row.top_type_emoji}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-gray-500">
                      No cache opportunities found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          
          {/* Bar Chart - Savings by Operation */}
          <div className="rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
            <div className={`h-1 ${theme.bg}`} />
            <div className="p-6">
              <h3 className={`text-sm font-medium ${theme.text} uppercase tracking-wide mb-6`}>
                💸 Savings by Operation
              </h3>
              
              {chart_data.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart
                    data={chart_data.slice(0, 6)}
                    layout="vertical"
                    margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray={CHART_CONFIG.grid.strokeDasharray} stroke={CHART_CONFIG.grid.stroke} />
                    <XAxis
                      type="number"
                      stroke={CHART_CONFIG.axis.stroke}
                      tick={CHART_CONFIG.axis.tick}
                      tickFormatter={(v) => `$${v.toFixed(2)}`}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      stroke={CHART_CONFIG.axis.stroke}
                      tick={CHART_CONFIG.axis.tick}
                      width={100}
                      interval={0}
                    />
                    <Tooltip
                      contentStyle={CHART_CONFIG.tooltip.contentStyle}
                      formatter={(value) => [`$${value.toFixed(4)}`, 'Wasted']}
                    />
                    <Bar
                      dataKey="wasted_cost"
                      fill={theme.color}
                      radius={[0, 4, 4, 0]}
                      cursor="pointer"
                      onClick={(data) => {
                        if (data && data.name) {
                          // Find the operation in detail_table to get agent
                          const op = detail_table.find(d => d.operation_name === data.name);
                          if (op) {
                            navigate(`/stories/cache/calls?operation=${encodeURIComponent(op.operation_name)}&agent=${encodeURIComponent(op.agent_name)}`);
                          } else {
                            navigate(`/stories/cache/calls?operation=${encodeURIComponent(data.name)}`);
                          }
                        }
                      }}
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-64 flex items-center justify-center text-gray-500">
                  No data to display
                </div>
              )}
            </div>
          </div>

          {/* Pie Chart - Cacheable vs Unique */}
          <div className="rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
            <div className={`h-1 ${theme.bg}`} />
            <div className="p-6">
              <h3 className={`text-sm font-medium ${theme.text} uppercase tracking-wide mb-6`}>
                📊 Cacheable vs Unique Calls
              </h3>
              
              {pieData.length > 0 && pieData.some(d => d.value > 0) ? (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      labelLine={false}
                      cursor="pointer"
                      onClick={(data) => {
                        if (data && data.name === 'Cacheable') {
                          navigate('/stories/cache/calls');
                        }
                      }}
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={CHART_CONFIG.tooltip.contentStyle}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-64 flex items-center justify-center text-gray-500">
                  No data to display
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Cache Types Legend */}
        <div className="rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
          <div className={`h-1 ${theme.bg}`} />
          <div className="p-6">
            <h4 className={`text-sm font-medium ${theme.text} uppercase tracking-wide mb-4`}>Cache Types</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="flex items-center gap-3">
                <span className="text-2xl">🎯</span>
                <div>
                  <div className={`font-medium ${theme.text}`}>Exact Match</div>
                  <div className="text-xs text-gray-500">Identical prompts • Easy fix</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-2xl">📌</span>
                <div>
                  <div className={`font-medium ${theme.text}`}>Stable/Prefix</div>
                  <div className="text-xs text-gray-500">Large system prompt • Easy fix</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-2xl">💎</span>
                <div>
                  <div className={`font-medium ${theme.text}`}>High-Value</div>
                  <div className="text-xs text-gray-500">Expensive/slow • Medium fix</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-2xl">🧠</span>
                <div>
                  <div className={`font-medium ${theme.text}`}>Semantic</div>
                  <div className="text-xs text-gray-500">Similar meaning • Advanced</div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </PageContainer>
    </div>
  );
}