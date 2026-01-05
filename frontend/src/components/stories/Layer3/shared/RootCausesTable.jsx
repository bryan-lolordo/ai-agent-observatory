/**
 * RootCausesTable - Shows root causes ranked by impact
 * Used in Diagnose panel to show WHY something is slow/expensive/poor quality
 *
 * UPDATED: Uses theme system - no hardcoded colors!
 */

import SeverityBadge from './SeverityBadge';
import { BASE_THEME, getSeverityColors } from '../../../../utils/themeUtils';
import { STORY_THEMES } from '../../../../config/theme';

export default function RootCausesTable({ causes = [], onViewFix, theme }) {
  // Use passed theme or default to latency theme
  const accentTheme = theme || STORY_THEMES.latency;

  if (causes.length === 0) return null;

  // Sort by severity and impact
  const sortedCauses = [...causes].sort((a, b) => {
    const severityOrder = { critical: 0, warning: 1, info: 2 };
    return severityOrder[a.severity] - severityOrder[b.severity];
  });

  // Get severity-based text color
  const getSeverityTextColor = (severity) => {
    const colors = getSeverityColors(severity);
    return colors.text;
  };

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden border border-gray-600">
      <table className="w-full text-base">
        <thead className="bg-gray-700 border-b border-gray-600">
          <tr className="text-left text-gray-200">
            <th className="py-4 px-6 font-medium w-[45%]">Cause</th>
            <th className="py-4 px-6 font-medium w-[22%]">Impact</th>
            <th className="py-4 px-6 font-medium w-[15%]">Severity</th>
            <th className="py-4 px-6 font-medium text-right w-[18%]">Action</th>
          </tr>
        </thead>
        <tbody>
          {sortedCauses.map((cause, idx) => (
            <tr
              key={cause.id || idx}
              className="border-b border-gray-700 hover:bg-gray-700/50 transition-colors"
            >
              {/* Cause */}
              <td className="py-5 px-6">
                <div className={`font-semibold ${BASE_THEME.text.primary} text-base mb-2`}>{cause.label}</div>
                {cause.description && (
                  <div className="text-base text-gray-300 leading-relaxed">{cause.description}</div>
                )}
              </td>

              {/* Impact */}
              <td className="py-5 px-6">
                <span className={`font-mono text-base font-semibold ${getSeverityTextColor(cause.severity)}`}>
                  {cause.impact}
                </span>
              </td>

              {/* Severity */}
              <td className="py-5 px-6">
                <SeverityBadge severity={cause.severity} />
              </td>

              {/* Action */}
              <td className="py-5 px-6 text-right">
                {onViewFix && cause.hasFix !== false && (
                  <button
                    onClick={() => onViewFix(cause.id)}
                    className={`text-sm px-4 py-2 bg-transparent border-2 ${accentTheme.border} hover:${accentTheme.bg} ${accentTheme.text} hover:text-white rounded transition-colors font-semibold`}
                  >
                    View Fix →
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
