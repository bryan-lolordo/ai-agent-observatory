/**
 * Layer 1: Optimization Impact - Baseline Mode
 * 
 * MVP: Shows current metrics vs targets and pending optimizations.
 * Future: Will show before/after comparisons when tracking is implemented.
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import KPICard from '../../../components/common/KPICard';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';

export default function OptimizationImpact() {
  const navigate = useNavigate();
  const { data, loading, error } = useStory('optimization');
  const theme = STORY_THEMES.optimization;

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
    mode = 'baseline',
    summary = {},
    kpis = {},
    baselines = [],
    pending_optimizations = [],
  } = data || {};

  const {
    targets_met = 0,
    total_targets = 0,
  } = summary;

  const {
    avg_latency_formatted = '—',
    total_cost_formatted = '—',
    avg_quality_formatted = '—',
    cache_hit_rate_formatted = '—',
  } = kpis;

  // Status colors
  const getStatusColor = (status) => {
    switch (status) {
      case 'met': return 'text-green-400';
      case 'close': return 'text-yellow-400';
      case 'far': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getStatusEmoji = (status) => {
    switch (status) {
      case 'met': return '✅';
      case 'close': return '🟡';
      case 'far': return '🔴';
      default: return '⚪';
    }
  };

  const getPriorityBadge = (priority) => {
    switch (priority) {
      case 'high': return 'bg-red-600 text-white';
      case 'medium': return 'bg-yellow-600 text-white';
      case 'low': return 'bg-green-600 text-white';
      default: return 'bg-gray-600 text-white';
    }
  };

  // Navigate to story for optimization
  const handleOptimizationClick = (opt) => {
    const storyRoutes = {
      1: '/stories/latency',
      2: '/stories/cache',
      3: '/stories/routing',
      4: '/stories/quality',
      5: '/stories/token_imbalance',
      6: '/stories/system_prompt',
      7: '/stories/cost',
    };
    const route = storyRoutes[opt.story];
    if (route) {
      navigate(route);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <StoryNavTabs activeStory="optimization" />

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
                {targets_met}/{total_targets} Targets Met
              </span>
            </div>
          </div>
          <p className="text-gray-400">
            Dashboard &gt; Optimization Impact
          </p>
        </div>

        {/* Status Banner */}
        <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gradient-to-br ${theme.gradient} p-6`}>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl">⏳</span>
            <h2 className={`text-xl font-bold ${theme.text}`}>Baseline Collection Mode</h2>
          </div>
          <p className="text-gray-300">
            Collecting baseline metrics. Implement optimizations from Stories 1-7, then return here to measure impact.
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <KPICard
            theme={theme}
            title="⏱️ Avg Latency"
            value={avg_latency_formatted}
            subtext="Current baseline"
          />
          <KPICard
            theme={theme}
            title="💵 Total Cost"
            value={total_cost_formatted}
            subtext="Last 7 days"
          />
          <KPICard
            theme={theme}
            title="⭐ Avg Quality"
            value={avg_quality_formatted}
            subtext="Judge score"
          />
          <KPICard
            theme={theme}
            title="💾 Cache Hit Rate"
            value={cache_hit_rate_formatted}
            subtext="Current rate"
          />
        </div>

        {/* Baselines Table */}
        <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          <div className={`${theme.bgLight} p-4 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              📊 Baseline Metrics vs Targets
            </h3>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-800">
                <tr className={`border-b-2 ${theme.border}`}>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Metric</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Current</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Target</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Gap</th>
                  <th className={`text-center py-3 px-4 ${theme.textLight}`}>Status</th>
                  <th className={`text-center py-3 px-4 ${theme.textLight}`}>Priority</th>
                </tr>
              </thead>
              <tbody>
                {baselines.length > 0 ? (
                  baselines.map((baseline, idx) => (
                    <tr key={idx} className="border-b border-gray-800">
                      <td className="py-3 px-4 text-gray-300 font-medium">{baseline.metric}</td>
                      <td className="py-3 px-4 text-right text-gray-300">{baseline.current_formatted}</td>
                      <td className="py-3 px-4 text-right text-gray-400">{baseline.target_formatted}</td>
                      <td className={`py-3 px-4 text-right ${getStatusColor(baseline.status)}`}>
                        {baseline.gap}
                      </td>
                      <td className="py-3 px-4 text-center text-lg">
                        {getStatusEmoji(baseline.status)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className={`px-2 py-1 rounded text-xs font-semibold ${getPriorityBadge(baseline.priority)}`}>
                          {baseline.priority}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-gray-500">
                      No baseline data available
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pending Optimizations */}
        <div className={`rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          <div className={`${theme.bgLight} p-4 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              🎯 Pending Optimizations (from Stories 1-7)
            </h3>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-800">
                <tr className={`border-b-2 ${theme.border}`}>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Story</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Target</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Issue</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Recommendation</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Expected Impact</th>
                  <th className={`text-center py-3 px-4 ${theme.textLight}`}>Status</th>
                </tr>
              </thead>
              <tbody>
                {pending_optimizations.length > 0 ? (
                  pending_optimizations.map((opt, idx) => (
                    <tr 
                      key={idx} 
                      onClick={() => handleOptimizationClick(opt)}
                      className={`border-b border-gray-800 cursor-pointer transition-all hover:bg-gradient-to-r hover:${theme.gradient} hover:border-l-4 hover:${theme.border}`}
                    >
                      <td className="py-3 px-4">
                        <span className={theme.text}>Story {opt.story}</span>
                        <span className="text-gray-500 ml-2 text-xs">{opt.story_name}</span>
                      </td>
                      <td className="py-3 px-4 font-mono text-gray-300">{opt.target}</td>
                      <td className="py-3 px-4 text-gray-400">{opt.issue}</td>
                      <td className="py-3 px-4 text-gray-300">{opt.recommendation}</td>
                      <td className="py-3 px-4 text-green-400">{opt.expected_impact}</td>
                      <td className="py-3 px-4 text-center">
                        <span className="px-2 py-1 bg-gray-700 rounded text-xs text-gray-300">
                          ⏳ TODO
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-gray-500">
                      No pending optimizations identified. Your system is well-optimized! 🎉
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Coming Soon Note */}
        <div className={`mt-6 p-4 rounded-lg border ${theme.border} bg-gray-900`}>
          <p className="text-sm text-gray-400">
            💡 <span className="text-blue-400">Coming Soon:</span> Track optimizations and see before/after comparisons. 
            Implement changes from Stories 1-7, then mark them complete here to measure impact.
          </p>
        </div>

      </div>
    </div>
  );
}