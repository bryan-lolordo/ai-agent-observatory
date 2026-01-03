/**
 * StoryNavTabs - Horizontal navigation for all 8 stories
 * 
 * Displays color-coded tabs matching the header width.
 * Active tab is highlighted with its signature color.
 * 
 * Location: components/stories/StoryNavTabs.jsx
 */

import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { STORY_THEMES } from '../../config/theme';
import { BASE_THEME } from '../../utils/themeUtils';

export default function StoryNavTabs() {
  const navigate = useNavigate();
  const location = useLocation();
  
  const stories = [
    'latency',
    'cache',
    'routing',
    'quality',
    'token_imbalance',
    'system_prompt',
    'cost',
    'optimization',
  ];
  
  // Determine which story is currently active
  const currentStory = stories.find(id => location.pathname.includes(id));
  
  return (
    <div className={`${BASE_THEME.container.secondary}/50 border-b ${BASE_THEME.border.default}`}>
      {/* Centered container matching header */}
      <div className="w-full px-6" style={{ maxWidth: '90%', margin: '0 auto' }}>
        <div className="flex py-2">

          {/* Dashboard Button */}
          <button
            onClick={() => navigate('/')}
            className={`flex-1 py-2.5 rounded-lg transition-all whitespace-nowrap
                       flex items-center justify-center gap-2 text-sm font-medium
                       ${BASE_THEME.container.tertiary}/50 ${BASE_THEME.text.muted} hover:${BASE_THEME.text.primary} hover:${BASE_THEME.container.tertiary}`}
          >
            <span className="text-base">🏠</span>
            <span className="hidden sm:inline">Dashboard</span>
          </button>

          {/* Story Tabs */}
          {stories.map(storyId => {
            const theme = STORY_THEMES[storyId];
            const isActive = currentStory === storyId;

            return (
              <button
                key={storyId}
                onClick={() => navigate(`/stories/${storyId}`)}
                className={`
                  flex-1 py-2.5 rounded-lg transition-all whitespace-nowrap
                  flex items-center justify-center gap-2 text-sm font-medium
                  ${isActive
                    ? `bg-gradient-to-br ${theme.gradient} ${theme.text} shadow-lg`
                    : `${BASE_THEME.container.tertiary}/50 ${BASE_THEME.text.muted} hover:${BASE_THEME.text.primary} hover:${BASE_THEME.container.tertiary}`
                  }
                `}
              >
                <span className="text-base">{theme.emoji}</span>
                <span className="hidden sm:inline">{theme.name}</span>
              </button>
            );
          })}

          {/* Optimization Queue Button */}
          <button
            onClick={() => navigate('/optimization')}
            className={`flex-1 py-2.5 rounded-lg transition-all whitespace-nowrap
                       flex items-center justify-center gap-2 text-sm font-medium
                       ${location.pathname === '/optimization'
                         ? 'bg-orange-600/30 text-orange-400 border border-orange-600'
                         : `${BASE_THEME.container.tertiary}/50 ${BASE_THEME.text.muted} hover:${BASE_THEME.text.primary} hover:${BASE_THEME.container.tertiary}`
                       }`}
          >
            <span className="text-base">🔧</span>
            <span className="hidden sm:inline">Queue</span>
          </button>
        </div>
      </div>
    </div>
  );
}