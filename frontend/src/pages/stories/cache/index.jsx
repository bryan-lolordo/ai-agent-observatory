/**
 * Layer 1: Cache Analysis - Overview
 * 
 * Shows operation-level cache opportunities with clickable KPIs.
 * Matches Latency story UI pattern.
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import KPICard from '../../../components/common/KPICard';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, formatCurrency, truncateText } from '../../../utils/formatters';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, PieChart, Pie } from 'recharts';

export default function Cache() {
  const navigate = useNavigate();
  const { data, loading, error } = useStory('cache');
  const theme = STORY_THEMES.cache;

  if (loading) return <StoryPageSkeleton />;
  
  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-900/20 border border-red-500 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-400 mb-2">Error Loading Data</h2>
            <p className="text-gray-300">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  // Extract data
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
    { name: 'Unique', value: Math.max(0, total_calls - duplicate_prompts), color: '#374151' },
  ].filter(d => d.value > 0);

  // Navigate to Layer 2
  const handleOperationClick = (row) => {
    navigate(`/stories/cache/operations/${encodeURIComponent(row.agent_name)}/${encodeURIComponent(row.operation_name)}`);
  };

  // Navigate to top offender
  const handleTopOffenderClick = () => {
    if (top_offender) {
      navigate(`/stories/cache/operations/${encodeURIComponent(top_offender.agent)}/${encodeURIComponent(top_offender.operation)}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Story Navigation */}
      <StoryNavTabs activeStory="cache" />

      <div className="max-w-7xl mx-auto p-8">
        
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <h1 className={`text-4xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-5xl">💾</span>
              Caching Strategy
            </h1>
            <div className={`px-4 py-2 rounded-full border-2 ${theme.border} ${theme.badgeBg}`}>
              <span className={`text-sm font-semibold ${theme.text}`}>
                {Math.round(health_score)}% Health
              </span>
            </div>
          </div>
          <p className="text-gray-400">
            Dashboard &gt; Caching Strategy
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <KPICard
            theme={theme}
            title="💰 Potential Savings"
            value={formatCurrency(potential_savings)}
            subtext="Per day from duplicates"
          />
          <KPICard
            theme={theme}
            title="🔄 Cacheable Calls"
            value={`${formatNumber(duplicate_prompts)} / ${formatNumber(total_calls)}`}
            subtext={`${total_calls ? Math.round((duplicate_prompts / total_calls) * 100) : 0}% cacheable`}
          />
          <KPICard
            theme={theme}
            title="📊 Cache Hit Rate"
            value={hit_rate_formatted}
            subtext="Current efficiency"
          />
          <KPICard
            theme={theme}
            title="⚠️ Top Offender"
            value={top_offender?.operation || '—'}
            subtext={top_offender ? `${top_offender.value_formatted} wasted` : 'No issues'}
          />
        </div>

        {/* Top Offender - Clickable */}
        {top_offender && (
          <div 
            onClick={handleTopOffenderClick}
            className={`mb-8 rounded-lg border-2 ${theme.border} bg-gradient-to-br ${theme.gradient} p-6 cursor-pointer hover:scale-[1.01] transition-all`}
          >
            <h3 className={`text-lg font-semibold ${theme.textLight} mb-3`}>
              🎯 Top Offender
            </h3>
            <div className={`text-2xl font-bold ${theme.text} mb-2 font-mono`}>
              {top_offender.agent}.{top_offender.operation}
            </div>
            <div className="flex gap-6 text-sm text-gray-300">
              <span>Wasted: {top_offender.value_formatted}</span>
              <span>{formatNumber(top_offender.call_count)} calls</span>
            </div>
            {top_offender.diagnosis && (
              <p className="text-sm text-gray-400 mt-2">
                💡 {top_offender.diagnosis}
              </p>
            )}
          </div>
        )}

        {/* Operations Table */}
        <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          <div className={`${theme.bgLight} p-4 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              📊 Operations by Cache Opportunity (click row to drill down)
            </h3>
          </div>
          
          <div className="overflow-x-auto overflow-y-auto max-h-80 story-scrollbar-thin cache">
            <table className="w-full text-sm">
              <thead className="bg-gray-800 sticky top-0">
                <tr className={`border-b-2 ${theme.border}`}>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Status</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Operation</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Agent</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Calls</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Cacheable</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Redundancy</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Waste</th>
                  <th className={`text-center py-3 px-4 ${theme.textLight}`}>Type</th>
                </tr>
              </thead>
              <tbody>
                {detail_table.length > 0 ? (
                  detail_table.map((row, idx) => (
                    <tr
                      key={idx}
                      onClick={() => handleOperationClick(row)}
                      className={`border-b border-gray-800 cursor-pointer transition-all hover:bg-gradient-to-r hover:${theme.gradient} hover:border-l-4 hover:${theme.border}`}
                    >
                      <td className="py-3 px-4 text-lg">{row.status}</td>
                      <td className={`py-3 px-4 font-mono ${theme.text} font-semibold`}>
                        {truncateText(row.operation_name || row.operation, 30)}
                      </td>
                      <td className="py-3 px-4 text-gray-400">
                        {row.agent_name || '—'}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        {formatNumber(row.total_calls)}
                      </td>
                      <td className={`py-3 px-4 text-right font-bold ${theme.text}`}>
                        {formatNumber(row.cacheable_count)}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-12 h-2 bg-gray-700 rounded-full overflow-hidden">
                            <div 
                              className={theme.bg}
                              style={{ width: `${Math.min(row.redundancy_pct * 100, 100)}%`, height: '100%' }}
                            />
                          </div>
                          <span className="text-gray-300 text-xs w-10 text-right">
                            {row.redundancy_formatted}
                          </span>
                        </div>
                      </td>
                      <td className={`py-3 px-4 text-right font-semibold ${theme.text}`}>
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
          <div className={`rounded-lg border-2 ${theme.border} bg-gray-900 p-6`}>
            <h3 className={`text-lg font-semibold ${theme.text} mb-6`}>
              💸 Savings by Operation
            </h3>
            
            {chart_data.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart 
                  data={chart_data.slice(0, 6)} 
                  layout="vertical"
                  margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    type="number" 
                    stroke="#9ca3af"
                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                    tickFormatter={(v) => `$${v.toFixed(2)}`}
                  />
                  <YAxis 
                    type="category" 
                    dataKey="name" 
                    stroke="#9ca3af"
                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                    width={100}
                    interval={0}
                  />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: '#111827',
                      border: `2px solid ${theme.color}`,
                      borderRadius: '8px',
                      color: '#f3f4f6'
                    }}
                    formatter={(value) => [`$${value.toFixed(4)}`, 'Wasted']}
                  />
                  <Bar dataKey="wasted_cost" fill={theme.color} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-500">
                No data to display
              </div>
            )}
          </div>

          {/* Pie Chart - Cacheable vs Unique */}
          <div className={`rounded-lg border-2 ${theme.border} bg-gray-900 p-6`}>
            <h3 className={`text-lg font-semibold ${theme.text} mb-6`}>
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
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: '#111827',
                      border: `2px solid ${theme.color}`,
                      borderRadius: '8px',
                      color: '#f3f4f6'
                    }}
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

        {/* Cache Types Legend */}
        <div className={`rounded-lg border-2 ${theme.border} bg-gray-900 p-6`}>
          <h4 className={`text-sm font-semibold ${theme.textLight} mb-4`}>CACHE TYPES</h4>
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
    </div>
  );
}