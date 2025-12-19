/**
 * Layer 3: Cache Opportunity Detail
 * 
 * Shows detailed view of a single cache opportunity with:
 * - Type-specific diagnosis
 * - Code snippet for fix
 * - Expected impact
 * - All calls in this group
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { STORY_THEMES } from '../../../config/theme';
import { InlineLoading } from '../../../components/common/Loading';
import { formatNumber, formatCurrency } from '../../../utils/formatters';

const theme = STORY_THEMES.cache;

// Collapsible Section Component
function CollapsibleSection({ title, tokenCount, content, defaultOpen = false }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  const handleCopy = async (e) => {
    e.stopPropagation();
    if (content) {
      await navigator.clipboard.writeText(content);
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
            <span className="text-gray-400 text-sm">({formatNumber(tokenCount)} tokens)</span>
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

export default function CacheOpportunityDetail() {
  const { agent, operation, group_id } = useParams();
  const navigate = useNavigate();
  
  // State
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [codeCopied, setCodeCopied] = useState(false);

  // Fetch data
  useEffect(() => {
    fetchData();
  }, [agent, operation, group_id]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(
        `/api/stories/cache/operations/${encodeURIComponent(agent)}/${encodeURIComponent(operation)}/groups/${group_id}`
      );
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      
      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Error fetching cache opportunity detail:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Navigation handlers
  const handleBack = () => {
    navigate(`/stories/cache/operations/${encodeURIComponent(agent)}/${encodeURIComponent(operation)}`);
  };

  const handleCallClick = (callId) => {
    navigate(`/stories/calls/${callId}?from=cache`);
  };

  const handleCopyCode = () => {
    if (data?.diagnosis?.code_snippet) {
      navigator.clipboard.writeText(data.diagnosis.code_snippet);
      setCodeCopied(true);
      setTimeout(() => setCodeCopied(false), 2000);
    }
  };

  const handleExportJSON = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cache-opportunity-${group_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 p-8 flex items-center justify-center">
        <InlineLoading text="Loading opportunity details..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 p-8">
        <div className="max-w-7xl mx-auto">
          <button
            onClick={handleBack}
            className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:${theme.textLight} transition`}
          >
            ← Back to {operation}
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
    cache_type = 'exact',
    cache_type_emoji = '🎯',
    cache_type_name = 'Exact Match',
    repeat_count = 0,
    wasted_calls = 0,
    wasted_cost_formatted = '$0.00',
    savable_time_formatted = '~0s',
    prompt = '',
    system_prompt = '',
    response_text = '',
    prompt_tokens = 0,
    completion_tokens = 0,
    diagnosis = {},
    calls = [],
  } = data || {};

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-7xl mx-auto p-8">
        
        {/* Back Button */}
        <button
          onClick={handleBack}
          className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:${theme.textLight} transition`}
        >
          ← Back to {agent}.{operation}
        </button>

        {/* Page Header */}
        <div className="mb-8">
          <h1 className={`text-3xl font-bold ${theme.text} flex items-center gap-3`}>
            <span className="text-4xl">{cache_type_emoji}</span>
            {cache_type_name} Opportunity
          </h1>
          <p className="text-gray-400">
            Dashboard &gt; Cache Analysis &gt; {agent} &gt; {operation} &gt; Opportunity
          </p>
          
          {/* Summary Stats */}
          <div className="mt-4 flex gap-6 text-sm">
            <span className="text-gray-400">
              Called: <span className={theme.text}>{formatNumber(repeat_count)}x</span>
            </span>
            <span className="text-gray-400">
              Wasted: <span className="text-red-400">{formatNumber(wasted_calls)} calls</span>
            </span>
            <span className="text-gray-400">
              Cost: <span className="text-red-400">{wasted_cost_formatted}</span>
            </span>
            <span className="text-gray-400">
              Savable: <span className="text-green-400">{savable_time_formatted}</span>
            </span>
          </div>
        </div>

        {/* Diagnosis Card */}
        <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          <div className={`${theme.bgLight} p-6 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text} flex items-center gap-2`}>
              {cache_type_emoji} DIAGNOSIS: {cache_type_name.toUpperCase()}
            </h3>
          </div>
          
          <div className="p-6 space-y-6">
            
            {/* Problem */}
            <div>
              <h4 className="text-sm font-semibold text-red-400 mb-2">🔴 PROBLEM</h4>
              <p className="text-gray-300">{diagnosis.problem}</p>
            </div>

            {/* Why */}
            <div>
              <h4 className="text-sm font-semibold text-gray-400 mb-2">WHY THIS HAPPENS</h4>
              <p className="text-gray-400">{diagnosis.why}</p>
            </div>

            {/* Fix */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold text-green-400">
                  ✅ FIX: {diagnosis.fix_title}
                </h4>
                <button
                  onClick={handleCopyCode}
                  className={`px-4 py-2 ${theme.bg} hover:opacity-80 text-white rounded-lg transition-colors`}
                >
                  {codeCopied ? '✓ Copied!' : 'Copy Code'}
                </button>
              </div>
              <p className="text-gray-400 mb-4">{diagnosis.fix_description}</p>
              
              {/* Code Snippet */}
              <div className="bg-gray-950 rounded-lg p-4 overflow-x-auto border border-gray-800">
                <pre className="text-sm text-gray-100 font-mono whitespace-pre">
                  {diagnosis.code_snippet}
                </pre>
              </div>
            </div>

            {/* Expected Impact */}
            {diagnosis.expected_impact && (
              <div className="bg-green-900/20 rounded-lg p-4 border border-green-700">
                <h4 className="text-sm font-semibold text-green-400 mb-3">📊 EXPECTED IMPACT</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <div className="text-gray-400">Calls</div>
                    <div className="font-semibold text-gray-100">
                      {diagnosis.expected_impact.calls_before} → {diagnosis.expected_impact.calls_after}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400">Reduction</div>
                    <div className="font-semibold text-green-400">
                      {diagnosis.expected_impact.reduction_pct}%
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400">Cost Saved</div>
                    <div className="font-semibold text-green-400">
                      {diagnosis.expected_impact.cost_saved_formatted}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400">Cache Latency</div>
                    <div className="font-semibold text-gray-100">
                      {diagnosis.expected_impact.latency_cached_ms}ms
                    </div>
                  </div>
                </div>
              </div>
            )}

          </div>
        </div>

        {/* Prompt Section */}
        <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          <div className={`${theme.bgLight} p-4 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              📝 The Repeated Prompt
            </h3>
          </div>
          
          <div className="p-4 space-y-3">
            {system_prompt && (
              <CollapsibleSection 
                title="System Prompt" 
                tokenCount={null}
                content={system_prompt}
              />
            )}
            
            <CollapsibleSection 
              title="Full Prompt" 
              tokenCount={prompt_tokens}
              content={prompt}
              defaultOpen={true}
            />
          </div>
        </div>

        {/* Response Section */}
        <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          <div className={`${theme.bgLight} p-4 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              💬 The Response <span className="text-sm font-normal text-gray-400">(generated {repeat_count} times)</span>
            </h3>
          </div>
          
          <div className="p-4">
            <CollapsibleSection 
              title="Response" 
              tokenCount={completion_tokens}
              content={response_text}
            />
          </div>
        </div>

        {/* All Calls Card */}
        <div className={`rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          
          {/* Card Header */}
          <div className={`${theme.bgLight} p-6 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              📋 All {repeat_count} Calls (click row for full details)
            </h3>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-800 sticky top-0">
                <tr className={`border-b-2 ${theme.border}`}>
                  <th className={`text-center py-3 px-4 ${theme.textLight}`}>#</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Timestamp</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>User/Session</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Latency</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Cost</th>
                  <th className={`text-center py-3 px-4 ${theme.textLight}`}>Note</th>
                </tr>
              </thead>
              <tbody>
                {calls.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="py-8 text-center text-gray-500">
                      No calls found
                    </td>
                  </tr>
                ) : (
                  calls.map((call, idx) => (
                    <tr
                      key={call.call_id || idx}
                      onClick={() => handleCallClick(call.call_id)}
                      className={`border-b border-gray-800 cursor-pointer transition-all hover:bg-gradient-to-r hover:${theme.gradient} hover:border-l-4 hover:${theme.border}`}
                    >
                      <td className="py-3 px-4 text-center text-gray-500">
                        {call.index}
                      </td>
                      <td className="py-3 px-4 text-gray-300">
                        {call.timestamp_formatted}
                      </td>
                      <td className="py-3 px-4 text-gray-400 font-mono text-xs">
                        {call.user_id !== '—' ? call.user_id : call.session_id}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        {call.latency_formatted}
                      </td>
                      <td className={`py-3 px-4 text-right ${theme.text}`}>
                        {call.cost_formatted}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className={call.is_first ? 'text-green-400' : 'text-gray-500'}>
                          {call.note}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Footer */}
          <div className="p-4 bg-gray-800 border-t border-gray-700 flex justify-between items-center text-sm text-gray-400">
            <span>
              Showing {calls.length} calls
            </span>
            <button 
              onClick={handleExportJSON}
              className="text-gray-400 hover:text-pink-400 transition"
            >
              Export JSON
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}