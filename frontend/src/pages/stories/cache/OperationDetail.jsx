/**
 * Layer 2: Cache Calls (All Cache Patterns)
 * 
 * Shows all cacheable patterns with full Layer2Table functionality.
 * Uses URL params for initial filters (from Layer 1 drill-down).
 */

import { useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import Layer2Table from '../../../components/stories/Layer2Table';
import { formatNumber, formatCurrency } from '../../../utils/formatters';
import { useCachePatterns } from '../../../hooks/useCalls';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';

const STORY_ID = 'cache';
const theme = STORY_THEMES.cache;

export default function CacheOperationDetail() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // Fetch data with automatic timeRange handling
  const { data, loading, error, refetch } = useCachePatterns();
  
  // Get initial filters from URL params
  const initialOperation = searchParams.get('operation');
  const initialAgent = searchParams.get('agent');
  
  // Build initial filters object
  const initialFilters = useMemo(() => {
    const filters = {};
    if (initialOperation) filters.operation = [initialOperation];
    if (initialAgent) filters.agent_name = [initialAgent];
    return filters;
  }, [initialOperation, initialAgent]);

  // Navigation handlers
  const handleBack = () => {
    navigate('/stories/cache');
  };

  const handleRowClick = (pattern) => {
    // Navigate to Layer 3 - pattern detail using existing route format
    navigate(`/stories/cache/operations/${encodeURIComponent(pattern.agent_name)}/${encodeURIComponent(pattern.operation)}/groups/${pattern.group_id}`);
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
            ← Back to Cache Overview
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

  // Calculate summary stats
  const totalWasted = data.reduce((sum, p) => sum + (p.wasted_cost || 0), 0);
  const totalRepeats = data.reduce((sum, p) => sum + (p.repeat_count || 0), 0);
  const exactMatchCount = data.filter(p => p.cache_type === 'exact').length;
  const highValueCount = data.filter(p => p.cache_type === 'high_value').length;

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
          ← Back to Cache Overview
        </button>

        {/* Page Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h1 className={`text-3xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-4xl">💾</span>
              Cache Opportunities
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
            Dashboard &gt; Caching Strategy &gt; All Patterns
          </p>
        </div>

        {/* Stat Badges Row */}
        <div className="mb-6 flex flex-wrap gap-4">
          <StatBadge label="Patterns" value={formatNumber(data.length)} theme={theme} />
          <StatBadge label="Total Wasted" value={formatCurrency(totalWasted)} color="text-red-400" />
          <StatBadge label="Total Repeats" value={formatNumber(totalRepeats)} color="text-yellow-400" />
          <StatBadge label="Exact Match" value={formatNumber(exactMatchCount)} color="text-green-400" />
          <StatBadge label="High-Value" value={formatNumber(highValueCount)} color="text-purple-400" />
        </div>

        {/* Layer2Table */}
        <Layer2Table
          storyId={STORY_ID}
          data={data}
          initialFilters={initialFilters}
          onRowClick={handleRowClick}
          loading={loading}
        />

      </PageContainer>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// STAT BADGE
// ─────────────────────────────────────────────────────────────────────────────

function StatBadge({ label, value, theme, color }) {
  const textColor = color || (theme ? theme.text : BASE_THEME.text.secondary);

  return (
    <div className={`px-4 py-2 ${BASE_THEME.container.secondary} rounded-lg border ${BASE_THEME.border.default}`}>
      <span className={`text-xs ${BASE_THEME.text.muted}`}>{label}: </span>
      <span className={`font-semibold ${textColor}`}>{value}</span>
    </div>
  );
}