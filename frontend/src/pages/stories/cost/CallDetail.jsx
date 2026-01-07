/**
 * Cost Story - Layer 3 (Call Detail)
 * 
 * Uses the universal Layer3Shell with cost-specific configuration.
 * Shows cost breakdown, model comparison, and cost optimization fixes.
 */

import { useParams, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useTimeRange } from '../../../context/TimeRangeContext';

import Layer3Shell from '../../../components/stories/Layer3';
import { STORY_THEMES } from '../../../config/theme';
import { BASE_THEME } from '../../../utils/themeUtils';
import { getFixesForCall } from '../../../config/fixes';

import {
  COST_STORY,
  getCostKPIs,
  getCostCurrentState,
  analyzeCostFactors,
  getCostBreakdown,
  getAlternativeModels,
  getCostFixes,
  getCostConfigHighlights,
} from '../../../config/layer3/cost';

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
    
    // Cost metrics
    total_cost: data.total_cost || 0,
    prompt_cost: data.prompt_cost,
    completion_cost: data.completion_cost,
    
    // Token metrics
    prompt_tokens: data.prompt_tokens || 0,
    completion_tokens: data.completion_tokens || 0,
    system_prompt_tokens: data.system_prompt_tokens || 0,
    user_message_tokens: data.user_message_tokens || 0,
    chat_history_tokens: data.chat_history_tokens || 0,
    
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

async function fetchSimilarCalls(call, timeRange) {
  try {
    const params = new URLSearchParams({
      operation: call.operation,
      agent: call.agent_name,
      days: String(timeRange || 7),
      limit: '20',
    });
    const response = await fetch(`/api/calls?${params}`);
    if (!response.ok) {
      return { items: [], stats: null };
    }
    const data = await response.json();
    
    // Calculate operation stats
    const calls = data.calls || [];
    const costs = calls.map(c => c.total_cost || 0);
    const totalCost = costs.reduce((a, b) => a + b, 0);
    const avgCost = costs.length ? totalCost / costs.length : 0;
    const maxCost = costs.length > 0 ? Math.max(...costs) : 0;
    
    // Transform to match our component expectations
    const items = calls.map(c => ({
      id: c.call_id || c.id,
      call_id: c.call_id || c.id,
      timestamp: c.timestamp,
      cost: c.total_cost || 0,
      tokens: (c.prompt_tokens || 0) + (c.completion_tokens || 0),
      model: c.model_name || '—',
      current: (c.call_id || c.id) === call.call_id,
      hasIssue: (c.total_cost || 0) > avgCost * 1.5,
    }));
    
    return {
      items,
      stats: {
        avg_cost: avgCost,
        total_cost: totalCost,
        total_calls: calls.length,
        max_cost: maxCost,
      },
    };
  } catch (err) {
    console.error('Failed to fetch similar calls:', err);
    return { items: [], stats: null };
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// COST BREAKDOWN VISUALIZATION
// ─────────────────────────────────────────────────────────────────────────────

function CostBreakdownBar({ breakdown }) {
  // Map field names from config to what we expect
  // Config returns: prompt, completion, total, promptPct, completionPct
  const { 
    prompt = 0,           // prompt cost
    completion = 0,       // completion cost
    total = 0,            // total cost
    promptPct = 50,       // prompt percentage
    completionPct = 50,   // completion percentage
  } = breakdown || {};
  
  return (
    <div className="space-y-4">
      {/* Cost Bar */}
      <div>
        <div className="h-10 bg-gray-700 rounded-full overflow-hidden flex">
          <div 
            className="bg-blue-500 flex items-center justify-center text-sm text-white font-medium"
            style={{ width: `${promptPct}%` }}
          >
            {promptPct > 20 && `Input $${prompt.toFixed(3)}`}
          </div>
          <div 
            className="bg-purple-500 flex items-center justify-center text-sm text-white font-medium"
            style={{ width: `${completionPct}%` }}
          >
            {completionPct > 20 && `Output $${completion.toFixed(3)}`}
          </div>
        </div>
      </div>
      
      {/* Legend */}
      <div className="flex gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-blue-500 rounded" />
          <span className="text-gray-400">
            Input: ${prompt.toFixed(3)} ({promptPct.toFixed(0)}%)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-purple-500 rounded" />
          <span className="text-gray-400">
            Output: ${completion.toFixed(3)} ({completionPct.toFixed(0)}%)
          </span>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ALTERNATIVE MODELS COMPARISON
// ─────────────────────────────────────────────────────────────────────────────

function AlternativeModelsTable({ currentModel, currentCost, alternatives }) {
  if (!alternatives || alternatives.length === 0) {
    return (
      <div className="text-gray-500 text-sm">
        No cheaper alternatives available for this task.
      </div>
    );
  }
  
  return (
    <div className={`${BASE_THEME.container.secondary} rounded-lg overflow-hidden`}>
      <table className="w-full text-sm">
        <thead className="bg-gray-800">
          <tr>
            <th className="text-left py-3 px-4 text-gray-400 font-medium">Model</th>
            <th className="text-right py-3 px-4 text-gray-400 font-medium">Input/1K</th>
            <th className="text-right py-3 px-4 text-gray-400 font-medium">Output/1K</th>
            <th className="text-right py-3 px-4 text-gray-400 font-medium">Est. Cost</th>
            <th className="text-right py-3 px-4 text-gray-400 font-medium">Savings</th>
            <th className="text-right py-3 px-4 text-gray-400 font-medium">Quality</th>
          </tr>
        </thead>
        <tbody>
          {/* Current model row */}
          <tr className="bg-amber-900/10 border-b border-gray-700">
            <td className="py-3 px-4 text-amber-400 font-medium">{currentModel} (current)</td>
            <td className="py-3 px-4 text-right text-gray-300">—</td>
            <td className="py-3 px-4 text-right text-gray-300">—</td>
            <td className="py-3 px-4 text-right font-medium text-gray-200">${(currentCost || 0).toFixed(3)}</td>
            <td className="py-3 px-4 text-right text-gray-500">—</td>
            <td className="py-3 px-4 text-right text-gray-300">100%</td>
          </tr>
          
          {/* Alternative models */}
          {alternatives.map((alt) => (
            <tr 
              key={alt.name} 
              className="border-b border-gray-700 hover:bg-gray-800/50 cursor-pointer"
            >
              <td className="py-3 px-4 text-gray-300">{alt.name}</td>
              <td className="py-3 px-4 text-right text-green-400">${alt.input_price}</td>
              <td className="py-3 px-4 text-right text-green-400">${alt.output_price}</td>
              <td className="py-3 px-4 text-right font-medium text-green-400">
                ${(alt.estimated_cost || 0).toFixed(4)}
              </td>
              <td className="py-3 px-4 text-right text-green-400 font-medium">
                -{(alt.savings_pct || 0).toFixed(0)}%
              </td>
              <td className="py-3 px-4 text-right text-yellow-400">{alt.quality}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

export default function CostCallDetail() {
  const { callId } = useParams();
  const navigate = useNavigate();
  const { timeRange } = useTimeRange();
  const [call, setCall] = useState(null);
  const [similarData, setSimilarData] = useState({ items: [], stats: null });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const callData = await fetchCallData(callId);
        setCall(callData);
        
        const similar = await fetchSimilarCalls(callData, timeRange);
        setSimilarData(similar);
      } catch (err) {
        console.error('Failed to load call data:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [callId, timeRange]);

  if (loading || !call) {
    return (
      <Layer3Shell
        storyId={COST_STORY.id}
        storyLabel={COST_STORY.label}
        storyIcon={COST_STORY.icon}
        theme={STORY_THEMES.cost}
        loading={true}
      />
    );
  }

  // Analyze the call
  const factors = analyzeCostFactors(call, similarData.stats);
  const breakdown = getCostBreakdown(call) || {
    prompt: 0,
    completion: 0,
    total: call.total_cost || 0,
    promptPct: 50,
    completionPct: 50,
    pricing: null,
  };
  const alternatives = getAlternativeModels(call);
  const fixes = getFixesForCall(call, 'cost', factors);
  const configHighlights = getCostConfigHighlights(call, factors);
  const currentState = getCostCurrentState(call);
  
  // Check if healthy
  const isHealthy = factors.length === 0 || factors.every(f => f.severity === 'info' || f.severity === 'ok');

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
      storyId={COST_STORY.id}
      storyLabel={COST_STORY.label}
      storyIcon={COST_STORY.icon}
      theme={STORY_THEMES.cost}
      
      // Entity info
      entityId={call.call_id}
      entityType="call"
      entityLabel={`${call.agent_name}.${call.operation}`}
      entitySubLabel={call.timestamp}
      entityMeta={`${call.provider} / ${call.model_name}`}
      
      // Navigation
      backPath={`/stories/cost/operations/${call.agent_name}/${call.operation}`}
      backLabel={`Back to ${call.operation}`}
      
      // KPIs
      kpis={getCostKPIs(call, operationStats)}
      
      // Current state for Fix comparison table
      currentState={currentState}
      
      // Response text for OUTPUT CHANGE section
      responseText={call.response_text}
      
      // Diagnose panel
      diagnoseProps={{
        factors,
        isHealthy,
        healthyMessage: `This call cost $${(call.total_cost || 0).toFixed(3)} which is within normal range for this operation.`,
        breakdownTitle: '📊 Cost Breakdown',
        breakdownComponent: (
          <CostBreakdownBar breakdown={breakdown} />
        ),
        breakdownSubtext: `${(breakdown.promptPct || 0).toFixed(0)}% input, ${(breakdown.completionPct || 0).toFixed(0)}% output`,
        additionalBreakdown: alternatives.length > 0 ? (
          <AlternativeModelsTable 
            currentModel={call.model_name}
            currentCost={call.total_cost}
            alternatives={alternatives}
          />
        ) : null,
        additionalBreakdownTitle: alternatives.length > 0 ? '🔄 Alternative Models' : null,
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
          system: call.system_prompt_tokens,
          user: call.user_message_tokens,
          history: call.chat_history_tokens,
          total: call.prompt_tokens,
        },
        // Cost-specific attributes
        costMetrics: {
          total_cost: call.total_cost,
          prompt_cost: breakdown.prompt,
          completion_cost: breakdown.completion,
          pricing: breakdown.pricing,
        },
      }}
      
      // Similar panel
      similarProps={{
        groupOptions: [
          { id: 'operation', label: 'Same Operation', filterFn: null },
          { id: 'expensive', label: 'Expensive', filterFn: (items) => items.filter(i => i.hasIssue) },
          { id: 'cheap', label: 'Low Cost', filterFn: (items) => items.filter(i => !i.hasIssue) },
        ],
        defaultGroup: 'operation',
        items: similarCalls,
        currentItemId: call.call_id,
        columns: [
          { key: 'id', label: 'Call ID', format: (v) => v?.substring(0, 8) + '...' },
          { key: 'timestamp', label: 'Timestamp' },
          { key: 'cost', label: 'Cost', format: (v) => `$${(v ?? 0).toFixed(3)}` },
          { key: 'tokens', label: 'Tokens', format: (v) => (v ?? 0).toLocaleString() },
          { key: 'model', label: 'Model' },
        ],
        aggregateStats: [
          { label: 'Total Calls', value: similarCalls.length, color: 'text-amber-400' },
          { label: 'Total Spend', value: `$${(operationStats?.total_cost ?? 0).toFixed(2)}`, color: 'text-amber-400' },
          { label: 'Avg/Call', value: `$${(operationStats?.avg_cost ?? 0).toFixed(3)}`, color: 'text-yellow-400' },
          { label: 'Max Cost', value: `$${(operationStats?.max_cost ?? 0).toFixed(3)}`, color: 'text-red-400' },
        ],
        issueKey: 'hasIssue',
        issueLabel: 'High',
        okLabel: 'Normal',
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
        },
        // Cost-specific raw data
        costDetails: {
          total_cost: call.total_cost,
          prompt_cost: breakdown.prompt,
          completion_cost: breakdown.completion,
          pricing: breakdown.pricing,
        },
        fullData: call,
      }}
      
      // Fixes
      fixes={fixes}
    />
  );
}