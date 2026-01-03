/**
 * BackButton - Reusable back navigation button
 * 
 * Provides consistent styling and behavior for back navigation
 * across all Layer 2 and Layer 3 pages.
 */

export default function BackButton({ 
  onClick, 
  label = "Back to Overview", 
  theme 
}) {
  const textColor = theme?.text || 'text-blue-400';
  
  return (
    <button
      onClick={onClick}
      className={`mb-6 flex items-center gap-2 text-sm ${textColor} hover:underline transition-colors`}
    >
      ← {label}
    </button>
  );
}