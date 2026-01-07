/**
 * Layer 1: Model Routing - Overview (2E Design)
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES, CHART_CONFIG } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber } from '../../../utils/formatters';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine, ZAxis } from 'recharts';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';
import Layer1Table from '../../../components/stories/Layer1Table';

export default function Routing() {
  const navigate = useNavigate();
  const { data, loading, error } = useStory('routing');
  const theme = STORY_THEMES.routing;

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
    current_model = '—',
    current_model_pct = 0,
    downgrade_count = 0,
    upgrade_count = 0,
    potential_savings_formatted = '$0.00',
  } = summary;

  const opportunityColors = CHART_CONFIG.opportunityColors;

  const handleOperationClick = (row) => {
    navigate(`/stories/routing/calls?agent=${encodeURIComponent(row.agent_name)}&operation=${encodeURIComponent(row.operation_name)}`);
};

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
          <p className="font-semibold text-purple-400 mb-1">{data.name}</p>
          <p className="text-sm text-gray-300">Complexity: {data.complexity?.toFixed(2)}</p>
          <p className="text-sm text-gray-300">Quality: {data.quality?.toFixed(1)}/10</p>
          <p className="text-sm text-gray-300">Calls: {formatNumber(data.call_count)}</p>
          <p className={`text-sm font-semibold ${
            data.opportunity === 'upgrade' ? 'text-red-400' :
            data.opportunity === 'downgrade' ? 'text-blue-400' :
            'text-green-400'
          }`}>
            {data.opportunity === 'upgrade' ? '↑ Needs Upgrade' :
             data.opportunity === 'downgrade' ? '↓ Can Downgrade' :
             '✓ Optimal'}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} ${BASE_THEME.text.primary}`}>
      <StoryNavTabs activeStory="routing" />

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
            Dashboard › Model Routing
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div
            onClick={() => navigate('/stories/routing/calls?filter=all')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Current Model</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{current_model}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>{current_model_pct}% of {formatNumber(total_calls)} calls</div>
          </div>

          <div
            onClick={() => navigate('/stories/routing/calls?filter=downgrade')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Downgrade Candidates</div>
            <div className="text-2xl font-bold text-blue-400">{downgrade_count}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Can use cheaper model</div>
          </div>

          <div
            onClick={() => navigate('/stories/routing/calls?filter=upgrade')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Upgrade Candidates</div>
            <div className="text-2xl font-bold text-red-400">{upgrade_count}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Need better model</div>
          </div>

          <div
            onClick={() => navigate('/stories/routing/calls?filter=all')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Potential Savings</div>
            <div className="text-2xl font-bold text-green-400">{potential_savings_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>From routing optimization</div>
          </div>
        </div>

        {/* Top Offender */}
        {top_offender && (
          <div
            onClick={() => navigate(`/stories/routing/operations/${encodeURIComponent(top_offender.agent)}/${encodeURIComponent(top_offender.operation)}`)}
            className={`mb-8 rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} overflow-hidden cursor-pointer hover:${BASE_THEME.border.light} transition-all`}
          >
            <div className={`h-1 ${theme.bg}`} />
            <div className="p-5">
              <h3 className={`text-xs font-medium ${BASE_THEME.text.muted} uppercase tracking-wide mb-2`}>
                🎯 Top Routing Opportunity
              </h3>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl font-bold text-purple-400">{top_offender.agent}</span>
                <span className={BASE_THEME.text.muted}>.</span>
                <span className={`text-xl font-bold ${theme.text} font-mono`}>{top_offender.operation}</span>
              </div>
              <div className={`flex gap-6 text-sm ${BASE_THEME.text.muted}`}>
                <span>{top_offender.opportunity_emoji} {top_offender.opportunity?.toUpperCase()}</span>
                <span>Complexity: <span className={BASE_THEME.text.primary}>{top_offender.complexity_formatted}</span></span>
                <span>Quality: <span className={BASE_THEME.text.primary}>{top_offender.quality_formatted}</span></span>
                <span>Calls: <span className={BASE_THEME.text.primary}>{formatNumber(top_offender.call_count)}</span></span>
              </div>
              {top_offender.suggested_model && (
                <p className={`text-sm ${BASE_THEME.text.muted} mt-3`}>
                  💡 Suggested: Switch to <span className={theme.text}>{top_offender.suggested_model}</span>
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
              operation: row.operation_name,
            }))}
            theme={theme}
            storyId="routing"
            onRowClick={handleOperationClick}
            columns={[
              { key: 'complexity_formatted', label: 'Complexity', width: '12%' },
              { key: 'avg_quality_formatted', label: 'Quality', width: '10%' },
              { key: 'avg_cost_formatted', label: 'Cost/Call', width: '10%' },
              { key: 'call_count', label: 'Calls', width: '8%' },
              { key: 'opportunity_label', label: 'Opportunity', width: '14%' },
            ]}
            renderMetricCells={(row) => (
              <>
                <td className="py-3 px-4 text-right">
                  <span className="inline-flex items-center gap-1">
                    <span>{row.complexity_emoji}</span>
                    <span className={BASE_THEME.text.secondary}>{row.complexity_formatted}</span>
                  </span>
                </td>
                <td className={`py-3 px-4 text-right ${
                  row.quality_status === 'good' ? 'text-green-400' :
                  row.quality_status === 'ok' ? 'text-yellow-400' :
                  row.quality_status === 'poor' ? 'text-red-400' :
                  BASE_THEME.text.muted
                }`}>
                  {row.avg_quality_formatted}
                </td>
                <td className={`py-3 px-4 text-right ${BASE_THEME.text.secondary}`}>
                  {row.avg_cost_formatted}
                </td>
                <td className={`py-3 px-4 text-right ${BASE_THEME.text.muted}`}>
                  {formatNumber(row.call_count)}
                </td>
                <td className={`py-3 px-4 text-right font-semibold ${
                  row.opportunity === 'upgrade' ? 'text-red-400' :
                  row.opportunity === 'downgrade' ? 'text-blue-400' :
                  'text-green-400'
                }`}>
                  {row.opportunity_emoji} {row.opportunity_label}
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
              📊 Complexity vs Quality
            </h3>

            {chart_data.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={350}>
                  <ScatterChart margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                    <CartesianGrid strokeDasharray={CHART_CONFIG.grid.strokeDasharray} stroke={CHART_CONFIG.grid.stroke} />
                    <XAxis
                      type="number"
                      dataKey="complexity"
                      name="Complexity"
                      domain={[0, 1]}
                      stroke={CHART_CONFIG.axis.stroke}
                      tick={CHART_CONFIG.axis.tick}
                    />
                    <YAxis
                      type="number"
                      dataKey="quality"
                      name="Quality"
                      domain={[0, 10]}
                      stroke={CHART_CONFIG.axis.stroke}
                      tick={CHART_CONFIG.axis.tick}
                    />
                    <ZAxis
                      type="number"
                      dataKey="call_count"
                      range={[50, 400]}
                      name="Calls"
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <ReferenceLine x={0.4} stroke={CHART_CONFIG.referenceLine.info} strokeDasharray="3 3" />
                    <ReferenceLine x={0.7} stroke={CHART_CONFIG.referenceLine.critical} strokeDasharray="3 3" />
                    <ReferenceLine y={7} stroke={CHART_CONFIG.referenceLine.warning} strokeDasharray="3 3" />

                    <Scatter
                      name="Operations"
                      data={chart_data}
                      cursor="pointer"
                    >
                      {chart_data.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={opportunityColors[entry.opportunity] || opportunityColors.keep}
                        />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>

                <div className="flex justify-center gap-8 mt-4 text-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    <span className={BASE_THEME.text.muted}>↑ Upgrade Needed</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                    <span className={BASE_THEME.text.muted}>↓ Can Downgrade</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <span className={BASE_THEME.text.muted}>✓ Optimal</span>
                  </div>
                </div>
              </>
            ) : (
              <div className={`h-64 flex items-center justify-center ${BASE_THEME.text.muted}`}>
                No data to display
              </div>
            )}
          </div>
        </div>

      </PageContainer>
    </div>
  );
}