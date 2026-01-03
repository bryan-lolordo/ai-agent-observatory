/**
 * Layer3Shell - Universal Layer 3 detail view shell
 * 
 * Orchestrates:
 * - Breadcrumb navigation + Queue button
 * - Header with KPIs
 * - Tab navigation (DIAGNOSE, ATTRIBUTE, SIMILAR, RAW, FIX)
 * - Panel rendering based on active tab
 * 
 * Each story provides config that defines:
 * - KPIs to display
 * - How to analyze data and detect factors
 * - What fixes are available
 * - Custom panel content
 * 
 * UPDATED: Passes storyId and data to TracePanel for cache support
 */

import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { KPICard } from './shared';
import DiagnosePanel from './DiagnosePanel';
import AttributePanel from './AttributePanel';
import SimilarPanel from './SimilarPanel';
import RawPanel from './RawPanel';
import FixPanel from './FixPanel';
import TracePanel from './TracePanel';
import StoryNavTabs from '../StoryNavTabs';
import { BASE_THEME } from '../../../utils/themeUtils';
import { STORY_THEMES } from '../../../config/theme';

// ─────────────────────────────────────────────────────────────────────────────
// BREADCRUMB NAVIGATION
// ─────────────────────────────────────────────────────────────────────────────

function Breadcrumbs({ items, theme }) {
  return (
    <nav className="flex items-center gap-2 text-sm">
      {items.map((item, idx) => (
        <span key={idx} className="flex items-center gap-2">
          {idx > 0 && <span className={BASE_THEME.text.muted}>›</span>}
          {item.href ? (
            <Link
              to={item.href}
              className={`${BASE_THEME.text.secondary} hover:${BASE_THEME.text.primary} transition-colors`}
            >
              {item.icon && <span className="mr-1">{item.icon}</span>}
              {item.label}
            </Link>
          ) : (
            <span className={theme.text}>
              {item.icon && <span className="mr-1">{item.icon}</span>}
              {item.label}
            </span>
          )}
        </span>
      ))}
    </nav>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// TAB BUTTON
// ─────────────────────────────────────────────────────────────────────────────

function TabButton({ active, onClick, children, badge, theme }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
        active
          ? `${BASE_THEME.container.secondary}/50 ${theme.text} ${theme.border}`
          : `${BASE_THEME.text.secondary} border-transparent hover:${BASE_THEME.text.primary} hover:${BASE_THEME.border.light}`
      }`}
    >
      {children}
      {badge != null && (
        <span
          className={`ml-2 px-2 py-0.5 text-white text-xs rounded-full ${theme.bg}`}
        >
          {badge}
        </span>
      )}
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN SHELL COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

// Use latency theme from STORY_THEMES as default fallback (no hardcoded colors!)
const DEFAULT_THEME = STORY_THEMES.latency;

export default function Layer3Shell({
  // Story config
  storyId,
  storyLabel,
  storyIcon,
  theme = DEFAULT_THEME, // Full theme object with Tailwind classes

  visibleTabs = ['diagnose', 'attribute', 'trace', 'similar', 'raw', 'fix'], // Default: all tabs
  
  // Entity info (call or pattern)
  entityId,
  entityType = 'call', // 'call' or 'pattern'
  entityLabel, // e.g., "ResumeMatching.deep_analyze_job"
  entitySubLabel, // e.g., "Dec 19, 2024 at 2:34 PM"
  entityMeta, // e.g., "openai / gpt-4o"
  
  // Full data object (NEW - for TracePanel to access)
  data = null,
  
  // Breadcrumb items (optional - will auto-generate if not provided)
  breadcrumbs = null,
  
  // Back navigation (legacy support)
  backPath,
  backLabel,
  
  // Queue count (for badge)
  queueCount = null,
  
  // KPIs
  kpis = [], // [{ label, value, subtext, status, icon }]
  
  // Current state for Fix panel comparison table
  currentState = null,
  
  // Diagnose panel props
  diagnoseProps = {},
  
  // Attribute panel props
  attributeProps = {},

  // Trace panel props
  traceProps = {},  // { callId, conversationId, chatHistoryBreakdown }
  
  // Similar panel props
  similarProps = {},
  
  // Raw panel props
  rawProps = {},
  
  // Fix panel props
  fixes = [],
  
  // Response text for before/after comparison in Fix panel
  responseText = null,
  
  // AI Analysis: For patterns, pass a call ID to use for AI analysis
  aiCallId = null,
  
  // Loading state
  loading = false,
}) {

  console.log('🟢 Layer3Shell:', {
    storyId,
    hasData: !!data,
    dataKeys: data ? Object.keys(data).slice(0, 10) : [],
    systemPromptTokens: data?.system_prompt_tokens,
    cacheableTokens: data?.cacheable_tokens,
  });

  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('diagnose');
  const [implementedFixes, setImplementedFixes] = useState([]);

  const handleMarkImplemented = (fixId) => {
    setImplementedFixes(prev =>
      prev.includes(fixId)
        ? prev.filter(id => id !== fixId)
        : [...prev, fixId]
    );
  };

  // Auto-generate breadcrumbs if not provided
  const breadcrumbItems = breadcrumbs || [
    { icon: storyIcon, label: storyLabel, href: `/stories/${storyId}` },
    entityLabel && { label: entityLabel.split('.')[1] || entityLabel, href: backPath },
    { label: entityId?.substring(0, 8) + '...' },
  ].filter(Boolean);

  // Tabs configuration
  // Show AI badge on FIX tab if AI Analysis is available (for calls OR patterns with aiCallId)
  const hasAIAnalysis = entityType === 'call' || !!aiCallId;
  const fixBadge = fixes.length > 0 ? fixes.length : (hasAIAnalysis ? '🤖' : null);
  
  // Define ALL possible tabs
  const allTabs = [
    { id: 'diagnose', label: 'DIAGNOSE' },
    { id: 'attribute', label: 'ATTRIBUTE' },
    { id: 'similar', label: 'SIMILAR' },
    { id: 'trace', label: 'TRACE' },
    { id: 'raw', label: 'RAW' },
    { id: 'fix', label: 'FIX', badge: fixBadge },
  ];

  // ⭐ Filter to only show visible tabs
  const tabs = allTabs.filter(tab => visibleTabs.includes(tab.id));

  if (loading) {
    return (
      <div className={`min-h-screen ${BASE_THEME.container.tertiary} ${BASE_THEME.text.primary}`}>
        <StoryNavTabs activeStory={storyId} />
        <div className="p-6">
          <div className="w-full px-6" style={{ maxWidth: '90%', margin: '0 auto' }}>
            <div className="animate-pulse space-y-6">
              <div className={`h-8 ${BASE_THEME.container.secondary} rounded w-1/3`} />
              <div className="grid grid-cols-4 gap-4">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className={`h-24 ${BASE_THEME.container.secondary} rounded-lg`} />
                ))}
              </div>
              <div className={`h-64 ${BASE_THEME.container.secondary} rounded-lg`} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} ${BASE_THEME.text.primary}`}>
      <StoryNavTabs activeStory={storyId} />
      <div className="p-6">
        <div className="w-full px-6" style={{ maxWidth: '90%', margin: '0 auto' }}>
        
        {/* Top Navigation Bar - Breadcrumbs + Queue Button */}
        <div className="flex justify-between items-center mb-6">
          <Breadcrumbs items={breadcrumbItems} theme={theme} />

          <Link
            to="/optimization"
            className={`flex items-center gap-2 px-4 py-2 ${BASE_THEME.container.secondary} hover:bg-gray-700 border ${BASE_THEME.border.default} rounded-lg text-sm transition-colors`}
          >
            <span>🔧</span>
            <span>Queue</span>
            {queueCount != null && (
              <span className={`px-2 py-0.5 text-white text-xs rounded-full ${theme.bg}`}>
                {queueCount}
              </span>
            )}
          </Link>
        </div>

        {/* Header */}
        <div className="mb-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className={`text-3xl font-bold flex items-center gap-3 ${theme.text}`}>
                <span className="text-4xl">{storyIcon}</span>
                {storyLabel}
              </h1>
              {entityLabel && (
                <p className={`${BASE_THEME.text.secondary} font-mono mt-1`}>{entityLabel}</p>
              )}
              {(entitySubLabel || entityMeta) && (
                <p className={`${BASE_THEME.text.muted} text-sm mt-1`}>
                  {entitySubLabel}
                  {entitySubLabel && entityMeta && ' • '}
                  {entityMeta}
                </p>
              )}
            </div>
            <code className={`text-sm ${BASE_THEME.text.muted} ${BASE_THEME.container.primary} px-3 py-2 rounded-lg`}>
              {entityId?.substring(0, 12)}...
            </code>
          </div>
        </div>

        {/* KPIs */}
        {kpis.length > 0 && (
          <div className={`grid gap-3 mb-6 ${kpis.length === 5 ? 'grid-cols-5' : 'grid-cols-4'}`}>
            {kpis.map((kpi, idx) => (
              <KPICard key={idx} {...kpi} theme={theme} />
            ))}
          </div>
        )}

        {/* Accent Bar */}
        <div className={`h-1 rounded-full mb-6 ${theme.bg} ${theme.dividerGlow}`} />

        {/* Tabs */}
        <div className={`flex gap-1 border-b ${BASE_THEME.border.default} mb-6`}>
          {tabs.map(tab => (
            <TabButton
              key={tab.id}
              active={activeTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
              badge={tab.badge}
              theme={theme}
            >
              {tab.label}
            </TabButton>
          ))}
        </div>

        {/* Panel Content */}
        <div className={`${BASE_THEME.container.primary} border ${BASE_THEME.border.default} rounded-lg p-6`}>
          {activeTab === 'diagnose' && (
            <DiagnosePanel
              {...diagnoseProps}
              theme={theme}
              onViewFix={() => setActiveTab('fix')}
            />
          )}
          {activeTab === 'attribute' && (
            <AttributePanel {...attributeProps} theme={theme} />
          )}
          {activeTab === 'trace' && (
            <TracePanel
              {...traceProps}
              storyType={storyId}
              data={data}
              theme={theme}
            />
          )}
          {activeTab === 'similar' && (
            <SimilarPanel
              {...similarProps}
              storyId={storyId}
              theme={theme}
            />
          )}
          {activeTab === 'raw' && (
            <RawPanel {...rawProps} theme={theme} />
          )}
          {activeTab === 'fix' && (
            <FixPanel
              fixes={fixes}
              implementedFixes={implementedFixes}
              currentState={currentState}
              onMarkImplemented={handleMarkImplemented}
              similarCount={similarProps?.items?.length || 0}
              theme={theme}
              // Pass entity info for AI Analysis
              entityId={entityId}
              entityType={entityType}
              // Pass response text for before/after comparison
              responseText={responseText}
              // Pass aiCallId for pattern-based AI Analysis
              aiCallId={aiCallId}
            />
          )}
        </div>
        </div>
      </div>
    </div>
  );
}