/**
 * Dashboard - Main Observatory Overview
 * 
 * Displays all 8 stories as opportunity-focused cards.
 * Each card shows: health, description, hero metric, and opportunity.
 * 
 * Location: src/pages/Dashboard.jsx
 */

import { useStories } from '../hooks/useStories';
import { getAllStories } from '../constants/storyDefinitions';
import StoryCard from '../components/stories/StoryCard';
import { DashboardSkeleton } from '../components/common/Loading';
import { BASE_THEME } from '../utils/themeUtils';
import PageContainer from '../components/layout/PageContainer';

export default function Dashboard() {
  // Fetch all stories data
  const { data, loading, error, timeRange } = useStories();
  
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

        {/* Page Header */}
        <div className="mb-8">
          <h1 className={`text-3xl font-bold ${BASE_THEME.text.primary} mb-2`}>
            🔭 AI Agent Observatory
          </h1>
          <p className={BASE_THEME.text.muted}>
            Monitor and optimize your LLM application performance
          </p>
        </div>

        {/* Story Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {stories.map((story) => {
            const apiData = storyData[story.id] || {};

            return (
              <StoryCard
                key={story.id}
                story={story}
                data={apiData}
              />
            );
          })}
        </div>

        {/* Footer Info */}
        <div className={`mt-8 text-center text-sm ${BASE_THEME.text.muted}`}>
          Showing data from the last {timeRange} days • {data?.total_calls || 0} total calls analyzed
        </div>

      </PageContainer>
    </div>
  );
}