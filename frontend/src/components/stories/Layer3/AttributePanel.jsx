/**
 * AttributePanel - Universal attribution view for Layer 3
 *
 * Shows where the issue originates:
 * - Model configuration (with highlights)
 * - Response/output analysis
 * - Prompt composition
 * - Custom attribution sections
 *
 * UPDATED: Uses theme system - no hardcoded colors!
 */

import { PromptBreakdownBar } from './shared';
import { BASE_THEME } from '../../../utils/themeUtils';

export default function AttributePanel({
  // Model config
  modelConfig = null,
  configHighlights = [], // [{ key, message, severity }]

  // Response analysis
  responseAnalysis = null, // { type, sections, tokenCount, ... }

  // Prompt analysis
  promptAnalysis = null, // { verbose_indicators, ... }
  promptBreakdown = null, // { system, user, history, tools, total }
  promptWarning = null, // String message if there's an issue

  // Custom sections (for story-specific attribution)
  customSections = [], // [{ title, content: ReactNode }]

  // Theme
  theme = {},
}) {
  return (
    <div className="space-y-6">
      {/* Model Configuration */}
      {modelConfig && (
        <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-5`}>
          <div className="flex justify-between items-center mb-4">
            <h3 className={`text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide`}>
              📍 Model Configuration
            </h3>
            <button
              onClick={() => navigator.clipboard.writeText(JSON.stringify(modelConfig, null, 2))}
              className={`text-xs px-2 py-1 ${BASE_THEME.container.primary} hover:bg-gray-600 ${BASE_THEME.text.secondary} rounded`}
            >
              Copy
            </button>
          </div>
          <div className={`${BASE_THEME.container.primary} rounded-lg p-4 font-mono text-sm overflow-x-auto`}>
            <pre className={BASE_THEME.text.secondary}>{'{'}</pre>
            {Object.entries(modelConfig).map(([key, value]) => {
              const highlight = configHighlights.find(h => h.key === key);
              const isHighlighted = !!highlight;
              const bgClass = highlight?.severity === 'critical'
                ? BASE_THEME.status.error.bg
                : highlight?.severity === 'warning'
                ? BASE_THEME.status.warning.bg
                : '';
              const textClass = highlight?.severity === 'critical'
                ? BASE_THEME.status.error.text
                : highlight?.severity === 'warning'
                ? BASE_THEME.status.warning.text
                : BASE_THEME.text.secondary;

              return (
                <pre
                  key={key}
                  className={`${textClass} ${isHighlighted ? `${bgClass} px-3 py-1 -mx-4 my-0.5` : ''}`}
                >
                  {`  "${key}": ${JSON.stringify(value)},`}
                  {highlight?.message && (
                    <span className={`ml-4 ${highlight.severity === 'critical' ? BASE_THEME.status.error.text : BASE_THEME.status.warning.text}`}>
                      ← ⚠️ {highlight.message}
                    </span>
                  )}
                </pre>
              );
            })}
            <pre className={BASE_THEME.text.secondary}>{'}'}</pre>
          </div>
        </div>
      )}

      {/* Response Analysis */}
      {responseAnalysis && (
        <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-5`}>
          <h3 className={`text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide mb-4`}>
            📤 Response Analysis
          </h3>
          <div className={`${BASE_THEME.container.primary} rounded-lg p-4`}>
            <div className="flex items-center gap-4 mb-4">
              <span className={`px-3 py-1 ${BASE_THEME.container.secondary} ${BASE_THEME.text.secondary} rounded text-sm uppercase font-medium`}>
                {responseAnalysis.type}
              </span>
              {responseAnalysis.tokenCount && (
                <span className={BASE_THEME.text.secondary}>
                  {responseAnalysis.tokenCount.toLocaleString()} tokens
                </span>
              )}
              {responseAnalysis.sectionCount > 0 && (
                <span className={BASE_THEME.text.secondary}>
                  • {responseAnalysis.sectionCount} sections
                </span>
              )}
            </div>

            {/* Sections if markdown */}
            {responseAnalysis.sections?.length > 0 && (
              <div className="space-y-2 mb-4">
                <div className={`text-sm ${BASE_THEME.text.muted}`}>Detected sections:</div>
                {responseAnalysis.sections.map((section, i) => (
                  <div
                    key={i}
                    className={`text-sm ${BASE_THEME.text.secondary} font-mono pl-4 border-l-2 ${BASE_THEME.border.default}`}
                  >
                    ## {section}
                  </div>
                ))}
              </div>
            )}

            {/* Prompt verbosity warning */}
            {promptAnalysis?.encourages_verbosity && (
              <div className={`p-3 ${BASE_THEME.status.warning.bg} border ${BASE_THEME.status.warning.border} rounded-lg text-sm ${BASE_THEME.status.warning.text}`}>
                ⚠️ Prompt uses verbose language: {promptAnalysis.verbose_indicators?.join(', ')}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Prompt Breakdown */}
      {promptBreakdown && promptBreakdown.total > 0 && (
        <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-5`}>
          <h3 className={`text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide mb-4`}>
            📝 Prompt Composition
          </h3>
          <PromptBreakdownBar breakdown={promptBreakdown} />

          {promptWarning && (
            <div className={`mt-4 p-3 ${BASE_THEME.status.error.bg} border ${BASE_THEME.status.error.border} rounded-lg text-sm ${BASE_THEME.status.error.text}`}>
              ⚠️ {promptWarning}
            </div>
          )}
        </div>
      )}

      {/* Custom Sections */}
      {customSections.map((section, idx) => (
        <div key={idx} className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-5`}>
          {section.title && (
            <h3 className={`text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide mb-4`}>
              {section.title}
            </h3>
          )}
          {section.content}
        </div>
      ))}
    </div>
  );
}
