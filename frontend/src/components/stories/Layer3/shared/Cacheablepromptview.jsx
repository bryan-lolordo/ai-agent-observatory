/**
 * CacheablePromptView - Visual prompt structure with cache boundaries
 *
 * Shows the actual prompt messages with:
 * - Visual cache boundaries
 * - Expandable content preview
 * - Token counts
 * - Cache control annotations
 * - Copy functionality
 *
 * UPDATED: Uses theme system - no hardcoded colors!
 *
 * Similar to ChatHistoryBreakdown but for caching analysis
 */

import { useState } from 'react';
import { BASE_THEME } from '../../../../utils/themeUtils';
import { STORY_THEMES } from '../../../../config/theme';

// Message colors using theme - cache=purple, not_cacheable=red
const MESSAGE_COLORS = {
  cacheable: {
    indicator: STORY_THEMES.routing.bg,
    bg: STORY_THEMES.routing.bgSubtle,
    border: STORY_THEMES.routing.borderLight,
    text: STORY_THEMES.routing.text,
    tag: `${STORY_THEMES.routing.bgSubtle} ${STORY_THEMES.routing.text}`,
  },
  not_cacheable: {
    indicator: STORY_THEMES.quality.bg,
    bg: STORY_THEMES.quality.bgSubtle,
    border: STORY_THEMES.quality.borderLight,
    text: STORY_THEMES.quality.text,
    tag: `${STORY_THEMES.quality.bgSubtle} ${STORY_THEMES.quality.text}`,
  },
};

const MESSAGE_ICONS = {
  system: '🟣',
  user: '🔴',
  assistant: '🔴',
  tool: '🟢',
};

function MessageBlock({
  role,
  content,
  tokens,
  cacheable,
  cacheControlCode,
  index,
}) {
  const [expanded, setExpanded] = useState(false);
  const colors = cacheable ? MESSAGE_COLORS.cacheable : MESSAGE_COLORS.not_cacheable;
  const icon = MESSAGE_ICONS[role] || '⚪';

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
  };

  const handleCopyWithCache = () => {
    if (cacheControlCode) {
      navigator.clipboard.writeText(cacheControlCode);
    }
  };

  // Truncate content for preview
  const preview = content.length > 150 ? content.substring(0, 150) + '...' : content;

  return (
    <div className={`rounded-lg border ${colors.border} ${colors.bg} overflow-hidden`}>
      {/* Header - Always visible */}
      <div
        onClick={() => setExpanded(!expanded)}
        className={`flex items-center gap-3 p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
      >
        {/* Color indicator bar */}
        <div className={`w-1 h-12 ${colors.indicator} rounded-full`} />

        {/* Content */}
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">{icon}</span>
            <span className={`font-semibold ${BASE_THEME.text.primary} uppercase text-sm`}>
              {role}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded font-semibold ${colors.tag}`}>
              {cacheable ? '✅ CACHEABLE' : '❌ NOT CACHEABLE'}
            </span>
            {cacheable && (
              <span className={`text-xs px-2 py-0.5 rounded ${STORY_THEMES.optimization.bgSubtle} ${STORY_THEMES.optimization.text} font-semibold`}>
                💾 ADD CACHE_CONTROL
              </span>
            )}
          </div>

          {/* Preview text */}
          <div className={`text-sm ${BASE_THEME.text.secondary} font-mono mb-2`}>
            {expanded ? null : `"${preview}"`}
          </div>

          {/* Metadata */}
          <div className={`flex items-center gap-4 text-xs ${BASE_THEME.text.muted}`}>
            <span>📊 {tokens.toLocaleString()} tokens</span>
            {cacheable && (
              <span className={STORY_THEMES.routing.text}>
                💰 ${((tokens / 1000) * 0.003 * 0.9).toFixed(4)} saved per call
              </span>
            )}
            <span className={BASE_THEME.text.muted}>
              {expanded ? '▼ Click to collapse' : '▶ Click to expand'}
            </span>
          </div>
        </div>

        {/* Copy buttons */}
        <div className="flex gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleCopy();
            }}
            className={`px-3 py-1 ${BASE_THEME.container.secondary} hover:bg-gray-600 ${BASE_THEME.text.secondary} rounded text-xs transition-colors`}
          >
            Copy Text
          </button>
          {cacheable && cacheControlCode && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleCopyWithCache();
              }}
              className={`px-3 py-1 ${STORY_THEMES.routing.bg} hover:bg-purple-500 text-white rounded text-xs transition-colors`}
            >
              Copy with Cache
            </button>
          )}
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className={`border-t ${BASE_THEME.border.default} p-4 ${BASE_THEME.container.primary}/50`}>
          <div className="mb-4">
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-2`}>
              Full Content
            </div>
            <pre className={`text-sm ${BASE_THEME.text.secondary} whitespace-pre-wrap font-mono ${BASE_THEME.container.tertiary} p-4 rounded border ${BASE_THEME.border.default} max-h-96 overflow-y-auto`}>
{content}
            </pre>
          </div>

          {/* Code with cache control */}
          {cacheable && cacheControlCode && (
            <div>
              <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-2`}>
                💾 With Cache Control
              </div>
              <pre className={`text-sm ${BASE_THEME.text.secondary} whitespace-pre-wrap font-mono ${BASE_THEME.container.tertiary} p-4 rounded border ${STORY_THEMES.routing.border}`}>
{cacheControlCode}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CacheBoundary({ above, below }) {
  return (
    <div className="relative py-4">
      <div className="absolute inset-0 flex items-center">
        <div className={`w-full border-t-2 border-dashed ${STORY_THEMES.routing.border}`}></div>
      </div>
      <div className="relative flex justify-center">
        <span className={`${BASE_THEME.container.primary} px-4 py-1 text-sm font-semibold ${STORY_THEMES.routing.text} border-2 ${STORY_THEMES.routing.border} rounded-full`}>
          ⚡ CACHE BOUNDARY
        </span>
      </div>
      <div className={`mt-2 text-center text-xs ${BASE_THEME.text.muted}`}>
        <span className={STORY_THEMES.routing.text}>↑ {above}</span>
        <span className="mx-2">•</span>
        <span className={STORY_THEMES.quality.text}>↓ {below}</span>
      </div>
    </div>
  );
}

export default function CacheablePromptView({
  // Prompt messages
  systemPrompt = null,
  systemPromptTokens = 0,

  toolDefinitions = null,
  toolDefinitionsTokens = 0,

  chatHistory = [], // [{ role, content, tokens }]
  chatHistoryTokens = 0,

  userMessage = null,
  userMessageTokens = 0,

  // Analysis
  cacheableTokens = 0,
  totalTokens = 0,

  // Insights
  insights = [],
}) {
  // Calculate percentages
  const cacheablePercentage = totalTokens > 0 ? (cacheableTokens / totalTokens) * 100 : 0;
  const nonCacheableTokens = totalTokens - cacheableTokens;
  const nonCacheablePercentage = 100 - cacheablePercentage;

  // Build messages array in order
  const messages = [];

  if (systemPrompt) {
    messages.push({
      id: 'system',
      role: 'system',
      content: systemPrompt,
      tokens: systemPromptTokens,
      cacheable: true,
      cacheControlCode: `{
  "role": "system",
  "content": "${systemPrompt.substring(0, 50)}...",
  "cache_control": {"type": "ephemeral"}  // ← Add this line
}`,
    });
  }

  if (toolDefinitions) {
    messages.push({
      id: 'tools',
      role: 'tool',
      content: toolDefinitions,
      tokens: toolDefinitionsTokens,
      cacheable: true,
      cacheControlCode: `{
  "role": "system",
  "content": [
    {"type": "text", "text": "..."},
    {"type": "tool_use", "tools": [...], "cache_control": {"type": "ephemeral"}}  // ← Add here
  ]
}`,
    });
  }

  // Add cache boundary after cacheable content
  const hasCacheableBoundary = messages.length > 0;

  // Add chat history (not cacheable)
  if (chatHistory && chatHistory.length > 0) {
    chatHistory.forEach((msg, idx) => {
      messages.push({
        id: `history-${idx}`,
        role: msg.role,
        content: msg.content,
        tokens: msg.tokens || 0,
        cacheable: false,
      });
    });
  }

  // Add user message (not cacheable)
  if (userMessage) {
    messages.push({
      id: 'user',
      role: 'user',
      content: userMessage,
      tokens: userMessageTokens,
      cacheable: false,
    });
  }

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className={`bg-gradient-to-r from-gray-800 to-gray-900 p-5 rounded-lg border ${BASE_THEME.border.default}`}>
        <h3 className={`text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide mb-4`}>
          📊 Prompt Structure Overview
        </h3>
        <div className="grid grid-cols-3 gap-6">
          <div>
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Total Tokens</div>
            <div className={`text-2xl font-bold ${BASE_THEME.text.primary}`}>{totalTokens.toLocaleString()}</div>
          </div>
          <div>
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Cacheable</div>
            <div className={`text-2xl font-bold ${STORY_THEMES.routing.text}`}>
              {cacheableTokens.toLocaleString()}
              <span className={`text-sm ${BASE_THEME.text.muted} ml-2`}>({cacheablePercentage.toFixed(1)}%)</span>
            </div>
          </div>
          <div>
            <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1`}>Not Cacheable</div>
            <div className={`text-2xl font-bold ${STORY_THEMES.quality.text}`}>
              {nonCacheableTokens.toLocaleString()}
              <span className={`text-sm ${BASE_THEME.text.muted} ml-2`}>({nonCacheablePercentage.toFixed(1)}%)</span>
            </div>
          </div>
        </div>

        {/* Visual progress bar */}
        <div className="mt-4 flex rounded-full h-3 overflow-hidden">
          <div
            className={STORY_THEMES.routing.bg}
            style={{ width: `${cacheablePercentage}%` }}
            title={`Cacheable: ${cacheablePercentage.toFixed(1)}%`}
          />
          <div
            className={STORY_THEMES.quality.bg}
            style={{ width: `${nonCacheablePercentage}%` }}
            title={`Not Cacheable: ${nonCacheablePercentage.toFixed(1)}%`}
          />
        </div>
      </div>

      {/* Visual Prompt Structure */}
      <div className="space-y-4">
        {messages.map((msg, idx) => {
          const isLastCacheable = msg.cacheable && (idx === messages.length - 1 || !messages[idx + 1]?.cacheable);

          return (
            <div key={msg.id}>
              <MessageBlock {...msg} index={idx} />

              {/* Add cache boundary after last cacheable message */}
              {isLastCacheable && hasCacheableBoundary && idx < messages.length - 1 && (
                <CacheBoundary
                  above="Cached (90% cheaper on repeat calls)"
                  below="Not cached (changes every call)"
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Insights */}
      {insights.length > 0 && (
        <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.light} rounded-lg p-4`}>
          <div className={`text-sm font-medium ${BASE_THEME.text.secondary} mb-3`}>💡 Insights</div>
          <ul className="space-y-2">
            {insights.map((insight, idx) => (
              <li key={idx} className={`text-sm ${BASE_THEME.text.secondary} flex items-start gap-2`}>
                <span className={BASE_THEME.text.muted}>•</span>
                <span>{insight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Summary Stats - Savings */}
      <div className="grid grid-cols-3 gap-3 text-center">
        <div className={`${BASE_THEME.container.primary} rounded-lg p-3 border ${BASE_THEME.border.default}`}>
          <div className={`text-2xl font-bold ${STORY_THEMES.routing.text}`}>
            {cacheableTokens.toLocaleString()}
          </div>
          <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Cacheable Tokens</div>
        </div>
        <div className={`${BASE_THEME.container.primary} rounded-lg p-3 border ${BASE_THEME.border.default}`}>
          <div className={`text-2xl font-bold ${STORY_THEMES.optimization.text}`}>
            ${((cacheableTokens / 1000) * 0.003 * 0.9).toFixed(4)}
          </div>
          <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Savings per Call</div>
        </div>
        <div className={`${BASE_THEME.container.primary} rounded-lg p-3 border ${BASE_THEME.border.default}`}>
          <div className={`text-2xl font-bold ${STORY_THEMES.latency.text}`}>
            90%
          </div>
          <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Cost Reduction</div>
        </div>
      </div>
    </div>
  );
}
