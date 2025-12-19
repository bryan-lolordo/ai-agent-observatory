/**
 * Header Component
 * 
 * Top navigation bar with:
 * - Logo/Title (links to Dashboard)
 * - Project filter dropdown
 * - Time range selector
 * 
 * Location: components/layout/Header.jsx
 */

import { useNavigate } from 'react-router-dom';

export default function Header({ selectedProject, onProjectChange, timeRange, onTimeRangeChange, projects = [] }) {
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-50 bg-gray-900 border-b border-gray-800">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          
          {/* Logo/Title - Left */}
          <button 
            onClick={() => navigate('/')}
            className="flex items-center gap-3 hover:opacity-80 transition"
          >
            <span className="text-3xl">🔭</span>
            <h1 className="text-xl font-bold text-gray-100">
              AI Agent Observatory
            </h1>
          </button>

          {/* Filters - Right */}
          <div className="flex items-center gap-4">
            
            {/* Project Selector */}
            <select
              value={selectedProject || ''}
              onChange={(e) => onProjectChange(e.target.value || null)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm text-gray-300
                         hover:border-gray-600 focus:outline-none focus:border-blue-500 transition"
            >
              <option value="">All Projects</option>
              {projects.map(project => (
                <option key={project} value={project}>
                  {project}
                </option>
              ))}
            </select>

            {/* Time Range Selector */}
            <select
              value={timeRange}
              onChange={(e) => onTimeRangeChange(Number(e.target.value))}
              className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm text-gray-300
                         hover:border-gray-600 focus:outline-none focus:border-blue-500 transition"
            >
              <option value={1}>Last 24 hours</option>
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>

          </div>
        </div>
      </div>
    </header>
  );
}