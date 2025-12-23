/**
 * Layer 1: Cost Analysis - Overview (2E Design)
 * Updated: Added Top Offender, clickable pie chart, agent/operation filters
 */

import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, truncateText } from '../../../utils/formatters';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Sector } from 'recharts';

const COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6', '#6b7280'];

// Custom active shape for hover effect on pie
const renderActiveShape = (props) => {
  const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;
  return (
    <g>
      <Sector
        cx={cx}
        cy={cy}
        innerRadius={innerRadius}
        outerRadius={outerRadius + 8}
        startAngle={startAngle}
        endAngle={endAngle}
        fill={fill}
        style={{ cursor: 'pointer', filter: 'brightness(1.2)' }}
      />
    </g>
  );
};

export default function CostAnalysis() {
  const navigate = useNavigate();
  const { data, loading, error } = useStory('cost');
  const theme = STORY_THEMES.cost;
  
  // Filter state - ALL HOOKS MUST BE BEFORE ANY RETURNS
  const [agentFilter, setAgentFilter] = useState('all');
  const [operationFilter, setOperationFilter] = useState('all');
  const [activeIndex, setActiveIndex] = useState(null);

  // Extract data (with defaults for when loading)
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

  // Get unique agents and operations for filters
  const uniqueAgents = useMemo(() => {
    const agents = [...new Set(detail_table.map(row => row.agent_name).filter(Boolean))];
    return agents.sort();
  }, [detail_table]);

  const uniqueOperations = useMemo(() => {
    const ops = [...new Set(detail_table.map(row => row.operation_name).filter(Boolean))];
    return ops.sort();
  }, [detail_table]);

  // Filter the table data
  const filteredTable = useMemo(() => {
    return detail_table.filter(row => {
      const matchesAgent = agentFilter === 'all' || row.agent_name === agentFilter;
      const matchesOp = operationFilter === 'all' || row.operation_name === operationFilter;
      return matchesAgent && matchesOp;
    });
  }, [detail_table, agentFilter, operationFilter]);

  // Recalculate chart data based on filters
  const filteredChartData = useMemo(() => {
    if (agentFilter === 'all' && operationFilter === 'all') {
      return chart_data;
    }
    
    const totalCost = filteredTable.reduce((sum, row) => sum + (row.total_cost || 0), 0);
    return filteredTable.map(row => ({
      name: row.operation_name,
      value: row.total_cost || 0,
      percentage: totalCost > 0 ? ((row.total_cost / totalCost) * 100).toFixed(1) : 0,
      agent_name: row.agent_name,
      operation_name: row.operation_name,
    })).slice(0, 7); // Limit to 7 for colors
  }, [filteredTable, chart_data, agentFilter, operationFilter]);

  // Top offender (highest cost operation)
  const topOffender = useMemo(() => {
    if (detail_table.length === 0) return null;
    
    // Sort by total cost descending
    const sorted = [...detail_table].sort((a, b) => (b.total_cost || 0) - (a.total_cost || 0));
    const top = sorted[0];
    
    // Generate insight based on the data
    let insight = '';
    if (top.avg_cost && top.avg_cost > 0.10) {
      insight = `High per-call cost (${top.avg_cost_formatted}) - consider output constraints or model downgrade`;
    } else if (top.call_count > 20) {
      insight = `High volume (${top.call_count} calls) - consider caching duplicates`;
    } else {
      insight = `${top.cost_pct_formatted} of total spend - review for optimization`;
    }
    
    return { ...top, insight };
  }, [detail_table]);

  // CONDITIONAL RETURNS AFTER ALL HOOKS
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

  const handleOperationClick = (row) => {
    navigate(`/stories/cost/operations/${encodeURIComponent(row.agent_name)}/${encodeURIComponent(row.operation_name)}`);
  };

  const handlePieClick = (data, index) => {
    if (data && data.agent_name && data.operation_name) {
      navigate(`/stories/cost/operations/${encodeURIComponent(data.agent_name)}/${encodeURIComponent(data.operation_name)}`);
    } else if (data && data.name) {
      // Fallback: find the matching row from detail_table
      const matchingRow = detail_table.find(row => row.operation_name === data.name);
      if (matchingRow) {
        handleOperationClick(matchingRow);
      }
    }
  };

  const clearFilters = () => {
    setAgentFilter('all');
    setOperationFilter('all');
  };

  const hasActiveFilters = agentFilter !== 'all' || operationFilter !== 'all';

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

        {/* Top Cost Driver Card - matches Layer 2 Top Offender design */}
        {topOffender && (
          <div 
            onClick={() => handleOperationClick(topOffender)}
            className="mb-8 rounded-lg border border-gray-700 bg-gray-900 overflow-hidden cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className={`h-1 ${theme.bg}`} />
            <div className="p-5">
              <div className="flex items-center gap-2 mb-4">
                <span className={theme.text}>🎯</span>
                <span className={`text-xs font-medium ${theme.text} uppercase tracking-wide`}>Top Cost Driver</span>
              </div>
              
              <div className="flex items-baseline gap-2 mb-1">
                <span className="text-purple-400 font-semibold text-lg">{topOffender.agent_name}</span>
                <span className="text-gray-500">·</span>
                <span className={`font-mono text-lg ${theme.text}`}>{topOffender.operation_name}</span>
              </div>
              
              <div className="flex items-center gap-4 text-sm text-gray-400 mb-4">
                <span>Total: <span className="text-emerald-400 font-semibold">{topOffender.total_cost_formatted}</span></span>
                <span>Calls: <span className="text-white">{topOffender.call_count}</span></span>
              </div>
              
              <div className="flex items-start gap-2 text-sm bg-gray-800/50 rounded p-3">
                <span className="text-yellow-500 mt-0.5">💡</span>
                <span className="text-gray-300">{topOffender.insight}</span>
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="mb-6 flex items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-500 uppercase tracking-wide">Agent:</label>
            <select
              value={agentFilter}
              onChange={(e) => setAgentFilter(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-yellow-500"
            >
              <option value="all">All Agents</option>
              {uniqueAgents.map(agent => (
                <option key={agent} value={agent}>{agent}</option>
              ))}
            </select>
          </div>
          
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-500 uppercase tracking-wide">Operation:</label>
            <select
              value={operationFilter}
              onChange={(e) => setOperationFilter(e.target.value)}
              className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-yellow-500"
            >
              <option value="all">All Operations</option>
              {uniqueOperations.map(op => (
                <option key={op} value={op}>{op}</option>
              ))}
            </select>
          </div>
          
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="px-3 py-1.5 text-sm text-gray-400 hover:text-white transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Operations Table */}
        <div className="mb-8 rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
          <div className={`h-1 ${theme.bg}`} />
          <div className="p-4 border-b border-gray-700">
            <h3 className="text-xs font-medium text-gray-300 uppercase tracking-wide">
              📊 Cost by Operation
              <span className="text-gray-500 normal-case ml-2 font-normal">Click row to analyze</span>
              {hasActiveFilters && (
                <span className="text-yellow-500 ml-2">
                  (Filtered: {filteredTable.length} of {detail_table.length})
                </span>
              )}
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
                {filteredTable.length > 0 ? (
                  filteredTable.map((row, idx) => (
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
                      {hasActiveFilters ? 'No operations match the current filters' : 'No cost data available'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Chart */}
        {filteredChartData.length > 0 && (
          <div className="rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
            <div className={`h-1 ${theme.bg}`} />
            <div className="p-6">
              <h3 className="text-xs font-medium text-gray-300 uppercase tracking-wide mb-2">
                📊 Cost Distribution
              </h3>
              <p className="text-xs text-gray-500 mb-6">Click a segment to drill into that operation</p>
              
              <div className="flex items-center justify-center gap-12">
                <ResponsiveContainer width={250} height={250}>
                  <PieChart>
                    <Pie
                      data={filteredChartData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      outerRadius={100}
                      dataKey="value"
                      activeIndex={activeIndex}
                      activeShape={renderActiveShape}
                      onMouseEnter={(_, index) => setActiveIndex(index)}
                      onMouseLeave={() => setActiveIndex(null)}
                      onClick={(data, index) => handlePieClick(filteredChartData[index], index)}
                      style={{ cursor: 'pointer' }}
                    >
                      {filteredChartData.map((entry, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={COLORS[index % COLORS.length]}
                          style={{ cursor: 'pointer' }}
                        />
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
                  {filteredChartData.map((entry, index) => (
                    <div 
                      key={index} 
                      className="flex items-center gap-2 cursor-pointer hover:bg-gray-800 rounded px-2 py-1 -mx-2 transition-colors"
                      onClick={() => handlePieClick(entry, index)}
                      onMouseEnter={() => setActiveIndex(index)}
                      onMouseLeave={() => setActiveIndex(null)}
                    >
                      <div 
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      ></div>
                      <span className="text-gray-400 truncate max-w-[150px]">{entry.name}</span>
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