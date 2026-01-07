/**
 * Layer 1: Optimization Impact - Hierarchical Tracking View
 *
 * Features:
 * - Expandable rows: Agent -> Operation -> Story -> Fixes -> Calls
 * - Track optimization progress across all stories
 * - View baseline metrics and improvements
 * - Add/manage applied fixes
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';
import OptimizationHierarchy from '../../../components/stories/OptimizationHierarchy';
import { Code2, Table } from 'lucide-react';

export default function OptimizationImpact() {
  const navigate = useNavigate();
  const { data, loading, error } = useStory('optimization');
  const theme = STORY_THEMES.optimization;

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
    mode = 'tracking',
    hierarchy = { agents: [], total_stories: 0, total_pending: 0, total_complete: 0 },
    kpis = {},
  } = data || {};

  const {
    total_stories = 0,
    complete_stories = 0,
    pending_stories = 0,
    progress_pct = 0,
    avg_latency_formatted = '—',
    total_cost_formatted = '—',
    avg_quality_formatted = '—',
    cache_hit_rate_formatted = '—',
    total_cost_saved_formatted = '$0.00',
    total_latency_saved_formatted = '0.0s',
  } = kpis;

  const handleStoryClick = (story, call) => {
    // Navigate to the relevant story page with the call selected
    const storyRoutes = {
      latency: '/stories/latency',
      cache: '/stories/cache',
      cost: '/stories/cost',
      quality: '/stories/quality',
      routing: '/stories/routing',
      token: '/stories/token_imbalance',
      prompt: '/stories/system_prompt',
    };

    const route = storyRoutes[story.story_id];
    if (route && call) {
      navigate(`${route}/calls/${call.id}`);
    } else if (route) {
      navigate(route);
    }
  };

  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} ${BASE_THEME.text.primary}`}>
      <StoryNavTabs activeStory="optimization" />

      <PageContainer>
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <h1 className={`text-3xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-4xl">{theme.emoji}</span>
              {theme.name}
            </h1>
            <div className="flex items-center gap-2">
              {/* View Toggle */}
              <button
                className={`px-3 py-1.5 rounded text-sm ${theme.bg} text-white flex items-center gap-1.5`}
              >
                <Table className="w-4 h-4" />
                Table View
              </button>
              <button
                onClick={() => navigate('/stories/optimization/code-view')}
                className={`px-3 py-1.5 rounded text-sm ${BASE_THEME.text.muted} hover:${BASE_THEME.text.secondary} hover:${BASE_THEME.container.tertiary} transition-colors flex items-center gap-1.5`}
              >
                <Code2 className="w-4 h-4" />
                Code View
              </button>
            </div>
            <div className="flex items-center gap-4">
              <div className={`px-4 py-2 rounded-full border ${BASE_THEME.border.default} ${BASE_THEME.container.primary}`}>
                <span className={`text-sm font-semibold ${theme.text}`}>
                  {complete_stories}/{total_stories} Complete
                </span>
              </div>
              <div className={`px-4 py-2 rounded-full border ${BASE_THEME.border.default} ${BASE_THEME.container.primary}`}>
                <span className={`text-sm ${BASE_THEME.text.muted}`}>
                  Health: <span className={theme.text}>{health_score.toFixed(0)}%</span>
                </span>
              </div>
            </div>
          </div>
          <p className={`${BASE_THEME.text.muted} text-sm`}>
            Dashboard / Optimization Impact
          </p>
        </div>

        {/* KPI Cards - 2 rows */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          {/* Row 1: Current metrics */}
          <div className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4`}>
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Avg Latency</div>
            <div className={`text-2xl font-bold ${BASE_THEME.text.primary}`}>{avg_latency_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Current baseline</div>
          </div>

          <div className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4`}>
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Total Cost</div>
            <div className={`text-2xl font-bold ${BASE_THEME.text.primary}`}>{total_cost_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Last 7 days</div>
          </div>

          <div className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4`}>
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Avg Quality</div>
            <div className={`text-2xl font-bold ${BASE_THEME.text.primary}`}>{avg_quality_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Judge score</div>
          </div>

          <div className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4`}>
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Cache Hit Rate</div>
            <div className={`text-2xl font-bold ${BASE_THEME.text.primary}`}>{cache_hit_rate_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Current rate</div>
          </div>
        </div>

        {/* Row 2: Impact metrics - glowing green border */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className={`rounded-lg border border-green-500/50 shadow-[0_0_10px_rgba(34,197,94,0.2)] ${BASE_THEME.container.primary} p-4`}>
            <div className="text-xs text-green-500 uppercase tracking-wide mb-1">Progress</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{progress_pct.toFixed(0)}%</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>{complete_stories} of {total_stories} stories</div>
          </div>

          <div className={`rounded-lg border border-green-500/50 shadow-[0_0_10px_rgba(34,197,94,0.2)] ${BASE_THEME.container.primary} p-4`}>
            <div className="text-xs text-green-500 uppercase tracking-wide mb-1">Cost Saved</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{total_cost_saved_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>From completed fixes</div>
          </div>

          <div className={`rounded-lg border border-green-500/50 shadow-[0_0_10px_rgba(34,197,94,0.2)] ${BASE_THEME.container.primary} p-4`}>
            <div className="text-xs text-green-500 uppercase tracking-wide mb-1">Latency Saved</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{total_latency_saved_formatted}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Per call improvement</div>
          </div>

          <div className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4`}>
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Pending</div>
            <div className="text-2xl font-bold text-yellow-400">{pending_stories}</div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Stories to optimize</div>
          </div>
        </div>

        {/* Main Hierarchy Table */}
        <div className={`rounded-lg ${BASE_THEME.container.primary} overflow-hidden`}>
          <div className={`h-1 ${theme.bg}`} />
          <div className={`p-4 border-b ${BASE_THEME.border.default} flex items-center justify-between`}>
            <h3 className={`text-sm font-medium ${theme.text} uppercase tracking-wide`}>
              Optimization Tracking
            </h3>
            <div className={`flex items-center gap-4 text-xs ${BASE_THEME.text.muted}`}>
              <span>{hierarchy.total_agents || 0} agents</span>
              <span>{hierarchy.total_operations || 0} operations</span>
              <span>{hierarchy.total_stories || 0} stories</span>
            </div>
          </div>

          <OptimizationHierarchy
            hierarchy={hierarchy}
            onStoryClick={handleStoryClick}
          />
        </div>

        {/* Help text */}
        <div className={`mt-6 p-4 rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary}`}>
          <p className={`text-sm ${BASE_THEME.text.muted}`}>
            <span className="text-green-400 font-medium">How it works:</span> Issues are automatically detected from your call data.
            Click on a story to view details, then add fixes as you implement them.
            Track your progress and see the impact of your optimizations over time.
          </p>
        </div>

      </PageContainer>
    </div>
  );
}
