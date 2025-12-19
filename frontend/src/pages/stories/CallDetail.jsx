/**
 * Layer 3: Call Detail - Shared Component
 * 
 * Shows complete details for a single LLM call with diagnosis
 * and recommendations. Used by all stories for drill-down.
 * 
 * Theming is determined by `?from=` query param.
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { STORY_THEMES } from '../../config/theme';
import { InlineLoading } from '../../components/common/Loading';

// =============================================================================
// COLLAPSIBLE SECTION COMPONENT
// =============================================================================

function CollapsibleSection({ title, tokenCount, content, theme, defaultOpen = false }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  const handleCopy = async (e) => {
    e.stopPropagation();
    if (content) {
      await navigator.clipboard.writeText(content);
      // Could add toast notification here
    }
  };

  return (
    <div className={`border ${theme.border} rounded-lg overflow-hidden`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full flex items-center justify-between p-4 ${theme.bgLight} hover:bg-opacity-80 transition-colors`}
      >
        <div className="flex items-center gap-3">
          <span className={`transition-transform ${isOpen ? 'rotate-90' : ''}`}>▶</span>
          <span className={`font-semibold ${theme.text}`}>{title}</span>
          {tokenCount !== null && tokenCount !== undefined && (
            <span className="text-gray-400 text-sm">({tokenCount.toLocaleString()} tokens)</span>
          )}
        </div>
        <button
          onClick={handleCopy}
          className="px-3 py-1 text-sm text-gray-400 hover:text-white bg-gray-800 rounded transition-colors"
        >
          Copy
        </button>
      </button>
      
      {isOpen && (
        <div className="p-4 bg-gray-900 border-t border-gray-800">
          <pre className="whitespace-pre-wrap text-sm text-gray-300 font-mono overflow-x-auto max-h-96 overflow-y-auto">
            {content || '(empty)'}
          </pre>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// KPI CARD COMPONENT
// =============================================================================

function KPICard({ label, value, subtext, status, theme }) {
  const statusColors = {
    critical: 'text-red-400',
    warning: 'text-yellow-400',
    good: 'text-green-400',
    neutral: theme.text,
  };

  return (
    <div className={`p-4 rounded-lg border ${theme.border} ${theme.bgLight}`}>
      <div className="text-sm text-gray-400 mb-1">{label}</div>
      <div className={`text-2xl font-bold ${statusColors[status] || statusColors.neutral}`}>
        {value}
      </div>
      {subtext && <div className="text-xs text-gray-500 mt-1">{subtext}</div>}
    </div>
  );
}

// =============================================================================
// ISSUE BADGE COMPONENT
// =============================================================================

function IssueBadge({ issue, theme }) {
  const severityConfig = {
    critical: { bg: 'bg-red-900/50', border: 'border-red-500', text: 'text-red-400', icon: '🔴' },
    warning: { bg: 'bg-yellow-900/50', border: 'border-yellow-500', text: 'text-yellow-400', icon: '🟡' },
    info: { bg: 'bg-blue-900/50', border: 'border-blue-500', text: 'text-blue-400', icon: '🔵' },
  };
  
  const config = severityConfig[issue.severity] || severityConfig.info;

  return (
    <div className={`p-4 rounded-lg border ${config.border} ${config.bg}`}>
      <div className="flex items-center gap-2 mb-1">
        <span>{config.icon}</span>
        <span className={`font-semibold ${config.text}`}>{issue.message}</span>
      </div>
      <div className="text-sm text-gray-400">{issue.detail}</div>
    </div>
  );
}

// =============================================================================
// RECOMMENDATION CARD COMPONENT
// =============================================================================

function RecommendationCard({ rec, theme }) {
  const impactColors = {
    high: 'text-green-400',
    medium: 'text-yellow-400',
    low: 'text-gray-400',
  };

  return (
    <div className={`p-4 rounded-lg border ${theme.border} bg-gray-800`}>
      <div className="flex items-center justify-between mb-2">
        <span className={`font-semibold ${theme.text}`}>💡 {rec.action}</span>
        <span className={`text-xs px-2 py-1 rounded ${impactColors[rec.impact]} bg-gray-900`}>
          {rec.impact} impact
        </span>
      </div>
      {rec.code_hint && (
        <code className="block text-sm text-gray-300 bg-gray-900 p-2 rounded font-mono mb-2">
          {rec.code_hint}
        </code>
      )}
      {rec.estimated_improvement && (
        <div className="text-xs text-gray-500">
          Expected: {rec.estimated_improvement}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function CallDetail() {
  const { callId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // Get theme from query param (default to latency)
  const fromStory = searchParams.get('from') || 'latency';
  const theme = STORY_THEMES[fromStory] || STORY_THEMES.latency;
  
  // State
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch call detail
  useEffect(() => {
    fetchCallDetail();
  }, [callId]);

  const fetchCallDetail = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`/api/stories/calls/${encodeURIComponent(callId)}`);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      
      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Error fetching call detail:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Handle back navigation
  const handleBack = () => {
    // Try to go back, or fall back to story page
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate(`/stories/${fromStory}`);
    }
  };

  // Export JSON
  const handleExportJSON = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `call-${callId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 p-8 flex items-center justify-center">
        <InlineLoading text="Loading call details..." />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 p-8">
        <div className="max-w-7xl mx-auto">
          <button
            onClick={handleBack}
            className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:underline`}
          >
            ← Back
          </button>
          <div className="bg-red-900/20 border border-red-500 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-400 mb-2">Error Loading Call</h2>
            <p className="text-gray-300">{error}</p>
            <button
              onClick={fetchCallDetail}
              className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  // Determine KPI statuses
  const latencyStatus = data.latency_ms > 10000 ? 'critical' : data.latency_ms > 5000 ? 'warning' : 'good';
  const qualityStatus = data.judge_score === null ? 'neutral' : data.judge_score < 5 ? 'critical' : data.judge_score < 7 ? 'warning' : 'good';
  const costStatus = data.total_cost > 0.1 ? 'critical' : data.total_cost > 0.05 ? 'warning' : 'good';

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-7xl mx-auto p-8">
        
        {/* Back Button */}
        <button
          onClick={handleBack}
          className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:underline`}
        >
          ← Back to {data.agent_name}.{data.operation}
        </button>

        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <h1 className={`text-3xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-4xl">{theme.emoji}</span>
              Call Detail
            </h1>
            <code className="text-sm text-gray-500 font-mono">
              {callId.substring(0, 16)}...
            </code>
          </div>
          <div className="text-lg font-mono text-gray-300">
            {data.agent_name}.{data.operation}
          </div>
          <div className="text-sm text-gray-500 mt-1">
            {data.timestamp ? new Date(data.timestamp).toLocaleString() : 'Unknown time'}
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <KPICard
            label="Latency"
            value={`${(data.latency_ms / 1000).toFixed(1)}s`}
            subtext={data.time_to_first_token_ms ? `TTFT: ${data.time_to_first_token_ms}ms` : null}
            status={latencyStatus}
            theme={theme}
          />
          <KPICard
            label="Tokens"
            value={data.total_tokens?.toLocaleString() || '—'}
            subtext={`${data.prompt_tokens?.toLocaleString() || 0} + ${data.completion_tokens?.toLocaleString() || 0}`}
            status="neutral"
            theme={theme}
          />
          <KPICard
            label="Cost"
            value={`$${data.total_cost?.toFixed(4) || '0.0000'}`}
            subtext={data.model_name}
            status={costStatus}
            theme={theme}
          />
          <KPICard
            label="Quality"
            value={data.judge_score !== null ? `${data.judge_score.toFixed(1)}/10` : '—'}
            subtext={data.hallucination_flag ? '⚠️ Hallucination' : data.success ? '✅ Success' : '❌ Error'}
            status={qualityStatus}
            theme={theme}
          />
        </div>

        {/* Diagnosis Section */}
        {data.diagnosis && data.diagnosis.issues && data.diagnosis.issues.length > 0 && (
          <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
            <div className={`${theme.bgLight} p-4 border-b-2 ${theme.border}`}>
              <h3 className={`text-lg font-semibold ${theme.text}`}>
                🎯 Diagnosis & Recommendations
              </h3>
            </div>
            
            <div className="p-6 space-y-6">
              {/* Issues */}
              <div>
                <h4 className="text-sm font-semibold text-gray-400 mb-3">ISSUES DETECTED</h4>
                <div className="space-y-3">
                  {data.diagnosis.issues.map((issue, idx) => (
                    <IssueBadge key={idx} issue={issue} theme={theme} />
                  ))}
                </div>
              </div>
              
              {/* Recommendations */}
              {data.diagnosis.recommendations && data.diagnosis.recommendations.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-gray-400 mb-3">RECOMMENDATIONS</h4>
                  <div className="grid md:grid-cols-2 gap-3">
                    {data.diagnosis.recommendations.map((rec, idx) => (
                      <RecommendationCard key={idx} rec={rec} theme={theme} />
                    ))}
                  </div>
                </div>
              )}
              
              {/* Comparison */}
              {data.comparison && data.comparison.available && (
                <div className={`p-4 rounded-lg ${theme.bgLight} border ${theme.border}`}>
                  <h4 className="text-sm font-semibold text-gray-400 mb-2">📊 COMPARISON</h4>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <div className="text-gray-400">This call</div>
                      <div className={`font-bold ${theme.text}`}>{(data.latency_ms / 1000).toFixed(1)}s</div>
                    </div>
                    <div>
                      <div className="text-gray-400">Operation avg</div>
                      <div className="font-bold text-gray-300">{(data.comparison.operation_avg_latency_ms / 1000).toFixed(1)}s</div>
                    </div>
                    <div>
                      <div className="text-gray-400">Ratio</div>
                      <div className={`font-bold ${data.comparison.latency_ratio > 2 ? 'text-red-400' : 'text-green-400'}`}>
                        {data.comparison.latency_ratio}x
                      </div>
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 mt-2">
                    Based on {data.comparison.operation_call_count} calls in last 7 days
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Prompt Section */}
        <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          <div className={`${theme.bgLight} p-4 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              📝 Prompt
            </h3>
          </div>
          
          <div className="p-4 space-y-3">
            {data.system_prompt && (
              <CollapsibleSection
                title="System Prompt"
                tokenCount={data.system_prompt_tokens}
                content={data.system_prompt}
                theme={theme}
              />
            )}
            
            {data.user_message && (
              <CollapsibleSection
                title="User Message"
                tokenCount={data.user_message_tokens}
                content={data.user_message}
                theme={theme}
              />
            )}
            
            {data.prompt && !data.system_prompt && !data.user_message && (
              <CollapsibleSection
                title="Full Prompt"
                tokenCount={data.prompt_tokens}
                content={data.prompt}
                theme={theme}
                defaultOpen={true}
              />
            )}
            
            {data.prompt && (data.system_prompt || data.user_message) && (
              <CollapsibleSection
                title="Full Prompt (raw)"
                tokenCount={data.prompt_tokens}
                content={data.prompt}
                theme={theme}
              />
            )}
          </div>
        </div>

        {/* Response Section */}
        <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          <div className={`${theme.bgLight} p-4 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              💬 Response
            </h3>
          </div>
          
          <div className="p-4">
            <CollapsibleSection
              title="Response"
              tokenCount={data.completion_tokens}
              content={data.response_text}
              theme={theme}
              defaultOpen={true}
            />
          </div>
        </div>

        {/* Metadata Section */}
        <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          <div className={`${theme.bgLight} p-4 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              📊 Metadata
            </h3>
          </div>
          
          <div className="p-4">
            <div className="grid md:grid-cols-2 gap-4 text-sm">
              <div className="space-y-2">
                <div className="flex justify-between py-2 border-b border-gray-800">
                  <span className="text-gray-400">Model</span>
                  <span className="font-mono">{data.model_name || '—'}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-800">
                  <span className="text-gray-400">Provider</span>
                  <span className="font-mono">{data.provider || '—'}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-800">
                  <span className="text-gray-400">Temperature</span>
                  <span className={`font-mono ${data.temperature === null ? 'text-yellow-400' : ''}`}>
                    {data.temperature !== null ? data.temperature : '(not set)'}
                  </span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-800">
                  <span className="text-gray-400">Max Tokens</span>
                  <span className={`font-mono ${data.max_tokens === null ? 'text-yellow-400' : ''}`}>
                    {data.max_tokens !== null ? data.max_tokens : '(not set)'}
                  </span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-800">
                  <span className="text-gray-400">Cached</span>
                  <span className={data.cache_hit ? 'text-green-400' : 'text-gray-500'}>
                    {data.cache_hit ? '✅ Yes' : '❌ No'}
                  </span>
                </div>
              </div>
              
              <div className="space-y-2">
                <div className="flex justify-between py-2 border-b border-gray-800">
                  <span className="text-gray-400">Session ID</span>
                  <span className="font-mono text-xs">{data.session_id?.substring(0, 16) || '—'}...</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-800">
                  <span className="text-gray-400">Conversation ID</span>
                  <span className="font-mono text-xs">{data.conversation_id?.substring(0, 16) || '—'}...</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-800">
                  <span className="text-gray-400">Turn Number</span>
                  <span className="font-mono">{data.turn_number || '—'}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-800">
                  <span className="text-gray-400">User ID</span>
                  <span className="font-mono text-xs">{data.user_id?.substring(0, 16) || '—'}...</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-800">
                  <span className="text-gray-400">Retry Count</span>
                  <span className={`font-mono ${data.retry_count > 0 ? 'text-yellow-400' : ''}`}>
                    {data.retry_count || 0}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Actions Footer */}
        <div className="flex justify-between items-center py-4 border-t border-gray-800">
          <button
            onClick={handleBack}
            className="text-gray-400 hover:text-white transition-colors"
          >
            ← Back
          </button>
          
          <div className="flex gap-3">
            <button
              onClick={handleExportJSON}
              className={`px-4 py-2 border ${theme.border} rounded-lg ${theme.text} hover:${theme.bgLight} transition-colors`}
            >
              Export JSON
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}