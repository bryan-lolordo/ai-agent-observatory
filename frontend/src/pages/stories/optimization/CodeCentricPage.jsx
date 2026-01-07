/**
 * CodeCentricPage - Code-First Optimization View
 *
 * Shows operations with their code at the center, surrounded by
 * issues and fixes. Makes it easy to see exactly where in your
 * code you need to make changes.
 *
 * URL: /stories/optimization/code-view
 */

import { useState, useMemo, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCalls } from '../../../hooks/useCalls';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';
import CodeCentricView, { generateIssuesFromOperation } from '../../../components/stories/CodeCentricView';
import { ChevronDown, ChevronRight, Code2, Layers, AlertCircle, RefreshCw, Loader2 } from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────────────
// Operation Selector Sidebar
// ─────────────────────────────────────────────────────────────────────────────

function OperationSelector({ operations, selectedOperation, onSelect, loading }) {
  const [expandedAgents, setExpandedAgents] = useState(() => {
    // Start with all agents expanded
    const expanded = {};
    operations.forEach(op => {
      expanded[op.agent_name] = true;
    });
    return expanded;
  });

  // Group operations by agent
  const operationsByAgent = useMemo(() => {
    const grouped = {};
    operations.forEach(op => {
      if (!grouped[op.agent_name]) {
        grouped[op.agent_name] = [];
      }
      grouped[op.agent_name].push(op);
    });
    return grouped;
  }, [operations]);

  const toggleAgent = (agent) => {
    setExpandedAgents(prev => ({
      ...prev,
      [agent]: !prev[agent]
    }));
  };

  if (loading) {
    return (
      <div className={`w-64 flex-shrink-0 border-r ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-4`}>
        <div className="animate-pulse space-y-3">
          <div className={`h-4 ${BASE_THEME.container.tertiary} rounded w-3/4`}></div>
          <div className={`h-8 ${BASE_THEME.container.primary} rounded`}></div>
          <div className={`h-8 ${BASE_THEME.container.primary} rounded`}></div>
          <div className={`h-8 ${BASE_THEME.container.primary} rounded`}></div>
        </div>
      </div>
    );
  }

  return (
    <div className={`w-64 flex-shrink-0 border-r ${BASE_THEME.border.default} ${BASE_THEME.container.primary} overflow-y-auto`}>
      <div className={`p-4 border-b ${BASE_THEME.border.default}`}>
        <h3 className={`text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide flex items-center gap-2`}>
          <Layers className="w-4 h-4" />
          Operations ({operations.length})
        </h3>
        <p className={`text-xs ${BASE_THEME.text.muted} mt-1`}>
          Select an operation to view its code
        </p>
      </div>

      <div className="py-2">
        {Object.entries(operationsByAgent).map(([agent, ops]) => (
          <div key={agent}>
            {/* Agent Header */}
            <button
              onClick={() => toggleAgent(agent)}
              className={`w-full flex items-center gap-2 px-4 py-2 text-sm ${BASE_THEME.text.muted} hover:${BASE_THEME.text.secondary} hover:${BASE_THEME.container.tertiary} transition-colors`}
            >
              {expandedAgents[agent] ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
              <span className="font-medium">{agent}</span>
              <span className={`text-xs ${BASE_THEME.text.muted}`}>({ops.length})</span>
            </button>

            {/* Operations under this agent */}
            {expandedAgents[agent] && (
              <div className="pl-6">
                {ops.map(op => (
                  <button
                    key={op.operation}
                    onClick={() => onSelect(op)}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors ${
                      selectedOperation?.operation === op.operation
                        ? 'bg-purple-500/20 text-purple-300 border-l-2 border-purple-500'
                        : `${BASE_THEME.text.muted} hover:${BASE_THEME.text.secondary} hover:${BASE_THEME.container.tertiary} border-l-2 border-transparent`
                    }`}
                  >
                    <Code2 className="w-3.5 h-3.5 flex-shrink-0" />
                    <span className="font-mono text-xs truncate">{op.operation}</span>
                    {op.issue_count > 0 && (
                      <span className="ml-auto text-xs px-1.5 py-0.5 rounded bg-yellow-500/20 text-yellow-400">
                        {op.issue_count}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}

        {operations.length === 0 && (
          <div className={`px-4 py-8 text-center ${BASE_THEME.text.muted} text-sm`}>
            No operations found
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Page Component
// ─────────────────────────────────────────────────────────────────────────────

export default function CodeCentricPage() {
  const navigate = useNavigate();
  const theme = STORY_THEMES.optimization;

  // Fetch all calls to get system prompts and metrics
  const { data: calls, loading, error, refetch } = useCalls({
    endpoint: '/api/calls',
    autoFetch: true,
  });

  const [selectedOperation, setSelectedOperation] = useState(null);
  const [systemPrompt, setSystemPrompt] = useState(null);
  const [loadingPrompt, setLoadingPrompt] = useState(false);

  // Fetch system prompt for selected operation (from call detail endpoint)
  const fetchSystemPrompt = useCallback(async (callId) => {
    if (!callId) return;

    setLoadingPrompt(true);
    try {
      const response = await fetch(`/api/calls/${callId}`);
      if (response.ok) {
        const data = await response.json();
        setSystemPrompt(data.system_prompt || data.prompt || null);
      }
    } catch (err) {
      console.error('Failed to fetch system prompt:', err);
    } finally {
      setLoadingPrompt(false);
    }
  }, []);

  // Group calls by operation and compute aggregate metrics
  const operations = useMemo(() => {
    if (!calls || calls.length === 0) return [];

    // Group calls by (agent, operation)
    const byOperation = {};

    calls.forEach(call => {
      const agent = call.agent_name || 'Unknown';
      const op = call.operation || 'unknown';
      const key = `${agent}::${op}`;

      if (!byOperation[key]) {
        byOperation[key] = {
          agent_name: agent,
          operation: op,
          calls: [],
          // We'll compute these after gathering all calls
        };
      }
      byOperation[key].calls.push(call);
    });

    // Now compute aggregate stats for each operation
    const ops = Object.values(byOperation).map(group => {
      const opCalls = group.calls;
      const callCount = opCalls.length;

      // Use the first call with a system prompt as the representative
      const sampleCall = opCalls.find(c => c.system_prompt) || opCalls[0];

      // Aggregate metrics
      const totalCost = opCalls.reduce((sum, c) => sum + (c.total_cost || 0), 0);
      const avgLatency = opCalls.reduce((sum, c) => sum + (c.latency_ms || 0), 0) / callCount;
      const avgSystemTokens = opCalls.reduce((sum, c) => sum + (c.system_prompt_tokens || 0), 0) / callCount;
      const avgPromptTokens = opCalls.reduce((sum, c) => sum + (c.prompt_tokens || 0), 0) / callCount;
      const avgCompletionTokens = opCalls.reduce((sum, c) => sum + (c.completion_tokens || 0), 0) / callCount;

      // Check for issues to determine issue_count
      let issueCount = 0;

      // High call count (potential batching opportunity)
      if (callCount > 10) issueCount++;

      // High cost
      if (totalCost > 1) issueCount++;

      // No caching and large system prompt
      const hasCacheHit = opCalls.some(c => c.cache_hit);
      if (!hasCacheHit && avgSystemTokens > 200) issueCount++;

      // Slow latency
      if (avgLatency > 2000) issueCount++;

      // Large system prompt
      if (avgSystemTokens > 500) issueCount++;

      // Token imbalance
      const ratio = avgPromptTokens / (avgCompletionTokens || 1);
      if (ratio > 20) issueCount++;

      return {
        agent_name: group.agent_name,
        operation: group.operation,
        call_count: callCount,
        total_cost: totalCost,
        avg_latency_ms: avgLatency,
        system_prompt_tokens: Math.round(avgSystemTokens),
        prompt_tokens: Math.round(avgPromptTokens),
        completion_tokens: Math.round(avgCompletionTokens),
        cache_hit: hasCacheHit,
        model_name: sampleCall?.model_name || 'Unknown',
        latency_ms: avgLatency,
        issue_count: issueCount,
        // Store sample call_id to fetch system prompt
        sample_call_id: sampleCall?.call_id || null,
        _sampleCall: sampleCall,
      };
    });

    // Sort by issue count (descending) then by call count
    return ops.sort((a, b) => {
      if (b.issue_count !== a.issue_count) return b.issue_count - a.issue_count;
      return b.call_count - a.call_count;
    });
  }, [calls]);

  // Auto-select first operation with issues
  useEffect(() => {
    if (!selectedOperation && operations.length > 0) {
      const withIssues = operations.find(op => op.issue_count > 0);
      const opToSelect = withIssues || operations[0];
      setSelectedOperation(opToSelect);
      // Fetch system prompt for this operation
      if (opToSelect?.sample_call_id) {
        fetchSystemPrompt(opToSelect.sample_call_id);
      }
    }
  }, [operations, selectedOperation, fetchSystemPrompt]);

  // When selected operation changes, fetch its system prompt
  const handleSelectOperation = useCallback((op) => {
    setSelectedOperation(op);
    setSystemPrompt(null); // Clear previous prompt
    if (op?.sample_call_id) {
      fetchSystemPrompt(op.sample_call_id);
    }
  }, [fetchSystemPrompt]);

  // Generate issues for selected operation
  const operationIssues = useMemo(() => {
    if (!selectedOperation) return [];
    return generateIssuesFromOperation(selectedOperation);
  }, [selectedOperation]);

  const handleIssueClick = (issue) => {
    // Navigate to the relevant story page
    const storyRoutes = {
      latency: '/stories/latency',
      cache: '/stories/cache',
      cost: '/stories/cost',
      quality: '/stories/quality',
      routing: '/stories/routing',
      token: '/stories/token_imbalance',
      prompt: '/stories/system_prompt',
    };

    const route = storyRoutes[issue.storyId];
    if (route) {
      navigate(route);
    }
  };

  if (loading && calls.length === 0) return <StoryPageSkeleton />;

  if (error) {
    return (
      <div className={`min-h-screen ${BASE_THEME.container.tertiary} p-8`}>
        <PageContainer>
          <div className={`${BASE_THEME.status.error.bg} border ${BASE_THEME.status.error.border} rounded-lg p-6`}>
            <h2 className={`text-xl font-bold ${BASE_THEME.status.error.textBold} mb-2 flex items-center gap-2`}>
              <AlertCircle className="w-5 h-5" />
              Error Loading Data
            </h2>
            <p className={BASE_THEME.text.secondary}>{error}</p>
            <button
              onClick={refetch}
              className="mt-4 px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 transition-colors flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Retry
            </button>
          </div>
        </PageContainer>
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} ${BASE_THEME.text.primary}`}>
      <StoryNavTabs activeStory="optimization" />

      {/* Page Header */}
      <div className={`border-b ${BASE_THEME.border.default} ${BASE_THEME.container.primary}`}>
        <PageContainer>
          <div className="py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className={`text-2xl font-bold ${theme.text} flex items-center gap-3`}>
                  <Code2 className="w-6 h-6" />
                  Code-Centric View
                </h1>
                <p className={`text-sm ${BASE_THEME.text.muted} mt-1`}>
                  See your operation code with issues and fixes - know exactly where to make changes
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => navigate('/stories/optimization')}
                  className={`px-3 py-1.5 rounded text-sm ${BASE_THEME.text.muted} hover:${BASE_THEME.text.secondary} hover:${BASE_THEME.container.tertiary} transition-colors`}
                >
                  Table View
                </button>
                <button
                  className={`px-3 py-1.5 rounded text-sm ${theme.bg} text-white`}
                >
                  Code View
                </button>
                <button
                  onClick={refetch}
                  className={`px-2 py-1.5 rounded text-sm ${BASE_THEME.text.muted} hover:${BASE_THEME.text.secondary} hover:${BASE_THEME.container.tertiary} transition-colors`}
                  title="Refresh data"
                >
                  <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                </button>
              </div>
            </div>
          </div>
        </PageContainer>
      </div>

      {/* Main Content - Sidebar + Code View */}
      <div className="flex" style={{ height: 'calc(100vh - 180px)' }}>
        {/* Operation Selector Sidebar */}
        <OperationSelector
          operations={operations}
          selectedOperation={selectedOperation}
          onSelect={handleSelectOperation}
          loading={loading && operations.length === 0}
        />

        {/* Code Centric View */}
        <div className="flex-1 overflow-y-auto p-6">
          {selectedOperation ? (
            <CodeCentricView
              operation={selectedOperation.operation}
              operationData={selectedOperation}
              systemPrompt={systemPrompt}
              systemPromptTokens={selectedOperation.system_prompt_tokens}
              issues={operationIssues}
              onIssueClick={handleIssueClick}
              loadingPrompt={loadingPrompt}
            />
          ) : (
            <div className={`flex items-center justify-center h-full ${BASE_THEME.text.muted}`}>
              <div className="text-center">
                <Code2 className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Select an operation from the sidebar to view its code</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
