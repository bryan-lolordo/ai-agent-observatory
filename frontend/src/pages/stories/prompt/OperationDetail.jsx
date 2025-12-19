/**
 * Layer 2: Prompt Composition Operation Detail
 * 
 * Shows prompt structure analysis for a specific operation.
 * Cache readiness diagnosis and restructuring suggestions.
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { STORY_THEMES } from '../../../config/theme';
import { InlineLoading } from '../../../components/common/Loading';

export default function PromptOperationDetail() {
  const { agent, operation } = useParams();
  const navigate = useNavigate();
  const theme = STORY_THEMES.system_prompt;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchData();
  }, [agent, operation]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(
        `/api/stories/system_prompt/operations/${encodeURIComponent(agent)}/${encodeURIComponent(operation)}`
      );
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      
      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Error fetching prompt operation detail:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCallClick = (callId) => {
    navigate(`/stories/calls/${callId}?from=system_prompt`);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 p-8 flex items-center justify-center">
        <InlineLoading text="Loading operation details..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 p-8">
        <div className="max-w-7xl mx-auto">
          <button
            onClick={() => navigate('/stories/system_prompt')}
            className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:${theme.textLight} transition`}
          >
            ← Back to Prompt Composition
          </button>
          <div className="bg-red-900/20 border border-red-500 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-400 mb-2">Error Loading Data</h2>
            <p className="text-gray-300">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  const {
    agent_name = agent,
    operation_name = operation,
    cache_status = 'unknown',
    cache_emoji = '⚪',
    cache_label = 'Unknown',
    cache_issue_reason = null,
    avg_system_formatted = '—',
    avg_user_formatted = '—',
    avg_history_formatted = '—',
    total_prompt_formatted = '—',
    system_pct = 0,
    user_pct = 0,
    history_pct = 0,
    system_variability = 0,
    system_variability_label = 'Low',
    composition = [],
    calls = [],
    call_count = 0,
  } = data || {};

  // Badge colors based on cache status
  const badgeColors = {
    ready: 'bg-green-600 border-green-400 text-white',
    partial: 'bg-yellow-600 border-yellow-400 text-white',
    not_ready: 'bg-red-600 border-red-400 text-white',
    none: 'bg-gray-600 border-gray-400 text-white',
    unknown: 'bg-gray-600 border-gray-400 text-white',
  };

  // Bar colors for composition
  const getBarColor = (component) => {
    if (component === 'System Prompt') return '#8b5cf6';
    if (component === 'User Message') return '#22c55e';
    if (component === 'Chat History') return '#f97316';
    return '#6b7280';
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-7xl mx-auto p-8">
        
        {/* Back Button */}
        <button
          onClick={() => navigate('/stories/system_prompt')}
          className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:${theme.textLight} transition`}
        >
          ← Back to Prompt Composition
        </button>

        {/* Page Header with Badge */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-2">
            <h1 className={`text-3xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-4xl">{theme.emoji}</span>
              {agent_name}.{operation_name}
            </h1>
            
            <div className={`px-3 py-1 rounded-full border-2 ${badgeColors[cache_status]} text-sm font-semibold`}>
              {cache_emoji} {cache_label}
            </div>
          </div>
          <p className="text-gray-400">
            Dashboard &gt; Prompt Composition &gt; {agent_name} &gt; {operation_name}
          </p>
          
          {/* Summary Stats */}
          <div className="mt-4 flex gap-6 text-sm">
            <span className="text-gray-400">
              Total Prompt: <span className={theme.text}>{total_prompt_formatted} tokens</span>
            </span>
            <span className="text-gray-400">
              Variability: <span className={system_variability > 20 ? 'text-red-400' : 'text-green-400'}>
                {system_variability}% ({system_variability_label})
              </span>
            </span>
            <span className="text-gray-400">
              Calls: <span className="text-gray-300">{call_count}</span>
            </span>
          </div>
        </div>

        {/* Cache Status Card */}
        {cache_issue_reason && (
          <div className={`mb-8 rounded-lg border-2 ${cache_status === 'not_ready' ? 'border-red-500 bg-red-900/20' : 'border-yellow-500 bg-yellow-900/20'} p-6`}>
            <h3 className={`text-lg font-semibold ${cache_status === 'not_ready' ? 'text-red-400' : 'text-yellow-400'} mb-2`}>
              {cache_emoji} Cache Status: {cache_label}
            </h3>
            <p className="text-gray-300">{cache_issue_reason}</p>
            {cache_status === 'not_ready' && (
              <p className="text-sm text-gray-400 mt-2">
                💡 Impact: Cannot use prompt caching (90% cost reduction unavailable)
              </p>
            )}
          </div>
        )}

        {/* Composition Breakdown */}
        <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gray-900 p-6`}>
          <h3 className={`text-lg font-semibold ${theme.text} mb-6`}>
            📊 Prompt Structure
          </h3>
          
          <div className="space-y-4">
            {composition.map((item, idx) => (
              <div key={idx} className="flex items-center gap-4">
                <div className="w-32 text-sm text-gray-400">{item.component}</div>
                <div className="flex-1 bg-gray-800 rounded-full h-8 overflow-hidden">
                  <div 
                    className="h-full rounded-full flex items-center px-3 text-sm font-semibold text-white transition-all"
                    style={{ 
                      width: `${Math.max(item.percentage, 5)}%`,
                      backgroundColor: getBarColor(item.component)
                    }}
                  >
                    {item.percentage > 10 && `${item.tokens.toLocaleString()}`}
                  </div>
                </div>
                <div className="w-20 text-right text-sm text-gray-400">
                  {item.percentage}%
                </div>
                <div className="w-24 text-right text-sm">
                  <span className={item.status === 'warning' ? 'text-yellow-400' : 'text-green-400'}>
                    {item.status_label}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Sample Calls */}
        <div className={`rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          <div className={`${theme.bgLight} p-4 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              📋 Sample Calls ({calls.length} of {call_count})
            </h3>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-800">
                <tr className={`border-b-2 ${theme.border}`}>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>#</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>System</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>User</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>History</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Time</th>
                </tr>
              </thead>
              <tbody>
                {calls.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-gray-500">
                      No calls available
                    </td>
                  </tr>
                ) : (
                  calls.map((call, idx) => (
                    <tr
                      key={call.call_id || idx}
                      onClick={() => handleCallClick(call.call_id)}
                      className={`border-b border-gray-800 cursor-pointer transition-all hover:bg-gradient-to-r hover:${theme.gradient} hover:border-l-4 hover:${theme.border}`}
                    >
                      <td className="py-3 px-4 text-gray-500">{call.index}</td>
                      <td className="py-3 px-4 text-right text-purple-400">{call.system_formatted}</td>
                      <td className="py-3 px-4 text-right text-green-400">{call.user_formatted}</td>
                      <td className="py-3 px-4 text-right text-orange-400">{call.history_formatted}</td>
                      <td className="py-3 px-4 text-gray-400">{call.timestamp_formatted}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </div>
  );
}