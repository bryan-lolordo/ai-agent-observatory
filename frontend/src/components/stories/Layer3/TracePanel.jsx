/**
 * TracePanel - Execution trace and conversation breakdown
 *
 * Shows:
 * - Routing-specific trace for routing story
 * - Cache prompt breakdown for cache story
 * - Conversation Statistics (top)
 * - Chat History Breakdown (left)
 * - Call Trace Tree (right)
 *
 * UPDATED: Uses theme system - no hardcoded colors!
 */

import { TraceTree } from './shared';
import ChatHistoryBreakdown from './shared/ChatHistoryBreakdown';
import CacheablePromptView from './shared/CacheablePromptView';
import RoutingTraceView from './shared/RoutingTraceView';
import { BASE_THEME } from '../../../utils/themeUtils';

export default function TracePanel({
  // For Call Trace Tree
  callId = null,
  conversationId = null,

  // For Chat History Breakdown
  chatHistoryBreakdown = null, // { messages, insights, total_tokens }

  // For Story-specific views
  storyType = null,
  data = null,
}) {
  // NEW: Routing story - show conversation routing analysis
  if (storyType === 'routing' && conversationId) {
    return <RoutingTraceView conversationId={conversationId} />;
  }

  // Cache story - use CacheablePromptView for clearer boundary visualization
  if (storyType === 'cache' && data?.cacheable_tokens > 0) {
    // Extract text content with fallback logic
    const systemPromptText = data.system_prompt || data.prompt || '';
    const userMessageText = data.user_message || '(Varies per call)';

    return (
      <CacheablePromptView
        systemPrompt={systemPromptText}
        systemPromptTokens={data.system_prompt_tokens || 0}
        userMessage={userMessageText}
        userMessageTokens={data.user_message_tokens || 0}
        chatHistory={data.chat_history}
        chatHistoryTokens={data.chat_history_tokens || 0}
        toolDefinitions={data.tool_definitions}
        toolDefinitionsTokens={data.tool_definitions_tokens || 0}
        cacheableTokens={data.cacheable_tokens}
        totalTokens={data.total_tokens}
        insights={data.insights || []}
      />
    );
  }

  // ORIGINAL LOGIC (unchanged) - for latency and other stories
  const hasHistory = chatHistoryBreakdown && chatHistoryBreakdown.messages && chatHistoryBreakdown.messages.length > 0;
  const hasTrace = callId || conversationId;

  // Extract conversation stats if available
  const conversationStats = chatHistoryBreakdown?.conversation_stats || null;

  // If we have both, show stats on top + side-by-side below
  if (hasHistory && hasTrace) {
    return (
      <div className="space-y-6">
        {/* Conversation Statistics - Top */}
        {conversationStats && (
          <div className={`bg-gradient-to-r from-gray-800 to-gray-900 p-6 rounded-lg border ${BASE_THEME.border.default}`}>
            <h3 className={`text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide mb-4`}>
              📊 Conversation Statistics
            </h3>
            <div className="grid grid-cols-4 gap-6">
              <div>
                <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Turns</div>
                <div className={`text-2xl font-bold ${BASE_THEME.text.primary}`}>{conversationStats.turns || 0}</div>
              </div>
              <div>
                <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Total Calls</div>
                <div className={`text-2xl font-bold ${BASE_THEME.text.primary}`}>{conversationStats.total_calls || 0}</div>
              </div>
              <div>
                <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Total Cost</div>
                <div className={`text-2xl font-bold ${BASE_THEME.text.primary}`}>${(conversationStats.total_cost || 0).toFixed(4)}</div>
              </div>
              <div>
                <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Total Time</div>
                <div className={`text-2xl font-bold ${BASE_THEME.text.primary}`}>{((conversationStats.total_time || 0) / 1000).toFixed(1)}s</div>
              </div>
            </div>
          </div>
        )}

        {/* Side-by-side panels */}
        <div className="grid grid-cols-2 gap-6">
          {/* Left: Chat History */}
          <div>
            <h3 className={`text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide mb-4`}>
              💬 Conversation Breakdown
            </h3>
            <ChatHistoryBreakdown {...chatHistoryBreakdown} />
          </div>

          {/* Right: Call Tree */}
          <div>
            <h3 className={`text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide mb-4`}>
              🌳 Call Hierarchy
            </h3>
            <TraceTree callId={callId} conversationId={conversationId} />
          </div>
        </div>
      </div>
    );
  }

  // If only history, show full width
  if (hasHistory) {
    return (
      <div className="space-y-6">
        {/* Conversation Statistics - Top */}
        {conversationStats && (
          <div className={`bg-gradient-to-r from-gray-800 to-gray-900 p-6 rounded-lg border ${BASE_THEME.border.default}`}>
            <h3 className={`text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide mb-4`}>
              📊 Conversation Statistics
            </h3>
            <div className="grid grid-cols-4 gap-6">
              <div>
                <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Turns</div>
                <div className={`text-2xl font-bold ${BASE_THEME.text.primary}`}>{conversationStats.turns || 0}</div>
              </div>
              <div>
                <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Total Calls</div>
                <div className={`text-2xl font-bold ${BASE_THEME.text.primary}`}>{conversationStats.total_calls || 0}</div>
              </div>
              <div>
                <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Total Cost</div>
                <div className={`text-2xl font-bold ${BASE_THEME.text.primary}`}>${(conversationStats.total_cost || 0).toFixed(4)}</div>
              </div>
              <div>
                <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Total Time</div>
                <div className={`text-2xl font-bold ${BASE_THEME.text.primary}`}>{((conversationStats.total_time || 0) / 1000).toFixed(1)}s</div>
              </div>
            </div>
          </div>
        )}

        <div>
          <h3 className={`text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide mb-4`}>
            💬 Conversation Breakdown
          </h3>
          <ChatHistoryBreakdown {...chatHistoryBreakdown} />
        </div>
      </div>
    );
  }

  // If only trace, show full width
  if (hasTrace) {
    return (
      <div>
        <h3 className={`text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide mb-4`}>
          🌳 Call Hierarchy
        </h3>
        <TraceTree callId={callId} conversationId={conversationId} />
      </div>
    );
  }

  // Neither available
  return (
    <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-8 text-center`}>
      <div className="text-4xl mb-4">🔍</div>
      <h3 className={`text-lg font-medium ${BASE_THEME.text.secondary} mb-2`}>No Trace Data Available</h3>
      <p className={`${BASE_THEME.text.muted} text-sm`}>
        No conversation history or call hierarchy data found for this call.
      </p>
    </div>
  );
}
