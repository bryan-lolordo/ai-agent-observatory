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
import { BASE_THEME } from '../../../utils/themeUtils';
import { STORY_THEMES } from '../../../config/theme';
import PageContainer from '../../../components/layout/PageContainer';
import { getFixesForCall } from '../../../config/fixes';

import Layer3Shell from '../../../components/stories/Layer3';

import {
  CACHE_STORY,
  getCacheKPIs,
  analyzeCacheFactors,
  getCacheFixes,
  CACHE_SIMILAR_CONFIG,
} from '../../../config/layer3/cache';

const theme = STORY_THEMES.cache;

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
        theme={theme}
        loading={true}
      />
    );
  }

  // Error state
  if (error || !pattern) {
    return (
      <div className={`min-h-screen ${BASE_THEME.container.tertiary} p-8`}>
        <PageContainer>
          <button
            onClick={() => navigate(`/stories/cache/operations/${encodeURIComponent(agent)}/${encodeURIComponent(operation)}`)}
            className="mb-6 flex items-center gap-2 text-sm text-pink-400 hover:underline"
          >
            ← Back to {operation}
          </button>
          <div className={`${BASE_THEME.status.error.bg} border ${BASE_THEME.status.error.border} rounded-lg p-6`}>
            <h2 className={`text-xl font-bold ${BASE_THEME.status.error.textBold} mb-2`}>Error Loading Pattern</h2>
            <p className={BASE_THEME.text.secondary}>{error || 'Pattern not found'}</p>
          </div>
        </PageContainer>
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
  const fixes = getFixesForCall(pattern, 'cache', factors);

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
      theme={theme}
      
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
          <div className={`${BASE_THEME.container.secondary} rounded-lg p-4`}>
            <table className="w-full text-sm">
              <thead>
                <tr className={`text-left ${BASE_THEME.text.muted}`}>
                  <th className="pb-2">Metric</th>
                  <th className="pb-2">Current</th>
                  <th className="pb-2">With Cache</th>
                  <th className="pb-2">Savings</th>
                </tr>
              </thead>
              <tbody className={BASE_THEME.text.secondary}>
                <tr className={`border-t ${BASE_THEME.border.default}`}>
                  <td className="py-2">LLM Calls</td>
                  <td>{repeat_count}</td>
                  <td>1</td>
                  <td className={BASE_THEME.status.success.text}>-{repeat_count - 1}</td>
                </tr>
                <tr className={`border-t ${BASE_THEME.border.default}`}>
                  <td className="py-2">Cost</td>
                  <td>${((wasted_cost || 0) + (unit_cost || 0.034)).toFixed(3)}</td>
                  <td>${(unit_cost || 0.034).toFixed(3)}</td>
                  <td className={BASE_THEME.status.success.text}>-${(wasted_cost || 0).toFixed(3)}</td>
                </tr>
                <tr className={`border-t ${BASE_THEME.border.default}`}>
                  <td className="py-2">Total Latency</td>
                  <td>~{((avg_latency_ms || 4000) * repeat_count / 1000).toFixed(0)}s</td>
                  <td>~{((avg_latency_ms || 4000) / 1000).toFixed(0)}s</td>
                  <td className={BASE_THEME.status.success.text}>-{repeat_count > 1 ? Math.round((1 - 1/repeat_count) * 100) : 0}%</td>
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
              <div className={`${BASE_THEME.container.secondary} rounded-lg p-4 space-y-3`}>
                <div className="flex justify-between text-sm">
                  <span className={BASE_THEME.text.muted}>Hash:</span>
                  <code className={BASE_THEME.text.secondary}>{prompt_hash || group_id}</code>
                </div>
                <div className="flex justify-between text-sm">
                  <span className={BASE_THEME.text.muted}>First Seen:</span>
                  <span className={BASE_THEME.text.secondary}>{first_seen || 'Unknown'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className={BASE_THEME.text.muted}>Last Seen:</span>
                  <span className={BASE_THEME.text.secondary}>{last_seen || 'Unknown'}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className={BASE_THEME.text.muted}>Occurrences:</span>
                  <span className={BASE_THEME.text.secondary}>{repeat_count} calls</span>
                </div>
              </div>
            ),
          },
          // Prompt Structure
          {
            title: '📝 Prompt Structure Analysis',
            content: (
              <div className={`${BASE_THEME.container.secondary} rounded-lg p-4`}>
                <div className="flex items-center gap-3 mb-4">
                  <span className={`px-3 py-1 ${BASE_THEME.status.success.bg} ${BASE_THEME.status.success.text} rounded text-sm font-medium`}>
                    {cache_type_emoji} {cache_type === 'exact' ? 'STATIC' : 'VARIABLE'}
                  </span>
                  <span className={BASE_THEME.text.muted}>
                    {cache_type === 'exact'
                      ? '100% identical across all calls'
                      : 'Has variable components'}
                  </span>
                </div>

                <div className="space-y-2 text-sm">
                  <div className={`flex items-center gap-2 ${BASE_THEME.status.success.text}`}>
                    <span>✅</span>
                    <span>No dynamic variables detected</span>
                  </div>
                  <div className={`flex items-center gap-2 ${BASE_THEME.status.success.text}`}>
                    <span>✅</span>
                    <span>No timestamps or session IDs</span>
                  </div>
                  <div className={`flex items-center gap-2 ${BASE_THEME.status.success.text}`}>
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
              <div className={`${BASE_THEME.container.secondary} rounded-lg p-4`}>
                <div className={`mb-3 text-sm ${BASE_THEME.text.muted}`}>
                  All {repeat_count} responses were compared:
                </div>
                <div className="mb-3">
                  <div className="flex justify-between text-sm mb-1">
                    <span className={BASE_THEME.text.muted}>Response Similarity</span>
                    <span className={response_similarity === 100 ? BASE_THEME.status.success.text : BASE_THEME.status.warning.text}>
                      {response_similarity}%
                    </span>
                  </div>
                  <div className={`h-3 ${BASE_THEME.container.tertiary} rounded-full overflow-hidden`}>
                    <div
                      className={`h-full ${response_similarity === 100 ? BASE_THEME.status.success.bgSolid : BASE_THEME.status.warning.bgSolid}`}
                      style={{ width: `${response_similarity}%` }}
                    />
                  </div>
                </div>
                <div className={`text-sm ${response_similarity === 100 ? BASE_THEME.status.success.text : BASE_THEME.status.warning.text}`}>
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