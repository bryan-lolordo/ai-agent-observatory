/**
 * Layer 1: Latency Analysis - Overview
 * 
 * Shows operation-level latency metrics with clickable KPIs that navigate
 * to Layer 2 with appropriate quick filters active.
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import KPICard from '../../../components/common/KPICard';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, truncateText } from '../../../utils/formatters';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts';

const LATENCY_THRESHOLD = 5000; // 5 seconds in ms (for reference line only)

export default function Latency() {
  const navigate = useNavigate();
  const { data, loading, error } = useStory('latency');
  const theme = STORY_THEMES.latency;

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

  // Extract data - using backend structure
  const { 
    health_score = 0, 
    status = 'ok', 
    summary = {}, 
    top_offender = null,
    detail_table = []
  } = data || {};

  // Calculate max latency from detail_table
  const maxLatencyMs = detail_table.length > 0 
    ? Math.max(...detail_table.map(r => r.max_latency_ms || 0))
    : 0;
  const maxLatency = (maxLatencyMs / 1000).toFixed(1);

  // Get first row for KPI clicks
  const firstRow = detail_table[0];

  // Helper: Extract operation name from combined "Agent.Operation" string
  const getOperationOnly = (row) => {
    if (!row) return '';
    // row.operation is "ResumeMatching.deep_analyze_job"
    // row.agent_name is "ResumeMatching"
    // We need just "deep_analyze_job"
    return row.operation.replace(row.agent_name + '.', '');
  };

  // Prepare chart data (top 8 operations) - use backend's is_slow flag
  const chartData = detail_table.slice(0, 8).map(row => ({
    name: truncateText(row.operation, 30),
    fullOperation: row.operation,
    agent: row.agent_name,
    operationOnly: getOperationOnly(row),
    latency: (row.avg_latency_ms || 0) / 1000,
    latency_ms: row.avg_latency_ms,
    isSlow: row.is_slow,  // Use backend's calculated value
  }));

  // Navigate to Layer 2 with quick filter (using agent + operation)
  const navigateWithFilter = (agent, operation, filter) => {
    if (agent && operation) {
      navigate(`/stories/latency/operations/${encodeURIComponent(agent)}/${encodeURIComponent(operation)}?filter=${filter}`);
    }
  };

  // Navigate to Layer 2 (using agent + operation)
  const handleOperationClick = (agent, operation) => {
    if (agent && operation) {
      navigate(`/stories/latency/operations/${encodeURIComponent(agent)}/${encodeURIComponent(operation)}`);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Story Navigation */}
      <StoryNavTabs activeStory="latency" />

      <div className="max-w-7xl mx-auto p-8">
        
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <h1 className={`text-4xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-5xl">{theme.emoji}</span>
              {theme.name}
            </h1>
            <div className={`px-4 py-2 rounded-full border-2 ${theme.border} ${theme.badgeBg}`}>
              <span className={`text-sm font-semibold ${theme.text}`}>
                {Math.round(health_score)}% Health
              </span>
            </div>
          </div>
          <p className="text-gray-400">
            Dashboard &gt; Latency Analysis
          </p>
        </div>

        {/* KPI Cards - Clickable */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="cursor-default">
            <KPICard
              theme={theme}
              title="Avg Latency"
              value={summary.avg_latency || '—'}
              subtext="Across all operations"
            />
          </div>

          <div 
            onClick={() => firstRow && navigateWithFilter(firstRow.agent_name, getOperationOnly(firstRow), 'slow')} 
            className="cursor-pointer hover:scale-105 transition-transform"
          >
            <KPICard
              theme={theme}
              title="Slow Operations"
              value={summary.issue_count || 0}
              subtext={`${summary.critical_count || 0} critical, ${summary.warning_count || 0} warning`}
            />
          </div>

          <div 
            onClick={() => firstRow && navigateWithFilter(firstRow.agent_name, getOperationOnly(firstRow), 'max')} 
            className="cursor-pointer hover:scale-105 transition-transform"
          >
            <KPICard
              theme={theme}
              title="Max Latency"
              value={`${maxLatency}s`}
              subtext="Worst single call"
            />
          </div>

          <div 
            onClick={() => firstRow && navigateWithFilter(firstRow.agent_name, getOperationOnly(firstRow), 'all')} 
            className="cursor-pointer hover:scale-105 transition-transform"
          >
            <KPICard
              theme={theme}
              title="Total Calls"
              value={formatNumber(summary.total_calls || 0)}
              subtext="Last 7 days"
            />
          </div>
        </div>

        {/* Top Offender - Clickable */}
        {top_offender && (
          <div 
            onClick={() => navigateWithFilter(top_offender.agent, top_offender.operation, 'top-offender')}
            className={`mb-8 rounded-lg border-2 ${theme.border} bg-gradient-to-br ${theme.gradient} p-6 cursor-pointer hover:scale-[1.01] transition-all`}
          >
            <h3 className={`text-lg font-semibold ${theme.textLight} mb-3`}>
              🎯 Top Offender
            </h3>
            <div className={`text-2xl font-bold ${theme.text} mb-2 font-mono`}>
              {top_offender.agent}.{top_offender.operation}
            </div>
            <div className="flex gap-6 text-sm text-gray-300">
              <span>Avg: {top_offender.value_formatted}</span>
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
              📊 Operations (click row to drill down)
            </h3>
          </div>
          
          <div className="overflow-x-auto overflow-y-auto max-h-80 story-scrollbar-thin latency">
            <table className="w-full text-sm">
              <thead className="bg-gray-800 sticky top-0">
                <tr className={`border-b-2 ${theme.border}`}>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Status</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Operation</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Agent</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Avg</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Max</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Calls</th>
                </tr>
              </thead>
              <tbody>
                {detail_table.map((row, idx) => {
                  const isCritical = row.avg_latency_ms > 10000;
                  const isSlow = row.is_slow;
                  const statusEmoji = isCritical ? '🔴' : isSlow ? '🟡' : '🟢';
                  const operationOnly = getOperationOnly(row);

                  return (
                    <tr
                      key={idx}
                      onClick={() => handleOperationClick(row.agent_name, operationOnly)}
                      className={`border-b border-gray-800 cursor-pointer transition-all hover:bg-gradient-to-r hover:${theme.gradient} hover:border-l-4 hover:${theme.border}`}
                    >
                      <td className="py-3 px-4 text-lg">{statusEmoji}</td>
                      <td className={`py-3 px-4 font-mono ${theme.text} font-semibold`}>
                        {truncateText(row.operation, 40)}
                      </td>
                      <td className="py-3 px-4 text-gray-400">
                        {row.agent_name || '—'}
                      </td>
                      <td className={`py-3 px-4 text-right font-bold ${isCritical ? 'text-red-400' : isSlow ? 'text-yellow-400' : theme.text}`}>
                        {((row.avg_latency_ms || 0) / 1000).toFixed(1)}s
                      </td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        {((row.max_latency_ms || 0) / 1000).toFixed(1)}s
                      </td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        {formatNumber(row.call_count)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Latency Chart */}
        <div className={`rounded-lg border-2 ${theme.border} bg-gray-900 p-6`}>
          <h3 className={`text-lg font-semibold ${theme.text} mb-6`}>
            📊 Latency Distribution
          </h3>
          
          <ResponsiveContainer width="100%" height={400}>
            <BarChart 
              data={chartData} 
              layout="vertical"
              margin={{ top: 5, right: 30, left: 180, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis 
                type="number" 
                stroke="#9ca3af"
                tick={{ fill: '#9ca3af', fontSize: 11 }}
                label={{ value: 'Latency (seconds)', position: 'insideBottom', offset: -5, fill: '#9ca3af' }}
              />
              <YAxis 
                type="category" 
                dataKey="name" 
                stroke="#9ca3af"
                tick={{ fill: '#9ca3af', fontSize: 11 }}
                width={180}
                interval={0}
              />
              <Tooltip 
                contentStyle={{
                  backgroundColor: '#111827',
                  border: `2px solid ${theme.color}`,
                  borderRadius: '8px',
                  color: '#f3f4f6'
                }}
                cursor={{ fill: 'rgba(249, 115, 22, 0.1)' }}
              />
              <ReferenceLine 
                x={LATENCY_THRESHOLD / 1000} 
                stroke="#ef4444" 
                strokeDasharray="3 3" 
                label={{ value: '5s Threshold', fill: '#ef4444', fontSize: 11 }}
              />
              <Bar 
                dataKey="latency" 
                onClick={(data) => handleOperationClick(data.agent, data.operationOnly)}
                cursor="pointer"
              >
                {chartData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={entry.isSlow ? theme.color : '#22c55e'} 
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          
          <p className="text-xs text-gray-400 mt-4 text-center">
            Click any bar to investigate that operation
          </p>
        </div>

      </div>
    </div>
  );
}