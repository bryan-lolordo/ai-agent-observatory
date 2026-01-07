/**
 * Layer 3: Routing Call Detail
 * 
 * Shows routing analysis for a specific LLM call.
 * Uses the shared Layer3Shell with routing-specific config.
 * 
 * Location: src/pages/stories/routing/CallDetail.jsx
 */

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { STORY_THEMES } from "../../../config/theme";
import { BASE_THEME } from "../../../utils/themeUtils";
import PageContainer from "../../../components/layout/PageContainer";
import Layer3Shell from "../../../components/stories/Layer3";
import routingConfig from "../../../config/layer3/routing";
import { getFixesForCall } from '../../../config/fixes';

const STORY_ID = "routing";
const theme = STORY_THEMES.routing;

export default function RoutingCallDetail() {
  const { callId } = useParams();
  const navigate = useNavigate();
  const [call, setCall] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchCallDetail();
  }, [callId]);

  const fetchCallDetail = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`/api/calls/${callId}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setCall(data);
    } catch (err) {
      console.error("Error fetching call detail:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <Layer3Shell
        storyId={STORY_ID}
        storyLabel="Model Routing"
        storyIcon={theme.emoji}
        theme={theme}
        loading={true}
      />
    );
  }

  // Error state
  if (error || !call) {
    return (
      <div className={`min-h-screen ${BASE_THEME.container.tertiary} p-8`}>
        <PageContainer>
          <button
            onClick={() => navigate("/stories/routing/calls")}
            className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:underline`}
          >
            ← Back to Routing Patterns
          </button>
          <div className={`${BASE_THEME.status.error.bg} border ${BASE_THEME.status.error.border} rounded-lg p-6`}>
            <h2 className={`text-xl font-bold ${BASE_THEME.status.error.textBold} mb-2`}>
              Error Loading Call
            </h2>
            <p className={BASE_THEME.text.secondary}>{error || "Call not found"}</p>
            <button
              onClick={fetchCallDetail}
              className={`mt-4 px-4 py-2 ${BASE_THEME.status.error.bgSolid} hover:bg-red-700 text-white rounded-lg`}
            >
              Retry
            </button>
          </div>
        </PageContainer>
      </div>
    );
  }

  // Get config functions
  const kpis = routingConfig.getKPIs(call);
  const factors = routingConfig.getFactors(call);
  const fixes = getFixesForCall(call, 'routing', factors);
  const customSections = routingConfig.getCustomSections(call);

  // Build entity label
  const entityLabel = `${call.agent_name || "Unknown"}.${call.operation || "unknown"}`;

  // Format timestamp
  const timestamp = call.timestamp
    ? new Date(call.timestamp).toLocaleString()
    : null;

  // Model config for Attribute panel
  const modelConfig = {
    provider: call.provider,
    model: call.model_name,
    temperature: call.temperature,
    max_tokens: call.max_tokens,
  };

  // Determine if healthy
  const routing = call.routing_analysis || {};
  const isHealthy = routing.opportunity === "keep";

  return (
    <Layer3Shell
      // Story config
      storyId={STORY_ID}
      storyLabel="Model Routing"
      storyIcon={theme.emoji}
      theme={theme}
      // Entity info
      entityId={call.call_id}
      entityType="call"
      entityLabel={entityLabel}
      entitySubLabel={timestamp}
      entityMeta={`${call.provider || "openai"} / ${call.model_name || "unknown"}`}
      // Navigation
      backPath="/stories/routing/calls"
      backLabel="Back to Routing Patterns"
      // KPIs
      kpis={kpis}
      // Current state for Fix comparison
      currentState={{
        model: call.model_name,
        cost: call.total_cost,
        latency: call.latency_ms,
        quality: call.judge_score,
      }}
      // Response text for before/after
      responseText={call.response_text}
      // Diagnose panel
      diagnoseProps={{
        factors: factors.map((f) => ({
          label: f.label,
          status: f.status,
          detail: f.detail,
          severity:
            f.status === "critical"
              ? "critical"
              : f.status === "warning"
                ? "warning"
                : "info",
        })),
        isHealthy,
        healthyMessage: `This call is using ${call.model_name} appropriately for the task complexity.`,
        breakdownTitle: "🎯 Routing Analysis",
        breakdownComponent: customSections.length > 0 ? (
          <div className="space-y-6">
            {customSections.map((section) => (
              <div key={section.id} className={`${BASE_THEME.container.secondary} rounded-lg p-4 border ${BASE_THEME.border.default}`}>
                <h4 className={`text-sm font-medium ${BASE_THEME.text.secondary} mb-4`}>{section.title}</h4>

                {/* Alternatives Table */}
                {section.type === 'table' && section.data && (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className={`${BASE_THEME.container.tertiary}/50`}>
                        <tr className={`border-b ${BASE_THEME.border.default}`}>
                          {section.data.headers.map((header, idx) => (
                            <th key={idx} className={`text-center py-3 px-4 ${BASE_THEME.text.muted} font-medium`}>
                              {header}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {section.data.rows.map((row, idx) => {
                          const verdictColors = {
                            'BEST': `${BASE_THEME.status.success.bg} ${BASE_THEME.status.success.border} ${BASE_THEME.status.success.text}`,
                            'CURRENT': `${BASE_THEME.status.info.bg} ${BASE_THEME.status.info.border} ${BASE_THEME.status.info.text}`,
                            'CHEAPER': 'bg-purple-500/20 border-purple-500/30 text-purple-400',
                            'EXPENSIVE': `${BASE_THEME.status.error.bg} ${BASE_THEME.status.error.border} ${BASE_THEME.status.error.text}`,
                          };
                          const verdictClass = verdictColors[row.verdict] || `${BASE_THEME.container.secondary} ${BASE_THEME.border.default} ${BASE_THEME.text.muted}`;

                          return (
                            <tr key={idx} className={`border-b ${BASE_THEME.container.tertiary}`}>
                              <td className={`py-3 px-4 text-center font-mono ${BASE_THEME.text.primary}`}>{row.model}</td>
                              <td className={`py-3 px-4 text-center ${BASE_THEME.text.secondary}`}>{row.quality}</td>
                              <td className={`py-3 px-4 text-center ${BASE_THEME.text.secondary}`}>${row.cost.toFixed(4)}</td>
                              <td className={`py-3 px-4 text-center ${BASE_THEME.text.secondary}`}>{row.latency}</td>
                              <td className="py-3 px-4 text-center">
                                <span className={`px-2 py-1 rounded border text-xs font-medium ${verdictClass}`}>
                                  {row.verdict}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Complexity Breakdown */}
                {section.type === 'breakdown' && section.data && (
                  <div className="space-y-3">
                    {section.data.items.map((item, idx) => (
                      <div key={idx} className="flex items-center gap-3">
                        <span className={`text-sm ${BASE_THEME.text.muted} w-32 capitalize`}>
                          {item.label}
                        </span>
                        <div className={`flex-1 h-6 ${BASE_THEME.border.default} rounded overflow-hidden`}>
                          <div
                            className="h-full bg-purple-500 flex items-center justify-end pr-2"
                            style={{ width: `${(item.value * 100)}%` }}
                          >
                            {item.value > 0.1 && (
                              <span className="text-xs text-white font-medium">
                                {(item.value * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                        </div>
                        <span className={`text-sm ${BASE_THEME.text.muted} w-32`}>{item.description}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : null,
      }}
      // Attribute panel
      attributeProps={{
        modelConfig,
        configHighlights: [
          {
            type: routing.is_cheap_model ? "info" : "warning",
            message: routing.is_cheap_model
              ? "Using budget-tier model"
              : "Using premium-tier model",
          },
          routing.complexity_score !== null && {
            type:
              routing.complexity_score < 0.4
                ? "success"
                : routing.complexity_score < 0.7
                  ? "info"
                  : "warning",
            message: `Task complexity: ${routing.complexity_label || "Unknown"}`,
          },
        ].filter(Boolean),
        responseAnalysis: {
          type: call.response_text?.trim().startsWith("{")
            ? "json"
            : call.response_text?.includes("```")
              ? "code"
              : "prose",
          tokenCount: call.completion_tokens,
        },
        promptBreakdown:
          call.system_prompt_tokens > 0
            ? {
                system: call.system_prompt_tokens,
                user: call.user_message_tokens,
                history: call.chat_history_tokens,
                total: call.prompt_tokens,
              }
            : null,
      }}
      // Trace panel
      traceProps={{
        callId: call.call_id,
        conversationId: call.conversation_id,
        storyType: 'routing',  // ADD THIS
      }}
      // Similar panel
      similarProps={{
        groupOptions: [
          { id: "operation", label: "Same Operation", filterFn: null },
        ],
        defaultGroup: "operation",
        items: [],
        currentItemId: call.call_id,
        columns: [
          {
            key: "id",
            label: "Call ID",
            format: (v) => v?.substring(0, 8) + "...",
          },
          { key: "timestamp", label: "Timestamp" },
          { key: "model_name", label: "Model" },
          {
            key: "total_cost",
            label: "Cost",
            format: (v) => `$${v?.toFixed(4)}`,
          },
        ],
        aggregateStats: [],
      }}
      // Raw panel
      rawProps={{
        metadata: {
          call_id: call.call_id,
          agent: call.agent_name,
          operation: call.operation,
          timestamp: call.timestamp,
          provider: call.provider,
          model: call.model_name,
          complexity_score: routing.complexity_score,
          opportunity: routing.opportunity,
        },
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
          total_tokens: call.total_tokens,
        },
        fullData: call,
      }}
      // Fixes
      fixes={fixes}
    />
  );
}