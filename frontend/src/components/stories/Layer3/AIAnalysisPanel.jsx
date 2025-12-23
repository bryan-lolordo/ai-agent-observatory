/**
 * AIAnalysisPanel - LLM-Powered Fix Recommendations
 * 
 * Displays contextual, AI-generated recommendations for optimizing an LLM call.
 * Used in Layer 3 to replace or augment static rule-based fixes.
 */

import { useState } from 'react';

// Helper to safely render any value (handles objects)
const safeRender = (value) => {
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return value;
};

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

export default function AIAnalysisPanel({ callId, themeColor = '#ec4899', responseText = null }) {
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
      <div className="bg-gradient-to-br from-purple-900/20 to-slate-900 rounded-xl border border-purple-500/30 p-6">
        <div className="text-center">
          <div className="text-4xl mb-4">🤖</div>
          <h3 className="text-lg font-semibold text-purple-300 mb-2">
            AI-Powered Analysis
          </h3>
          <p className="text-slate-400 text-sm mb-6 max-w-md mx-auto">
            Get tailored recommendations by analyzing your actual prompt and response.
            The AI will suggest specific changes based on your use case.
          </p>
          <button
            onClick={handleAnalyze}
            className="px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-lg font-medium transition-colors flex items-center gap-2 mx-auto"
          >
            <span>🔍</span>
            <span>Analyze This Call</span>
            <span className="text-purple-300 text-xs">(~$0.02)</span>
          </button>
          <p className="text-xs text-slate-500 mt-3">
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
      <div className="bg-slate-900 rounded-xl border border-slate-700 p-8">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin" />
          <div className="text-slate-300">Analyzing call with AI...</div>
          <div className="text-xs text-slate-500">This may take 5-10 seconds</div>
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // ERROR STATE
  // ─────────────────────────────────────────────────────────────────────────────
  
  if (error) {
    return (
      <div className="bg-red-900/20 rounded-xl border border-red-500/50 p-6">
        <div className="flex items-start gap-3">
          <span className="text-2xl">⚠️</span>
          <div>
            <h3 className="text-red-400 font-semibold mb-1">Analysis Failed</h3>
            <p className="text-slate-300 text-sm">{safeRender(error)}</p>
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
      
      {/* Analysis Summary */}
      <div className="bg-slate-900 rounded-xl border border-slate-700 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-purple-300 flex items-center gap-2">
            <span>🤖</span>
            AI Analysis
          </h3>
          {analysis.from_cache && (
            <span className="px-2 py-1 bg-slate-800 rounded text-xs text-slate-400">
              Cached
            </span>
          )}
        </div>
        
        {callAnalysis && (
          <div className="space-y-4">
            {/* Purpose */}
            <div>
              <div className="text-xs text-slate-500 uppercase mb-1">Purpose</div>
              <p className="text-slate-300">{safeRender(callAnalysis.purpose)}</p>
            </div>
            
            {/* Output Format Assessment */}
            {callAnalysis.output_format_assessment && (
              <div>
                <div className="text-xs text-slate-500 uppercase mb-1">Output Format</div>
                <p className="text-slate-300">{safeRender(callAnalysis.output_format_assessment)}</p>
              </div>
            )}
            
            {/* Essential vs Redundant */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-green-500 uppercase mb-2">Essential Output</div>
                <ul className="text-sm text-slate-400 space-y-1">
                  {callAnalysis.essential_output?.map((item, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-green-500">✓</span>
                      <span>{safeRender(item)}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="text-xs text-yellow-500 uppercase mb-2">Redundant Output</div>
                <ul className="text-sm text-slate-400 space-y-1">
                  {callAnalysis.redundant_output?.map((item, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-yellow-500">−</span>
                      <span>{safeRender(item)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            
            {/* Prompt Issues */}
            {callAnalysis.prompt_issues?.length > 0 && (
              <div>
                <div className="text-xs text-red-400 uppercase mb-2">Prompt Issues</div>
                <ul className="text-sm text-slate-400 space-y-1">
                  {callAnalysis.prompt_issues.map((issue, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-red-400">!</span>
                      <span>{safeRender(issue)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Recommendations */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
          <span>💡</span>
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
            themeColor={themeColor}
            responseText={responseText}
          />
        ))}
      </div>

      {/* Re-analyze button */}
      <div className="text-center pt-4">
        <button
          onClick={handleAnalyze}
          className="text-sm text-slate-500 hover:text-slate-300 underline"
        >
          Re-analyze (clear cache)
        </button>
        {analysis.analysis_cost && (
          <span className="text-xs text-slate-600 ml-2">
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
  themeColor,
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
    <div className="bg-slate-900 rounded-xl border border-slate-700 overflow-hidden">
      {/* Header - Always visible */}
      <div
        onClick={onToggle}
        className="p-4 cursor-pointer hover:bg-slate-800/50 transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Priority indicator */}
            <div className={`w-2 h-2 rounded-full ${priorityColors[rec.priority] || 'bg-gray-500'}`} />
            
            {/* Rank */}
            <span className="text-2xl font-bold text-slate-600">#{index + 1}</span>
            
            {/* Title */}
            <div>
              <h4 className="font-semibold text-slate-200">{safeRender(rec.title)}</h4>
              <div className="flex items-center gap-3 text-xs mt-1">
                <span className={effortColors[rec.effort] || 'text-slate-400'}>
                  {safeRender(rec.effort)} effort
                </span>
                <span className="text-slate-500">•</span>
                <span className="text-slate-400">
                  {Math.round((rec.confidence || 0) * 100)}% confidence
                </span>
              </div>
            </div>
          </div>
          
          {/* Impact preview */}
          <div className="flex items-center gap-4">
            {rec.estimated_impact?.cost_reduction_pct > 0 && (
              <span className="text-green-400 text-sm font-semibold">
                -{rec.estimated_impact.cost_reduction_pct}% cost
              </span>
            )}
            <span className="text-slate-400 text-lg">
              {isExpanded ? '▼' : '▶'}
            </span>
          </div>
        </div>
      </div>
      
      {/* Expanded content */}
      {isExpanded && (
        <div className="border-t border-slate-700 p-4 space-y-4">
          
          {/* Problem & Solution */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs text-red-400 uppercase mb-2">Problem</div>
              <p className="text-sm text-slate-300">{safeRender(rec.problem)}</p>
            </div>
            <div>
              <div className="text-xs text-green-400 uppercase mb-2">Solution</div>
              <p className="text-sm text-slate-300">{safeRender(rec.solution)}</p>
            </div>
          </div>
          
          {/* Impact metrics */}
          {rec.estimated_impact && (
            <div>
              <div className="text-xs text-slate-500 uppercase mb-2">Estimated Impact</div>
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
          
          {/* New prompt */}
          {rec.new_prompt && rec.new_prompt !== 'N/A' && rec.new_prompt !== 'N/A - no prompt change needed' && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs text-purple-400 uppercase">Optimized Prompt</div>
                <button
                  onClick={() => onCopyCode(rec.new_prompt)}
                  className="px-3 py-1 bg-purple-600 hover:bg-purple-500 text-white text-xs rounded"
                >
                  {isCopied ? '✓ Copied!' : 'Copy Prompt'}
                </button>
              </div>
              <pre className="bg-slate-800 rounded-lg p-4 text-sm text-slate-300 overflow-x-auto max-h-64 whitespace-pre-wrap">
                {safeRender(rec.new_prompt)}
              </pre>
            </div>
          )}
          
          {/* Output Before/After Comparison */}
          {(responseText || rec.expected_output_example) && (
            <div>
              <div className="text-xs text-slate-500 uppercase mb-2">📤 Output Comparison</div>
              
              {responseText && rec.expected_output_example ? (
                // Side-by-side comparison when both are available
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-xs text-red-400 mb-2 flex items-center gap-2">
                      <span>BEFORE</span>
                      <span className="text-slate-500">(Current Output)</span>
                    </div>
                    <pre className="bg-slate-800 rounded-lg p-4 text-sm text-slate-400 overflow-x-auto max-h-48 whitespace-pre-wrap border border-red-900/50">
                      {safeRender(responseText).substring(0, 1000)}{responseText?.length > 1000 ? '...' : ''}
                    </pre>
                    {responseText?.length > 1000 && (
                      <div className="text-xs text-slate-500 mt-1">
                        Showing first 1000 chars of {responseText.length.toLocaleString()} total
                      </div>
                    )}
                  </div>
                  <div>
                    <div className="text-xs text-green-400 mb-2 flex items-center gap-2">
                      <span>AFTER</span>
                      <span className="text-slate-500">(Expected with fix)</span>
                    </div>
                    <pre className="bg-slate-800 rounded-lg p-4 text-sm text-slate-300 overflow-x-auto max-h-48 whitespace-pre-wrap border border-green-900/50">
                      {safeRender(rec.expected_output_example)}
                    </pre>
                  </div>
                </div>
              ) : rec.expected_output_example ? (
                // Only expected output available
                <div>
                  <div className="text-xs text-green-400 mb-2">Expected Output (After Fix)</div>
                  <pre className="bg-slate-800 rounded-lg p-4 text-sm text-slate-300 overflow-x-auto max-h-40 whitespace-pre-wrap border border-green-900/50">
                    {safeRender(rec.expected_output_example)}
                  </pre>
                </div>
              ) : responseText ? (
                // Only current output available
                <div>
                  <div className="text-xs text-slate-400 mb-2">Current Output</div>
                  <pre className="bg-slate-800 rounded-lg p-4 text-sm text-slate-400 overflow-x-auto max-h-40 whitespace-pre-wrap">
                    {safeRender(responseText).substring(0, 500)}{responseText?.length > 500 ? '...' : ''}
                  </pre>
                </div>
              ) : null}
            </div>
          )}
          
          {/* Preserves & Tradeoffs */}
          <div className="grid grid-cols-2 gap-4">
            {rec.preserves?.length > 0 && (
              <div>
                <div className="text-xs text-green-500 uppercase mb-2">Preserves</div>
                <ul className="text-sm text-slate-400 space-y-1">
                  {rec.preserves.map((item, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-green-500">✓</span>
                      <span>{safeRender(item)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {rec.tradeoffs?.length > 0 && (
              <div>
                <div className="text-xs text-yellow-500 uppercase mb-2">Trade-offs</div>
                <ul className="text-sm text-slate-400 space-y-1">
                  {rec.tradeoffs.map((item, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-yellow-500">⚠</span>
                      <span>{safeRender(item)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// IMPACT METRIC
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
    <div className="bg-slate-800 rounded-lg p-3">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      {before != null && after != null ? (
        <div className="text-sm">
          <span className="text-slate-400">{safeRender(before)}</span>
          <span className="text-slate-600 mx-1">→</span>
          <span className="text-slate-200">{safeRender(after)}</span>
        </div>
      ) : null}
      {change != null && (
        <div className={`text-lg font-bold ${isImprovement ? 'text-green-400' : 'text-red-400'}`}>
          {getChangeText()}
        </div>
      )}
    </div>
  );
}