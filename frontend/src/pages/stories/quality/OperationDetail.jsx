/**
 * Layer 2: Quality Operation Detail
 * 
 * Shows calls for a specific operation with quality scores and issues.
 * Matches Routing Layer 2 pattern - NO StoryNavTabs.
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { STORY_THEMES } from '../../../config/theme';
import { InlineLoading } from '../../../components/common/Loading';
import { formatNumber } from '../../../utils/formatters';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const QUICK_FILTERS = {
  ALL: 'all',
  ERRORS: 'errors',
  HALLUCINATIONS: 'hallucinations',
  LOW_QUALITY: 'low-quality',
  RECENT: 'recent',
};

export default function QualityOperationDetail() {
  const { agent, operation } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const theme = STORY_THEMES.quality;

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
        `/api/stories/quality/operations/${encodeURIComponent(agent)}/${encodeURIComponent(operation)}`
      );
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      
      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Error fetching quality operation detail:', err);
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
      case QUICK_FILTERS.ERRORS:
        filtered = filtered.filter(call => call.is_error);
        break;
      case QUICK_FILTERS.HALLUCINATIONS:
        filtered = filtered.filter(call => call.is_hallucination);
        break;
      case QUICK_FILTERS.LOW_QUALITY:
        filtered = filtered.filter(call => call.score !== null && call.score < 7);
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
    navigate(`/stories/calls/${callId}?from=quality`);
  };

  // Chart colors based on quality threshold
  const getBarColor = (bucket) => {
    if (bucket < 5) return '#ef4444';  // red - critical
    if (bucket < 7) return '#f97316';  // orange - low
    if (bucket < 8) return '#eab308';  // yellow - ok
    return '#22c55e';                   // green - good
  };

  // Quick filter button component
  const QuickFilterButton = ({ filter, icon, label, count }) => {
    const isActive = activeQuickFilter === filter;
    return (
      <button
        onClick={() => setActiveQuickFilter(filter)}
        className={`
          px-4 py-2 rounded-lg font-semibold text-sm transition-all
          ${isActive 
            ? `${theme.bg} text-white border-2 ${theme.border}` 
            : 'bg-gray-800 text-gray-400 border border-gray-700 hover:border-red-500'
          }
        `}
      >
        {icon} {label}
        {count !== undefined && count > 0 && (
          <span className="ml-1 text-xs">({count})</span>
        )}
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
            onClick={() => navigate('/stories/quality')}
            className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:${theme.textLight} transition`}
          >
            ← Back to Quality Monitoring
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
    avg_score = null,
    avg_score_formatted = '—',
    min_score_formatted = '—',
    max_score_formatted = '—',
    call_count = 0,
    evaluated_count = 0,
    error_count = 0,
    hallucination_count = 0,
    calls = [],
    quality_distribution = [],
  } = data || {};

  // Badge colors based on status
  const badgeColors = {
    good: 'bg-green-600 border-green-400 text-white',
    ok: 'bg-yellow-600 border-yellow-400 text-white',
    low: 'bg-orange-600 border-orange-400 text-white',
    critical: 'bg-red-600 border-red-400 text-white',
    unknown: 'bg-gray-600 border-gray-400 text-white',
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-7xl mx-auto p-8">
        
        {/* Back Button */}
        <button
          onClick={() => navigate('/stories/quality')}
          className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:${theme.textLight} transition`}
        >
          ← Back to Quality Monitoring
        </button>

        {/* Page Header with Badge */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-2">
            <h1 className={`text-3xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-4xl">{theme.emoji}</span>
              {agent_name}.{operation_name}
            </h1>
            
            {/* Quality Badge */}
            <div className={`px-3 py-1 rounded-full border-2 ${badgeColors[status]} text-sm font-semibold`}>
              {status_emoji} {status_label.toUpperCase()}
            </div>
          </div>
          <p className="text-gray-400">
            Dashboard &gt; Quality Monitoring &gt; {agent_name} &gt; {operation_name}
          </p>
          
          {/* Summary Stats */}
          <div className="mt-4 flex gap-6 text-sm">
            <span className="text-gray-400">
              Avg: <span className={theme.text}>{avg_score_formatted}</span>
            </span>
            <span className="text-gray-400">
              Min: <span className="text-gray-300">{min_score_formatted}</span>
            </span>
            <span className="text-gray-400">
              Errors: <span className={error_count > 0 ? 'text-red-400' : 'text-gray-300'}>
                {error_count}
              </span>
            </span>
            <span className="text-gray-400">
              Hallucinations: <span className={hallucination_count > 0 ? 'text-yellow-400' : 'text-gray-300'}>
                {hallucination_count}
              </span>
            </span>
            <span className="text-gray-400">
              Calls: <span className="text-gray-300">{call_count}</span>
            </span>
          </div>
        </div>

        {/* Main Content Card */}
        <div className={`rounded-lg border-2 ${theme.border} bg-gray-900 overflow-hidden mb-8`}>
          
          {/* Card Header */}
          <div className={`${theme.bgLight} p-6 border-b-2 ${theme.border}`}>
            <h3 className={`text-lg font-semibold ${theme.text}`}>
              📋 Calls for {agent_name}.{operation_name} ({call_count} total, {evaluated_count} evaluated)
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
                  filter={QUICK_FILTERS.ERRORS} 
                  icon="❌" 
                  label="Errors" 
                  count={error_count}
                />
                <QuickFilterButton 
                  filter={QUICK_FILTERS.HALLUCINATIONS} 
                  icon="⚠️" 
                  label="Hallucinations" 
                  count={hallucination_count}
                />
                <QuickFilterButton 
                  filter={QUICK_FILTERS.LOW_QUALITY} 
                  icon="🔴" 
                  label="Low Quality (<7)" 
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
                  className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 focus:border-red-500 focus:outline-none"
                />

                <button
                  onClick={() => {
                    setActiveQuickFilter(QUICK_FILTERS.ALL);
                    setSearchText('');
                  }}
                  className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-400 hover:text-red-400 hover:border-red-500 transition"
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
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Score</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Issues</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Time</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>ID</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Latency</th>
                  <th className={`text-right py-3 px-4 ${theme.textLight}`}>Cost</th>
                  <th className={`text-left py-3 px-4 ${theme.textLight}`}>Model</th>
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
                        <td className={`py-3 px-4 font-bold ${
                          call.score_status === 'good' ? 'text-green-400' :
                          call.score_status === 'ok' ? 'text-yellow-400' :
                          call.score_status === 'low' ? 'text-orange-400' :
                          call.score_status === 'critical' ? 'text-red-400' :
                          'text-gray-400'
                        }`}>
                          {call.score_formatted}
                        </td>
                        <td className="py-3 px-4">
                          {call.issues_display || (
                            <span className="text-gray-600">—</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-gray-400">
                          {call.timestamp_formatted}
                        </td>
                        <td className="py-3 px-4 font-mono text-xs text-gray-500">
                          {call.call_id?.substring(0, 8) || '—'}...
                        </td>
                        <td className="py-3 px-4 text-right text-gray-300">
                          {call.latency_formatted}
                        </td>
                        <td className="py-3 px-4 text-right text-gray-300">
                          {call.cost_formatted}
                        </td>
                        <td className="py-3 px-4 text-gray-400 text-xs">
                          {call.model_name}
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
            <button className="text-gray-400 hover:text-red-400 transition">
              Export CSV
            </button>
          </div>
        </div>

        {/* Quality Distribution Histogram */}
        {quality_distribution.length > 0 && (
          <div className={`rounded-lg border-2 ${theme.border} bg-gray-900 p-6`}>
            <h3 className={`text-lg font-semibold ${theme.text} mb-6`}>
              📊 Quality Distribution
            </h3>
            
            <ResponsiveContainer width="100%" height={200}>
              <BarChart 
                data={quality_distribution}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="label" 
                  stroke="#9ca3af"
                  tick={{ fill: '#9ca3af', fontSize: 11 }}
                  label={{ value: 'Quality Score', position: 'insideBottom', offset: -5, fill: '#9ca3af' }}
                />
                <YAxis 
                  stroke="#9ca3af"
                  tick={{ fill: '#9ca3af', fontSize: 11 }}
                  label={{ value: 'Count', angle: -90, position: 'insideLeft', fill: '#9ca3af' }}
                />
                <Tooltip 
                  contentStyle={{
                    backgroundColor: '#111827',
                    border: `2px solid ${theme.color}`,
                    borderRadius: '8px',
                    color: '#f3f4f6'
                  }}
                  formatter={(value, name) => [value, 'Calls']}
                  labelFormatter={(label) => `Score: ${label}`}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {quality_distribution.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={getBarColor(entry.bucket)}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            
            <p className="text-xs text-gray-400 mt-4 text-center">
              Red = Critical (&lt;5) • Orange = Low (5-7) • Yellow = OK (7-8) • Green = Good (&gt;8)
            </p>
          </div>
        )}

      </div>
    </div>
  );
}