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
import { BASE_THEME } from '../../utils/themeUtils';

export default function Header({ selectedProject, onProjectChange, timeRange, onTimeRangeChange, projects = [] }) {
  const navigate = useNavigate();

  return (
    <header className={`sticky top-0 z-50 ${BASE_THEME.container.secondary} border-b ${BASE_THEME.border.default}`}>
      <div className="w-full px-6 py-4" style={{ maxWidth: '90%', margin: '0 auto' }}>
        <div className="flex items-center justify-between">
          
          {/* Logo/Title - Left */}
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-3 hover:opacity-80 transition"
          >
            <span className="text-3xl">🔭</span>
            <h1 className={`text-xl font-bold ${BASE_THEME.text.primary}`}>
              AI Agent Observatory
            </h1>
          </button>

          {/* Filters - Right */}
          <div className="flex items-center gap-4">

            {/* Project Selector */}
            <select
              value={selectedProject || ''}
              onChange={(e) => onProjectChange(e.target.value || null)}
              className={`${BASE_THEME.container.tertiary} border ${BASE_THEME.border.default} rounded-lg px-4 py-2 text-sm ${BASE_THEME.text.secondary}
                         hover:border-gray-600 focus:outline-none focus:border-blue-500 transition`}
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
              className={`${BASE_THEME.container.tertiary} border ${BASE_THEME.border.default} rounded-lg px-4 py-2 text-sm ${BASE_THEME.text.secondary}
                         hover:border-gray-600 focus:outline-none focus:border-blue-500 transition`}
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