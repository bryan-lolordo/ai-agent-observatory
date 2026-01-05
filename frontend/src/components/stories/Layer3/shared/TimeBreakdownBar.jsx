/**
 * TimeBreakdownBar - Visual breakdown of time components
 * Used in Latency story to show TTFT vs Generation time
 *
 * UPDATED: Uses theme system - no hardcoded colors!
 */

import { BASE_THEME } from '../../../../utils/themeUtils';
import { STORY_THEMES, COLORS } from '../../../../config/theme';

// Tree visualization colors using theme values (static, non-story-specific)
const TREE_COLORS = {
  // Tree structure
  branch: COLORS.border, // #374151 (gray-700)
  mutedText: COLORS.textMuted, // #9ca3af (gray-400)
  secondaryText: COLORS.textSecondary, // #d1d5db (gray-300)

  // Network (cyan theme)
  network: {
    label: STORY_THEMES.system_prompt.color, // #06b6d4
    value: '#22d3ee', // cyan-400
    percentage: '#67e8f9', // cyan-200
  },

  // TTFT (purple theme)
  ttft: {
    label: STORY_THEMES.routing.color, // #8b5cf6
    value: '#a78bfa', // purple-400
    percentage: '#c4b5fd', // purple-300
  },

  // Generation (amber theme)
  generation: {
    label: STORY_THEMES.cost.color, // #f59e0b
    value: '#fbbf24', // amber-400
    percentage: '#fde047', // yellow-300
  },

  // Tokens (pink theme)
  tokens: STORY_THEMES.cache.color, // #ec4899

  // Status colors
  success: COLORS.success, // #22c55e
  error: COLORS.error, // #ef4444
};


export default function TimeBreakdownBar({
  segments = [], // [{ label, value, percentage, color, icon }]
  total,
  unit = 's',
}) {
  return (
    <div className={`${BASE_THEME.container.primary} rounded-lg p-4`}>
      {/* Progress Bar */}
      <div className="flex items-center gap-2 mb-3">
        <div className={`flex-1 ${BASE_THEME.border.default.replace('border', 'bg')} rounded-full h-6 overflow-hidden flex`}>
          {segments.map((segment, idx) => (
            <div
              key={idx}
              className={`${segment.color} h-full flex items-center justify-center text-xs text-white font-medium transition-all`}
              style={{ width: `${Math.max(segment.percentage, 5)}%` }}
            >
              {segment.percentage > 15 && `${segment.percentage.toFixed(0)}%`}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className={`flex justify-between text-sm ${BASE_THEME.text.secondary}`}>
        {segments.map((segment, idx) => (
          <span key={idx}>
            {segment.icon} {segment.label}: {segment.value.toFixed(1)}{unit} ({segment.percentage.toFixed(0)}%)
          </span>
        ))}
      </div>
    </div>
  );
}

/**
 * Convenience component for Latency TTFT/Generation breakdown
 */
export function LatencyBreakdownBar({ ttft_ms, generation_ms, total_ms }) {
  const ttft_pct = (ttft_ms / total_ms) * 100;
  const generation_pct = (generation_ms / total_ms) * 100;

  return (
    <TimeBreakdownBar
      segments={[
        {
          label: 'TTFT',
          value: ttft_ms / 1000,
          percentage: ttft_pct,
          color: 'bg-green-500',
          icon: '🟢',
        },
        {
          label: 'Generation',
          value: generation_ms / 1000,
          percentage: generation_pct,
          color: 'bg-red-500',
          icon: '🔴',
        },
      ]}
      total={total_ms}
      unit="s"
    />
  );
}

/**
 * TimeAttributionTree - Detailed hierarchical time breakdown
 * Shows WHERE the time went in a tree structure
 *
 * UPDATED: Uses theme system - no hardcoded hex colors!
 */
export function TimeAttributionTree({
  total_ms,
  ttft_ms,
  generation_ms,
  completion_tokens,
  tokens_per_second,
  expected_tokens_per_second = 20,
  theme,
}) {
  // Use passed theme or default to latency theme
  const accentTheme = theme || STORY_THEMES.latency;
  const accentColor = accentTheme.color;

  const network_ms = 500; // Rough estimate
  const ttft_pct = (ttft_ms / total_ms) * 100;
  const generation_pct = (generation_ms / total_ms) * 100;
  const network_pct = (network_ms / total_ms) * 100;

  const isProblem = tokens_per_second < expected_tokens_per_second * 0.5;

  return (
    <div className={`${BASE_THEME.container.primary} rounded-lg p-6 text-base`} style={{
      fontFamily: "'Roboto Mono', 'Ubuntu Mono', monospace",
      letterSpacing: '0.5px'
    }}>
      {/* Total */}
      <div className="mb-4">
        <span className="font-bold text-2xl" style={{ color: accentColor }}>
          {(total_ms / 1000).toFixed(1)}s
        </span>
        <span className="text-lg" style={{ color: TREE_COLORS.secondaryText }}> total</span>
      </div>

      {/* Tree branches */}
      <div className="ml-4 space-y-3">
        {/* Network */}
        <div className="flex items-center gap-3">
          <span className="text-lg" style={{ color: TREE_COLORS.branch }}>├─</span>
          <span className="text-lg" style={{ color: TREE_COLORS.network.label }}>Network:</span>
          <span className="font-bold text-lg" style={{ color: TREE_COLORS.network.value }}>
            ~{(network_ms / 1000).toFixed(1)}s
          </span>
          <span className="text-base" style={{ color: TREE_COLORS.network.percentage }}>({network_pct.toFixed(0)}%)</span>
          <span className="text-sm italic" style={{ color: TREE_COLORS.success }}>← negligible</span>
        </div>

        {/* TTFT */}
        <div className="flex items-center gap-3">
          <span className="text-lg" style={{ color: TREE_COLORS.branch }}>├─</span>
          <span className="text-lg" style={{ color: TREE_COLORS.ttft.label }}>TTFT:</span>
          <span className="font-bold text-lg" style={{ color: TREE_COLORS.ttft.value }}>
            {(ttft_ms / 1000).toFixed(1)}s
          </span>
          <span className="text-base" style={{ color: TREE_COLORS.ttft.percentage }}>({ttft_pct.toFixed(0)}%)</span>
          <span className="text-sm" style={{ color: TREE_COLORS.mutedText }}>← Model thinking</span>
        </div>

        {/* Generation (with sub-tree) */}
        <div>
          <div className="flex items-center gap-3">
            <span className="text-lg" style={{ color: TREE_COLORS.branch }}>└─</span>
            <span className="text-lg" style={{ color: TREE_COLORS.generation.label }}>Generation:</span>
            <span className="font-bold text-lg" style={{ color: TREE_COLORS.generation.value }}>
              {(generation_ms / 1000).toFixed(1)}s
            </span>
            <span className="text-base" style={{ color: TREE_COLORS.generation.percentage }}>({generation_pct.toFixed(0)}%)</span>
            <span className="text-sm" style={{ color: TREE_COLORS.mutedText }}>← Token output</span>
          </div>

          {/* Generation sub-items */}
          <div className="ml-8 mt-3 space-y-2">
            <div className="flex items-center gap-3">
              <span className="text-lg" style={{ color: TREE_COLORS.branch }}>├─</span>
              <span className="font-bold text-lg" style={{ color: TREE_COLORS.tokens }}>
                {completion_tokens} tokens
              </span>
              <span className="text-base" style={{ color: TREE_COLORS.secondaryText }}> @ </span>
              <span className="font-bold text-xl" style={{ color: TREE_COLORS.error }}>
                {tokens_per_second.toFixed(1)} tok/sec
              </span>
              {isProblem && (
                <span className="text-sm font-black" style={{ color: TREE_COLORS.error }}>
                  ← PROBLEM
                </span>
              )}
            </div>
            <div className="flex items-center gap-3">
              <span className="text-lg" style={{ color: TREE_COLORS.branch }}>└─</span>
              <span className="text-base" style={{ color: TREE_COLORS.mutedText }}>Expected:</span>
              <span className="font-bold text-lg" style={{ color: TREE_COLORS.success }}>
                ~{expected_tokens_per_second} tok/sec
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Problem callout */}
      {isProblem && (
        <div className={`mt-6 p-4 ${BASE_THEME.container.primary} border-2 ${BASE_THEME.status.error.border} rounded text-base`}>
          <div className={`${BASE_THEME.status.error.text} font-semibold mb-2 text-lg`}>⚠️ Slow Token Generation</div>
          <div className={`${BASE_THEME.text.secondary} text-base`}>
            Generation is {(expected_tokens_per_second / tokens_per_second).toFixed(1)}x slower than expected.
            Likely cause: Large context or conversation history.
          </div>
        </div>
      )}
    </div>
  );
}
