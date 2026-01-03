/**
 * RoutingTraceView - Shows routing decisions across conversation with vibrant colors
 * DESIGN 1: Clean Minimal (No Glows, Flat Backgrounds)
 */

import { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, CheckCircle, AlertTriangle, Flame, Lightbulb } from 'lucide-react';

// Design 1: Clean Minimal - Flat backgrounds, no glows
const ROUTING_COLORS = {
  optimal: {
    border: 'border-l-4 border-green-500',
    bg: 'bg-gray-800',
    text: 'text-green-400',
    badge: 'bg-green-500/10 border border-green-500/30',
    icon: '✓',
    label: 'OPTIMAL',
  },
  overprovisioned: {
    border: 'border-l-4 border-cyan-500',
    bg: 'bg-gray-800',
    text: 'text-cyan-400',
    badge: 'bg-cyan-500/10 border border-cyan-500/30',
    icon: '▼',
    label: 'OVERPROVISIONED',
  },
  underprovisioned: {
    border: 'border-l-4 border-pink-500',
    bg: 'bg-gray-800',
    text: 'text-pink-400',
    badge: 'bg-pink-500/10 border border-pink-500/30',
    icon: '⚠️',
    label: 'UNDERPROVISIONED',
  },
};

// ============================================================================
// Helper function to group calls by operation
// ============================================================================

function groupCallsByFunction(calls) {
  const groups = {};
  
  calls.forEach(call => {
    const key = `${call.agent_name}_${call.operation}`;
    
    if (!groups[key]) {
      groups[key] = {
        agent_name: call.agent_name,
        operation: call.operation,
        model: call.model,
        calls: [],
        total_latency: 0,
        total_cost: 0,
      };
    }
    
    groups[key].calls.push({
      call_id: call.call_id,
      latency: call.latency_ms,
      cost: call.total_cost,
      complexity: call.complexity_score,
      quality: call.judge_score,
      routing_verdict: call.routing_analysis?.verdict,
      model: call.model_name,
    });
    
    groups[key].total_latency += call.latency_ms || 0;
    groups[key].total_cost += call.total_cost || 0;
  });
  
  return Object.values(groups);
}

// ============================================================================
// GROUP NODE - Shows aggregated calls with routing verdict
// ============================================================================

function GroupNode({ group, depth = 0 }) {
  const [expanded, setExpanded] = useState(false);
  
  const indent = depth * 24;
  const count = group.calls.length;
  
  // Determine group verdict (worst case from all calls)
  const hasUnder = group.calls.some(c => c.routing_verdict === 'underprovisioned');
  const hasOver = group.calls.some(c => c.routing_verdict === 'overprovisioned');
  const verdict = hasUnder ? 'underprovisioned' : hasOver ? 'overprovisioned' : 'optimal';
  
  const colors = ROUTING_COLORS[verdict];
  
  // Calculate metrics
  const avgComplexity = (group.calls.reduce((sum, c) => sum + (c.complexity || 0), 0) / count).toFixed(2);
  const avgQuality = group.calls[0]?.quality || 0;
  const totalCost = group.total_cost.toFixed(4);
  const totalTime = (group.total_latency / 1000).toFixed(1);
  
  return (
    <div className="font-mono text-sm">
      {/* Group Header */}
      <div
        className={`
          flex items-center gap-2 py-3 px-3
          ${colors.border} ${colors.bg}
          hover:bg-gray-750 cursor-pointer transition-colors
          border-r border-gray-700
        `}
        style={{ paddingLeft: `${indent + 12}px` }}
        onClick={() => setExpanded(!expanded)}
      >
        {/* Expand/Collapse */}
        {count > 1 ? (
          expanded ? (
            <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
          )
        ) : (
          <div className="w-4 h-4 flex-shrink-0" />
        )}
        
        {/* Verdict Icon */}
        <span className={`text-xl ${colors.text}`}>{colors.icon}</span>
        
        {/* Agent & Operation */}
        <span className="font-semibold text-purple-400">{group.agent_name}</span>
        <span className="text-gray-500">→</span>
        <span className="text-gray-300">{group.operation}</span>
        
        {/* Count Badge */}
        {count > 1 && (
          <span className={`ml-2 px-2 py-0.5 text-xs rounded ${colors.badge} ${colors.text}`}>
            ×{count}
          </span>
        )}
        
        {/* Verdict Badge */}
        <span className={`ml-2 px-2 py-0.5 text-xs rounded ${colors.badge} ${colors.text}`}>
          {colors.label}
        </span>
        
        {/* Metrics (right-aligned) */}
        <div className="ml-auto flex items-center gap-6 text-xs text-gray-400 flex-shrink-0">
          <span className="w-16 text-right" title="Total Time">{totalTime}s</span>
          <span className="w-20 text-right" title="Total Cost">${totalCost}</span>
          <span className="w-16 text-center" title="Avg Complexity">{avgComplexity}</span>
          <span className="w-16 text-center" title="Quality">{avgQuality.toFixed(1)}/10</span>
        </div>
      </div>
      
      {/* Routing Analysis Details */}
      <div className="ml-12 mr-3 mt-2 mb-2 p-3 rounded bg-gray-800 border border-gray-700 text-sm" style={{ marginLeft: `${indent + 48}px` }}>
        <div className="flex items-start gap-2">
          <Lightbulb className={`w-4 h-4 flex-shrink-0 mt-0.5 ${colors.text}`} />
          <div className="flex-1">
            {/* Reasoning */}
            <div className={`${colors.text} font-medium mb-1`}>
              {verdict === 'optimal' && `Model: ${group.calls[0]?.model || 'unknown'} - Well-matched for this task`}
              {verdict === 'overprovisioned' && `Could downgrade to gpt-3.5-turbo • Save ~90% on these ${count} calls`}
              {verdict === 'underprovisioned' && `Should upgrade to gpt-4o • Improve quality by ~15%`}
            </div>
            {/* Metrics */}
            <div className="text-gray-400 text-xs">
              Complexity: {avgComplexity} • Quality: {avgQuality.toFixed(1)}/10 • 
              {verdict === 'overprovisioned' && ` Potential savings: $${(group.total_cost * 0.9).toFixed(4)}`}
              {verdict === 'underprovisioned' && ` Additional cost: $${(group.total_cost * 1.5).toFixed(4)}`}
              {verdict === 'optimal' && ' No action needed'}
            </div>
          </div>
        </div>
      </div>
      
      {/* Individual Calls (Expanded) */}
      {expanded && count > 1 && (
        <div className="ml-6" style={{ marginLeft: `${indent + 24}px` }}>
          {group.calls.map((call, idx) => (
            <div key={call.call_id || idx} className="flex items-center gap-2 py-2 px-3 text-xs text-gray-400">
              <span className="text-gray-600 w-6">#{idx + 1}</span>
              <CheckCircle className="w-3 h-3 text-green-500 flex-shrink-0" />
              <span className="text-gray-500 flex-1">{call.call_id?.substring(0, 8)}...</span>
              <div className="flex items-center gap-6 flex-shrink-0">
                <span className="w-16 text-right">{((call.latency || 0) / 1000).toFixed(1)}s</span>
                <span className="w-20 text-right">${(call.cost || 0).toFixed(4)}</span>
                <span className="w-16 text-center">{(call.complexity || 0).toFixed(2)}</span>
                <span className="w-16 text-center">{call.quality?.toFixed(1) || '—'}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// MAIN ROUTING TRACE VIEW
// ============================================================================

export default function RoutingTraceView({ conversationId }) {
  const [trace, setTrace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    fetchTrace();
  }, [conversationId]);
  
  const fetchTrace = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/calls/conversations/${conversationId}/routing-trace`);
      if (!response.ok) throw new Error('Failed to fetch routing trace');
      const data = await response.json();
      setTrace(data);
    } catch (err) {
      console.error('Error fetching routing trace:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600" />
        <span className="ml-3 text-gray-400">Loading routing trace...</span>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="bg-pink-900/20 border border-pink-700 rounded-lg p-4">
        <div className="flex items-center gap-2 text-pink-400">
          <AlertTriangle className="w-5 h-5" />
          <span className="font-semibold">Failed to load routing trace</span>
        </div>
        <p className="mt-2 text-sm text-pink-300">{error}</p>
      </div>
    );
  }
  
  if (!trace) return null;
  
  const { summary, turns } = trace;
  
  return (
    <div className="space-y-6">
      
      {/* Conversation Routing Summary */}
      <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-4">
          📊 Conversation Routing Summary
        </h3>
        <div className="grid grid-cols-4 gap-6">
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Turns</div>
            <div className="text-2xl font-bold text-purple-400">{summary?.total_turns || 0}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Model Used</div>
            <div className="text-2xl font-bold text-cyan-400">{summary?.model || 'gpt-4o-mini'}</div>
            <div className="text-xs text-gray-500 mt-1">{summary?.routing_type || 'Static'}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Routing Score</div>
            <div className="text-2xl font-bold text-green-400">{summary?.routing_score || 0}%</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Opportunities</div>
            <div className="text-2xl font-bold text-pink-400">{summary?.opportunity_count || 0} calls</div>
          </div>
        </div>
      </div>
      
      {/* Column Headers */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2">
        <div className="flex items-center gap-2 text-xs font-medium text-gray-400 uppercase tracking-wide">
          <div className="flex-1 flex items-center gap-2">
            <div className="w-4" />
            <div className="w-4" />
            <span>Call Chain</span>
          </div>
          <div className="flex items-center gap-6 flex-shrink-0">
            <span className="w-16 text-right">Time</span>
            <span className="w-20 text-right">Cost</span>
            <span className="w-16 text-center">Complexity</span>
            <span className="w-16 text-center">Quality</span>
          </div>
        </div>
      </div>
      
      {/* Turns with Grouped Calls */}
      <div className="space-y-4">
        {turns && turns.map((turn) => {
          // Group calls by operation
          const groups = groupCallsByFunction(turn.calls || []);
          
          // Count opportunities
          const opportunities = turn.calls?.filter(c => c.routing_analysis?.verdict !== 'optimal').length || 0;
          
          return (
            <div key={turn.turn_number} className="border border-gray-700 rounded-lg overflow-hidden bg-gray-900">
              {/* Turn Header */}
              <div className="bg-gray-800 px-4 py-3 border-b border-gray-700">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <span className="bg-purple-600 text-white text-xs font-bold px-2 py-1 rounded flex-shrink-0">
                      Turn {turn.turn_number}
                    </span>
                    <span className="text-sm text-gray-300 font-medium truncate">
                      "{turn.user_message || 'No message'}"
                    </span>
                    {opportunities > 0 && (
                      <span className="flex items-center gap-1 text-xs text-pink-400">
                        <Flame className="w-3 h-3" />
                        {opportunities} opportunities
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-400 flex-shrink-0 ml-4">
                    <span>{turn.total_calls || 0} calls</span>
                    <span>{((turn.total_latency || 0) / 1000).toFixed(1)}s</span>
                    <span>${(turn.total_cost || 0).toFixed(4)}</span>
                  </div>
                </div>
              </div>
              
              {/* Grouped Calls */}
              <div>
                {groups.map((group, idx) => (
                  <GroupNode key={`${group.agent_name}-${group.operation}-${idx}`} group={group} depth={0} />
                ))}
              </div>
            </div>
          );
        })}
      </div>
      
      {/* Routing Insights */}
      {summary?.insights && summary.insights.length > 0 && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-5">
          <div className="flex items-start gap-3">
            <span className="text-3xl">💡</span>
            <div className="flex-1">
              <div className="text-purple-400 font-bold text-lg mb-2">Routing Insights</div>
              <div className="space-y-2">
                {summary.insights.map((insight, idx) => (
                  <div key={idx} className="text-gray-300 text-sm">• {insight}</div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Legend */}
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-4">
        <div className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-3">Legend</div>
        <div className="grid grid-cols-3 gap-4 text-sm">
          {Object.entries(ROUTING_COLORS).map(([key, colors]) => (
            <div key={key} className="flex items-center gap-2">
              <div className={`w-4 h-4 rounded bg-gray-800 ${colors.border}`} />
              <span className={colors.text}>{colors.icon} {colors.label}</span>
            </div>
          ))}
        </div>
      </div>
      
    </div>
  );
}