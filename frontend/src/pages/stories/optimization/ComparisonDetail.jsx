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
      <div className="min-h-screen bg-gray-950 p-8">
        <div className="max-w-7xl mx-auto">
          <button
            onClick={handleBack}
            className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:underline`}
          >
            ← Back to Optimization Impact Overview
          </button>
          <div className="bg-red-900/20 border border-red-500 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-400 mb-2">Error Loading Data</h2>
            <p className="text-gray-300">{error}</p>
            <button
              onClick={refetch}
              className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Story Navigation */}
      <StoryNavTabs activeStory="optimization" />

      <div className="max-w-7xl mx-auto p-8">
        
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
        
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// StatBadge - Summary stat display
// ─────────────────────────────────────────────────────────────────────────────

function StatBadge({ label, value, theme, color }) {
  const textColor = color || (theme ? theme.text : 'text-gray-300');
  
  return (
    <div className="px-4 py-2 bg-gray-900 rounded-lg border border-gray-700">
      <span className="text-xs text-gray-500">{label}: </span>
      <span className={`font-semibold ${textColor}`}>{value}</span>
    </div>
  );
}