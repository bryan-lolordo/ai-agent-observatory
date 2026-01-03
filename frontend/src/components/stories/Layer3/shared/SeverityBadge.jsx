/**
 * SeverityBadge - Displays severity level with icon and color
 * 
 * UPDATED: WARNING badge uses outlined style (variation 1.2), larger font
 */

const SEVERITY_STYLES = {
  critical: {
    bg: 'bg-red-900/50',
    text: 'text-red-300',
    border: 'border-red-700',
    icon: '🔴',
  },
  warning: {
    // Variation 1.2: Outlined style
    bg: 'bg-transparent',
    text: 'text-yellow-400',
    border: 'border-yellow-400 border-2',
    icon: '🟡',
  },
  info: {
    bg: 'bg-blue-900/50',
    text: 'text-blue-300',
    border: 'border-blue-700',
    icon: '🔵',
  },
  ok: {
    bg: 'bg-green-900/50',
    text: 'text-green-300',
    border: 'border-green-700',
    icon: '🟢',
  },
};

export default function SeverityBadge({ severity }) {
  const style = SEVERITY_STYLES[severity] || SEVERITY_STYLES.info;

  return (
    <span className={`px-3 py-1 rounded text-sm border ${style.bg} ${style.text} ${style.border} font-semibold`}>
      {style.icon} {severity.toUpperCase()}
    </span>
  );
}