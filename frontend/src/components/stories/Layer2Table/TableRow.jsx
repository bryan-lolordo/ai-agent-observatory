/**
 * TableRow - Individual data row
 *
 * Applies proper coloring based on column definitions and colorizers.
 * Clickable to navigate to Layer 3.
 * All data is centered.
 */

import { BASE_THEME } from '../../../utils/themeUtils';

export default function TableRow({
  row,
  columns,
  onClick,
  theme,
  storyId,
  primaryMetric,
  columnWidths,
}) {
  return (
    <tr
      onClick={onClick}
      className="border-b border-numerro-border/20 cursor-pointer transition-all"
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
        let colorClass = col.className || BASE_THEME.text.secondary;

        // Apply colorizer if exists
        if (col.colorizer) {
          colorClass = col.colorizer(value);
        }

        // Special handling for operation column - use story color
        if (col.key === 'operation') {
          colorClass = `${theme.textLight} ${col.classNameBase || ''}`;
        }

        // Get column width from state
        const width = columnWidths?.[col.key];

        return (
          <td
            key={col.key}
            className="py-3 px-4 text-center"
            style={{ width: width ? `${width}px` : 'auto', minWidth: '80px' }}
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
