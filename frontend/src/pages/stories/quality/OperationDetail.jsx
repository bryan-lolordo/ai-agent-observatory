/**
 * Layer 2: Quality Operation Detail
 *
 * Uses Layer2Table component for full-featured data exploration.
 * Shows all calls for a specific operation (or all calls if no operation selected).
 *
 * UPDATED: Uses common components - BackButton, ErrorDisplay, StatBadge
 */

import { useMemo } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import Layer2Table from '../../../components/stories/Layer2Table';
import { formatNumber } from '../../../utils/formatters';
import { useCalls } from '../../../hooks/useCalls';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';

// Common components
import BackButton from '../../../components/common/BackButton';
import ErrorDisplay from '../../../components/common/ErrorDisplay';
import StatBadge from '../../../components/common/StatBadge';

const STORY_ID = 'quality';
const theme = STORY_THEMES.quality;

export default function QualityOperationDetail() {
  const { agent, operation } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Fetch data with automatic timeRange handling
  const { data, loading, error, refetch } = useCalls();

  // Get initial filter from URL if coming from Layer 1
  const initialQuickFilter = searchParams.get('filter') || 'all';

  // Build initial column filters if operation is specified
  const initialFilters = useMemo(() => {
    const filters = {};
    if (operation) {
      filters.operation = [operation];
    }
    if (agent) {
      filters.agent_name = [agent];
    }
    return filters;
  }, [agent, operation]);

  // Calculate stats from data
  const stats = useMemo(() => {
    if (!data || data.length === 0) return null;

    // Calculate quality stats
    const evaluatedCalls = data.filter(c => c.judge_score != null);
    const scores = evaluatedCalls.map(c => c.judge_score);
    const avgScore = scores.length > 0
      ? `${(scores.reduce((sum, s) => sum + s, 0) / scores.length).toFixed(1)}/10`
      : '—';
    const lowQuality = evaluatedCalls.filter(c => c.judge_score < 7).length;

    return {
      total: data.length,
      evaluated: evaluatedCalls.length,
      avgScore,
      lowQuality,
      errors: data.filter(c => c.status === 'error').length,
    };
  }, [data]);

  // Navigation handlers
  const handleBack = () => {
    navigate('/stories/quality');
  };

  const handleRowClick = (row) => {
    navigate(`/stories/quality/calls/${row.call_id}`);
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
        backLabel="Quality Overview"
        theme={theme}
      />
    );
  }

  // Build page title
  const pageTitle = operation
    ? `${agent}.${operation}`
    : agent
      ? `${agent} Agent`
      : 'All Calls';

  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} ${BASE_THEME.text.primary}`}>
      {/* Story Navigation */}
      <StoryNavTabs activeStory="quality" />

      <PageContainer>

        {/* Back Button */}
        <BackButton
          onClick={handleBack}
          label="Quality Overview"
          theme={theme}
        />

        {/* Page Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h1 className={`text-3xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-4xl">{theme.emoji}</span>
              {pageTitle}
            </h1>
          </div>
          <p className={BASE_THEME.text.muted}>
            Dashboard &gt; Quality Monitoring &gt; {operation ? 'Operation Detail' : 'All Calls'}
          </p>
        </div>

        {/* Summary Stats Bar */}
        {stats && (
          <div className="mb-6 flex flex-wrap gap-4">
            <StatBadge label="Total" value={formatNumber(stats.total)} />
            <StatBadge label="Evaluated" value={formatNumber(stats.evaluated)} />
            <StatBadge label="Avg Score" value={stats.avgScore} theme={theme} />
            <StatBadge label="Low Quality" value={formatNumber(stats.lowQuality)} color={stats.lowQuality > 0 ? BASE_THEME.status.warning.text : BASE_THEME.status.success.text} />
            <StatBadge
              label="Errors"
              value={`${stats.errors} (${((stats.errors / stats.total) * 100).toFixed(1)}%)`}
              color={stats.errors > 0 ? BASE_THEME.status.error.text : BASE_THEME.status.success.text}
            />
          </div>
        )}

        {/* Layer2Table */}
        <Layer2Table
          storyId={STORY_ID}
          data={data}
          initialFilters={initialFilters}
          initialQuickFilter={initialQuickFilter}
          onRowClick={handleRowClick}
          loading={loading}
        />

      </PageContainer>
    </div>
  );
}
