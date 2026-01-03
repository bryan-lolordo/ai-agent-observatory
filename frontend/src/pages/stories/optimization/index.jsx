/**
 * Layer 1: Optimization Impact - Overview (2E Design)
 */

import { useNavigate } from 'react-router-dom';
import { useStory } from '../../../hooks/useStories';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';

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
            <div className="px-4 py-2 rounded-full border border-gray-700 bg-gray-900">
              <span className={`text-sm font-semibold ${theme.text}`}>
                {targets_met}/{total_targets} Targets Met
              </span>
            </div>
          </div>
          <p className="text-gray-500 text-sm">
            Dashboard › Optimization Impact
          </p>
        </div>

        {/* Status Banner */}
        <div className="mb-8 rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
          <div className={`h-1 ${theme.bg}`} />
          <div className="p-5">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">⏳</span>
              <h2 className={`text-lg font-bold ${theme.text}`}>Baseline Collection Mode</h2>
            </div>
            <p className="text-gray-400 text-sm">
              Collecting baseline metrics. Implement optimizations from Stories 1-7, then return here to measure impact.
            </p>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div 
            onClick={() => navigate('/stories/optimization/calls?filter=slow')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Avg Latency</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{avg_latency_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">Current baseline</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/optimization/calls?filter=expensive')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Total Cost</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{total_cost_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">Last 7 days</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/optimization/calls?filter=low_quality')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Avg Quality</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{avg_quality_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">Judge score</div>
          </div>
          
          <div 
            onClick={() => navigate('/stories/optimization/calls?filter=all')}
            className="rounded-lg border border-gray-700 bg-gray-900 p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
          >
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Cache Hit Rate</div>
            <div className={`text-2xl font-bold ${theme.text}`}>{cache_hit_rate_formatted}</div>
            <div className="text-xs text-gray-500 mt-1">Current rate</div>
          </div>
        </div>

        {/* Baselines Table */}
        <div className="mb-8 rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
          <div className={`h-1 ${theme.bg}`} />
          <div className="p-4 border-b border-gray-700">
            <h3 className={`text-sm font-medium ${theme.text} uppercase tracking-wide`}>
              📊 Baseline Metrics vs Targets
            </h3>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ tableLayout: 'fixed' }}>
              <thead className="bg-gray-800/50">
                <tr className="border-b border-gray-700">
                  <th style={{ width: '30%' }} className="text-left py-3 px-4 text-gray-400 font-medium">Metric</th>
                  <th style={{ width: '15%' }} className="text-right py-3 px-4 text-gray-400 font-medium">Current</th>
                  <th style={{ width: '15%' }} className="text-right py-3 px-4 text-gray-400 font-medium">Target</th>
                  <th style={{ width: '15%' }} className="text-right py-3 px-4 text-gray-400 font-medium">Gap</th>
                  <th style={{ width: '10%' }} className="text-center py-3 px-4 text-gray-400 font-medium">Status</th>
                  <th style={{ width: '15%' }} className="text-center py-3 px-4 text-gray-400 font-medium">Priority</th>
                </tr>
              </thead>
              <tbody>
                {baselines.length > 0 ? (
                  baselines.map((baseline, idx) => (
                    <tr key={idx} className="border-b border-gray-800">
                      <td className="py-3 px-4 text-gray-300 font-medium">{baseline.metric}</td>
                      <td className="py-3 px-4 text-right text-gray-300">{baseline.current_formatted}</td>
                      <td className="py-3 px-4 text-right text-gray-500">{baseline.target_formatted}</td>
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
        <div className="rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
          <div className={`h-1 ${theme.bg}`} />
          <div className="p-4 border-b border-gray-700">
            <h3 className={`text-sm font-medium ${theme.text} uppercase tracking-wide`}>
              🎯 Pending Optimizations
              <span className="text-gray-500 normal-case ml-2 font-normal">from Stories 1-7</span>
            </h3>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ tableLayout: 'fixed' }}>
              <thead className="bg-gray-800/50">
                <tr className="border-b border-gray-700">
                  <th style={{ width: '14%' }} className="text-left py-3 px-4 text-gray-400 font-medium">Story</th>
                  <th style={{ width: '14%' }} className="text-left py-3 px-4 text-gray-400 font-medium">Target</th>
                  <th style={{ width: '22%' }} className="text-left py-3 px-4 text-gray-400 font-medium">Issue</th>
                  <th style={{ width: '26%' }} className="text-left py-3 px-4 text-gray-400 font-medium">Recommendation</th>
                  <th style={{ width: '14%' }} className="text-left py-3 px-4 text-gray-400 font-medium">Expected Impact</th>
                  <th style={{ width: '10%' }} className="text-center py-3 px-4 text-gray-400 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {pending_optimizations.length > 0 ? (
                  pending_optimizations.map((opt, idx) => (
                    <tr 
                      key={idx} 
                      onClick={() => handleOptimizationClick(opt)}
                      className="border-b border-gray-800 cursor-pointer hover:bg-gray-800/50 transition-colors"
                    >
                      <td className="py-3 px-4">
                        <span className={theme.text}>Story {opt.story}</span>
                        <span className="text-gray-500 ml-2 text-xs">{opt.story_name}</span>
                      </td>
                      <td className="py-3 px-4 font-mono text-purple-400">{opt.target}</td>
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
                      No pending optimizations. Your system is well-optimized! 🎉
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Coming Soon Note */}
        <div className="mt-6 p-4 rounded-lg border border-gray-700 bg-gray-900">
          <p className="text-sm text-gray-400">
            💡 <span className="text-blue-400">Coming Soon:</span> Track optimizations and see before/after comparisons. 
            Implement changes from Stories 1-7, then mark them complete here to measure impact.
          </p>
        </div>

      </PageContainer>
    </div>
  );
}