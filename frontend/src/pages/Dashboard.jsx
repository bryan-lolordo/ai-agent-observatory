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
      <div className="min-h-screen bg-gray-950 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-900/20 border border-red-500 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-400 mb-2">
              Failed to Load Dashboard
            </h2>
            <p className="text-gray-300 mb-4">{error}</p>
            <button 
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Extract data from API response
  const storyData = data?.stories || {};

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-100 mb-2">
            🔭 AI Agent Observatory
          </h1>
          <p className="text-gray-400">
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
        <div className="mt-8 text-center text-sm text-gray-500">
          Showing data from the last {timeRange} days • {data?.total_calls || 0} total calls analyzed
        </div>

      </div>
    </div>
  );
}