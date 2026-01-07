/**
 * Layer 1: Token Efficiency - Overview (2E Design)
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES, CHART_CONFIG } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber } from '../../../utils/formatters';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';
import Layer1Table from '../../../components/stories/Layer1Table';

export default function TokenImbalance() {
  const navigate = useNavigate();
  const { data, loading, error } = useStory('token_imbalance');
  const theme = STORY_THEMES.token_imbalance;

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
    avg_ratio_formatted = '—',
    imbalanced_count = 0,
    worst_ratio_formatted = '—',
    wasted_cost_formatted = '$0.00',
  } = summary;

  const getBarColor = (status) => {
    return CHART_CONFIG.statusColors[status] || CHART_CONFIG.statusColors.good;
  };

  const handleOperationClick = (row) => {
    navigate(`/stories/token_imbalance/operations/${encodeURIComponent(row.agent_name)}/${encodeURIComponent(row.operation_name)}`);
  };

  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} ${BASE_THEME.text.primary}`}>
      <StoryNavTabs activeStory="token_imbalance" />

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
            Dashboard › Token Efficiency
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div
            onClick={() => navigate('/stories/token_imbalance/calls?filter=all')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Avg Ratio</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{avg_ratio_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Prompt:Completion</div>
          </div>

          <div
            onClick={() => navigate('/stories/token_imbalance/calls?filter=imbalanced')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Imbalanced Ops</div>
            <div className="text-2xl font-bold text-red-400">{imbalanced_count}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Ratio &gt; 10:1</div>
          </div>

          <div
            onClick={() => navigate('/stories/token_imbalance/calls?filter=max')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Worst Ratio</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{worst_ratio_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Highest imbalance</div>
          </div>

          <div
            onClick={() => navigate('/stories/token_imbalance/calls?filter=all')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Wasted Cost</div>
            <div className="text-2xl font-bold text-red-400">{wasted_cost_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>From excess tokens</div>
          </div>
        </div>

        {/* Top Offender */}
        {top_offender && (
          <div
            onClick={() => navigate(`/stories/token_imbalance/operations/${encodeURIComponent(top_offender.agent)}/${encodeURIComponent(top_offender.operation)}`)}
            className={`mb-8 rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} overflow-hidden cursor-pointer hover:${BASE_THEME.border.light} transition-all`}
          >
            <div className={`h-1 ${theme.bg}`} />
            <div className="p-5">
              <h3 className={`text-xs font-medium ${BASE_THEME.text.muted} uppercase tracking-wide mb-2`}>
                🎯 Worst Token Imbalance
              </h3>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl font-bold text-purple-400">{top_offender.agent}</span>
                <span className={BASE_THEME.text.muted}>.</span>
                <span className={`text-xl font-bold ${theme.text} font-mono`}>{top_offender.operation}</span>
              </div>
              <div className={`flex gap-6 text-sm ${BASE_THEME.text.muted}`}>
                <span>Ratio: <span className="text-red-400 font-bold">{top_offender.ratio_formatted}</span></span>
                <span>Calls: <span className={BASE_THEME.text.primary}>{formatNumber(top_offender.call_count)}</span></span>
              </div>
              {top_offender.diagnosis && (
                <p className="text-sm text-yellow-400 mt-3">
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
              operation: row.operation_name,
            }))}
            theme={theme}
            storyId="token_imbalance"
            onRowClick={handleOperationClick}
            columns={[
              { key: 'avg_prompt_formatted', label: 'Prompt', width: '11%' },
              { key: 'avg_completion_formatted', label: 'Completion', width: '13%' },
              { key: 'ratio_formatted', label: 'Ratio', width: '10%' },
              { key: 'total_cost_formatted', label: 'Cost', width: '10%' },
              { key: 'call_count', label: 'Calls', width: '8%' },
            ]}
            renderMetricCells={(row) => (
              <>
                <td className={`py-3 px-4 text-right ${BASE_THEME.text.secondary}`}>
                  {row.avg_prompt_formatted}
                </td>
                <td className={`py-3 px-4 text-right ${BASE_THEME.text.secondary}`}>
                  {row.avg_completion_formatted}
                </td>
                <td className={`py-3 px-4 text-right font-bold ${
                  row.status === 'severe' ? 'text-red-400' :
                  row.status === 'high' ? 'text-orange-400' :
                  row.status === 'moderate' ? 'text-yellow-400' :
                  'text-green-400'
                }`}>
                  {row.ratio_formatted}
                </td>
                <td className={`py-3 px-4 text-right ${BASE_THEME.text.secondary}`}>
                  {row.total_cost_formatted}
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
              📊 Ratio Distribution
            </h3>

            {chart_data.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={chart_data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                    <CartesianGrid strokeDasharray={CHART_CONFIG.grid.strokeDasharray} stroke={CHART_CONFIG.grid.stroke} />
                    <XAxis
                      dataKey="label"
                      stroke={CHART_CONFIG.axis.stroke}
                      tick={CHART_CONFIG.axis.tick}
                    />
                    <YAxis
                      stroke={CHART_CONFIG.axis.stroke}
                      tick={CHART_CONFIG.axis.tick}
                    />
                    <Tooltip
                      contentStyle={CHART_CONFIG.tooltip.contentStyle}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {chart_data.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={getBarColor(entry.status)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>

                <div className="flex justify-center gap-8 mt-4 text-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <span className={BASE_THEME.text.muted}>&lt;5:1 Balanced</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                    <span className={BASE_THEME.text.muted}>5-10:1 Moderate</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                    <span className={BASE_THEME.text.muted}>10-20:1 High</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    <span className={BASE_THEME.text.muted}>&gt;20:1 Severe</span>
                  </div>
                </div>
              </>
            ) : (
              <div className={`h-64 flex items-center justify-center ${BASE_THEME.text.muted}`}>
                No ratio data to display
              </div>
            )}
          </div>
        </div>

      </PageContainer>
    </div>
  );
}