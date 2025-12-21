/**
 * DiagnosePanel - Universal diagnosis view for Layer 3
 * 
 * Shows:
 * - Primary issue / healthy state
 * - Time or metric breakdown (configurable)
 * - Contributing factors list
 * - Optional additional breakdowns
 */

import { SeverityBadge } from './shared';

export default function DiagnosePanel({
  // Primary diagnosis data
  factors = [],
  primaryFactor = null,
  
  // Health state
  isHealthy = false,
  healthyMessage = 'Performing within normal parameters.',
  
  // Breakdown components (passed as rendered components)
  breakdownComponent = null,
  breakdownTitle = 'Breakdown',
  breakdownSubtext = null,
  
  // Additional breakdown (e.g., prompt composition)
  additionalBreakdown = null,
  additionalBreakdownTitle = null,
  
  // Actions
  onViewFix,
  
  // Theme
  theme = {},
}) {
  const primary = primaryFactor || factors[0];

  return (
    <div className="space-y-6">
      {/* Primary Issue or Healthy State */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-5">
        <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wide mb-4">
          {isHealthy ? '✅ Health Status' : '🎯 Root Cause'}
        </h3>

        {isHealthy ? (
          <div className="bg-green-900/20 border border-green-800 rounded-lg p-5">
            <h4 className="text-lg font-semibold text-green-400 mb-2">
              No Issues Detected
            </h4>
            <p className="text-slate-300">{healthyMessage}</p>
          </div>
        ) : primary ? (
          <div
            className={`border rounded-lg p-5 ${
              primary.severity === 'critical'
                ? 'bg-red-900/20 border-red-800'
                : 'bg-yellow-900/20 border-yellow-800'
            }`}
          >
            <div className="flex items-center gap-3 mb-3">
              <SeverityBadge severity={primary.severity} />
              <h4
                className={`text-lg font-semibold ${
                  primary.severity === 'critical' ? 'text-red-400' : 'text-yellow-400'
                }`}
              >
                {primary.label}
              </h4>
            </div>
            <p className="text-slate-300 mb-2">{primary.description}</p>
            {primary.impact && (
              <p className="text-slate-400">Impact: {primary.impact}</p>
            )}
          </div>
        ) : null}
      </div>

      {/* Breakdown (e.g., Time breakdown, Cache breakdown) */}
      {breakdownComponent && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-5">
          <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wide mb-4">
            {breakdownTitle}
          </h3>
          {breakdownComponent}
          {breakdownSubtext && (
            <div className="mt-4 text-sm text-slate-500">{breakdownSubtext}</div>
          )}
        </div>
      )}

      {/* All Contributing Factors */}
      {factors.length > 0 && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-5">
          <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wide mb-4">
            📋 Contributing Factors ({factors.length})
          </h3>
          <div className="space-y-3">
            {factors.map((factor) => (
              <div
                key={factor.id}
                className={`border rounded-lg p-4 ${
                  factor.severity === 'critical'
                    ? 'border-red-800 bg-red-900/10'
                    : factor.severity === 'warning'
                    ? 'border-yellow-800 bg-yellow-900/10'
                    : 'border-slate-700 bg-slate-900/50'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <SeverityBadge severity={factor.severity} />
                    <span className="text-slate-200 font-medium">{factor.label}</span>
                  </div>
                  {onViewFix && factor.hasFix !== false && (
                    <button
                      onClick={() => onViewFix(factor.id)}
                      className="text-sm px-3 py-1 bg-orange-600/30 hover:bg-orange-600/50 text-orange-300 rounded transition-colors"
                    >
                      View Fix →
                    </button>
                  )}
                </div>
                {factor.impact && (
                  <p className="text-sm text-slate-400">{factor.impact}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Additional Breakdown (e.g., Prompt composition) */}
      {additionalBreakdown && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-5">
          {additionalBreakdownTitle && (
            <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wide mb-4">
              {additionalBreakdownTitle}
            </h3>
          )}
          {additionalBreakdown}
        </div>
      )}
    </div>
  );
}