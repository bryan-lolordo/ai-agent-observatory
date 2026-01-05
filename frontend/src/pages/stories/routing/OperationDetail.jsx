/**
 * Layer 2: Routing Patterns (All Routing Opportunities)
 *
 * Shows all routing patterns with full Layer2Table functionality.
 * Uses URL params for initial filters (from Layer 1 drill-down).
 */

import { useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import Layer2Table from '../../../components/stories/Layer2Table';
import { formatNumber, formatCurrency } from '../../../utils/formatters';

// Small stat badge for summary stats
function StatBadge({ label, value, color }) {
  return (
    <div className="px-4 py-2 bg-gray-800/50 rounded-lg border border-gray-700">
      <span className="text-xs text-gray-500">{label}: </span>
      <span className={`font-semibold ${color || 'text-gray-300'}`}>{value}</span>
    </div>
  );
}
import { useRoutingPatterns } from '../../../hooks/useCalls';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';

const STORY_ID = 'routing';
const theme = STORY_THEMES.routing;

export default function RoutingOperationDetail() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Fetch data with automatic timeRange handling
  const { data, loading, error, refetch, rawResponse } = useRoutingPatterns();

  // Get stats from rawResponse
  const stats = rawResponse?.stats || null;

  // Get initial filters from URL params
  const initialOperation = searchParams.get('operation');
  const initialAgent = searchParams.get('agent');
  const initialFilter = searchParams.get('filter');

  // Build initial filters object
  const initialFilters = useMemo(() => {
    const filters = {};
    if (initialOperation) filters.operation = [initialOperation];
    if (initialAgent) filters.agent_name = [initialAgent];
    return filters;
  }, [initialOperation, initialAgent]);

  // Navigation handlers
  const handleBack = () => {
    navigate('/stories/routing');
  };

  const handleRowClick = (pattern) => {
    // Navigate to Layer 3 - call detail using sample_call_id
    if (pattern.sample_call_id) {
      navigate(`/stories/routing/calls/${pattern.sample_call_id}`);
    }
  };

  // Loading state
  if (loading) return <StoryPageSkeleton />;

  // Error state
  if (error) {
    return (
      <div className={`min-h-screen ${BASE_THEME.container.tertiary} p-8`}>
        <PageContainer>
          <button
            onClick={handleBack}
            className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:underline`}
          >
            ← Back to Model Routing Overview
          </button>
          <div className={`${BASE_THEME.status.error.bg} border ${BASE_THEME.status.error.border} rounded-lg p-6`}>
            <h2 className={`text-xl font-bold ${BASE_THEME.status.error.textBold} mb-2`}>Error Loading Data</h2>
            <p className={BASE_THEME.text.secondary}>{error}</p>
            <button
              onClick={refetch}
              className={`mt-4 px-4 py-2 ${BASE_THEME.status.error.bgSolid} hover:bg-red-700 text-white rounded-lg`}
            >
              Retry
            </button>
          </div>
        </PageContainer>
      </div>
    );
  }

  // Calculate summary stats from data if not in rawResponse
  const totalPatterns = stats?.total_patterns || data.length;
  const totalSavable = stats?.total_savable_formatted || formatCurrency(data.reduce((sum, p) => sum + (p.savable || 0), 0));
  const downgradeCount = stats?.downgrade_count || data.filter(p => p.type === 'downgrade').length;
  const upgradeCount = stats?.upgrade_count || data.filter(p => p.type === 'upgrade').length;
  const keepCount = stats?.keep_count || data.filter(p => p.type === 'keep').length;

  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} ${BASE_THEME.text.primary}`}>
      {/* Story Navigation */}
      <StoryNavTabs activeStory={STORY_ID} />

      <PageContainer>

        {/* Back Button */}
        <button
          onClick={handleBack}
          className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:underline`}
        >
          ← Back to Model Routing Overview
        </button>

        {/* Page Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h1 className={`text-3xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-4xl">🔀</span>
              Routing Opportunities
              {(initialOperation || initialAgent) && (
                <span className="text-lg font-normal text-gray-400">
                  {initialAgent && initialOperation
                    ? `• ${initialAgent}.${initialOperation}`
                    : initialOperation || initialAgent
                  }
                </span>
              )}
            </h1>
          </div>
          <p className="text-gray-400">
            Dashboard &gt; Model Routing &gt; All Patterns
          </p>
        </div>

        {/* Summary Stats */}
        <div className="mb-6 flex flex-wrap gap-3">
          <StatBadge label="Patterns" value={formatNumber(totalPatterns)} color={theme.text} />
          <StatBadge label="Total Savable" value={totalSavable} color="text-green-400" />
          <StatBadge label="↓ Downgrade" value={downgradeCount} color="text-blue-400" />
          <StatBadge label="↑ Upgrade" value={upgradeCount} color="text-red-400" />
          <StatBadge label="✓ Keep" value={keepCount} color="text-green-400" />
        </div>

        {/* Layer2Table */}
        <Layer2Table
          storyId={STORY_ID}
          data={data}
          initialFilters={initialFilters}
          initialQuickFilter={initialFilter}
          onRowClick={handleRowClick}
          loading={loading}
        />

      </PageContainer>
    </div>
  );
}
