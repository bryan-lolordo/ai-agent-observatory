/**
 * Dashboard - Main Observatory Overview
 * 
 * Displays all 8 stories as rainbow-themed cards with health scores.
 * Each card navigates to its respective story page.
 */

import { useNavigate } from 'react-router-dom';
import { useStories } from '../hooks/useStories';
import { getAllStories } from '../constants/storyDefinitions';
import StoryCard from '../components/stories/StoryCard';
import { DashboardSkeleton } from '../components/common/Loading';

export default function Dashboard() {
  const navigate = useNavigate();
  
  // Fetch all stories data
  const { data, loading, error } = useStories({ days: 7 });
  
  // Get story metadata
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

  // Extract story data from API response
  const storyData = data?.stories || {};

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-100 mb-2">
            🔭 AI Agent Observatory
          </h1>
          <p className="text-lg text-gray-400">
            Monitor and optimize your LLM application performance
          </p>
        </div>

        {/* Global KPIs */}
        {data?.summary && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
              <p className="text-sm text-gray-400 mb-2">Total Calls</p>
              <div className="text-3xl font-bold text-blue-400">
                {data.summary.total_calls?.toLocaleString() || 0}
              </div>
            </div>
            
            <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
              <p className="text-sm text-gray-400 mb-2">Avg Latency</p>
              <div className="text-3xl font-bold text-orange-400">
                {data.summary.avg_latency || '—'}
              </div>
            </div>
            
            <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
              <p className="text-sm text-gray-400 mb-2">Total Cost</p>
              <div className="text-3xl font-bold text-green-400">
                {data.summary.total_cost || '$0.00'}
              </div>
            </div>
            
            <div className="bg-gray-900 border border-gray-700 rounded-lg p-6">
              <p className="text-sm text-gray-400 mb-2">Avg Quality</p>
              <div className="text-3xl font-bold text-purple-400">
                {data.summary.avg_quality || '—'}
              </div>
            </div>
          </div>
        )}

        {/* Rainbow Story Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {stories.map((story) => {
            // Get data for this story from API response
            const storyInfo = storyData[story.id] || {};
            
            return (
              <StoryCard
                key={story.id}
                story={story}
                healthScore={storyInfo.health_score || 0}
                status={storyInfo.status || 'ok'}
                issueCount={storyInfo.issue_count || 0}
                primaryMetric={storyInfo.primary_metric || '—'}
              />
            );
          })}
        </div>

      </div>
    </div>
  );
}