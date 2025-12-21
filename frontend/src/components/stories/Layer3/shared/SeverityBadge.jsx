/**
 * SeverityBadge - Displays severity level with icon and color
 */

const SEVERITY_STYLES = {
  critical: {
    bg: 'bg-red-900/50',
    text: 'text-red-300',
    border: 'border-red-700',
    icon: '🔴',
  },
  warning: {
    bg: 'bg-yellow-900/50',
    text: 'text-yellow-300',
    border: 'border-yellow-700',
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
    <span className={`px-2 py-0.5 rounded text-xs border ${style.bg} ${style.text} ${style.border}`}>
      {style.icon} {severity.toUpperCase()}
    </span>
  );
}