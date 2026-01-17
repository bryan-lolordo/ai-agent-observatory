/**
 * Header Component
 *
 * Top navigation bar with:
 * - Logo/Title (links to Dashboard)
 * - Project filter dropdown
 * - Phase selector (All Data / Baseline / Optimized)
 * - Time range selector
 *
 * Location: components/layout/Header.jsx
 */

import { useNavigate } from 'react-router-dom';
import { BASE_THEME } from '../../utils/themeUtils';

export default function Header({
  selectedProject,
  onProjectChange,
  timeRange,
  onTimeRangeChange,
  phase,
  onPhaseChange,
  projects = []
}) {
  const navigate = useNavigate();

  const selectStyles = `
    appearance-none bg-white/5 border border-white/10 rounded-md px-3 py-1.5 text-sm text-gray-300
    hover:bg-white/10 hover:border-white/20 focus:outline-none focus:ring-1 focus:ring-blue-500/50 focus:border-blue-500/50
    transition-all duration-150 cursor-pointer
    bg-[url('data:image/svg+xml;charset=UTF-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2212%22%20height%3D%2212%22%20viewBox%3D%220%200%2012%2012%22%3E%3Cpath%20fill%3D%22%239ca3af%22%20d%3D%22M3%204.5L6%208l3-3.5H3z%22%2F%3E%3C%2Fsvg%3E')]
    bg-no-repeat bg-[right_8px_center] pr-7
  `;

  return (
    <header className="sticky top-0 z-50 bg-[#1a1a1a]/80 backdrop-blur-md border-b border-white/5 shadow-lg shadow-black/20">
      <div className="w-full px-6 py-3" style={{ maxWidth: '90%', margin: '0 auto' }}>
        <div className="flex items-center justify-between">

          {/* Logo/Title - Left */}
          <button
            onClick={() => navigate('/')}
            className="hover:opacity-80 transition-opacity"
          >
            <h1 className="text-base font-semibold text-white tracking-tight">
              AI Agent Observatory
            </h1>
          </button>

          {/* Filters - Right */}
          <div className="flex items-center gap-2">

            {/* Project Selector */}
            <select
              value={selectedProject || ''}
              onChange={(e) => onProjectChange(e.target.value || null)}
              className={selectStyles}
            >
              <option value="">All Projects</option>
              {projects.map(project => (
                <option key={project} value={project}>
                  {project}
                </option>
              ))}
            </select>

            {/* Divider */}
            <div className="w-px h-5 bg-white/10" />

            {/* Phase Selector */}
            <select
              value={phase || ''}
              onChange={(e) => onPhaseChange(e.target.value || null)}
              className={selectStyles}
            >
              <option value="">All Data</option>
              <option value="baseline">Baseline</option>
              <option value="optimized">Optimized</option>
            </select>

            {/* Time Range Selector */}
            <select
              value={timeRange}
              onChange={(e) => onTimeRangeChange(Number(e.target.value))}
              className={selectStyles}
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