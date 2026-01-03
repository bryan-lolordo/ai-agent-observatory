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
 * Similar to ChatHistoryBreakdown but for caching analysis
 */

import { useState } from 'react';

const MESSAGE_COLORS = {
  cacheable: {
    indicator: 'bg-purple-500',
    bg: 'bg-purple-900/20',
    border: 'border-purple-500/30',
    text: 'text-purple-400',
    tag: 'bg-purple-500/20 text-purple-300',
  },
  not_cacheable: {
    indicator: 'bg-red-500',
    bg: 'bg-red-900/20',
    border: 'border-red-500/30',
    text: 'text-red-400',
    tag: 'bg-red-500/20 text-red-300',
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
        className="flex items-center gap-3 p-4 cursor-pointer hover:bg-gray-800/30 transition-colors"
      >
        {/* Color indicator bar */}
        <div className={`w-1 h-12 ${colors.indicator} rounded-full`} />

        {/* Content */}
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">{icon}</span>
            <span className="font-semibold text-gray-200 uppercase text-sm">
              {role}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded font-semibold ${colors.tag}`}>
              {cacheable ? '✅ CACHEABLE' : '❌ NOT CACHEABLE'}
            </span>
            {cacheable && (
              <span className="text-xs px-2 py-0.5 rounded bg-green-900/30 text-green-400 font-semibold">
                💾 ADD CACHE_CONTROL
              </span>
            )}
          </div>

          {/* Preview text */}
          <div className="text-sm text-gray-400 font-mono mb-2">
            {expanded ? null : `"${preview}"`}
          </div>

          {/* Metadata */}
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>📊 {tokens.toLocaleString()} tokens</span>
            {cacheable && (
              <span className="text-purple-400">
                💰 ${((tokens / 1000) * 0.003 * 0.9).toFixed(4)} saved per call
              </span>
            )}
            <span className="text-gray-600">
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
            className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded text-xs transition-colors"
          >
            Copy Text
          </button>
          {cacheable && cacheControlCode && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleCopyWithCache();
              }}
              className="px-3 py-1 bg-purple-600 hover:bg-purple-500 text-white rounded text-xs transition-colors"
            >
              Copy with Cache
            </button>
          )}
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-gray-700 p-4 bg-gray-900/50">
          <div className="mb-4">
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">
              Full Content
            </div>
            <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono bg-gray-950 p-4 rounded border border-gray-700 max-h-96 overflow-y-auto">
{content}
            </pre>
          </div>

          {/* Code with cache control */}
          {cacheable && cacheControlCode && (
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">
                💾 With Cache Control
              </div>
              <pre className="text-sm text-gray-300 whitespace-pre-wrap font-mono bg-gray-950 p-4 rounded border border-purple-700">
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
        <div className="w-full border-t-2 border-dashed border-purple-500"></div>
      </div>
      <div className="relative flex justify-center">
        <span className="bg-gray-900 px-4 py-1 text-sm font-semibold text-purple-400 border-2 border-purple-500 rounded-full">
          ⚡ CACHE BOUNDARY
        </span>
      </div>
      <div className="mt-2 text-center text-xs text-gray-500">
        <span className="text-purple-400">↑ {above}</span>
        <span className="mx-2">•</span>
        <span className="text-red-400">↓ {below}</span>
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
      <div className="bg-gradient-to-r from-gray-800 to-gray-900 p-5 rounded-lg border border-gray-700">
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-4">
          📊 Prompt Structure Overview
        </h3>
        <div className="grid grid-cols-3 gap-6">
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Total Tokens</div>
            <div className="text-2xl font-bold text-gray-100">{totalTokens.toLocaleString()}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Cacheable</div>
            <div className="text-2xl font-bold text-purple-400">
              {cacheableTokens.toLocaleString()}
              <span className="text-sm text-gray-500 ml-2">({cacheablePercentage.toFixed(1)}%)</span>
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Not Cacheable</div>
            <div className="text-2xl font-bold text-red-400">
              {nonCacheableTokens.toLocaleString()}
              <span className="text-sm text-gray-500 ml-2">({nonCacheablePercentage.toFixed(1)}%)</span>
            </div>
          </div>
        </div>

        {/* Visual progress bar */}
        <div className="mt-4 flex rounded-full h-3 overflow-hidden">
          <div
            className="bg-purple-500"
            style={{ width: `${cacheablePercentage}%` }}
            title={`Cacheable: ${cacheablePercentage.toFixed(1)}%`}
          />
          <div
            className="bg-red-500"
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
        <div className="bg-gray-800 border border-gray-600 rounded-lg p-4">
          <div className="text-sm font-medium text-gray-300 mb-3">💡 Insights</div>
          <ul className="space-y-2">
            {insights.map((insight, idx) => (
              <li key={idx} className="text-sm text-gray-300 flex items-start gap-2">
                <span className="text-gray-500">•</span>
                <span>{insight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Summary Stats - Savings */}
      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="bg-gray-900 rounded-lg p-3 border border-gray-700">
          <div className="text-2xl font-bold text-purple-400">
            {cacheableTokens.toLocaleString()}
          </div>
          <div className="text-xs text-gray-500 mt-1">Cacheable Tokens</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 border border-gray-700">
          <div className="text-2xl font-bold text-green-400">
            ${((cacheableTokens / 1000) * 0.003 * 0.9).toFixed(4)}
          </div>
          <div className="text-xs text-gray-500 mt-1">Savings per Call</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 border border-gray-700">
          <div className="text-2xl font-bold text-orange-400">
            90%
          </div>
          <div className="text-xs text-gray-500 mt-1">Cost Reduction</div>
        </div>
      </div>
    </div>
  );
}