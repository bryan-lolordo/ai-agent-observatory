// src/components/stories/Layer3/shared/TraceTree.jsx
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

// ===========================================================================
// AGENT ROLE ICONS
// ===========================================================================

const AgentRoleIcon = ({ role }) => {
  const icons = {
    orchestrator: MessageSquare,
    retriever: Database,
    analyst: Wrench,
    reviewer: AlertCircle,
    planner: Wrench,
  };
  
  const colors = {
    orchestrator: 'text-blue-400',
    retriever: 'text-green-400',
    analyst: 'text-purple-400',
    reviewer: 'text-orange-400',
    planner: 'text-pink-400',
  };
  
  const Icon = icons[role] || Wrench;
  const colorClass = colors[role] || 'text-gray-400';
  
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
    // Check if calls are similar (potential duplicates or loop)
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
  
  // Severity colors
  const severityColors = {
    critical: 'text-red-400 bg-red-900/20 border-red-700',
    warning: 'text-orange-400 bg-orange-900/20 border-orange-700',
    info: 'text-blue-400 bg-blue-900/20 border-blue-700',
  };
  
  const severityColor = severityColors[severity] || severityColors.info;
  
  return (
    <div className="font-mono text-sm">
      {/* Group header */}
      <div 
        className={`
          flex items-center gap-2 py-2 px-3 
          hover:bg-gray-800/50
          cursor-pointer
          transition-colors
          ${depth > 0 ? 'border-l-2 border-gray-700' : ''}
          ${severity === 'critical' ? 'bg-red-900/10' : ''}
          ${severity === 'warning' ? 'bg-orange-900/10' : ''}
          ${group.has_errors ? 'border-red-700' : ''}
        `}
        style={{ paddingLeft: `${indent + 12}px` }}
        onClick={() => setShowAll(!showAll)}
      >
        {/* Expand/collapse chevron */}
        {count > 1 ? (
          showAll ? (
            <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
          )
        ) : (
          <div className="w-4 h-4 flex-shrink-0" />
        )}
        
        {/* Severity indicator */}
        {severity === 'critical' && <Flame className="w-4 h-4 text-red-400 flex-shrink-0" />}
        {severity === 'warning' && <AlertTriangle className="w-4 h-4 text-orange-400 flex-shrink-0" />}
        {severity === 'info' && <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />}
        
        {/* Agent role icon */}
        <AgentRoleIcon role={group.agent_role} />
        
        {/* Agent name & operation */}
        <span className="font-semibold text-gray-200">
          {group.agent_name || 'Unknown'}
        </span>
        <span className="text-gray-500">→</span>
        <span className="text-gray-300">{group.operation}</span>
        
        {/* Call count badge */}
        {count > 1 && (
          <span className={`ml-2 px-2 py-0.5 text-xs rounded border ${severityColor}`}>
            ×{count}
          </span>
        )}
        
        {/* Error indicator */}
        {group.has_errors && (
          <span className="ml-2 px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded border border-red-500/30">
            ERRORS
          </span>
        )}
        
        {/* Metrics (right-aligned) */}
        <div className="ml-auto flex items-center gap-6 text-xs text-gray-400 flex-shrink-0">
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
          className={`ml-12 mr-3 mt-1 mb-2 p-2 rounded border text-xs ${severityColor}`}
          style={{ marginLeft: `${indent + 48}px` }}
        >
          <div className="flex items-start gap-2">
            <Lightbulb className="w-3 h-3 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              {suggestions.map((suggestion, idx) => (
                <div key={idx} className="text-gray-300">
                  {suggestion}
                </div>
              ))}
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowSuggestions(false);
              }}
              className="text-gray-500 hover:text-gray-300"
            >
              ✕
            </button>
          </div>
        </div>
      )}
      
      {/* Individual calls (expanded) */}
      {showAll && count > 1 && (
        <div className="border-l-2 border-gray-700 ml-6" style={{ marginLeft: `${indent + 24}px` }}>
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
        flex items-center gap-2 py-2 px-3 
        text-xs text-gray-400
        ${!call.success ? 'bg-red-900/20 border-red-700' : ''}
      `}
      style={{ paddingLeft: `${indent + 12}px` }}
    >
      {/* Call number */}
      {index && (
        <span className="text-gray-600 w-6">#{index}</span>
      )}
      
      {/* Success/Error indicator */}
      {call.success ? (
        <CheckCircle className="w-3 h-3 text-green-500 flex-shrink-0" />
      ) : (
        <XCircle className="w-3 h-3 text-red-500 flex-shrink-0" />
      )}
      
      {/* Timestamp or ID */}
      <span className="text-gray-500 flex-1">
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
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        <span className="ml-3 text-gray-400">Loading trace...</span>
      </div>
    );
  }
  
  // Error state
  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-700 rounded-lg p-4">
        <div className="flex items-center gap-2 text-red-400">
          <AlertCircle className="w-5 h-5" />
          <span className="font-semibold">Failed to load trace</span>
        </div>
        <p className="mt-2 text-sm text-red-300">{error}</p>
      </div>
    );
  }
  
  // No data
  if (!trace) {
    return (
      <div className="text-center p-8 text-gray-500">
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
        <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2">
          <div className="flex items-center gap-2 text-xs font-medium text-gray-400 uppercase tracking-wide">
            <div className="flex-1 flex items-center gap-2">
              <div className="w-4" />
              <div className="w-4" />
              <div className="w-4" />
              <span>Call Chain</span>
            </div>
            <div className="flex items-center gap-6 flex-shrink-0">
              <span className="w-14 text-center">Calls</span>
              <span className="flex items-center gap-1 w-16 justify-center">
                <Clock className="w-3 h-3" />
                Time
              </span>
              <span className="flex items-center gap-1 w-20 justify-center">
                <DollarSign className="w-3 h-3" />
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
            
            // User message should come from the ChatAgent call in this turn
            // Backend should query: SELECT user_message FROM llm_calls WHERE turn_number = X AND agent_name = 'ChatAgent'
            const userMessage = turn.user_message || "[No user message recorded]";
            const displayMessage = userMessage.length > 100 
              ? userMessage.substring(0, 100) + '...' 
              : userMessage;
            
            // Group children by function
            const groups = groupCallsByFunction(turn.children || []);
            
            // Determine turn severity
            const hasExpensiveCalls = turn.total_cost > 0.5 || turn.total_latency_ms > 10000;
            const turnSeverity = hasExpensiveCalls ? 'bg-red-900/10' : '';
            
            return (
              <div key={turn.turn_number} className={`border border-gray-700 rounded-lg overflow-hidden bg-gray-900 ${turnSeverity}`}>
                {/* Turn header */}
                <div className="bg-gradient-to-r from-gray-800 to-gray-900 px-4 py-3 border-b border-gray-700">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <span className="bg-blue-600 text-white text-xs font-bold px-2 py-1 rounded flex-shrink-0">
                        Turn {turn.turn_number}
                      </span>
                      <span className="text-sm text-gray-300 font-medium truncate">
                        "{displayMessage}"
                      </span>
                      {hasExpensiveCalls && (
                        <span className="flex items-center gap-1 text-xs text-red-400">
                          <Flame className="w-3 h-3" />
                          EXPENSIVE
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-400 flex-shrink-0 ml-4">
                      <span>{turn.total_calls} calls</span>
                      <span>{turnTimeSeconds}s</span>
                      <span>${(turn.total_cost || 0).toFixed(4)}</span>
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
          <div className="flex gap-2 border-b border-gray-700 pb-2">
            <button className="px-4 py-2 rounded-t font-medium bg-blue-600 text-white" disabled>
              This Call Only
            </button>
            <button
              className="px-4 py-2 rounded-t font-medium bg-gray-800 text-gray-300 hover:bg-gray-700"
              onClick={() => {
                window.location.href = `/api/calls/conversations/${trace.root_call.conversation_id}/tree`;
              }}
            >
              Full Conversation ({trace.conversation_turns.length} turns)
            </button>
          </div>
        )}
        
        {/* Column Headers */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2">
          <div className="flex items-center gap-2 text-xs font-medium text-gray-400 uppercase tracking-wide">
            <div className="flex-1 flex items-center gap-2">
              <div className="w-4" />
              <div className="w-4" />
              <div className="w-4" />
              <span>Call Chain</span>
            </div>
            <div className="flex items-center gap-6 flex-shrink-0">
              <span className="w-14 text-center">Calls</span>
              <span className="flex items-center gap-1 w-16 justify-center">
                <Clock className="w-3 h-3" />
                Time
              </span>
              <span className="flex items-center gap-1 w-20 justify-center">
                <DollarSign className="w-3 h-3" />
                Cost
              </span>
              <span className="w-16 text-center">🪙 Tokens</span>
            </div>
          </div>
        </div>
        
        {/* Grouped calls */}
        <div className="border border-gray-700 rounded-lg overflow-hidden bg-gray-900">
          {groups.map((group, idx) => (
            <GroupedCallNode key={idx} group={group} depth={0} />
          ))}
        </div>
      </div>
    );
  }
  
  return <div className="text-gray-500 p-8">Invalid trace data</div>;
}