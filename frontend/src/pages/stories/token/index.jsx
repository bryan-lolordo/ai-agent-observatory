/**
 * Layer 1: Token Efficiency - Overview (2E Design)
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES, CHART_CONFIG } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, truncateText } from '../../../utils/formatters';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';

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
            <div className="px-4 py-2 rounded-full border border-gray-700 bg-gray-900">
              <span className={`text-sm font-semibold ${theme.text}`}>
                {Math.round(health_score)}% Health
              </span>
            </div>
          </div>
          <p className="text-gray-500 text-sm">
            Dashboard › Token Efficiency
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div 
            onClick={() => navigate('/stories/token_imbalance/calls?filter=all')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Avg Ratio</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{avg_ratio_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">Prompt:Completion</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/token_imbalance/calls?filter=imbalanced')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Imbalanced Ops</div>
            <div className="text-2xl font-bold text-red-400">{imbalanced_count}</div>
            <div className="text-xs text-gray-500 mt-1">Ratio &gt; 10:1</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/token_imbalance/calls?filter=max')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Worst Ratio</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{worst_ratio_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">Highest imbalance</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/token_imbalance/calls?filter=all')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Wasted Cost</div>
            <div className="text-2xl font-bold text-red-400">{wasted_cost_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">From excess tokens</div>
          </div>
        </div>

        {/* Top Offender */}
        {top_offender && (
          <div 
            onClick={() => navigate(`/stories/token_imbalance/operations/${encodeURIComponent(top_offender.agent)}/${encodeURIComponent(top_offender.operation)}`)}
            className="mb-8 rounded-lg border border-gray-700 bg-gray-900 overflow-hidden cursor-pointer hover:border-gray-600 transition-all"
          >
            <div className={`h-1 ${theme.bg}`} />
            <div className="p-5">
              <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">
                🎯 Worst Token Imbalance
              </h3>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl font-bold text-purple-400">{top_offender.agent}</span>
                <span className="text-gray-500">.</span>
                <span className={`text-xl font-bold ${theme.text} font-mono`}>{top_offender.operation}</span>
              </div>
              <div className="flex gap-6 text-sm text-gray-400">
                <span>Ratio: <span className="text-red-400 font-bold">{top_offender.ratio_formatted}</span></span>
                <span>Calls: <span className="text-gray-200">{formatNumber(top_offender.call_count)}</span></span>
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
        <div className="mb-8 rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
          <div className={`h-1 ${theme.bg}`} />
          <div className="p-4 border-b border-gray-700">
            <h3 className={`text-sm font-medium ${theme.text} uppercase tracking-wide`}>
              📊 Operations
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
                  <th style={{ width: '11%' }} className="text-right py-3 px-4 text-gray-400 font-medium">Prompt</th>
                  <th style={{ width: '13%' }} className="text-right py-3 px-4 text-gray-400 font-medium">Completion</th>
                  <th style={{ width: '10%' }} className="text-center py-3 px-4 text-gray-400 font-medium">Ratio</th>
                  <th style={{ width: '10%' }} className="text-right py-3 px-4 text-gray-400 font-medium">Cost</th>
                  <th style={{ width: '8%' }} className="text-right py-3 px-4 text-gray-400 font-medium">Calls</th>
                </tr>
              </thead>
              <tbody>
                {detail_table.length > 0 ? (
                  detail_table.map((row, idx) => (
                    <tr
                      key={idx}
                      onClick={() => handleOperationClick(row)}
                      className="border-b border-gray-800 cursor-pointer hover:bg-gray-800/50 transition-colors"
                    >
                      <td className="py-3 px-4 text-lg">{row.status_emoji}</td>
                      <td className="py-3 px-4 font-semibold text-purple-400">
                        {row.agent_name}
                      </td>
                      <td className={`py-3 px-4 font-mono ${theme.text}`}>
                        {truncateText(row.operation_name, 25)}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        {row.avg_prompt_formatted}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        {row.avg_completion_formatted}
                      </td>
                      <td className={`py-3 px-4 text-center font-bold ${
                        row.status === 'severe' ? 'text-red-400' :
                        row.status === 'high' ? 'text-orange-400' :
                        row.status === 'moderate' ? 'text-yellow-400' :
                        'text-green-400'
                      }`}>
                        {row.ratio_formatted}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        {row.total_cost_formatted}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-400">
                        {formatNumber(row.call_count)}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-gray-500">
                      No token data available
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Chart */}
        <div className="rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
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
                    <span className="text-gray-400">&lt;5:1 Balanced</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                    <span className="text-gray-400">5-10:1 Moderate</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                    <span className="text-gray-400">10-20:1 High</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    <span className="text-gray-400">&gt;20:1 Severe</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-500">
                No ratio data to display
              </div>
            )}
          </div>
        </div>

      </PageContainer>
    </div>
  );
}