/**
 * Layer 1: Quality Monitoring - Overview
 * 
 * Shows quality issues across operations.
 * Matches Routing/Cache story UI pattern exactly.
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import KPICard from '../../../components/common/KPICard';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, truncateText } from '../../../utils/formatters';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, Cell 
} from 'recharts';

export default function Quality() {
  const navigate = useNavigate();
  const { data, loading, error } = useStory('quality');
  const theme = STORY_THEMES.quality;

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
    evaluated_calls = 0,
    avg_quality = null,
    avg_quality_formatted = '—',
    low_quality_count = 0,
    error_count = 0,
    error_rate = 0,
    error_rate_formatted = '0%',
    hallucination_count = 0,
  } = summary;

  // Chart colors based on quality threshold
  const getBarColor = (bucket) => {
    if (bucket < 5) return '#ef4444';  // red - critical
    if (bucket < 7) return '#f97316';  // orange - low
    if (bucket < 8) return '#eab308';  // yellow - ok
    return '#22c55e';                   // green - good
  };

  // Navigate to Layer 2
  const handleOperationClick = (row) => {
    navigate(`/stories/quality/operations/${encodeURIComponent(row.agent_name)}/${encodeURIComponent(row.operation_name)}`);
  };

  // Navigate to top offender
  const handleTopOffenderClick = () => {
    if (top_offender) {
      navigate(`/stories/quality/operations/${encodeURIComponent(top_offender.agent)}/${encodeURIComponent(top_offender.operation)}`);
    }
  };

  // Custom tooltip for bar chart
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-gray-800 border border-red-500 rounded-lg p-3 shadow-lg">
          <p className="font-semibold text-red-400 mb-1">Score: {data.label}</p>
          <p className="text-sm text-gray-300">{data.count} calls</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Story Navigation */}
      <StoryNavTabs activeStory="quality" />

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
            Dashboard &gt; Quality Monitoring
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <KPICard
            theme={theme}
            title="📊 Avg Quality"
            value={avg_quality_formatted}
            subtext={`${formatNumber(evaluated_calls)} of ${formatNumber(total_calls)} evaluated`}
          />
          <KPICard
            theme={theme}
            title="🔴 Low Quality Ops"
            value={low_quality_count}
            subtext="Operations below 7.0"
          />
          <KPICard
            theme={theme}
            title="❌ Error Rate"
            value={error_rate_formatted}
            subtext={`${formatNumber(error_count)} errors`}
          />
          <KPICard
            theme={theme}
            title="⚠️ Hallucinations"
            value={hallucination_count}
            subtext="Detected in responses"
          />
        </div>

        {/* Top Offender - Clickable */}
        {top_offender && (
          <div 
            onClick={handleTopOffenderClick}
            className={`mb-8 rounded-lg border-2 ${theme.border} bg-gradient-to-br ${theme.gradient} p-6 cursor-pointer hover:scale-[1.01] transition-all`}
          >
            <h3 className={`text-lg font-semibold ${theme.textLight} mb-3`}>
              🎯 Worst Quality Operation
            </h3>
            <div className={`text-2xl font-bold ${theme.text} mb-2 font-mono`}>
              {top_offender.agent}.{top_offender.operation}
            </div>
            <div className="flex gap-6 text-sm text-gray-300">
              <span>Score: {top_offender.avg_score_formatted}</span>
              <span>{formatNumber(top_offender.call_count)} calls</span>
              {top_offender.error_count > 0 && (
                <span className="text-red-400">❌ {top_offender.error_count} errors</span>
              )}
              {top_offender.hallucination_count > 0 && (
                <span className="text-yellow-400">⚠️ {top_offender.hallucination_count} hallucinations</span>
              )}
            </div>
            <p className="text-sm text-gray-400 mt-2">
              💡 Click to investigate quality issues
            </p>
          </div>
        )}

        {/* Operations Table */}
        <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          <div className={`${theme.bgLight} p-4 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              📋 Operations by Quality (click row to drill down)
            </h3>
          </div>
          
          <div className="overflow-x-auto overflow-y-auto max-h-80 story-scrollbar-thin quality">
            <table className="w-full text-sm">
              <thead className="bg-gray-800 sticky top-0">
                <tr className={`border-b-2 ${theme.border}`}>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Status</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Operation</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Agent</th>
                  <th className={`text-center py-3 px-4 ${theme.textLight}`}>Avg Score</th>
                  <th className={`text-center py-3 px-4 ${theme.textLight}`}>Min</th>
                  <th className={`text-center py-3 px-4 ${theme.textLight}`}>Errors</th>
                  <th className={`text-center py-3 px-4 ${theme.textLight}`}>Halluc.</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Calls</th>
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
                      <td className={`py-3 px-4 text-center font-bold ${
                        row.status === 'good' ? 'text-green-400' :
                        row.status === 'ok' ? 'text-yellow-400' :
                        row.status === 'low' ? 'text-orange-400' :
                        row.status === 'critical' ? 'text-red-400' :
                        'text-gray-400'
                      }`}>
                        {row.avg_score_formatted}
                      </td>
                      <td className="py-3 px-4 text-center text-gray-400">
                        {row.min_score_formatted}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {row.error_count > 0 ? (
                          <span className="text-red-400">❌ {row.error_count}</span>
                        ) : (
                          <span className="text-gray-600">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {row.hallucination_count > 0 ? (
                          <span className="text-yellow-400">⚠️ {row.hallucination_count}</span>
                        ) : (
                          <span className="text-gray-600">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        {formatNumber(row.call_count)}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-gray-500">
                      No quality data available
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Quality Distribution Chart */}
        <div className={`rounded-lg border-2 ${theme.border} bg-gray-900 p-6`}>
          <h3 className={`text-lg font-semibold ${theme.text} mb-6`}>
            📊 Quality Score Distribution
          </h3>
          
          {chart_data.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart 
                  data={chart_data}
                  margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="label" 
                    stroke="#9ca3af"
                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                    label={{ value: 'Quality Score Range', position: 'insideBottom', offset: -10, fill: '#9ca3af' }}
                  />
                  <YAxis 
                    stroke="#9ca3af"
                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                    label={{ value: 'Call Count', angle: -90, position: 'insideLeft', fill: '#9ca3af' }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar 
                    dataKey="count" 
                    radius={[4, 4, 0, 0]}
                  >
                    {chart_data.map((entry, index) => (
                      <Cell 
                        key={`cell-${index}`} 
                        fill={getBarColor(entry.bucket)}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              
              {/* Legend */}
              <div className="flex justify-center gap-8 mt-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500"></div>
                  <span className="text-gray-400">&lt;5 Critical</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                  <span className="text-gray-400">5-7 Low</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                  <span className="text-gray-400">7-8 OK</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500"></div>
                  <span className="text-gray-400">&gt;8 Good</span>
                </div>
              </div>
            </>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-500">
              No quality scores to display
            </div>
          )}
        </div>

      </div>
    </div>
  );
}