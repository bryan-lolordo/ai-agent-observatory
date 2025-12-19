/**
 * KPICard Component
 * 
 * Displays a key performance indicator with rainbow theme support.
 * Used across all story pages for metric display.
 */

import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';

/**
 * @param {object} props
 * @param {object} props.theme - Story theme from STORY_THEMES (optional)
 * @param {string} props.title - Card title (e.g., "Avg Latency")
 * @param {string|number} props.value - Main value (e.g., "2.11s" or 85.5)
 * @param {string} props.subtitle - Optional subtitle (e.g., "(>5s threshold)")
 * @param {string} props.status - Optional status: 'ok', 'warning', 'error'
 * @param {string} props.icon - Optional icon (Lucide icon name)
 * @param {string} props.trend - Optional trend indicator: 'up', 'down', 'neutral'
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
  className = '',
}) {
  // Trend indicators
  const trendIcons = {
    up: '↑',
    down: '↓',
    neutral: '→',
  };

  // Rainbow themed version
  if (theme) {
    return (
      <div className={`rounded-lg border-2 ${theme.border} bg-gradient-to-br ${theme.gradient} p-6 ${className}`}>
        <p className={`text-sm ${theme.textLight} mb-2 flex items-center gap-2`}>
          {Icon && <Icon className="h-4 w-4" />}
          {title}
        </p>
        <div className={`text-3xl font-bold ${theme.text} flex items-baseline gap-2`}>
          {value}
          {trend && (
            <span className="text-sm font-normal text-gray-400">
              {trendIcons[trend]}
            </span>
          )}
        </div>
        {subtitle && (
          <p className="text-xs text-gray-400 mt-1">
            {subtitle}
          </p>
        )}
      </div>
    );
  }

  // Default non-themed version
  const statusColors = {
    ok: 'text-green-400',
    warning: 'text-yellow-400',
    error: 'text-red-400',
  };

  const valueColor = status ? statusColors[status] : 'text-gray-100';

  return (
    <Card className={`hover:shadow-md transition-shadow border-gray-700 bg-gray-800 ${className}`}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
          {Icon && <Icon className="h-4 w-4" />}
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold ${valueColor} flex items-baseline gap-2`}>
          {value}
          {trend && (
            <span className="text-sm font-normal text-gray-500">
              {trendIcons[trend]}
            </span>
          )}
        </div>
        {subtitle && (
          <p className="text-xs text-gray-400 mt-1">
            {subtitle}
          </p>
        )}
      </CardContent>
    </Card>
  );
}