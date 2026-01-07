/**
 * AIAnalysisPanel - LLM-Powered Fix Recommendations
 *
 * Displays contextual, AI-generated recommendations for optimizing an LLM call.
 * Used in Layer 3 to replace or augment static rule-based fixes.
 *
 * UPDATED: Improved visual hierarchy and readability
 * - Clear section groupings with outer boxes
 * - Larger, more prominent metrics
 * - Vertical stacking for before/after comparisons
 * - Better spacing and typography
 */

import { useState } from 'react';
import { BASE_THEME } from '../../../utils/themeUtils';

// Helper to safely render any value (handles objects)
const safeRender = (value) => {
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return value;
};

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

export default function AIAnalysisPanel({ callId, responseText = null }) {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedRec, setExpandedRec] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/analysis/calls/${callId}`);
      const data = await response.json();

      if (data.error) {
        setError(data.error + (data.details ? `: ${data.details}` : ''));
      } else {
        setAnalysis(data);
        // Auto-expand first recommendation
        if (data.recommendations?.length > 0) {
          setExpandedRec(data.recommendations[0].id);
        }
      }
    } catch (err) {
      setError(`Failed to analyze: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCopyCode = (code, recId) => {
    navigator.clipboard.writeText(typeof code === 'object' ? JSON.stringify(code, null, 2) : code);
    setCopiedId(recId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // ─────────────────────────────────────────────────────────────────────────────
  // NOT YET ANALYZED STATE
  // ─────────────────────────────────────────────────────────────────────────────

  if (!analysis && !loading && !error) {
    return (
      <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-8`}>
        <div className="text-center">
          <div className="text-5xl mb-4">🤖</div>
          <h3 className={`text-xl font-semibold ${BASE_THEME.text.primary} mb-3`}>
            AI-Powered Analysis
          </h3>
          <p className={`${BASE_THEME.text.secondary} text-base mb-6 max-w-md mx-auto`}>
            Get tailored recommendations by analyzing your actual prompt and response.
            The AI will suggest specific changes based on your use case.
          </p>
          <button
            onClick={handleAnalyze}
            className="px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-lg font-medium transition-colors flex items-center gap-2 mx-auto text-base"
          >
            <span>🔍</span>
            <span>Analyze This Call</span>
            <span className="text-purple-300 text-sm">(~$0.02)</span>
          </button>
          <p className={`text-sm ${BASE_THEME.text.muted} mt-4`}>
            Uses GPT-4o to analyze your prompt, response, and metrics
          </p>
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // LOADING STATE
  // ─────────────────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-8`}>
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin" />
          <div className={`${BASE_THEME.text.secondary} text-base`}>Analyzing call with AI...</div>
          <div className={`${BASE_THEME.text.muted} text-sm`}>This may take 5-10 seconds</div>
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // ERROR STATE
  // ─────────────────────────────────────────────────────────────────────────────

  if (error) {
    return (
      <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.status.error.border} rounded-lg p-6`}>
        <div className="flex items-start gap-3">
          <span className="text-2xl">⚠️</span>
          <div>
            <h3 className={`${BASE_THEME.status.error.text} font-semibold text-lg mb-2`}>Analysis Failed</h3>
            <p className={`${BASE_THEME.text.secondary} text-base`}>{safeRender(error)}</p>
            <button
              onClick={handleAnalyze}
              className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-sm"
            >
              Retry Analysis
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // ANALYSIS RESULTS
  // ─────────────────────────────────────────────────────────────────────────────

  const { analysis: callAnalysis, recommendations = [] } = analysis;

  return (
    <div className="space-y-6">

      {/* Analysis Summary - Outer container */}
      <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-6`}>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-semibold text-purple-400 flex items-center gap-3">
            <span className="text-2xl">🤖</span>
            AI Analysis
          </h3>
          {analysis.from_cache && (
            <span className="px-3 py-1 bg-gray-700 rounded text-sm text-gray-300">
              Cached
            </span>
          )}
        </div>

        {callAnalysis && (
          <div className="space-y-6">
            {/* Purpose - Prominent section */}
            <div className={`${BASE_THEME.container.tertiary} rounded-lg p-4`}>
              <div className={`text-base font-bold ${BASE_THEME.text.muted} uppercase tracking-wide mb-2`}>Purpose</div>
              <p className={`${BASE_THEME.text.primary} text-base`}>{safeRender(callAnalysis.purpose)}</p>
            </div>

            {/* Output Format Assessment */}
            {callAnalysis.output_format_assessment && (
              <div className={`${BASE_THEME.container.tertiary} rounded-lg p-4`}>
                <div className={`text-base font-bold ${BASE_THEME.text.muted} uppercase tracking-wide mb-2`}>Output Format</div>
                <p className={`${BASE_THEME.text.primary} text-base`}>{safeRender(callAnalysis.output_format_assessment)}</p>
              </div>
            )}

            {/* Essential vs Redundant - Side by side */}
            <div className="grid grid-cols-2 gap-4">
              <div className={`${BASE_THEME.container.tertiary} rounded-lg p-4`}>
                <div className={`text-base font-bold ${BASE_THEME.status.success.text} uppercase tracking-wide mb-3`}>Essential Output</div>
                <ul className="space-y-2">
                  {callAnalysis.essential_output?.map((item, i) => (
                    <li key={i} className={`text-base ${BASE_THEME.text.secondary} flex items-start gap-2`}>
                      <span className={BASE_THEME.status.success.text}>✓</span>
                      <span>{safeRender(item)}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className={`${BASE_THEME.container.tertiary} rounded-lg p-4`}>
                <div className={`text-base font-bold ${BASE_THEME.status.warning.text} uppercase tracking-wide mb-3`}>Redundant Output</div>
                <ul className="space-y-2">
                  {callAnalysis.redundant_output?.map((item, i) => (
                    <li key={i} className={`text-base ${BASE_THEME.text.secondary} flex items-start gap-2`}>
                      <span className={BASE_THEME.status.warning.text}>−</span>
                      <span>{safeRender(item)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Prompt Issues */}
            {callAnalysis.prompt_issues?.length > 0 && (
              <div className={`${BASE_THEME.container.tertiary} rounded-lg p-4`}>
                <div className={`text-base font-bold ${BASE_THEME.status.error.text} uppercase tracking-wide mb-3`}>Prompt Issues</div>
                <ul className="space-y-2">
                  {callAnalysis.prompt_issues.map((issue, i) => (
                    <li key={i} className={`text-base ${BASE_THEME.text.secondary} flex items-start gap-2`}>
                      <span className={BASE_THEME.status.error.text}>!</span>
                      <span>{safeRender(issue)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Recommendations Section */}
      <div className="space-y-4">
        <h3 className={`text-xl font-semibold ${BASE_THEME.text.primary} flex items-center gap-3`}>
          <span className="text-2xl">💡</span>
          Recommendations
        </h3>

        {recommendations.map((rec, index) => (
          <RecommendationCard
            key={rec.id || index}
            recommendation={rec}
            index={index}
            isExpanded={expandedRec === rec.id}
            onToggle={() => setExpandedRec(expandedRec === rec.id ? null : rec.id)}
            onCopyCode={(code) => handleCopyCode(code, rec.id)}
            isCopied={copiedId === rec.id}
            responseText={responseText}
          />
        ))}
      </div>

      {/* Re-analyze button */}
      <div className="text-center pt-4">
        <button
          onClick={handleAnalyze}
          className={`text-sm ${BASE_THEME.text.muted} hover:${BASE_THEME.text.secondary} underline`}
        >
          Re-analyze (clear cache)
        </button>
        {analysis.analysis_cost && (
          <span className={`text-sm ${BASE_THEME.text.muted} ml-2`}>
            Analysis cost: ${analysis.analysis_cost}
          </span>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// RECOMMENDATION CARD
// ─────────────────────────────────────────────────────────────────────────────

function RecommendationCard({
  recommendation,
  index,
  isExpanded,
  onToggle,
  onCopyCode,
  isCopied,
  responseText,
}) {
  const rec = recommendation;

  const priorityColors = {
    high: 'bg-red-500',
    medium: 'bg-yellow-500',
    low: 'bg-green-500',
  };

  const effortColors = {
    Low: 'text-green-400',
    Medium: 'text-yellow-400',
    High: 'text-red-400',
  };

  return (
    <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg overflow-hidden`}>
      {/* Header - Always visible */}
      <div
        onClick={onToggle}
        className="p-5 cursor-pointer hover:bg-gray-700/30 transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Priority indicator */}
            <div className={`w-3 h-3 rounded-full ${priorityColors[rec.priority] || 'bg-gray-500'}`} />

            {/* Rank */}
            <span className={`text-2xl font-bold ${BASE_THEME.text.muted}`}>#{index + 1}</span>

            {/* Title */}
            <div>
              <h4 className={`text-lg font-semibold ${BASE_THEME.text.primary}`}>{safeRender(rec.title)}</h4>
              <div className="flex items-center gap-3 text-sm mt-1">
                <span className={effortColors[rec.effort] || 'text-gray-400'}>
                  {safeRender(rec.effort)} effort
                </span>
                <span className={BASE_THEME.text.muted}>•</span>
                <span className={BASE_THEME.text.secondary}>
                  {Math.round((rec.confidence || 0) * 100)}% confidence
                </span>
              </div>
            </div>
          </div>

          {/* Impact preview */}
          <div className="flex items-center gap-4">
            {rec.estimated_impact?.cost_reduction_pct > 0 && (
              <span className={`${BASE_THEME.status.success.text} text-base font-semibold`}>
                -{rec.estimated_impact.cost_reduction_pct}% cost
              </span>
            )}
            <span className={`${BASE_THEME.text.muted} text-xl`}>
              {isExpanded ? '▼' : '▶'}
            </span>
          </div>
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className={`border-t ${BASE_THEME.border.default} p-6 space-y-6`}>

          {/* Problem & Solution - Side by side */}
          <div className="grid grid-cols-2 gap-4">
            <div className={`${BASE_THEME.container.tertiary} rounded-lg p-4`}>
              <div className={`text-base font-bold ${BASE_THEME.status.error.text} uppercase tracking-wide mb-2`}>Problem</div>
              <p className={`text-base ${BASE_THEME.text.primary}`}>{safeRender(rec.problem)}</p>
            </div>
            <div className={`${BASE_THEME.container.tertiary} rounded-lg p-4`}>
              <div className={`text-base font-bold ${BASE_THEME.status.success.text} uppercase tracking-wide mb-2`}>Solution</div>
              <p className={`text-base ${BASE_THEME.text.primary}`}>{safeRender(rec.solution)}</p>
            </div>
          </div>

          {/* Impact metrics - Larger and more prominent */}
          {rec.estimated_impact && (
            <div className={`${BASE_THEME.container.tertiary} rounded-lg p-5`}>
              <div className={`text-base font-bold ${BASE_THEME.text.muted} uppercase tracking-wide mb-4`}>Estimated Impact</div>
              <div className="grid grid-cols-3 gap-4">
                <ImpactMetric
                  label="Tokens"
                  before={rec.estimated_impact.tokens_before}
                  after={rec.estimated_impact.tokens_after}
                  change={rec.estimated_impact.token_reduction_pct}
                />
                <ImpactMetric
                  label="Latency"
                  change={rec.estimated_impact.latency_reduction_pct}
                />
                <ImpactMetric
                  label="Cost"
                  change={rec.estimated_impact.cost_reduction_pct}
                />
              </div>
            </div>
          )}

          {/* Implementation Code - Before/After (like static recommendations) */}
          {rec.implementation && (rec.implementation.code_before || rec.implementation.code_after) && (
            <div className={`${BASE_THEME.container.tertiary} rounded-lg p-5`}>
              <div className={`text-base font-bold ${BASE_THEME.text.muted} uppercase tracking-wide mb-4`}>📝 Implementation</div>
              <div className="grid grid-cols-2 gap-4">
                {/* Before */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className={`text-base font-bold ${BASE_THEME.status.error.text}`}>BEFORE</div>
                    <button
                      onClick={() => onCopyCode(rec.implementation.code_before)}
                      className={`px-3 py-1 ${BASE_THEME.container.secondary} hover:opacity-80 ${BASE_THEME.text.secondary} text-xs rounded`}
                    >
                      Copy
                    </button>
                  </div>
                  <pre className={`${BASE_THEME.container.primary} rounded-lg p-4 text-sm ${BASE_THEME.text.secondary} overflow-x-auto max-h-64 whitespace-pre-wrap font-mono`}>
                    {safeRender(rec.implementation.code_before)}
                  </pre>
                </div>
                {/* After */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <div className={`text-base font-bold ${BASE_THEME.status.success.text}`}>AFTER</div>
                    <button
                      onClick={() => onCopyCode(rec.implementation.code_after)}
                      className="px-3 py-1 bg-purple-600 hover:bg-purple-500 text-white text-xs rounded"
                    >
                      Copy
                    </button>
                  </div>
                  <pre className={`${BASE_THEME.container.primary} rounded-lg p-4 text-sm ${BASE_THEME.text.primary} overflow-x-auto max-h-64 whitespace-pre-wrap font-mono`}>
                    {safeRender(rec.implementation.code_after)}
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* Prompt Change (if applicable) */}
          {rec.new_prompt && rec.new_prompt !== 'N/A' && rec.new_prompt !== 'N/A - no prompt change needed' && (
            <div className={`${BASE_THEME.container.tertiary} rounded-lg p-5`}>
              <div className="flex items-center justify-between mb-4">
                <div className={`text-base font-bold ${BASE_THEME.text.muted} uppercase tracking-wide`}>📄 Prompt Change</div>
                <button
                  onClick={() => onCopyCode(rec.new_prompt)}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white text-sm rounded-lg"
                >
                  {isCopied ? '✓ Copied!' : 'Copy New Prompt'}
                </button>
              </div>
              <pre className={`${BASE_THEME.container.primary} rounded-lg p-4 text-base ${BASE_THEME.text.primary} overflow-x-auto max-h-48 whitespace-pre-wrap`}>
                {safeRender(rec.new_prompt)}
              </pre>
            </div>
          )}

          {/* Output Comparison (optional - only show if expected_output_example exists) */}
          {rec.expected_output_example && (
            <div className={`${BASE_THEME.container.tertiary} rounded-lg p-5`}>
              <div className={`text-base font-bold ${BASE_THEME.text.muted} uppercase tracking-wide mb-4`}>📤 Expected Output Change</div>

              {responseText ? (
                <div className="space-y-4">
                  <div>
                    <div className={`text-base font-bold ${BASE_THEME.status.error.text} mb-2`}>Current Output</div>
                    <pre className={`${BASE_THEME.container.primary} rounded-lg p-4 text-base ${BASE_THEME.text.secondary} overflow-x-auto max-h-32 whitespace-pre-wrap`}>
                      {safeRender(responseText).substring(0, 500)}{responseText?.length > 500 ? '...' : ''}
                    </pre>
                  </div>
                  <div className="flex justify-center">
                    <span className={`${BASE_THEME.text.muted} text-2xl`}>↓</span>
                  </div>
                  <div>
                    <div className={`text-base font-bold ${BASE_THEME.status.success.text} mb-2`}>Expected After Fix</div>
                    <pre className={`${BASE_THEME.container.primary} rounded-lg p-4 text-base ${BASE_THEME.text.primary} overflow-x-auto max-h-32 whitespace-pre-wrap`}>
                      {safeRender(rec.expected_output_example)}
                    </pre>
                  </div>
                </div>
              ) : (
                <div>
                  <div className={`text-base font-bold ${BASE_THEME.status.success.text} mb-2`}>Expected Output</div>
                  <pre className={`${BASE_THEME.container.primary} rounded-lg p-4 text-base ${BASE_THEME.text.primary} overflow-x-auto max-h-32 whitespace-pre-wrap`}>
                    {safeRender(rec.expected_output_example)}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* Preserves & Tradeoffs - Side by side since they're short */}
          {(rec.preserves?.length > 0 || rec.tradeoffs?.length > 0) && (
            <div className="grid grid-cols-2 gap-4">
              {rec.preserves?.length > 0 && (
                <div className={`${BASE_THEME.container.tertiary} rounded-lg p-4`}>
                  <div className={`text-base font-bold ${BASE_THEME.status.success.text} uppercase tracking-wide mb-3`}>Preserves</div>
                  <ul className="space-y-2">
                    {rec.preserves.map((item, i) => (
                      <li key={i} className={`text-base ${BASE_THEME.text.secondary} flex items-start gap-2`}>
                        <span className={BASE_THEME.status.success.text}>✓</span>
                        <span>{safeRender(item)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {rec.tradeoffs?.length > 0 && (
                <div className={`${BASE_THEME.container.tertiary} rounded-lg p-4`}>
                  <div className={`text-base font-bold ${BASE_THEME.status.warning.text} uppercase tracking-wide mb-3`}>Trade-offs</div>
                  <ul className="space-y-2">
                    {rec.tradeoffs.map((item, i) => (
                      <li key={i} className={`text-base ${BASE_THEME.text.secondary} flex items-start gap-2`}>
                        <span className={BASE_THEME.status.warning.text}>⚠</span>
                        <span>{safeRender(item)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// IMPACT METRIC - Larger and more prominent
// ─────────────────────────────────────────────────────────────────────────────

function ImpactMetric({ label, before, after, change }) {
  const isImprovement = change > 0;

  // Label-specific wording
  const getChangeText = () => {
    if (change == null) return null;
    const value = Math.abs(change);

    switch (label.toLowerCase()) {
      case 'tokens':
        return `${value}% reduction`;
      case 'latency':
        return `${value}% faster`;
      case 'cost':
        return `${value}% savings`;
      default:
        return `${value}% improvement`;
    }
  };

  return (
    <div className={`${BASE_THEME.container.primary} rounded-lg p-4 text-center`}>
      <div className={`text-sm ${BASE_THEME.text.muted} uppercase tracking-wide mb-2`}>{label}</div>
      {before != null && after != null && (
        <div className={`text-base ${BASE_THEME.text.secondary} mb-1`}>
          <span>{safeRender(before)}</span>
          <span className={BASE_THEME.text.muted}> → </span>
          <span className={BASE_THEME.text.primary}>{safeRender(after)}</span>
        </div>
      )}
      {change != null && (
        <div className={`text-2xl font-bold ${isImprovement ? BASE_THEME.status.success.text : BASE_THEME.status.error.text}`}>
          {getChangeText()}
        </div>
      )}
    </div>
  );
}
