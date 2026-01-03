/**
 * Layer 2: Optimization Comparison Detail
 * 
 * Uses Layer2Table component for full-featured data exploration.
 * Shows all calls for viewing optimization opportunities.
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

const STORY_ID = 'optimization';
const theme = STORY_THEMES.optimization;

export default function OptimizationComparisonDetail() {
  const { comparisonId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // Fetch data with automatic timeRange handling
  const { data, loading, error, refetch } = useCalls();
  
  // Get initial filter from URL if coming from Layer 1
  const initialQuickFilter = searchParams.get('filter') || 'all';
  
  // No initial filters for optimization - shows all calls
  const initialFilters = useMemo(() => ({}), []);
  
  // Calculate stats from data
  const stats = useMemo(() => {
    if (!data || data.length === 0) return null;
    
    const totalCost = data.reduce((sum, c) => sum + (c.total_cost || 0), 0);
    const totalLatency = data.reduce((sum, c) => sum + (c.latency_ms || 0), 0);
    const avgLatency = data.length ? totalLatency / data.length : 0;
    const errors = data.filter(c => c.status === 'error').length;
    
    return {
      total: data.length,
      totalCost,
      avgLatency: (avgLatency / 1000).toFixed(2),
      errors,
    };
  }, [data]);
  
  // Navigation handlers
  const handleBack = () => {
    navigate('/stories/optimization');
  };
  
  const handleRowClick = (row) => {
    navigate(`/stories/calls/${row.call_id}?from=optimization`);
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
            ← Back to Optimization Impact Overview
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
  
  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} ${BASE_THEME.text.primary}`}>
      {/* Story Navigation */}
      <StoryNavTabs activeStory="optimization" />

      <PageContainer>
        
        {/* Back Button */}
        <button
          onClick={handleBack}
          className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:underline`}
        >
          ← Back to Optimization Impact Overview
        </button>
        
        {/* Page Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <h1 className={`text-3xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-4xl">{theme.emoji}</span>
              All Calls
            </h1>
          </div>
          <p className="text-gray-400">
            Dashboard &gt; Optimization Impact &gt; All Calls
          </p>
        </div>
        
        {/* Summary Stats Bar */}
        {stats && (
          <div className="mb-6 flex flex-wrap gap-4">
            <StatBadge label="Total" value={formatNumber(stats.total)} />
            <StatBadge label="Total Cost" value={formatCurrency(stats.totalCost)} theme={theme} />
            <StatBadge label="Avg Latency" value={`${stats.avgLatency}s`} />
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