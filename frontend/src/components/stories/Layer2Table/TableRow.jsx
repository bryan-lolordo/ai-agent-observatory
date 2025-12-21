/**
 * TableRow - Individual data row
 * 
 * Applies proper coloring based on column definitions and colorizers.
 * Clickable to navigate to Layer 3.
 */

export default function TableRow({
  row,
  columns,
  onClick,
  theme,
  storyId,
  primaryMetric,
}) {
  return (
    <tr
      onClick={onClick}
      className="border-b border-gray-800 cursor-pointer transition-all hover:bg-gray-800/50"
      style={{
        // Subtle hover effect with story color
        '--hover-bg': `${theme.color}10`,
      }}
      onMouseEnter={(e) => e.currentTarget.style.backgroundColor = `${theme.color}08`}
      onMouseLeave={(e) => e.currentTarget.style.backgroundColor = ''}
    >
      {columns.map(col => {
        const value = row[col.key];
        
        // Get formatted value
        const formattedValue = col.formatter ? col.formatter(value) : value ?? '—';
        
        // Determine text color class
        let colorClass = col.className || 'text-gray-300';
        
        // Apply colorizer if exists
        if (col.colorizer) {
          colorClass = col.colorizer(value);
        }
        
        // Special handling for operation column - use story color
        if (col.key === 'operation') {
          colorClass = `${theme.textLight} ${col.classNameBase || ''}`;
        }
        
        // Alignment
        const alignClass = col.align === 'right' ? 'text-right' 
                        : col.align === 'center' ? 'text-center' 
                        : 'text-left';
        
        return (
          <td 
            key={col.key} 
            className={`py-3 px-4 ${alignClass} ${col.width || ''}`}
          >
            <span className={colorClass}>
              {formattedValue}
            </span>
          </td>
        );
      })}
      
      {/* Empty cell for add column button */}
      <td className="py-3 px-2 w-12" />
    </tr>
  );
}
