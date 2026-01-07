/**
 * OptimizationHierarchy - Expandable Rows Table
 *
 * Hierarchical view: Agent -> Operation -> Story -> Fixes -> Calls
 *
 * Features:
 * - Expandable rows at each level
 * - Inline metrics in columns (Before, After, Delta%)
 * - Status badges and progress indicators
 * - Click to expand for fixes and sample calls
 */

import { useState } from 'react';
import { ChevronRight, ChevronDown, Check, Plus } from 'lucide-react';
import { STORY_THEMES } from '../../config/theme';
import { BASE_THEME } from '../../utils/themeUtils';

// Story color mapping
const STORY_COLORS = {
  latency: STORY_THEMES.latency,
  cache: STORY_THEMES.cache,
  cost: STORY_THEMES.cost,
  quality: STORY_THEMES.quality,
  routing: STORY_THEMES.routing,
  token: STORY_THEMES.token_imbalance,
  prompt: STORY_THEMES.system_prompt,
};

// Status badge component
const StatusBadge = ({ status }) => {
  const configs = {
    pending: { bg: '${BASE_THEME.container.tertiary}', text: BASE_THEME.text.secondary, label: 'Pending' },
    in_progress: { bg: 'bg-blue-600', text: 'text-white', label: 'In Progress' },
    complete: { bg: 'bg-green-600', text: 'text-white', label: 'Complete' },
    skipped: { bg: '${BASE_THEME.container.tertiary}', text: BASE_THEME.text.secondary, label: 'Skipped' },
  };
  const config = configs[status] || configs.pending;

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${config.bg} ${config.text}`}>
      {config.label}
    </span>
  );
};

// Progress indicator for agent/operation level
const ProgressIndicator = ({ complete, total }) => {
  const pct = total > 0 ? (complete / total) * 100 : 0;
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 ${BASE_THEME.container.tertiary} rounded-full overflow-hidden">
        <div
          className="h-full bg-green-500 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-xs ${BASE_THEME.text.muted}`}>{complete}/{total}</span>
    </div>
  );
};

// Agent Row (top level)
const AgentRow = ({ agent, expanded, onToggle, onStoryClick }) => {
  return (
    <>
      <tr
        onClick={onToggle}
        className={`cursor-pointer hover:${BASE_THEME.container.secondary}/50 transition-colors`}
      >
        <td className="py-3 px-4">
          <div className="flex items-center gap-2">
            {expanded ? (
              <ChevronDown className={`w-4 h-4 ${BASE_THEME.text.muted}`} />
            ) : (
              <ChevronRight className={`w-4 h-4 ${BASE_THEME.text.muted}`} />
            )}
            <span className={`font-medium ${BASE_THEME.text.primary}`}>{agent.agent_name}</span>
            <span className={`text-xs ${BASE_THEME.text.muted}`}>Agent</span>
          </div>
        </td>
        <td className={`py-3 px-4 text-right ${BASE_THEME.text.secondary}`}>{agent.call_count}</td>
        <td className="py-3 px-4"></td>
        <td className="py-3 px-4"></td>
        <td className="py-3 px-4"></td>
        <td className="py-3 px-4"></td>
        <td className="py-3 px-4">
          <ProgressIndicator complete={agent.complete_count} total={agent.total_stories} />
        </td>
      </tr>

      {expanded && agent.operations.map((operation) => (
        <OperationRows
          key={operation.operation}
          operation={operation}
          agentName={agent.agent_name}
          onStoryClick={onStoryClick}
        />
      ))}
    </>
  );
};

// Operation Rows (second level)
const OperationRows = ({ operation, agentName, onStoryClick }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        onClick={() => setExpanded(!expanded)}
        className={`cursor-pointer hover:${BASE_THEME.container.tertiary}/30 transition-colors ${BASE_THEME.container.primary}/30`}
      >
        <td className="py-2.5 px-4 pl-10">
          <div className="flex items-center gap-2">
            {expanded ? (
              <ChevronDown className={`w-4 h-4 ${BASE_THEME.text.muted}`} />
            ) : (
              <ChevronRight className={`w-4 h-4 ${BASE_THEME.text.muted}`} />
            )}
            <span className="font-mono text-purple-400">{operation.operation}</span>
          </div>
        </td>
        <td className={`py-2.5 px-4 text-right ${BASE_THEME.text.muted}`}>{operation.call_count}</td>
        <td className="py-2.5 px-4"></td>
        <td className="py-2.5 px-4"></td>
        <td className="py-2.5 px-4"></td>
        <td className="py-2.5 px-4"></td>
        <td className="py-2.5 px-4">
          <ProgressIndicator complete={operation.complete_count} total={operation.total_stories} />
        </td>
      </tr>

      {expanded && operation.stories.map((story) => (
        <StoryRows
          key={story.id}
          story={story}
          onStoryClick={onStoryClick}
        />
      ))}
    </>
  );
};

// Story Rows (third level - main tracking unit)
const StoryRows = ({ story, onStoryClick }) => {
  const [expanded, setExpanded] = useState(false);
  const storyTheme = STORY_COLORS[story.story_id] || STORY_THEMES.optimization;

  const hasImprovement = story.current_value !== null && story.improvement_pct !== null;

  return (
    <>
      <tr
        onClick={() => setExpanded(!expanded)}
        className={`cursor-pointer transition-colors ${BASE_THEME.container.primary}/50 ${storyTheme.rowHover}`}
      >
        {/* Story Name */}
        <td className="py-2.5 px-4 pl-16">
          <div className="flex items-center gap-2">
            {expanded ? (
              <ChevronDown className={`w-4 h-4 ${BASE_THEME.text.muted}`} />
            ) : (
              <ChevronRight className={`w-4 h-4 ${BASE_THEME.text.muted}`} />
            )}
            <span className="text-lg">{story.story_icon}</span>
            <span className={storyTheme.text}>
              {story.story_id.charAt(0).toUpperCase() + story.story_id.slice(1)}
            </span>
          </div>
        </td>

        {/* Calls */}
        <td className={`py-2.5 px-4 text-right ${BASE_THEME.text.muted}`}>
          {story.call_count}
        </td>

        {/* Before (Baseline) */}
        <td className="py-2.5 px-4 text-right">
          <span className={BASE_THEME.text.secondary}>{story.baseline_value_formatted}</span>
        </td>

        {/* After (Current) */}
        <td className="py-2.5 px-4 text-right">
          {hasImprovement ? (
            <span className={storyTheme.text}>{story.current_value_formatted}</span>
          ) : (
            <span className={BASE_THEME.text.muted}>—</span>
          )}
        </td>

        {/* Delta % */}
        <td className="py-2.5 px-4 text-right">
          {hasImprovement ? (
            <span className="text-green-400 font-medium">{story.improvement_formatted}</span>
          ) : (
            <span className={BASE_THEME.text.muted}>—</span>
          )}
        </td>

        {/* Fixes */}
        <td className="py-2.5 px-4 text-center">
          {story.fix_count > 0 ? (
            <span className="text-green-400">{story.fix_count}</span>
          ) : (
            <span className={BASE_THEME.text.muted}>0</span>
          )}
        </td>

        {/* Status */}
        <td className="py-2.5 px-4">
          <StatusBadge status={story.status} />
        </td>
      </tr>

      {/* Expanded content: Applied Fixes + Sample Calls + Actions */}
      {expanded && (
        <tr className={`${BASE_THEME.container.primary}`}>
          <td colSpan={7} className="p-0">
            <div className="pl-20 pr-4 py-3 space-y-3">
              {/* Applied Fixes */}
              {story.fixes && story.fixes.length > 0 && (
                <div className="space-y-2">
                  <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide`}>Applied Fixes</div>
                  {story.fixes.map((fix) => (
                    <div
                      key={fix.id}
                      className={`flex items-center gap-4 p-2 rounded ${BASE_THEME.container.primary}/30 border ${BASE_THEME.border.default}`}
                    >
                      <Check className="w-4 h-4 text-green-500" />
                      <span className={`font-medium ${storyTheme.text}`}>{fix.fix_type}</span>
                      <span className={BASE_THEME.text.muted}>
                        {fix.before_value?.toFixed(2)} → {fix.after_value?.toFixed(2)}
                      </span>
                      {fix.improvement_pct && (
                        <span className="text-green-400">
                          {fix.improvement_pct > 0 ? '-' : '+'}{Math.abs(fix.improvement_pct).toFixed(0)}%
                        </span>
                      )}
                      {fix.applied_date && (
                        <span className={`${BASE_THEME.text.muted} text-xs`}>
                          {new Date(fix.applied_date).toLocaleDateString()}
                        </span>
                      )}
                      {fix.git_commit && (
                        <span className={`font-mono text-xs ${BASE_THEME.text.muted}`}>
                          {fix.git_commit.slice(0, 7)}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Sample Calls */}
              {story.calls && story.calls.length > 0 && (
                <div className="space-y-2">
                  <div className={`text-xs ${BASE_THEME.text.muted} uppercase tracking-wide`}>Sample Calls</div>
                  <div className="flex flex-wrap gap-2">
                    {story.calls.slice(0, 5).map((call) => (
                      <div
                        key={call.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          onStoryClick && onStoryClick(story, call);
                        }}
                        className={`px-2 py-1 rounded ${BASE_THEME.container.tertiary} border ${BASE_THEME.border.default} text-xs cursor-pointer hover:${BASE_THEME.container.tertiary} transition-colors`}
                      >
                        <span className={`font-mono ${BASE_THEME.text.secondary}`}>{call.id?.slice(0, 8)}...</span>
                        <span className={`${BASE_THEME.text.muted} ml-2`}>{call.metric_formatted}</span>
                      </div>
                    ))}
                    {story.calls.length > 5 && (
                      <div className={`px-2 py-1 text-xs ${BASE_THEME.text.muted}`}>
                        +{story.calls.length - 5} more
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Action buttons */}
              <div className="flex gap-2 pt-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onStoryClick && onStoryClick(story);
                  }}
                  className={`px-3 py-1.5 rounded text-xs font-medium ${storyTheme.bg} text-white hover:opacity-80 transition-opacity`}
                >
                  <Plus className="w-3 h-3 inline mr-1" />
                  Add Fix
                </button>
                {story.status === 'pending' && (
                  <button
                    onClick={(e) => e.stopPropagation()}
                    className={`px-3 py-1.5 rounded text-xs font-medium ${BASE_THEME.container.tertiary} ${BASE_THEME.text.secondary} hover:${BASE_THEME.container.secondary} transition-colors`}
                  >
                    Mark In Progress
                  </button>
                )}
                {story.status !== 'complete' && story.status !== 'skipped' && (
                  <button
                    onClick={(e) => e.stopPropagation()}
                    className={`px-3 py-1.5 rounded text-xs font-medium ${BASE_THEME.container.tertiary} ${BASE_THEME.text.secondary} hover:${BASE_THEME.container.tertiary} transition-colors`}
                  >
                    Skip
                  </button>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
};

// Main component
export default function OptimizationHierarchy({ hierarchy, onStoryClick }) {
  // Initialize all agents as expanded by default
  const [expandedAgents, setExpandedAgents] = useState(() => {
    if (!hierarchy?.agents) return {};
    return hierarchy.agents.reduce((acc, agent) => {
      acc[agent.agent_name] = true; // Start expanded
      return acc;
    }, {});
  });

  const toggleAgent = (agentName) => {
    setExpandedAgents(prev => ({
      ...prev,
      [agentName]: !prev[agentName]
    }));
  };

  if (!hierarchy || !hierarchy.agents || hierarchy.agents.length === 0) {
    return (
      <div className={`p-8 text-center ${BASE_THEME.text.muted}`}>
        No optimization opportunities detected. Your system looks well-optimized!
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className={BASE_THEME.container.secondary}>
          <tr>
            <th className={`text-left py-3 px-4 ${BASE_THEME.text.secondary} font-medium`}>
              Agent / Operation / Story
            </th>
            <th className={`text-right py-3 px-4 ${BASE_THEME.text.secondary} font-medium w-20`}>Calls</th>
            <th className={`text-right py-3 px-4 ${BASE_THEME.text.secondary} font-medium w-24`}>Before</th>
            <th className={`text-right py-3 px-4 ${BASE_THEME.text.secondary} font-medium w-24`}>After</th>
            <th className={`text-right py-3 px-4 ${BASE_THEME.text.secondary} font-medium w-20`}>Δ%</th>
            <th className={`text-center py-3 px-4 ${BASE_THEME.text.secondary} font-medium w-16`}>Fixes</th>
            <th className={`text-left py-3 px-4 ${BASE_THEME.text.secondary} font-medium w-28`}>Status</th>
          </tr>
        </thead>
        <tbody>
          {hierarchy.agents.map((agent) => (
            <AgentRow
              key={agent.agent_name}
              agent={agent}
              expanded={expandedAgents[agent.agent_name]}
              onToggle={() => toggleAgent(agent.agent_name)}
              onStoryClick={onStoryClick}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
