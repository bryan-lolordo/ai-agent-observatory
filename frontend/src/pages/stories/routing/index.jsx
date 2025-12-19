/**
 * Layer 1: Model Routing - Overview
 * 
 * Shows routing opportunities (upgrade/downgrade candidates).
 * Matches Latency/Cache story UI pattern exactly.
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import KPICard from '../../../components/common/KPICard';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, formatCurrency, truncateText } from '../../../utils/formatters';
import { 
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, Cell, ReferenceLine, ZAxis 
} from 'recharts';

export default function Routing() {
  const navigate = useNavigate();
  const { data, loading, error } = useStory('routing');
  const theme = STORY_THEMES.routing;

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
    current_model = '—',
    current_model_pct = 0,
    downgrade_count = 0,
    upgrade_count = 0,
    potential_savings = 0,
    potential_savings_formatted = '$0.00',
  } = summary;

  // Color mapping for opportunities
  const opportunityColors = {
    upgrade: '#ef4444',    // red
    downgrade: '#3b82f6',  // blue
    keep: '#22c55e',       // green
  };

  // Navigate to Layer 2
  const handleOperationClick = (row) => {
    navigate(`/stories/routing/operations/${encodeURIComponent(row.agent_name)}/${encodeURIComponent(row.operation_name)}`);
  };

  // Navigate to top offender
  const handleTopOffenderClick = () => {
    if (top_offender) {
      navigate(`/stories/routing/operations/${encodeURIComponent(top_offender.agent)}/${encodeURIComponent(top_offender.operation)}`);
    }
  };

  // Custom tooltip for scatter chart
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-gray-800 border border-purple-500 rounded-lg p-3 shadow-lg">
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
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Story Navigation */}
      <StoryNavTabs activeStory="routing" />

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
            Dashboard &gt; Model Routing
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <KPICard
            theme={theme}
            title="🤖 Current Model"
            value={current_model}
            subtext={`${current_model_pct}% of ${formatNumber(total_calls)} calls`}
          />
          <KPICard
            theme={theme}
            title="↓ Downgrade Candidates"
            value={downgrade_count}
            subtext="Can use cheaper model"
          />
          <KPICard
            theme={theme}
            title="↑ Upgrade Candidates"
            value={upgrade_count}
            subtext="Need better model"
          />
          <KPICard
            theme={theme}
            title="💰 Potential Savings"
            value={potential_savings_formatted}
            subtext="From routing optimization"
          />
        </div>

        {/* Top Offender - Clickable */}
        {top_offender && (
          <div 
            onClick={handleTopOffenderClick}
            className={`mb-8 rounded-lg border-2 ${theme.border} bg-gradient-to-br ${theme.gradient} p-6 cursor-pointer hover:scale-[1.01] transition-all`}
          >
            <h3 className={`text-lg font-semibold ${theme.textLight} mb-3`}>
              🎯 Top Routing Opportunity
            </h3>
            <div className={`text-2xl font-bold ${theme.text} mb-2 font-mono`}>
              {top_offender.agent}.{top_offender.operation}
            </div>
            <div className="flex gap-6 text-sm text-gray-300">
              <span>{top_offender.opportunity_emoji} {top_offender.opportunity?.toUpperCase()}</span>
              <span>Complexity: {top_offender.complexity_formatted}</span>
              <span>Quality: {top_offender.quality_formatted}</span>
              <span>{formatNumber(top_offender.call_count)} calls</span>
            </div>
            {top_offender.suggested_model && (
              <p className="text-sm text-gray-400 mt-2">
                💡 Suggested: Switch to <span className={theme.text}>{top_offender.suggested_model}</span>
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
          
          <div className="overflow-x-auto overflow-y-auto max-h-80 story-scrollbar-thin routing">
            <table className="w-full text-sm">
              <thead className="bg-gray-800 sticky top-0">
                <tr className={`border-b-2 ${theme.border}`}>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Status</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Operation</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Agent</th>
                  <th className={`text-center py-3 px-4 ${theme.textLight}`}>Complexity</th>
                  <th className={`text-center py-3 px-4 ${theme.textLight}`}>Quality</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Cost/Call</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Calls</th>
                  <th className={`text-center py-3 px-4 ${theme.textLight}`}>Opportunity</th>
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
                      <td className="py-3 px-4 text-lg">{row.status_emoji}</td>
                      <td className={`py-3 px-4 font-mono ${theme.text} font-semibold`}>
                        {truncateText(row.operation_name, 25)}
                      </td>
                      <td className="py-3 px-4 text-gray-400">
                        {row.agent_name || '—'}
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
                      <td className="py-3 px-4 text-right text-gray-300">
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

        {/* Scatter Chart - Complexity vs Quality */}
        <div className={`rounded-lg border-2 ${theme.border} bg-gray-900 p-6`}>
          <h3 className={`text-lg font-semibold ${theme.text} mb-6`}>
            📊 Complexity vs Quality
          </h3>
          
          {chart_data.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={400}>
                <ScatterChart margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    type="number" 
                    dataKey="complexity" 
                    name="Complexity"
                    domain={[0, 1]}
                    stroke="#9ca3af"
                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                    label={{ value: 'Complexity', position: 'insideBottom', offset: -10, fill: '#9ca3af' }}
                  />
                  <YAxis 
                    type="number" 
                    dataKey="quality" 
                    name="Quality"
                    domain={[0, 10]}
                    stroke="#9ca3af"
                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                    label={{ value: 'Quality (0-10)', angle: -90, position: 'insideLeft', fill: '#9ca3af' }}
                  />
                  <ZAxis 
                    type="number" 
                    dataKey="call_count" 
                    range={[50, 400]} 
                    name="Calls"
                  />
                  <Tooltip content={<CustomTooltip />} />
                  
                  {/* Reference lines for thresholds */}
                  <ReferenceLine 
                    x={0.4} 
                    stroke="#3b82f6" 
                    strokeDasharray="3 3"
                    label={{ value: 'Low', position: 'top', fill: '#3b82f6', fontSize: 10 }}
                  />
                  <ReferenceLine 
                    x={0.7} 
                    stroke="#ef4444" 
                    strokeDasharray="3 3"
                    label={{ value: 'High', position: 'top', fill: '#ef4444', fontSize: 10 }}
                  />
                  <ReferenceLine 
                    y={8} 
                    stroke="#22c55e" 
                    strokeDasharray="3 3"
                    label={{ value: 'Good', position: 'right', fill: '#22c55e', fontSize: 10 }}
                  />
                  <ReferenceLine 
                    y={7} 
                    stroke="#eab308" 
                    strokeDasharray="3 3"
                    label={{ value: 'OK', position: 'right', fill: '#eab308', fontSize: 10 }}
                  />
                  
                  <Scatter 
                    name="Operations" 
                    data={chart_data}
                    onClick={(data) => {
                      if (data && data.agent && data.operation) {
                        navigate(`/stories/routing/operations/${encodeURIComponent(data.agent)}/${encodeURIComponent(data.operation)}`);
                      }
                    }}
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
              
              {/* Legend */}
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
          
          <p className="text-xs text-gray-400 mt-4 text-center">
            Click any point to investigate that operation. Bubble size = call volume.
          </p>
        </div>

      </div>
    </div>
  );
}