/**
 * FixPanel - Fix comparison and detail view for Layer 3
 *
 * Two views:
 * 1. Comparison View - Stacked cards with output preview + quick comparison table
 * 2. Detail View - Full code before/after, output preview, tradeoffs/benefits
 *
 * UPDATED:
 * - Uses theme system - no hardcoded colors!
 * - Now includes AI Analysis Panel at the bottom for LLM-powered recommendations
 * - Supports both 'call' and 'pattern' entityTypes
 */

import { useState } from 'react';
import AIAnalysisPanel from './AIAnalysisPanel';
import { BASE_THEME } from '../../../utils/themeUtils';
import { STORY_THEMES } from '../../../config/theme';

// ─────────────────────────────────────────────────────────────────────────────
// FIX CARD (Stacked layout in comparison view)
// ─────────────────────────────────────────────────────────────────────────────

function FixCard({ fix, isImplemented, isRecommended, onSelect, onMarkImplemented, theme }) {
  return (
    <div
      className={`border rounded-lg p-5 transition-colors ${BASE_THEME.container.secondary} ${BASE_THEME.border.default}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h4 className={`font-semibold ${BASE_THEME.text.primary}`}>{fix.title}</h4>
            {isRecommended && <span className={BASE_THEME.status.success.text}>⭐ Recommended</span>}
            {isImplemented && <span className={`${BASE_THEME.status.success.text} text-sm`}>✓ Implemented</span>}
          </div>
          {fix.subtitle && (
            <p className={`text-sm ${BASE_THEME.text.secondary} mt-1`}>{fix.subtitle}</p>
          )}
        </div>
        <span className={`px-3 py-1 rounded text-sm ${fix.effortColor || BASE_THEME.status.success.text} ${BASE_THEME.container.primary}`}>
          {fix.effort} Effort
        </span>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-4 gap-3 mb-4">
        {fix.metrics?.map(metric => (
          <div key={metric.label} className={`${BASE_THEME.container.primary} rounded-lg p-3 text-center`}>
            <div className={`text-lg font-bold ${BASE_THEME.text.primary}`}>
              {metric.after}
            </div>
            <div className={`text-xs ${metric.changePercent < 0 ? BASE_THEME.status.success.text : metric.changePercent > 0 ? BASE_THEME.status.error.text : BASE_THEME.text.muted}`}>
              {metric.changePercent === 0 ? '—' : `${metric.changePercent}%`}
            </div>
            <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>{metric.label}</div>
          </div>
        ))}
      </div>

      {/* Output Preview */}
      {fix.outputPreview && (
        <div className="mb-4">
          <div className={`text-xs ${BASE_THEME.text.muted} uppercase mb-2`}>Output Preview:</div>
          <div className={`${BASE_THEME.container.primary} rounded-lg p-3 border ${BASE_THEME.border.default}`}>
            <pre className={`text-xs ${BASE_THEME.text.secondary} whitespace-pre-wrap font-mono max-h-32 overflow-hidden`}>
              {fix.outputPreview.substring(0, 300)}{fix.outputPreview.length > 300 ? '...' : ''}
            </pre>
            {fix.outputNote && (
              <div className={`text-xs mt-2 ${fix.outputNoteColor || (fix.outputTruncated ? BASE_THEME.status.warning.text : BASE_THEME.status.success.text)}`}>
                {fix.outputNote}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Best For + Actions */}
      <div className="flex justify-between items-center">
        {fix.bestFor && (
          <div className={`text-sm ${BASE_THEME.text.secondary}`}>
            <span className={BASE_THEME.text.muted}>Best for:</span> {fix.bestFor}
          </div>
        )}
        <button
          onClick={() => onSelect(fix.id)}
          className={`px-3 py-1 ${BASE_THEME.container.primary} border ${BASE_THEME.border.default} hover:bg-gray-700 ${theme.text} rounded text-sm`}
        >
          View Details →
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// QUICK COMPARISON TABLE
// ─────────────────────────────────────────────────────────────────────────────

function QuickComparisonTable({ fixes, currentState, theme }) {
  return (
    <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-4 mt-6`}>
      <h3 className={`text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide mb-3`}>
        📊 Quick Comparison
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className={`text-left ${BASE_THEME.text.muted} border-b ${BASE_THEME.border.default}`}>
              <th className="pb-2">Fix</th>
              <th className="pb-2">Latency</th>
              <th className="pb-2">Tokens</th>
              <th className="pb-2">Cost</th>
              <th className="pb-2">Quality</th>
              <th className="pb-2">Effort</th>
            </tr>
          </thead>
          <tbody>
            {/* Current State Row */}
            {currentState && (
              <tr className={`border-b ${BASE_THEME.border.light}`}>
                <td className={`py-2 ${BASE_THEME.text.secondary}`}>Current</td>
                <td className={`py-2 ${BASE_THEME.status.error.text}`}>{currentState.latency}</td>
                <td className={`py-2 ${BASE_THEME.status.error.text}`}>{currentState.tokens}</td>
                <td className={`py-2 ${BASE_THEME.status.warning.text}`}>{currentState.cost}</td>
                <td className={`py-2 ${BASE_THEME.text.secondary}`}>{currentState.quality || '—'}</td>
                <td className="py-2">—</td>
              </tr>
            )}
            {fixes.map(fix => {
              const latencyMetric = fix.metrics?.find(m => m.label === 'Latency');
              const tokensMetric = fix.metrics?.find(m => m.label === 'Tokens');
              const costMetric = fix.metrics?.find(m => m.label === 'Cost');
              const qualityMetric = fix.metrics?.find(m => m.label === 'Quality');

              return (
                <tr key={fix.id} className={`border-b ${BASE_THEME.border.light}`}>
                  <td className={`py-2 ${BASE_THEME.text.primary}`}>{fix.title}</td>
                  <td className={`py-2 ${BASE_THEME.status.success.text}`}>{latencyMetric?.after || '—'}</td>
                  <td className={`py-2 ${BASE_THEME.status.success.text}`}>{tokensMetric?.after || '—'}</td>
                  <td className={`py-2 ${BASE_THEME.status.success.text}`}>{costMetric?.after || '—'}</td>
                  <td className={`py-2 ${qualityMetric?.status === 'warning' ? BASE_THEME.status.warning.text : BASE_THEME.status.success.text}`}>
                    {qualityMetric?.after || '—'}
                  </td>
                  <td className={`py-2 ${fix.effortColor || BASE_THEME.status.success.text}`}>{fix.effort}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// CUMULATIVE IMPACT
// ─────────────────────────────────────────────────────────────────────────────

function CumulativeImpact({ fixes, implementedFixes = [], theme }) {
  if (fixes.length === 0) return null;

  // Calculate cumulative impact
  const allFixes = fixes.filter(f => implementedFixes.includes(f.id));
  const pendingFixes = fixes.filter(f => !implementedFixes.includes(f.id));

  const calculateCumulative = (fixList) => {
    let totalLatency = 0;
    let totalCost = 0;
    let totalTokens = 0;

    fixList.forEach(fix => {
      const latencyMetric = fix.metrics?.find(m => m.label === 'Latency');
      const costMetric = fix.metrics?.find(m => m.label === 'Cost');
      const tokensMetric = fix.metrics?.find(m => m.label === 'Tokens');

      if (latencyMetric?.after) {
        const match = latencyMetric.after.match(/([0-9.]+)/);
        if (match) totalLatency += parseFloat(match[1]);
      }

      if (costMetric?.after) {
        const match = costMetric.after.match(/([0-9.]+)/);
        if (match) totalCost += parseFloat(match[1]);
      }

      if (tokensMetric?.after) {
        const match = tokensMetric.after.replace(/,/g, '').match(/([0-9]+)/);
        if (match) totalTokens += parseInt(match[1]);
      }
    });

    return { totalLatency, totalCost, totalTokens };
  };

  const implemented = calculateCumulative(allFixes);
  const potential = calculateCumulative(pendingFixes);

  return (
    <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-6`}>
      <h3 className={`text-sm font-medium ${theme.text} uppercase tracking-wide mb-4`}>
        📊 Cumulative Impact
      </h3>

      <div className="grid grid-cols-2 gap-6">
        {/* Implemented */}
        {allFixes.length > 0 && (
          <div>
            <div className={`text-sm ${BASE_THEME.text.secondary} mb-3`}>
              ✅ Implemented ({allFixes.length} {allFixes.length === 1 ? 'fix' : 'fixes'})
            </div>
            <div className="space-y-2">
              <div className={`flex items-center justify-between ${BASE_THEME.container.primary} rounded p-3`}>
                <span className={BASE_THEME.text.secondary}>Latency Saved:</span>
                <span className={`${BASE_THEME.status.success.text} font-bold`}>{implemented.totalLatency.toFixed(1)}s</span>
              </div>
              <div className={`flex items-center justify-between ${BASE_THEME.container.primary} rounded p-3`}>
                <span className={BASE_THEME.text.secondary}>Cost Saved:</span>
                <span className={`${BASE_THEME.status.success.text} font-bold`}>${implemented.totalCost.toFixed(3)}</span>
              </div>
              <div className={`flex items-center justify-between ${BASE_THEME.container.primary} rounded p-3`}>
                <span className={BASE_THEME.text.secondary}>Tokens Reduced:</span>
                <span className={`${BASE_THEME.status.success.text} font-bold`}>{implemented.totalTokens.toLocaleString()}</span>
              </div>
            </div>
          </div>
        )}

        {/* Potential */}
        {pendingFixes.length > 0 && (
          <div>
            <div className={`text-sm ${BASE_THEME.text.secondary} mb-3`}>
              ⏳ Remaining ({pendingFixes.length} {pendingFixes.length === 1 ? 'fix' : 'fixes'})
            </div>
            <div className="space-y-2">
              <div className={`flex items-center justify-between ${BASE_THEME.container.primary} rounded p-3`}>
                <span className={BASE_THEME.text.secondary}>Potential Latency:</span>
                <span className={`${theme.text} font-bold`}>-{potential.totalLatency.toFixed(1)}s</span>
              </div>
              <div className={`flex items-center justify-between ${BASE_THEME.container.primary} rounded p-3`}>
                <span className={BASE_THEME.text.secondary}>Potential Cost:</span>
                <span className={`${theme.text} font-bold`}>-${potential.totalCost.toFixed(3)}</span>
              </div>
              <div className={`flex items-center justify-between ${BASE_THEME.container.primary} rounded p-3`}>
                <span className={BASE_THEME.text.secondary}>Potential Tokens:</span>
                <span className={`${theme.text} font-bold`}>-{potential.totalTokens.toLocaleString()}</span>
              </div>
            </div>
          </div>
        )}

        {/* All fixes pending */}
        {allFixes.length === 0 && pendingFixes.length > 0 && (
          <div className="col-span-2">
            <div className={`text-center p-6 ${BASE_THEME.container.primary} border ${BASE_THEME.border.default} rounded-lg`}>
              <div className="text-3xl mb-2">🚀</div>
              <div className={`text-lg font-semibold ${theme.text} mb-2`}>
                Apply All {pendingFixes.length} Fixes
              </div>
              <div className={`text-2xl font-bold ${theme.text} mb-1`}>
                -{potential.totalLatency.toFixed(1)}s • -${potential.totalCost.toFixed(3)} • -{potential.totalTokens.toLocaleString()} tokens
              </div>
              <div className={`text-sm ${BASE_THEME.text.secondary} mt-3`}>
                Estimated total impact if all fixes are implemented
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Progress bar if some implemented */}
      {allFixes.length > 0 && pendingFixes.length > 0 && (
        <div className="mt-6">
          <div className={`flex items-center justify-between text-sm ${BASE_THEME.text.secondary} mb-2`}>
            <span>Implementation Progress</span>
            <span>{allFixes.length} of {fixes.length} applied</span>
          </div>
          <div className={`${BASE_THEME.container.primary} rounded-full h-3 overflow-hidden`}>
            <div
              className={`${STORY_THEMES.optimization.bg} h-full transition-all`}
              style={{ width: `${(allFixes.length / fixes.length) * 100}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// FIX COMPARISON VIEW (with cumulative impact)
// ─────────────────────────────────────────────────────────────────────────────

function FixComparisonView({
  fixes,
  implementedFixes,
  currentState,
  onSelectFix,
  onMarkImplemented,
  theme,
  // AI Analysis props
  entityId,
  entityType,
  responseText,
  aiCallId,
}) {
  const callIdForAI = entityType === 'call' ? entityId : aiCallId;
  const canShowAI = !!callIdForAI;

  if (fixes.length === 0 && !canShowAI) {
    return (
      <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-8 text-center`}>
        <div className="text-4xl mb-4">✅</div>
        <h3 className={`text-lg font-medium ${BASE_THEME.status.success.text} mb-2`}>No Fixes Needed</h3>
        <p className={BASE_THEME.text.secondary}>
          This is already well-optimized. No significant improvements available.
        </p>
      </div>
    );
  }

  const recommendedId = fixes.find(f => f.recommended)?.id || fixes[0]?.id;

  return (
    <div className="space-y-6">
      {/* 1. STATIC FIXES SECTION */}
      {fixes.length > 0 && (
        <>
          {/* Implementation Tracker */}
          {implementedFixes.length > 0 && (
            <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-5`}>
              <h3 className={`text-sm font-medium ${BASE_THEME.status.success.text} uppercase tracking-wide mb-3`}>
                📋 Implementation Progress
              </h3>
              <div className="space-y-2">
                {fixes.map(fix => (
                  <div key={fix.id} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={implementedFixes.includes(fix.id) ? BASE_THEME.status.success.text : BASE_THEME.text.muted}>
                        {implementedFixes.includes(fix.id) ? '☑' : '☐'}
                      </span>
                      <span className={implementedFixes.includes(fix.id) ? BASE_THEME.status.success.text : BASE_THEME.text.secondary}>
                        {fix.title}
                      </span>
                    </div>
                    {implementedFixes.includes(fix.id) && (
                      <button
                        onClick={() => onMarkImplemented(fix.id)}
                        className={`text-xs ${BASE_THEME.text.muted} hover:${BASE_THEME.text.secondary}`}
                      >
                        Undo
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Stacked Fix Cards */}
          <div className="space-y-4">
            {fixes.map(fix => (
              <FixCard
                key={fix.id}
                fix={fix}
                isImplemented={implementedFixes.includes(fix.id)}
                isRecommended={fix.id === recommendedId}
                onSelect={onSelectFix}
                onMarkImplemented={onMarkImplemented}
                theme={theme}
              />
            ))}
          </div>

          {/* 2. QUICK COMPARISON TABLE */}
          <QuickComparisonTable fixes={fixes} currentState={currentState} theme={theme} />

          {/* 3. CUMULATIVE IMPACT */}
          <CumulativeImpact fixes={fixes} implementedFixes={implementedFixes} theme={theme} />
        </>
      )}

      {/* No Static Fixes Message */}
      {fixes.length === 0 && canShowAI && (
        <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-6 text-center`}>
          <div className="text-3xl mb-3">✨</div>
          <h3 className={`text-lg font-medium ${BASE_THEME.text.secondary} mb-2`}>No Rule-Based Fixes Detected</h3>
          <p className={`${BASE_THEME.text.secondary} text-sm`}>
            Try AI Analysis below for deeper, context-aware recommendations.
          </p>
        </div>
      )}

      {/* 4. AI ANALYSIS SECTION */}
      {canShowAI && (
        <div className={`mt-8 pt-8 border-t ${BASE_THEME.border.default}`}>
          <h3 className={`text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide mb-4`}>
            🤖 AI-Powered Analysis
          </h3>
          <AIAnalysisPanel
            callId={callIdForAI}
            responseText={responseText}
          />
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// FIX DETAIL VIEW
// ─────────────────────────────────────────────────────────────────────────────

function FixDetailView({ fix, isImplemented, onBack, onMarkImplemented, similarCount = 0, responseText = null, theme }) {
  const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <button
        onClick={onBack}
        className={`${theme.text} hover:opacity-80 text-sm flex items-center gap-2`}
      >
        ← Back to Comparison
      </button>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className={`text-xl font-semibold ${BASE_THEME.text.primary}`}>{fix.title}</h2>
            {fix.recommended && <span className={BASE_THEME.status.success.text}>⭐</span>}
          </div>
          {fix.subtitle && (
            <p className={`${BASE_THEME.text.secondary} mt-1`}>{fix.subtitle}</p>
          )}
        </div>
        <span className={`px-3 py-1 rounded ${fix.effortColor || BASE_THEME.status.success.text} ${BASE_THEME.container.primary}`}>
          {fix.effort} Effort
        </span>
      </div>

      {/* Metrics - Large KPI Cards */}
      {fix.metrics && fix.metrics.length > 0 && (
        <div className="grid grid-cols-4 gap-4">
          {fix.metrics.map(metric => (
            <div key={metric.label} className={`${BASE_THEME.container.primary} rounded-lg p-4 text-center`}>
              <div className={`text-3xl font-bold ${BASE_THEME.status.success.text}`}>{metric.after}</div>
              <div className={`text-sm ${metric.changePercent < 0 ? BASE_THEME.status.success.text : metric.changePercent > 0 ? BASE_THEME.status.error.text : BASE_THEME.text.muted}`}>
                {metric.changePercent === 0 ? '—' : `${metric.changePercent}%`}
              </div>
              <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>{metric.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Code Before/After */}
      <div>
        <h3 className={`text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide mb-3`}>
          💻 Implementation
        </h3>

        {fix.codeBefore && fix.codeAfter ? (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className={`text-xs ${BASE_THEME.status.error.text} font-medium`}>BEFORE</span>
                <button
                  onClick={() => handleCopy(fix.codeBefore)}
                  className={`text-xs px-2 py-1 ${BASE_THEME.container.secondary} hover:bg-gray-600 ${BASE_THEME.text.secondary} rounded`}
                >
                  Copy
                </button>
              </div>
              <pre className={`${BASE_THEME.container.primary} rounded-lg p-4 text-sm font-mono ${BASE_THEME.text.secondary} overflow-x-auto max-h-64 overflow-y-auto`}>
                {fix.codeBefore}
              </pre>
            </div>
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className={`text-xs ${BASE_THEME.status.success.text} font-medium`}>AFTER</span>
                <button
                  onClick={() => handleCopy(fix.codeAfter)}
                  className={`text-xs px-2 py-1 ${BASE_THEME.status.success.bg} hover:opacity-80 ${BASE_THEME.status.success.text} rounded`}
                >
                  Copy
                </button>
              </div>
              <pre className={`${BASE_THEME.container.primary} rounded-lg p-4 text-sm font-mono ${BASE_THEME.text.secondary} overflow-x-auto max-h-64 overflow-y-auto border ${BASE_THEME.border.default}`}>
                {fix.codeAfter}
              </pre>
            </div>
          </div>
        ) : fix.codeAfter ? (
          <div>
            <div className="flex justify-between items-center mb-2">
              <span className={`text-xs ${BASE_THEME.status.success.text} font-medium`}>IMPLEMENTATION</span>
              <button
                onClick={() => handleCopy(fix.codeAfter)}
                className={`text-xs px-2 py-1 ${BASE_THEME.container.secondary} hover:bg-gray-600 ${BASE_THEME.text.secondary} rounded`}
              >
                Copy
              </button>
            </div>
            <pre className={`${BASE_THEME.container.primary} rounded-lg p-4 text-sm font-mono ${BASE_THEME.text.secondary} overflow-x-auto max-h-64 overflow-y-auto`}>
              {fix.codeAfter}
            </pre>
          </div>
        ) : null}
      </div>

      {/* Output Before/After - OUTPUT CHANGE section */}
      {(fix.outputBefore || fix.outputAfter || responseText) && (
        <div>
          <h3 className={`text-sm font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide mb-3`}>
            📦 Output Change
          </h3>

          {/* Generate predicted output based on fix type if not provided */}
          {(() => {
            const beforeOutput = fix.outputBefore || responseText;

            // Generate predicted "after" output based on fix type
            let afterOutput = fix.outputAfter;
            let afterTokens = fix.outputAfterTokens;
            let isTruncated = fix.outputTruncated;
            let afterNote = fix.outputNote;
            let afterNoteColor = fix.outputNoteColor;

            // If no outputAfter but we have responseText, generate predicted output
            if (!afterOutput && responseText && fix.id) {
              // Latency fixes
              if (fix.id === 'add_max_tokens') {
                const truncateAt = 1500;
                if (responseText.length > truncateAt) {
                  let cutPoint = responseText.lastIndexOf(' ', truncateAt);
                  if (cutPoint < truncateAt - 200) cutPoint = truncateAt;
                  afterOutput = responseText.substring(0, cutPoint) + '...';
                  isTruncated = true;
                  afterTokens = 500;
                  afterNote = '⚠️ STOPS HERE - Cut off at 500 tokens';
                  afterNoteColor = BASE_THEME.status.warning.text;
                } else {
                  afterOutput = responseText;
                  afterTokens = Math.round(responseText.length / 4);
                }
              } else if (fix.id === 'simplify_prompt') {
                afterOutput = fix.outputPreview || responseText.substring(0, 800);
                afterTokens = 200;
              } else if (fix.id === 'enable_streaming') {
                afterOutput = responseText;
                afterTokens = Math.round(responseText.length / 4);
                afterNote = '✅ Same output, but user sees tokens as they generate';
                afterNoteColor = BASE_THEME.status.success.text;
              } else if (fix.id === 'truncate_history') {
                afterOutput = responseText;
                afterNote = '✅ Same output quality with less input context';
                afterNoteColor = BASE_THEME.status.success.text;
              }
              // Cache fixes
              else if (fix.id === 'simple_cache' || fix.id === 'redis_cache' || fix.id === 'lru_cache' || fix.id === 'enable_caching') {
                afterOutput = responseText;
                afterTokens = Math.round(responseText.length / 4);
                afterNote = '✅ Identical output served instantly from cache';
                afterNoteColor = BASE_THEME.status.success.text;
              }
              // Quality fixes
              else if (fix.id === 'add_accuracy_constraints') {
                afterOutput = responseText;
                afterNote = '✅ Same content with verified accuracy';
                afterNoteColor = BASE_THEME.status.success.text;
              } else if (fix.id === 'enforce_sections') {
                afterOutput = responseText;
                afterNote = '✅ Guaranteed to include all required sections';
                afterNoteColor = BASE_THEME.status.success.text;
              } else if (fix.id === 'add_examples') {
                afterOutput = responseText;
                afterNote = '✅ Higher quality output following examples';
                afterNoteColor = BASE_THEME.status.success.text;
              } else if (fix.id === 'adjust_temperature') {
                afterOutput = responseText;
                afterNote = '✅ More creative/varied output';
                afterNoteColor = BASE_THEME.status.success.text;
              }
              // Token fixes
              else if (fix.id === 'simplify_system_prompt') {
                afterOutput = responseText;
                afterNote = '✅ Same output with reduced input tokens';
                afterNoteColor = BASE_THEME.status.success.text;
              } else if (fix.id === 'request_longer_output') {
                afterOutput = responseText + '\n\n[Extended analysis would continue here with more detail...]';
                afterNote = '📝 Output extended to provide more detail';
                afterNoteColor = BASE_THEME.status.info.text;
              } else if (fix.id === 'combined_optimization') {
                afterOutput = responseText;
                afterNote = '✅ Optimized input/output balance';
                afterNoteColor = BASE_THEME.status.success.text;
              }
              // Cost fixes
              else if (fix.id === 'switch_model') {
                afterOutput = responseText;
                afterNote = '✅ Similar output from cheaper model';
                afterNoteColor = BASE_THEME.status.success.text;
              } else if (fix.id === 'reduce_tokens') {
                const truncateAt = 1200;
                if (responseText.length > truncateAt) {
                  let cutPoint = responseText.lastIndexOf(' ', truncateAt);
                  if (cutPoint < truncateAt - 200) cutPoint = truncateAt;
                  afterOutput = responseText.substring(0, cutPoint) + '...';
                  isTruncated = true;
                  afterNote = '⚠️ Output truncated to reduce cost';
                  afterNoteColor = BASE_THEME.status.warning.text;
                } else {
                  afterOutput = responseText;
                }
              }
            }

            // Estimate token count from response length if not provided
            const beforeTokens = fix.outputBeforeTokens || (responseText ? Math.round(responseText.length / 4) : null);

            if (beforeOutput && afterOutput) {
              return (
                <div className="space-y-4">
                  {/* BEFORE */}
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className={`text-xs ${BASE_THEME.text.secondary}`}>BEFORE (Actual Response)</span>
                      {beforeTokens && (
                        <span className={`text-xs ${BASE_THEME.text.muted}`}>{beforeTokens.toLocaleString()} tokens</span>
                      )}
                    </div>
                    <div className={`${BASE_THEME.container.primary} rounded-lg p-4 border ${BASE_THEME.border.default} max-h-48 overflow-y-auto`}>
                      <pre className={`text-sm font-mono ${BASE_THEME.text.secondary} whitespace-pre-wrap`}>
                        {typeof beforeOutput === 'string' ? beforeOutput.substring(0, 1500) : beforeOutput}
                        {typeof beforeOutput === 'string' && beforeOutput.length > 1500 ? '...' : ''}
                      </pre>
                    </div>
                  </div>

                  {/* Arrow */}
                  <div className="flex justify-center">
                    <span className={`${BASE_THEME.text.muted} text-lg`}>↓</span>
                  </div>

                  {/* AFTER */}
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className={`text-xs ${isTruncated ? BASE_THEME.status.warning.text : BASE_THEME.status.success.text}`}>
                        AFTER (Predicted)
                      </span>
                      {afterTokens && (
                        <span className={`text-xs ${BASE_THEME.text.muted}`}>~{afterTokens.toLocaleString()} tokens</span>
                      )}
                    </div>
                    <div className={`${BASE_THEME.container.primary} rounded-lg p-4 border max-h-48 overflow-y-auto ${BASE_THEME.border.default}`}>
                      <pre className={`text-sm font-mono ${BASE_THEME.text.secondary} whitespace-pre-wrap`}>
                        {afterOutput}
                      </pre>
                    </div>
                    {afterNote && (
                      <div className={`text-xs mt-2 ${afterNoteColor || BASE_THEME.status.success.text}`}>
                        {afterNote}
                      </div>
                    )}
                  </div>
                </div>
              );
            } else if (fix.outputPreview) {
              return (
                <div className={`${BASE_THEME.container.primary} rounded-lg p-4 border ${BASE_THEME.border.default}`}>
                  <pre className={`text-sm font-mono ${BASE_THEME.text.secondary} whitespace-pre-wrap max-h-48 overflow-y-auto`}>
                    {fix.outputPreview}
                  </pre>
                  {fix.outputNote && (
                    <div className={`mt-3 pt-3 border-t ${BASE_THEME.border.default} ${fix.outputNoteColor || BASE_THEME.status.success.text} text-sm font-medium`}>
                      {fix.outputNote}
                    </div>
                  )}
                </div>
              );
            } else if (beforeOutput) {
              return (
                <div>
                  <div className={`text-xs ${BASE_THEME.text.secondary} mb-2`}>Current Output</div>
                  <div className={`${BASE_THEME.container.primary} rounded-lg p-4 border ${BASE_THEME.border.default} max-h-48 overflow-y-auto`}>
                    <pre className={`text-sm font-mono ${BASE_THEME.text.secondary} whitespace-pre-wrap`}>
                      {typeof beforeOutput === 'string' ? beforeOutput.substring(0, 500) : beforeOutput}
                      {typeof beforeOutput === 'string' && beforeOutput.length > 500 ? '...' : ''}
                    </pre>
                  </div>
                </div>
              );
            }
            return null;
          })()}
        </div>
      )}

      {/* Trade-offs & Benefits */}
      {(fix.tradeoffs?.length > 0 || fix.benefits?.length > 0) && (
        <div className="grid grid-cols-2 gap-4">
          {fix.tradeoffs?.length > 0 && (
            <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-4`}>
              <h4 className={`text-sm font-medium ${BASE_THEME.status.error.text} mb-3`}>⚠️ Trade-offs</h4>
              <ul className="space-y-2">
                {fix.tradeoffs.map((t, i) => (
                  <li key={i} className={`text-sm ${BASE_THEME.text.secondary} flex items-start gap-2`}>
                    <span>•</span> {t}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {fix.benefits?.length > 0 && (
            <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-4`}>
              <h4 className={`text-sm font-medium ${BASE_THEME.status.success.text} mb-3`}>✅ Benefits</h4>
              <ul className="space-y-2">
                {fix.benefits.map((b, i) => (
                  <li key={i} className={`text-sm ${BASE_THEME.text.secondary} flex items-start gap-2`}>
                    <span>•</span> {b}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Best For */}
      {fix.bestFor && (
        <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-4`}>
          <span className={`text-sm ${theme.text} font-medium`}>✅ Best For: </span>
          <span className={`text-sm ${BASE_THEME.text.secondary}`}>{fix.bestFor}</span>
        </div>
      )}

      {/* Similar Count */}
      {similarCount > 1 && (
        <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-4`}>
          <div className={`text-sm ${BASE_THEME.text.secondary}`}>
            <span className={`${theme.text} font-medium`}>{similarCount} similar calls</span> have this same issue.
            Fixing this will multiply your savings by {similarCount}x.
          </div>
        </div>
      )}

      {/* Bottom Actions */}
      <div className={`flex justify-end gap-3 pt-4 border-t ${BASE_THEME.border.default}`}>
        <button
          onClick={onBack}
          className={`px-4 py-2 ${BASE_THEME.container.secondary} ${BASE_THEME.text.secondary} rounded-lg text-sm`}
        >
          ← Back to Compare
        </button>
        <button
          onClick={() => handleCopy(fix.codeAfter || '')}
          className={`px-4 py-2 ${BASE_THEME.container.secondary} ${BASE_THEME.text.secondary} rounded-lg text-sm`}
        >
          Copy Code
        </button>
        <button
          onClick={() => onMarkImplemented(fix.id)}
          className={`px-4 py-2 rounded-lg text-sm ${
            isImplemented
              ? `${BASE_THEME.status.success.bg} text-white`
              : `${theme.bg} hover:opacity-80 text-white`
          }`}
        >
          {isImplemented ? '☑ Implemented' : 'Apply This Fix ✓'}
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

export default function FixPanel({
  fixes = [],
  implementedFixes = [],
  currentState = null,
  onMarkImplemented,
  similarCount = 0,
  // Theme prop for story-specific colors
  theme = STORY_THEMES.latency,
  // AI Analysis props (passed from Layer3Shell)
  entityId = null,
  entityType = 'call',
  responseText = null,
  // For patterns - pass first call ID for AI analysis
  aiCallId = null,
}) {
  const [selectedFixId, setSelectedFixId] = useState(null);

  const selectedFix = fixes.find(f => f.id === selectedFixId);

  if (selectedFix) {
    return (
      <FixDetailView
        fix={selectedFix}
        isImplemented={implementedFixes.includes(selectedFix.id)}
        onBack={() => setSelectedFixId(null)}
        onMarkImplemented={onMarkImplemented}
        similarCount={similarCount}
        responseText={responseText}
        theme={theme}
      />
    );
  }

  return (
    <FixComparisonView
      fixes={fixes}
      implementedFixes={implementedFixes}
      currentState={currentState}
      onSelectFix={setSelectedFixId}
      onMarkImplemented={onMarkImplemented}
      theme={theme}
      // Pass AI Analysis props
      entityId={entityId}
      entityType={entityType}
      responseText={responseText}
      aiCallId={aiCallId}
    />
  );
}
