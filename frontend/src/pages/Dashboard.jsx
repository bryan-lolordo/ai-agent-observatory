/**
 * Dashboard - Main Observatory Overview
 *
 * Displays all 9 stories as opportunity-focused cards.
 * Each card shows: health, description, hero metric, and opportunity.
 *
 * Location: src/pages/Dashboard.jsx
 */

import { useState, useEffect } from 'react';
import { useStories } from '../hooks/useStories';
import { useTimeRange } from '../context/TimeRangeContext';
import { getAllStories } from '../constants/storyDefinitions';
import StoryCard from '../components/stories/StoryCard';
import { DashboardSkeleton } from '../components/common/Loading';
import { BASE_THEME } from '../utils/themeUtils';
import PageContainer from '../components/layout/PageContainer';

export default function Dashboard() {
  // Fetch all stories data
  const { data, loading, error } = useStories();
  const { timeRange } = useTimeRange();
  const [queueData, setQueueData] = useState(null);

  // Fetch optimization queue data separately
  useEffect(() => {
    async function fetchQueueData() {
      try {
        const params = new URLSearchParams({ days: String(timeRange), limit: '100' });
        const response = await fetch(`/api/optimization/opportunities?${params}`);
        if (response.ok) {
          const result = await response.json();
          const opportunities = result.opportunities || [];
          const quickWins = opportunities.filter(o => o.effort === 'Low').length;
          const totalSavings = opportunities.reduce((sum, o) => sum + (o.impactValue || 0), 0);

          setQueueData({
            hero_metric: opportunities.length,
            hero_label: 'opportunities found',
            issue_count: quickWins,
            issue_label: 'quick wins',
            savings: totalSavings > 0 ? `$${totalSavings.toFixed(2)} potential savings` : null,
          });
        }
      } catch (err) {
        console.error('Failed to fetch queue data:', err);
      }
    }
    fetchQueueData();
  }, [timeRange]);

  // Get story metadata (has description, emoji, color, route)
  const stories = getAllStories();

  // Loading state
  if (loading) {
    return <DashboardSkeleton />;
  }

  // Error state
  if (error) {
    return (
      <div className={`min-h-screen ${BASE_THEME.container.tertiary} p-8`}>
        <PageContainer>
          <div className={`${BASE_THEME.status.error.bg} border ${BASE_THEME.status.error.border} rounded-lg p-6`}>
            <h2 className={`text-xl font-bold ${BASE_THEME.status.error.textBold} mb-2`}>
              Failed to Load Dashboard
            </h2>
            <p className={`${BASE_THEME.text.secondary} mb-4`}>{error}</p>
            <button
              onClick={() => window.location.reload()}
              className={`px-4 py-2 ${BASE_THEME.status.error.bgSolid} hover:bg-red-700 text-white rounded-lg`}
            >
              Retry
            </button>
          </div>
        </PageContainer>
      </div>
    );
  }

  // Extract data from API response
  const storyData = data?.stories || {};

  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} ${BASE_THEME.text.primary} p-6`}>
      <PageContainer>

        {/* Story Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {stories.map((story) => {
            // Use queue-specific data for the queue card
            const apiData = story.id === 'queue'
              ? queueData || {}
              : storyData[story.id] || {};

            return (
              <StoryCard
                key={story.id}
                story={story}
                data={apiData}
              />
            );
          })}
        </div>

      </PageContainer>
    </div>
  );
}