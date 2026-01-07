/**
 * Prompt Composition Story - Layer 3 (Call Detail)
 * Location: src/pages/stories/prompt/CallDetail.jsx
 * 
 * Uses the universal Layer3Shell with prompt-specific configuration.
 */

import { useParams, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';

import Layer3Shell from '../../../components/stories/Layer3';
import { PromptBreakdownBar } from '../../../components/stories/Layer3/shared';
import { STORY_THEMES } from '../../../config/theme';
import { BASE_THEME } from '../../../utils/themeUtils';
import { getFixesForCall } from '../../../config/fixes';

import {
  PROMPT_STORY,
  getPromptKPIs,
  getPromptCurrentState,
  analyzePromptFactors,
  getPromptComposition,
  getCacheReadinessAnalysis,
  getComponentAnalysis,
  getTokenMetrics,
  getCostBreakdown,
  getPromptFixes,
  getPromptConfigHighlights,
  PROMPT_RAW_CONFIG,
  PROMPT_SIMILAR_CONFIG,
} from '../../../config/layer3/prompt';

// ─────────────────────────────────────────────────────────────────────────────
// DATA FETCHING
// ─────────────────────────────────────────────────────────────────────────────

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
    
    // Performance
    latency_ms: data.latency_ms || 0,
    
    // Tokens
    prompt_tokens: data.prompt_tokens || 0,
    completion_tokens: data.completion_tokens || 0,
    total_tokens: data.total_tokens || 0,
    
    // Token Breakdown
    system_prompt_tokens: data.system_prompt_tokens || 0,
    user_message_tokens: data.user_message_tokens || 0,
    chat_history_tokens: data.chat_history_tokens || 0,
    
    // Percentages (from backend)
    system_pct: data.system_pct || 0,
    user_pct: data.user_pct || 0,
    history_pct: data.history_pct || 0,
    
    // Cost
    prompt_cost: data.prompt_cost,
    completion_cost: data.completion_cost,
    total_cost: data.total_cost || 0,
    
    // Cache (from backend)
    cache_status: data.cache_status || 'none',
    cache_emoji: data.cache_emoji || '➖',
    cache_label: data.cache_label || 'Unknown',
    cache_issue_reason: data.cache_issue_reason,
    cache_analysis: data.cache_analysis || {},
    
    // Content
    system_prompt: data.system_prompt || '',
    user_message: data.user_message || '',
    response_text: data.response_text || data.response || '',
    chat_history: data.chat_history || [],
    
    // Model config
    temperature: data.temperature,
    max_tokens: data.max_tokens,
    
    // Operation stats
    operation_avg_system_tokens: data.operation_avg_system_tokens,
    operation_avg_user_tokens: data.operation_avg_user_tokens,
    operation_avg_history_tokens: data.operation_avg_history_tokens,
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
      return [];
    }
    const data = await response.json();
    
    return (data.calls || []).map(c => ({
      id: c.call_id || c.id,
      call_id: c.call_id || c.id,
      timestamp: c.timestamp,
      system_prompt_tokens: c.system_prompt_tokens || 0,
      chat_history_tokens: c.chat_history_tokens || 0,
      prompt_tokens: c.prompt_tokens || 0,
      cache_status: c.cache_status || 'none',
      total_cost: c.total_cost || 0,
      current: (c.call_id || c.id) === call.call_id,
    }));
  } catch (err) {
    console.error('Failed to fetch similar calls:', err);
    return [];
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// CUSTOM COMPONENTS
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Prompt Composition Stacked Bar
 */
function PromptCompositionBar({ composition }) {
  if (!composition || !composition.components) return null;
  
  const { components, total } = composition;
  
  return (
    <div className="space-y-3">
      {/* Stacked bar */}
      <div className="h-8 flex rounded-lg overflow-hidden ${BASE_THEME.container.tertiary}">
        {components.map((comp) => (
          comp.percentage > 0 && (
            <div
              key={comp.id}
              className={`${comp.bgClass} flex items-center justify-center text-xs font-medium text-white transition-all`}
              style={{ width: `${comp.percentage}%` }}
              title={`${comp.label}: ${comp.tokens.toLocaleString()} tokens (${comp.percentage.toFixed(1)}%)`}
            >
              {comp.percentage > 10 && `${comp.percentage.toFixed(0)}%`}
            </div>
          )
        ))}
      </div>
      
      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-sm">
        {components.map((comp) => (
          <div key={comp.id} className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded ${comp.bgClass}`} />
            <span className="text-gray-400">{comp.label}:</span>
            <span className={comp.textClass}>{comp.tokens.toLocaleString()}</span>
            <span className="text-gray-500">({comp.percentage.toFixed(1)}%)</span>
          </div>
        ))}
      </div>
      
      {/* Total */}
      <div className="text-sm text-gray-400 pt-2 border-t border-gray-700">
        Total Prompt: <span className="text-white font-medium">{total.toLocaleString()} tokens</span>
      </div>
    </div>
  );
}

/**
 * Cache Readiness Card
 */
function CacheReadinessCard({ analysis }) {
  if (!analysis) return null;
  
  const statusColors = {
    ready: 'border-green-500/30 bg-green-500/10',
    partial: 'border-yellow-500/30 bg-yellow-500/10',
    not_ready: 'border-red-500/30 bg-red-500/10',
    none: 'border-gray-500/30 bg-gray-500/10',
  };
  
  return (
    <div className={`rounded-lg border p-4 ${statusColors[analysis.status] || statusColors.none}`}>
      <div className="flex items-center gap-3 mb-3">
        <span className="text-2xl">{analysis.emoji}</span>
        <div>
          <div className={`font-medium ${analysis.color}`}>{analysis.label}</div>
          <div className="text-sm text-gray-400">Cache Readiness</div>
        </div>
      </div>
      
      {analysis.issueReason && (
        <div className="text-sm text-gray-300 mb-3 p-2 ${BASE_THEME.container.tertiary}/50 rounded">
          {analysis.issueReason}
        </div>
      )}
      
      {analysis.recommendation && (
        <div className="text-sm text-cyan-400">
          💡 {analysis.recommendation}
        </div>
      )}
    </div>
  );
}

/**
 * Component Analysis Cards
 */
function ComponentAnalysisCards({ components }) {
  if (!components || components.length === 0) return null;
  
  const colorClasses = {
    purple: { border: 'border-purple-500/30', bg: 'bg-purple-500/10', text: 'text-purple-400' },
    green: { border: 'border-green-500/30', bg: 'bg-green-500/10', text: 'text-green-400' },
    orange: { border: 'border-orange-500/30', bg: 'bg-orange-500/10', text: 'text-orange-400' },
  };
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {components.map((comp) => {
        const colors = colorClasses[comp.color] || colorClasses.purple;
        return (
          <div key={comp.id} className={`rounded-lg border p-4 ${colors.border} ${colors.bg}`}>
            <div className="flex items-center justify-between mb-2">
              <span className={`font-medium ${colors.text}`}>{comp.label}</span>
              <span className="text-lg">{comp.emoji}</span>
            </div>
            <div className="text-2xl font-bold text-white mb-1">
              {comp.tokens.toLocaleString()}
            </div>
            <div className="text-sm text-gray-400 mb-2">{comp.statusLabel}</div>
            <div className="text-xs text-gray-500">{comp.description}</div>
          </div>
        );
      })}
    </div>
  );
}

/**
 * Chat History List
 */
function ChatHistoryList({ history, maxShow = 8 }) {
  const [expanded, setExpanded] = useState(false);
  
  if (!history || history.length === 0) {
    return (
      <div className="text-sm text-gray-500 italic p-4 ${BASE_THEME.container.tertiary}/50 rounded-lg">
        No chat history in this call
      </div>
    );
  }
  
  const displayHistory = expanded ? history : history.slice(0, maxShow);
  const hasMore = history.length > maxShow;
  
  return (
    <div className="space-y-2">
      {displayHistory.map((msg, idx) => (
        <div 
          key={idx}
          className={`p-3 rounded-lg text-sm ${
            msg.role === 'user' 
              ? 'bg-cyan-500/10 border border-cyan-500/20 ml-4' 
              : '${BASE_THEME.container.tertiary} border border-gray-700 mr-4'
          }`}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className={msg.role === 'user' ? 'text-cyan-400' : 'text-gray-400'}>
              {msg.role === 'user' ? '👤 User' : '🤖 Assistant'}
            </span>
            <span className="text-xs text-gray-500">Message {idx + 1}</span>
          </div>
          <div className="text-gray-300 line-clamp-3">
            {msg.content || msg.text || JSON.stringify(msg)}
          </div>
        </div>
      ))}
      
      {hasMore && (
        <button 
          onClick={() => setExpanded(!expanded)}
          className="text-sm text-cyan-400 hover:text-cyan-300 w-full text-center py-2"
        >
          {expanded ? '▲ Show Less' : `▼ Show ${history.length - maxShow} More Messages`}
        </button>
      )}
    </div>
  );
}

/**
 * Metrics Grid (for Breakdown tab)
 */
function MetricsGrid({ items, title }) {
  return (
    <div className="space-y-3">
      {title && <h4 className="text-sm font-medium text-gray-400">{title}</h4>}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {items.map((item, idx) => (
          <div 
            key={idx} 
            className={`p-3 rounded-lg ${BASE_THEME.container.tertiary}/50 border border-gray-700 ${
              item.highlight ? 'border-yellow-500/50' : ''
            }`}
          >
            <div className="text-xs text-gray-500 mb-1">{item.label}</div>
            <div className={`text-lg font-medium ${item.color || 'text-white'}`}>
              {item.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

export default function PromptCallDetail() {
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
        storyId={PROMPT_STORY.id}
        storyLabel={PROMPT_STORY.label}
        storyIcon={PROMPT_STORY.icon}
        theme={STORY_THEMES.system_prompt}
        loading={true}
      />
    );
  }

  // Analyze the call
  const factors = analyzePromptFactors(call);
  const composition = getPromptComposition(call);
  const cacheAnalysis = getCacheReadinessAnalysis(call);
  const componentAnalysis = getComponentAnalysis(call);
  const tokenMetrics = getTokenMetrics(call);
  const costBreakdown = getCostBreakdown(call);
  const fixes = getFixesForCall(call, 'prompt', factors);
  const configHighlights = getPromptConfigHighlights(call, factors);
  const currentState = getPromptCurrentState(call);

  // Check if healthy
  const isHealthy = factors.length === 0 || factors.every(f => f.severity === 'info' || f.severity === 'ok');

  // Build model config for Raw tab
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

  // Cache analysis for Raw tab
  const cacheAnalysisRaw = {
    status: call.cache_status,
    label: call.cache_label,
    issue_reason: call.cache_issue_reason,
    ...call.cache_analysis,
  };

  return (
    <Layer3Shell
      // Story config
      storyId={PROMPT_STORY.id}
      storyLabel={PROMPT_STORY.label}
      storyIcon={PROMPT_STORY.icon}
      theme={STORY_THEMES.system_prompt}
      
      // Entity info
      entityId={call.call_id}
      entityType="call"
      entityLabel={`${call.agent_name}.${call.operation}`}
      entitySubLabel={call.timestamp}
      entityMeta={`${call.provider} / ${call.model_name}`}
      
      // Navigation
      backPath={`/stories/system_prompt/operations/${call.agent_name}/${call.operation}`}
      backLabel={`Back to ${call.operation}`}
      
      // KPIs
      kpis={getPromptKPIs(call)}
      
      // Current state for Fix comparison table
      currentState={currentState}
      
      // Diagnose panel
      diagnoseProps={{
        factors,
        isHealthy,
        healthyMessage: `This call has ${call.system_prompt_tokens.toLocaleString()} system tokens and ${call.chat_history_tokens.toLocaleString()} history tokens. Cache status: ${call.cache_label || 'Unknown'}.`,
        
        // Cache Readiness Analysis (main diagnosis)
        breakdownTitle: '💾 Cache Readiness Analysis',
        breakdownComponent: <CacheReadinessCard analysis={cacheAnalysis} />,
        
        // Component Analysis
        additionalBreakdownTitle: '🔍 Component Analysis',
        additionalBreakdown: <ComponentAnalysisCards components={componentAnalysis} />,
      }}
      
      // Breakdown panel (custom for Prompt)
      attributeProps={{
        customSections: [
          {
            title: '📊 Prompt Composition',
            content: <PromptCompositionBar composition={composition} />,
          },
          {
            title: '🔢 Token Metrics',
            content: <MetricsGrid items={tokenMetrics} />,
          },
          {
            title: '💰 Cost Breakdown', 
            content: <MetricsGrid items={costBreakdown} />,
          },
          {
            title: `💬 Chat History (${call.cache_analysis?.history_messages || 0} messages)`,
            content: <ChatHistoryList history={call.chat_history} />,
          },
        ],
      }}
      
      // Similar panel
      similarProps={{
        groupOptions: PROMPT_SIMILAR_CONFIG.groupOptions,
        defaultGroup: 'operation',
        items: similarCalls,
        currentItemId: call.call_id,
        columns: PROMPT_SIMILAR_CONFIG.columns,
        aggregateStats: [
          { label: 'Total Calls', value: similarCalls.length, color: 'text-cyan-400' },
          { label: 'Cache Issues', value: similarCalls.filter(c => c.cache_status !== 'ready').length, color: 'text-yellow-400' },
          { label: 'Large History', value: similarCalls.filter(c => (c.chat_history_tokens || 0) > 500).length, color: 'text-orange-400' },
          { label: 'Avg History', value: `${Math.round(similarCalls.reduce((sum, c) => sum + (c.chat_history_tokens || 0), 0) / (similarCalls.length || 1)).toLocaleString()}`, color: 'text-cyan-400' },
        ],
        issueKey: 'cache_status',
        issueCheck: PROMPT_SIMILAR_CONFIG.issueCheck,
        issueLabel: PROMPT_SIMILAR_CONFIG.issueLabel,
        okLabel: PROMPT_SIMILAR_CONFIG.okLabel,
        onRowClick: (item) => navigate(`/stories/system_prompt/calls/${item.call_id}`),
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
        chatHistory: call.chat_history,
        chatHistoryTokens: call.chat_history_tokens,
        cacheAnalysis: cacheAnalysisRaw,
        modelConfig,
        tokenBreakdown: {
          system_tokens: call.system_prompt_tokens,
          user_tokens: call.user_message_tokens,
          history_tokens: call.chat_history_tokens,
          prompt_tokens: call.prompt_tokens,
          completion_tokens: call.completion_tokens,
          total_tokens: call.prompt_tokens + call.completion_tokens,
        },
        fullData: call,
        // Highlight cache analysis section
        highlightSections: ['cacheAnalysis'],
      }}
      
      // Fixes
      fixes={fixes}
      
      // Response text for before/after comparison in Fix panel
      responseText={call.response_text}
      
      // Similar calls count for fix impact
      similarCallsWithIssue={similarCalls.filter(c => c.cache_status !== 'ready').length}
    />
  );
}