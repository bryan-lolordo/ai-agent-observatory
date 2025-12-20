/**
 * Layer 2: Quality Operation Detail
 * 
 * Uses Layer2Table component for full-featured data exploration.
 * Shows all calls for a specific operation (or all calls if no operation selected).
 */

import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import Layer2Table from '../../../components/Layer2Table';
import { formatNumber } from '../../../utils/formatters';

const STORY_ID = 'quality';
const theme = STORY_THEMES.quality;

export default function QualityOperationDetail() {
  const { agent, operation } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // State
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  
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
  
  // Fetch all calls
  useEffect(() => {
    fetchData();
  }, []);
  
  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/calls?days=7');
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const result = await response.json();
      setData(result.calls || []);
      
      // Calculate stats
      if (result.calls?.length > 0) {
        const calls = result.calls;
        const scores = calls.map(c => c.judge_score).filter(s => s != null);
        const avgScore = scores.length ? (scores.reduce((a, b) => a + b, 0) / scores.length) : null;
        const lowQuality = scores.filter(s => s < 7).length;
        const errors = calls.filter(c => c.status === 'error').length;
        
        setStats({
          total: calls.length,
          evaluated: scores.length,
          avgScore: avgScore ? avgScore.toFixed(1) : '—',
          lowQuality,
          errors,
        });
      }
    } catch (err) {
      console.error('Error fetching calls:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  // Navigation handlers
  const handleBack = () => {
    navigate('/stories/quality');
  };
  
  const handleRowClick = (row) => {
    navigate(`/stories/calls/${row.call_id}?from=quality`);
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
            ← Back to Quality Overview
          </button>
          <div className="bg-red-900/20 border border-red-500 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-400 mb-2">Error Loading Data</h2>
            <p className="text-gray-300">{error}</p>
            <button
              onClick={fetchData}
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
      <StoryNavTabs activeStory="quality" />

      <div className="max-w-7xl mx-auto p-8">
        
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