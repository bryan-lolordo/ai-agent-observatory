/**
 * SeverityBadge - Displays severity level with icon and color
 *
 * UPDATED:
 * - WARNING badge uses outlined style (variation 1.2), larger font
 * - Uses theme system via getSeverityColors from themeUtils
 */

import { getSeverityColors, BASE_THEME } from '../../../../utils/themeUtils';

// Severity styles mapping using theme system
const SEVERITY_STYLES = {
  critical: {
    bg: BASE_THEME.status.error.bg,
    text: BASE_THEME.status.error.text,
    border: BASE_THEME.status.error.border,
    icon: '🔴',
  },
  warning: {
    // Variation 1.2: Outlined style
    bg: 'bg-transparent',
    text: BASE_THEME.status.warning.text,
    border: `${BASE_THEME.status.warning.border} border-2`,
    icon: '🟡',
  },
  info: {
    bg: BASE_THEME.status.info.bg,
    text: BASE_THEME.status.info.text,
    border: BASE_THEME.status.info.border,
    icon: '🔵',
  },
  ok: {
    bg: BASE_THEME.status.success.bg,
    text: BASE_THEME.status.success.text,
    border: BASE_THEME.status.success.border,
    icon: '🟢',
  },
};

export default function SeverityBadge({ severity }) {
  const style = SEVERITY_STYLES[severity] || SEVERITY_STYLES.info;

  return (
    <span className={`px-3 py-1 rounded text-sm border ${style.bg} ${style.text} ${style.border} font-semibold`}>
      {style.icon} {severity.toUpperCase()}
    </span>
  );
}
