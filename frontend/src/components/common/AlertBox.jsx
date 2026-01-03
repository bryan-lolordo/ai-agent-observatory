/**
 * AlertBox - Reusable alert/message box for different status types
 * 
 * Displays error, warning, success, or info messages with consistent styling.
 * Uses BASE_THEME.status for all color variations.
 * 
 * Examples:
 * - Error states (API failures, validation errors)
 * - Warning messages (caution, deprecation notices)
 * - Success messages (save confirmations, completed actions)
 * - Info messages (helpful tips, general notices)
 */

import { BASE_THEME } from '../../utils/themeUtils';

export default function AlertBox({ 
  type = 'info',        // 'error' | 'warning' | 'success' | 'info'
  title,                // Optional bold title
  message,              // Main message content
  children,             // Or use children for custom content
  icon,                 // Optional custom icon (overrides default)
  onClose,              // Optional close handler
  actions,              // Optional action buttons (JSX)
  className = ""
}) {
  const statusStyles = BASE_THEME.status[type];
  
  // Default icons for each type
  const defaultIcons = {
    error: '❌',
    warning: '⚠️',
    success: '✅',
    info: 'ℹ️',
  };
  
  const displayIcon = icon !== undefined ? icon : defaultIcons[type];
  
  return (
    <div className={`${statusStyles.bg} border ${statusStyles.border} rounded-lg p-6 ${className}`}>
      <div className="flex items-start gap-3">
        {/* Icon */}
        {displayIcon && (
          <span className="text-2xl flex-shrink-0">{displayIcon}</span>
        )}
        
        {/* Content */}
        <div className="flex-1">
          {title && (
            <h3 className={`text-xl font-bold ${statusStyles.textBold} mb-2`}>
              {title}
            </h3>
          )}
          
          {message && (
            <p className={BASE_THEME.text.secondary}>{message}</p>
          )}
          
          {children && (
            <div className={BASE_THEME.text.secondary}>
              {children}
            </div>
          )}
          
          {/* Action Buttons */}
          {actions && (
            <div className="mt-4 flex gap-3">
              {actions}
            </div>
          )}
        </div>
        
        {/* Close Button */}
        {onClose && (
          <button
            onClick={onClose}
            className={`${BASE_THEME.text.muted} hover:${statusStyles.text} transition-colors`}
            aria-label="Close"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
}