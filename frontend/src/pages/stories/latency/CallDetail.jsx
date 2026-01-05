/**
 * Latency Story - Layer 3 (Call Detail)
 * 
 * Complete implementation with:
 * - Time Attribution Tree
 * - Chat History Breakdown
 * - Comparison Benchmarks
 * - Root Causes Table
 * - All existing features preserved
 */

import { useParams, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { getFixesForCall } from '../../../config/fixes';

import Layer3Shell from '../../../components/stories/Layer3';

import { STORY_THEMES } from '../../../config/theme';
import {
  LATENCY_STORY,
  getLatencyKPIs,
  getLatencyCurrentState,
  analyzeLatencyFactors,
  getTimeAttribution,
  getLatencyConfigHighlights,
  getLatencyBreakdown,
  analyzeLatencyResponse,
  analyzeLatencyPrompt,
} from '../../../config/layer3/latency';

const theme = STORY_THEMES.latency;

// Fetch call data from API
async function fetchCallData(callId) {
  const response = await fetch(`/api/calls/${callId}`);
  if (!response.ok) {
    throw new Error(`Call not found: ${callId}`);
  }
  const data = await response.json();
  
  return {
    call_id: data.call_id || data.id,
    agent_name: data.agent_name || 'Unknown',
    operation: data.operation || 'unknown',
    timestamp: data.timestamp,
    provider: data.provider || 'openai',
    model_name: data.model_name || 'gpt-4o',
    latency_ms: data.latency_ms || 0,
    ttft_ms: data.time_to_first_token_ms || data.ttft_ms || null,
    prompt_tokens: data.prompt_tokens || 0,
    completion_tokens: data.completion_tokens || 0,
    total_cost: data.total_cost || 0,
    temperature: data.temperature,
    max_tokens: data.max_tokens,
    streaming: data.streaming_metrics?.is_streaming || false,
    system_prompt_tokens: data.system_prompt_tokens || 0,
    user_message_tokens: data.user_message_tokens || 0,
    chat_history_tokens: data.chat_history_tokens || 0,
    chat_history_count: data.chat_history_count || 0,
    turn_number: data.turn_number || 1,
    response_text: data.response_text || data.response || '',
    system_prompt: data.system_prompt || '',
    user_message: data.user_message || '',
    conversation_id: data.conversation_id || null,  
    conversation_breakdown: data.conversation_breakdown,
    comparison_benchmarks: data.comparison_benchmarks,
  };
}

async function fetchConversationBreakdown(conversationId, turnNumber) {
  if (!conversationId || !turnNumber) return null;
  
  try {
    const response = await fetch(`/api/calls/conversations/${conversationId}/tree`);
    if (!response.ok) return null;
    
    const data = await response.json();
    
    // Find the turn that matches this call's turn number
    const turn = data.turns?.find(t => t.turn_number === turnNumber);
    return turn?.chatHistoryBreakdown || null;
  } catch (err) {
    console.error('Failed to fetch conversation breakdown:', err);
    return null;
  }
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
      return [];
    }
    const data = await response.json();
    
    return (data.calls || []).map(c => ({
      id: c.call_id || c.id,
      call_id: c.call_id || c.id,
      timestamp: c.timestamp,
      latency_ms: c.latency_ms || 0,
      cost: c.total_cost || 0,
      current: (c.call_id || c.id) === call.call_id,
      hasIssue: (c.latency_ms || 0) > 5000 || !c.max_tokens,
      sameTemplate: true,
    }));
  } catch (err) {
    console.error('Failed to fetch similar calls:', err);
    return [];
  }
}

export default function LatencyCallDetail() {
  const { callId } = useParams();
  const navigate = useNavigate();
  const [call, setCall] = useState(null);
  const [similarCalls, setSimilarCalls] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const callData = await fetchCallData(callId);

        // Fetch conversation breakdown with actual content
        const breakdown = await fetchConversationBreakdown(
          callData.conversation_id,
          callData.turn_number
        );
        
        // Override the conversation_breakdown with the one that has content
        if (breakdown) {
          callData.conversation_breakdown = breakdown;
        }
        
        setCall(callData);
        
        const similar = await fetchSimilarCalls(callData);
        setSimilarCalls(similar);
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
        storyId={LATENCY_STORY.id}
        storyLabel={LATENCY_STORY.label}
        storyIcon={LATENCY_STORY.icon}
        theme={theme}
        loading={true}
      />
    );
  }

  // Analyze the call
  const factors = analyzeLatencyFactors(call);
  console.log('🔍 LATENCY FACTORS:', factors);
  const timeAttribution = getTimeAttribution(call);
  const fixes = getFixesForCall(call, 'latency', factors);
  console.log('🔧 GENERATED FIXES:', fixes);
  const configHighlights = getLatencyConfigHighlights(call, factors);
  const currentState = getLatencyCurrentState(call);
  const breakdown = getLatencyBreakdown(call);
  const responseAnalysis = analyzeLatencyResponse(call);
  const promptAnalysis = analyzeLatencyPrompt(call);
  
  // Check if healthy
  const isHealthy = factors.length === 0 || factors.every(f => f.severity === 'info' || f.severity === 'ok');

  // Build model config
  const modelConfig = {
    provider: call.provider,
    model: call.model_name,
    temperature: call.temperature,
    max_tokens: call.max_tokens,
    stream: call.streaming,
  };

  // Build metadata for Raw tab
  const metadata = {
    call_id: call.call_id,
    agent: call.agent_name,
    operation: call.operation,
    timestamp: call.timestamp,
    provider: call.provider,
    model: call.model_name,
    latency_ms: call.latency_ms,
    ttft_ms: call.ttft_ms,
    turn_number: call.turn_number,
    chat_history_count: call.chat_history_count,
  };

  return (
    <Layer3Shell
      // Story config
      storyId={LATENCY_STORY.id}
      storyLabel={LATENCY_STORY.label}
      storyIcon={LATENCY_STORY.icon}
      theme={theme}
      
      // ⭐ NEW: Specify which tabs to show (only 3 tabs)
      visibleTabs={['diagnose', 'trace', 'fix']}
      
      // Entity info
      entityId={call.call_id}
      entityType="call"
      entityLabel={`${call.agent_name}.${call.operation}`}
      entitySubLabel={call.timestamp}
      entityMeta={`${call.provider} / ${call.model_name} / Turn ${call.turn_number}`}
      
      // Navigation
      backPath={`/stories/latency/operations/${call.agent_name}/${call.operation}`}
      backLabel={`Back to ${call.operation}`}
      
      // Queue count
      queueCount={null}
      
      // KPIs
      kpis={getLatencyKPIs(call)}
      
      // Current state for Fix comparison table
      currentState={currentState}
      
      // Diagnose panel (UPDATED - removed chatHistoryBreakdown)
      diagnoseProps={{
        factors,
        isHealthy,
        healthyMessage: `This call completed in ${(call.latency_ms / 1000).toFixed(1)}s with ${call.completion_tokens.toLocaleString()} tokens. No significant optimization opportunities detected.`,
        
        // Time Attribution Tree
        timeAttribution,
        
        
        // Comparison Benchmarks
        comparisonBenchmarks: call.comparison_benchmarks,
      }}
      
      // ⭐ NEW: Trace panel props (chat history + call tree)
      traceProps={{
        callId: call.call_id,
        conversationId: call.conversation_id,
        chatHistoryBreakdown: call.conversation_breakdown,
      }}
      
      // Attribute panel
      attributeProps={{
        modelConfig,
        configHighlights,
        responseAnalysis,
        promptAnalysis,
      }}
      
      // Similar panel
      similarProps={{
        groupOptions: [
          { id: 'operation', label: 'Same Operation', filterFn: null },
          { id: 'template', label: 'Same Template', filterFn: (items) => items.filter(i => i.sameTemplate) },
          { id: 'issue', label: 'Same Issue', filterFn: (items) => items.filter(i => i.hasIssue) },
        ],
        defaultGroup: 'operation',
        items: similarCalls,
        currentItemId: call.call_id,
        columns: [
          { key: 'id', label: 'Call ID', format: (v) => v?.substring(0, 8) + '...' },
          { key: 'timestamp', label: 'Timestamp' },
          { key: 'latency_ms', label: 'Latency', format: (v) => `${(v / 1000).toFixed(2)}s` },
          { key: 'cost', label: 'Cost', format: (v) => `$${v?.toFixed(3)}` },
        ],
        aggregateStats: [
          { label: 'Total Calls', value: similarCalls.length, color: 'text-orange-400' },
          { label: 'Total Cost', value: `$${similarCalls.reduce((sum, c) => sum + c.cost, 0).toFixed(2)}`, color: 'text-yellow-400' },
          { label: 'With Issue', value: similarCalls.filter(c => c.hasIssue).length, color: 'text-red-400' },
          { label: 'Avg Latency', value: `${(similarCalls.reduce((sum, c) => sum + c.latency_ms, 0) / similarCalls.length / 1000).toFixed(1)}s`, color: 'text-orange-400' },
        ],
        issueKey: 'hasIssue',
        issueLabel: 'Slow',
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
          chat_history_tokens: call.chat_history_tokens,
          chat_history_count: call.chat_history_count,
        },
        timingDetails: {
          latency_ms: call.latency_ms,
          ttft_ms: call.ttft_ms,
          generation_ms: timeAttribution.generation_ms,
          tokens_per_second: timeAttribution.tokens_per_second,
        },
        fullData: call,
      }}
      
      // Fixes
      fixes={fixes}
      
      // Response text for AI Analysis and before/after comparison
      responseText={call.response_text}
    />
  );
}