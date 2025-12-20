/**
 * Layer 1: Cost Analysis - Overview (2E Design)
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, truncateText } from '../../../utils/formatters';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

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
    top_3_concentration_formatted = '0%',
    potential_savings_formatted = '$0.00',
  } = summary;

  const handleOperationClick = (row) => {
    navigate(`/stories/cost/operations/${encodeURIComponent(row.agent_name)}/${encodeURIComponent(row.operation_name)}`);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <StoryNavTabs activeStory="cost" />

      <div className="max-w-7xl mx-auto p-6">
        
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
            Dashboard › Cost Analysis
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div 
            onClick={() => navigate('/stories/cost/calls?filter=all')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Total Cost</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{total_cost_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">Last 7 days</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/cost/calls?filter=all')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Avg Cost/Call</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{avg_cost_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">Per LLM call</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/cost/calls?filter=expensive')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Top 3 Concentration</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{top_3_concentration_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">Of total cost</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/cost/calls?filter=all')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Potential Savings</div>
            <div className="text-2xl font-bold text-green-400">{potential_savings_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">Weekly estimate</div>
          </div>
        </div>

        {/* Operations Table */}
        <div className="mb-8 rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
          <div className={`h-1 ${theme.bg}`} />
          <div className="p-4 border-b border-gray-700">
            <h3 className="text-xs font-medium text-gray-300 uppercase tracking-wide">
              📊 Cost by Operation
              <span className="text-gray-500 normal-case ml-2 font-normal">Click row to analyze</span>
            </h3>
          </div>
          
          <div className="overflow-x-auto overflow-y-auto max-h-80">
            <table className="w-full text-sm">
              <thead className="bg-gray-800/50">
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Status</th>
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Agent</th>
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Operation</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Cost</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">% Total</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Calls</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Avg/Call</th>
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
                        {row.agent_name || '—'}
                      </td>
                      <td className={`py-3 px-4 font-mono ${theme.text}`}>
                        {truncateText(row.operation_name, 25)}
                      </td>
                      <td className="py-3 px-4 text-right text-emerald-400 font-semibold">
                        {row.total_cost_formatted}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        {row.cost_pct_formatted}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-400">
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

        {/* Chart */}
        {chart_data.length > 0 && (
          <div className="rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
            <div className={`h-1 ${theme.bg}`} />
            <div className="p-6">
              <h3 className="text-xs font-medium text-gray-300 uppercase tracking-wide mb-6">
                📊 Cost Distribution
              </h3>
              
              <div className="flex items-center justify-center gap-12">
                <ResponsiveContainer width={250} height={250}>
                  <PieChart>
                    <Pie
                      data={chart_data}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      outerRadius={100}
                      dataKey="value"
                    >
                      {chart_data.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        color: '#f3f4f6'
                      }}
                      formatter={(value) => `$${value.toFixed(2)}`}
                    />
                  </PieChart>
                </ResponsiveContainer>
                
                <div className="flex flex-col gap-2 text-sm">
                  {chart_data.map((entry, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <div 
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      ></div>
                      <span className="text-gray-400">{entry.name}</span>
                      <span className="text-gray-300">({entry.percentage}%)</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}