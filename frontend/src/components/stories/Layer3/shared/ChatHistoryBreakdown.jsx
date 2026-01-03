/**
 * ChatHistoryBreakdown - Visual conversation history analysis
 * Shows color-coded breakdown of chat messages with optimization opportunities
 */

import { useState } from 'react';

// Updated with vibrant rainbow colors - using circle bullets
const STATUS_COLORS = {
  cacheable: 'bg-purple-500',   // Purple for caching
  current: 'bg-green-500',      // Green for current/active
  recent: 'bg-pink-500',        // Pink for recent (more vibrant)
  old: 'bg-amber-500',          // Amber for old
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
              className="bg-gray-900 rounded-lg border border-gray-700 overflow-hidden"
            >
              {/* Header - Always visible */}
              <div
                onClick={() => toggleExpanded(idx)}
                className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-800/50 transition-colors"
              >
                {/* Left side */}
                <div className="flex items-center gap-3 flex-1">
                  {/* Color indicator - circle bullet */}
                  <div className={`w-3 h-3 ${statusColor} rounded-full flex-shrink-0`} />

                  {/* Label and stats */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-gray-200">{message.label}</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${statusColor} bg-opacity-20`}>
                        {statusLabel}
                      </span>
                    </div>

                    {/* Progress bar with stats on same line */}
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-700 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`${statusColor} h-full`}
                          style={{ width: `${Math.max(message.percentage, 2)}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-400 font-mono w-24 text-right flex-shrink-0">
                        {message.tokens.toLocaleString()} tokens
                      </span>
                      <span className="text-xs text-gray-500 w-12 text-right flex-shrink-0">
                        {message.percentage.toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  {/* Expand/collapse icon */}
                  <span className="text-gray-500 text-sm flex-shrink-0">
                    {isExpanded ? '▼' : '▶'}
                  </span>
                </div>
              </div>

              {/* Expanded details - Show actual message content */}
              {isExpanded && (
                <div className="border-t border-gray-700 p-4 bg-gray-800/30">
                  {/* Message content */}
                  {message.content && (
                    <div className="mb-3">
                      <div className="text-xs text-gray-500 mb-2">Content:</div>
                      <div className="text-sm text-gray-300 bg-gray-900 rounded p-3 max-h-64 overflow-y-auto font-mono whitespace-pre-wrap">
                        {message.content}
                      </div>
                    </div>
                  )}

                  {/* Optimization suggestion */}
                  {message.status === 'old' && (
                    <div className="mt-3 p-2 bg-gray-800 border border-gray-600 rounded text-xs">
                      <span className="text-amber-400 font-medium">💡 Optimization:</span>
                      <span className="text-gray-300 ml-2">
                        This old turn could be summarized or removed to reduce context
                      </span>
                    </div>
                  )}
                  {message.status === 'cacheable' && (
                    <div className="mt-3 p-2 bg-gray-800 border border-gray-600 rounded text-xs">
                      <span className="text-purple-400 font-medium">💡 Optimization:</span>
                      <span className="text-gray-300 ml-2">
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

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="bg-gray-900 rounded-lg p-3 border border-gray-700">
          <div className="text-2xl font-bold text-amber-400">
            {messages.filter(m => m.status === 'old').reduce((sum, m) => sum + m.tokens, 0).toLocaleString()}
          </div>
          <div className="text-xs text-gray-500 mt-1">Old Tokens</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 border border-gray-700">
          <div className="text-2xl font-bold text-purple-400">
            {messages.filter(m => m.status === 'cacheable').reduce((sum, m) => sum + m.tokens, 0).toLocaleString()}
          </div>
          <div className="text-xs text-gray-500 mt-1">Cacheable Tokens</div>
        </div>
        <div className="bg-gray-900 rounded-lg p-3 border border-gray-700">
          <div className="text-2xl font-bold text-green-400">
            {messages.filter(m => m.status === 'current').reduce((sum, m) => sum + m.tokens, 0).toLocaleString()}
          </div>
          <div className="text-xs text-gray-500 mt-1">Current Input</div>
        </div>
      </div>
    </div>
  );
}