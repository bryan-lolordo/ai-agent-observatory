/**
 * Layer 1: Model Routing - Overview (2E Design)
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, truncateText } from '../../../utils/formatters';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine, ZAxis } from 'recharts';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';

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

  const opportunityColors = {
    upgrade: '#ef4444',
    downgrade: '#3b82f6',
    keep: '#22c55e',
  };

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
            <div className="px-4 py-2 rounded-full border border-gray-700 bg-gray-900">
              <span className={`text-sm font-semibold ${theme.text}`}>
                {Math.round(health_score)}% Health
              </span>
            </div>
          </div>
          <p className="text-gray-500 text-sm">
            Dashboard › Model Routing
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div 
            onClick={() => navigate('/stories/routing/calls?filter=all')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Current Model</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{current_model}</div>
            <div className="text-xs text-gray-500 mt-1">{current_model_pct}% of {formatNumber(total_calls)} calls</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/routing/calls?filter=downgrade')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Downgrade Candidates</div>
            <div className="text-2xl font-bold text-blue-400">{downgrade_count}</div>
            <div className="text-xs text-gray-500 mt-1">Can use cheaper model</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/routing/calls?filter=upgrade')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Upgrade Candidates</div>
            <div className="text-2xl font-bold text-red-400">{upgrade_count}</div>
            <div className="text-xs text-gray-500 mt-1">Need better model</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/routing/calls?filter=all')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Potential Savings</div>
            <div className="text-2xl font-bold text-green-400">{potential_savings_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">From routing optimization</div>
          </div>
        </div>

        {/* Top Offender */}
        {top_offender && (
          <div 
            onClick={() => navigate(`/stories/routing/operations/${encodeURIComponent(top_offender.agent)}/${encodeURIComponent(top_offender.operation)}`)}
            className="mb-8 rounded-lg border border-gray-700 bg-gray-900 overflow-hidden cursor-pointer hover:border-gray-600 transition-all"
          >
            <div className={`h-1 ${theme.bg}`} />
            <div className="p-5">
              <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">
                🎯 Top Routing Opportunity
              </h3>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl font-bold text-purple-400">{top_offender.agent}</span>
                <span className="text-gray-500">.</span>
                <span className={`text-xl font-bold ${theme.text} font-mono`}>{top_offender.operation}</span>
              </div>
              <div className="flex gap-6 text-sm text-gray-400">
                <span>{top_offender.opportunity_emoji} {top_offender.opportunity?.toUpperCase()}</span>
                <span>Complexity: <span className="text-gray-200">{top_offender.complexity_formatted}</span></span>
                <span>Quality: <span className="text-gray-200">{top_offender.quality_formatted}</span></span>
                <span>Calls: <span className="text-gray-200">{formatNumber(top_offender.call_count)}</span></span>
              </div>
              {top_offender.suggested_model && (
                <p className="text-sm text-gray-500 mt-3">
                  💡 Suggested: Switch to <span className={theme.text}>{top_offender.suggested_model}</span>
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
                  <th style={{ width: '28%' }} className="text-left py-3 px-4 text-gray-400 font-medium">Operation</th>
                  <th style={{ width: '12%' }} className="text-center py-3 px-4 text-gray-400 font-medium">Complexity</th>
                  <th style={{ width: '10%' }} className="text-center py-3 px-4 text-gray-400 font-medium">Quality</th>
                  <th style={{ width: '10%' }} className="text-right py-3 px-4 text-gray-400 font-medium">Cost/Call</th>
                  <th style={{ width: '8%' }} className="text-right py-3 px-4 text-gray-400 font-medium">Calls</th>
                  <th style={{ width: '14%' }} className="text-center py-3 px-4 text-gray-400 font-medium">Opportunity</th>
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
                      <td className="py-3 px-4 text-center">
                        <span className="inline-flex items-center gap-1">
                          <span>{row.complexity_emoji}</span>
                          <span className="text-gray-300">{row.complexity_formatted}</span>
                        </span>
                      </td>
                      <td className={`py-3 px-4 text-center ${
                        row.quality_status === 'good' ? 'text-green-400' :
                        row.quality_status === 'ok' ? 'text-yellow-400' :
                        row.quality_status === 'poor' ? 'text-red-400' :
                        'text-gray-400'
                      }`}>
                        {row.avg_quality_formatted}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        {row.avg_cost_formatted}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-400">
                        {formatNumber(row.call_count)}
                      </td>
                      <td className={`py-3 px-4 text-center font-semibold ${
                        row.opportunity === 'upgrade' ? 'text-red-400' :
                        row.opportunity === 'downgrade' ? 'text-blue-400' :
                        'text-green-400'
                      }`}>
                        {row.opportunity_emoji} {row.opportunity_label}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-gray-500">
                      No routing data available
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
              📊 Complexity vs Quality
            </h3>
            
            {chart_data.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={350}>
                  <ScatterChart margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis 
                      type="number" 
                      dataKey="complexity" 
                      name="Complexity"
                      domain={[0, 1]}
                      stroke="#6b7280"
                      tick={{ fill: '#9ca3af', fontSize: 11 }}
                    />
                    <YAxis 
                      type="number" 
                      dataKey="quality" 
                      name="Quality"
                      domain={[0, 10]}
                      stroke="#6b7280"
                      tick={{ fill: '#9ca3af', fontSize: 11 }}
                    />
                    <ZAxis 
                      type="number" 
                      dataKey="call_count" 
                      range={[50, 400]} 
                      name="Calls"
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <ReferenceLine x={0.4} stroke="#3b82f6" strokeDasharray="3 3" />
                    <ReferenceLine x={0.7} stroke="#ef4444" strokeDasharray="3 3" />
                    <ReferenceLine y={7} stroke="#eab308" strokeDasharray="3 3" />
                    
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
                    <span className="text-gray-400">↑ Upgrade Needed</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                    <span className="text-gray-400">↓ Can Downgrade</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <span className="text-gray-400">✓ Optimal</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="h-64 flex items-center justify-center text-gray-500">
                No data to display
              </div>
            )}
          </div>
        </div>

      </PageContainer>
    </div>
  );
}