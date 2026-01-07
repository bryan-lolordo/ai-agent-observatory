/**
 * Layer 2: Cache Calls (All Cache Patterns)
 *
 * Shows all cacheable patterns with full Layer2Table functionality.
 * Uses URL params for initial filters (from Layer 1 drill-down).
 *
 * UPDATED: Uses common components - BackButton, ErrorDisplay, StatBadge
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

// Common components
import BackButton from '../../../components/common/BackButton';
import ErrorDisplay from '../../../components/common/ErrorDisplay';
import StatBadge from '../../../components/common/StatBadge';

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
      <ErrorDisplay
        error={error}
        onRetry={refetch}
        onBack={handleBack}
        backLabel="Cache Overview"
        theme={theme}
      />
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
        <BackButton
          onClick={handleBack}
          label="Cache Overview"
          theme={theme}
        />

        {/* Page Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h1 className={`text-3xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-4xl">💾</span>
              Cache Opportunities
              {(initialOperation || initialAgent) && (
                <span className={`text-lg font-normal ${BASE_THEME.text.muted}`}>
                  {initialAgent && initialOperation
                    ? `• ${initialAgent}.${initialOperation}`
                    : initialOperation || initialAgent
                  }
                </span>
              )}
            </h1>
          </div>
          <p className={BASE_THEME.text.muted}>
            Dashboard &gt; Caching Strategy &gt; All Patterns
          </p>
        </div>

        {/* Stat Badges Row */}
        <div className="mb-6 flex flex-wrap gap-4">
          <StatBadge label="Patterns" value={formatNumber(data.length)} theme={theme} />
          <StatBadge label="Total Wasted" value={formatCurrency(totalWasted)} color={BASE_THEME.status.error.text} />
          <StatBadge label="Total Repeats" value={formatNumber(totalRepeats)} color={BASE_THEME.status.warning.text} />
          <StatBadge label="Exact Match" value={formatNumber(exactMatchCount)} color={BASE_THEME.status.success.text} />
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
