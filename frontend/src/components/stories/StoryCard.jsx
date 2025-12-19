/**
 * StoryCard Component
 * 
 * Rainbow-themed story cards for Dashboard.
 * Each story gets its signature color from STORY_THEMES.
 */

import { useNavigate } from 'react-router-dom';
import { STORY_THEMES } from '../../config/theme';

/**
 * @param {object} props
 * @param {object} props.story - Story metadata from storyDefinitions
 * @param {number} props.healthScore - Health score (0-100)
 * @param {string} props.status - Status: 'ok', 'warning', 'error'
 * @param {number} props.issueCount - Number of issues
 * @param {string} props.primaryMetric - Primary metric to display
 */
export default function StoryCard({ 
  story,
  healthScore = 0,
  status = 'ok',
  issueCount = 0,
  primaryMetric = '—',
}) {
  const navigate = useNavigate();
  const theme = STORY_THEMES[story.id];

  if (!theme) {
    console.warn(`No theme found for story: ${story.id}`);
    return null;
  }

  const handleClick = () => {
    navigate(story.route);
  };

  return (
    <div 
      onClick={handleClick}
      className={`
        rounded-lg border-2 ${theme.border}
        bg-gradient-to-br ${theme.gradient}
        p-6 cursor-pointer transition-all
        hover:scale-[1.02] hover:shadow-xl hover:${theme.borderHover}
      `}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{theme.emoji}</span>
          <h3 className={`text-lg font-bold ${theme.textLight}`}>
            {story.title}
          </h3>
        </div>
        <span className={`px-2 py-1 rounded-full text-xs border ${theme.badgeBg} ${theme.textLight} ${theme.badgeBorder}`}>
          {issueCount} {issueCount === 1 ? 'issue' : 'issues'}
        </span>
      </div>

      {/* Description */}
      <p className="text-sm text-gray-300 mb-4">
        {story.description}
      </p>

      {/* Metrics */}
      <div className="space-y-2 mb-4">
        <div className="flex justify-between">
          <span className="text-sm text-gray-400">Health:</span>
          <span className={`text-sm font-bold ${theme.text}`}>
            {Math.round(healthScore)}%
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-sm text-gray-400">Primary:</span>
          <span className={`text-sm font-bold ${theme.text}`}>
            {primaryMetric}
          </span>
        </div>
      </div>

      {/* Action Button */}
      <button 
        className={`w-full ${theme.bg} ${theme.bgHover} text-white rounded-lg py-2 font-semibold transition`}
      >
        View Details →
      </button>
    </div>
  );
}