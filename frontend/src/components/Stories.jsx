import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, ScatterChart, Scatter, ComposedChart, Line, Area } from 'recharts';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6', '#ec4899'];

// API fetch functions
async function fetchStories(project = null, days = 7) {
  const params = new URLSearchParams();
  if (project) params.append('project', project);
  params.append('days', days);
  
  const response = await fetch(`${API_BASE_URL}/api/stories?${params}`);
  if (!response.ok) throw new Error('Failed to fetch stories');
  return response.json();
}

async function fetchStoryDetail(storyId, project = null, days = 7) {
  const params = new URLSearchParams();
  if (project) params.append('project', project);
  params.append('days', days);
  
  const response = await fetch(`${API_BASE_URL}/api/stories/${storyId}?${params}`);
  if (!response.ok) throw new Error('Failed to fetch story detail');
  return response.json();
}

async function fetchProjects() {
  const response = await fetch(`${API_BASE_URL}/api/projects`);
  if (!response.ok) throw new Error('Failed to fetch projects');
  return response.json();
}

export default function ObservatoryStories() {
  const [activeStory, setActiveStory] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [timeRange, setTimeRange] = useState(7);
  
  const [storiesData, setStoriesData] = useState(null);
  const [storyDetails, setStoryDetails] = useState({});
  
  useEffect(() => {
    fetchProjects()
      .then(data => setProjects(data.projects || []))
      .catch(err => console.error('Failed to load projects:', err));
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    
    fetchStories(selectedProject, timeRange)
      .then(data => {
        setStoriesData(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [selectedProject, timeRange]);

  useEffect(() => {
    if (!storiesData) return;
    
    const storyIds = ['latency', 'cache', 'routing', 'quality', 'token_imbalance', 'system_prompt', 'cost'];
    const storyId = storyIds[activeStory - 1];
    
    if (storyId && !storyDetails[storyId]) {
      fetchStoryDetail(storyId, selectedProject, timeRange)
        .then(data => {
          setStoryDetails(prev => ({ ...prev, [storyId]: data }));
        })
        .catch(err => console.error(`Failed to load ${storyId} detail:`, err));
    }
  }, [activeStory, storiesData, selectedProject, timeRange]);

  const getStory = (id) => {
    if (!storiesData?.stories) return null;
    return storiesData.stories.find(s => s.id === id);
  };

  const getDetail = (id) => storyDetails[id]?.analysis || null;

  // Transform functions
  const transformLatencyData = (detail) => {
    if (!detail?.detail_table) return [];
    return detail.detail_table.slice(0, 6).map(row => ({
      name: row.agent_operation || `${row.agent}.${row.operation}`,
      latency: (row.avg_latency_ms || 0) / 1000,
      threshold: 5
    }));
  };

  const transformCacheData = (detail) => {
    if (!detail?.detail_table) return [];
    return detail.detail_table.slice(0, 6).map(row => ({
      name: row.agent_operation || `${row.agent}.${row.operation}`,
      cacheMisses: row.total_calls || 0,
      potential: row.duplicate_count || Math.floor((row.total_calls || 0) * (row.redundancy_pct || 0))
    }));
  };

  const transformTokenData = (detail) => {
    if (!detail?.detail_table) return [];
    return detail.detail_table.slice(0, 6).map(row => ({
      name: row.agent_operation || `${row.agent}.${row.operation}`,
      prompt: row.avg_prompt_tokens || 0,
      completion: row.avg_completion_tokens || 0
    }));
  };

  const transformRoutingData = (detail) => {
    if (!detail?.detail_table) return [];
    return detail.detail_table.map(row => ({
      name: row.agent_operation || `${row.agent}.${row.operation}`,
      complexity: row.avg_complexity || 0,
      calls: row.call_count || 0,
      fill: (row.avg_complexity || 0) >= 0.7 ? '#ef4444' : (row.avg_complexity || 0) >= 0.5 ? '#eab308' : '#22c55e'
    }));
  };

  const transformSystemPromptData = (detail) => {
    if (!detail?.detail_table) return [];
    return detail.detail_table.slice(0, 6).map(row => ({
      name: row.agent_operation || `${row.agent}.${row.operation}`,
      system: row.avg_system_tokens || 0,
      user: row.avg_user_tokens || 0,
      context: row.avg_context_tokens || 0
    }));
  };

  const transformCostData = (detail) => {
    if (!detail?.detail_table) return [];
    const totalCost = detail.detail_table.reduce((sum, row) => sum + (row.total_cost || 0), 0);
    return detail.detail_table.slice(0, 6).map(row => ({
      name: row.agent_operation || `${row.agent}.${row.operation}`,
      cost: row.total_cost || 0,
      pct: totalCost > 0 ? ((row.total_cost || 0) / totalCost * 100).toFixed(1) : 0
    }));
  };

  const stories = [
    { id: 1, key: 'latency', title: "Latency Monster", icon: "🐌" },
    { id: 2, key: 'cache', title: "Zero Cache Hits", icon: "💾" },
    { id: 3, key: 'routing', title: "Model Routing", icon: "🔀" },
    { id: 4, key: 'quality', title: "Quality Issues", icon: "❌" },
    { id: 5, key: 'token_imbalance', title: "Token Imbalance", icon: "⚖️" },
    { id: 6, key: 'system_prompt', title: "System Prompt Waste", icon: "📝" },
    { id: 7, key: 'cost', title: "Cost Deep Dive", icon: "💰" },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin text-4xl mb-4">🔭</div>
          <p className="text-gray-400">Loading Observatory data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 text-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4">❌</div>
          <p className="text-red-400 mb-2">Failed to load data</p>
          <p className="text-gray-500 text-sm">{error}</p>
          <p className="text-gray-600 text-xs mt-2">API: {API_BASE_URL}</p>
          <button 
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-500"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const meta = storiesData?.meta || {};
  const health = storiesData?.health || {};
  const currentStoryKey = stories[activeStory - 1]?.key;
  const currentStory = getStory(currentStoryKey);
  const currentDetail = getDetail(currentStoryKey);

  // Top Offender Component
  const TopOffender = ({ story }) => {
    if (!story?.top_offender) return null;
    return (
      <div className="bg-gray-800 rounded-lg p-4 mt-6">
        <h3 className="font-semibold text-gray-300 mb-2">🎯 Top Offender</h3>
        <div className="font-mono text-blue-400 mb-2">
          {story.top_offender.agent_operation || `${story.top_offender.agent}.${story.top_offender.operation}`}
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          {Object.entries(story.top_offender)
            .filter(([k]) => !['agent', 'operation', 'agent_operation', 'calls', 'duplicate_groups'].includes(k))
            .slice(0, 4)
            .map(([key, value]) => (
              <div key={key}>
                <span className="text-gray-500">{key.replace(/_/g, ' ')}: </span>
                <span className="text-gray-200">
                  {typeof value === 'number' ? 
                    (Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2)) 
                    : String(value)}
                </span>
              </div>
            ))
          }
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold mb-2 text-white">AI Agent Observatory - Data Stories</h1>
            <p className="text-gray-400">
              {meta.calls_analyzed?.toLocaleString() || 0} LLM calls • {health.total_count || 0} checks • Last {meta.days || 7} days
            </p>
          </div>
          
          <div className="flex gap-4">
            <select 
              value={selectedProject || ''}
              onChange={(e) => setSelectedProject(e.target.value || null)}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
            >
              <option value="">All Projects</option>
              {projects.map(p => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            <select 
              value={timeRange}
              onChange={(e) => setTimeRange(Number(e.target.value))}
              className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
            >
              <option value={1}>24 hours</option>
              <option value={7}>7 days</option>
              <option value={30}>30 days</option>
            </select>
          </div>
        </div>

        {/* Story Navigation - Reference Style */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-8">
          {stories.map(story => (
            <button
              key={story.id}
              onClick={() => setActiveStory(story.id)}
              className={`p-3 rounded-lg text-left transition-all ${
                activeStory === story.id 
                  ? 'bg-blue-600 border-blue-400 border-2' 
                  : 'bg-gray-800 border-gray-700 border hover:bg-gray-700'
              }`}
            >
              <div className="font-semibold text-sm flex items-center gap-2">
                <span>{story.icon}</span>
                <span>Story {story.id}</span>
              </div>
              <div className="text-xs text-gray-300 mt-1">{story.title}</div>
            </button>
          ))}
        </div>

        {/* Story Content */}
        <div className="space-y-6">
          {/* Story 1: Latency Monster */}
          {activeStory === 1 && currentStory && (
            <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
              <h2 className="text-xl font-bold mb-1 flex items-center gap-2">
                <span className="text-2xl">🐌</span> Story 1: The Latency Monster
              </h2>
              <p className="text-gray-400 mb-4">Columns: <code className="bg-gray-800 px-2 py-1 rounded text-sm">latency_ms</code>, <code className="bg-gray-800 px-2 py-1 rounded text-sm">completion_tokens</code>, <code className="bg-gray-800 px-2 py-1 rounded text-sm">total_cost</code></p>
              
              {/* Table */}
              {currentDetail?.detail_table && (
                <div className="overflow-x-auto mb-6">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left py-2 px-3">Flag</th>
                        <th className="text-left py-2 px-3">Operation</th>
                        <th className="text-right py-2 px-3">Calls</th>
                        <th className="text-right py-2 px-3">Avg Latency</th>
                        <th className="text-right py-2 px-3">Max Latency</th>
                        <th className="text-right py-2 px-3">Avg Completion</th>
                        <th className="text-right py-2 px-3">Total Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {currentDetail.detail_table.slice(0, 8).map((row, i) => {
                        const avgLatency = (row.avg_latency_ms || 0) / 1000;
                        const flag = avgLatency > 10 ? '🔴' : avgLatency > 5 ? '🟡' : '🟢';
                        return (
                          <tr key={i} className="border-b border-gray-800 hover:bg-gray-800">
                            <td className="py-2 px-3">{flag}</td>
                            <td className="py-2 px-3 font-mono text-blue-400">{row.agent_operation || `${row.agent}.${row.operation}`}</td>
                            <td className="py-2 px-3 text-right">{row.call_count || row.total_calls || 0}</td>
                            <td className="py-2 px-3 text-right font-semibold" style={{color: avgLatency > 10 ? '#ef4444' : avgLatency > 5 ? '#eab308' : '#22c55e'}}>{avgLatency.toFixed(1)}s</td>
                            <td className="py-2 px-3 text-right">{((row.max_latency_ms || 0) / 1000).toFixed(1)}s</td>
                            <td className="py-2 px-3 text-right">{row.avg_completion_tokens || 0}</td>
                            <td className="py-2 px-3 text-right font-semibold">${(row.total_cost || 0).toFixed(2)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Chart */}
              <div className="h-72 mb-6">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={transformLatencyData(currentDetail)} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis type="number" stroke="#9ca3af" unit="s" />
                    <YAxis dataKey="name" type="category" stroke="#9ca3af" width={120} tick={{fontSize: 11}} />
                    <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }} />
                    <Bar dataKey="latency" fill="#3b82f6" name="Avg Latency (s)" />
                    <Line dataKey="threshold" stroke="#ef4444" strokeWidth={2} strokeDasharray="5 5" name="5s Threshold" dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              {/* Action */}
              <div className="p-4 bg-red-950 border border-red-800 rounded-lg">
                <h3 className="font-semibold text-red-400 mb-2">🎯 Action Required</h3>
                <p className="text-sm text-gray-300">Constrain <code className="bg-gray-800 px-1 rounded">{currentStory.top_offender?.agent_operation || 'high-latency operation'}</code> output to structured JSON format. Expected: 75% latency reduction, 80% fewer completion tokens.</p>
              </div>

              <TopOffender story={currentStory} />
            </div>
          )}

          {/* Story 2: Zero Cache Hits */}
          {activeStory === 2 && currentStory && (
            <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
              <h2 className="text-xl font-bold mb-1 flex items-center gap-2">
                <span className="text-2xl">💾</span> Story 2: Zero Cache Hits
              </h2>
              <p className="text-gray-400 mb-4">Columns: <code className="bg-gray-800 px-2 py-1 rounded text-sm">cache_metadata.cache_hit</code>, <code className="bg-gray-800 px-2 py-1 rounded text-sm">prompt</code> (uniqueness)</p>
              
              {/* KPI Cards */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-red-500">{currentDetail?.cache_hits || 0}</div>
                  <div className="text-sm text-gray-400">Cache Hits</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-yellow-500">{currentDetail?.cache_misses || currentDetail?.total_calls || 0}</div>
                  <div className="text-sm text-gray-400">Cache Misses</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-green-500">~${(currentDetail?.potential_savings || 0).toFixed(2)}</div>
                  <div className="text-sm text-gray-400">Potential Savings</div>
                </div>
              </div>

              {/* Table */}
              {currentDetail?.detail_table && (
                <div className="overflow-x-auto mb-6">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left py-2 px-3">Operation</th>
                        <th className="text-right py-2 px-3">Total Calls</th>
                        <th className="text-right py-2 px-3">Unique Prompts</th>
                        <th className="text-right py-2 px-3">Redundant Calls</th>
                        <th className="text-right py-2 px-3">Redundancy %</th>
                        <th className="text-right py-2 px-3">Potential Savings</th>
                      </tr>
                    </thead>
                    <tbody>
                      {currentDetail.detail_table.slice(0, 8).map((row, i) => (
                        <tr key={i} className="border-b border-gray-800 hover:bg-gray-800">
                          <td className="py-2 px-3 font-mono text-blue-400">{row.agent_operation || `${row.agent}.${row.operation}`}</td>
                          <td className="py-2 px-3 text-right">{row.total_calls || 0}</td>
                          <td className="py-2 px-3 text-right">{row.unique_prompts || 0}</td>
                          <td className="py-2 px-3 text-right font-semibold text-red-400">{row.duplicate_count || 0}</td>
                          <td className="py-2 px-3 text-right" style={{color: (row.redundancy_pct || 0) > 40 ? '#ef4444' : '#eab308'}}>{((row.redundancy_pct || 0) * 100).toFixed(0)}%</td>
                          <td className="py-2 px-3 text-right text-green-400">${(row.potential_savings || 0).toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Chart */}
              <div className="h-64 mb-6">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={transformCacheData(currentDetail)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="name" stroke="#9ca3af" tick={{fontSize: 10}} />
                    <YAxis stroke="#9ca3af" />
                    <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }} />
                    <Legend />
                    <Bar dataKey="cacheMisses" fill="#ef4444" name="Cache Misses (Current)" />
                    <Bar dataKey="potential" fill="#22c55e" name="Could Be Cached" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Action */}
              <div className="p-4 bg-yellow-950 border border-yellow-800 rounded-lg">
                <h3 className="font-semibold text-yellow-400 mb-2">🎯 Action Required</h3>
                <p className="text-sm text-gray-300">Implement semantic caching in <code className="bg-gray-800 px-1 rounded">CacheManager</code>. {currentStory.top_offender?.agent_operation || 'Top operation'} alone has high redundancy - many calls could be cached.</p>
              </div>

              <TopOffender story={currentStory} />
            </div>
          )}

          {/* Story 3: Model Routing */}
          {activeStory === 3 && currentStory && (
            <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
              <h2 className="text-xl font-bold mb-1 flex items-center gap-2">
                <span className="text-2xl">🔀</span> Story 3: Model Routing Not Utilized
              </h2>
              <p className="text-gray-400 mb-4">Columns: <code className="bg-gray-800 px-2 py-1 rounded text-sm">routing_decision.complexity_score</code>, <code className="bg-gray-800 px-2 py-1 rounded text-sm">model_name</code></p>
              
              {/* KPI Cards */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-red-500">{currentDetail?.misrouted_count || 0}</div>
                  <div className="text-sm text-gray-400">Misrouted Calls</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-yellow-500">{currentDetail?.high_complexity_count || 0}</div>
                  <div className="text-sm text-gray-400">High-Complexity Calls (≥0.7)</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-blue-500">{currentDetail?.operations_affected || currentStory?.red_flag_count || 0}</div>
                  <div className="text-sm text-gray-400">Operations Affected</div>
                </div>
              </div>

              {/* Table */}
              {currentDetail?.detail_table && (
                <div className="overflow-x-auto mb-6">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left py-2 px-3">Operation</th>
                        <th className="text-right py-2 px-3">Complexity</th>
                        <th className="text-right py-2 px-3">Calls</th>
                        <th className="text-left py-2 px-3">Current Model</th>
                        <th className="text-left py-2 px-3">Recommended</th>
                        <th className="text-center py-2 px-3">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {currentDetail.detail_table.slice(0, 8).map((row, i) => {
                        const complexity = row.avg_complexity || 0;
                        const needsUpgrade = complexity >= 0.7;
                        return (
                          <tr key={i} className="border-b border-gray-800 hover:bg-gray-800">
                            <td className="py-2 px-3 font-mono text-blue-400">{row.agent_operation || `${row.agent}.${row.operation}`}</td>
                            <td className="py-2 px-3 text-right">
                              <span className={`px-2 py-1 rounded text-xs font-semibold ${
                                complexity >= 0.7 ? 'bg-red-900 text-red-300' : 
                                complexity >= 0.5 ? 'bg-yellow-900 text-yellow-300' : 
                                'bg-green-900 text-green-300'
                              }`}>{complexity.toFixed(2)}</span>
                            </td>
                            <td className="py-2 px-3 text-right">{row.call_count || 0}</td>
                            <td className="py-2 px-3 font-mono text-gray-400">{row.model_name || 'gpt-4o-mini'}</td>
                            <td className="py-2 px-3 font-mono">{needsUpgrade ? 'gpt-4o ⬆️' : 'gpt-4o-mini ✓'}</td>
                            <td className="py-2 px-3 text-center">
                              <span className={`px-2 py-1 rounded text-xs ${needsUpgrade ? 'bg-blue-900 text-blue-300' : 'bg-gray-700 text-gray-300'}`}>
                                {needsUpgrade ? 'Upgrade' : 'Keep'}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Chart */}
              <div className="h-64 mb-6">
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="complexity" name="Complexity" stroke="#9ca3af" domain={[0, 1]} />
                    <YAxis dataKey="calls" name="Calls" stroke="#9ca3af" />
                    <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }} cursor={{ strokeDasharray: '3 3' }} />
                    <Scatter data={transformRoutingData(currentDetail)} fill="#3b82f6">
                      {transformRoutingData(currentDetail).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
              </div>

              {/* Action */}
              <div className="p-4 bg-blue-950 border border-blue-800 rounded-lg">
                <h3 className="font-semibold text-blue-400 mb-2">🎯 Action Required</h3>
                <p className="text-sm text-gray-300">Implement <code className="bg-gray-800 px-1 rounded">ModelRouter</code> to upgrade high-complexity operations (≥0.7) to gpt-4o for better quality.</p>
              </div>

              <TopOffender story={currentStory} />
            </div>
          )}

          {/* Story 4: Quality Issues */}
          {activeStory === 4 && currentStory && (
            <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
              <h2 className="text-xl font-bold mb-1 flex items-center gap-2">
                <span className="text-2xl">❌</span> Story 4: Quality Issues
              </h2>
              <p className="text-gray-400 mb-4">Columns: <code className="bg-gray-800 px-2 py-1 rounded text-sm">success</code>, <code className="bg-gray-800 px-2 py-1 rounded text-sm">error</code>, <code className="bg-gray-800 px-2 py-1 rounded text-sm">agent_name</code></p>
              
              {/* KPI Cards */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-red-500">{currentDetail?.error_count || 0}</div>
                  <div className="text-sm text-gray-400">Failed Calls</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-yellow-500">{currentDetail?.operations_affected || currentStory?.red_flag_count || 0}</div>
                  <div className="text-sm text-gray-400">Operations Affected</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-green-500">{((currentDetail?.success_rate || 0) * 100).toFixed(0)}%</div>
                  <div className="text-sm text-gray-400">Success Rate</div>
                </div>
              </div>

              {/* Chart */}
              <div className="grid grid-cols-2 gap-6 mb-6">
                <div className="h-48">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={[
                          { name: 'Success', value: currentDetail?.success_count || 0, color: '#22c55e' },
                          { name: 'Failed', value: currentDetail?.error_count || 0, color: '#ef4444' },
                        ].filter(d => d.value > 0)}
                        cx="50%"
                        cy="50%"
                        innerRadius={40}
                        outerRadius={70}
                        paddingAngle={2}
                        dataKey="value"
                        label={({name, value}) => `${name}: ${value}`}
                      >
                        {[
                          { name: 'Success', value: currentDetail?.success_count || 0, color: '#22c55e' },
                          { name: 'Failed', value: currentDetail?.error_count || 0, color: '#ef4444' },
                        ].filter(d => d.value > 0).map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex flex-col justify-center">
                  <div className="text-4xl font-bold text-green-500 mb-1">{((currentDetail?.success_rate || 0) * 100).toFixed(0)}%</div>
                  <div className="text-gray-400">Success Rate</div>
                  <div className="text-sm text-gray-500 mt-2">{currentDetail?.success_count || 0} successful / {currentDetail?.error_count || 0} failed</div>
                </div>
              </div>

              {/* Table */}
              {currentDetail?.detail_table && (
                <div className="overflow-x-auto mb-6">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left py-2 px-3">Agent</th>
                        <th className="text-left py-2 px-3">Operation</th>
                        <th className="text-left py-2 px-3">Error Message</th>
                        <th className="text-left py-2 px-3">Type</th>
                        <th className="text-left py-2 px-3">Fix</th>
                      </tr>
                    </thead>
                    <tbody>
                      {currentDetail.detail_table.slice(0, 8).map((row, i) => (
                        <tr key={i} className="border-b border-gray-800 hover:bg-gray-800">
                          <td className="py-2 px-3 font-mono text-purple-400">{row.agent || row.agent_name}</td>
                          <td className="py-2 px-3 font-mono text-blue-400">{row.operation}</td>
                          <td className="py-2 px-3 text-red-400 text-xs">{row.error || row.error_message || '—'}</td>
                          <td className="py-2 px-3">
                            <span className={`px-2 py-1 rounded text-xs ${
                              row.error_type === 'Code Bug' ? 'bg-red-900 text-red-300' : 'bg-yellow-900 text-yellow-300'
                            }`}>{row.error_type || 'Error'}</span>
                          </td>
                          <td className="py-2 px-3 text-green-400 text-xs">{row.fix || row.suggested_fix || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Action */}
              <div className="p-4 bg-red-950 border border-red-800 rounded-lg">
                <h3 className="font-semibold text-red-400 mb-2">🎯 Action Required</h3>
                <p className="text-sm text-gray-300">Fix variable scope bugs and add input validation before LLM calls to prevent errors.</p>
              </div>

              <TopOffender story={currentStory} />
            </div>
          )}

          {/* Story 5: Token Imbalance */}
          {activeStory === 5 && currentStory && (
            <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
              <h2 className="text-xl font-bold mb-1 flex items-center gap-2">
                <span className="text-2xl">⚖️</span> Story 5: Token Imbalance
              </h2>
              <p className="text-gray-400 mb-4">Columns: <code className="bg-gray-800 px-2 py-1 rounded text-sm">prompt_tokens</code>, <code className="bg-gray-800 px-2 py-1 rounded text-sm">completion_tokens</code></p>
              
              {/* KPI Cards */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-red-500">{currentDetail?.worst_ratio || currentStory?.summary_metric || '—'}</div>
                  <div className="text-sm text-gray-400">Worst Ratio (P:C)</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-yellow-500">{currentDetail?.imbalanced_count || currentStory?.red_flag_count || 0}</div>
                  <div className="text-sm text-gray-400">Operations Affected</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-blue-500">{currentDetail?.avg_ratio || '—'}</div>
                  <div className="text-sm text-gray-400">Avg Ratio</div>
                </div>
              </div>

              {/* Table */}
              {currentDetail?.detail_table && (
                <div className="overflow-x-auto mb-6">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left py-2 px-3">Flag</th>
                        <th className="text-left py-2 px-3">Operation</th>
                        <th className="text-right py-2 px-3">Avg Prompt Tokens</th>
                        <th className="text-right py-2 px-3">Avg Completion Tokens</th>
                        <th className="text-right py-2 px-3">Ratio (P:C)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {currentDetail.detail_table.slice(0, 8).map((row, i) => {
                        const ratio = row.ratio || (row.avg_prompt_tokens / (row.avg_completion_tokens || 1));
                        const flag = ratio > 20 ? '🔴' : ratio > 10 ? '🟡' : '🟢';
                        return (
                          <tr key={i} className="border-b border-gray-800 hover:bg-gray-800">
                            <td className="py-2 px-3">{flag}</td>
                            <td className="py-2 px-3 font-mono text-blue-400">{row.agent_operation || `${row.agent}.${row.operation}`}</td>
                            <td className="py-2 px-3 text-right">{(row.avg_prompt_tokens || 0).toLocaleString()}</td>
                            <td className="py-2 px-3 text-right">{(row.avg_completion_tokens || 0).toLocaleString()}</td>
                            <td className="py-2 px-3 text-right font-semibold" style={{color: ratio > 20 ? '#ef4444' : ratio > 10 ? '#eab308' : '#22c55e'}}>{ratio.toFixed(1)}:1</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Chart */}
              <div className="h-64 mb-6">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={transformTokenData(currentDetail)} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis type="number" stroke="#9ca3af" />
                    <YAxis dataKey="name" type="category" stroke="#9ca3af" width={120} tick={{fontSize: 11}} />
                    <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }} />
                    <Legend />
                    <Bar dataKey="prompt" fill="#f97316" name="Prompt Tokens" />
                    <Bar dataKey="completion" fill="#22c55e" name="Completion Tokens" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Action */}
              <div className="p-4 bg-orange-950 border border-orange-800 rounded-lg">
                <h3 className="font-semibold text-orange-400 mb-2">🎯 Action Required</h3>
                <p className="text-sm text-gray-300">Add conversation summarization to cap history tokens. High prompt:completion ratios indicate wasted input tokens.</p>
              </div>

              <TopOffender story={currentStory} />
            </div>
          )}

          {/* Story 6: System Prompt Waste */}
          {activeStory === 6 && currentStory && (
            <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
              <h2 className="text-xl font-bold mb-1 flex items-center gap-2">
                <span className="text-2xl">📝</span> Story 6: System Prompt Redundancy
              </h2>
              <p className="text-gray-400 mb-4">Columns: <code className="bg-gray-800 px-2 py-1 rounded text-sm">prompt_breakdown.system_prompt_tokens</code>, <code className="bg-gray-800 px-2 py-1 rounded text-sm">prompt_breakdown.user_message_tokens</code></p>
              
              {/* KPI Cards */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-red-500">{currentDetail?.total_system_tokens?.toLocaleString() || '—'}</div>
                  <div className="text-sm text-gray-400">Total System Tokens Sent</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-yellow-500">{currentDetail?.largest_system_prompt?.toLocaleString() || '—'}</div>
                  <div className="text-sm text-gray-400">Largest System Prompt</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-green-500">~90%</div>
                  <div className="text-sm text-gray-400">Cacheable with Prefix Caching</div>
                </div>
              </div>

              {/* Table */}
              {currentDetail?.detail_table && (
                <div className="overflow-x-auto mb-6">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left py-2 px-3">Operation</th>
                        <th className="text-right py-2 px-3">System Tokens</th>
                        <th className="text-right py-2 px-3">User Tokens</th>
                        <th className="text-right py-2 px-3">Context Tokens</th>
                        <th className="text-right py-2 px-3">System %</th>
                        <th className="text-right py-2 px-3">Calls</th>
                        <th className="text-right py-2 px-3">Total Sys Sent</th>
                      </tr>
                    </thead>
                    <tbody>
                      {currentDetail.detail_table.slice(0, 8).map((row, i) => {
                        const systemPct = row.system_pct || (row.avg_system_tokens / (row.avg_system_tokens + row.avg_user_tokens + (row.avg_context_tokens || 0)) * 100);
                        return (
                          <tr key={i} className="border-b border-gray-800 hover:bg-gray-800">
                            <td className="py-2 px-3 font-mono text-blue-400">{row.agent_operation || `${row.agent}.${row.operation}`}</td>
                            <td className="py-2 px-3 text-right font-semibold" style={{color: (row.avg_system_tokens || 0) > 500 ? '#ef4444' : '#22c55e'}}>{(row.avg_system_tokens || 0).toLocaleString()}</td>
                            <td className="py-2 px-3 text-right">{(row.avg_user_tokens || 0).toLocaleString()}</td>
                            <td className="py-2 px-3 text-right text-gray-500">{(row.avg_context_tokens || 0).toLocaleString()}</td>
                            <td className="py-2 px-3 text-right" style={{color: systemPct > 40 ? '#ef4444' : systemPct > 25 ? '#eab308' : '#22c55e'}}>{systemPct.toFixed(1)}%</td>
                            <td className="py-2 px-3 text-right">{row.call_count || row.total_calls || 0}</td>
                            <td className="py-2 px-3 text-right text-red-400 font-semibold">{(row.total_system_sent || (row.avg_system_tokens * (row.call_count || 1))).toLocaleString()}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Chart */}
              <div className="h-64 mb-6">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={transformSystemPromptData(currentDetail)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="name" stroke="#9ca3af" tick={{fontSize: 10}} />
                    <YAxis stroke="#9ca3af" />
                    <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }} />
                    <Legend />
                    <Bar dataKey="system" stackId="a" fill="#ef4444" name="System Prompt" />
                    <Bar dataKey="user" stackId="a" fill="#22c55e" name="User Message" />
                    <Bar dataKey="context" stackId="a" fill="#3b82f6" name="Context/History" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Action */}
              <div className="p-4 bg-purple-950 border border-purple-800 rounded-lg">
                <h3 className="font-semibold text-purple-400 mb-2">🎯 Action Required</h3>
                <p className="text-sm text-gray-300">1. Enable Azure OpenAI prompt caching (automatic for &gt;1024 token prefixes). 2. Trim large system prompts. 3. Add conversation summarization.</p>
              </div>

              <TopOffender story={currentStory} />
            </div>
          )}

          {/* Story 7: Cost Deep Dive */}
          {activeStory === 7 && currentStory && (
            <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
              <h2 className="text-xl font-bold mb-1 flex items-center gap-2">
                <span className="text-2xl">💰</span> Story 7: Cost Deep Dive
              </h2>
              <p className="text-gray-400 mb-4">Columns: <code className="bg-gray-800 px-2 py-1 rounded text-sm">total_cost</code>, <code className="bg-gray-800 px-2 py-1 rounded text-sm">prompt_tokens</code>, <code className="bg-gray-800 px-2 py-1 rounded text-sm">completion_tokens</code>, <code className="bg-gray-800 px-2 py-1 rounded text-sm">agent_name</code></p>
              
              {/* KPI Cards */}
              <div className="grid grid-cols-4 gap-4 mb-6">
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-yellow-500">${(currentDetail?.total_cost || 0).toFixed(2)}</div>
                  <div className="text-sm text-gray-400">Total Cost</div>
                  <div className="text-xs text-gray-500">Last {timeRange} days</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-blue-500">{currentDetail?.total_calls || 0}</div>
                  <div className="text-sm text-gray-400">Total Calls</div>
                  <div className="text-xs text-gray-500">LLM invocations</div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-purple-500">${(currentDetail?.avg_cost_per_call || 0).toFixed(3)}</div>
                  <div className="text-sm text-gray-400">Avg Cost/Call</div>
                  <div className="text-xs text-gray-500">Per invocation</div>
                </div>
                <div className="bg-green-900/30 border border-green-800 rounded-lg p-4 text-center">
                  <div className="text-3xl font-bold text-green-400">-${(currentDetail?.potential_savings || 0).toFixed(2)}</div>
                  <div className="text-sm text-green-400">Potential Savings</div>
                  <div className="text-xs text-green-500">Per week</div>
                </div>
              </div>

              {/* Main Insight Banner */}
              <div className="bg-gradient-to-r from-yellow-950 to-orange-950 border border-yellow-800 rounded-lg p-4 mb-6">
                <div className="flex items-start gap-3">
                  <span className="text-2xl">📊</span>
                  <div>
                    <h3 className="font-semibold text-yellow-400 mb-1">72% of cost concentrated in top 3 operations</h3>
                    <p className="text-sm text-gray-300">
                      Focus optimization efforts on the highest-cost operations for maximum impact.
                    </p>
                  </div>
                </div>
              </div>

              {/* Cost by Operation Table */}
              {currentDetail?.detail_table && (
                <div className="overflow-x-auto mb-6">
                  <h3 className="text-lg font-semibold mb-3 text-gray-300">Cost by Operation</h3>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left py-2 px-3">Operation</th>
                        <th className="text-left py-2 px-3">Agent</th>
                        <th className="text-right py-2 px-3">Total Cost</th>
                        <th className="text-right py-2 px-3">% of Total</th>
                        <th className="text-right py-2 px-3">Calls</th>
                        <th className="text-right py-2 px-3">Avg Cost</th>
                        <th className="text-right py-2 px-3">Prompt Tokens</th>
                        <th className="text-right py-2 px-3">Completion Tokens</th>
                      </tr>
                    </thead>
                    <tbody>
                      {currentDetail.detail_table.slice(0, 8).map((row, i) => {
                        const pct = currentDetail.total_cost > 0 ? ((row.total_cost || 0) / currentDetail.total_cost * 100) : 0;
                        return (
                          <tr key={i} className="border-b border-gray-800 hover:bg-gray-800">
                            <td className="py-2 px-3 font-mono text-blue-400">{row.operation || row.agent_operation}</td>
                            <td className="py-2 px-3 text-purple-400">{row.agent || row.agent_name}</td>
                            <td className="py-2 px-3 text-right font-semibold text-yellow-400">${(row.total_cost || 0).toFixed(2)}</td>
                            <td className="py-2 px-3 text-right">
                              <div className="flex items-center justify-end gap-2">
                                <div className="w-16 bg-gray-700 rounded-full h-2">
                                  <div className="bg-yellow-500 h-2 rounded-full" style={{width: `${pct}%`}} />
                                </div>
                                <span className="w-12 text-right">{pct.toFixed(1)}%</span>
                              </div>
                            </td>
                            <td className="py-2 px-3 text-right">{row.call_count || row.total_calls || 0}</td>
                            <td className="py-2 px-3 text-right">${(row.avg_cost || 0).toFixed(3)}</td>
                            <td className="py-2 px-3 text-right text-orange-400">{(row.total_prompt_tokens || 0).toLocaleString()}</td>
                            <td className="py-2 px-3 text-right text-green-400">{(row.total_completion_tokens || 0).toLocaleString()}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Charts Row */}
              <div className="grid grid-cols-2 gap-6 mb-6">
                <div className="bg-gray-800 rounded-lg p-4">
                  <h3 className="text-sm font-semibold mb-3 text-gray-300">Cost Distribution</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={transformCostData(currentDetail)}
                          cx="50%"
                          cy="50%"
                          innerRadius={50}
                          outerRadius={80}
                          dataKey="cost"
                          label={({name, pct}) => `${name?.substring(0, 10)}... ${pct}%`}
                          labelLine={false}
                        >
                          {transformCostData(currentDetail).map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }} 
                          formatter={(value) => `$${value.toFixed(2)}`}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="bg-gray-800 rounded-lg p-4">
                  <h3 className="text-sm font-semibold mb-3 text-gray-300">Cost by Operation</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={transformCostData(currentDetail)} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis type="number" stroke="#9ca3af" tickFormatter={(v) => `$${v}`} />
                        <YAxis dataKey="name" type="category" stroke="#9ca3af" width={110} tick={{fontSize: 11}} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }} 
                          formatter={(value) => `$${value.toFixed(2)}`}
                        />
                        <Bar dataKey="cost" fill="#eab308" name="Cost" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              {/* Savings Opportunities */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-3 text-gray-300 flex items-center gap-2">
                  <span className="text-green-400">💡</span> Savings Opportunities
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { strategy: 'Semantic Caching', target: 'quick_score_job', savings: 0.67, effort: 'Medium', impact: 'High' },
                    { strategy: 'Prompt Compression', target: 'streamlit_chat', savings: 0.50, effort: 'Low', impact: 'Medium' },
                    { strategy: 'Output Constraints', target: 'deep_analyze_job', savings: 0.42, effort: 'Low', impact: 'High' },
                    { strategy: 'Model Routing', target: 'generate_sql', savings: 0.15, effort: 'Medium', impact: 'Low' },
                  ].map((opp, i) => (
                    <div key={i} className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-green-700 transition-colors">
                      <div className="flex justify-between items-start mb-2">
                        <h4 className="font-semibold text-gray-200">{opp.strategy}</h4>
                        <span className={`px-2 py-1 rounded text-xs ${
                          opp.impact === 'High' ? 'bg-green-900 text-green-300' : 
                          opp.impact === 'Medium' ? 'bg-yellow-900 text-yellow-300' : 
                          'bg-gray-700 text-gray-300'
                        }`}>{opp.impact} Impact</span>
                      </div>
                      <p className="text-sm text-gray-400 mb-2">Target: <code className="bg-gray-700 px-1 rounded">{opp.target}</code></p>
                      <div className="flex justify-between items-center">
                        <span className="text-xl font-bold text-green-400">-${opp.savings.toFixed(2)}</span>
                        <span className="text-xs text-gray-500">{opp.effort} effort</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Top 3 Actions */}
              <div className="p-4 bg-yellow-950 border border-yellow-800 rounded-lg">
                <h3 className="font-semibold text-yellow-400 mb-2">🎯 Top 3 Actions for Cost Reduction</h3>
                <ol className="text-sm text-gray-300 space-y-2">
                  <li>1. <strong>Enable semantic caching</strong> for <code className="bg-gray-800 px-1 rounded">quick_score_job</code> - high redundancy = significant savings</li>
                  <li>2. <strong>Compress prompts</strong> in <code className="bg-gray-800 px-1 rounded">streamlit_chat</code> - large system prompt can be reduced by 60%</li>
                  <li>3. <strong>Constrain output</strong> in <code className="bg-gray-800 px-1 rounded">deep_analyze_job</code> - high completion tokens is excessive</li>
                </ol>
              </div>
            </div>
          )}

          {/* No data state */}
          {!currentStory && (
            <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
              <div className="text-center py-12 text-gray-500">
                <p>No data available for this story</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}