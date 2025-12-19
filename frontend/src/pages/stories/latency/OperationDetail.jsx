/**
 * Layer 2: Operation Detail - Latency Analysis
 * 
 * Shows all calls for a specific operation with quick filters and
 * advanced filtering options.
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { STORY_THEMES } from '../../../config/theme';
import { InlineLoading } from '../../../components/common/Loading';
import { formatLatency, formatCurrency } from '../../../utils/formatters';

const QUICK_FILTERS = {
  ALL: 'all',
  MAX: 'max',
  SLOW: 'slow',
  CRITICAL: 'critical',
  RECENT: 'recent',
  OUTLIERS: 'outliers',
  ERRORS: 'errors',
  TOP_OFFENDER: 'top-offender',
};

export default function LatencyOperationDetail() {
  const { agent, operation } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const theme = STORY_THEMES.latency;

  // State
  const [calls, setCalls] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeQuickFilter, setActiveQuickFilter] = useState(QUICK_FILTERS.ALL);
  const [searchText, setSearchText] = useState('');
  const [dateFilter, setDateFilter] = useState('7d');
  const [modelFilter, setModelFilter] = useState('all');

  // Get initial filter from URL
  useEffect(() => {
    const filter = searchParams.get('filter');
    if (filter) {
      setActiveQuickFilter(filter);
    }
  }, [searchParams]);

  // Fetch data - use both agent and operation
  useEffect(() => {
    fetchOperationCalls();
  }, [agent, operation]);

  const fetchOperationCalls = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Use composite URL: /api/stories/latency/operations/{agent}/{operation}
      const response = await fetch(
        `/api/stories/latency/operations/${encodeURIComponent(agent)}/${encodeURIComponent(operation)}`
      );
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      
      const data = await response.json();
      setCalls(data.calls || []);
      setSummary(data.summary || null);
    } catch (err) {
      console.error('Error fetching operation calls:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Apply quick filters
  const getFilteredCalls = () => {
    let filtered = [...calls];

    // Apply quick filter
    switch (activeQuickFilter) {
      case QUICK_FILTERS.MAX:
        // Show only the call with max latency
        const maxCall = filtered.reduce((max, call) => 
          call.latency_ms > max.latency_ms ? call : max, filtered[0]);
        filtered = maxCall ? [maxCall] : [];
        break;

      case QUICK_FILTERS.SLOW:
        // Calls > 5s
        filtered = filtered.filter(call => call.latency_ms > 5000);
        break;

      case QUICK_FILTERS.CRITICAL:
        // Calls > 10s
        filtered = filtered.filter(call => call.latency_ms > 10000);
        break;

      case QUICK_FILTERS.RECENT:
        // Last 24 hours
        const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
        filtered = filtered.filter(call => new Date(call.timestamp) > oneDayAgo);
        break;

      case QUICK_FILTERS.OUTLIERS:
        // Statistical outliers (> avg + 2*stddev)
        if (filtered.length > 0) {
          const avg = filtered.reduce((sum, c) => sum + c.latency_ms, 0) / filtered.length;
          const variance = filtered.reduce((sum, c) => sum + Math.pow(c.latency_ms - avg, 2), 0) / filtered.length;
          const stddev = Math.sqrt(variance);
          const threshold = avg + 2 * stddev;
          filtered = filtered.filter(call => call.latency_ms > threshold);
        }
        break;

      case QUICK_FILTERS.ERRORS:
        // Only failed calls
        filtered = filtered.filter(call => call.error);
        break;

      case QUICK_FILTERS.TOP_OFFENDER:
      case QUICK_FILTERS.ALL:
      default:
        // Show all calls (already filtered by operation)
        break;
    }

    // Apply advanced filters
    if (searchText) {
      filtered = filtered.filter(call => 
        call.prompt_preview?.toLowerCase().includes(searchText.toLowerCase())
      );
    }

    if (modelFilter !== 'all') {
      filtered = filtered.filter(call => call.model_name === modelFilter);
    }

    if (dateFilter !== '7d') {
      const daysAgo = parseInt(dateFilter.replace('d', ''));
      const cutoff = new Date(Date.now() - daysAgo * 24 * 60 * 60 * 1000);
      filtered = filtered.filter(call => new Date(call.timestamp) > cutoff);
    }

    return filtered;
  };

  const filteredCalls = getFilteredCalls();

  // Get unique models for filter dropdown
  const uniqueModels = [...new Set(calls.map(c => c.model_name))].filter(Boolean);

  // Handle call click (navigate to Layer 3)
  const handleCallClick = (callId) => {
    navigate(`/stories/calls/${callId}?from=latency`);
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
            ? `${theme.bg} ${theme.text} border-2 ${theme.border}` 
            : 'bg-gray-800 text-gray-400 border border-gray-700 hover:border-orange-500'
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
            onClick={() => navigate('/stories/latency')}
            className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:${theme.textLight} transition`}
          >
            ← Back to Latency Analysis
          </button>
          <div className="bg-red-900/20 border border-red-500 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-400 mb-2">Error Loading Data</h2>
            <p className="text-gray-300">{error}</p>
            <button
              onClick={fetchOperationCalls}
              className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-7xl mx-auto p-8">
        
        {/* Back Button */}
        <button
          onClick={() => navigate('/stories/latency')}
          className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:${theme.textLight} transition`}
        >
          ← Back to Latency Analysis
        </button>

        {/* Page Header */}
        <div className="mb-8">
          <h1 className={`text-4xl font-bold ${theme.text} mb-2 flex items-center gap-3`}>
            <span className="text-5xl">{theme.emoji}</span>
            {agent}.{operation}
          </h1>
          <p className="text-gray-400">
            Dashboard &gt; Latency Analysis &gt; {agent} &gt; {operation}
          </p>
          
          {/* Summary Stats */}
          {summary && (
            <div className="mt-4 flex gap-6 text-sm">
              <span className="text-gray-400">
                Avg: <span className={theme.text}>{(summary.avg_latency_ms / 1000).toFixed(2)}s</span>
              </span>
              <span className="text-gray-400">
                Max: <span className="text-red-400">{(summary.max_latency_ms / 1000).toFixed(2)}s</span>
              </span>
              <span className="text-gray-400">
                Min: <span className="text-green-400">{(summary.min_latency_ms / 1000).toFixed(2)}s</span>
              </span>
              <span className="text-gray-400">
                Cost: <span className={theme.text}>${summary.total_cost?.toFixed(4)}</span>
              </span>
              <span className="text-gray-400">
                Errors: <span className={summary.error_count > 0 ? 'text-red-400' : 'text-green-400'}>
                  {summary.error_count} ({summary.error_rate}%)
                </span>
              </span>
            </div>
          )}
        </div>

        {/* Main Content Card */}
        <div className={`rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden`}>
          
          {/* Card Header */}
          <div className={`${theme.bgLight} p-6 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              📊 Calls for {agent}.{operation} ({calls.length} total)
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
                <QuickFilterButton filter={QUICK_FILTERS.ALL} icon="🎯" label="All Calls" />
                <QuickFilterButton filter={QUICK_FILTERS.MAX} icon="🔴" label="Max Latency" />
                <QuickFilterButton filter={QUICK_FILTERS.SLOW} icon="🐌" label="Slow >5s" />
                <QuickFilterButton filter={QUICK_FILTERS.CRITICAL} icon="⚡" label="Critical >10s" />
                <QuickFilterButton filter={QUICK_FILTERS.RECENT} icon="⏱️" label="Recent 24h" />
                <QuickFilterButton filter={QUICK_FILTERS.OUTLIERS} icon="📊" label="Outliers" />
                <QuickFilterButton filter={QUICK_FILTERS.ERRORS} icon="❌" label="Errors" />
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
                  placeholder="🔍 Search prompt..."
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 focus:border-orange-500 focus:outline-none"
                />
                
                <select
                  value={dateFilter}
                  onChange={(e) => setDateFilter(e.target.value)}
                  className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 focus:border-orange-500 focus:outline-none"
                >
                  <option value="1d">Last 24 hours</option>
                  <option value="7d">Last 7 days</option>
                  <option value="30d">Last 30 days</option>
                </select>

                {uniqueModels.length > 1 && (
                  <select
                    value={modelFilter}
                    onChange={(e) => setModelFilter(e.target.value)}
                    className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 focus:border-orange-500 focus:outline-none"
                  >
                    <option value="all">All Models</option>
                    {uniqueModels.map(model => (
                      <option key={model} value={model}>{model}</option>
                    ))}
                  </select>
                )}

                <button
                  onClick={() => {
                    setActiveQuickFilter(QUICK_FILTERS.ALL);
                    setSearchText('');
                    setDateFilter('7d');
                    setModelFilter('all');
                  }}
                  className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-400 hover:text-orange-400 hover:border-orange-500 transition"
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
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Time</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>ID</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Latency</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Prompt</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Complete</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Total</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Cost</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Preview</th>
                </tr>
              </thead>
              <tbody>
                {filteredCalls.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="py-8 text-center text-gray-500">
                      No calls match the current filters
                    </td>
                  </tr>
                ) : (
                  filteredCalls.map((call, idx) => {
                    const isSlow = call.latency_ms > 5000;
                    const isCritical = call.latency_ms > 10000;
                    
                    return (
                      <tr
                        key={idx}
                        onClick={() => handleCallClick(call.call_id)}
                        className={`border-b border-gray-800 cursor-pointer transition-all hover:bg-gradient-to-r hover:${theme.gradient} hover:border-l-4 hover:${theme.border}`}
                      >
                        <td className="py-3 px-4 text-gray-400">
                          {new Date(call.timestamp).toLocaleTimeString('en-US', { 
                            hour: 'numeric', 
                            minute: '2-digit',
                            hour12: true 
                          })}
                        </td>
                        <td className="py-3 px-4 font-mono text-xs text-gray-500">
                          {call.call_id?.substring(0, 8) || '—'}
                        </td>
                        <td className={`py-3 px-4 text-right font-bold ${isCritical ? 'text-red-400' : isSlow ? 'text-yellow-400' : theme.text}`}>
                          {formatLatency(call.latency_ms)}
                        </td>
                        <td className="py-3 px-4 text-right text-gray-300">
                          {call.prompt_tokens?.toLocaleString() || '—'}
                        </td>
                        <td className="py-3 px-4 text-right text-gray-300">
                          {call.completion_tokens?.toLocaleString() || '—'}
                        </td>
                        <td className="py-3 px-4 text-right text-gray-300">
                          {call.total_tokens?.toLocaleString() || '—'}
                        </td>
                        <td className="py-3 px-4 text-right text-gray-300">
                          {formatCurrency(call.total_cost)}
                        </td>
                        <td className="py-3 px-4 text-gray-400 max-w-xs truncate">
                          {call.prompt_preview || '—'}
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
            <button className="text-gray-400 hover:text-orange-400 transition">
              Export CSV
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}