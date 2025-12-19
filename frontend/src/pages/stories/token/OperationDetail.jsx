/**
 * Layer 2: Token Efficiency Operation Detail
 * 
 * Shows token breakdown for a specific operation.
 * Highlights where tokens are going (system, history, user message).
 * Matches other Layer 2 patterns - NO StoryNavTabs.
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { STORY_THEMES } from '../../../config/theme';
import { InlineLoading } from '../../../components/common/Loading';
import { formatNumber } from '../../../utils/formatters';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const QUICK_FILTERS = {
  ALL: 'all',
  HIGH_RATIO: 'high-ratio',
  RECENT: 'recent',
};

export default function TokenOperationDetail() {
  const { agent, operation } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const theme = STORY_THEMES.token_imbalance;

  // State
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeQuickFilter, setActiveQuickFilter] = useState(QUICK_FILTERS.ALL);
  const [searchText, setSearchText] = useState('');

  // Get initial filter from URL
  useEffect(() => {
    const filter = searchParams.get('filter');
    if (filter) {
      setActiveQuickFilter(filter);
    }
  }, [searchParams]);

  // Fetch data
  useEffect(() => {
    fetchData();
  }, [agent, operation]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(
        `/api/stories/token_imbalance/operations/${encodeURIComponent(agent)}/${encodeURIComponent(operation)}`
      );
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      
      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Error fetching token operation detail:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Apply filters
  const getFilteredCalls = () => {
    let filtered = [...(data?.calls || [])];

    // Apply quick filter
    switch (activeQuickFilter) {
      case QUICK_FILTERS.HIGH_RATIO:
        filtered = filtered.filter(call => call.ratio !== null && call.ratio >= 10);
        break;
      case QUICK_FILTERS.RECENT:
        // Last 24 hours
        const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
        filtered = filtered.filter(call => new Date(call.timestamp) > oneDayAgo);
        break;
      case QUICK_FILTERS.ALL:
      default:
        break;
    }

    // Apply search filter (search in call_id)
    if (searchText) {
      filtered = filtered.filter(call => 
        call.call_id?.toLowerCase().includes(searchText.toLowerCase())
      );
    }

    return filtered;
  };

  const filteredCalls = getFilteredCalls();

  // Navigation handlers
  const handleCallClick = (callId) => {
    navigate(`/stories/calls/${callId}?from=token_imbalance`);
  };

  // Get color for breakdown bar
  const getBreakdownColor = (component, status) => {
    if (status === 'warning') return '#ef4444';  // red
    
    switch (component) {
      case 'System Prompt': return '#8b5cf6';    // purple
      case 'Chat History': return '#f97316';     // orange
      case 'User Message': return '#22c55e';     // green
      case 'Context': return '#3b82f6';          // blue
      case 'Tool Definitions': return '#06b6d4'; // cyan
      default: return '#6b7280';                 // gray
    }
  };

  // Quick filter button component
  const QuickFilterButton = ({ filter, icon, label }) => {
    const isActive = activeQuickFilter === filter;
    return (
      <button
        onClick={() => setActiveQuickFilter(filter)}
        className={`
          px-4 py-2 rounded-lg font-semibold text-sm transition-all
          ${isActive 
            ? `${theme.bg} text-white border-2 ${theme.border}` 
            : 'bg-gray-800 text-gray-400 border border-gray-700 hover:border-yellow-500'
          }
        `}
      >
        {icon} {label}
      </button>
    );
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
            onClick={() => navigate('/stories/token_imbalance')}
            className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:${theme.textLight} transition`}
          >
            ← Back to Token Efficiency
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
    agent_name = agent,
    operation_name = operation,
    status = 'unknown',
    status_emoji = '⚪',
    status_label = 'Unknown',
    avg_prompt_tokens = 0,
    avg_prompt_formatted = '—',
    avg_completion_tokens = 0,
    avg_completion_formatted = '—',
    ratio = null,
    ratio_formatted = '—',
    total_cost_formatted = '$0.00',
    call_count = 0,
    token_breakdown = [],
    problems = [],
    calls = [],
  } = data || {};

  // Badge colors based on status
  const badgeColors = {
    balanced: 'bg-green-600 border-green-400 text-white',
    moderate: 'bg-yellow-600 border-yellow-400 text-white',
    high: 'bg-orange-600 border-orange-400 text-white',
    severe: 'bg-red-600 border-red-400 text-white',
    unknown: 'bg-gray-600 border-gray-400 text-white',
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-7xl mx-auto p-8">
        
        {/* Back Button */}
        <button
          onClick={() => navigate('/stories/token_imbalance')}
          className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:${theme.textLight} transition`}
        >
          ← Back to Token Efficiency
        </button>

        {/* Page Header with Badge */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-2">
            <h1 className={`text-3xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-4xl">{theme.emoji}</span>
              {agent_name}.{operation_name}
            </h1>
            
            {/* Ratio Badge */}
            <div className={`px-3 py-1 rounded-full border-2 ${badgeColors[status]} text-sm font-semibold`}>
              {status_emoji} {ratio_formatted} ({status_label})
            </div>
          </div>
          <p className="text-gray-400">
            Dashboard &gt; Token Efficiency &gt; {agent_name} &gt; {operation_name}
          </p>
          
          {/* Summary Stats */}
          <div className="mt-4 flex gap-6 text-sm">
            <span className="text-gray-400">
              Avg Prompt: <span className={theme.text}>{avg_prompt_formatted} tokens</span>
            </span>
            <span className="text-gray-400">
              Avg Completion: <span className="text-gray-300">{avg_completion_formatted} tokens</span>
            </span>
            <span className="text-gray-400">
              Total Cost: <span className="text-gray-300">{total_cost_formatted}</span>
            </span>
            <span className="text-gray-400">
              Calls: <span className="text-gray-300">{call_count}</span>
            </span>
          </div>
        </div>

        {/* Token Breakdown Visualization */}
        {token_breakdown.length > 0 && (
          <div className={`mb-8 rounded-lg border-2 ${theme.border} bg-gray-900 p-6`}>
            <h3 className={`text-lg font-semibold ${theme.text} mb-6`}>
              📊 Token Breakdown (where are prompt tokens going?)
            </h3>
            
            <div className="space-y-4">
              {token_breakdown.map((item, idx) => (
                <div key={idx} className="flex items-center gap-4">
                  <div className="w-36 text-sm text-gray-400">{item.component}</div>
                  <div className="flex-1 bg-gray-800 rounded-full h-8 overflow-hidden">
                    <div 
                      className="h-full rounded-full flex items-center px-3 text-sm font-semibold text-white transition-all"
                      style={{ 
                        width: `${Math.max(item.percentage, 5)}%`,
                        backgroundColor: getBreakdownColor(item.component, item.status)
                      }}
                    >
                      {item.percentage > 10 && `${item.tokens.toLocaleString()}`}
                    </div>
                  </div>
                  <div className="w-24 text-right text-sm">
                    <span className={item.status === 'warning' ? 'text-red-400 font-bold' : 'text-gray-400'}>
                      {item.percentage}%
                    </span>
                  </div>
                  <div className="w-24 text-right text-sm text-gray-500">
                    {item.tokens.toLocaleString()} tokens
                  </div>
                </div>
              ))}
              
              {/* Completion row */}
              <div className="flex items-center gap-4 pt-4 border-t border-gray-700">
                <div className="w-36 text-sm text-gray-400">→ Completion</div>
                <div className="flex-1 bg-gray-800 rounded-full h-8 overflow-hidden">
                  <div 
                    className="h-full rounded-full flex items-center px-3 text-sm font-semibold text-white bg-green-600"
                    style={{ 
                      width: `${Math.min(100, (avg_completion_tokens / avg_prompt_tokens) * 100)}%`,
                    }}
                  >
                    {avg_completion_tokens > 0 && avg_completion_formatted}
                  </div>
                </div>
                <div className="w-24 text-right text-sm text-green-400">
                  output
                </div>
                <div className="w-24 text-right text-sm text-gray-500">
                  {avg_completion_formatted} tokens
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Problem Detection */}
        {problems.length > 0 && (
          <div className={`mb-8 rounded-lg border-2 border-red-500 bg-red-900/20 p-6`}>
            <h3 className="text-lg font-semibold text-red-400 mb-4">
              ⚠️ Problems Detected
            </h3>
            <div className="space-y-4">
              {problems.map((problem, idx) => (
                <div key={idx} className="flex gap-3">
                  <span className="text-2xl">{problem.emoji}</span>
                  <div>
                    <div className="font-semibold text-red-300">{problem.title}</div>
                    <div className="text-sm text-gray-400">{problem.description}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Main Content Card - Calls Table */}
        <div className={`rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          
          {/* Card Header */}
          <div className={`${theme.bgLight} p-6 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              📋 Calls for {agent_name}.{operation_name} ({call_count} total)
            </h3>
          </div>

          {/* Filters Section */}
          <div className="p-6 space-y-4 border-b border-gray-800">
            
            {/* Quick Filters */}
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-2">
                QUICK FILTERS:
              </label>
              <div className="flex flex-wrap gap-2">
                <QuickFilterButton 
                  filter={QUICK_FILTERS.ALL} 
                  icon="🎯" 
                  label="All Calls" 
                />
                <QuickFilterButton 
                  filter={QUICK_FILTERS.HIGH_RATIO} 
                  icon="🔴" 
                  label="High Ratio (≥10:1)" 
                />
                <QuickFilterButton 
                  filter={QUICK_FILTERS.RECENT} 
                  icon="⏱️" 
                  label="Recent 24h" 
                />
              </div>
            </div>

            {/* Advanced Filters */}
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-2">
                ADVANCED FILTERS:
              </label>
              <div className="flex flex-wrap gap-3">
                <input
                  type="text"
                  placeholder="🔍 Search by call ID..."
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 focus:border-yellow-500 focus:outline-none"
                />

                <button
                  onClick={() => {
                    setActiveQuickFilter(QUICK_FILTERS.ALL);
                    setSearchText('');
                  }}
                  className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-400 hover:text-yellow-400 hover:border-yellow-500 transition"
                >
                  Clear All
                </button>
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-800 sticky top-0">
                <tr className={`border-b-2 ${theme.border}`}>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>#</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Prompt</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>History</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Completion</th>
                  <th className={`text-center py-3 px-4 ${theme.textLight}`}>Ratio</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Cost</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Time</th>
                </tr>
              </thead>
              <tbody>
                {filteredCalls.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="py-8 text-center text-gray-500">
                      No calls match the current filters
                    </td>
                  </tr>
                ) : (
                  filteredCalls.map((call, idx) => {
                    return (
                      <tr
                        key={call.call_id || idx}
                        onClick={() => handleCallClick(call.call_id)}
                        className={`border-b border-gray-800 cursor-pointer transition-all hover:bg-gradient-to-r hover:${theme.gradient} hover:border-l-4 hover:${theme.border}`}
                      >
                        <td className="py-3 px-4 text-gray-500">
                          {call.index}
                        </td>
                        <td className="py-3 px-4 text-right text-gray-300">
                          {call.prompt_formatted}
                        </td>
                        <td className="py-3 px-4 text-right text-orange-400">
                          {call.history_formatted}
                        </td>
                        <td className="py-3 px-4 text-right text-gray-300">
                          {call.completion_formatted}
                        </td>
                        <td className={`py-3 px-4 text-center font-bold ${
                          call.ratio_status === 'severe' ? 'text-red-400' :
                          call.ratio_status === 'high' ? 'text-orange-400' :
                          call.ratio_status === 'moderate' ? 'text-yellow-400' :
                          'text-green-400'
                        }`}>
                          {call.ratio_formatted}
                        </td>
                        <td className="py-3 px-4 text-right text-gray-300">
                          {call.cost_formatted}
                        </td>
                        <td className="py-3 px-4 text-gray-400">
                          {call.timestamp_formatted}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Footer */}
          <div className="p-4 bg-gray-800 border-t border-gray-700 flex justify-between items-center text-sm text-gray-400">
            <span>
              Showing {filteredCalls.length} of {calls.length} calls
              {filteredCalls.length !== calls.length && (
                <span className={theme.text}> (filtered)</span>
              )}
            </span>
            <button className="text-gray-400 hover:text-yellow-400 transition">
              Export CSV
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}