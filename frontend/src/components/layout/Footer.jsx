/**
 * Footer Component
 *
 * Bottom bar with:
 * - Copyright
 * - Quick links (Docs, GitHub, API)
 * - Version number
 * - Settings icon
 *
 * UPDATED: Uses theme system - no hardcoded colors!
 *
 * Location: components/layout/Footer.jsx
 */

import { BASE_THEME } from '../../utils/themeUtils';

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className={`mt-auto border-t ${BASE_THEME.border.default} ${BASE_THEME.container.primary}`}>
      <div className="w-full px-6 py-4" style={{ maxWidth: '90%', margin: '0 auto' }}>
        <div className={`flex items-center justify-between text-sm ${BASE_THEME.text.secondary}`}>

          {/* Copyright - Left */}
          <div>
            © {currentYear} Observatory
          </div>

          {/* Links - Center */}
          <div className="flex items-center gap-6">
            <a
              href="https://docs.observatory.ai"
              target="_blank"
              rel="noopener noreferrer"
              className={`hover:${BASE_THEME.text.primary} transition`}
            >
              Docs
            </a>
            <span className={BASE_THEME.border.default.replace('border', 'text')}>│</span>
            <a
              href="https://github.com/yourusername/observatory"
              target="_blank"
              rel="noopener noreferrer"
              className={`hover:${BASE_THEME.text.primary} transition`}
            >
              GitHub
            </a>
            <span className={BASE_THEME.border.default.replace('border', 'text')}>│</span>
            <a
              href="/api/docs"
              className={`hover:${BASE_THEME.text.primary} transition`}
            >
              API
            </a>
            <span className={BASE_THEME.border.default.replace('border', 'text')}>│</span>
            <span className={BASE_THEME.text.muted}>v1.0.0</span>
          </div>

          {/* Settings - Right */}
          <button
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg
                       ${BASE_THEME.container.secondary} hover:bg-gray-700 border ${BASE_THEME.border.default}
                       hover:${BASE_THEME.border.light} transition`}
            onClick={() => {
              // TODO: Open settings modal
              alert('Settings coming soon!');
            }}
          >
            <span>⚙️</span>
            <span className={BASE_THEME.text.secondary}>Settings</span>
          </button>
        </div>
      </div>
    </footer>
  );
}
