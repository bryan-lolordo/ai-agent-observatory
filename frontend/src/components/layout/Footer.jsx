/**
 * Footer Component
 * 
 * Bottom bar with:
 * - Copyright
 * - Quick links (Docs, GitHub, API)
 * - Version number
 * - Settings icon
 * 
 * Location: components/layout/Footer.jsx
 */

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="mt-auto border-t border-gray-800 bg-gray-900">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between text-sm text-gray-400">
          
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
              className="hover:text-gray-200 transition"
            >
              Docs
            </a>
            <span className="text-gray-700">│</span>
            <a 
              href="https://github.com/yourusername/observatory" 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:text-gray-200 transition"
            >
              GitHub
            </a>
            <span className="text-gray-700">│</span>
            <a 
              href="/api/docs" 
              className="hover:text-gray-200 transition"
            >
              API
            </a>
            <span className="text-gray-700">│</span>
            <span className="text-gray-500">v1.0.0</span>
          </div>

          {/* Settings - Right */}
          <button 
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg
                       bg-gray-800 hover:bg-gray-700 border border-gray-700
                       hover:border-gray-600 transition"
            onClick={() => {
              // TODO: Open settings modal
              alert('Settings coming soon!');
            }}
          >
            <span>⚙️</span>
            <span className="text-gray-300">Settings</span>
          </button>
        </div>
      </div>
    </footer>
  );
}