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
import { formatNumber } from '../../../utils/formatters';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Sector } from 'recharts';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';
import Layer1Table from '../../../components/stories/Layer1Table';

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

  // Pie chart hover state
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

  const handleOperationClick = (row) => {
    navigate(`/stories/cost/operations/${encodeURIComponent(row.agent_name)}/${encodeURIComponent(row.operation_name)}`);
  };

  const handlePieClick = (data) => {
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

  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} ${BASE_THEME.text.primary}`}>
      <StoryNavTabs activeStory="cost" />

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
            Dashboard › Cost Analysis
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div
            onClick={() => navigate('/stories/cost/calls?filter=all')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Total Cost</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{total_cost_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Last 7 days</div>
          </div>

          <div
            onClick={() => navigate('/stories/cost/calls?filter=all')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Avg Cost/Call</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{avg_cost_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Per LLM call</div>
          </div>

          <div
            onClick={() => navigate('/stories/cost/calls?filter=expensive')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Top 3 Concentration</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{top_3_concentration_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Of total cost</div>
          </div>

          <div
            onClick={() => navigate('/stories/cost/calls?filter=all')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Potential Savings</div>
            <div className="text-2xl font-bold text-green-400">{potential_savings_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Weekly estimate</div>
          </div>
        </div>

        {/* Top Cost Driver Card */}
        {topOffender && (
          <div
            onClick={() => handleOperationClick(topOffender)}
            className={`mb-8 rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} overflow-hidden cursor-pointer hover:${BASE_THEME.border.light} transition-all`}
          >
            <div className={`h-1 ${theme.bg}`} />
            <div className="p-5">
              <h3 className={`text-xs font-medium ${BASE_THEME.text.muted} uppercase tracking-wide mb-2`}>
                🎯 Top Cost Driver
              </h3>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl font-bold text-purple-400">{topOffender.agent_name}</span>
                <span className={BASE_THEME.text.muted}>.</span>
                <span className={`text-xl font-bold ${theme.text} font-mono`}>{topOffender.operation_name}</span>
              </div>
              <div className={`flex gap-6 text-sm ${BASE_THEME.text.muted}`}>
                <span>Total: <span className="text-emerald-400 font-bold">{topOffender.total_cost_formatted}</span></span>
                <span>Calls: <span className={BASE_THEME.text.primary}>{topOffender.call_count}</span></span>
              </div>
              {topOffender.insight && (
                <p className="text-sm text-yellow-400 mt-3">
                  💡 {topOffender.insight}
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
            storyId="cost"
            onRowClick={handleOperationClick}
            columns={[
              { key: 'total_cost_formatted', label: 'Cost', width: '11%' },
              { key: 'cost_pct_formatted', label: '% Total', width: '11%' },
              { key: 'call_count', label: 'Calls', width: '9%' },
              { key: 'avg_cost_formatted', label: 'Avg/Call', width: '11%' },
            ]}
            renderMetricCells={(row) => (
              <>
                <td className="py-3 px-4 text-right text-emerald-400 font-semibold">
                  {row.total_cost_formatted}
                </td>
                <td className={`py-3 px-4 text-right ${BASE_THEME.text.secondary}`}>
                  {row.cost_pct_formatted}
                </td>
                <td className={`py-3 px-4 text-right ${BASE_THEME.text.muted}`}>
                  {formatNumber(row.call_count)}
                </td>
                <td className={`py-3 px-4 text-right font-semibold ${
                  row.status === 'high' ? 'text-red-400' :
                  row.status === 'medium' ? 'text-yellow-400' :
                  'text-green-400'
                }`}>
                  {row.avg_cost_formatted}
                </td>
              </>
            )}
          />
        </div>

        {/* Chart */}
        {chart_data.length > 0 && (
          <div className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} overflow-hidden`}>
            <div className={`h-1 ${theme.bg}`} />
            <div className="p-6">
              <h3 className={`text-sm font-medium ${theme.text} uppercase tracking-wide mb-2`}>
                📊 Cost Distribution
              </h3>
              <p className={`text-xs ${BASE_THEME.text.muted} mb-6`}>Click a segment to drill into that operation</p>

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
                      activeIndex={activeIndex}
                      activeShape={renderActiveShape}
                      onMouseEnter={(_, index) => setActiveIndex(index)}
                      onMouseLeave={() => setActiveIndex(null)}
                      onClick={(_, index) => handlePieClick(chart_data[index], index)}
                      style={{ cursor: 'pointer' }}
                    >
                      {chart_data.map((entry, index) => (
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
                  {chart_data.map((entry, index) => (
                    <div
                      key={index}
                      className={`flex items-center gap-2 cursor-pointer hover:${BASE_THEME.container.secondary} rounded px-2 py-1 -mx-2 transition-colors`}
                      onClick={() => handlePieClick(entry, index)}
                      onMouseEnter={() => setActiveIndex(index)}
                      onMouseLeave={() => setActiveIndex(null)}
                    >
                      <div
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: COLORS[index % COLORS.length] }}
                      ></div>
                      <span className={`${BASE_THEME.text.muted} truncate max-w-[150px]`}>{entry.name}</span>
                      <span className={BASE_THEME.text.secondary}>({entry.percentage}%)</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

      </PageContainer>
    </div>
  );
}