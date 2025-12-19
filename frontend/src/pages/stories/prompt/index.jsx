/**
 * Layer 1: Prompt Composition - Overview
 * 
 * Shows prompt structure across operations with cache readiness.
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import KPICard from '../../../components/common/KPICard';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, truncateText } from '../../../utils/formatters';

export default function PromptComposition() {
  const navigate = useNavigate();
  const { data, loading, error } = useStory('system_prompt');
  const theme = STORY_THEMES.system_prompt;

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

  // Navigate to Layer 2
  const handleOperationClick = (row) => {
    navigate(`/stories/system_prompt/operations/${encodeURIComponent(row.agent_name)}/${encodeURIComponent(row.operation_name)}`);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <StoryNavTabs activeStory="system_prompt" />

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
            Dashboard &gt; Prompt Composition
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <KPICard
            theme={theme}
            title="🔷 Avg System"
            value={avg_system_formatted}
            subtext={`${system_pct}% of prompt`}
          />
          <KPICard
            theme={theme}
            title="🟢 Avg User"
            value={avg_user_formatted}
            subtext={`${user_pct}% of prompt`}
          />
          <KPICard
            theme={theme}
            title="🟠 Avg History"
            value={avg_history_formatted}
            subtext={`${history_pct}% of prompt`}
          />
          <KPICard
            theme={theme}
            title="✅ Cache Ready"
            value={`${cache_ready_count}/${total_operations}`}
            subtext="Operations"
          />
        </div>

        {/* Composition Overview */}
        {composition_chart.length > 0 && (
          <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gray-900 p-6`}>
            <h3 className={`text-lg font-semibold ${theme.text} mb-4`}>
              📊 Prompt Composition Overview
            </h3>
            
            <div className="flex items-center gap-8">
              {/* Stacked bar visualization */}
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
        )}

        {/* Operations Table */}
        <div className={`rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          <div className={`${theme.bgLight} p-4 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              📋 Operations (click row to analyze)
            </h3>
          </div>
          
          <div className="overflow-x-auto overflow-y-auto max-h-96 story-scrollbar-thin prompt">
            <table className="w-full text-sm">
              <thead className="bg-gray-800 sticky top-0">
                <tr className={`border-b-2 ${theme.border}`}>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Operation</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Agent</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>System</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>User</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>History</th>
                  <th className={`text-center py-3 px-4 ${theme.textLight}`}>Cache</th>
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
                      <td className={`py-3 px-4 font-mono ${theme.text} font-semibold`}>
                        {truncateText(row.operation_name, 25)}
                      </td>
                      <td className="py-3 px-4 text-gray-400">
                        {row.agent_name || '—'}
                      </td>
                      <td className="py-3 px-4 text-right text-purple-400">
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
                      <td className="py-3 px-4 text-right text-gray-300">
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
        <div className={`mt-6 p-4 rounded-lg border ${theme.border} bg-gray-900`}>
          <p className="text-sm text-gray-400">
            ✅ <span className="text-green-400">{cache_ready_count}</span> operations have static system prompts → cache ready
            {total_operations - cache_ready_count > 0 && (
              <span className="ml-4">
                ⚠️ <span className="text-yellow-400">{total_operations - cache_ready_count}</span> operations need restructuring
              </span>
            )}
          </p>
        </div>

      </div>
    </div>
  );
}