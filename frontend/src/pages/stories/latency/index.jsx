/**
 * Layer 1: Latency Analysis - Overview (2E Design)
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, truncateText } from '../../../utils/formatters';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';

const LATENCY_THRESHOLD = 5000;

export default function Latency() {
  const navigate = useNavigate();
  const { data, loading, error } = useStory('latency');
  const theme = STORY_THEMES.latency;

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
    detail_table = []
  } = data || {};

  const maxLatencyMs = detail_table.length > 0 
    ? Math.max(...detail_table.map(r => r.max_latency_ms || 0))
    : 0;
  const maxLatency = (maxLatencyMs / 1000).toFixed(1);

  const getOperationOnly = (row) => {
    if (!row) return '';
    return row.operation.replace(row.agent_name + '.', '');
  };

  const chartData = detail_table.slice(0, 8).map(row => ({
    name: truncateText(row.operation, 30),
    fullOperation: row.operation,
    agent: row.agent_name,
    operationOnly: getOperationOnly(row),
    latency: (row.avg_latency_ms || 0) / 1000,
    latency_ms: row.avg_latency_ms,
    isSlow: row.is_slow,
  }));

  const handleOperationClick = (agent, operation) => {
    if (agent && operation) {
      navigate(`/stories/latency/operations/${encodeURIComponent(agent)}/${encodeURIComponent(operation)}`);
    }
  };

  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} ${BASE_THEME.text.primary}`}>
      <StoryNavTabs activeStory="latency" />

      <PageContainer>
        
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <h1 className={`text-3xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-4xl">{theme.emoji}</span>
              {theme.name}
            </h1>
            <div className="px-4 py-2 rounded-full border border-gray-700 bg-gray-900">
              <span className={`text-sm font-semibold ${theme.text}`}>
                {Math.round(health_score)}% Health
              </span>
            </div>
          </div>
          <p className="text-gray-500 text-sm">
            Dashboard › Latency Analysis
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div 
            onClick={() => navigate('/stories/latency/calls?filter=all')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Avg Latency</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{summary.avg_latency || '—'}</div>
            <div className="text-xs text-gray-500 mt-1">Across all operations</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/latency/calls?filter=slow')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Slow Operations</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{summary.issue_count || 0}</div>
            <div className="text-xs text-gray-500 mt-1">{summary.critical_count || 0} critical, {summary.warning_count || 0} warning</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/latency/calls?filter=max')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Max Latency</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{maxLatency}s</div>
            <div className="text-xs text-gray-500 mt-1">Worst single call</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/latency/calls?filter=all')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Total Calls</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{formatNumber(summary.total_calls || 0)}</div>
            <div className="text-xs text-gray-500 mt-1">Last 7 days</div>
          </div>
        </div>

        {/* Top Offender */}
        {top_offender && (
          <div 
            onClick={() => navigate(`/stories/latency/operations/${encodeURIComponent(top_offender.agent)}/${encodeURIComponent(top_offender.operation)}`)}
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
                <span>Avg: <span className="text-gray-200">{top_offender.value_formatted}</span></span>
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
            <h3 className="text-xs font-medium text-gray-300 uppercase tracking-wide">
              📊 Operations
              <span className="text-gray-500 normal-case ml-2 font-normal">Click row to drill down</span>
            </h3>
          </div>
          
          <div className="overflow-x-auto overflow-y-auto max-h-80">
            <table className="w-full text-sm" style={{ tableLayout: 'fixed' }}>
              <thead className="bg-gray-800/50">
                <tr className="border-b border-gray-700">
                  <th style={{ width: '5%' }} className="text-left py-3 px-4 text-gray-400 font-medium">Status</th>
                  <th style={{ width: '18%' }} className="text-left py-3 px-4 text-gray-400 font-medium">Agent</th>
                  <th style={{ width: '47%' }} className="text-left py-3 px-4 text-gray-400 font-medium">Operation</th>
                  <th style={{ width: '10%' }} className="text-right py-3 px-4 text-gray-400 font-medium">Avg</th>
                  <th style={{ width: '10%' }} className="text-right py-3 px-4 text-gray-400 font-medium">Max</th>
                  <th style={{ width: '10%' }} className="text-right py-3 px-4 text-gray-400 font-medium">Calls</th>
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
                      className="border-b border-gray-800 cursor-pointer hover:bg-gray-800/50 transition-colors"
                    >
                      <td className="py-3 px-4 text-lg">{statusEmoji}</td>
                      <td className="py-3 px-4 font-semibold text-purple-400">
                        {row.agent_name}
                      </td>
                      <td className={`py-3 px-4 font-mono ${theme.text}`}>
                        {truncateText(operationOnly, 30)}
                      </td>
                      <td className={`py-3 px-4 text-right font-semibold ${isCritical ? 'text-red-400' : isSlow ? 'text-yellow-400' : 'text-green-400'}`}>
                        {((row.avg_latency_ms || 0) / 1000).toFixed(2)}s
                      </td>
                      <td className="py-3 px-4 text-right text-gray-400">
                        {((row.max_latency_ms || 0) / 1000).toFixed(2)}s
                      </td>
                      <td className="py-3 px-4 text-right text-gray-400">
                        {formatNumber(row.call_count)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Chart */}
        <div className="rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
          <div className={`h-1 ${theme.bg}`} />
          <div className="p-6">
            <h3 className="text-xs font-medium text-gray-300 uppercase tracking-wide mb-6">
              📊 Latency Distribution
            </h3>
            
            <ResponsiveContainer width="100%" height={300}>
              <BarChart 
                data={chartData} 
                layout="vertical"
                margin={{ top: 5, right: 30, left: 150, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  type="number" 
                  stroke="#6b7280"
                  tick={{ fill: '#9ca3af', fontSize: 11 }}
                  axisLine={{ stroke: '#374151' }}
                />
                <YAxis 
                  type="category" 
                  dataKey="name" 
                  stroke="#6b7280"
                  tick={{ fill: '#9ca3af', fontSize: 11 }}
                  width={150}
                  axisLine={{ stroke: '#374151' }}
                />
                <Tooltip 
                  contentStyle={{
                    backgroundColor: '#1f2937',
                    border: '1px solid #374151',
                    borderRadius: '8px',
                    color: '#f3f4f6'
                  }}
                />
                <ReferenceLine 
                  x={LATENCY_THRESHOLD / 1000} 
                  stroke="#ef4444" 
                  strokeDasharray="3 3" 
                />
                <Bar 
                  dataKey="latency" 
                  radius={[0, 4, 4, 0]}
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
            
            <p className="text-xs text-gray-500 mt-4 text-center">
              Click any bar to investigate
            </p>
          </div>
        </div>

      </PageContainer>
    </div>
  );
}