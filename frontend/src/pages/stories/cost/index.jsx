/**
 * Layer 1: Cost Analysis - Overview
 * 
 * Shows cost breakdown by operation with concentration analysis.
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import KPICard from '../../../components/common/KPICard';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, truncateText } from '../../../utils/formatters';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

// Color palette for pie chart
const COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6', '#6b7280'];

export default function CostAnalysis() {
  const navigate = useNavigate();
  const { data, loading, error } = useStory('cost');
  const theme = STORY_THEMES.cost;

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

  const { 
    health_score = 0, 
    summary = {}, 
    detail_table = [],
    chart_data = [],
  } = data || {};

  const {
    total_cost_formatted = '$0.00',
    avg_cost_formatted = '$0.000',
    top_3_concentration = 0,
    top_3_concentration_formatted = '0%',
    potential_savings_formatted = '$0.00',
  } = summary;

  // Navigate to Layer 2
  const handleOperationClick = (row) => {
    navigate(`/stories/cost/operations/${encodeURIComponent(row.agent_name)}/${encodeURIComponent(row.operation_name)}`);
  };

  // Custom tooltip for pie chart
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-gray-800 border border-emerald-500 rounded-lg p-3 shadow-lg">
          <p className="font-semibold text-emerald-400 mb-1">{data.name}</p>
          <p className="text-sm text-gray-300">${data.value.toFixed(2)} ({data.percentage}%)</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <StoryNavTabs activeStory="cost" />

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
            Dashboard &gt; Cost Analysis
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <KPICard
            theme={theme}
            title="💵 Total Cost"
            value={total_cost_formatted}
            subtext="Last 7 days"
          />
          <KPICard
            theme={theme}
            title="📊 Avg Cost/Call"
            value={avg_cost_formatted}
            subtext="Per LLM call"
          />
          <KPICard
            theme={theme}
            title="🎯 Top 3 Concentration"
            value={top_3_concentration_formatted}
            subtext="Of total cost"
          />
          <KPICard
            theme={theme}
            title="💡 Potential Savings"
            value={potential_savings_formatted}
            subtext="Weekly estimate"
          />
        </div>

        {/* Operations Table */}
        <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          <div className={`${theme.bgLight} p-4 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              📋 Cost by Operation (click row to analyze)
            </h3>
          </div>
          
          <div className="overflow-x-auto overflow-y-auto max-h-80 story-scrollbar-thin cost">
            <table className="w-full text-sm">
              <thead className="bg-gray-800 sticky top-0">
                <tr className={`border-b-2 ${theme.border}`}>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Status</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Operation</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Agent</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Cost</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>% Total</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Calls</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Avg/Call</th>
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
                      <td className="py-3 px-4 text-right text-emerald-400 font-semibold">
                        {row.total_cost_formatted}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        {row.cost_pct_formatted}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        {formatNumber(row.call_count)}
                      </td>
                      <td className={`py-3 px-4 text-right font-semibold ${
                        row.status === 'high' ? 'text-red-400' :
                        row.status === 'medium' ? 'text-yellow-400' :
                        'text-green-400'
                      }`}>
                        {row.avg_cost_formatted}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-gray-500">
                      No cost data available
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pie Chart */}
        {chart_data.length > 0 && (
          <div className={`rounded-lg border-2 ${theme.border} bg-gray-900 p-6`}>
            <h3 className={`text-lg font-semibold ${theme.text} mb-6`}>
              📊 Cost Distribution
            </h3>
            
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={chart_data}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                  label={({ name, percentage }) => percentage > 5 ? `${name} (${percentage}%)` : ''}
                >
                  {chart_data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            
            {/* Legend */}
            <div className="flex flex-wrap justify-center gap-4 mt-4 text-sm">
              {chart_data.map((entry, index) => (
                <div key={index} className="flex items-center gap-2">
                  <div 
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  ></div>
                  <span className="text-gray-400">{entry.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Insight */}
        <div className={`mt-6 p-4 rounded-lg border ${theme.border} bg-gray-900`}>
          <p className="text-sm text-gray-400">
            📊 {top_3_concentration_formatted} of costs concentrated in top 3 operations
            {detail_table.filter(d => d.status === 'high').length > 0 && (
              <span className="ml-4">
                💡 <span className="text-yellow-400">{detail_table.filter(d => d.status === 'high').length}</span> high-cost operations identified
              </span>
            )}
          </p>
        </div>

      </div>
    </div>
  );
}