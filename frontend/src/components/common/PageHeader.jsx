/**
 * PageHeader - Consistent page header for all story pages
 * 
 * Provides standardized header with title, emoji, breadcrumb,
 * and optional health score or custom right content.
 * 
 * Uses BASE_THEME for neutral colors - no hardcoded grays!
 */

import { BASE_THEME } from '../../utils/themeUtils';

export default function PageHeader({ 
  title, 
  emoji, 
  theme, 
  breadcrumb, 
  healthScore, // optional health percentage
  rightContent // optional custom JSX for right side
}) {
  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-2">
        <h1 className={`text-3xl font-bold ${theme?.text || BASE_THEME.text.primary} flex items-center gap-3`}>
          {emoji && <span className="text-4xl">{emoji}</span>}
          {title}
        </h1>
        
        {/* Health Score Badge */}
        {healthScore !== undefined && (
          <div className={`px-4 py-2 rounded-full border ${BASE_THEME.border.default} ${BASE_THEME.container.primary}`}>
            <span className={`text-sm font-semibold ${theme?.text || BASE_THEME.text.primary}`}>
              {Math.round(healthScore)}% Health
            </span>
          </div>
        )}
        
        {/* Custom Right Content */}
        {rightContent}
      </div>
      
      {/* Breadcrumb */}
      {breadcrumb && (
        <p className={`${BASE_THEME.text.muted} text-sm`}>{breadcrumb}</p>
      )}
    </div>
  );
}