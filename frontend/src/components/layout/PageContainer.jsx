/**
 * PageContainer - Consistent width/padding wrapper for all story pages
 * 
 * Provides standardized container with configurable max-width.
 * Default is 95% for data-rich dashboards to maximize screen real estate.
 */

export default function PageContainer({ 
  children, 
  maxWidth = "95%",
  variant = "default" // "default" | "full" | "narrow"
}) {
  const widths = {
    default: "90%",
    full: "100%",
    narrow: "1280px" // original max-w-7xl
  };

  const finalWidth = widths[variant] || maxWidth;
  
  return (
    <div 
      className="w-full px-6 py-6" 
      style={{ maxWidth: finalWidth, margin: '0 auto' }}
    >
      {children}
    </div>
  );
}