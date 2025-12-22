/**
 * Layer 2: Cost Analysis Operation Detail
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
    
    return {
        total: data.length,
        avgRatio,
        totalPrompt,
        totalCompletion,
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
      <div className="min-h-screen bg-gray-950 p-8">
        <div className="max-w-7xl mx-auto">
          <button
            onClick={handleBack}
            className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:underline`}
          >
            ← Back to Cost Analysis Overview
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
  
  // Build page title
  const pageTitle = operation 
    ? `${agent}.${operation}` 
    : agent 
      ? `${agent} Agent` 
      : 'All Calls';
  
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Story Navigation */}
      <StoryNavTabs activeStory="cost" />

      <div className="max-w-7xl mx-auto p-8">
        
        {/* Back Button */}
        <button
          onClick={handleBack}
          className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:underline`}
        >
          ← Back to Cost Analysis Overview
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
            Dashboard &gt; Cost Analysis &gt; {operation ? 'Operation Detail' : 'All Calls'}
          </p>
        </div>
        
        {/* Summary Stats Bar */}
        {stats && (
          <div className="mb-6 flex flex-wrap gap-4">
            <StatBadge label="Total" value={formatNumber(stats.total)} />
            <StatBadge label="Total Cost" value={formatCurrency(stats.totalCost)} theme={theme} />
            <StatBadge label="Avg Cost" value={formatCurrency(stats.avgCost)} />
            <StatBadge label="Max Cost" value={formatCurrency(stats.maxCost)} color="text-red-400" />
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