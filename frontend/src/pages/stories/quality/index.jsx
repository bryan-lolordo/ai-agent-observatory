/**
 * Layer 1: Quality Monitoring - Overview (2E Design)
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, truncateText } from '../../../utils/formatters';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

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
    avg_quality_formatted = '—',
    low_quality_count = 0,
    error_count = 0,
    error_rate_formatted = '0%',
    hallucination_count = 0,
  } = summary;

  const getBarColor = (bucket) => {
    if (bucket < 5) return '#ef4444';
    if (bucket < 7) return '#f97316';
    if (bucket < 8) return '#eab308';
    return '#22c55e';
  };

  const handleOperationClick = (row) => {
    navigate(`/stories/quality/operations/${encodeURIComponent(row.agent_name)}/${encodeURIComponent(row.operation_name)}`);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <StoryNavTabs activeStory="quality" />

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
            Dashboard › Quality Monitoring
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div 
            onClick={() => navigate('/stories/quality/calls?filter=all')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Avg Quality</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{avg_quality_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">{formatNumber(evaluated_calls)} of {formatNumber(total_calls)} evaluated</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/quality/calls?filter=low')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Low Quality Ops</div>
            <div className="text-2xl font-bold text-red-400">{low_quality_count}</div>
            <div className="text-xs text-gray-500 mt-1">Operations below 7.0</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/quality/calls?filter=errors')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Error Rate</div>
            <div className="text-2xl font-bold text-red-400">{error_rate_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">{formatNumber(error_count)} errors</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/quality/calls?filter=hallucinations')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Hallucinations</div>
            <div className="text-2xl font-bold text-yellow-400">{hallucination_count}</div>
            <div className="text-xs text-gray-500 mt-1">Detected in responses</div>
          </div>
        </div>

        {/* Top Offender */}
        {top_offender && (
          <div 
            onClick={() => navigate(`/stories/quality/operations/${encodeURIComponent(top_offender.agent)}/${encodeURIComponent(top_offender.operation)}`)}
            className="mb-8 rounded-lg border border-gray-700 bg-gray-900 overflow-hidden cursor-pointer hover:border-gray-600 transition-all"
          >
            <div className={`h-1 ${theme.bg}`} />
            <div className="p-5">
              <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">
                🎯 Worst Quality Operation
              </h3>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl font-bold text-purple-400">{top_offender.agent}</span>
                <span className="text-gray-500">.</span>
                <span className={`text-xl font-bold ${theme.text} font-mono`}>{top_offender.operation}</span>
              </div>
              <div className="flex gap-6 text-sm text-gray-400">
                <span>Score: <span className="text-gray-200">{top_offender.avg_score_formatted}</span></span>
                <span>Calls: <span className="text-gray-200">{formatNumber(top_offender.call_count)}</span></span>
                {top_offender.error_count > 0 && (
                  <span className="text-red-400">❌ {top_offender.error_count} errors</span>
                )}
                {top_offender.hallucination_count > 0 && (
                  <span className="text-yellow-400">⚠️ {top_offender.hallucination_count} hallucinations</span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Operations Table */}
        <div className="mb-8 rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
          <div className={`h-1 ${theme.bg}`} />
          <div className="p-4 border-b border-gray-700">
            <h3 className="text-xs font-medium text-gray-300 uppercase tracking-wide">
              📊 Operations
              <span className="text-gray-500 normal-case ml-2 font-normal">Click row to drill down</span>
            </h3>
          </div>
          
          <div className="overflow-x-auto overflow-y-auto max-h-80">
            <table className="w-full text-sm">
              <thead className="bg-gray-800/50">
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Status</th>
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Agent</th>
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Operation</th>
                  <th className="text-center py-3 px-4 text-gray-400 font-medium">Avg Score</th>
                  <th className="text-center py-3 px-4 text-gray-400 font-medium">Min</th>
                  <th className="text-center py-3 px-4 text-gray-400 font-medium">Errors</th>
                  <th className="text-center py-3 px-4 text-gray-400 font-medium">Halluc.</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Calls</th>
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
                      <td className="py-3 px-4 text-right text-gray-400">
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

        {/* Chart */}
        <div className="rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
          <div className={`h-1 ${theme.bg}`} />
          <div className="p-6">
            <h3 className="text-xs font-medium text-gray-300 uppercase tracking-wide mb-6">
              📊 Quality Score Distribution
            </h3>
            
            {chart_data.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={chart_data} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis 
                      dataKey="label" 
                      stroke="#6b7280"
                      tick={{ fill: '#9ca3af', fontSize: 11 }}
                    />
                    <YAxis 
                      stroke="#6b7280"
                      tick={{ fill: '#9ca3af', fontSize: 11 }}
                    />
                    <Tooltip 
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        color: '#f3f4f6'
                      }}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {chart_data.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={getBarColor(entry.bucket)} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                
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
    </div>
  );
}