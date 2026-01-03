/**
 * BackButton - Reusable back navigation button
 *
 * Provides consistent styling and behavior for back navigation
 * across all Layer 2 and Layer 3 pages.
 *
 * UPDATED: Uses theme system - no hardcoded colors!
 */

import { BASE_THEME } from '../../utils/themeUtils';

export default function BackButton({
  onClick,
  label = "Back to Overview",
  theme
}) {
  // Use theme text color if provided, otherwise use info status color from BASE_THEME
  const textColor = theme?.text || BASE_THEME.status.info.text;

  return (
    <button
      onClick={onClick}
      className={`mb-6 flex items-center gap-2 text-sm ${textColor} hover:underline transition-colors`}
    >
      ← {label}
    </button>
  );
}
