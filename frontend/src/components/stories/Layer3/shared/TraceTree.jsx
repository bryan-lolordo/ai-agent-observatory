/**
 * TraceTree - Shows call trace hierarchy with pattern analysis
 *
 * UPDATED: Uses theme system - no hardcoded colors!
 */

import React, { useState, useEffect } from 'react';
import {
  ChevronRight,
  ChevronDown,
  Clock,
  DollarSign,
  MessageSquare,
  Wrench,
  Database,
  AlertCircle,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Flame,
  Lightbulb
} from 'lucide-react';
import { BASE_THEME, getSeverityColors } from '../../../../utils/themeUtils';
import { STORY_THEMES } from '../../../../config/theme';

// ===========================================================================
// AGENT ROLE ICONS - Using theme colors
// ===========================================================================

const AgentRoleIcon = ({ role }) => {
  const icons = {
    orchestrator: MessageSquare,
    retriever: Database,
    analyst: Wrench,
    reviewer: AlertCircle,
    planner: Wrench,
  };

  // Map roles to story themes
  const colors = {
    orchestrator: BASE_THEME.status.info.text,
    retriever: STORY_THEMES.optimization.text,
    analyst: STORY_THEMES.routing.text,
    reviewer: STORY_THEMES.latency.text,
    planner: STORY_THEMES.cache.text,
  };

  const Icon = icons[role] || Wrench;
  const colorClass = colors[role] || BASE_THEME.text.secondary;

  return <Icon className={`w-4 h-4 ${colorClass}`} />;
};

// ===========================================================================
// HELPER: Group calls by function name
// ===========================================================================

function groupCallsByFunction(children) {
  const groups = {};

  children.forEach(child => {
    const key = `${child.call.agent_name}_${child.call.operation}`;

    if (!groups[key]) {
      groups[key] = {
        agent_name: child.call.agent_name,
        operation: child.call.operation,
        agent_role: child.call.agent_role,
        calls: [],
        total_latency: 0,
        total_cost: 0,
        total_tokens: 0,
        has_errors: false,
      };
    }

    groups[key].calls.push(child);
    groups[key].total_latency += child.call.latency_ms || 0;
    groups[key].total_cost += child.call.total_cost || 0;
    groups[key].total_tokens += child.call.total_tokens || 0;
    if (!child.call.success) groups[key].has_errors = true;
  });

  return Object.values(groups);
}

// ===========================================================================
// HELPER: Detect patterns and suggest optimizations
// ===========================================================================

function analyzePattern(group) {
  const count = group.calls.length;
  const avgLatency = group.total_latency / count;

  // Expensive thresholds
  const isExpensive = group.total_cost > 0.05 || group.total_latency > 5000;
  const isSlow = avgLatency > 1000;
  const isHighVolume = count > 10;

  const suggestions = [];
  let severity = 'info'; // info, warning, critical

  // Pattern detection
  if (count > 1) {
    if (count > 5) {
      suggestions.push(`${count} sequential calls detected - consider batching or parallelizing`);
      severity = 'warning';
    } else if (count > 2) {
      suggestions.push(`${count} repeated calls - check if caching would help`);
      severity = 'info';
    }
  }

  if (isExpensive && isHighVolume) {
    suggestions.push(`High cost from volume (${count} calls × $${(group.total_cost / count).toFixed(4)})`);
    severity = 'critical';
  }

  if (isSlow && count > 1) {
    suggestions.push(`Slow execution - avg ${(avgLatency / 1000).toFixed(1)}s per call`);
    severity = severity === 'critical' ? 'critical' : 'warning';
  }

  return { suggestions, severity };
}

// ===========================================================================
// GROUPED CALL NODE (shows multiple calls as one)
// ===========================================================================

const GroupedCallNode = ({ group, depth = 0 }) => {
  const [showAll, setShowAll] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);

  const count = group.calls.length;
  const indent = depth * 24;

  // Format metrics
  const latencySeconds = (group.total_latency / 1000).toFixed(1);
  const cost = group.total_cost.toFixed(4);
  const tokens = group.total_tokens;

  // Analyze pattern
  const { suggestions, severity } = analyzePattern(group);

  // Get severity colors from theme
  const severityColorsMap = {
    critical: getSeverityColors('critical'),
    warning: getSeverityColors('warning'),
    info: getSeverityColors('info'),
  };

  const severityTheme = severityColorsMap[severity] || severityColorsMap.info;

  return (
    <div className="font-mono text-base">
      {/* Group header */}
      <div
        className={`
          flex items-center gap-2 py-2.5 px-3
          ${BASE_THEME.state.hover}
          cursor-pointer
          transition-colors
          ${depth > 0 ? `border-l-2 ${BASE_THEME.border.default}` : ''}
        `}
        style={{ paddingLeft: `${indent + 12}px` }}
        onClick={() => setShowAll(!showAll)}
      >
        {/* Expand/collapse chevron */}
        {count > 1 ? (
          showAll ? (
            <ChevronDown className={`w-5 h-5 ${BASE_THEME.text.secondary} flex-shrink-0`} />
          ) : (
            <ChevronRight className={`w-5 h-5 ${BASE_THEME.text.secondary} flex-shrink-0`} />
          )
        ) : (
          <div className="w-5 h-5 flex-shrink-0" />
        )}

        {/* Severity indicator */}
        {severity === 'critical' && <Flame className={`w-5 h-5 ${BASE_THEME.status.error.text} flex-shrink-0`} />}
        {severity === 'warning' && <AlertTriangle className={`w-5 h-5 ${BASE_THEME.status.warning.text} flex-shrink-0`} />}
        {severity === 'info' && <CheckCircle className={`w-5 h-5 ${BASE_THEME.status.success.text} flex-shrink-0`} />}

        {/* Agent role icon */}
        <AgentRoleIcon role={group.agent_role} />

        {/* Agent name & operation */}
        <span className={`font-semibold ${BASE_THEME.text.primary}`}>
          {group.agent_name || 'Unknown'}
        </span>
        <span className={BASE_THEME.text.muted}>→</span>
        <span className={BASE_THEME.text.secondary}>{group.operation}</span>

        {/* Call count badge */}
        {count > 1 && (
          <span className={`ml-2 px-2.5 py-1 text-sm rounded border ${severityTheme.text} ${severityTheme.bg} ${severityTheme.border}`}>
            ×{count}
          </span>
        )}

        {/* Error indicator */}
        {group.has_errors && (
          <span className={`ml-2 px-2.5 py-1 ${BASE_THEME.status.error.bg} ${BASE_THEME.status.error.text} text-sm rounded border ${BASE_THEME.status.error.border}`}>
            ERRORS
          </span>
        )}

        {/* Metrics (right-aligned) */}
        <div className={`ml-auto flex items-center gap-6 text-sm ${BASE_THEME.text.secondary} flex-shrink-0`}>
          <span className="w-14 text-center" title="Number of calls">
            {count}
          </span>
          <span className="w-16 text-right" title="Total Latency">
            {latencySeconds}s
          </span>
          <span className="w-20 text-right" title="Total Cost">
            ${cost}
          </span>
          <span className="w-16 text-center" title="Total Tokens">
            {tokens}
          </span>
        </div>
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && showSuggestions && (
        <div
          className={`ml-12 mr-3 mt-1 mb-2 p-3 rounded border text-sm ${severityTheme.text} ${severityTheme.bg} ${severityTheme.border}`}
          style={{ marginLeft: `${indent + 48}px` }}
        >
          <div className="flex items-start gap-2">
            <Lightbulb className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              {suggestions.map((suggestion, idx) => (
                <div key={idx} className={BASE_THEME.text.secondary}>
                  {suggestion}
                </div>
              ))}
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowSuggestions(false);
              }}
              className={`${BASE_THEME.text.muted} hover:${BASE_THEME.text.secondary}`}
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Individual calls (expanded) */}
      {showAll && count > 1 && (
        <div className={`border-l-2 ${BASE_THEME.border.default} ml-6`} style={{ marginLeft: `${indent + 24}px` }}>
          {group.calls.map((child, idx) => (
            <IndividualCallNode
              key={child.call.call_id}
              nodeData={child}
              depth={depth + 1}
              index={idx + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};

// ===========================================================================
// INDIVIDUAL CALL NODE (single call detail)
// ===========================================================================

const IndividualCallNode = ({ nodeData, depth = 0, index = null }) => {
  const call = nodeData.call;
  const indent = depth * 24;

  // Format metrics
  const latencySeconds = ((call.latency_ms || 0) / 1000).toFixed(1);
  const cost = (call.total_cost || 0).toFixed(4);
  const tokens = call.total_tokens || 0;

  return (
    <div
      className={`
        flex items-center gap-2 py-2.5 px-3
        text-sm ${BASE_THEME.text.secondary}
        ${!call.success ? `${BASE_THEME.status.error.bg} ${BASE_THEME.status.error.border}` : ''}
      `}
      style={{ paddingLeft: `${indent + 12}px` }}
    >
      {/* Call number */}
      {index && (
        <span className={`${BASE_THEME.text.muted} w-6`}>#{index}</span>
      )}

      {/* Success/Error indicator */}
      {call.success ? (
        <CheckCircle className={`w-4 h-4 ${BASE_THEME.status.success.text} flex-shrink-0`} />
      ) : (
        <XCircle className={`w-4 h-4 ${BASE_THEME.status.error.text} flex-shrink-0`} />
      )}

      {/* Timestamp or ID */}
      <span className={`${BASE_THEME.text.muted} flex-1`}>
        {call.call_id?.substring(0, 8)}...
      </span>

      {/* Metrics */}
      <div className="flex items-center gap-6 flex-shrink-0">
        <span className="w-14 text-center">-</span>
        <span className="w-16 text-right">{latencySeconds}s</span>
        <span className="w-20 text-right">${cost}</span>
        <span className="w-16 text-center">{tokens}</span>
      </div>
    </div>
  );
};

// ===========================================================================
// MAIN TRACE TREE COMPONENT
// ===========================================================================

export default function TraceTree({ callId, conversationId }) {
  const [trace, setTrace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('single');

  useEffect(() => {
    fetchTrace();
  }, [callId, conversationId]);

  const fetchTrace = async () => {
    setLoading(true);
    setError(null);

    try {
      let url;
      if (conversationId) {
        url = `/api/calls/conversations/${conversationId}/tree`;
        setViewMode('conversation');
      } else if (callId) {
        url = `/api/calls/${callId}/trace?include_siblings=true`;
        setViewMode('single');
      } else {
        throw new Error('Either callId or conversationId is required');
      }

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch trace: ${response.statusText}`);
      }

      const data = await response.json();
      setTrace(data);
    } catch (err) {
      console.error('Failed to fetch trace:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className={`animate-spin rounded-full h-8 w-8 border-b-2 ${BASE_THEME.status.info.border}`} />
        <span className={`ml-3 ${BASE_THEME.text.secondary}`}>Loading trace...</span>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={`${BASE_THEME.status.error.bg} border ${BASE_THEME.status.error.border} rounded-lg p-4`}>
        <div className={`flex items-center gap-2 ${BASE_THEME.status.error.text}`}>
          <AlertCircle className="w-5 h-5" />
          <span className="font-semibold">Failed to load trace</span>
        </div>
        <p className={`mt-2 text-sm ${BASE_THEME.status.error.text}`}>{error}</p>
      </div>
    );
  }

  // No data
  if (!trace) {
    return (
      <div className={`text-center p-8 ${BASE_THEME.text.muted}`}>
        No trace data available
      </div>
    );
  }

  // ===========================================================================
  // RENDER: Conversation View (with grouping)
  // ===========================================================================

  if (viewMode === 'conversation' && trace.turns) {
    return (
      <div className="space-y-4">
        {/* Column Headers */}
        <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg px-3 py-2.5`}>
          <div className={`flex items-center gap-2 text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide`}>
            <div className="flex-1 flex items-center gap-2">
              <div className="w-5" />
              <div className="w-5" />
              <div className="w-5" />
              <span>Call Chain</span>
            </div>
            <div className="flex items-center gap-6 flex-shrink-0">
              <span className="w-14 text-center">Calls</span>
              <span className="flex items-center gap-1 w-16 justify-center">
                <Clock className="w-4 h-4" />
                Time
              </span>
              <span className="flex items-center gap-1 w-20 justify-center">
                <DollarSign className="w-4 h-4" />
                Cost
              </span>
              <span className="w-16 text-center">🪙 Tokens</span>
            </div>
          </div>
        </div>

        {/* Turns */}
        <div className="space-y-4">
          {trace.turns.map((turn) => {
            const turnTimeSeconds = ((turn.total_latency_ms || 0) / 1000).toFixed(1);

            const userMessage = turn.user_message || "[No user message recorded]";
            const displayMessage = userMessage.length > 100
              ? userMessage.substring(0, 100) + '...'
              : userMessage;

            const groups = groupCallsByFunction(turn.children || []);

            const hasExpensiveCalls = turn.total_cost > 0.5 || turn.total_latency_ms > 10000;

            return (
              <div key={turn.turn_number} className={`border ${BASE_THEME.border.default} rounded-lg overflow-hidden ${BASE_THEME.container.primary}`}>
                {/* Turn header */}
                <div className={`${BASE_THEME.container.secondary} px-3 py-3 border-b ${BASE_THEME.border.default}`}>
                  <div className="flex items-center gap-2">
                    {/* Left side - matches the spacing of grouped calls */}
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <div className="w-5 flex-shrink-0" /> {/* Chevron spacer */}
                      <div className="w-5 flex-shrink-0" /> {/* Severity spacer */}
                      <div className="w-5 flex-shrink-0" /> {/* Icon spacer */}
                      <span className={`${BASE_THEME.status.info.bg} text-white text-sm font-bold px-2.5 py-1 rounded flex-shrink-0`}>
                        Turn {turn.turn_number}
                      </span>
                      <span className={`text-base ${BASE_THEME.text.secondary} font-medium truncate`}>
                        "{displayMessage}"
                      </span>
                      {hasExpensiveCalls && (
                        <span className={`flex items-center gap-1 text-sm ${BASE_THEME.status.error.text}`}>
                          <Flame className="w-4 h-4" />
                          EXPENSIVE
                        </span>
                      )}
                    </div>
                    {/* Right side - matches column widths exactly */}
                    <div className={`flex items-center gap-6 text-sm ${BASE_THEME.text.secondary} font-medium flex-shrink-0`}>
                      <span className="w-14 text-center">{turn.total_calls}</span>
                      <span className="w-16 text-right">{turnTimeSeconds}s</span>
                      <span className="w-20 text-right">${(turn.total_cost || 0).toFixed(4)}</span>
                      <span className="w-16 text-center">{turn.total_tokens || '-'}</span>
                    </div>
                  </div>
                </div>

                {/* Grouped calls */}
                <div>
                  {groups.map((group, idx) => (
                    <GroupedCallNode key={idx} group={group} depth={0} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // ===========================================================================
  // RENDER: Single Call View (with grouping)
  // ===========================================================================

  if (viewMode === 'single' && trace.root_call) {
    const hasConversation = trace.conversation_turns && trace.conversation_turns.length > 1;
    const groups = groupCallsByFunction(trace.children || []);

    return (
      <div className="space-y-4">
        {/* View toggle */}
        {hasConversation && (
          <div className={`flex gap-2 border-b ${BASE_THEME.border.default} pb-2`}>
            <button className={`px-4 py-2 rounded-t font-medium ${BASE_THEME.status.info.bg} text-white`} disabled>
              This Call Only
            </button>
            <button
              className={`px-4 py-2 rounded-t font-medium ${BASE_THEME.container.secondary} ${BASE_THEME.text.secondary} hover:${BASE_THEME.container.tertiary}`}
              onClick={() => {
                window.location.href = `/api/calls/conversations/${trace.root_call.conversation_id}/tree`;
              }}
            >
              Full Conversation ({trace.conversation_turns.length} turns)
            </button>
          </div>
        )}

        {/* Column Headers */}
        <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg px-3 py-2.5`}>
          <div className={`flex items-center gap-2 text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide`}>
            <div className="flex-1 flex items-center gap-2">
              <div className="w-5" />
              <div className="w-5" />
              <div className="w-5" />
              <span>Call Chain</span>
            </div>
            <div className="flex items-center gap-6 flex-shrink-0">
              <span className="w-14 text-center">Calls</span>
              <span className="flex items-center gap-1 w-16 justify-center">
                <Clock className="w-4 h-4" />
                Time
              </span>
              <span className="flex items-center gap-1 w-20 justify-center">
                <DollarSign className="w-4 h-4" />
                Cost
              </span>
              <span className="w-16 text-center">🪙 Tokens</span>
            </div>
          </div>
        </div>

        {/* Grouped calls */}
        <div className={`border ${BASE_THEME.border.default} rounded-lg overflow-hidden ${BASE_THEME.container.primary}`}>
          {groups.map((group, idx) => (
            <GroupedCallNode key={idx} group={group} depth={0} />
          ))}
        </div>
      </div>
    );
  }

  return <div className={`${BASE_THEME.text.muted} p-8`}>Invalid trace data</div>;
}
