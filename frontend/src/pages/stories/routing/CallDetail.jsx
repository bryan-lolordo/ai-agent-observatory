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
import Layer3Shell from "../../../components/stories/Layer3";
import routingConfig from "../../../config/layer3/routing";

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
        themeColor={theme.color}
        loading={true}
      />
    );
  }

  // Error state
  if (error || !call) {
    return (
      <div className="min-h-screen bg-gray-950 p-8">
        <div className="max-w-7xl mx-auto">
          <button
            onClick={() => navigate("/stories/routing/calls")}
            className={`mb-6 flex items-center gap-2 text-sm ${theme.text} hover:underline`}
          >
            ← Back to Routing Patterns
          </button>
          <div className="bg-red-900/20 border border-red-500 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-400 mb-2">
              Error Loading Call
            </h2>
            <p className="text-gray-300">{error || "Call not found"}</p>
            <button
              onClick={fetchCallDetail}
              className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Get config functions
  const kpis = routingConfig.getKPIs(call);
  const factors = routingConfig.getFactors(call);
  const fixes = routingConfig.getFixes(call);
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
      themeColor={theme.color}
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
          <div className="space-y-4">
            {/* Complexity Chart */}
            {customSections.find((s) => s.id === "complexity-analysis") && (
              <div className="bg-slate-900 rounded-lg p-4">
                <h4 className="text-sm font-medium text-slate-400 mb-3">
                  Complexity Score
                </h4>
                <div className="space-y-2">
                  {customSections
                    .find((s) => s.id === "complexity-analysis")
                    ?.data?.items?.map((item, idx) => (
                      <div key={idx} className="flex items-center gap-3">
                        <span className="text-sm text-slate-400 w-24">
                          {item.label}
                        </span>
                        <div className="flex-1 h-4 bg-slate-700 rounded overflow-hidden">
                          <div
                            className="h-full rounded"
                            style={{
                              width: `${(item.value / item.max) * 100}%`,
                              backgroundColor: item.color,
                            }}
                          />
                        </div>
                        <span className="text-sm text-slate-300 w-12 text-right">
                          {item.value.toFixed(2)}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* Routing Decision Cards */}
            {customSections.find((s) => s.id === "routing-decision") && (
              <div className="grid grid-cols-3 gap-3">
                {customSections
                  .find((s) => s.id === "routing-decision")
                  ?.data?.cards?.map((card, idx) => {
                    const colorMap = {
                      green: "border-green-500/30 bg-green-500/10",
                      yellow: "border-yellow-500/30 bg-yellow-500/10",
                      red: "border-red-500/30 bg-red-500/10",
                      blue: "border-blue-500/30 bg-blue-500/10",
                      purple: "border-purple-500/30 bg-purple-500/10",
                    };
                    return (
                      <div
                        key={idx}
                        className={`rounded-lg p-3 border ${colorMap[card.color] || colorMap.purple}`}
                      >
                        <div className="text-2xl mb-1">{card.icon}</div>
                        <div className="text-xs text-slate-400">
                          {card.label}
                        </div>
                        <div className="text-sm font-medium text-slate-200">
                          {card.value}
                        </div>
                      </div>
                    );
                  })}
              </div>
            )}
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
      // Similar panel (empty for now - could show similar patterns)
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