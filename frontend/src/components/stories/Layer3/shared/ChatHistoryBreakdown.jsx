/**
 * ChatHistoryBreakdown - Visual conversation history analysis
 * Shows color-coded breakdown of chat messages with optimization opportunities
 *
 * UPDATED: Uses theme system - no hardcoded colors!
 */

import { useState } from 'react';
import { BASE_THEME } from '../../../../utils/themeUtils';
import { STORY_THEMES } from '../../../../config/theme';

// Status colors mapped to story themes
const STATUS_COLORS = {
  cacheable: STORY_THEMES.routing.bg.replace('bg-', 'bg-'),  // Purple for caching
  current: STORY_THEMES.optimization.bg.replace('bg-', 'bg-'), // Green for current/active
  recent: STORY_THEMES.cache.bg.replace('bg-', 'bg-'),       // Pink for recent
  old: STORY_THEMES.cost.bg.replace('bg-', 'bg-'),           // Amber for old
};

// Text colors for summary stats
const STATUS_TEXT_COLORS = {
  cacheable: STORY_THEMES.routing.text,
  current: STORY_THEMES.optimization.text,
  recent: STORY_THEMES.cache.text,
  old: STORY_THEMES.cost.text,
};

const STATUS_LABELS = {
  cacheable: 'CACHEABLE',
  current: 'CURRENT',
  recent: 'RECENT',
  old: 'OLD - Could summarize',
};

export default function ChatHistoryBreakdown({
  messages = [],
  insights = [],
  total_tokens = 0,
}) {
  const [expanded, setExpanded] = useState({});

  if (messages.length === 0) return null;

  const toggleExpanded = (idx) => {
    setExpanded(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  return (
    <div className="space-y-4">
      {/* Visual Breakdown */}
      <div className="space-y-2">
        {messages.map((message, idx) => {
          const isExpanded = expanded[idx];
          const statusColor = STATUS_COLORS[message.status] || 'bg-gray-500';
          const statusLabel = STATUS_LABELS[message.status] || message.status;

          return (
            <div
              key={idx}
              className={`${BASE_THEME.container.primary} rounded-lg border ${BASE_THEME.border.default} overflow-hidden`}
            >
              {/* Header - Always visible */}
              <div
                onClick={() => toggleExpanded(idx)}
                className={`flex items-center justify-between p-3 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
              >
                {/* Left side */}
                <div className="flex items-center gap-3 flex-1">
                  {/* Color indicator - circle bullet */}
                  <div className={`w-3 h-3 ${statusColor} rounded-full flex-shrink-0`} />

                  {/* Label and stats */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`font-medium ${BASE_THEME.text.primary}`}>{message.label}</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${statusColor} bg-opacity-20`}>
                        {statusLabel}
                      </span>
                    </div>

                    {/* Progress bar with stats on same line */}
                    <div className="flex items-center gap-2">
                      <div className={`flex-1 ${BASE_THEME.border.default.replace('border', 'bg')} rounded-full h-1.5 overflow-hidden`}>
                        <div
                          className={`${statusColor} h-full`}
                          style={{ width: `${Math.max(message.percentage, 2)}%` }}
                        />
                      </div>
                      <span className={`text-xs ${BASE_THEME.text.secondary} font-mono w-24 text-right flex-shrink-0`}>
                        {message.tokens.toLocaleString()} tokens
                      </span>
                      <span className={`text-xs ${BASE_THEME.text.muted} w-12 text-right flex-shrink-0`}>
                        {message.percentage.toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  {/* Expand/collapse icon */}
                  <span className={`${BASE_THEME.text.muted} text-sm flex-shrink-0`}>
                    {isExpanded ? '▼' : '▶'}
                  </span>
                </div>
              </div>

              {/* Expanded details - Show actual message content */}
              {isExpanded && (
                <div className={`border-t ${BASE_THEME.border.default} p-4 ${BASE_THEME.container.secondary}/30`}>
                  {/* Message content */}
                  {message.content && (
                    <div className="mb-3">
                      <div className={`text-xs ${BASE_THEME.text.muted} mb-2`}>Content:</div>
                      <div className={`text-sm ${BASE_THEME.text.secondary} ${BASE_THEME.container.primary} rounded p-3 max-h-64 overflow-y-auto font-mono whitespace-pre-wrap`}>
                        {message.content}
                      </div>
                    </div>
                  )}

                  {/* Optimization suggestion */}
                  {message.status === 'old' && (
                    <div className={`mt-3 p-2 ${BASE_THEME.container.secondary} border ${BASE_THEME.border.light} rounded text-xs`}>
                      <span className={`${STATUS_TEXT_COLORS.old} font-medium`}>💡 Optimization:</span>
                      <span className={`${BASE_THEME.text.secondary} ml-2`}>
                        This old turn could be summarized or removed to reduce context
                      </span>
                    </div>
                  )}
                  {message.status === 'cacheable' && (
                    <div className={`mt-3 p-2 ${BASE_THEME.container.secondary} border ${BASE_THEME.border.light} rounded text-xs`}>
                      <span className={`${STATUS_TEXT_COLORS.cacheable} font-medium`}>💡 Optimization:</span>
                      <span className={`${BASE_THEME.text.secondary} ml-2`}>
                        Static content - enable caching for 90% cost reduction on repeated calls
                      </span>
                    </div>
                  )}
                </div>
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

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-3 text-center">
        <div className={`${BASE_THEME.container.primary} rounded-lg p-3 border ${BASE_THEME.border.default}`}>
          <div className={`text-2xl font-bold ${STATUS_TEXT_COLORS.old}`}>
            {messages.filter(m => m.status === 'old').reduce((sum, m) => sum + m.tokens, 0).toLocaleString()}
          </div>
          <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Old Tokens</div>
        </div>
        <div className={`${BASE_THEME.container.primary} rounded-lg p-3 border ${BASE_THEME.border.default}`}>
          <div className={`text-2xl font-bold ${STATUS_TEXT_COLORS.cacheable}`}>
            {messages.filter(m => m.status === 'cacheable').reduce((sum, m) => sum + m.tokens, 0).toLocaleString()}
          </div>
          <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Cacheable Tokens</div>
        </div>
        <div className={`${BASE_THEME.container.primary} rounded-lg p-3 border ${BASE_THEME.border.default}`}>
          <div className={`text-2xl font-bold ${STATUS_TEXT_COLORS.current}`}>
            {messages.filter(m => m.status === 'current').reduce((sum, m) => sum + m.tokens, 0).toLocaleString()}
          </div>
          <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>Current Input</div>
        </div>
      </div>
    </div>
  );
}
