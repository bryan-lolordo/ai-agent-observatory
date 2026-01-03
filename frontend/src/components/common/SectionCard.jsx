/**
 * SectionCard - Consistent container for tables, charts, and sections
 * 
 * Provides the standard card wrapper with colored top border,
 * optional header, and content area. Used for operations tables,
 * charts, and other major page sections.
 * 
 * Fully integrated with Observatory theme system (theme.js)
 * Uses BASE_THEME for neutral colors - no hardcoded grays!
 */

import { BASE_THEME } from '../../utils/themeUtils';

export default function SectionCard({ 
  title, 
  subtitle, 
  theme, 
  children,
  className = "",
  noPadding = false // For tables that need full-width
}) {
  return (
    <div className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} overflow-hidden ${className}`}>
      {/* Colored top border with glow effect */}
      {theme?.bg && (
        <div className={`h-1 ${theme.bg} ${theme.dividerGlow || ''}`} />
      )}
      
      {/* Optional Header */}
      {title && (
        <div className={`p-4 border-b ${BASE_THEME.border.default}`}>
          <h3 className={`text-xs font-medium ${BASE_THEME.text.secondary} uppercase tracking-wide`}>
            {title}
            {subtitle && (
              <span className={`${BASE_THEME.text.muted} normal-case ml-2 font-normal`}>{subtitle}</span>
            )}
          </h3>
        </div>
      )}
      
      {/* Content */}
      <div className={noPadding ? '' : 'p-6'}>
        {children}
      </div>
    </div>
  );
}