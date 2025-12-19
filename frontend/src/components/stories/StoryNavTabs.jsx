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
    <div className="bg-gray-900/50 border-b border-gray-800">
      {/* Centered container matching header */}
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex gap-1 overflow-x-auto py-2 scrollbar-thin scrollbar-thumb-gray-700">

          {/* Dashboard Button */}
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2.5 rounded-lg transition-all whitespace-nowrap
                       flex items-center gap-2 text-sm font-medium
                       bg-gray-800/50 text-gray-400 hover:text-gray-200 hover:bg-gray-800"
          >
            <span className="text-base">🏠</span>
            <span>Dashboard</span>
          </button>

          {/* Separator */}
          <div className="w-px bg-gray-700 mx-1 self-stretch" />

          {/* Story Tabs */}
          {stories.map(storyId => {
            const theme = STORY_THEMES[storyId];
            const isActive = currentStory === storyId;
            
            return (
              <button
                key={storyId}
                onClick={() => navigate(`/stories/${storyId}`)}
                className={`
                  px-3 py-2.5 rounded-lg transition-all whitespace-nowrap
                  flex items-center gap-2 text-sm font-medium
                  ${isActive 
                    ? `bg-gradient-to-br ${theme.gradient} ${theme.text} shadow-lg` 
                    : `bg-gray-800/50 text-gray-400 hover:text-gray-200 hover:bg-gray-800`
                  }
                `}
              >
                <span className="text-base">{theme.emoji}</span>
                <span className="hidden sm:inline">{theme.name}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}