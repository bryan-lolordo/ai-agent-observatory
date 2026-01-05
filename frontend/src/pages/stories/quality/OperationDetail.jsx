/**
 * Layer 2: Quality Operation Detail
 * 
 * Uses Layer2Table component for full-featured data exploration.
 * Shows all calls for a specific operation (or all calls if no operation selected).
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
      <div className={`min-h-screen ${BASE_THEME.container.tertiary} p-8`}>
        <PageContainer>
          <button
            onClick={handleBack}
            className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:underline`}
          >
            ← Back to Quality Overview
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
        <button
          onClick={handleBack}
          className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:underline`}
        >
          ← Back to Quality Overview
        </button>
        
        {/* Page Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h1 className={`text-3xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-4xl">{theme.emoji}</span>
              {pageTitle}
            </h1>
          </div>
          <p className="text-gray-400">
            Dashboard &gt; Quality Monitoring &gt; {operation ? 'Operation Detail' : 'All Calls'}
          </p>
        </div>
        
        {/* Summary Stats Bar */}
        {stats && (
          <div className="mb-6 flex flex-wrap gap-4">
            <StatBadge label="Total" value={formatNumber(stats.total)} />
            <StatBadge label="Evaluated" value={formatNumber(stats.evaluated)} />
            <StatBadge label="Avg Score" value={stats.avgScore} theme={theme} />
            <StatBadge label="Low Quality" value={formatNumber(stats.lowQuality)} color={stats.lowQuality > 0 ? 'text-yellow-400' : 'text-green-400'} />
            <StatBadge 
              label="Errors" 
              value={`${stats.errors} (${((stats.errors / stats.total) * 100).toFixed(1)}%)`}
              color={stats.errors > 0 ? 'text-red-400' : 'text-green-400'}
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

// ─────────────────────────────────────────────────────────────────────────────
// StatBadge - Summary stat display
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