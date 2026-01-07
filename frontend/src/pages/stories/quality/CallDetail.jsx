/**
 * Quality Story - Layer 3 (Call Detail)
 * Location: src/pages/stories/quality/CallDetail.jsx
 * 
 * UPDATED:
 * - Added benchmarks fetch for DIAGNOSE tab comparison
 * - Added traceProps for TRACE tab
 * - Cleaned up data fetching
 */

import { useParams, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';

import Layer3Shell from '../../../components/stories/Layer3';
import { BASE_THEME } from '../../../utils/themeUtils';
import { PromptBreakdownBar } from '../../../components/stories/Layer3/shared';
import { getFixesForCall } from '../../../config/fixes';

import {
  QUALITY_STORY,
  getQualityKPIs,
  getQualityCurrentState,
  analyzeQualityFactors,
  getQualityCriteriaBreakdown,
  getJudgeEvaluation,
  getQualityFixes,
  getQualityConfigHighlights,
} from '../../../config/layer3/quality';

// ─────────────────────────────────────────────────────────────────────────────
// QUALITY-SPECIFIC BREAKDOWN COMPONENTS
// ─────────────────────────────────────────────────────────────────────────────

function CriteriaBreakdownBar({ criteria }) {
  if (!criteria?.length) {
    return <div className="text-gray-500 text-sm">No criteria breakdown available</div>;
  }

  return (
    <div className={`${BASE_THEME.container.secondary} rounded-lg p-4 space-y-3`}>
      {criteria.map(c => {
        const pct = (c.score / 10) * 100;
        const color = c.status === 'critical' ? 'red' : c.status === 'warning' ? 'yellow' : 'green';
        return (
          <div key={c.key}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-400">{c.label}</span>
              <span className={`text-${color}-400`}>{c.score.toFixed(1)}/10</span>
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div className={`h-full bg-${color}-500`} style={{ width: `${pct}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function JudgeEvaluationSection({ evaluation }) {
  const { reasoning, issues_found, strengths } = evaluation || {};
  if (!reasoning && !issues_found?.length && !strengths?.length) return null;

  return (
    <div className="space-y-4">
      {reasoning && (
        <div>
          <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-2">🧠 Judge Reasoning</h4>
          <div className={`${BASE_THEME.container.secondary} rounded-lg p-4`}>
            <p className="text-gray-300 text-sm leading-relaxed">{reasoning}</p>
          </div>
        </div>
      )}
      {issues_found?.length > 0 && (
        <div>
          <h4 className={`text-sm font-medium ${BASE_THEME.text.muted} uppercase tracking-wide mb-2`}>❌ Issues Found</h4>
          <div className={`${BASE_THEME.container.secondary} rounded-lg p-4 space-y-2`}>
            {issues_found.map((issue, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <span className={BASE_THEME.status.error.text}>•</span>
                <span className={BASE_THEME.text.secondary}>{issue}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {strengths?.length > 0 && (
        <div>
          <h4 className={`text-sm font-medium ${BASE_THEME.text.muted} uppercase tracking-wide mb-2`}>✅ Strengths</h4>
          <div className={`${BASE_THEME.container.secondary} rounded-lg p-4 space-y-2`}>
            {strengths.map((s, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <span className={BASE_THEME.status.success.text}>•</span>
                <span className={BASE_THEME.text.secondary}>{s}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// DATA FETCHING
// ─────────────────────────────────────────────────────────────────────────────

async function fetchCallData(callId) {
  const response = await fetch(`/api/calls/${callId}`);
  if (!response.ok) throw new Error(`Call not found: ${callId}`);
  const data = await response.json();

  // Parse quality_evaluation if string
  let qualityEval = data.quality_evaluation || data.judge_evaluation;
  if (typeof qualityEval === 'string') {
    try { qualityEval = JSON.parse(qualityEval); } catch { qualityEval = {}; }
  }

  return {
    call_id: data.call_id || data.id,
    agent_name: data.agent_name || 'Unknown',
    operation: data.operation || 'unknown',
    timestamp: data.timestamp,
    provider: data.provider || 'openai',
    model_name: data.model_name || 'gpt-4o',
    judge_score: data.judge_score,
    hallucination_flag: data.hallucination_flag || false,
    quality_evaluation: qualityEval || {},
    success: data.success !== false,
    prompt_tokens: data.prompt_tokens || 0,
    completion_tokens: data.completion_tokens || 0,
    total_cost: data.total_cost || 0,
    latency_ms: data.latency_ms || 0,
    temperature: data.temperature,
    max_tokens: data.max_tokens,
    system_prompt_tokens: data.system_prompt_tokens || 0,
    user_message_tokens: data.user_message_tokens || 0,
    chat_history_tokens: data.chat_history_tokens || 0,
    response_text: data.response_text || data.response || '',
    system_prompt: data.system_prompt || '',
    user_message: data.user_message || '',
    operation_avg_score: data.operation_avg_score,
    conversation_id: data.conversation_id,
    request_id: data.request_id,
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
    if (!response.ok) return { items: [], stats: null };

    const data = await response.json();
    const calls = data.calls || [];
    const scores = calls.map(c => c.judge_score).filter(s => s != null);

    return {
      items: calls.map(c => ({
        id: c.call_id || c.id,
        call_id: c.call_id || c.id,
        timestamp: c.timestamp,
        score: c.judge_score,
        score_formatted: c.judge_score != null ? `${c.judge_score.toFixed(1)}/10` : '—',
        hallucination: c.hallucination_flag || false,
        cost: c.total_cost || 0,
        current: (c.call_id || c.id) === call.call_id,
        hasIssue: (c.judge_score != null && c.judge_score < 7) || c.hallucination_flag,
      })),
      stats: {
        avg_score: scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null,
        total_calls: calls.length,
        low_quality: calls.filter(c => c.judge_score != null && c.judge_score < 7).length,
      },
    };
  } catch { 
    return { items: [], stats: null }; 
  }
}

async function fetchBenchmarks(callId) {
  try {
    const response = await fetch(`/api/stories/quality/benchmarks/${callId}`);
    if (!response.ok) return { available: false };
    return await response.json();
  } catch {
    return { available: false };
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

export default function QualityCallDetail() {
  const { callId } = useParams();
  const navigate = useNavigate();
  const [call, setCall] = useState(null);
  const [similarData, setSimilarData] = useState({ items: [], stats: null });
  const [benchmarks, setBenchmarks] = useState({ available: false });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const callData = await fetchCallData(callId);
        setCall(callData);
        
        // Fetch similar calls and benchmarks in parallel
        const [similar, bench] = await Promise.all([
          fetchSimilarCalls(callData),
          fetchBenchmarks(callId),
        ]);
        
        setSimilarData(similar);
        setBenchmarks(bench);
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
        storyId={QUALITY_STORY.id} 
        storyLabel={QUALITY_STORY.label} 
        storyIcon={QUALITY_STORY.icon} 
        theme={{
          color: QUALITY_STORY.color,
          text: 'text-red-400',
          bg: 'bg-red-600',
          border: 'border-red-500',
          dividerGlow: 'shadow-[0_0_10px_rgba(239,68,68,0.5)]',
        }}
        loading={true} 
      />
    );
  }

  // Analyze the call
  const factors = analyzeQualityFactors(call);
  const criteria = getQualityCriteriaBreakdown(call);
  const judgeEval = getJudgeEvaluation(call);
  const fixes = getFixesForCall(call, 'quality', factors);
  const configHighlights = getQualityConfigHighlights(call, factors);
  const currentState = getQualityCurrentState(call);
  const isHealthy = factors.length === 0 || factors.every(f => f.severity === 'info' || f.severity === 'ok');
  const { items: similarCalls, stats: opStats } = similarData;

  const modelConfig = { 
    provider: call.provider, 
    model: call.model_name, 
    temperature: call.temperature, 
    max_tokens: call.max_tokens 
  };
  
  const promptBreakdown = call.chat_history_tokens > 0 ? { 
    system: call.system_prompt_tokens, 
    user: call.user_message_tokens, 
    history: call.chat_history_tokens, 
    total: call.prompt_tokens 
  } : null;
  
  const metadata = { 
    call_id: call.call_id, 
    agent: call.agent_name, 
    operation: call.operation, 
    timestamp: call.timestamp, 
    judge_score: call.judge_score, 
    hallucination_flag: call.hallucination_flag 
  };

  return (
    <Layer3Shell
      storyId={QUALITY_STORY.id} 
      storyLabel={QUALITY_STORY.label} 
      storyIcon={QUALITY_STORY.icon}
      theme={{
        color: QUALITY_STORY.color,
        text: 'text-red-400',
        bg: 'bg-red-600',
        border: 'border-red-500',
        borderLight: 'border-red-500/30',
        dividerGlow: 'shadow-[0_0_10px_rgba(239,68,68,0.5)]',
      }}
      
      entityId={call.call_id} 
      entityType="call" 
      entityLabel={`${call.agent_name}.${call.operation}`} 
      entitySubLabel={call.timestamp} 
      entityMeta={`${call.provider} / ${call.model_name}`}
      
      backPath={`/stories/quality/operations/${call.agent_name}/${call.operation}`} 
      backLabel={`Back to ${call.operation}`}
      
      kpis={getQualityKPIs(call, opStats)} 
      currentState={currentState} 
      responseText={call.response_text}

      diagnoseProps={{
        factors, 
        isHealthy,
        healthyMessage: call.judge_score 
          ? `Scored ${call.judge_score.toFixed(1)}/10 with no significant issues.` 
          : 'Not evaluated.',
        breakdownTitle: '📊 Criteria Breakdown',
        breakdownComponent: <CriteriaBreakdownBar criteria={criteria} />,
        additionalBreakdown: judgeEval.reasoning || judgeEval.issues_found?.length 
          ? <JudgeEvaluationSection evaluation={judgeEval} /> 
          : null,
        additionalBreakdownTitle: judgeEval.reasoning ? '🧠 Judge Evaluation' : null,
        comparisonBenchmarks: benchmarks,
        benchmarkConfig: {
          metricKey: 'score',
          formatValue: (v) => `${v.toFixed(1)}/10`,
          comparisonLabel: 'better',
          higherIsBetter: true,
          thresholdForCallout: 1.5,
        },
      }}

      attributeProps={{ 
        modelConfig, 
        configHighlights, 
        promptBreakdown 
      }}

      traceProps={{
        callId: call.call_id,
        conversationId: call.conversation_id,
      }}

      similarProps={{
        groupOptions: [
          { id: 'operation', label: 'Same Operation', filterFn: null },
          { id: 'lowQuality', label: 'Low Quality', filterFn: items => items.filter(i => i.score != null && i.score < 7) },
          { id: 'issues', label: 'With Issues', filterFn: items => items.filter(i => i.hasIssue) },
        ],
        defaultGroup: 'operation', 
        items: similarCalls, 
        currentItemId: call.call_id,
        columns: [
          { key: 'id', label: 'Call ID', format: v => v?.substring(0, 8) + '...' },
          { key: 'timestamp', label: 'Timestamp' },
          { key: 'score_formatted', label: 'Score' },
          { key: 'hallucination', label: 'Halluc.', format: v => v ? '⚠️' : '—' },
          { key: 'cost', label: 'Cost', format: v => `$${v?.toFixed(3)}` },
        ],
        aggregateStats: [
          { label: 'Total Calls', value: similarCalls.length, color: 'text-red-400' },
          { label: 'Avg Score', value: opStats?.avg_score ? `${opStats.avg_score.toFixed(1)}/10` : '—', color: 'text-red-400' },
          { label: 'Low Quality', value: opStats?.low_quality || 0, color: 'text-red-400' },
        ],
        issueKey: 'hasIssue', 
        issueLabel: 'Issue', 
        okLabel: 'OK',
      }}

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
          total_tokens: call.prompt_tokens + call.completion_tokens 
        },
        qualityEvaluation: call.quality_evaluation,
        fullData: call,
      }}

      fixes={fixes}
    />
  );
}