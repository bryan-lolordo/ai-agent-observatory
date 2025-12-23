/**
 * StoryCard - Dashboard Story Card Component
 * 
 * Option 1: Opportunity-Focused Design
 * Shows: health marker, title, description, hero metric, opportunity
 * 
 * Location: src/components/stories/StoryCard.jsx
 */

import { useNavigate } from 'react-router-dom';

// Color configuration for each story
const COLORS = {
  orange: { 
    bg: 'bg-orange-500/10', 
    border: 'border-orange-500/50', 
    text: 'text-orange-400', 
    button: 'bg-orange-500 hover:bg-orange-600',
    glow: 'shadow-orange-500/20',
  },
  pink: { 
    bg: 'bg-pink-500/10', 
    border: 'border-pink-500/50', 
    text: 'text-pink-400', 
    button: 'bg-pink-500 hover:bg-pink-600',
    glow: 'shadow-pink-500/20',
  },
  purple: { 
    bg: 'bg-purple-500/10', 
    border: 'border-purple-500/50', 
    text: 'text-purple-400', 
    button: 'bg-purple-500 hover:bg-purple-600',
    glow: 'shadow-purple-500/20',
  },
  red: { 
    bg: 'bg-red-500/10', 
    border: 'border-red-500/50', 
    text: 'text-red-400', 
    button: 'bg-red-500 hover:bg-red-600',
    glow: 'shadow-red-500/20',
  },
  yellow: { 
    bg: 'bg-yellow-500/10', 
    border: 'border-yellow-500/50', 
    text: 'text-yellow-400', 
    button: 'bg-yellow-500 hover:bg-yellow-600',
    glow: 'shadow-yellow-500/20',
  },
  cyan: { 
    bg: 'bg-cyan-500/10', 
    border: 'border-cyan-500/50', 
    text: 'text-cyan-400', 
    button: 'bg-cyan-500 hover:bg-cyan-600',
    glow: 'shadow-cyan-500/20',
  },
  amber: { 
    bg: 'bg-amber-500/10', 
    border: 'border-amber-500/50', 
    text: 'text-amber-400', 
    button: 'bg-amber-500 hover:bg-amber-600',
    glow: 'shadow-amber-500/20',
  },
  green: { 
    bg: 'bg-green-500/10', 
    border: 'border-green-500/50', 
    text: 'text-green-400', 
    button: 'bg-green-500 hover:bg-green-600',
    glow: 'shadow-green-500/20',
  },
};

/**
 * Health indicator dot with color based on score
 */
function HealthIndicator({ score }) {
  let colorClass = 'bg-red-500';
  let label = 'Critical';
  
  if (score >= 80) {
    colorClass = 'bg-green-500';
    label = 'Healthy';
  } else if (score >= 50) {
    colorClass = 'bg-yellow-500';
    label = 'Warning';
  }
  
  return (
    <div className="flex items-center gap-2" title={`Health: ${score}%`}>
      <span className="text-xs text-gray-500">{Math.round(score)}%</span>
      <div className={`w-3 h-3 rounded-full ${colorClass} shadow-lg`} />
    </div>
  );
}

/**
 * StoryCard Component
 * 
 * Props:
 * - story: Story metadata from storyDefinitions (id, title, emoji, description, color, route)
 * - data: API response data (health_score, hero_metric, hero_label, issue_count, issue_label, savings)
 */
export default function StoryCard({ story, data = {} }) {
  const navigate = useNavigate();
  const colors = COLORS[story.color] || COLORS.orange;
  
  // Extract data with fallbacks
  const healthScore = data.health_score ?? 0;
  const heroMetric = data.hero_metric ?? '—';
  const heroLabel = data.hero_label ?? '';
  const issueCount = data.issue_count ?? 0;
  const issueLabel = data.issue_label ?? 'issues';
  const savings = data.savings ?? '';
  
  const handleClick = () => {
    navigate(story.route);
  };
  
  return (
    <div 
      className={`
        ${colors.bg} border ${colors.border} rounded-xl p-5 
        flex flex-col h-full min-h-[280px]
        hover:shadow-lg ${colors.glow} transition-all duration-200
        cursor-pointer
      `}
      onClick={handleClick}
    >
      {/* Header: Title + Health Indicator */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{story.emoji}</span>
          <h3 className="font-semibold text-white">{story.title}</h3>
        </div>
        <HealthIndicator score={healthScore} />
      </div>
      
      {/* Description */}
      <p className="text-sm text-gray-400 mb-4 leading-relaxed">
        {story.description}
      </p>
      
      {/* Hero Metric */}
      <div className="flex-1 flex flex-col justify-center">
        <div className={`text-4xl font-bold ${colors.text}`}>
          {heroMetric}
        </div>
        {heroLabel && (
          <div className="text-sm text-gray-500 mt-1">
            {heroLabel}
          </div>
        )}
      </div>
      
      {/* Opportunity Section */}
      <div className="border-t border-gray-700/50 pt-4 mt-4">
        {issueCount > 0 || savings ? (
          <>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-yellow-400">💡</span>
              <span className="text-gray-300">
                {issueCount} {issueLabel}
              </span>
            </div>
            {savings && (
              <div className={`text-sm ${colors.text} mt-1 font-medium`}>
                → {savings}
              </div>
            )}
          </>
        ) : (
          <div className="text-sm text-gray-500 flex items-center gap-2">
            <span className="text-green-400">✓</span>
            No issues detected
          </div>
        )}
      </div>
      
      {/* Action Button */}
      <button 
        className={`
          mt-4 w-full py-2.5 rounded-lg text-white text-sm font-medium 
          ${colors.button} transition-colors
        `}
        onClick={(e) => {
          e.stopPropagation();
          handleClick();
        }}
      >
        View Details →
      </button>
    </div>
  );
}