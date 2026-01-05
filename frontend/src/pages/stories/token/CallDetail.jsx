/**
 * Token Imbalance Story - Layer 3 (Call Detail)
 * 
 * Uses the universal Layer3Shell with token-specific configuration.
 * Shows token breakdown visualization and efficiency fixes.
 */

import { useParams, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';

import Layer3Shell from '../../../components/stories/Layer3';
import { STORY_THEMES } from '../../../config/theme';
import { getFixesForCall } from '../../../config/fixes';

import {
  TOKEN_STORY,
  getTokenKPIs,
  getTokenCurrentState,
  analyzeTokenFactors,
  getTokenBreakdown,
  getTokenFixes,
  getTokenConfigHighlights,
} from '../../../config/layer3/token';

// ─────────────────────────────────────────────────────────────────────────────
// DATA FETCHING
// ─────────────────────────────────────────────────────────────────────────────

async function fetchCallData(callId) {
  const response = await fetch(`/api/calls/${callId}`);
  if (!response.ok) {
    throw new Error(`Call not found: ${callId}`);
  }
  const data = await response.json();
  
  // Normalize the response to match our component expectations
  return {
    call_id: data.call_id || data.id,
    agent_name: data.agent_name || 'Unknown',
    operation: data.operation || 'unknown',
    timestamp: data.timestamp,
    provider: data.provider || 'openai',
    model_name: data.model_name || 'gpt-4o',
    
    // Token metrics
    prompt_tokens: data.prompt_tokens || 0,
    completion_tokens: data.completion_tokens || 0,
    system_prompt_tokens: data.system_prompt_tokens || 0,
    user_message_tokens: data.user_message_tokens || 0,
    chat_history_tokens: data.chat_history_tokens || 0,
    
    // Cost
    total_cost: data.total_cost || 0,
    prompt_cost: data.prompt_cost,
    completion_cost: data.completion_cost,
    
    // Timing
    latency_ms: data.latency_ms || 0,
    
    // Model config
    temperature: data.temperature,
    max_tokens: data.max_tokens,
    
    // Content
    response_text: data.response_text || data.response || '',
    system_prompt: data.system_prompt || '',
    user_message: data.user_message || '',
  };
}

async function fetchSimilarCalls(call) {
  try {
    const params = new URLSearchParams({
      operation: call.operation,
      agent: call.agent_name,
      days: '7',
      limit: '20',
    });
    const response = await fetch(`/api/calls?${params}`);
    if (!response.ok) {
      return { items: [], stats: null };
    }
    const data = await response.json();
    
    // Calculate operation stats
    const calls = data.calls || [];
    const ratios = calls.map(c => {
      if (!c.completion_tokens) return null;
      return c.prompt_tokens / c.completion_tokens;
    }).filter(r => r != null && r !== Infinity);
    
    const avgRatio = ratios.length ? ratios.reduce((a, b) => a + b, 0) / ratios.length : null;
    const severeCount = ratios.filter(r => r > 20).length;
    const balancedCount = ratios.filter(r => r <= 5).length;
    
    // Transform to match our component expectations
    const items = calls.map(c => {
      const ratio = c.completion_tokens ? (c.prompt_tokens / c.completion_tokens) : Infinity;
      return {
        id: c.call_id || c.id,
        call_id: c.call_id || c.id,
        timestamp: c.timestamp,
        prompt_tokens: c.prompt_tokens,
        completion_tokens: c.completion_tokens,
        ratio: ratio === Infinity ? '∞' : ratio.toFixed(0),
        cost: c.total_cost || 0,
        current: (c.call_id || c.id) === call.call_id,
        hasIssue: ratio > 20,
      };
    });
    
    return {
      items,
      stats: {
        avg_ratio: avgRatio,
        total_calls: calls.length,
        severe_count: severeCount,
        balanced_count: balancedCount,
      },
    };
  } catch (err) {
    console.error('Failed to fetch similar calls:', err);
    return { items: [], stats: null };
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// TOKEN BREAKDOWN VISUALIZATION
// ─────────────────────────────────────────────────────────────────────────────

function TokenBreakdownBar({ breakdown }) {
  const { system, systemPct, user, userPct, history, historyPct, total, completion } = breakdown;
  
  // Calculate output bar width relative to input
  const outputPct = total > 0 ? (completion / total) * 100 : 0;
  
  return (
    <div className="space-y-4">
      {/* Input Tokens Bar */}
      <div>
        <div className="text-xs text-gray-500 mb-2">
          Input Tokens ({total.toLocaleString()})
        </div>
        <div className="h-8 bg-gray-700 rounded-full overflow-hidden flex">
          {systemPct > 0 && (
            <div 
              className="bg-purple-500 flex items-center justify-center text-xs text-white"
              style={{ width: `${systemPct}%` }}
            >
              {systemPct > 15 && 'System'}
            </div>
          )}
          {userPct > 0 && (
            <div 
              className="bg-blue-500 flex items-center justify-center text-xs text-white"
              style={{ width: `${userPct}%` }}
            >
              {userPct > 15 && 'User'}
            </div>
          )}
          {historyPct > 0 && (
            <div 
              className="bg-orange-500 flex items-center justify-center text-xs text-white"
              style={{ width: `${historyPct}%` }}
            >
              {historyPct > 15 && 'History'}
            </div>
          )}
        </div>
      </div>
      
      {/* Output Tokens Bar */}
      <div>
        <div className="text-xs text-gray-500 mb-2">
          Output Tokens ({completion.toLocaleString()})
        </div>
        <div className="h-8 bg-gray-700 rounded-full overflow-hidden">
          <div 
            className="bg-green-500 h-full flex items-center justify-center text-xs text-white"
            style={{ width: `${Math.min(outputPct, 100)}%`, minWidth: completion > 0 ? '40px' : '0' }}
          >
            {completion > 0 && completion.toLocaleString()}
          </div>
        </div>
      </div>
      
      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs pt-2">
        {system > 0 && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-purple-500 rounded" />
            <span className="text-gray-400">
              System: {system.toLocaleString()} ({systemPct.toFixed(0)}%)
            </span>
          </div>
        )}
        {user > 0 && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-blue-500 rounded" />
            <span className="text-gray-400">
              User: {user.toLocaleString()} ({userPct.toFixed(0)}%)
            </span>
          </div>
        )}
        {history > 0 && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-orange-500 rounded" />
            <span className="text-gray-400">
              History: {history.toLocaleString()} ({historyPct.toFixed(0)}%)
            </span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 rounded" />
          <span className="text-gray-400">
            Output: {completion.toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// COST IMPACT SECTION
// ─────────────────────────────────────────────────────────────────────────────

function CostImpactSection({ call, breakdown }) {
  const promptCost = call.prompt_cost || (call.total_cost * (call.prompt_tokens / (call.prompt_tokens + call.completion_tokens)));
  const completionCost = call.completion_cost || (call.total_cost - promptCost);
  const inputPct = (promptCost / call.total_cost) * 100;
  
  return (
    <div className="bg-gray-900 rounded-lg p-4">
      <div className="grid grid-cols-3 gap-4 text-center">
        <div>
          <div className="text-2xl font-bold text-red-400">${promptCost.toFixed(3)}</div>
          <div className="text-xs text-gray-500">Input Cost ({inputPct.toFixed(0)}%)</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-green-400">${completionCost.toFixed(3)}</div>
          <div className="text-xs text-gray-500">Output Cost ({(100 - inputPct).toFixed(0)}%)</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-pink-400">${call.total_cost.toFixed(3)}</div>
          <div className="text-xs text-gray-500">Total Cost</div>
        </div>
      </div>
      
      {inputPct > 80 && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <p className="text-sm text-gray-400">
            <span className="text-red-400 font-medium">{inputPct.toFixed(0)}% of cost</span> is from input tokens. 
            {breakdown.systemPct > 50 && (
              <span> Reducing system prompt by 50% would save <span className="text-green-400 font-medium">${(promptCost * 0.5 * (breakdown.systemPct / 100)).toFixed(3)}/call</span>.</span>
            )}
          </p>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

export default function TokenCallDetail() {
  const { callId } = useParams();
  const navigate = useNavigate();
  const [call, setCall] = useState(null);
  const [similarData, setSimilarData] = useState({ items: [], stats: null });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const callData = await fetchCallData(callId);
        setCall(callData);
        
        const similar = await fetchSimilarCalls(callData);
        setSimilarData(similar);
      } catch (err) {
        console.error('Failed to load call data:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [callId]);

  if (loading || !call) {
    return (
      <Layer3Shell
        storyId={TOKEN_STORY.id}
        storyLabel={TOKEN_STORY.label}
        storyIcon={TOKEN_STORY.icon}
        theme={STORY_THEMES.token_imbalance}
        loading={true}
      />
    );
  }

  // Analyze the call
  const factors = analyzeTokenFactors(call);
  const breakdown = getTokenBreakdown(call);
  const fixes = getFixesForCall(call, 'token', factors);
  const configHighlights = getTokenConfigHighlights(call, factors);
  const currentState = getTokenCurrentState(call);
  
  // Check if healthy
  const isHealthy = factors.length === 0 || factors.every(f => f.severity === 'info' || f.severity === 'ok');
  
  // Calculate ratio for display
  const ratio = call.completion_tokens > 0 
    ? (call.prompt_tokens / call.completion_tokens).toFixed(0) 
    : '∞';

  // Build model config
  const modelConfig = {
    provider: call.provider,
    model: call.model_name,
    temperature: call.temperature,
    max_tokens: call.max_tokens,
  };

  // Build metadata for Raw tab
  const metadata = {
    call_id: call.call_id,
    agent: call.agent_name,
    operation: call.operation,
    timestamp: call.timestamp,
    provider: call.provider,
    model: call.model_name,
  };

  // Build similar items with operation stats
  const { items: similarCalls, stats: operationStats } = similarData;

  return (
    <Layer3Shell
      // Story config
      storyId={TOKEN_STORY.id}
      storyLabel={TOKEN_STORY.label}
      storyIcon={TOKEN_STORY.icon}
      theme={STORY_THEMES.token_imbalance}
      
      // Entity info
      entityId={call.call_id}
      entityType="call"
      entityLabel={`${call.agent_name}.${call.operation}`}
      entitySubLabel={call.timestamp}
      entityMeta={`${call.provider} / ${call.model_name}`}
      
      // Navigation
      backPath={`/stories/token_imbalance/operations/${call.agent_name}/${call.operation}`}
      backLabel={`Back to ${call.operation}`}
      
      // KPIs
      kpis={getTokenKPIs(call, operationStats)}
      
      // Current state for Fix comparison table
      currentState={currentState}
      
      // Response text for OUTPUT CHANGE section
      responseText={call.response_text}
      
      // Diagnose panel
      diagnoseProps={{
        factors,
        isHealthy,
        healthyMessage: `This call has a ${ratio}:1 token ratio which is within acceptable range.`,
        breakdownTitle: '📊 Token Distribution',
        breakdownComponent: (
          <TokenBreakdownBar breakdown={breakdown} />
        ),
        breakdownSubtext: `Ratio: ${ratio}:1 (input:output)`,
        additionalBreakdown: (
          <CostImpactSection call={call} breakdown={breakdown} />
        ),
        additionalBreakdownTitle: '💰 Cost Impact',
      }}
      
      // Attribute panel
      attributeProps={{
        modelConfig,
        configHighlights,
        responseAnalysis: {
          type: call.response_text?.trim().startsWith('{') ? 'json' : 
                call.response_text?.includes('```') ? 'code' : 
                /^##?\s/m.test(call.response_text || '') ? 'markdown' : 'prose',
          tokenCount: call.completion_tokens,
        },
        promptBreakdown: {
          system: breakdown.system,
          user: breakdown.user,
          history: breakdown.history,
          total: breakdown.total,
        },
        // Token-specific attributes
        tokenMetrics: {
          ratio: ratio,
          prompt_tokens: call.prompt_tokens,
          completion_tokens: call.completion_tokens,
        },
      }}
      
      // Similar panel
      similarProps={{
        groupOptions: [
          { id: 'operation', label: 'Same Operation', filterFn: null },
          { id: 'severe', label: 'Severe (>20:1)', filterFn: (items) => items.filter(i => parseFloat(i.ratio) > 20) },
          { id: 'balanced', label: 'Balanced (<5:1)', filterFn: (items) => items.filter(i => parseFloat(i.ratio) <= 5) },
        ],
        defaultGroup: 'operation',
        items: similarCalls,
        currentItemId: call.call_id,
        columns: [
          { key: 'id', label: 'Call ID', format: (v) => v?.substring(0, 8) + '...' },
          { key: 'timestamp', label: 'Timestamp' },
          { key: 'prompt_tokens', label: 'Prompt', format: (v) => v?.toLocaleString() },
          { key: 'completion_tokens', label: 'Completion', format: (v) => v?.toLocaleString() },
          { key: 'ratio', label: 'Ratio', format: (v) => `${v}:1` },
        ],
        aggregateStats: [
          { label: 'Total Calls', value: similarCalls.length, color: 'text-pink-400' },
          { label: 'Avg Ratio', value: operationStats?.avg_ratio ? `${operationStats.avg_ratio.toFixed(0)}:1` : '—', color: 'text-pink-400' },
          { label: 'Severe (>20:1)', value: operationStats?.severe_count || 0, color: 'text-red-400' },
          { label: 'Balanced (<5:1)', value: operationStats?.balanced_count || 0, color: 'text-green-400' },
        ],
        issueKey: 'hasIssue',
        issueLabel: 'Severe',
        okLabel: 'OK',
      }}
      
      // Raw panel
      rawProps={{
        metadata,
        systemPrompt: call.system_prompt,
        systemPromptTokens: call.system_prompt_tokens,
        userMessage: call.user_message,
        userMessageTokens: call.user_message_tokens,
        response: call.response_text,
        responseTokens: call.completion_tokens,
        modelConfig,
        tokenBreakdown: {
          prompt_tokens: call.prompt_tokens,
          completion_tokens: call.completion_tokens,
          total_tokens: call.prompt_tokens + call.completion_tokens,
          ratio: `${ratio}:1`,
          breakdown: {
            system_prompt_tokens: breakdown.system,
            user_message_tokens: breakdown.user,
            chat_history_tokens: breakdown.history,
          },
        },
        fullData: call,
      }}
      
      // Fixes
      fixes={fixes}
    />
  );
}