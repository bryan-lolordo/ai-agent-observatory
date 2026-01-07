/**
 * StatusBadge Component
 *
 * Displays status indicators (🔴🟡🟢) or text badges.
 * Used in tables and story headers.
 *
 * UPDATED: Uses BASE_THEME - no hardcoded colors!
 */

import { Badge } from '../ui/badge';
import { BASE_THEME } from '../../utils/themeUtils';

/**
 * @param {object} props
 * @param {string} props.status - Status: 'ok', 'warning', 'error'
 * @param {string} props.variant - Display variant: 'emoji' or 'text'
 * @param {string} props.size - Size: 'sm', 'md', 'lg'
 * @param {string} props.className - Additional CSS classes
 */
export default function StatusBadge({ 
  status, 
  variant = 'emoji',
  size = 'md',
  className = '' 
}) {
  // Emoji indicators
  const statusEmojis = {
    ok: '🟢',
    warning: '🟡',
    error: '🔴',
  };

  // Text labels
  const statusLabels = {
    ok: 'OK',
    warning: 'Warning',
    error: 'Critical',
  };

  // Badge variants for shadcn/ui
  const badgeVariants = {
    ok: 'default',
    warning: 'secondary',
    error: 'destructive',
  };

  // Size classes
  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-0.5',
    lg: 'text-base px-3 py-1',
  };

  if (variant === 'emoji') {
    return (
      <span className={`text-${size === 'sm' ? 'base' : size === 'lg' ? '2xl' : 'lg'} ${className}`}>
        {statusEmojis[status] || '⚪'}
      </span>
    );
  }

  return (
    <Badge 
      variant={badgeVariants[status]} 
      className={`${sizeClasses[size]} ${className}`}
    >
      {statusLabels[status] || status}
    </Badge>
  );
}

/**
 * HealthScore Component
 *
 * Displays health score with color coding
 * Uses BASE_THEME.status for colors
 */
export function HealthScore({ score, showLabel = true, className = '' }) {
  const getColor = (score) => {
    if (score >= 80) return BASE_THEME.status.success.text;
    if (score >= 50) return BASE_THEME.status.warning.text;
    return BASE_THEME.status.error.text;
  };

  const getStatus = (score) => {
    if (score >= 80) return 'Healthy';
    if (score >= 50) return 'Warning';
    return 'Critical';
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span className={`text-2xl font-bold ${getColor(score)}`}>
        {Math.round(score)}
      </span>
      {showLabel && (
        <span className={`text-sm ${BASE_THEME.text.muted}`}>
          / 100 {getStatus(score)}
        </span>
      )}
    </div>
  );
}