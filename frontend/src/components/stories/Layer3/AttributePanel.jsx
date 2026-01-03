/**
 * AttributePanel - Universal attribution view for Layer 3
 * 
 * Shows where the issue originates:
 * - Model configuration (with highlights)
 * - Response/output analysis
 * - Prompt composition
 * - Custom attribution sections
 */

import { PromptBreakdownBar } from './shared';

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
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-5">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
              📍 Model Configuration
            </h3>
            <button
              onClick={() => navigator.clipboard.writeText(JSON.stringify(modelConfig, null, 2))}
              className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded"
            >
              Copy
            </button>
          </div>
          <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-gray-300">{'{'}</pre>
            {Object.entries(modelConfig).map(([key, value]) => {
              const highlight = configHighlights.find(h => h.key === key);
              const isHighlighted = !!highlight;
              const bgClass = highlight?.severity === 'critical' 
                ? 'bg-red-900/30' 
                : highlight?.severity === 'warning'
                ? 'bg-yellow-900/30'
                : '';
              const textClass = highlight?.severity === 'critical'
                ? 'text-red-400'
                : highlight?.severity === 'warning'
                ? 'text-yellow-400'
                : 'text-gray-300';

              return (
                <pre
                  key={key}
                  className={`${textClass} ${isHighlighted ? `${bgClass} px-3 py-1 -mx-4 my-0.5` : ''}`}
                >
                  {`  "${key}": ${JSON.stringify(value)},`}
                  {highlight?.message && (
                    <span className={`ml-4 ${highlight.severity === 'critical' ? 'text-red-300' : 'text-yellow-300'}`}>
                      ← ⚠️ {highlight.message}
                    </span>
                  )}
                </pre>
              );
            })}
            <pre className="text-gray-300">{'}'}</pre>
          </div>
        </div>
      )}

      {/* Response Analysis */}
      {responseAnalysis && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-5">
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-4">
            📤 Response Analysis
          </h3>
          <div className="bg-gray-900 rounded-lg p-4">
            <div className="flex items-center gap-4 mb-4">
              <span className="px-3 py-1 bg-gray-700 text-gray-300 rounded text-sm uppercase font-medium">
                {responseAnalysis.type}
              </span>
              {responseAnalysis.tokenCount && (
                <span className="text-gray-400">
                  {responseAnalysis.tokenCount.toLocaleString()} tokens
                </span>
              )}
              {responseAnalysis.sectionCount > 0 && (
                <span className="text-gray-400">
                  • {responseAnalysis.sectionCount} sections
                </span>
              )}
            </div>

            {/* Sections if markdown */}
            {responseAnalysis.sections?.length > 0 && (
              <div className="space-y-2 mb-4">
                <div className="text-sm text-gray-500">Detected sections:</div>
                {responseAnalysis.sections.map((section, i) => (
                  <div
                    key={i}
                    className="text-sm text-gray-400 font-mono pl-4 border-l-2 border-gray-700"
                  >
                    ## {section}
                  </div>
                ))}
              </div>
            )}

            {/* Prompt verbosity warning */}
            {promptAnalysis?.encourages_verbosity && (
              <div className="p-3 bg-yellow-900/20 border border-yellow-800 rounded-lg text-sm text-yellow-300">
                ⚠️ Prompt uses verbose language: {promptAnalysis.verbose_indicators?.join(', ')}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Prompt Breakdown */}
      {promptBreakdown && promptBreakdown.total > 0 && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-5">
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-4">
            📝 Prompt Composition
          </h3>
          <PromptBreakdownBar breakdown={promptBreakdown} />
          
          {promptWarning && (
            <div className="mt-4 p-3 bg-red-900/20 border border-red-800 rounded-lg text-sm text-red-300">
              ⚠️ {promptWarning}
            </div>
          )}
        </div>
      )}

      {/* Custom Sections */}
      {customSections.map((section, idx) => (
        <div key={idx} className="bg-gray-800 border border-gray-700 rounded-lg p-5">
          {section.title && (
            <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-4">
              {section.title}
            </h3>
          )}
          {section.content}
        </div>
      ))}
    </div>
  );
}