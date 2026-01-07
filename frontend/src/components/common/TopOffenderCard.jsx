/**
 * TopOffenderCard Component
 *
 * Displays the "top offender" or "worst performer" for a story.
 * Used across all Layer 1 index pages.
 *
 * Features:
 * - Colored accent bar matching story theme
 * - Agent.operation display with purple agent color
 * - Flexible stats display
 * - Optional diagnosis/suggestion text
 * - Click handler for navigation
 *
 * Uses BASE_THEME - no hardcoded colors!
 */

import { BASE_THEME } from '../../utils/themeUtils';

export default function TopOffenderCard({
  // Display
  title = '🎯 Top Offender',
  agent,
  operation,
  theme,              // Story theme for accent color

  // Stats - array of { label, value, color? } objects
  stats = [],

  // Optional
  diagnosis,          // Tip/diagnosis text
  onClick,            // Click handler
  className = '',
}) {
  if (!agent && !operation) return null;

  return (
    <div
      onClick={onClick}
      className={`mb-8 rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} overflow-hidden ${
        onClick ? `cursor-pointer hover:${BASE_THEME.border.light} transition-all` : ''
      } ${className}`}
    >
      {/* Colored accent bar */}
      {theme?.bg && <div className={`h-1 ${theme.bg}`} />}

      <div className="p-5">
        {/* Title */}
        <h3 className={`text-xs font-medium ${BASE_THEME.text.muted} uppercase tracking-wide mb-2`}>
          {title}
        </h3>

        {/* Agent.Operation */}
        <div className="flex items-center gap-2 mb-2">
          {agent && (
            <>
              <span className={`text-xl font-bold ${BASE_THEME.status.info.text}`}>{agent}</span>
              <span className={BASE_THEME.text.muted}>.</span>
            </>
          )}
          <span className={`text-xl font-bold ${theme?.text || BASE_THEME.text.primary} font-mono`}>
            {operation}
          </span>
        </div>

        {/* Stats row */}
        {stats.length > 0 && (
          <div className={`flex gap-6 text-sm ${BASE_THEME.text.muted}`}>
            {stats.map((stat, idx) => (
              <span key={idx}>
                {stat.label}: {' '}
                <span className={stat.color || BASE_THEME.text.primary}>
                  {stat.value}
                </span>
              </span>
            ))}
          </div>
        )}

        {/* Diagnosis/tip */}
        {diagnosis && (
          <p className={`text-sm ${BASE_THEME.text.muted} mt-3`}>
            💡 {diagnosis}
          </p>
        )}
      </div>
    </div>
  );
}
