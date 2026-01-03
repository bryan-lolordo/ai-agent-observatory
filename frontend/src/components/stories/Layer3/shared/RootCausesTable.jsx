/**
 * RootCausesTable - Shows root causes ranked by impact
 * Used in Diagnose panel to show WHY something is slow/expensive/poor quality
 * 
 * UPDATED: Improved spacing - more breathing room, better column widths
 */

import SeverityBadge from './SeverityBadge';

export default function RootCausesTable({ causes = [], onViewFix }) {
  if (causes.length === 0) return null;

  // Sort by severity and impact
  const sortedCauses = [...causes].sort((a, b) => {
    const severityOrder = { critical: 0, warning: 1, info: 2 };
    return severityOrder[a.severity] - severityOrder[b.severity];
  });

  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden border border-gray-700">
      <table className="w-full text-base">
        <thead className="bg-gray-800 border-b border-gray-700">
          <tr className="text-left text-gray-400">
            {/* Wider padding in header */}
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
              className={`border-b border-gray-800 hover:bg-gray-800/50 transition-colors ${
                cause.severity === 'critical' ? 'bg-red-900/5' :
                cause.severity === 'warning' ? 'bg-yellow-900/5' :
                ''
              }`}
            >
              {/* Cause - More vertical padding */}
              <td className="py-5 px-6">
                <div className="font-semibold text-gray-200 text-base mb-2">{cause.label}</div>
                {cause.description && (
                  <div className="text-sm text-gray-500 leading-relaxed">{cause.description}</div>
                )}
              </td>

              {/* Impact - More padding */}
              <td className="py-5 px-6">
                <span className={`font-mono text-base font-semibold ${
                  cause.severity === 'critical' ? 'text-red-400' :
                  cause.severity === 'warning' ? 'text-yellow-400' :
                  'text-gray-400'
                }`}>
                  {cause.impact}
                </span>
              </td>

              {/* Severity - More padding */}
              <td className="py-5 px-6">
                <SeverityBadge severity={cause.severity} />
              </td>

              {/* Action - More padding */}
              <td className="py-5 px-6 text-right">
                {onViewFix && cause.hasFix !== false && (
                  <button
                    onClick={() => onViewFix(cause.id)}
                    className="text-sm px-4 py-2 bg-transparent border-2 border-orange-500 hover:bg-orange-500 text-orange-400 hover:text-white rounded transition-colors font-semibold"
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