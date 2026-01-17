/**
 * ComparisonDetail - Narrative-Driven Optimization Story View
 *
 * Tells the story of optimization impact through:
 * 1. Hero stats (headline wins)
 * 2. Strategy explanation (batching + caching)
 * 3. Top wins ranking
 * 4. Detailed metrics table (expandable)
 *
 * URL: /stories/optimization/comparison
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { STORY_THEMES } from '../../../config/theme';
import { StoryPageSkeleton } from '../../../components/common/Loading';
import StoryNavTabs from '../../../components/stories/StoryNavTabs';
import { BASE_THEME } from '../../../utils/themeUtils';
import PageContainer from '../../../components/layout/PageContainer';
import {
  Code2,
  Table,
  BarChart3,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Zap,
  Database,
  Hash,
  Settings,
  ChevronDown,
  ChevronRight,
  Trophy,
  BookOpen,
  ArrowRight,
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// =============================================================================
// HERO STATS SECTION
// =============================================================================

const HeroStats = ({ baseline, optimized }) => {
  // Calculate improvement percentages
  const latencyImprovement = baseline.avg_latency_ms && optimized.avg_latency_ms
    ? ((baseline.avg_latency_ms - optimized.avg_latency_ms) / baseline.avg_latency_ms * 100)
    : 0;

  const costImprovement = baseline.total_cost && optimized.total_cost
    ? ((baseline.total_cost - optimized.total_cost) / baseline.total_cost * 100)
    : 0;

  const tokenImprovement = baseline.total_tokens && optimized.total_tokens
    ? ((baseline.total_tokens - optimized.total_tokens) / baseline.total_tokens * 100)
    : 0;

  // Quality improvement (higher is better)
  const qualityImprovement = baseline.avg_quality && optimized.avg_quality
    ? ((optimized.avg_quality - baseline.avg_quality) / baseline.avg_quality * 100)
    : 0;

  const latencySavedMs = baseline.avg_latency_ms - optimized.avg_latency_ms;
  const costSaved = baseline.total_cost - optimized.total_cost;
  const tokensSaved = baseline.total_tokens - optimized.total_tokens;

  const cacheHits = optimized.cache_hits || 0;
  const cacheHitRate = optimized.cache_hit_rate || 0;

  // Format large numbers
  const formatTokens = (num) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(0)}K`;
    return num.toString();
  };

  const stats = [
    {
      label: 'Faster',
      value: `${latencyImprovement.toFixed(1)}%`,
      subValue: `${(latencySavedMs / 1000).toFixed(1)}s saved`,
      icon: Zap,
      color: 'blue',
      show: latencyImprovement > 0,
    },
    {
      label: 'Cheaper',
      value: `${costImprovement.toFixed(1)}%`,
      subValue: `$${costSaved.toFixed(2)} saved`,
      icon: DollarSign,
      color: 'green',
      show: costImprovement > 0,
    },
    {
      label: 'Quality Score',
      value: optimized.avg_quality ? `${optimized.avg_quality.toFixed(1)}/10` : '—',
      subValue: qualityImprovement > 0
        ? `+${qualityImprovement.toFixed(1)}% vs baseline`
        : baseline.avg_quality
          ? `${baseline.avg_quality.toFixed(1)}/10 baseline`
          : 'No judge scores',
      icon: TrendingUp,
      color: 'purple',
      show: optimized.avg_quality !== null && optimized.avg_quality !== undefined,
    },
    {
      label: 'Tokens Saved',
      value: `${tokenImprovement.toFixed(1)}%`,
      subValue: `${formatTokens(tokensSaved)} tokens`,
      icon: Hash,
      color: 'orange',
      show: tokensSaved > 0,
    },
    {
      label: 'Cache Hits',
      value: cacheHits.toString(),
      subValue: `${cacheHitRate.toFixed(1)}% hit rate`,
      icon: Database,
      color: 'cyan',
      show: cacheHits > 0,
    },
  ].filter(s => s.show);

  const colorClasses = {
    green: {
      border: 'border-green-500/50',
      shadow: 'shadow-[0_0_15px_rgba(34,197,94,0.3)]',
      text: 'text-green-400',
      bg: 'bg-green-500/10',
    },
    blue: {
      border: 'border-blue-500/50',
      shadow: 'shadow-[0_0_15px_rgba(59,130,246,0.3)]',
      text: 'text-blue-400',
      bg: 'bg-blue-500/10',
    },
    purple: {
      border: 'border-purple-500/50',
      shadow: 'shadow-[0_0_15px_rgba(147,51,234,0.3)]',
      text: 'text-purple-400',
      bg: 'bg-purple-500/10',
    },
    orange: {
      border: 'border-orange-500/50',
      shadow: 'shadow-[0_0_15px_rgba(249,115,22,0.3)]',
      text: 'text-orange-400',
      bg: 'bg-orange-500/10',
    },
    cyan: {
      border: 'border-cyan-500/50',
      shadow: 'shadow-[0_0_15px_rgba(6,182,212,0.3)]',
      text: 'text-cyan-400',
      bg: 'bg-cyan-500/10',
    },
  };

  if (stats.length === 0) return null;

  return (
    <div className="mb-8">
      <div className={`grid grid-cols-${Math.min(stats.length, 4)} gap-4`}>
        {stats.map((stat, idx) => {
          const colors = colorClasses[stat.color];
          const Icon = stat.icon;
          return (
            <div
              key={idx}
              className={`rounded-xl border ${colors.border} ${colors.shadow} ${BASE_THEME.container.primary} p-5 text-center`}
            >
              <div className={`inline-flex items-center justify-center w-10 h-10 rounded-full ${colors.bg} mb-2`}>
                <Icon className={`w-5 h-5 ${colors.text}`} />
              </div>
              <div className={`text-3xl font-bold ${colors.text} mb-1`}>
                {stat.value}
              </div>
              <div className={`text-base font-medium ${BASE_THEME.text.primary} mb-1`}>
                {stat.label}
              </div>
              <div className={`text-sm ${BASE_THEME.text.muted}`}>
                {stat.subValue}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// =============================================================================
// TOP WINS SECTION - Detailed operation breakdown
// =============================================================================

const TopWinsSection = ({ baseline, optimized }) => {
  const wins = useMemo(() => {
    const results = [];
    const baseOps = baseline.by_operation || {};
    const optOps = optimized.by_operation || {};

    for (const [key, baseOp] of Object.entries(baseOps)) {
      const optOp = optOps[key];
      if (optOp && baseOp.count > 0) {
        // Calculate total latency (not avg)
        const baseTotalLatency = baseOp.avg_latency * baseOp.count;
        const optTotalLatency = optOp.avg_latency * optOp.count;
        const totalLatencySaved = baseTotalLatency - optTotalLatency;
        const totalLatencyPctImproved = baseTotalLatency > 0
          ? (totalLatencySaved / baseTotalLatency) * 100
          : 0;

        // Call reduction
        const callChange = optOp.count - baseOp.count;
        const callChangePct = baseOp.count > 0
          ? ((callChange) / baseOp.count) * 100
          : 0;

        // Avg latency change
        const avgLatencySaved = baseOp.avg_latency - optOp.avg_latency;
        const avgLatencyPctImproved = baseOp.avg_latency > 0
          ? (avgLatencySaved / baseOp.avg_latency) * 100
          : 0;

        // Cost savings
        const baseTotalCost = baseOp.avg_cost * baseOp.count;
        const optTotalCost = optOp.avg_cost * optOp.count;
        const costSaved = baseTotalCost - optTotalCost;

        // Determine technique based on patterns
        let technique = '';
        let hasCacheHits = false;
        let cacheHitRate = 0;

        // Check for caching (fewer calls with similar work, or explicit cache data)
        if (optOp.count > baseOp.count && avgLatencyPctImproved > 50) {
          technique = 'Intelligent caching';
          hasCacheHits = true;
          // Estimate cache rate based on latency improvement
          cacheHitRate = Math.min(95, avgLatencyPctImproved);
        } else if (callChangePct < -30) {
          technique = 'Batching multiple items';
        } else if (avgLatencyPctImproved > 80 && optOp.count === 0) {
          technique = 'Complete cache coverage';
          hasCacheHits = true;
          cacheHitRate = 100;
        } else if (avgLatencyPctImproved > 50) {
          technique = 'Optimized prompts';
        } else if (callChangePct < 0) {
          technique = 'Reduced redundant calls';
        }

        // Only include if there's meaningful improvement
        if (totalLatencySaved > 100 || costSaved > 0.01 || Math.abs(callChangePct) > 10) {
          results.push({
            key,
            operation: baseOp.operation,
            agent: baseOp.agent,
            // Counts
            baseCount: baseOp.count,
            optCount: optOp.count,
            callChange,
            callChangePct,
            // Latency
            baseAvgLatency: baseOp.avg_latency,
            optAvgLatency: optOp.avg_latency,
            avgLatencyPctImproved,
            baseTotalLatency,
            optTotalLatency,
            totalLatencySaved,
            totalLatencyPctImproved,
            // Cost
            costSaved,
            // Technique
            technique,
            hasCacheHits,
            cacheHitRate,
          });
        }
      }
    }

    // Sort by total latency saved (biggest impact first)
    return results.sort((a, b) => b.totalLatencySaved - a.totalLatencySaved).slice(0, 5);
  }, [baseline, optimized]);

  const medalColors = ['bg-yellow-500', 'bg-gray-400', 'bg-amber-600', 'bg-gray-500', 'bg-gray-600'];
  const medalText = ['text-yellow-900', 'text-gray-900', 'text-amber-900', 'text-gray-200', 'text-gray-200'];

  if (wins.length === 0) {
    return null;
  }

  const formatTime = (ms) => {
    if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
    return `${ms.toFixed(0)}ms`;
  };

  return (
    <div className="mb-8">
      <div className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} overflow-hidden`}>
        {/* Section Header */}
        <div className={`flex items-center gap-3 p-4 ${BASE_THEME.container.secondary}`}>
          <Trophy className="w-5 h-5 text-yellow-400" />
          <span className={`font-semibold ${BASE_THEME.text.primary}`}>Top Improvements</span>
          <span className={`text-sm ${BASE_THEME.text.muted}`}>({wins.length} operations)</span>
        </div>

        {/* Table */}
        <table className="w-full">
          <thead>
            <tr className={`border-b ${BASE_THEME.border.default}`}>
              <th className={`py-2 px-4 text-left text-xs font-medium ${BASE_THEME.text.muted} w-2/5`}>
                Operation
              </th>
              <th className={`py-2 px-4 text-center text-xs font-medium text-blue-400 w-1/5`}>
                Baseline
              </th>
              <th className={`py-2 px-4 text-center text-xs font-medium text-green-400 w-1/5`}>
                Optimized
              </th>
              <th className={`py-2 px-4 text-center text-xs font-medium ${BASE_THEME.text.muted} w-1/5`}>
                Impact
              </th>
            </tr>
          </thead>
          <tbody>
            {wins.map((win, idx) => (
              <tr
                key={win.key}
                className={`border-b ${BASE_THEME.border.default} hover:bg-gray-800/20 transition-colors`}
              >
                {/* Operation column */}
                <td className="py-3 px-4">
                  <div className="flex items-center gap-3">
                    <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${medalColors[idx]} ${medalText[idx]}`}>
                      {idx + 1}
                    </span>
                    <div>
                      <div className={`font-medium ${BASE_THEME.text.primary}`}>
                        {win.operation.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className={`text-xs ${BASE_THEME.text.muted}`}>{win.agent}</span>
                        {win.technique && (
                          <span className="text-xs px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400">
                            {win.technique}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </td>

                {/* Baseline column */}
                <td className={`py-3 px-4 text-center`}>
                  <div className={`font-mono text-sm ${BASE_THEME.text.muted}`}>
                    {formatTime(win.baseTotalLatency)}
                  </div>
                  <div className={`text-xs ${BASE_THEME.text.muted}`}>
                    {win.baseCount} calls
                  </div>
                </td>

                {/* Optimized column */}
                <td className={`py-3 px-4 text-center`}>
                  <div className={`font-mono text-sm ${BASE_THEME.text.primary}`}>
                    {formatTime(win.optTotalLatency)}
                  </div>
                  <div className={`text-xs ${BASE_THEME.text.muted}`}>
                    {win.optCount} calls
                  </div>
                </td>

                {/* Impact column */}
                <td className="py-3 px-4 text-center">
                  <div className="flex items-center justify-center gap-1 text-green-400">
                    <TrendingUp className="w-3 h-3" />
                    <span className="font-medium">-{win.totalLatencyPctImproved.toFixed(0)}%</span>
                  </div>
                  <div className="text-xs text-green-400/70">
                    {formatTime(win.totalLatencySaved)} saved
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// =============================================================================
// DETAILED METRICS TABLE - Full comparison with all sections
// =============================================================================

const ImpactBadge = ({ value, isImproved, isNeutral }) => {
  if (!value || value === '—' || value === 'N/A') {
    return <span className="text-gray-500">—</span>;
  }

  // Neutral metrics (like call count) - just show the value without color
  if (isNeutral) {
    return (
      <span className={`font-medium text-sm ${BASE_THEME.text.secondary}`}>{value}</span>
    );
  }

  return (
    <div className={`flex items-center justify-center gap-1 ${isImproved ? 'text-green-400' : 'text-red-400'}`}>
      {isImproved ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
      <span className="font-medium text-sm">{value}</span>
    </div>
  );
};

// Section icons for the table
const SECTION_ICONS = {
  cost: DollarSign,
  performance: Zap,
  quality: TrendingUp,
  caching: Database,
  tokens: Hash,
  routing: Settings,
  operations: Settings,
};

const SECTION_COLORS = {
  cost: 'text-green-400',
  performance: 'text-blue-400',
  quality: 'text-purple-400',
  caching: 'text-orange-400',
  tokens: 'text-cyan-400',
  routing: 'text-pink-400',
  operations: 'text-pink-400',
};

// =============================================================================
// OPERATIONS HIERARCHY TABLE - Cascading Agent → Operation → Metrics
// =============================================================================

const OperationsHierarchyTable = ({ baseline, optimized }) => {
  const [expandedAgents, setExpandedAgents] = useState({});
  const [expandedOperations, setExpandedOperations] = useState({});

  // Build hierarchy from by_operation data
  const hierarchy = useMemo(() => {
    const baseOps = baseline?.by_operation || {};
    const optOps = optimized?.by_operation || {};
    const allKeys = new Set([...Object.keys(baseOps), ...Object.keys(optOps)]);

    // Group by agent
    const byAgent = {};

    for (const key of allKeys) {
      const baseOp = baseOps[key] || {};
      const optOp = optOps[key] || {};

      const agent = baseOp.agent || optOp.agent || 'Unknown';
      const operation = baseOp.operation || optOp.operation || key;

      if (!byAgent[agent]) {
        byAgent[agent] = { operations: {} };
      }

      // Build metrics for this operation
      const metrics = [];

      // Calls - neutral metric, not better or worse
      const baseCount = baseOp.count || 0;
      const optCount = optOp.count || 0;
      if (baseCount > 0 || optCount > 0) {
        const change = baseCount > 0 ? ((optCount - baseCount) / baseCount) * 100 : 0;
        metrics.push({
          label: 'Calls',
          baseline: baseCount.toString(),
          optimized: optCount.toString(),
          change: change !== 0 ? `${change > 0 ? '+' : ''}${change.toFixed(0)}%` : '—',
          isNeutral: true, // Calls are informational, not good/bad
        });
      }

      // Avg Latency
      const baseLat = baseOp.avg_latency || 0;
      const optLat = optOp.avg_latency || 0;
      if (baseLat > 0 || optLat > 0) {
        const change = baseLat > 0 ? ((baseLat - optLat) / baseLat) * 100 : 0;
        const formatLat = (ms) => ms >= 1000 ? `${(ms / 1000).toFixed(2)}s` : `${ms.toFixed(0)}ms`;
        metrics.push({
          label: 'Avg Latency',
          baseline: formatLat(baseLat),
          optimized: formatLat(optLat),
          change: change !== 0 ? `${change > 0 ? '-' : '+'}${Math.abs(change).toFixed(0)}%` : '—',
          isImproved: change > 0,
        });
      }

      // Avg Cost
      const baseCost = baseOp.avg_cost || 0;
      const optCost = optOp.avg_cost || 0;
      if (baseCost > 0 || optCost > 0) {
        const change = baseCost > 0 ? ((baseCost - optCost) / baseCost) * 100 : 0;
        metrics.push({
          label: 'Avg Cost',
          baseline: `$${baseCost.toFixed(3)}`,
          optimized: `$${optCost.toFixed(3)}`,
          change: change !== 0 ? `${change > 0 ? '-' : '+'}${Math.abs(change).toFixed(0)}%` : '—',
          isImproved: change > 0,
        });
      }

      // Avg Prompt Tokens
      const baseTokens = baseOp.avg_prompt_tokens || 0;
      const optTokens = optOp.avg_prompt_tokens || 0;
      if (baseTokens > 0 || optTokens > 0) {
        const change = baseTokens > 0 ? ((baseTokens - optTokens) / baseTokens) * 100 : 0;
        metrics.push({
          label: 'Avg Prompt Tokens',
          baseline: baseTokens.toFixed(0),
          optimized: optTokens.toFixed(0),
          change: change !== 0 ? `${change > 0 ? '-' : '+'}${Math.abs(change).toFixed(0)}%` : '—',
          isImproved: change > 0,
        });
      }

      byAgent[agent].operations[operation] = { metrics };
    }

    return byAgent;
  }, [baseline, optimized]);

  const toggleAgent = (agent) => {
    setExpandedAgents(prev => ({ ...prev, [agent]: !prev[agent] }));
  };

  const toggleOperation = (key) => {
    setExpandedOperations(prev => ({ ...prev, [key]: prev[key] === false ? true : false }));
  };

  if (Object.keys(hierarchy).length === 0) {
    return (
      <div className={`p-4 text-center ${BASE_THEME.text.muted}`}>
        No operation-specific metrics available
      </div>
    );
  }

  return (
    <div className="border-t border-gray-700/50">
      <table className="w-full">
        <thead>
          <tr className={`border-b ${BASE_THEME.border.default}`}>
            <th className={`py-2 px-4 text-left text-xs font-medium ${BASE_THEME.text.muted} w-2/5`}>
              Agent / Operation / Metric
            </th>
            <th className={`py-2 px-4 text-center text-xs font-medium text-blue-400 w-1/5`}>
              Baseline
            </th>
            <th className={`py-2 px-4 text-center text-xs font-medium text-green-400 w-1/5`}>
              Optimized
            </th>
            <th className={`py-2 px-4 text-center text-xs font-medium ${BASE_THEME.text.muted} w-1/5`}>
              Impact
            </th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(hierarchy).map(([agentName, agentData]) => {
            const isAgentExpanded = expandedAgents[agentName] !== false;

            return (
              <React.Fragment key={agentName}>
                {/* Agent Row */}
                <tr
                  onClick={() => toggleAgent(agentName)}
                  className={`cursor-pointer hover:bg-gray-800/30 transition-colors ${BASE_THEME.container.secondary}`}
                >
                  <td className="py-3 px-4" colSpan={4}>
                    <div className="flex items-center gap-3">
                      {isAgentExpanded ? (
                        <ChevronDown className="w-4 h-4 text-pink-400" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-pink-400" />
                      )}
                      <span className={`font-semibold ${BASE_THEME.text.primary}`}>{agentName}</span>
                      <span className={`text-xs px-2 py-0.5 rounded bg-gray-700/50 ${BASE_THEME.text.muted}`}>Agent</span>
                    </div>
                  </td>
                </tr>

                {/* Operations under this agent */}
                {isAgentExpanded && Object.entries(agentData.operations).map(([opName, opData]) => {
                  const opKey = `${agentName}_${opName}`;
                  const isOpExpanded = expandedOperations[opKey] !== false;

                  return (
                    <React.Fragment key={opKey}>
                      {/* Operation Row */}
                      <tr
                        onClick={() => toggleOperation(opKey)}
                        className={`cursor-pointer hover:bg-gray-800/20 transition-colors border-t border-gray-700/30`}
                      >
                        <td className="py-2 px-4 pl-10" colSpan={4}>
                          <div className="flex items-center gap-3">
                            {isOpExpanded ? (
                              <ChevronDown className="w-4 h-4 text-purple-400" />
                            ) : (
                              <ChevronRight className="w-4 h-4 text-purple-400" />
                            )}
                            <span className="font-mono text-purple-400">{opName}</span>
                          </div>
                        </td>
                      </tr>

                      {/* Metrics under this operation */}
                      {isOpExpanded && opData.metrics.map((metric, idx) => (
                        <tr
                          key={`${opKey}_${idx}`}
                          className={`border-t border-gray-700/20 hover:bg-gray-800/10 transition-colors`}
                        >
                          <td className={`py-2 px-4 pl-16 ${BASE_THEME.text.secondary} text-sm`}>
                            {metric.label}
                          </td>
                          <td className={`py-2 px-4 text-center font-mono text-sm ${BASE_THEME.text.muted}`}>
                            {metric.baseline}
                          </td>
                          <td className={`py-2 px-4 text-center font-mono text-sm ${BASE_THEME.text.primary}`}>
                            {metric.optimized}
                          </td>
                          <td className="py-2 px-4 text-center">
                            <ImpactBadge value={metric.change} isImproved={metric.isImproved} isNeutral={metric.isNeutral} />
                          </td>
                        </tr>
                      ))}
                    </React.Fragment>
                  );
                })}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

const DetailedMetricsTable = ({ comparison, baseline, optimized, expandedSections, toggleSection }) => {
  // Group comparison rows by section
  const sections = useMemo(() => {
    const grouped = {};
    let currentSection = null;

    for (const row of comparison || []) {
      if (row.is_header) {
        // Header rows use 'label' field and 'section' for the key
        currentSection = row.section || row.label?.toLowerCase().replace(' metrics', '');
        grouped[currentSection] = {
          name: row.label || row.section,
          rows: [],
        };
      } else if (currentSection && grouped[currentSection]) {
        grouped[currentSection].rows.push(row);
      }
    }

    return grouped;
  }, [comparison]);

  if (Object.keys(sections).length === 0) {
    return (
      <div className={`rounded-lg ${BASE_THEME.container.primary} p-8 text-center`}>
        <p className={BASE_THEME.text.muted}>No comparison data available</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {Object.entries(sections).map(([sectionKey, section]) => {
        const Icon = SECTION_ICONS[sectionKey] || Settings;
        const colorClass = SECTION_COLORS[sectionKey] || 'text-gray-400';
        const isExpanded = expandedSections[sectionKey] !== false;

        return (
          <div
            key={sectionKey}
            className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} overflow-hidden`}
          >
            {/* Section Header */}
            <div
              className={`flex items-center justify-between p-4 cursor-pointer hover:bg-gray-800/30 transition-colors ${BASE_THEME.container.secondary}`}
              onClick={() => toggleSection(sectionKey)}
            >
              <div className="flex items-center gap-3">
                {isExpanded ? (
                  <ChevronDown className={`w-4 h-4 ${colorClass}`} />
                ) : (
                  <ChevronRight className={`w-4 h-4 ${colorClass}`} />
                )}
                <Icon className={`w-5 h-5 ${colorClass}`} />
                <span className={`font-semibold ${BASE_THEME.text.primary}`}>
                  {section.name}
                </span>
                {sectionKey !== 'operations' && (
                  <span className={`text-sm ${BASE_THEME.text.muted}`}>
                    ({section.rows.length} metrics)
                  </span>
                )}
              </div>
            </div>

            {/* Section Table - Use hierarchy for operations, flat table for others */}
            {isExpanded && sectionKey === 'operations' && (
              <OperationsHierarchyTable baseline={baseline} optimized={optimized} />
            )}

            {isExpanded && sectionKey !== 'operations' && section.rows.length > 0 && (
              <div className="border-t border-gray-700/50">
                <table className="w-full">
                  <thead>
                    <tr className={`border-b ${BASE_THEME.border.default}`}>
                      <th className={`py-2 px-4 text-left text-xs font-medium ${BASE_THEME.text.muted} w-2/5`}>
                        Metric
                      </th>
                      <th className={`py-2 px-4 text-center text-xs font-medium text-blue-400 w-1/5`}>
                        Baseline
                      </th>
                      <th className={`py-2 px-4 text-center text-xs font-medium text-green-400 w-1/5`}>
                        Optimized
                      </th>
                      <th className={`py-2 px-4 text-center text-xs font-medium ${BASE_THEME.text.muted} w-1/5`}>
                        Impact
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {section.rows.map((row, idx) => {
                      // Use API field names: baseline_fmt, optimized_fmt, indicator, direction
                      const baselineDisplay = row.baseline_fmt || row.baseline || '—';
                      const optimizedDisplay = row.optimized_fmt || row.optimized || '—';
                      const impactDisplay = row.indicator || '—';
                      const isImproved = row.direction === 'improved';

                      return (
                        <tr
                          key={idx}
                          className={`border-b ${BASE_THEME.border.default} hover:bg-gray-800/20 transition-colors`}
                        >
                          <td className={`py-2 px-4 ${BASE_THEME.text.secondary} text-sm`}>
                            {row.metric}
                          </td>
                          <td className={`py-2 px-4 text-center font-mono text-sm ${BASE_THEME.text.muted}`}>
                            {baselineDisplay}
                          </td>
                          <td className={`py-2 px-4 text-center font-mono text-sm ${BASE_THEME.text.primary}`}>
                            {optimizedDisplay}
                          </td>
                          <td className="py-2 px-4 text-center">
                            <ImpactBadge value={impactDisplay} isImproved={isImproved} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function ComparisonDetail() {
  const navigate = useNavigate();
  const theme = STORY_THEMES.optimization;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('narrative'); // 'narrative' or 'table'
  const [showDetailedTable, setShowDetailedTable] = useState(false);
  const [expandedSections, setExpandedSections] = useState({});

  // Fetch comparison data
  useEffect(() => {
    const fetchComparison = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE}/api/stories/optimization/comparison`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const result = await response.json();
        setData(result);
      } catch (err) {
        console.error('Error fetching comparison:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchComparison();
  }, []);

  const toggleSection = (sectionKey) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionKey]: prev[sectionKey] === false ? true : false,
    }));
  };

  if (loading) return <StoryPageSkeleton />;

  if (error) {
    return (
      <div className={`min-h-screen ${BASE_THEME.container.tertiary} p-8`}>
        <PageContainer>
          <div className={`${BASE_THEME.status.error.bg} border ${BASE_THEME.status.error.border} rounded-lg p-6`}>
            <h2 className={`text-xl font-bold ${BASE_THEME.status.error.textBold} mb-2`}>Error Loading Comparison</h2>
            <p className={BASE_THEME.text.secondary}>{error}</p>
          </div>
        </PageContainer>
      </div>
    );
  }

  const {
    baseline_period = {},
    optimized_period = {},
    baseline = {},
    optimized = {},
    comparison = [],
  } = data || {};

  const hasData = baseline.total_calls > 0 || optimized.total_calls > 0;

  return (
    <div className={`min-h-screen ${BASE_THEME.container.tertiary} ${BASE_THEME.text.primary}`}>
      <StoryNavTabs activeStory="optimization" />

      <PageContainer>
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <h1 className={`text-3xl font-bold ${theme.text} flex items-center gap-3`}>
              <span className="text-4xl">{theme.emoji}</span>
              Optimization Impact
            </h1>
            <div className="flex items-center gap-2">
              {/* View Mode Toggle */}
              <div className={`flex rounded-lg ${BASE_THEME.container.secondary} p-1`}>
                <button
                  onClick={() => setViewMode('narrative')}
                  className={`px-3 py-1.5 rounded text-sm transition-colors flex items-center gap-1.5 ${
                    viewMode === 'narrative'
                      ? `${theme.bg} text-white`
                      : `${BASE_THEME.text.muted} hover:${BASE_THEME.text.secondary}`
                  }`}
                >
                  <BookOpen className="w-4 h-4" />
                  Story
                </button>
                <button
                  onClick={() => setViewMode('table')}
                  className={`px-3 py-1.5 rounded text-sm transition-colors flex items-center gap-1.5 ${
                    viewMode === 'table'
                      ? `${theme.bg} text-white`
                      : `${BASE_THEME.text.muted} hover:${BASE_THEME.text.secondary}`
                  }`}
                >
                  <Table className="w-4 h-4" />
                  Table
                </button>
              </div>

              {/* Page Navigation */}
              <button
                onClick={() => navigate('/stories/optimization')}
                className={`px-3 py-1.5 rounded text-sm ${BASE_THEME.text.muted} hover:${BASE_THEME.text.secondary} hover:bg-gray-700/50 transition-colors flex items-center gap-1.5`}
              >
                <BarChart3 className="w-4 h-4" />
                Tracking
              </button>
              <button
                onClick={() => navigate('/stories/optimization/code-view')}
                className={`px-3 py-1.5 rounded text-sm ${BASE_THEME.text.muted} hover:${BASE_THEME.text.secondary} hover:bg-gray-700/50 transition-colors flex items-center gap-1.5`}
              >
                <Code2 className="w-4 h-4" />
                Code
              </button>
            </div>
          </div>

          {/* Period Info */}
          <div className={`flex items-center gap-4 mt-4 ${BASE_THEME.text.muted} text-sm`}>
            <div className="flex items-center gap-2">
              <span className="font-medium text-blue-400">Baseline:</span>
              <span>
                {baseline_period.start && baseline_period.end
                  ? `${baseline_period.start} to ${baseline_period.end}`
                  : 'N/A'}
              </span>
              <span className="text-gray-500">({baseline.total_calls || 0} calls)</span>
            </div>
            <span className="text-gray-600">|</span>
            <div className="flex items-center gap-2">
              <span className="font-medium text-green-400">Optimized:</span>
              <span>
                {optimized_period.start && optimized_period.end
                  ? `${optimized_period.start} to ${optimized_period.end}`
                  : 'N/A'}
              </span>
              <span className="text-gray-500">({optimized.total_calls || 0} calls)</span>
            </div>
          </div>
        </div>

        {/* No Data State */}
        {!hasData && (
          <div className={`rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary} p-12 text-center`}>
            <Database className={`w-12 h-12 ${BASE_THEME.text.muted} mx-auto mb-4`} />
            <h2 className={`text-xl font-semibold ${BASE_THEME.text.primary} mb-2`}>No Comparison Data</h2>
            <p className={BASE_THEME.text.muted}>
              Tag your LLM calls with <code className="text-green-400">phase='baseline'</code> or{' '}
              <code className="text-green-400">phase='optimized'</code> to see comparisons.
            </p>
          </div>
        )}

        {/* Narrative View */}
        {hasData && viewMode === 'narrative' && (
          <>
            {/* Hero Stats */}
            <HeroStats baseline={baseline} optimized={optimized} />

            {/* Top Wins */}
            <TopWinsSection baseline={baseline} optimized={optimized} />

            {/* Expandable Detailed Table */}
            <div className="mb-6">
              <button
                onClick={() => setShowDetailedTable(!showDetailedTable)}
                className={`flex items-center gap-2 text-sm ${BASE_THEME.text.muted} hover:${BASE_THEME.text.secondary} transition-colors`}
              >
                {showDetailedTable ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
                <Table className="w-4 h-4" />
                {showDetailedTable ? 'Hide' : 'Show'} Detailed Metrics
              </button>

              {showDetailedTable && (
                <div className="mt-4">
                  <DetailedMetricsTable
                    comparison={comparison}
                    baseline={baseline}
                    optimized={optimized}
                    expandedSections={expandedSections}
                    toggleSection={toggleSection}
                  />
                </div>
              )}
            </div>
          </>
        )}

        {/* Table View (Full) */}
        {hasData && viewMode === 'table' && (
          <DetailedMetricsTable
            comparison={comparison}
            baseline={baseline}
            optimized={optimized}
            expandedSections={expandedSections}
            toggleSection={toggleSection}
          />
        )}

        {/* Help text */}
        <div className={`mt-6 p-4 rounded-lg border ${BASE_THEME.border.default} ${BASE_THEME.container.primary}`}>
          <p className={`text-sm ${BASE_THEME.text.muted}`}>
            <span className="text-green-400 font-medium">How it works:</span> This view compares your baseline period
            against your optimized period. Use the Story/Table toggle to switch between narrative and detailed views.
            Green indicators show improvements, red shows regressions.
          </p>
        </div>
      </PageContainer>
    </div>
  );
}
