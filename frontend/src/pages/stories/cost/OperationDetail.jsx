/**
 * Layer 2: Cost Analysis Operation Detail
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
import { formatNumber, formatCurrency } from '../../../utils/formatters';
import { useCalls } from '../../../hooks/useCalls';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';

// Common components
import BackButton from '../../../components/common/BackButton';
import ErrorDisplay from '../../../components/common/ErrorDisplay';
import StatBadge from '../../../components/common/StatBadge';

const STORY_ID = 'cost';
const theme = STORY_THEMES.cost;

export default function CostOperationDetail() {
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

    const totalPrompt = data.reduce((sum, c) => sum + (c.prompt_tokens || 0), 0);
    const totalCompletion = data.reduce((sum, c) => sum + (c.completion_tokens || 0), 0);
    const avgRatio = totalCompletion > 0 ? (totalPrompt / totalCompletion).toFixed(1) : '—';

    // Add cost calculations
    const costs = data.map(c => c.total_cost || 0);
    const totalCost = costs.reduce((a, b) => a + b, 0);
    const avgCost = data.length > 0 ? totalCost / data.length : 0;
    const maxCost = Math.max(...costs, 0);

    return {
      total: data.length,
      avgRatio,
      totalPrompt,
      totalCompletion,
      totalCost,
      avgCost,
      maxCost,
      errors: data.filter(c => c.status === 'error').length,
    };
  }, [data]);

  // Navigation handlers
  const handleBack = () => {
    navigate('/stories/cost');
  };

  const handleRowClick = (row) => {
    navigate(`/stories/cost/calls/${row.call_id}`);
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
        backLabel="Cost Analysis Overview"
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
      <StoryNavTabs activeStory="cost" />

      <PageContainer>

        {/* Back Button */}
        <BackButton
          onClick={handleBack}
          label="Cost Analysis Overview"
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
            Dashboard &gt; Cost Analysis &gt; {operation ? 'Operation Detail' : 'All Calls'}
          </p>
        </div>

        {/* Summary Stats Bar */}
        {stats && (
          <div className="mb-6 flex flex-wrap gap-4">
            <StatBadge label="Total" value={formatNumber(stats.total)} />
            <StatBadge label="Total Cost" value={formatCurrency(stats.totalCost)} theme={theme} />
            <StatBadge label="Avg Cost" value={formatCurrency(stats.avgCost)} />
            <StatBadge label="Max Cost" value={formatCurrency(stats.maxCost)} color={BASE_THEME.status.error.text} />
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
