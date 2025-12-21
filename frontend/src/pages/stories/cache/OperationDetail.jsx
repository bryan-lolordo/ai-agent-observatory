/**
 * Layer 2: Cache Calls (All Cache Patterns)
 * 
 * Shows all cacheable patterns with full Layer2Table functionality.
 * Uses URL params for initial filters (from Layer 1 drill-down).
 */

import { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { STORY_THEMES } from '../../../config/theme';
import { getLayer2Config } from '../../../config/storyDefinitions';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import Layer2Table from '../../../components/stories/Layer2Table';
import { formatNumber, formatCurrency } from '../../../utils/formatters';

const STORY_ID = 'cache';
const theme = STORY_THEMES.cache;
const config = getLayer2Config(STORY_ID);

export default function CacheOperationDetail() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
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
  
  // State
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({
    total_patterns: 0,
    total_wasted: 0,
    total_savable: 0,
  });

  // Fetch all cache patterns
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/stories/cache/patterns');
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const result = await response.json();
      
      // API returns { patterns: [...], stats: {...} }
      setData(result.patterns || []);
      setStats(result.stats || {
        total_patterns: result.patterns?.length || 0,
        total_wasted: 0,
        total_savable: 0,
      });
    } catch (err) {
      console.error('Error fetching cache patterns:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

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

  // Calculate summary stats
  const totalWasted = data.reduce((sum, p) => sum + (p.wasted_cost || 0), 0);
  const totalRepeats = data.reduce((sum, p) => sum + (p.repeat_count || 0), 0);
  const exactMatchCount = data.filter(p => p.cache_type === 'exact').length;
  const highValueCount = data.filter(p => p.cache_type === 'high_value').length;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Story Navigation */}
      <StoryNavTabs activeStory={STORY_ID} />

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

      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// STAT BADGE
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