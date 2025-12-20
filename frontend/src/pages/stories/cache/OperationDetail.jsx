/**
 * Layer 2: Cache Operation Detail
 * 
 * Shows cache opportunities for a specific operation with type filters.
 * This is the original cache-specific design (not Layer2Table).
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import KPICard from '../../../components/common/KPICard';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, formatCurrency, truncateText } from '../../../utils/formatters';

const theme = STORY_THEMES.cache;

// Cache type filter definitions
const CACHE_TYPE_FILTERS = [
  { id: 'all', name: 'All Types', emoji: '📊' },
  { id: 'exact', name: 'Exact Match', emoji: '🎯' },
  { id: 'stable', name: 'Stable/Prefix', emoji: '📌' },
  { id: 'high_value', name: 'High-Value', emoji: '💎' },
];

export default function CacheOperationDetail() {
  const { agent, operation } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // State
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedType, setSelectedType] = useState(searchParams.get('type') || 'all');

  // Fetch data
  useEffect(() => {
    fetchData();
  }, [agent, operation]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`/api/stories/cache/operations/${encodeURIComponent(agent)}/${encodeURIComponent(operation)}`);
      
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(`Operation not found: ${agent}.${operation}`);
        }
        throw new Error(`HTTP ${response.status}`);
      }
      
      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Error fetching cache operation detail:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Navigation handlers
  const handleBack = () => {
    navigate('/stories/cache');
  };

  const handleOpportunityClick = (opportunity) => {
    navigate(`/stories/cache/operations/${encodeURIComponent(agent)}/${encodeURIComponent(operation)}/groups/${opportunity.group_id}`);
  };

  // Filter opportunities by type
  const filteredOpportunities = data?.opportunities?.filter(opp => 
    selectedType === 'all' || opp.cache_type === selectedType
  ) || [];

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

  const {
    total_calls = 0,
    unique_prompts = 0,
    cacheable_count = 0,
    wasted_cost = 0,
    wasted_cost_formatted = '$0.00',
    opportunities = [],
    type_counts = {},
  } = data || {};

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Story Navigation */}
      <StoryNavTabs activeStory="cache" />

      <div className="max-w-7xl mx-auto p-8">
        
        {/* Back Button + Header */}
        <button
          onClick={handleBack}
          className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:underline`}
        >
          ← Back to Cache Overview
        </button>

        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <h1 className={`text-4xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-5xl">💾</span>
              {operation}
            </h1>
            <div className={`px-4 py-2 rounded-full border-2 ${theme.border} ${theme.badgeBg}`}>
              <span className={`text-sm font-semibold ${theme.text}`}>
                {Math.round((cacheable_count / total_calls) * 100) || 0}% Cacheable
              </span>
            </div>
          </div>
          <p className="text-gray-400">
            {agent} Agent • {formatNumber(total_calls)} calls • {formatNumber(unique_prompts)} unique prompts
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <KPICard
            theme={theme}
            title="📊 Total Calls"
            value={formatNumber(total_calls)}
            subtext="In this operation"
          />
          <KPICard
            theme={theme}
            title="✨ Unique Prompts"
            value={formatNumber(unique_prompts)}
            subtext="Would be cached"
          />
          <KPICard
            theme={theme}
            title="🔄 Cacheable"
            value={formatNumber(cacheable_count)}
            subtext="Could eliminate"
          />
          <KPICard
            theme={theme}
            title="💸 Wasted Cost"
            value={wasted_cost_formatted}
            subtext="Recoverable"
          />
        </div>

        {/* Type Filter Buttons */}
        <div className={`mb-6 rounded-lg border-2 ${theme.border} bg-gray-900 p-4`}>
          <div className="flex flex-wrap gap-2">
            {CACHE_TYPE_FILTERS.map(type => {
              const count = type.id === 'all' 
                ? opportunities.length 
                : type_counts[type.id] || 0;
              
              const isSelected = selectedType === type.id;
              const isDisabled = count === 0 && type.id !== 'all';
              
              return (
                <button
                  key={type.id}
                  onClick={() => !isDisabled && setSelectedType(type.id)}
                  disabled={isDisabled}
                  className={`
                    px-4 py-2 rounded-lg text-sm font-medium transition-all
                    flex items-center gap-2
                    ${isSelected 
                      ? `${theme.bg} text-white` 
                      : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                    }
                    ${isDisabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}
                  `}
                >
                  <span>{type.emoji}</span>
                  <span>{type.name}</span>
                  <span className={`
                    px-2 py-0.5 rounded-full text-xs
                    ${isSelected ? 'bg-white/20' : 'bg-gray-700'}
                  `}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Opportunities Table */}
        <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          <div className={`${theme.bgLight} p-4 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              📋 Cache Opportunities (click row for details + fix)
              {selectedType !== 'all' && (
                <span className="ml-2 text-sm font-normal text-gray-400">
                  (filtered by {CACHE_TYPE_FILTERS.find(t => t.id === selectedType)?.name})
                </span>
              )}
            </h3>
          </div>
          
          <div className="overflow-x-auto overflow-y-auto max-h-96 story-scrollbar-thin cache">
            <table className="w-full text-sm">
              <thead className="bg-gray-800 sticky top-0">
                <tr className={`border-b-2 ${theme.border}`}>
                  <th className={`text-center py-3 px-4 ${theme.textLight}`}>Type</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Prompt Preview</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Repeats</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Wasted</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Savable</th>
                  <th className={`text-center py-3 px-4 ${theme.textLight}`}>Effort</th>
                </tr>
              </thead>
              <tbody>
                {filteredOpportunities.length > 0 ? (
                  filteredOpportunities.map((opp, idx) => (
                    <tr
                      key={opp.group_id || idx}
                      onClick={() => handleOpportunityClick(opp)}
                      className={`border-b border-gray-800 cursor-pointer transition-all hover:bg-gradient-to-r hover:${theme.gradient} hover:border-l-4 hover:${theme.border}`}
                    >
                      <td className="py-3 px-4 text-center">
                        <span className="text-xl" title={opp.cache_type_name}>
                          {opp.cache_type_emoji}
                        </span>
                      </td>
                      <td className="py-3 px-4 max-w-md">
                        <div className={`text-sm ${theme.text} font-mono truncate`}>
                          "{truncateText(opp.prompt_preview, 60)}"
                        </div>
                      </td>
                      <td className={`py-3 px-4 text-right font-bold ${theme.text}`}>
                        {opp.repeat_count}x
                      </td>
                      <td className={`py-3 px-4 text-right font-semibold ${theme.text}`}>
                        {opp.wasted_cost_formatted}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-400">
                        {opp.savable_time_formatted}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span title={`${opp.effort} effort`}>
                          {opp.effort_badge}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-gray-500">
                      {selectedType !== 'all' 
                        ? `No ${CACHE_TYPE_FILTERS.find(t => t.id === selectedType)?.name} opportunities found`
                        : 'No cache opportunities found for this operation'
                      }
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Quick Win Insight */}
        {type_counts.exact > 0 && (
          <div className={`rounded-lg border-2 border-green-600 bg-gradient-to-br from-green-900/30 to-gray-900 p-6`}>
            <h3 className="text-lg font-semibold text-green-400 mb-2 flex items-center gap-2">
              <span>💡</span>
              Quick Win Available
            </h3>
            <p className="text-gray-300">
              {type_counts.exact} exact match{type_counts.exact > 1 ? 'es' : ''} can be cached with a simple key-value store.
              This is the easiest optimization to implement.
            </p>
          </div>
        )}

      </div>
    </div>
  );
}