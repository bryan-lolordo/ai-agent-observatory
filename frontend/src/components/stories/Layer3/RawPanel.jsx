/**
 * RawPanel - Universal raw data view for Layer 3
 *
 * Shows expandable sections for:
 * - System prompt
 * - User message
 * - Response
 * - Quality/Judge evaluation (NEW)
 * - Model config
 * - Token breakdown
 * - Cost details
 * - Timing details
 * - Full JSON
 *
 * UPDATED:
 * - Added qualityEvaluation prop for judge JSON display
 * - Uses theme system - no hardcoded colors!
 */

import { useState } from 'react';
import { BASE_THEME } from '../../../utils/themeUtils';

function ExpandableSection({ title, tokens, content, defaultExpanded = false, highlight = false }) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const handleCopy = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(typeof content === 'string' ? content : JSON.stringify(content, null, 2));
  };

  return (
    <div className={`${BASE_THEME.container.secondary} border rounded-lg overflow-hidden ${highlight ? BASE_THEME.status.warning.border : BASE_THEME.border.default}`}>
      <div
        className={`flex justify-between items-center p-4 cursor-pointer ${BASE_THEME.state.hover} transition-colors`}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <span className={BASE_THEME.text.secondary}>{expanded ? '▼' : '▶'}</span>
          <span className={`font-medium ${BASE_THEME.text.secondary}`}>{title}</span>
          {tokens && (
            <span className={`text-sm ${BASE_THEME.text.muted}`}>
              ({typeof tokens === 'number' ? tokens.toLocaleString() : tokens} tokens)
            </span>
          )}
          {highlight && (
            <span className={`text-xs px-2 py-0.5 ${BASE_THEME.status.warning.bg} ${BASE_THEME.status.warning.text} rounded`}>
              Judge Output
            </span>
          )}
        </div>
        <button
          onClick={handleCopy}
          className={`text-xs px-2 py-1 ${BASE_THEME.container.primary} hover:bg-gray-600 ${BASE_THEME.text.secondary} rounded`}
        >
          Copy
        </button>
      </div>
      {expanded && content && (
        <div className={`p-4 border-t ${BASE_THEME.border.default} ${BASE_THEME.container.primary}`}>
          <pre className={`text-sm ${BASE_THEME.text.secondary} whitespace-pre-wrap font-mono overflow-x-auto max-h-96 overflow-y-auto`}>
            {typeof content === 'string' ? content : JSON.stringify(content, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default function RawPanel({
  // Main content sections
  sections = [], // [{ title, tokens?, content, defaultExpanded?, highlight? }]
  
  // Or pass individual items for backward compatibility
  systemPrompt = null,
  systemPromptTokens = null,
  userMessage = null,
  userMessageTokens = null,
  response = null,
  responseTokens = null,
  modelConfig = null,
  tokenBreakdown = null,
  timingDetails = null,
  costDetails = null,
  
  // NEW: Quality/Judge evaluation
  qualityEvaluation = null,
  
  // Full data fallback
  fullData = null,
}) {
  // Build sections from individual props if sections not provided
  const allSections = sections.length > 0 ? sections : [
    systemPrompt && {
      title: '📝 System Prompt',
      tokens: systemPromptTokens,
      content: systemPrompt,
    },
    userMessage && {
      title: '💬 User Message',
      tokens: userMessageTokens,
      content: userMessage,
    },
    response && {
      title: '📤 Response',
      tokens: responseTokens,
      content: response,
    },
    qualityEvaluation && {
      title: '⭐ Judge Evaluation',
      content: qualityEvaluation,
      highlight: true,
      defaultExpanded: true,
    },
    modelConfig && {
      title: '⚙️ Model Configuration',
      content: modelConfig,
    },
    tokenBreakdown && {
      title: '🔢 Token Breakdown',
      content: tokenBreakdown,
    },
    costDetails && {
      title: '💰 Cost Details',
      content: costDetails,
    },
    timingDetails && {
      title: '⏱️ Timing Details',
      content: timingDetails,
    },
    fullData && {
      title: '📋 Full JSON',
      content: fullData,
    },
  ].filter(Boolean);

  if (allSections.length === 0) {
    return (
      <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-6 text-center`}>
        <div className={BASE_THEME.text.muted}>No raw data available</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {allSections.map((section, idx) => (
        <ExpandableSection
          key={section.title || idx}
          title={section.title}
          tokens={section.tokens}
          content={section.content}
          defaultExpanded={section.defaultExpanded}
          highlight={section.highlight}
        />
      ))}
    </div>
  );
}