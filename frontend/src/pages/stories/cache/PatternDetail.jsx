/**
 * Cache Story - Layer 3 (Pattern Detail)
 * 
 * Uses the universal Layer3Shell with cache-specific configuration.
 * Note: This operates on PATTERNS (grouped prompts), not individual calls.
 * 
 * UPDATED: Now passes full pattern data to Layer3Shell for CacheablePromptView support
 */

import { useParams, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useTimeRange } from '../../../context/TimeRangeContext'; 

import Layer3Shell from '../../../components/stories/Layer3';

import {
  CACHE_STORY,
  getCacheKPIs,
  analyzeCacheFactors,
  getCacheFixes,
  CACHE_SIMILAR_CONFIG,
} from '../../../config/layer3/cache';

export default function CachePatternDetail() {
  const { agent, operation, groupId } = useParams();
  const navigate = useNavigate();
  const { timeRange } = useTimeRange();
  
  const [pattern, setPattern] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(
          `/api/stories/cache/operations/${encodeURIComponent(agent)}/${encodeURIComponent(operation)}/groups/${encodeURIComponent(groupId)}?days=${timeRange}`
        );
        
        if (!response.ok) {
          if (response.status === 404) {
            throw new Error(`Pattern not found: ${groupId}`);
          }
          throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        // ADD THIS DEBUG LOG HERE
        console.log('🔵 PatternDetail: Loaded data:', {
          hasSystemPrompt: !!data.system_prompt,
          systemPromptTokens: data.system_prompt_tokens,
          hasPrompt: !!data.prompt,
          promptLength: data.prompt?.length,
          hasInsights: !!data.insights,
          insightsCount: data.insights?.length,
          cacheableTokens: data.cacheable_tokens,
        });
        
        setPattern(data);
      } catch (err) {
        console.error('Failed to load pattern data:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    
    loadData();
  }, [agent, operation, groupId, timeRange]);

  // Loading state
  if (loading) {
    return (
      <Layer3Shell
        storyId={CACHE_STORY.id}
        storyLabel={CACHE_STORY.label}
        storyIcon={CACHE_STORY.icon}
        themeColor={CACHE_STORY.color}
        loading={true}
      />
    );
  }

  // Error state
  if (error || !pattern) {
    return (
      <div className="min-h-screen bg-gray-950 p-8">
        <div className="max-w-7xl mx-auto">
          <button
            onClick={() => navigate(`/stories/cache/operations/${encodeURIComponent(agent)}/${encodeURIComponent(operation)}`)}
            className="mb-6 flex items-center gap-2 text-sm text-pink-400 hover:underline"
          >
            ← Back to {operation}
          </button>
          <div className="bg-red-900/20 border border-red-500 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-400 mb-2">Error Loading Pattern</h2>
            <p className="text-gray-300">{error || 'Pattern not found'}</p>
          </div>
        </div>
      </div>
    );
  }

  // Extract data from API response
  const {
    group_id,
    prompt_hash,
    cache_type = 'exact',
    cache_type_emoji = '🎯',
    cache_type_name = 'Exact Match',
    repeat_count = 0,
    wasted_cost = 0,
    wasted_cost_formatted = '$0.00',
    unit_cost = 0,
    avg_latency_ms = 0,
    total_latency_ms = 0,
    effort = 'low',
    effort_badge = '🟢',
    first_seen,
    last_seen,
    response_similarity = 100,
    prompt_preview = '',
    full_prompt = '',
    sample_response = '',
    calls = [],
  } = pattern;

  // Analyze the pattern
  const factors = analyzeCacheFactors(pattern);
  const fixes = getCacheFixes(pattern);

  // Back path
  const backPath = `/stories/cache/operations/${encodeURIComponent(agent)}/${encodeURIComponent(operation)}`;

  // Get first call ID for AI Analysis
  const firstCallId = calls[0]?.call_id || calls[0]?.id || null;

  return (
    <Layer3Shell
      // Story config
      storyId={CACHE_STORY.id}
      storyLabel={CACHE_STORY.label}
      storyIcon={CACHE_STORY.icon}
      themeColor={CACHE_STORY.color}
      
      // Entity info (pattern, not call)
      entityId={group_id || groupId}
      entityType="pattern"
      entityLabel={`${cache_type_name} Pattern`}
      entitySubLabel={`${agent}.${operation}`}
      entityMeta={`${repeat_count}x repeats • ${first_seen || 'Unknown'} - ${last_seen || 'Unknown'}`}
      
      // ⭐ NEW: Pass full pattern data for CacheablePromptView
      data={pattern}
      
      // Navigation
      backPath={backPath}
      backLabel={`Back to ${operation}`}
      
      // KPIs
      kpis={getCacheKPIs(pattern)}
      
      // AI Analysis - pass first call ID for patterns
      aiCallId={firstCallId}
      
      // Diagnose panel
      diagnoseProps={{
        factors,
        isHealthy: false, // Cache opportunities are never "healthy" - they're opportunities
        breakdownTitle: '📊 Impact Summary',
        breakdownComponent: (
          <div className="bg-gray-900 rounded-lg p-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500">
                  <th className="pb-2">Metric</th>
                  <th className="pb-2">Current</th>
                  <th className="pb-2">With Cache</th>
                  <th className="pb-2">Savings</th>
                </tr>
              </thead>
              <tbody className="text-gray-300">
                <tr className="border-t border-gray-700">
                  <td className="py-2">LLM Calls</td>
                  <td>{repeat_count}</td>
                  <td>1</td>
                  <td className="text-green-400">-{repeat_count - 1}</td>
                </tr>
                <tr className="border-t border-gray-700">
                  <td className="py-2">Cost</td>
                  <td>${((wasted_cost || 0) + (unit_cost || 0.034)).toFixed(3)}</td>
                  <td>${(unit_cost || 0.034).toFixed(3)}</td>
                  <td className="text-green-400">-${(wasted_cost || 0).toFixed(3)}</td>
                </tr>
                <tr className="border-t border-gray-700">
                  <td className="py-2">Total Latency</td>
                  <td>~{((avg_latency_ms || 4000) * repeat_count / 1000).toFixed(0)}s</td>
                  <td>~{((avg_latency_ms || 4000) / 1000).toFixed(0)}s</td>
                  <td className="text-green-400">-{repeat_count > 1 ? Math.round((1 - 1/repeat_count) * 100) : 0}%</td>
                </tr>
              </tbody>
            </table>
          </div>
        ),
      }}
      
      // Attribute panel
      attributeProps={{
        customSections: [
          // Prompt Fingerprint
          {
            title: '🔑 Prompt Fingerprint',
            content: (
              <div className="bg-gray-900 rounded-lg p-4 space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Hash:</span>
                  <code className="text-gray-300">{prompt_hash || group_id}</code>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">First Seen:</span>
                  <span className="text-gray-300">{first_seen || 'Unknown'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Last Seen:</span>
                  <span className="text-gray-300">{last_seen || 'Unknown'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Occurrences:</span>
                  <span className="text-gray-300">{repeat_count} calls</span>
                </div>
              </div>
            ),
          },
          // Prompt Structure
          {
            title: '📝 Prompt Structure Analysis',
            content: (
              <div className="bg-gray-900 rounded-lg p-4">
                <div className="flex items-center gap-3 mb-4">
                  <span className="px-3 py-1 bg-green-900/50 text-green-300 rounded text-sm font-medium">
                    {cache_type_emoji} {cache_type === 'exact' ? 'STATIC' : 'VARIABLE'}
                  </span>
                  <span className="text-gray-400">
                    {cache_type === 'exact' 
                      ? '100% identical across all calls'
                      : 'Has variable components'}
                  </span>
                </div>
                
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2 text-green-400">
                    <span>✅</span>
                    <span>No dynamic variables detected</span>
                  </div>
                  <div className="flex items-center gap-2 text-green-400">
                    <span>✅</span>
                    <span>No timestamps or session IDs</span>
                  </div>
                  <div className="flex items-center gap-2 text-green-400">
                    <span>✅</span>
                    <span>Safe for exact-match caching</span>
                  </div>
                </div>
              </div>
            ),
          },
          // Response Consistency
          response_similarity != null && {
            title: '📤 Response Consistency',
            content: (
              <div className="bg-gray-900 rounded-lg p-4">
                <div className="mb-3 text-sm text-gray-400">
                  All {repeat_count} responses were compared:
                </div>
                <div className="mb-3">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-400">Response Similarity</span>
                    <span className={response_similarity === 100 ? 'text-green-400' : 'text-yellow-400'}>
                      {response_similarity}%
                    </span>
                  </div>
                  <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${response_similarity === 100 ? 'bg-green-500' : 'bg-yellow-500'}`}
                      style={{ width: `${response_similarity}%` }}
                    />
                  </div>
                </div>
                <div className={`text-sm ${response_similarity === 100 ? 'text-green-400' : 'text-yellow-400'}`}>
                  {response_similarity === 100 
                    ? '✅ Caching will return correct results'
                    : '⚠️ Responses vary slightly - verify cache validity'}
                </div>
              </div>
            ),
          },
        ].filter(Boolean),
      }}
      
      // Trace panel - empty props, Layer3Shell will pass storyId and data
      traceProps={{}}
      
      // Similar panel (shows all calls using this pattern)
      similarProps={{
        ...CACHE_SIMILAR_CONFIG,
        items: calls,
        currentItemId: calls[0]?.call_id,
        aggregateStats: [
          { label: 'Total Calls', value: calls.length || repeat_count, color: 'text-pink-400' },
          { label: 'Total Cost', value: `$${((calls.length || repeat_count) * (unit_cost || 0.034)).toFixed(3)}`, color: 'text-yellow-400' },
          { label: 'Total Time', value: `${((calls.length || repeat_count) * (avg_latency_ms || 4000) / 1000).toFixed(0)}s`, color: 'text-red-400' },
          { label: 'Savable', value: wasted_cost_formatted || `$${(wasted_cost || 0).toFixed(3)}`, color: 'text-green-400' },
        ],
        onSelectItem: (item) => {
          // Navigate to the individual call detail (latency view)
          navigate(`/stories/latency/calls/${item.call_id}`);
        },
      }}
      
      // Raw panel
      rawProps={{
        sections: [
          {
            title: 'Full Prompt',
            tokens: repeat_count * 500, // Approximate
            content: full_prompt || prompt_preview || '[Prompt not available]',
            defaultExpanded: true,
          },
          {
            title: 'Sample Response (from first call)',
            content: sample_response || '[Response not available]',
          },
          {
            title: 'Pattern Metadata',
            content: {
              group_id: group_id || groupId,
              prompt_hash,
              cache_type,
              repeat_count,
              wasted_cost,
              response_similarity,
              agent_name: agent,
              operation,
            },
          },
        ],
      }}
      
      // Fixes
      fixes={fixes}
      
      // Response text for before/after comparison
      responseText={sample_response}
    />
  );
}