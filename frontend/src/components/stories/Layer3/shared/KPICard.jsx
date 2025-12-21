/**
 * KPICard - Reusable KPI display card for Layer 3
 */

export default function KPICard({ label, value, subtext, status = 'neutral', icon }) {
  const statusColors = {
    critical: 'text-red-400',
    warning: 'text-yellow-400',
    good: 'text-green-400',
    neutral: 'text-slate-300',
  };

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
      <div className="text-xs text-slate-500 uppercase tracking-wide mb-1 flex items-center gap-2">
        {icon && <span>{icon}</span>}
        {label}
      </div>
      <div className={`text-2xl font-bold ${statusColors[status]}`}>
        {value}
      </div>
      {subtext && (
        <div className="text-xs text-slate-500 mt-1">{subtext}</div>
      )}
    </div>
  );
}