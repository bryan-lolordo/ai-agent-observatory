/**
 * KPICard Component
 * 
 * Displays a key performance indicator with rainbow theme support.
 * Used across all story pages for metric display.
 * 
 * UPDATED: Now uses BASE_THEME for consistent colors - no more hardcoded grays!
 */

import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { BASE_THEME } from '../../utils/themeUtils';

/**
 * @param {object} props
 * @param {object} props.theme - Story theme from STORY_THEMES (optional)
 * @param {string} props.title - Card title (e.g., "Avg Latency")
 * @param {string|number} props.value - Main value (e.g., "2.11s" or 85.5)
 * @param {string} props.subtitle - Optional subtitle (e.g., "(>5s threshold)")
 * @param {string} props.status - Optional status: 'ok', 'warning', 'error'
 * @param {string} props.icon - Optional icon (Lucide icon name)
 * @param {string} props.trend - Optional trend indicator: 'up', 'down', 'neutral'
 * @param {function} props.onClick - Optional click handler for drill-down
 * @param {string} props.className - Additional CSS classes
 */
export default function KPICard({
  theme,
  title,
  value,
  subtitle,
  status,
  icon: Icon,
  trend,
  onClick,
  className = '',
}) {
  // Trend indicators
  const trendIcons = {
    up: '↑',
    down: '↓',
    neutral: '→',
  };

  // Status colors using BASE_THEME
  const statusColors = {
    ok: BASE_THEME.status.success.text,
    warning: BASE_THEME.status.warning.text,
    error: BASE_THEME.status.error.text,
  };

  // Rainbow themed version (for Layer 1 overview pages)
  if (theme) {
    const isClickable = !!onClick;
    
    return (
      <div 
        onClick={onClick}
        className={`rounded-lg border-2 ${theme.border} bg-gradient-to-br ${theme.gradient} p-6 ${
          isClickable ? `cursor-pointer ${theme.borderHover} transition-all` : ''
        } ${className}`}
      >
        <p className={`text-sm ${theme.textLight} mb-2 flex items-center gap-2`}>
          {Icon && <Icon className="h-4 w-4" />}
          {title}
        </p>
        <div className={`text-3xl font-bold ${theme.text} flex items-baseline gap-2`}>
          {value}
          {trend && (
            <span className={`text-sm font-normal ${BASE_THEME.text.muted}`}>
              {trendIcons[trend]}
            </span>
          )}
        </div>
        {subtitle && (
          <p className={`text-xs ${BASE_THEME.text.muted} mt-1`}>
            {subtitle}
          </p>
        )}
      </div>
    );
  }

  // Default non-themed version (for generic KPI cards)
  const valueColor = status ? statusColors[status] : BASE_THEME.text.primary;
  const isClickable = !!onClick;

  return (
    <Card 
      onClick={onClick}
      className={`${BASE_THEME.state.hover} transition-shadow border ${BASE_THEME.border.default} ${BASE_THEME.container.secondary} ${
        isClickable ? 'cursor-pointer' : ''
      } ${className}`}
    >
      <CardHeader className="pb-2">
        <CardTitle className={`text-sm font-medium ${BASE_THEME.text.muted} flex items-center gap-2`}>
          {Icon && <Icon className="h-4 w-4" />}
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${valueColor} flex items-baseline gap-2`}>
          {value}
          {trend && (
            <span className={`text-sm font-normal ${BASE_THEME.text.muted}`}>
              {trendIcons[trend]}
            </span>
          )}
        </div>
        {subtitle && (
          <p className={`text-xs ${BASE_THEME.text.muted} mt-1`}>
            {subtitle}
          </p>
        )}
      </CardContent>
    </Card>
  );
}