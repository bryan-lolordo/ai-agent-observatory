/**
 * Layer 2: Routing Patterns (Pattern-Based View)
 * 
 * Shows operation+model combinations with routing opportunities.
 * Similar to Cache Layer 2 pattern-based approach.
 * 
 * Location: src/pages/stories/routing/OperationDetail.jsx
 */

import { useState, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { formatNumber, formatCurrency } from '../../../utils/formatters';
import { useRoutingPatterns } from '../../../hooks/useCalls';

const STORY_ID = 'routing';
const theme = STORY_THEMES.routing;

// Quick filter options
const QUICK_FILTERS = [
  { id: 'all', label: 'All Types', color: 'bg-purple-500' },
  { id: 'downgrade', label: '↓ Downgrade', color: 'bg-blue-500' },
  { id: 'upgrade', label: '↑ Upgrade', color: 'bg-red-500' },
  { id: 'keep', label: '✓ Keep', color: 'bg-green-500' },
  { id: 'risky', label: '⚠️ Risky', color: 'bg-yellow-500' },
];

export default function RoutingOperationDetail() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // Fetch patterns with automatic timeRange handling
  const { data: patterns, loading, error, refetch, rawResponse } = useRoutingPatterns();
  
  // Get stats from rawResponse
  const stats = rawResponse?.stats || null;
  
  // Get initial filter from URL
  const initialFilter = searchParams.get('filter') || 'all';
  
  // UI State
  const [activeFilter, setActiveFilter] = useState(initialFilter);
  const [sortBy, setSortBy] = useState('savable');
  const [sortOrder, setSortOrder] = useState('desc');
  
  // Get initial filters from URL params (like Cache)
  const initialAgent = searchParams.get('agent');
  const initialOperation = searchParams.get('operation');

  // Column filters - initialize from URL params
  const [agentFilter, setAgentFilter] = useState(initialAgent ? [initialAgent] : []);
  const [operationFilter, setOperationFilter] = useState(initialOperation ? [initialOperation] : []);
  const [modelFilter, setModelFilter] = useState([]);

  // Get unique values for filters
  const filterOptions = useMemo(() => {
    const agents = [...new Set((patterns || []).map(p => p.agent_name))].sort();
    const operations = [...new Set((patterns || []).map(p => p.operation))].sort();
    const models = [...new Set((patterns || []).map(p => p.model))].sort();
    return { agents, operations, models };
  }, [patterns]);

  // Filter and sort patterns
  const filteredPatterns = useMemo(() => {
    let result = patterns || [];
    
    // Quick filter
    if (activeFilter !== 'all') {
      if (activeFilter === 'risky') {
        result = result.filter(p => p.safe_pct < 80);
      } else {
        result = result.filter(p => p.type === activeFilter);
      }
    }
    
    // Column filters
    if (agentFilter.length > 0) {
      result = result.filter(p => agentFilter.includes(p.agent_name));
    }
    if (operationFilter.length > 0) {
      result = result.filter(p => operationFilter.includes(p.operation));
    }
    if (modelFilter.length > 0) {
      result = result.filter(p => modelFilter.includes(p.model));
    }
    
    // Sort
    result = [...result].sort((a, b) => {
      let aVal, bVal;
      
      switch (sortBy) {
        case 'savable':
          aVal = Math.abs(a.savable || 0);
          bVal = Math.abs(b.savable || 0);
          break;
        case 'calls':
          aVal = a.call_count || 0;
          bVal = b.call_count || 0;
          break;
        case 'quality':
          aVal = a.avg_quality || 0;
          bVal = b.avg_quality || 0;
          break;
        case 'complexity':
          aVal = a.complexity_avg || 0;
          bVal = b.complexity_avg || 0;
          break;
        default:
          aVal = a.savable || 0;
          bVal = b.savable || 0;
      }
      
      return sortOrder === 'desc' ? bVal - aVal : aVal - bVal;
    });
    
    return result;
  }, [patterns, activeFilter, agentFilter, operationFilter, modelFilter, sortBy, sortOrder]);

  // Handlers
  const handleBack = () => {
    navigate('/stories/routing');
  };

  const handleRowClick = (pattern) => {
    navigate(`/stories/routing/calls/${pattern.sample_call_id}`);
  };

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  const clearFilters = () => {
    setAgentFilter([]);
    setOperationFilter([]);
    setModelFilter([]);
    setActiveFilter('all');
  };

  // Helper functions
  const getTypeColor = (type) => {
    if (type === 'downgrade') return 'text-blue-400';
    if (type === 'upgrade') return 'text-red-400';
    return 'text-green-400';
  };

  const getTypeBg = (type) => {
    if (type === 'downgrade') return 'bg-blue-500/20 border-blue-500/30';
    if (type === 'upgrade') return 'bg-red-500/20 border-red-500/30';
    return 'bg-green-500/20 border-green-500/30';
  };

  const getQualityColor = (status) => {
    if (status === 'good') return 'text-green-400';
    if (status === 'ok') return 'text-yellow-400';
    return 'text-red-400';
  };

  const getComplexityColor = (label) => {
    if (label === 'Low') return 'text-green-400';
    if (label === 'Medium') return 'text-yellow-400';
    return 'text-red-400';
  };

  const getSafePctColor = (pct) => {
    if (pct >= 90) return 'text-green-400';
    if (pct >= 70) return 'text-yellow-400';
    return 'text-red-400';
  };

  // Loading state
  if (loading) return <StoryPageSkeleton />;

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 p-8">
        <div className="max-w-7xl mx-auto">
          <button
            onClick={handleBack}
            className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:underline`}
          >
            ← Back to Model Routing Overview
          </button>
          <div className="bg-red-900/20 border border-red-500 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-400 mb-2">Error Loading Data</h2>
            <p className="text-gray-300">{error}</p>
            <button
              onClick={refetch}
              className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const hasActiveFilters = agentFilter.length > 0 || operationFilter.length > 0 || modelFilter.length > 0;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Story Navigation */}
      <StoryNavTabs activeStory={STORY_ID} />

      <div className="max-w-7xl mx-auto p-6">
        
        {/* Back Button */}
        <button
          onClick={handleBack}
          className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:underline`}
        >
          ← Back to Model Routing Overview
        </button>

        {/* Page Header */}
        <div className="mb-6">
          <h1 className={`text-3xl font-bold ${theme.text} flex items-center gap-3 mb-2`}>
            <span className="text-4xl">{theme.emoji}</span>
            Routing Opportunities
            <span className="text-lg font-normal text-gray-400">• All Patterns</span>
          </h1>
          <p className="text-gray-500 text-sm">
            Dashboard › Model Routing › All Patterns
          </p>
        </div>

        {/* Stat Badges */}
        {stats && (
          <div className="mb-6 flex flex-wrap gap-3">
            <StatBadge label="Patterns" value={formatNumber(stats.total_patterns)} theme={theme} />
            <StatBadge label="Total Savable" value={stats.total_savable_formatted || '$0.00'} color="text-green-400" />
            <StatBadge label="↓ Downgrade" value={stats.downgrade_count} color="text-blue-400" />
            <StatBadge label="↑ Upgrade" value={stats.upgrade_count} color="text-red-400" />
            <StatBadge label="✓ Keep" value={stats.keep_count} color="text-green-400" />
          </div>
        )}

        {/* Filters Section */}
        <div className="mb-6 p-4 bg-gray-900/50 rounded-lg border border-gray-800">
          {/* Quick Filters */}
          <div className="flex items-center gap-4 mb-4">
            <span className="text-xs text-gray-500 uppercase tracking-wide">Quick Filters</span>
            <div className="flex gap-2">
              {QUICK_FILTERS.map(filter => (
                <button
                  key={filter.id}
                  onClick={() => setActiveFilter(filter.id)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                    activeFilter === filter.id
                      ? `${filter.color} text-white`
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  {filter.label}
                </button>
              ))}
              {(activeFilter !== 'all' || hasActiveFilters) && (
                <button
                  onClick={clearFilters}
                  className="px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 text-sm hover:bg-gray-700"
                >
                  Clear All
                </button>
              )}
            </div>
          </div>
          
          {/* Column Filters */}
          <div className="flex items-center gap-4">
            <span className="text-xs text-gray-500 uppercase tracking-wide">Filters</span>
            <div className="flex gap-2">
              <FilterDropdown
                label="Agent"
                icon="🏠"
                options={filterOptions.agents}
                selected={agentFilter}
                onChange={setAgentFilter}
              />
              <FilterDropdown
                label="Operation"
                icon="⚙️"
                options={filterOptions.operations}
                selected={operationFilter}
                onChange={setOperationFilter}
              />
              <FilterDropdown
                label="Model"
                icon="🤖"
                options={filterOptions.models}
                selected={modelFilter}
                onChange={setModelFilter}
              />
              {hasActiveFilters && (
                <button
                  onClick={() => {
                    setAgentFilter([]);
                    setOperationFilter([]);
                    setModelFilter([]);
                  }}
                  className="px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 text-sm hover:bg-gray-700"
                >
                  Clear
                </button>
              )}
            </div>
          </div>
          
          {/* Active Filters Display */}
          {hasActiveFilters && (
            <div className="flex items-center gap-2 mt-3">
              <span className="text-xs text-gray-500">Active:</span>
              {agentFilter.map(f => (
                <FilterTag key={`agent-${f}`} label={`Agent: ${f}`} onRemove={() => setAgentFilter(agentFilter.filter(x => x !== f))} />
              ))}
              {operationFilter.map(f => (
                <FilterTag key={`op-${f}`} label={`Operation: ${f}`} onRemove={() => setOperationFilter(operationFilter.filter(x => x !== f))} />
              ))}
              {modelFilter.map(f => (
                <FilterTag key={`model-${f}`} label={`Model: ${f}`} onRemove={() => setModelFilter(modelFilter.filter(x => x !== f))} />
              ))}
            </div>
          )}
        </div>

        {/* Patterns Table */}
        <div className="rounded-lg border border-gray-700 bg-gray-900 overflow-hidden">
          <div className={`h-1 ${theme.bg}`} />
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-800/50">
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-gray-400 font-medium"># Type</th>
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Agent</th>
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Operation</th>
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Model</th>
                  <th 
                    className="text-center py-3 px-4 text-gray-400 font-medium cursor-pointer hover:text-white"
                    onClick={() => handleSort('complexity')}
                  >
                    <span className="flex items-center justify-center gap-1">
                      Complexity
                      {sortBy === 'complexity' && <span className="text-purple-400">{sortOrder === 'desc' ? '↓' : '↑'}</span>}
                    </span>
                  </th>
                  <th 
                    className="text-center py-3 px-4 text-gray-400 font-medium cursor-pointer hover:text-white"
                    onClick={() => handleSort('quality')}
                  >
                    <span className="flex items-center justify-center gap-1">
                      Quality
                      {sortBy === 'quality' && <span className="text-purple-400">{sortOrder === 'desc' ? '↓' : '↑'}</span>}
                    </span>
                  </th>
                  <th 
                    className="text-right py-3 px-4 text-gray-400 font-medium cursor-pointer hover:text-white"
                    onClick={() => handleSort('calls')}
                  >
                    <span className="flex items-center justify-end gap-1">
                      Calls
                      {sortBy === 'calls' && <span className="text-purple-400">{sortOrder === 'desc' ? '↓' : '↑'}</span>}
                    </span>
                  </th>
                  <th 
                    className="text-right py-3 px-4 text-gray-400 font-medium cursor-pointer hover:text-white"
                    onClick={() => handleSort('savable')}
                  >
                    <span className="flex items-center justify-end gap-1">
                      Savable
                      {sortBy === 'savable' && <span className="text-purple-400">{sortOrder === 'desc' ? '↓' : '↑'}</span>}
                    </span>
                  </th>
                  <th className="text-center py-3 px-4 text-gray-400 font-medium">Safe %</th>
                </tr>
              </thead>
              <tbody>
                {filteredPatterns.length > 0 ? (
                  filteredPatterns.map((pattern) => (
                    <tr
                      key={pattern.id}
                      onClick={() => handleRowClick(pattern)}
                      className="border-b border-gray-800 cursor-pointer hover:bg-purple-500/10 transition-colors"
                    >
                      {/* Type */}
                      <td className="py-4 px-4">
                        <div className={`inline-flex items-center gap-2 px-2 py-1 rounded border ${getTypeBg(pattern.type)}`}>
                          <span className={`text-lg ${getTypeColor(pattern.type)}`}>{pattern.type_emoji}</span>
                          <span className={`text-sm font-medium ${getTypeColor(pattern.type)}`}>{pattern.type_label}</span>
                        </div>
                      </td>
                      
                      {/* Agent */}
                      <td className="py-4 px-4 font-semibold text-purple-400">
                        {pattern.agent_name}
                      </td>
                      
                      {/* Operation */}
                      <td className={`py-4 px-4 font-mono ${theme.text}`}>
                        {pattern.operation}
                      </td>
                      
                      {/* Model */}
                      <td className="py-4 px-4">
                        <div className="text-gray-300">{pattern.model}</div>
                        {pattern.suggested_model && (
                          <div className="text-xs text-gray-500 mt-0.5">
                            → {pattern.suggested_model}
                          </div>
                        )}
                      </td>
                      
                      {/* Complexity */}
                      <td className="py-4 px-4 text-center">
                        <div className="flex flex-col items-center">
                          <span className={`flex items-center gap-1 ${getComplexityColor(pattern.complexity_label)}`}>
                            <span>{pattern.complexity_emoji}</span>
                            <span>{pattern.complexity_avg?.toFixed(2) || '—'}</span>
                          </span>
                          {pattern.complexity_min !== null && pattern.complexity_max !== null && (
                            <span className="text-xs text-gray-500">
                              {pattern.complexity_min.toFixed(2)} - {pattern.complexity_max.toFixed(2)}
                            </span>
                          )}
                        </div>
                      </td>
                      
                      {/* Quality */}
                      <td className={`py-4 px-4 text-center font-medium ${getQualityColor(pattern.quality_status)}`}>
                        {pattern.avg_quality_formatted}
                      </td>
                      
                      {/* Calls */}
                      <td className="py-4 px-4 text-right text-gray-300">
                        {formatNumber(pattern.call_count)}
                      </td>
                      
                      {/* Savable */}
                      <td className="py-4 px-4 text-right">
                        {pattern.savable > 0 ? (
                          <span className="text-green-400 font-semibold">${pattern.savable.toFixed(2)}</span>
                        ) : pattern.savable < 0 ? (
                          <span className="text-red-400 font-semibold">+${Math.abs(pattern.savable).toFixed(2)}</span>
                        ) : (
                          <span className="text-gray-500">—</span>
                        )}
                      </td>
                      
                      {/* Safe % */}
                      <td className="py-4 px-4 text-center">
                        <div className="flex flex-col items-center">
                          <span className={`font-medium ${getSafePctColor(pattern.safe_pct)}`}>
                            {pattern.safe_pct}%
                          </span>
                          {pattern.safe_pct < 80 && (
                            <span className="text-xs text-yellow-400">⚠️ risky</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={9} className="py-12 text-center text-gray-500">
                      No routing patterns found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          
          {/* Footer */}
          <div className="px-4 py-3 border-t border-gray-800 flex items-center justify-between text-sm text-gray-500">
            <span>
              Showing <span className="text-white">{filteredPatterns.length}</span> of {(patterns || []).length} patterns
            </span>
            <div className="flex items-center gap-4">
              <span>9 columns</span>
              <span>Sort: {sortBy.charAt(0).toUpperCase() + sortBy.slice(1)} {sortOrder === 'desc' ? '↓' : '↑'}</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// HELPER COMPONENTS
// ─────────────────────────────────────────────────────────────────────────────

function StatBadge({ label, value, theme, color }) {
  const textColor = color || (theme ? theme.text : 'text-gray-300');
  
  return (
    <div className="px-4 py-2 bg-gray-900 rounded-lg border border-gray-700">
      <span className="text-xs text-gray-500">{label}: </span>
      <span className={`font-semibold ${textColor}`}>{value}</span>
    </div>
  );
}

function FilterDropdown({ label, icon, options, selected, onChange }) {
  const [isOpen, setIsOpen] = useState(false);
  
  const toggleOption = (option) => {
    if (selected.includes(option)) {
      onChange(selected.filter(x => x !== option));
    } else {
      onChange([...selected, option]);
    }
  };
  
  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 text-sm flex items-center gap-2 hover:bg-gray-700"
      >
        <span>{icon}</span>
        <span>{label}</span>
        {selected.length > 0 && (
          <span className="bg-purple-500 text-white text-xs px-1.5 rounded">{selected.length}</span>
        )}
        <span className="text-gray-500">▼</span>
      </button>
      
      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute top-full left-0 mt-1 z-20 bg-gray-800 border border-gray-700 rounded-lg shadow-xl min-w-48 max-h-64 overflow-y-auto">
            {options.map(option => (
              <label
                key={option}
                className="flex items-center gap-2 px-3 py-2 hover:bg-gray-700 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selected.includes(option)}
                  onChange={() => toggleOption(option)}
                  className="rounded bg-gray-700 border-gray-600 text-purple-500 focus:ring-purple-500"
                />
                <span className="text-sm text-gray-300">{option}</span>
              </label>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function FilterTag({ label, onRemove }) {
  return (
    <span className="px-2 py-1 bg-gray-800 rounded text-sm text-gray-300 flex items-center gap-1">
      {label}
      <button onClick={onRemove} className="text-gray-500 hover:text-white ml-1">×</button>
    </span>
  );
}