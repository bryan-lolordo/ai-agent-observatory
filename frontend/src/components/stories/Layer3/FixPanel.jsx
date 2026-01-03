/**
 * FixPanel - Fix comparison and detail view for Layer 3
 * 
 * Two views:
 * 1. Comparison View - Stacked cards with output preview + quick comparison table
 * 2. Detail View - Full code before/after, output preview, tradeoffs/benefits
 * 
 * UPDATED: 
 * - Now includes AI Analysis Panel at the bottom for LLM-powered recommendations
 * - Supports both 'call' and 'pattern' entityTypes
 */

import { useState } from 'react';
import AIAnalysisPanel from './AIAnalysisPanel';

// ─────────────────────────────────────────────────────────────────────────────
// FIX CARD (Stacked layout in comparison view)
// ─────────────────────────────────────────────────────────────────────────────

function FixCard({ fix, isImplemented, isRecommended, onSelect, onMarkImplemented }) {
  return (
    <div
      className={`border rounded-lg p-5 transition-colors ${
        isImplemented
          ? 'border-green-700 bg-green-900/20'
          : isRecommended
          ? 'border-orange-600 bg-orange-900/10'
          : 'border-gray-700 bg-gray-800'
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h4 className="font-semibold text-gray-200">{fix.title}</h4>
            {isRecommended && <span className="text-green-400">⭐ Recommended</span>}
            {isImplemented && <span className="text-green-400 text-sm">✓ Implemented</span>}
          </div>
          {fix.subtitle && (
            <p className="text-sm text-gray-400 mt-1">{fix.subtitle}</p>
          )}
        </div>
        <span className={`px-3 py-1 rounded text-sm ${fix.effortColor || 'text-green-400'} bg-gray-900`}>
          {fix.effort} Effort
        </span>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-4 gap-3 mb-4">
        {fix.metrics?.map(metric => (
          <div key={metric.label} className="bg-gray-900 rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-gray-200">
              {metric.after}
            </div>
            <div className={`text-xs ${metric.changePercent < 0 ? 'text-green-400' : metric.changePercent > 0 ? 'text-red-400' : 'text-gray-500'}`}>
              {metric.changePercent === 0 ? '—' : `${metric.changePercent}%`}
            </div>
            <div className="text-xs text-gray-500 mt-1">{metric.label}</div>
          </div>
        ))}
      </div>

      {/* Output Preview */}
      {fix.outputPreview && (
        <div className="mb-4">
          <div className="text-xs text-gray-500 uppercase mb-2">Output Preview:</div>
          <div className={`bg-gray-900 rounded-lg p-3 border ${
            fix.outputTruncated ? 'border-yellow-800' : 'border-green-800'
          }`}>
            <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono max-h-32 overflow-hidden">
              {fix.outputPreview.substring(0, 300)}{fix.outputPreview.length > 300 ? '...' : ''}
            </pre>
            {fix.outputNote && (
              <div className={`text-xs mt-2 ${fix.outputNoteColor || (fix.outputTruncated ? 'text-yellow-400' : 'text-green-400')}`}>
                {fix.outputNote}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Best For + Actions */}
      <div className="flex justify-between items-center">
        {fix.bestFor && (
          <div className="text-sm text-gray-400">
            <span className="text-gray-500">Best for:</span> {fix.bestFor}
          </div>
        )}
        <button
          onClick={() => onSelect(fix.id)}
          className="px-3 py-1 bg-orange-600/30 hover:bg-orange-600/50 text-orange-400 rounded text-sm"
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

function QuickComparisonTable({ fixes, currentState }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 mt-6">
      <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">
        📊 Quick Comparison
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-700">
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
              <tr className="border-b border-gray-700/50">
                <td className="py-2 text-gray-400">Current</td>
                <td className="py-2 text-red-400">{currentState.latency}</td>
                <td className="py-2 text-red-400">{currentState.tokens}</td>
                <td className="py-2 text-yellow-400">{currentState.cost}</td>
                <td className="py-2 text-gray-300">{currentState.quality || '—'}</td>
                <td className="py-2">—</td>
              </tr>
            )}
            {fixes.map(fix => {
              const latencyMetric = fix.metrics?.find(m => m.label === 'Latency');
              const tokensMetric = fix.metrics?.find(m => m.label === 'Tokens');
              const costMetric = fix.metrics?.find(m => m.label === 'Cost');
              const qualityMetric = fix.metrics?.find(m => m.label === 'Quality');
              
              return (
                <tr key={fix.id} className="border-b border-gray-700/50">
                  <td className="py-2 text-gray-200">{fix.title}</td>
                  <td className="py-2 text-green-400">{latencyMetric?.after || '—'}</td>
                  <td className="py-2 text-green-400">{tokensMetric?.after || '—'}</td>
                  <td className="py-2 text-green-400">{costMetric?.after || '—'}</td>
                  <td className={`py-2 ${qualityMetric?.status === 'warning' ? 'text-yellow-400' : 'text-green-400'}`}>
                    {qualityMetric?.after || '—'}
                  </td>
                  <td className={`py-2 ${fix.effortColor || 'text-green-400'}`}>{fix.effort}</td>
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
// CUMULATIVE IMPACT (NEW)
// ─────────────────────────────────────────────────────────────────────────────

function CumulativeImpact({ fixes, implementedFixes = [] }) {
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
        // Extract numeric value (e.g., "2.0s" -> 2.0)
        const match = latencyMetric.after.match(/([0-9.]+)/);
        if (match) totalLatency += parseFloat(match[1]);
      }

      if (costMetric?.after) {
        // Extract numeric value (e.g., "$0.05" -> 0.05)
        const match = costMetric.after.match(/([0-9.]+)/);
        if (match) totalCost += parseFloat(match[1]);
      }

      if (tokensMetric?.after) {
        // Extract numeric value (e.g., "500" or "1,200" -> 1200)
        const match = tokensMetric.after.replace(/,/g, '').match(/([0-9]+)/);
        if (match) totalTokens += parseInt(match[1]);
      }
    });

    return { totalLatency, totalCost, totalTokens };
  };

  const implemented = calculateCumulative(allFixes);
  const potential = calculateCumulative(pendingFixes);

  return (
    <div className="bg-gradient-to-br from-purple-900/20 to-gray-900 border border-purple-600/30 rounded-lg p-6">
      <h3 className="text-sm font-medium text-purple-300 uppercase tracking-wide mb-4">
        📊 Cumulative Impact
      </h3>

      <div className="grid grid-cols-2 gap-6">
        {/* Implemented */}
        {allFixes.length > 0 && (
          <div>
            <div className="text-sm text-gray-400 mb-3">
              ✅ Implemented ({allFixes.length} {allFixes.length === 1 ? 'fix' : 'fixes'})
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between bg-gray-800/50 rounded p-3">
                <span className="text-gray-400">Latency Saved:</span>
                <span className="text-green-400 font-bold">{implemented.totalLatency.toFixed(1)}s</span>
              </div>
              <div className="flex items-center justify-between bg-gray-800/50 rounded p-3">
                <span className="text-gray-400">Cost Saved:</span>
                <span className="text-green-400 font-bold">${implemented.totalCost.toFixed(3)}</span>
              </div>
              <div className="flex items-center justify-between bg-gray-800/50 rounded p-3">
                <span className="text-gray-400">Tokens Reduced:</span>
                <span className="text-green-400 font-bold">{implemented.totalTokens.toLocaleString()}</span>
              </div>
            </div>
          </div>
        )}

        {/* Potential */}
        {pendingFixes.length > 0 && (
          <div>
            <div className="text-sm text-gray-400 mb-3">
              ⏳ Remaining ({pendingFixes.length} {pendingFixes.length === 1 ? 'fix' : 'fixes'})
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between bg-gray-800/50 rounded p-3">
                <span className="text-gray-400">Potential Latency:</span>
                <span className="text-orange-400 font-bold">-{potential.totalLatency.toFixed(1)}s</span>
              </div>
              <div className="flex items-center justify-between bg-gray-800/50 rounded p-3">
                <span className="text-gray-400">Potential Cost:</span>
                <span className="text-orange-400 font-bold">-${potential.totalCost.toFixed(3)}</span>
              </div>
              <div className="flex items-center justify-between bg-gray-800/50 rounded p-3">
                <span className="text-gray-400">Potential Tokens:</span>
                <span className="text-orange-400 font-bold">-{potential.totalTokens.toLocaleString()}</span>
              </div>
            </div>
          </div>
        )}

        {/* All fixes pending */}
        {allFixes.length === 0 && pendingFixes.length > 0 && (
          <div className="col-span-2">
            <div className="text-center p-6 bg-orange-900/20 border border-orange-700 rounded-lg">
              <div className="text-3xl mb-2">🚀</div>
              <div className="text-lg font-semibold text-orange-300 mb-2">
                Apply All {pendingFixes.length} Fixes
              </div>
              <div className="text-2xl font-bold text-orange-400 mb-1">
                -{potential.totalLatency.toFixed(1)}s • -${potential.totalCost.toFixed(3)} • -{potential.totalTokens.toLocaleString()} tokens
              </div>
              <div className="text-sm text-gray-400 mt-3">
                Estimated total impact if all fixes are implemented
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Progress bar if some implemented */}
      {allFixes.length > 0 && pendingFixes.length > 0 && (
        <div className="mt-6">
          <div className="flex items-center justify-between text-sm text-gray-400 mb-2">
            <span>Implementation Progress</span>
            <span>{allFixes.length} of {fixes.length} applied</span>
          </div>
          <div className="bg-gray-700 rounded-full h-3 overflow-hidden">
            <div
              className="bg-gradient-to-r from-green-500 to-green-400 h-full transition-all"
              style={{ width: `${(allFixes.length / fixes.length) * 100}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// UPDATED FIX COMPARISON VIEW (with cumulative impact)
// ─────────────────────────────────────────────────────────────────────────────

function FixComparisonView({
  fixes,
  implementedFixes,
  currentState,
  onSelectFix,
  onMarkImplemented,
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
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-8 text-center">
        <div className="text-4xl mb-4">✅</div>
        <h3 className="text-lg font-medium text-green-400 mb-2">No Fixes Needed</h3>
        <p className="text-gray-400">
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
            <div className="bg-green-900/20 border border-green-800 rounded-lg p-5">
              <h3 className="text-sm font-medium text-green-400 uppercase tracking-wide mb-3">
                📋 Implementation Progress
              </h3>
              <div className="space-y-2">
                {fixes.map(fix => (
                  <div key={fix.id} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={implementedFixes.includes(fix.id) ? 'text-green-400' : 'text-gray-500'}>
                        {implementedFixes.includes(fix.id) ? '☑' : '☐'}
                      </span>
                      <span className={implementedFixes.includes(fix.id) ? 'text-green-300' : 'text-gray-400'}>
                        {fix.title}
                      </span>
                    </div>
                    {implementedFixes.includes(fix.id) && (
                      <button
                        onClick={() => onMarkImplemented(fix.id)}
                        className="text-xs text-gray-500 hover:text-gray-300"
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
              />
            ))}
          </div>

          {/* 2. QUICK COMPARISON TABLE */}
          <QuickComparisonTable fixes={fixes} currentState={currentState} />

          {/* 3. CUMULATIVE IMPACT (NEW) */}
          <CumulativeImpact fixes={fixes} implementedFixes={implementedFixes} />
        </>
      )}

      {/* No Static Fixes Message */}
      {fixes.length === 0 && canShowAI && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 text-center">
          <div className="text-3xl mb-3">✨</div>
          <h3 className="text-lg font-medium text-gray-300 mb-2">No Rule-Based Fixes Detected</h3>
          <p className="text-gray-400 text-sm">
            Try AI Analysis below for deeper, context-aware recommendations.
          </p>
        </div>
      )}

      {/* 4. AI ANALYSIS SECTION */}
      {canShowAI && (
        <div className="mt-8 pt-8 border-t border-gray-700">
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-4">
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

function FixDetailView({ fix, isImplemented, onBack, onMarkImplemented, similarCount = 0, responseText = null }) {
  const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="text-orange-400 hover:text-orange-300 text-sm flex items-center gap-2"
      >
        ← Back to Comparison
      </button>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-semibold text-gray-200">{fix.title}</h2>
            {fix.recommended && <span className="text-green-400">⭐</span>}
          </div>
          {fix.subtitle && (
            <p className="text-gray-400 mt-1">{fix.subtitle}</p>
          )}
        </div>
        <span className={`px-3 py-1 rounded ${fix.effortColor || 'text-green-400'} bg-gray-900`}>
          {fix.effort} Effort
        </span>
      </div>

      {/* Metrics - Large KPI Cards */}
      {fix.metrics && fix.metrics.length > 0 && (
        <div className="grid grid-cols-4 gap-4">
          {fix.metrics.map(metric => (
            <div key={metric.label} className="bg-gray-900 rounded-lg p-4 text-center">
              <div className="text-3xl font-bold text-green-400">{metric.after}</div>
              <div className={`text-sm ${metric.changePercent < 0 ? 'text-green-500' : metric.changePercent > 0 ? 'text-red-500' : 'text-gray-500'}`}>
                {metric.changePercent === 0 ? '—' : `${metric.changePercent}%`}
              </div>
              <div className="text-xs text-gray-500 mt-1">{metric.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Code Before/After */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">
          💻 Implementation
        </h3>
        
        {fix.codeBefore && fix.codeAfter ? (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs text-red-400 font-medium">BEFORE</span>
                <button
                  onClick={() => handleCopy(fix.codeBefore)}
                  className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded"
                >
                  Copy
                </button>
              </div>
              <pre className="bg-gray-900 rounded-lg p-4 text-sm font-mono text-gray-300 overflow-x-auto max-h-64 overflow-y-auto">
                {fix.codeBefore}
              </pre>
            </div>
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs text-green-400 font-medium">AFTER</span>
                <button
                  onClick={() => handleCopy(fix.codeAfter)}
                  className="text-xs px-2 py-1 bg-green-900/50 hover:bg-green-900/70 text-green-300 rounded"
                >
                  Copy
                </button>
              </div>
              <pre className="bg-gray-900 rounded-lg p-4 text-sm font-mono text-gray-300 overflow-x-auto max-h-64 overflow-y-auto border border-green-800">
                {fix.codeAfter}
              </pre>
            </div>
          </div>
        ) : fix.codeAfter ? (
          <div>
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs text-green-400 font-medium">IMPLEMENTATION</span>
              <button
                onClick={() => handleCopy(fix.codeAfter)}
                className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded"
              >
                Copy
              </button>
            </div>
            <pre className="bg-gray-900 rounded-lg p-4 text-sm font-mono text-gray-300 overflow-x-auto max-h-64 overflow-y-auto">
              {fix.codeAfter}
            </pre>
          </div>
        ) : null}
      </div>

      {/* Output Before/After - OUTPUT CHANGE section */}
      {(fix.outputBefore || fix.outputAfter || responseText) && (
        <div>
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide mb-3">
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
                  afterNoteColor = 'text-yellow-400';
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
                afterNoteColor = 'text-green-400';
              } else if (fix.id === 'truncate_history') {
                afterOutput = responseText;
                afterNote = '✅ Same output quality with less input context';
                afterNoteColor = 'text-green-400';
              }
              // Cache fixes
              else if (fix.id === 'simple_cache' || fix.id === 'redis_cache' || fix.id === 'lru_cache' || fix.id === 'enable_caching') {
                afterOutput = responseText;
                afterTokens = Math.round(responseText.length / 4);
                afterNote = '✅ Identical output served instantly from cache';
                afterNoteColor = 'text-green-400';
              }
              // Quality fixes
              else if (fix.id === 'add_accuracy_constraints') {
                afterOutput = responseText;
                afterNote = '✅ Same content with verified accuracy';
                afterNoteColor = 'text-green-400';
              } else if (fix.id === 'enforce_sections') {
                afterOutput = responseText;
                afterNote = '✅ Guaranteed to include all required sections';
                afterNoteColor = 'text-green-400';
              } else if (fix.id === 'add_examples') {
                afterOutput = responseText;
                afterNote = '✅ Higher quality output following examples';
                afterNoteColor = 'text-green-400';
              } else if (fix.id === 'adjust_temperature') {
                afterOutput = responseText;
                afterNote = '✅ More creative/varied output';
                afterNoteColor = 'text-green-400';
              }
              // Token fixes
              else if (fix.id === 'simplify_system_prompt') {
                afterOutput = responseText;
                afterNote = '✅ Same output with reduced input tokens';
                afterNoteColor = 'text-green-400';
              } else if (fix.id === 'request_longer_output') {
                afterOutput = responseText + '\n\n[Extended analysis would continue here with more detail...]';
                afterNote = '📝 Output extended to provide more detail';
                afterNoteColor = 'text-blue-400';
              } else if (fix.id === 'combined_optimization') {
                afterOutput = responseText;
                afterNote = '✅ Optimized input/output balance';
                afterNoteColor = 'text-green-400';
              }
              // Cost fixes
              else if (fix.id === 'switch_model') {
                afterOutput = responseText;
                afterNote = '✅ Similar output from cheaper model';
                afterNoteColor = 'text-green-400';
              } else if (fix.id === 'reduce_tokens') {
                const truncateAt = 1200;
                if (responseText.length > truncateAt) {
                  let cutPoint = responseText.lastIndexOf(' ', truncateAt);
                  if (cutPoint < truncateAt - 200) cutPoint = truncateAt;
                  afterOutput = responseText.substring(0, cutPoint) + '...';
                  isTruncated = true;
                  afterNote = '⚠️ Output truncated to reduce cost';
                  afterNoteColor = 'text-yellow-400';
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
                      <span className="text-xs text-gray-400">BEFORE (Actual Response)</span>
                      {beforeTokens && (
                        <span className="text-xs text-gray-500">{beforeTokens.toLocaleString()} tokens</span>
                      )}
                    </div>
                    <div className="bg-gray-900 rounded-lg p-4 border border-gray-700 max-h-48 overflow-y-auto">
                      <pre className="text-sm font-mono text-gray-300 whitespace-pre-wrap">
                        {typeof beforeOutput === 'string' ? beforeOutput.substring(0, 1500) : beforeOutput}
                        {typeof beforeOutput === 'string' && beforeOutput.length > 1500 ? '...' : ''}
                      </pre>
                    </div>
                  </div>
                  
                  {/* Arrow */}
                  <div className="flex justify-center">
                    <span className="text-gray-600 text-lg">↓</span>
                  </div>
                  
                  {/* AFTER */}
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className={`text-xs ${isTruncated ? 'text-yellow-400' : 'text-green-400'}`}>
                        AFTER (Predicted)
                      </span>
                      {afterTokens && (
                        <span className="text-xs text-gray-500">~{afterTokens.toLocaleString()} tokens</span>
                      )}
                    </div>
                    <div className={`bg-gray-900 rounded-lg p-4 border max-h-48 overflow-y-auto ${
                      isTruncated ? 'border-yellow-800' : 'border-green-800'
                    }`}>
                      <pre className="text-sm font-mono text-gray-300 whitespace-pre-wrap">
                        {afterOutput}
                      </pre>
                    </div>
                    {afterNote && (
                      <div className={`text-xs mt-2 ${afterNoteColor || 'text-green-400'}`}>
                        {afterNote}
                      </div>
                    )}
                  </div>
                </div>
              );
            } else if (fix.outputPreview) {
              return (
                <div className={`bg-gray-900 rounded-lg p-4 border ${
                  fix.outputTruncated ? 'border-yellow-800' : 'border-green-800'
                }`}>
                  <pre className="text-sm font-mono text-gray-300 whitespace-pre-wrap max-h-48 overflow-y-auto">
                    {fix.outputPreview}
                  </pre>
                  {fix.outputNote && (
                    <div className={`mt-3 pt-3 border-t border-gray-700 ${fix.outputNoteColor || 'text-green-400'} text-sm font-medium`}>
                      {fix.outputNote}
                    </div>
                  )}
                </div>
              );
            } else if (beforeOutput) {
              return (
                <div>
                  <div className="text-xs text-gray-400 mb-2">Current Output</div>
                  <div className="bg-gray-900 rounded-lg p-4 border border-gray-700 max-h-48 overflow-y-auto">
                    <pre className="text-sm font-mono text-gray-400 whitespace-pre-wrap">
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
            <div className="bg-red-900/20 border border-red-800 rounded-lg p-4">
              <h4 className="text-sm font-medium text-red-400 mb-3">⚠️ Trade-offs</h4>
              <ul className="space-y-2">
                {fix.tradeoffs.map((t, i) => (
                  <li key={i} className="text-sm text-red-300 flex items-start gap-2">
                    <span>•</span> {t}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {fix.benefits?.length > 0 && (
            <div className="bg-green-900/20 border border-green-800 rounded-lg p-4">
              <h4 className="text-sm font-medium text-green-400 mb-3">✅ Benefits</h4>
              <ul className="space-y-2">
                {fix.benefits.map((b, i) => (
                  <li key={i} className="text-sm text-green-300 flex items-start gap-2">
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
        <div className="bg-orange-900/20 border border-orange-700 rounded-lg p-4">
          <span className="text-sm text-orange-400 font-medium">✅ Best For: </span>
          <span className="text-sm text-orange-300">{fix.bestFor}</span>
        </div>
      )}

      {/* Similar Count */}
      {similarCount > 1 && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
          <div className="text-sm text-gray-400">
            <span className="text-orange-400 font-medium">{similarCount} similar calls</span> have this same issue. 
            Fixing this will multiply your savings by {similarCount}x.
          </div>
        </div>
      )}

      {/* Bottom Actions */}
      <div className="flex justify-end gap-3 pt-4 border-t border-gray-700">
        <button
          onClick={onBack}
          className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg text-sm"
        >
          ← Back to Compare
        </button>
        <button
          onClick={() => handleCopy(fix.codeAfter || '')}
          className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg text-sm"
        >
          Copy Code
        </button>
        <button
          onClick={() => onMarkImplemented(fix.id)}
          className={`px-4 py-2 rounded-lg text-sm ${
            isImplemented
              ? 'bg-green-600 text-white'
              : 'bg-orange-600 hover:bg-orange-500 text-white'
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
      // Pass AI Analysis props
      entityId={entityId}
      entityType={entityType}
      responseText={responseText}
      aiCallId={aiCallId}
    />
  );
}