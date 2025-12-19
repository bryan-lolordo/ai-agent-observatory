/**
 * Layer 2: Cost Analysis Operation Detail
 * 
 * Shows cost breakdown for a specific operation.
 * Prompt vs completion cost, cost driver analysis.
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { STORY_THEMES } from '../../../config/theme';
import { InlineLoading } from '../../../components/common/Loading';
import { formatNumber } from '../../../utils/formatters';

export default function CostOperationDetail() {
  const { agent, operation } = useParams();
  const navigate = useNavigate();
  const theme = STORY_THEMES.cost;

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
        `/api/stories/cost/operations/${encodeURIComponent(agent)}/${encodeURIComponent(operation)}`
      );
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      
      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Error fetching cost operation detail:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCallClick = (callId) => {
    navigate(`/stories/calls/${callId}?from=cost`);
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
            onClick={() => navigate('/stories/cost')}
            className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:${theme.textLight} transition`}
          >
            ← Back to Cost Analysis
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
    status = 'low',
    status_emoji = '🟢',
    status_label = 'Low',
    total_cost_formatted = '$0.00',
    avg_cost_formatted = '$0.000',
    call_count = 0,
    avg_prompt_formatted = '0',
    avg_completion_formatted = '0',
    cost_breakdown = [],
    cost_driver = null,
    savings = [],
    calls = [],
  } = data || {};

  // Badge colors based on status
  const badgeColors = {
    high: 'bg-red-600 border-red-400 text-white',
    medium: 'bg-yellow-600 border-yellow-400 text-white',
    low: 'bg-green-600 border-green-400 text-white',
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-7xl mx-auto p-8">
        
        {/* Back Button */}
        <button
          onClick={() => navigate('/stories/cost')}
          className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:${theme.textLight} transition`}
        >
          ← Back to Cost Analysis
        </button>

        {/* Page Header with Badge */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-2">
            <h1 className={`text-3xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-4xl">{theme.emoji}</span>
              {agent_name}.{operation_name}
            </h1>
            
            <div className={`px-3 py-1 rounded-full border-2 ${badgeColors[status]} text-sm font-semibold`}>
              {status_emoji} {status_label} Cost
            </div>
          </div>
          <p className="text-gray-400">
            Dashboard &gt; Cost Analysis &gt; {agent_name} &gt; {operation_name}
          </p>
          
          {/* Summary Stats */}
          <div className="mt-4 flex gap-6 text-sm">
            <span className="text-gray-400">
              Total: <span className={theme.text}>{total_cost_formatted}</span>
            </span>
            <span className="text-gray-400">
              Avg/Call: <span className="text-gray-300">{avg_cost_formatted}</span>
            </span>
            <span className="text-gray-400">
              Calls: <span className="text-gray-300">{call_count}</span>
            </span>
          </div>
        </div>

        {/* Cost Breakdown */}
        <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gray-900 p-6`}>
          <h3 className={`text-lg font-semibold ${theme.text} mb-6`}>
            💰 Cost Breakdown by Component
          </h3>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-2 text-gray-400">Component</th>
                  <th className="text-right py-2 text-gray-400">Avg Tokens</th>
                  <th className="text-right py-2 text-gray-400">Avg Cost</th>
                  <th className="text-right py-2 text-gray-400">% of Call</th>
                </tr>
              </thead>
              <tbody>
                {cost_breakdown.map((item, idx) => (
                  <tr key={idx} className="border-b border-gray-800">
                    <td className="py-3 text-gray-300">
                      {item.component}
                      {item.is_main_driver && (
                        <span className="ml-2 text-xs text-yellow-400">← Main Driver</span>
                      )}
                    </td>
                    <td className="py-3 text-right text-gray-400">{item.avg_tokens.toLocaleString()}</td>
                    <td className="py-3 text-right text-emerald-400">{item.avg_cost_formatted}</td>
                    <td className="py-3 text-right text-gray-300">{item.percentage}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Cost Driver Analysis */}
        {cost_driver && (
          <div className={`mb-8 rounded-lg border-2 ${cost_driver.emoji === '🔴' ? 'border-red-500 bg-red-900/20' : cost_driver.emoji === '🟡' ? 'border-yellow-500 bg-yellow-900/20' : `${theme.border} bg-gray-900`} p-6`}>
            <h3 className={`text-lg font-semibold ${cost_driver.emoji === '🔴' ? 'text-red-400' : cost_driver.emoji === '🟡' ? 'text-yellow-400' : theme.text} mb-2`}>
              {cost_driver.emoji} {cost_driver.title}
            </h3>
            <p className="text-gray-300">{cost_driver.description}</p>
          </div>
        )}

        {/* Savings Opportunities */}
        {savings.length > 0 && (
          <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gray-900 p-6`}>
            <h3 className={`text-lg font-semibold ${theme.text} mb-4`}>
              💡 Savings Opportunities
            </h3>
            
            <div className="space-y-4">
              {savings.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between p-4 bg-gray-800 rounded-lg">
                  <div>
                    <div className="font-semibold text-gray-200">{item.strategy}</div>
                    <div className="text-sm text-gray-400">{item.description}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-emerald-400 font-bold">{item.savings_formatted}</div>
                    <div className="text-xs text-gray-500">Impact: {item.impact} | Effort: {item.effort}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Calls Table */}
        <div className={`rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          <div className={`${theme.bgLight} p-4 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              📋 Calls (sorted by cost)
            </h3>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-800">
                <tr className={`border-b-2 ${theme.border}`}>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>#</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Prompt</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Completion</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Cost</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Latency</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Time</th>
                </tr>
              </thead>
              <tbody>
                {calls.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-gray-500">
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
                      <td className="py-3 px-4 text-right text-gray-300">{call.prompt_formatted}</td>
                      <td className="py-3 px-4 text-right text-gray-300">{call.completion_formatted}</td>
                      <td className="py-3 px-4 text-right text-emerald-400 font-semibold">{call.cost_formatted}</td>
                      <td className="py-3 px-4 text-right text-gray-400">{call.latency_formatted}</td>
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