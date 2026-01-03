/**
 * Layer 1: Quality Monitoring - Overview (2E Design)
 * 
 * Updated to use BASE_THEME for all colors - no hardcoded grays!
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, truncateText } from '../../../utils/formatters';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';

export default function Quality() {
  const navigate = useNavigate();
  const { data, loading, error } = useStory('quality');
  const theme = STORY_THEMES.quality;

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
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} ${BASE_THEME.text.primary}`}>
      <StoryNavTabs activeStory="quality" />

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
            Dashboard › Quality Monitoring
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div 
            onClick={() => navigate('/stories/quality/calls?filter=all')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Avg Quality</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{avg_quality_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>{formatNumber(evaluated_calls)} of {formatNumber(total_calls)} evaluated</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/quality/calls?filter=low')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Low Quality Ops</div>
            <div className={`text-2xl font-bold ${BASE_THEME.status.error.text}`}>{low_quality_count}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Operations below 7.0</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/quality/calls?filter=errors')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Error Rate</div>
            <div className={`text-2xl font-bold ${BASE_THEME.status.error.text}`}>{error_rate_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>{formatNumber(error_count)} errors</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/quality/calls?filter=hallucinations')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Hallucinations</div>
            <div className={`text-2xl font-bold ${BASE_THEME.status.warning.text}`}>{hallucination_count}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Detected in responses</div>
          </div>
        </div>

        {/* Top Offender */}
        {top_offender && (
          <div 
            onClick={() => navigate(`/stories/quality/operations/${encodeURIComponent(top_offender.agent)}/${encodeURIComponent(top_offender.operation)}`)}
            className={`mb-8 rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} overflow-hidden cursor-pointer hover:${BASE_THEME.border.hover} transition-all`}
          >
            <div className={`h-1 ${theme.bg}`} />
            <div className="p-5">
              <h3 className={`text-xs font-medium ${BASE_THEME.text.muted} uppercase tracking-wide mb-2`}>
                🎯 Worst Quality Operation
              </h3>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl font-bold text-purple-400">{top_offender.agent}</span>
                <span className={BASE_THEME.text.muted}>.</span>
                <span className={`text-xl font-bold ${theme.text} font-mono`}>{top_offender.operation}</span>
              </div>
              <div className={`flex gap-6 text-sm ${BASE_THEME.text.muted}`}>
                <span>Score: <span className={BASE_THEME.text.secondary}>{top_offender.avg_score_formatted}</span></span>
                <span>Calls: <span className={BASE_THEME.text.secondary}>{formatNumber(top_offender.call_count)}</span></span>
                {top_offender.error_count > 0 && (
                  <span className={BASE_THEME.status.error.text}>❌ {top_offender.error_count} errors</span>
                )}
                {top_offender.hallucination_count > 0 && (
                  <span className={BASE_THEME.status.warning.text}>⚠️ {top_offender.hallucination_count} hallucinations</span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Operations Table */}
        <div className={`mb-8 rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} overflow-hidden`}>
          <div className={`h-1 ${theme.bg}`} />
          <div className={`p-4 border-b ${BASE_THEME.border.default}`}>
            <h3 className={`text-xs font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide`}>
              📊 Operations
              <span className={`${BASE_THEME.text.muted} normal-case ml-2 font-normal`}>Click row to drill down</span>
            </h3>
          </div>
          
          <div className="overflow-x-auto overflow-y-auto max-h-80">
            <table className="w-full text-sm" style={{ tableLayout: 'fixed' }}>
              <thead className={BASE_THEME.container.secondary}>
                <tr className={`border-b ${BASE_THEME.border.default}`}>
                  <th style={{ width: '4%' }} className={`text-left py-3 px-4 ${BASE_THEME.text.muted} font-medium`}>Status</th>
                  <th style={{ width: '14%' }} className={`text-left py-3 px-4 ${BASE_THEME.text.muted} font-medium`}>Agent</th>
                  <th style={{ width: '34%' }} className={`text-left py-3 px-4 ${BASE_THEME.text.muted} font-medium`}>Operation</th>
                  <th style={{ width: '12%' }} className={`text-center py-3 px-4 ${BASE_THEME.text.muted} font-medium`}>Avg Score</th>
                  <th style={{ width: '9%' }} className={`text-center py-3 px-4 ${BASE_THEME.text.muted} font-medium`}>Min</th>
                  <th style={{ width: '9%' }} className={`text-center py-3 px-4 ${BASE_THEME.text.muted} font-medium`}>Errors</th>
                  <th style={{ width: '9%' }} className={`text-center py-3 px-4 ${BASE_THEME.text.muted} font-medium`}>Halluc.</th>
                  <th style={{ width: '9%' }} className={`text-right py-3 px-4 ${BASE_THEME.text.muted} font-medium`}>Calls</th>
                </tr>
              </thead>
              <tbody>
                {detail_table.length > 0 ? (
                  detail_table.map((row, idx) => (
                    <tr
                      key={idx}
                      onClick={() => handleOperationClick(row)}
                      className={`border-b ${BASE_THEME.border.default} cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
                    >
                      <td className="py-3 px-4 text-lg">{row.status_emoji}</td>
                      <td className="py-3 px-4 font-semibold text-purple-400">
                        {row.agent_name}
                      </td>
                      <td className={`py-3 px-4 font-mono ${theme.text}`}>
                        {truncateText(row.operation_name, 25)}
                      </td>
                      <td className={`py-3 px-4 text-center font-bold ${
                        row.status === 'good' ? BASE_THEME.status.success.text :
                        row.status === 'ok' ? BASE_THEME.status.warning.text :
                        row.status === 'low' ? 'text-orange-400' :
                        row.status === 'critical' ? BASE_THEME.status.error.text :
                        BASE_THEME.text.muted
                      }`}>
                        {row.avg_score_formatted}
                      </td>
                      <td className={`py-3 px-4 text-center ${BASE_THEME.text.muted}`}>
                        {row.min_score_formatted}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {row.error_count > 0 ? (
                          <span className={BASE_THEME.status.error.text}>❌ {row.error_count}</span>
                        ) : (
                          <span className="text-gray-600">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {row.hallucination_count > 0 ? (
                          <span className={BASE_THEME.status.warning.text}>⚠️ {row.hallucination_count}</span>
                        ) : (
                          <span className="text-gray-600">—</span>
                        )}
                      </td>
                      <td className={`py-3 px-4 text-right ${BASE_THEME.text.muted}`}>
                        {formatNumber(row.call_count)}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className={`py-8 text-center ${BASE_THEME.text.muted}`}>
                      No quality data available
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Chart */}
        <div className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} overflow-hidden`}>
          <div className={`h-1 ${theme.bg}`} />
          <div className="p-6">
            <h3 className={`text-xs font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide mb-6`}>
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
                    <span className={BASE_THEME.text.muted}>&lt;5 Critical</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                    <span className={BASE_THEME.text.muted}>5-7 Low</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                    <span className={BASE_THEME.text.muted}>7-8 OK</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <span className={BASE_THEME.text.muted}>&gt;8 Good</span>
                  </div>
                </div>
              </>
            ) : (
              <div className={`h-64 flex items-center justify-center ${BASE_THEME.text.muted}`}>
                No quality scores to display
              </div>
            )}
          </div>
        </div>

      </PageContainer>
    </div>
  );
}