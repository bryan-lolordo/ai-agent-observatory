/**
 * Layer 2: Cache All Calls View
 * 
 * Uses Layer2Table component for full-featured data exploration.
 * Shows all calls (accessed via KPI cards in Layer 1).
 */

import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import Layer2Table from '../../../components/Layer2Table';
import { formatNumber, formatCurrency } from '../../../utils/formatters';

const STORY_ID = 'cache';
const theme = STORY_THEMES.cache;

export default function CacheAllCalls() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // State
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  
  // Get initial filter from URL if coming from Layer 1
  const initialQuickFilter = searchParams.get('filter') || 'all';
  
  // No initial column filters - showing all calls
  const initialFilters = {};
  
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
        const cachedCalls = calls.filter(c => c.cached);
        const totalCost = calls.reduce((sum, c) => sum + (c.total_cost || 0), 0);
        
        setStats({
          total: calls.length,
          cached: cachedCalls.length,
          hitRate: calls.length ? ((cachedCalls.length / calls.length) * 100).toFixed(1) : 0,
          totalCost: totalCost,
          errors: calls.filter(c => c.status === 'error').length,
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
    navigate('/stories/cache');
  };
  
  const handleRowClick = (row) => {
    navigate(`/stories/calls/${row.call_id}?from=cache`);
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
            ← Back to Cache Overview
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
  
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Story Navigation */}
      <StoryNavTabs activeStory="cache" />

      <div className="max-w-7xl mx-auto p-8">
        
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
              <span className="text-4xl">{theme.emoji}</span>
              All Calls
            </h1>
          </div>
          <p className="text-gray-400">
            Dashboard &gt; Caching Strategy &gt; All Calls
          </p>
        </div>
        
        {/* Summary Stats Bar */}
        {stats && (
          <div className="mb-6 flex flex-wrap gap-4">
            <StatBadge label="Total" value={formatNumber(stats.total)} />
            <StatBadge label="Cached" value={formatNumber(stats.cached)} theme={theme} />
            <StatBadge label="Hit Rate" value={`${stats.hitRate}%`} color={stats.hitRate > 50 ? 'text-green-400' : 'text-yellow-400'} />
            <StatBadge label="Total Cost" value={formatCurrency(stats.totalCost)} />
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
