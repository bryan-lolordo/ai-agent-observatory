/**
 * Layer 1: Latency Analysis - Overview (2E Design)
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES, CHART_CONFIG, COLORS } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, truncateText } from '../../../utils/formatters';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';
import Layer1Table from '../../../components/stories/Layer1Table';

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
            <div className={`px-4 py-2 rounded-full border ${BASE_THEME.border.default} ${BASE_THEME.container.primary}`}>
              <span className={`text-sm font-semibold ${theme.text}`}>
                {Math.round(health_score)}% Health
              </span>
            </div>
          </div>
          <p className={`${BASE_THEME.text.muted} text-sm`}>
            Dashboard › Latency Analysis
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div
            onClick={() => navigate('/stories/latency/calls?filter=all')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Avg Latency</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{summary.avg_latency || '—'}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Across all operations</div>
          </div>

          <div
            onClick={() => navigate('/stories/latency/calls?filter=slow')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Slow Operations</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{summary.issue_count || 0}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>{summary.critical_count || 0} critical, {summary.warning_count || 0} warning</div>
          </div>

          <div
            onClick={() => navigate('/stories/latency/calls?filter=max')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Max Latency</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{maxLatency}s</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Worst single call</div>
          </div>

          <div
            onClick={() => navigate('/stories/latency/calls?filter=all')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Total Calls</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{formatNumber(summary.total_calls || 0)}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Last 7 days</div>
          </div>
        </div>

        {/* Top Offender */}
        {top_offender && (
          <div
            onClick={() => navigate(`/stories/latency/operations/${encodeURIComponent(top_offender.agent)}/${encodeURIComponent(top_offender.operation)}`)}
            className={`mb-8 rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} overflow-hidden cursor-pointer hover:${BASE_THEME.border.light} transition-all`}
          >
            <div className={`h-1 ${theme.bg}`} />
            <div className="p-5">
              <h3 className={`text-xs font-medium ${BASE_THEME.text.muted} uppercase tracking-wide mb-2`}>
                🎯 Top Offender
              </h3>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl font-bold text-purple-400">{top_offender.agent}</span>
                <span className={BASE_THEME.text.muted}>.</span>
                <span className={`text-xl font-bold ${theme.text} font-mono`}>{top_offender.operation}</span>
              </div>
              <div className={`flex gap-6 text-sm ${BASE_THEME.text.muted}`}>
                <span>Avg: <span className={BASE_THEME.text.primary}>{top_offender.value_formatted}</span></span>
                <span>Calls: <span className={BASE_THEME.text.primary}>{formatNumber(top_offender.call_count)}</span></span>
              </div>
              {top_offender.diagnosis && (
                <p className={`text-sm ${BASE_THEME.text.muted} mt-3`}>
                  💡 {top_offender.diagnosis}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Operations Table */}
        <div className="mb-8">
          <Layer1Table
            data={detail_table.map(row => ({
              ...row,
              operation: getOperationOnly(row),
              status_emoji: row.avg_latency_ms > 10000 ? '🔴' : row.is_slow ? '🟡' : '🟢',
            }))}
            theme={theme}
            storyId="latency"
            onRowClick={(row) => handleOperationClick(row.agent_name, row.operation)}
            columns={[
              { key: 'avg_latency_ms', label: 'Avg', width: '12%' },
              { key: 'max_latency_ms', label: 'Max', width: '12%' },
              { key: 'call_count', label: 'Calls', width: '11%' },
            ]}
            renderMetricCells={(row) => (
              <>
                <td className={`py-3 px-4 text-right font-semibold ${
                  row.avg_latency_ms > 10000 ? 'text-red-400' :
                  row.is_slow ? 'text-yellow-400' : 'text-green-400'
                }`}>
                  {((row.avg_latency_ms || 0) / 1000).toFixed(2)}s
                </td>
                <td className={`py-3 px-4 text-right ${BASE_THEME.text.muted}`}>
                  {((row.max_latency_ms || 0) / 1000).toFixed(2)}s
                </td>
                <td className={`py-3 px-4 text-right ${BASE_THEME.text.muted}`}>
                  {formatNumber(row.call_count)}
                </td>
              </>
            )}
          />
        </div>

        {/* Chart */}
        <div className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} overflow-hidden`}>
          <div className={`h-1 ${theme.bg}`} />
          <div className="p-6">
            <h3 className={`text-sm font-medium ${theme.text} uppercase tracking-wide mb-6`}>
              📊 Latency Distribution
            </h3>

            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 5, right: 30, left: 150, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray={CHART_CONFIG.grid.strokeDasharray} stroke={CHART_CONFIG.grid.stroke} />
                <XAxis
                  type="number"
                  stroke={CHART_CONFIG.axis.stroke}
                  tick={CHART_CONFIG.axis.tick}
                  axisLine={CHART_CONFIG.axis.axisLine}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  stroke={CHART_CONFIG.axis.stroke}
                  tick={CHART_CONFIG.axis.tick}
                  width={150}
                  axisLine={CHART_CONFIG.axis.axisLine}
                />
                <Tooltip
                  contentStyle={CHART_CONFIG.tooltip.contentStyle}
                />
                <ReferenceLine
                  x={LATENCY_THRESHOLD / 1000}
                  stroke={CHART_CONFIG.referenceLine.critical}
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
                      fill={entry.isSlow ? theme.color : COLORS.success}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>

            <p className={`text-xs ${BASE_THEME.text.muted} mt-4 text-center`}>
              Click any bar to investigate
            </p>
          </div>
        </div>

      </PageContainer>
    </div>
  );
}