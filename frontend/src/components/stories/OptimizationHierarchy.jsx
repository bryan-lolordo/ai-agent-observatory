/**
 * OptimizationHierarchy - Expandable Rows Table
 *
 * Hierarchical view: Agent -> Operation -> Story -> Fixes -> Calls
 *
 * Features:
 * - Expandable rows at each level
 * - Status badges and progress indicators
 * - Inline baseline info and fix history
 * - Click to mark fixes as complete
 */

import { useState } from 'react';
import { ChevronRight, ChevronDown, Check, Clock, XCircle, Plus } from 'lucide-react';
import { STORY_THEMES } from '../../config/theme';

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
    pending: { bg: 'bg-gray-700', text: 'text-gray-300', label: 'Pending' },
    in_progress: { bg: 'bg-blue-600', text: 'text-white', label: 'In Progress' },
    complete: { bg: 'bg-green-600', text: 'text-white', label: 'Complete' },
    skipped: { bg: 'bg-gray-600', text: 'text-gray-300', label: 'Skipped' },
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
      <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-green-500 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-500">{complete}/{total}</span>
    </div>
  );
};

// Agent Row (top level)
const AgentRow = ({ agent, expanded, onToggle, onStoryClick }) => {
  return (
    <>
      <tr
        onClick={onToggle}
        className="border-b border-gray-800 cursor-pointer hover:bg-gray-800/50 transition-colors"
      >
        <td className="py-3 px-4">
          <div className="flex items-center gap-2">
            {expanded ? (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500" />
            )}
            <span className="font-medium text-gray-200">{agent.agent_name}</span>
            <span className="text-xs text-gray-500">Agent</span>
          </div>
        </td>
        <td className="py-3 px-4 text-right text-gray-400">{agent.call_count}</td>
        <td className="py-3 px-4"></td>
        <td className="py-3 px-4"></td>
        <td className="py-3 px-4">
          <ProgressIndicator complete={agent.complete_count} total={agent.total_stories} />
        </td>
        <td className="py-3 px-4"></td>
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
        className="border-b border-gray-800 cursor-pointer hover:bg-gray-800/30 transition-colors bg-gray-900/30"
      >
        <td className="py-2.5 px-4 pl-10">
          <div className="flex items-center gap-2">
            {expanded ? (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500" />
            )}
            <span className="font-mono text-purple-400">{operation.operation}</span>
          </div>
        </td>
        <td className="py-2.5 px-4 text-right text-gray-500">{operation.call_count}</td>
        <td className="py-2.5 px-4"></td>
        <td className="py-2.5 px-4"></td>
        <td className="py-2.5 px-4">
          <ProgressIndicator complete={operation.complete_count} total={operation.total_stories} />
        </td>
        <td className="py-2.5 px-4"></td>
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
        className={`border-b border-gray-800 cursor-pointer transition-colors bg-gray-900/50 ${storyTheme.rowHover}`}
      >
        <td className="py-2.5 px-4 pl-16" onClick={() => setExpanded(!expanded)}>
          <div className="flex items-center gap-2">
            {expanded ? (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500" />
            )}
            <span className="text-lg">{story.story_icon}</span>
            <span className={storyTheme.text}>
              {story.story_id.charAt(0).toUpperCase() + story.story_id.slice(1)}
            </span>
          </div>
        </td>
        <td className="py-2.5 px-4 text-right text-gray-500" onClick={() => setExpanded(!expanded)}>
          {story.call_count}
        </td>
        <td className="py-2.5 px-4" onClick={() => setExpanded(!expanded)}>
          <div className="flex items-center gap-2">
            <span className="text-gray-300">{story.baseline_value_formatted}</span>
            {hasImprovement && (
              <>
                <span className="text-gray-600">→</span>
                <span className={storyTheme.text}>{story.current_value_formatted}</span>
              </>
            )}
          </div>
        </td>
        <td className="py-2.5 px-4 text-center" onClick={() => setExpanded(!expanded)}>
          {story.fix_count > 0 ? (
            <span className="text-green-400">{story.fix_count} fix{story.fix_count > 1 ? 'es' : ''}</span>
          ) : (
            <span className="text-gray-600">0 fixes</span>
          )}
        </td>
        <td className="py-2.5 px-4" onClick={() => setExpanded(!expanded)}>
          <StatusBadge status={story.status} />
        </td>
        <td className="py-2.5 px-4 text-right">
          {hasImprovement ? (
            <span className="text-green-400 font-medium">{story.improvement_formatted}</span>
          ) : (
            <span className="text-gray-600">—</span>
          )}
        </td>
      </tr>

      {/* Expanded content: Baseline + Fixes + Calls */}
      {expanded && (
        <tr className="border-b border-gray-800 bg-gray-950">
          <td colSpan={6} className="p-0">
            <div className="pl-20 pr-4 py-3 space-y-3">
              {/* Baseline info */}
              <div className={`p-3 rounded border ${storyTheme.borderLight} bg-gray-900/50`}>
                <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">Baseline</div>
                <div className="flex gap-6 text-sm">
                  <div>
                    <span className="text-gray-500">Avg: </span>
                    <span className="text-gray-300">{story.baseline_value_formatted}</span>
                  </div>
                  {story.baseline_p95_formatted && (
                    <div>
                      <span className="text-gray-500">P95: </span>
                      <span className="text-gray-300">{story.baseline_p95_formatted}</span>
                    </div>
                  )}
                  <div>
                    <span className="text-gray-500">Calls: </span>
                    <span className="text-gray-300">{story.baseline_call_count}</span>
                  </div>
                  {story.baseline_date && (
                    <div>
                      <span className="text-gray-500">Captured: </span>
                      <span className="text-gray-300">
                        {new Date(story.baseline_date).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Applied Fixes */}
              {story.fixes && story.fixes.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs text-gray-500 uppercase tracking-wide">Applied Fixes</div>
                  {story.fixes.map((fix, idx) => (
                    <div
                      key={fix.id}
                      className="flex items-center gap-4 p-2 rounded bg-gray-900/30 border border-gray-800"
                    >
                      <Check className="w-4 h-4 text-green-500" />
                      <span className={`font-medium ${storyTheme.text}`}>{fix.fix_type}</span>
                      <span className="text-gray-500">
                        {fix.before_value?.toFixed(2)} → {fix.after_value?.toFixed(2)}
                      </span>
                      {fix.improvement_pct && (
                        <span className="text-green-400">
                          {fix.improvement_pct > 0 ? '-' : '+'}{Math.abs(fix.improvement_pct).toFixed(0)}%
                        </span>
                      )}
                      {fix.applied_date && (
                        <span className="text-gray-600 text-xs">
                          {new Date(fix.applied_date).toLocaleDateString()}
                        </span>
                      )}
                      {fix.git_commit && (
                        <span className="font-mono text-xs text-gray-600">
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
                  <div className="text-xs text-gray-500 uppercase tracking-wide">Sample Calls</div>
                  <div className="flex flex-wrap gap-2">
                    {story.calls.slice(0, 5).map((call) => (
                      <div
                        key={call.id}
                        onClick={() => onStoryClick && onStoryClick(story, call)}
                        className="px-2 py-1 rounded bg-gray-800 border border-gray-700 text-xs cursor-pointer hover:bg-gray-700 transition-colors"
                      >
                        <span className="font-mono text-gray-400">{call.id?.slice(0, 8)}...</span>
                        <span className="text-gray-500 ml-2">{call.metric_formatted}</span>
                      </div>
                    ))}
                    {story.calls.length > 5 && (
                      <div className="px-2 py-1 text-xs text-gray-600">
                        +{story.calls.length - 5} more
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Action buttons */}
              <div className="flex gap-2 pt-2">
                <button
                  onClick={() => onStoryClick && onStoryClick(story)}
                  className={`px-3 py-1.5 rounded text-xs font-medium ${storyTheme.bg} text-white hover:opacity-80 transition-opacity`}
                >
                  <Plus className="w-3 h-3 inline mr-1" />
                  Add Fix
                </button>
                {story.status === 'pending' && (
                  <button
                    className="px-3 py-1.5 rounded text-xs font-medium bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors"
                  >
                    Mark In Progress
                  </button>
                )}
                {story.status !== 'complete' && story.status !== 'skipped' && (
                  <button
                    className="px-3 py-1.5 rounded text-xs font-medium bg-gray-800 text-gray-400 hover:bg-gray-700 transition-colors"
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
  const [expandedAgents, setExpandedAgents] = useState({});

  const toggleAgent = (agentName) => {
    setExpandedAgents(prev => ({
      ...prev,
      [agentName]: !prev[agentName]
    }));
  };

  if (!hierarchy || !hierarchy.agents || hierarchy.agents.length === 0) {
    return (
      <div className="p-8 text-center text-gray-500">
        No optimization opportunities detected. Your system looks well-optimized!
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-gray-800/50">
          <tr className="border-b border-gray-700">
            <th className="text-left py-3 px-4 text-gray-400 font-medium">
              Agent / Operation / Story
            </th>
            <th className="text-right py-3 px-4 text-gray-400 font-medium w-20">Calls</th>
            <th className="text-left py-3 px-4 text-gray-400 font-medium w-40">Metric</th>
            <th className="text-center py-3 px-4 text-gray-400 font-medium w-24">Fixes</th>
            <th className="text-left py-3 px-4 text-gray-400 font-medium w-32">Status</th>
            <th className="text-right py-3 px-4 text-gray-400 font-medium w-24">Impact</th>
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
