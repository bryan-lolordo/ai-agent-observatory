/**
 * KPICard - Reusable KPI display card for Layer 3
 *
 * UPDATED: Uses theme system - no hardcoded colors!
 */

import { BASE_THEME } from '../../../../utils/themeUtils';

export default function KPICard({ label, value, subtext, status = 'neutral', icon, theme }) {
  const statusColors = {
    critical: BASE_THEME.status.error.text,
    warning: BASE_THEME.status.warning.text,
    good: BASE_THEME.status.success.text,
    neutral: theme?.text || BASE_THEME.text.secondary,
  };

  return (
    <div className={`${BASE_THEME.container.secondary} border ${BASE_THEME.border.default} rounded-lg p-4`}>
      <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide mb-1 flex items-center gap-2`}>
        {icon && <span>{icon}</span>}
        {label}
      </div>
      <div className={`text-2xl font-bold ${statusColors[status]}`}>
        {value}
      </div>
      {subtext && (
        <div className={`text-xs ${BASE_THEME.text.muted} mt-1`}>{subtext}</div>
      )}
    </div>
  );
}
