/**
 * App - Main Application Component
 * 
 * Sets up routing for the Observatory dashboard and all story pages.
 * Includes Header with filters and Footer.
 * Provides TimeRangeContext for global date filtering.
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { BASE_THEME } from './utils/themeUtils';

// Context
import TimeRangeContext from './context/TimeRangeContext';

// Layout
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import ScrollToTop from './components/common/ScrollToTop';

// Pages - Dashboard
import Dashboard from './pages/Dashboard';

// Pages - Optimization Queue (cross-story fix dashboard)
import OptimizationQueue from './pages/OptimizationQueue';

// Pages - Latency Story (Layers 1, 2, 3)
import Latency from './pages/stories/latency';
import LatencyOperationDetail from './pages/stories/latency/OperationDetail';
import LatencyCallDetail from './pages/stories/latency/CallDetail';

// Pages - Cache Story (Layers 1, 2, 3)
import Cache from './pages/stories/cache';
import CacheOperationDetail from './pages/stories/cache/OperationDetail';
import CachePatternDetail from './pages/stories/cache/PatternDetail';

// Pages - Routing Story (Layers 1, 2, 3)
import Routing from './pages/stories/routing';
import RoutingOperationDetail from './pages/stories/routing/OperationDetail';
import RoutingCallDetail from './pages/stories/routing/CallDetail';

// Pages - Quality Story (Layers 1, 2, 3)
import Quality from './pages/stories/quality';
import QualityOperationDetail from './pages/stories/quality/OperationDetail';
import QualityCallDetail from './pages/stories/quality/CallDetail';

// Pages - Token Story (Layers 1, 2, 3)
import Token from './pages/stories/token';
import TokenOperationDetail from './pages/stories/token/OperationDetail';
import TokenCallDetail from './pages/stories/token/CallDetail';

// Pages - Prompt Story (Layers 1, 2, 3)
import Prompt from './pages/stories/prompt';
import PromptOperationDetail from './pages/stories/prompt/OperationDetail';
import PromptCallDetail from './pages/stories/prompt/CallDetail';

// Pages - Cost Story (Layers 1, 2, 3)
import Cost from './pages/stories/cost';
import CostOperationDetail from './pages/stories/cost/OperationDetail';
import CostCallDetail from './pages/stories/cost/CallDetail';

// Pages - Optimization Story (Layers 1 & 2)
import Optimization from './pages/stories/optimization';
import OptimizationComparisonDetail from './pages/stories/optimization/ComparisonDetail';
import CodeCentricPage from './pages/stories/optimization/CodeCentricPage';

function App() {
  // Global filter state
  const [selectedProject, setSelectedProject] = useState(null);
  const [timeRange, setTimeRange] = useState(30); // Default: 30 days
  const [projects, setProjects] = useState([]);

  // Fetch available projects on mount
  useEffect(() => {
    fetch('/api/projects')
      .then(res => {
        if (!res.ok) {
          console.warn('Projects endpoint not available yet');
          return { projects: [] };
        }
        return res.json();
      })
      .then(data => setProjects(data.projects || []))
      .catch(err => {
        console.warn('Failed to load projects:', err);
        setProjects([]);
      });
  }, []);

  return (
    <TimeRangeContext.Provider value={{ timeRange, setTimeRange }}>
      <BrowserRouter>
        <ScrollToTop />
        <div className={`min-h-screen ${BASE_THEME.container.primary} flex flex-col`}>
          
          {/* Header - Sticky navigation with filters */}
          <Header 
            selectedProject={selectedProject}
            onProjectChange={setSelectedProject}
            timeRange={timeRange}
            onTimeRangeChange={setTimeRange}
            projects={projects}
          />

          {/* Main Content Area */}
          <main className="flex-1">
            <Routes>
              {/* Dashboard */}
              <Route path="/" element={<Dashboard />} />

              {/* Optimization Queue - Cross-story fix dashboard */}
              <Route path="/optimization" element={<OptimizationQueue />} />
              
              {/* ============================================= */}
              {/* LATENCY STORY - Layers 1, 2, 3                */}
              {/* ============================================= */}
              <Route path="/stories/latency" element={<Latency />} />
              <Route path="/stories/latency/calls" element={<LatencyOperationDetail />} />
              <Route path="/stories/latency/calls/:callId" element={<LatencyCallDetail />} />
              <Route path="/stories/latency/operations/:agent/:operation" element={<LatencyOperationDetail />} />
              
              {/* ============================================= */}
              {/* CACHE STORY - Layers 1, 2, 3                  */}
              {/* Layer 2: All cache patterns with filtering    */}
              {/* Layer 3: Pattern detail + fix                 */}
              {/* ============================================= */}
              <Route path="/stories/cache" element={<Cache />} />
              <Route path="/stories/cache/calls" element={<CacheOperationDetail />} />
              <Route path="/stories/cache/operations/:agent/:operation" element={<CacheOperationDetail />} />
              <Route path="/stories/cache/operations/:agent/:operation/groups/:groupId" element={<CachePatternDetail />} />
              
              {/* ============================================= */}
              {/* ROUTING STORY - Layers 1, 2, 3                */}
              {/* ============================================= */}
              <Route path="/stories/routing" element={<Routing />} />
              <Route path="/stories/routing/calls" element={<RoutingOperationDetail />} />
              <Route path="/stories/routing/calls/:callId" element={<RoutingCallDetail />} />
              <Route path="/stories/routing/operations/:agent/:operation" element={<RoutingOperationDetail />} />
              
              {/* ============================================= */}
              {/* QUALITY STORY - Layers 1, 2, 3                */}
              {/* ============================================= */}
              <Route path="/stories/quality" element={<Quality />} />
              <Route path="/stories/quality/calls" element={<QualityOperationDetail />} />
              <Route path="/stories/quality/calls/:callId" element={<QualityCallDetail />} />
              <Route path="/stories/quality/operations/:agent/:operation" element={<QualityOperationDetail />} />
              
              {/* ============================================= */}
              {/* TOKEN EFFICIENCY STORY - Layers 1, 2, 3       */}
              {/* ============================================= */}
              <Route path="/stories/token_imbalance" element={<Token />} />
              <Route path="/stories/token_imbalance/calls" element={<TokenOperationDetail />} />
              <Route path="/stories/token_imbalance/calls/:callId" element={<TokenCallDetail />} />
              <Route path="/stories/token_imbalance/operations/:agent/:operation" element={<TokenOperationDetail />} />
              
              {/* ============================================= */}
              {/* PROMPT COMPOSITION STORY - Layers 1, 2, 3     */}
              {/* ============================================= */}
              <Route path="/stories/system_prompt" element={<Prompt />} />
              <Route path="/stories/system_prompt/calls" element={<PromptOperationDetail />} />
              <Route path="/stories/system_prompt/calls/:callId" element={<PromptCallDetail />} />
              <Route path="/stories/system_prompt/operations/:agent/:operation" element={<PromptOperationDetail />} />
              
              {/* ============================================= */}
              {/* COST ANALYSIS STORY - Layers 1, 2, 3          */}
              {/* ============================================= */}
              <Route path="/stories/cost" element={<Cost />} />
              <Route path="/stories/cost/calls" element={<CostOperationDetail />} />
              <Route path="/stories/cost/calls/:callId" element={<CostCallDetail />} />
              <Route path="/stories/cost/operations/:agent/:operation" element={<CostOperationDetail />} />
              
              {/* ============================================= */}
              {/* OPTIMIZATION IMPACT STORY - Layers 1 & 2      */}
              {/* ============================================= */}
              <Route path="/stories/optimization" element={<Optimization />} />
              <Route path="/stories/optimization/code-view" element={<CodeCentricPage />} />
              <Route path="/stories/optimization/calls" element={<OptimizationComparisonDetail />} />
              <Route path="/stories/optimization/comparisons/:comparisonId" element={<OptimizationComparisonDetail />} />
              
              {/* Catch-all redirect */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>

          {/* Footer - Bottom navigation and links */}
          <Footer />

        </div>
      </BrowserRouter>
    </TimeRangeContext.Provider>
  );
}

export default App;