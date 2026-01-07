/**
 * Layer 1: Prompt Composition - Overview (2E Design)
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber } from '../../../utils/formatters';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';
import Layer1Table from '../../../components/stories/Layer1Table';

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
            <div className={`px-4 py-2 rounded-full border ${BASE_THEME.border.default} ${BASE_THEME.container.primary}`}>
              <span className={`text-sm font-semibold ${theme.text}`}>
                {Math.round(health_score)}% Health
              </span>
            </div>
          </div>
          <p className={`${BASE_THEME.text.muted} text-sm`}>
            Dashboard › Prompt Composition
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div
            onClick={() => navigate('/stories/system_prompt/calls?filter=all')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Avg System</div>
            <div className="text-2xl font-bold text-blue-400">{avg_system_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>{system_pct}% of prompt</div>
          </div>

          <div
            onClick={() => navigate('/stories/system_prompt/calls?filter=all')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Avg User</div>
            <div className="text-2xl font-bold text-green-400">{avg_user_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>{user_pct}% of prompt</div>
          </div>

          <div
            onClick={() => navigate('/stories/system_prompt/calls?filter=large')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Avg History</div>
            <div className="text-2xl font-bold text-orange-400">{avg_history_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>{history_pct}% of prompt</div>
          </div>

          <div
            onClick={() => navigate('/stories/system_prompt/calls?filter=all')}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
          >
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Cache Ready</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{cache_ready_count}/{total_operations}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Operations</div>
          </div>
        </div>

        {/* Composition Overview */}
        {composition_chart.length > 0 && (
          <div className={`mb-8 rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} overflow-hidden`}>
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
        <div className="mb-8">
          <Layer1Table
            data={detail_table.map(row => ({
              ...row,
              operation: row.operation_name,
              status_emoji: row.cache_emoji,
            }))}
            theme={theme}
            storyId="system_prompt"
            onRowClick={handleOperationClick}
            columns={[
              { key: 'avg_system_formatted', label: 'System', width: '12%' },
              { key: 'avg_user_formatted', label: 'User', width: '12%' },
              { key: 'avg_history_formatted', label: 'History', width: '12%' },
              { key: 'cache_emoji', label: 'Cache', width: '6%' },
              { key: 'call_count', label: 'Calls', width: '6%' },
            ]}
            renderMetricCells={(row) => (
              <>
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
                <td className={`py-3 px-4 text-right ${BASE_THEME.text.muted}`}>
                  {formatNumber(row.call_count)}
                </td>
              </>
            )}
          />
        </div>

        {/* Insight */}
        <div className={`mt-6 p-4 rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary}`}>
          <p className={`text-sm ${BASE_THEME.text.muted}`}>
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