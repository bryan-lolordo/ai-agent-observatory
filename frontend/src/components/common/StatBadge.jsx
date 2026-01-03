/**
 * StatBadge - Display summary statistics
 * 
 * Small badge for showing key metrics in summary bars.
 * Used in Layer 2 operation detail pages.
 * 
 * Uses BASE_THEME for neutral colors - no hardcoded grays!
 */

import { BASE_THEME } from '../../utils/themeUtils';

export default function StatBadge({ 
  label, 
  value, 
  theme, 
  color 
}) {
  const textColor = color || (theme ? theme.text : BASE_THEME.text.secondary);
  
  return (
    <div className={`px-4 py-2 ${BASE_THEME.container.primary} rounded-lg border ${BASE_THEME.border.default}`}>
      <span className={`text-xs ${BASE_THEME.text.muted}`}>{label}: </span>
      <span className={`font-semibold ${textColor}`}>{value}</span>
    </div>
  );
}