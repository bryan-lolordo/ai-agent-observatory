/**
 * Layer 1: Prompt Composition - Overview (2E Design)
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, truncateText } from '../../../utils/formatters';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';

export default function PromptComposition() {
  const navigate = useNavigate();
  const { data, loading, error } = useStory('system_prompt');
  const theme = STORY_THEMES.system_prompt;

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
    composition_chart = [],
    detail_table = [],
  } = data || {};

  const {
    avg_system_formatted = '0',
    avg_user_formatted = '0',
    avg_history_formatted = '0',
    system_pct = 0,
    user_pct = 0,
    history_pct = 0,
    cache_ready_count = 0,
    total_operations = 0,
  } = summary;

  const handleOperationClick = (row) => {
    navigate(`/stories/system_prompt/operations/${encodeURIComponent(row.agent_name)}/${encodeURIComponent(row.operation_name)}`);
  };

  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} ${BASE_THEME.text.primary}`}>
      <StoryNavTabs activeStory="system_prompt" />

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
            Dashboard › Prompt Composition
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div 
            onClick={() => navigate('/stories/system_prompt/calls?filter=all')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Avg System</div>
            <div className="text-2xl font-bold text-blue-400">{avg_system_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">{system_pct}% of prompt</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/system_prompt/calls?filter=all')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Avg User</div>
            <div className="text-2xl font-bold text-green-400">{avg_user_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">{user_pct}% of prompt</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/system_prompt/calls?filter=large')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Avg History</div>
            <div className="text-2xl font-bold text-orange-400">{avg_history_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">{history_pct}% of prompt</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/system_prompt/calls?filter=all')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Cache Ready</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{cache_ready_count}/{total_operations}</div>
            <div className="text-xs text-gray-500 mt-1">Operations</div>
          </div>
        </div>

        {/* Composition Overview */}
        {composition_chart.length > 0 && (
          <div className="mb-8 rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
            <div className={`h-1 ${theme.bg}`} />
            <div className="p-6">
              <h3 className={`text-sm font-medium ${theme.text} uppercase tracking-wide mb-4`}>
                📊 Prompt Composition Overview
              </h3>
              
              <div className="flex items-center gap-8">
                {/* Stacked bar */}
                <div className="flex-1">
                  <div className="flex h-12 rounded-lg overflow-hidden">
                    {composition_chart.map((item, idx) => (
                      <div
                        key={idx}
                        style={{ 
                          width: `${item.percentage}%`,
                          backgroundColor: item.color,
                        }}
                        className="flex items-center justify-center text-white text-sm font-semibold"
                      >
                        {item.percentage > 10 && `${item.percentage}%`}
                      </div>
                    ))}
                  </div>
                </div>
                
                {/* Legend */}
                <div className="flex flex-col gap-2 text-sm">
                  {composition_chart.map((item, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <div 
                        className="w-4 h-4 rounded"
                        style={{ backgroundColor: item.color }}
                      ></div>
                      <span className="text-gray-300">
                        {item.component}: {item.tokens.toLocaleString()} tokens ({item.percentage}%)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Operations Table */}
        <div className="rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
          <div className={`h-1 ${theme.bg}`} />
          <div className="p-4 border-b border-gray-700">
            <h3 className={`text-sm font-medium ${theme.text} uppercase tracking-wide`}>
              📊 Operations
              <span className="text-gray-500 normal-case ml-2 font-normal">Click row to analyze</span>
            </h3>
          </div>
          
          <div className="overflow-x-auto overflow-y-auto max-h-96">
            <table className="w-full text-sm" style={{ tableLayout: 'fixed' }}>
              <thead className="bg-gray-800/50">
                <tr className="border-b border-gray-700">
                  <th style={{ width: '16%' }} className="text-left py-3 px-4 text-gray-400 font-medium">Agent</th>
                  <th style={{ width: '36%' }} className="text-left py-3 px-4 text-gray-400 font-medium">Operation</th>
                  <th style={{ width: '12%' }} className="text-right py-3 px-4 text-gray-400 font-medium">System</th>
                  <th style={{ width: '12%' }} className="text-right py-3 px-4 text-gray-400 font-medium">User</th>
                  <th style={{ width: '12%' }} className="text-right py-3 px-4 text-gray-400 font-medium">History</th>
                  <th style={{ width: '6%' }} className="text-center py-3 px-4 text-gray-400 font-medium">Cache</th>
                  <th style={{ width: '6%' }} className="text-right py-3 px-4 text-gray-400 font-medium">Calls</th>
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
                      <td className="py-3 px-4 font-semibold text-purple-400">
                        {row.agent_name || '—'}
                      </td>
                      <td className={`py-3 px-4 font-mono ${theme.text}`}>
                        {truncateText(row.operation_name, 25)}
                      </td>
                      <td className="py-3 px-4 text-right text-blue-400">
                        {row.avg_system_formatted}
                      </td>
                      <td className="py-3 px-4 text-right text-green-400">
                        {row.avg_user_formatted}
                      </td>
                      <td className="py-3 px-4 text-right text-orange-400">
                        {row.avg_history_formatted}
                      </td>
                      <td className="py-3 px-4 text-center text-lg">
                        {row.cache_emoji}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-400">
                        {formatNumber(row.call_count)}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-gray-500">
                      No prompt data available
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Insight */}
        <div className="mt-6 p-4 rounded-lg border border-gray-700 bg-gray-900">
          <p className="text-sm text-gray-400">
            ✅ <span className="text-green-400">{cache_ready_count}</span> operations have static system prompts → cache ready
            {total_operations - cache_ready_count > 0 && (
              <span className="ml-4">
                ⚠️ <span className="text-yellow-400">{total_operations - cache_ready_count}</span> operations need restructuring
              </span>
            )}
          </p>
        </div>

      </PageContainer>
    </div>
  );
}