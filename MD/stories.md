# AI Agent Observatory - Data Stories Implementation Plan

## 📋 Document Overview

This document outlines the complete implementation plan for transforming the AI Agent Observatory dashboard into a **story-driven optimization experience**. The goal is to make data insights actionable by guiding developers from high-level stories down to specific code changes.

---

## 🎯 The Vision

The AI Agent Observatory should tell **stories** about your AI application's performance, not just display metrics. Each story represents a specific optimization opportunity, and clicking into a story walks the developer through:

1. **What's happening** (the data)
2. **Why it matters** (the impact)
3. **Where to fix it** (the code location)
4. **How to fix it** (the code change)
5. **Did it work?** (measure the impact)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     📊 DATA STORIES (Main Dashboard)                │
│                                                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ 🐌 Story 1  │ │ 💾 Story 2  │ │ 💰 Story 3  │ │ 📝 Story 4  │   │
│  │ Latency     │ │ Zero Cache  │ │ Cost        │ │ System      │   │
│  │ Monster     │ │ Hits        │ │ Breakdown   │ │ Prompt Waste│   │
│  │             │ │             │ │             │ │             │   │
│  │ 16s avg     │ │ 110 misses  │ │ 72% in 3ops │ │ 46K tokens  │   │
│  │ [View →]    │ │ [View →]    │ │ [View →]    │ │ [View →]    │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
│                                                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                   │
│  │ ⚖️ Story 5  │ │ 🔀 Story 6  │ │ ❌ Story 7  │                   │
│  │ Token       │ │ Model       │ │ Quality     │                   │
│  │ Imbalance   │ │ Routing     │ │ Issues      │                   │
│  └─────────────┘ └─────────────┘ └─────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ Click "Story 2: Zero Cache Hits"
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     💾 CACHE ANALYZER                               │
│                     (Pre-filtered to show the problem)              │
│                                                                     │
│  🎯 Filtered: quick_score_job (32 calls, 53% redundant)            │
│                                                                     │
│  [Duplicate groups table]                                           │
│  [Actual prompts]                                                   │
│  [Code change guide]                                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🗺️ The Complete User Journey

```
┌────────────────────────────────────────────────────────────────┐
│                    📊 DATA STORIES                              │
│                    (Main Dashboard)                             │
│                                                                 │
│  "Here's what your data is telling you"                        │
└────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
     ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
     │ 💾 Cache    │   │ 🔀 Router   │   │ ✨ Prompt   │
     │ Analyzer    │   │             │   │ Optimizer   │
     │             │   │             │   │             │
     │ "Here's the │   │ "Here's the │   │ "Here's the │
     │  problem"   │   │  problem"   │   │  problem"   │
     │             │   │             │   │             │
     │ "Here's the │   │ "Here's the │   │ "Here's the │
     │  code fix"  │   │  code fix"  │   │  code fix"  │
     └─────────────┘   └─────────────┘   └─────────────┘
            │                 │                 │
            └─────────────────┼─────────────────┘
                              ▼
                    ┌─────────────────┐
                    │ 📈 Optimization │
                    │    Impact       │
                    │                 │
                    │ "Did it work?"  │
                    │ Baseline vs     │
                    │ Optimized       │
                    └─────────────────┘
```

---

## 🔄 The Detailed Flow

### Step 1: Story View (Entry Point)

```
┌─────────────────────────────────────────────────────────────────────┐
│  STORY VIEW (New)                                                   │
│  "Story 6: System Prompt Redundancy"                                │
│  - Table showing operations with redundant system prompts           │
│  - Red flags highlighted                                            │
│  - Click streamlit_chat to drill down                               │
└─────────────────────────────────────────────────────────────────────┘
```

**What the user sees:**
- Story title and description
- Key metric (e.g., "46K redundant tokens")
- Table of affected operations
- Red flag indicators
- "View →" button for each operation

### Step 2: Operation Drill-Down

```
┌─────────────────────────────────────────────────────────────────────┐
│  OPERATION DRILL-DOWN (Enhanced)                                    │
│  "streamlit_chat - 12 calls, 1,544 system tokens each"              │
│  - Show actual prompts (grouped by similarity)                      │
│  - Token breakdown visualization                                    │
│  - "These 12 calls sent the same 1,544 token system prompt"         │
└─────────────────────────────────────────────────────────────────────┘
```

**What the user sees:**
- Operation name and call count
- Actual prompt content (the real data)
- Token breakdown visualization
- Clear explanation of the problem

### Step 3: Code Change Guide

```
┌─────────────────────────────────────────────────────────────────────┐
│  CODE CHANGE GUIDE (Enhanced)                                       │
│  📁 File: agents/plugins/ChatPlugin.py                              │
│  🔧 Method: streamlit_chat()                                        │
│  📍 Line: ~45 (where system prompt is defined)                      │
│                                                                     │
│  BEFORE: [Show their actual system prompt - 1,544 tokens]           │
│  AFTER:  [Show compressed version - ~400 tokens]                    │
│                                                                     │
│  Expected: 74% reduction in system prompt tokens                    │
│            ~$0.80/session saved                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**What the user sees:**
- Exact file path to modify
- Method name and approximate line number
- Before/after code comparison
- Expected impact metrics

### Step 4: Measure Success

```
┌─────────────────────────────────────────────────────────────────────┐
│  MEASURE SUCCESS (Existing - Optimization Impact)                   │
│  Run with metadata={'phase': 'optimized'}                           │
│  Compare baseline vs optimized                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**What the user sees:**
- Instructions to run with phase tagging
- Side-by-side comparison of baseline vs optimized
- Actual savings achieved

---

## 📋 Complete Implementation To-Do List

### Phase 1: Foundation & Configuration

#### 1.1 Create Plugin Map Configuration
- [ ] Create `dashboard/config/plugin_map.py` with mapping of agent_name → file path → method → line hints
- [ ] Map all your current agents:
  - [ ] ChatAgent → ChatPlugin.py
  - [ ] ResumeMatching → ResumeMatchingPlugin.py
  - [ ] ResumeTailoring → ResumeTailoringPlugin.py
  - [ ] DatabaseQuery → QueryDatabasePlugin.py
  - [ ] SelfImprovingMatch → SelfImprovingMatchPlugin.py
  - [ ] JobPlugin → JobPlugin.py
- [ ] Add operation-to-method mapping for each agent
- [ ] Add line number hints (approximate) for key methods

#### 1.2 Create Story Definitions Configuration
- [ ] Create `dashboard/config/story_definitions.py`
- [ ] Define each story with:
  - [ ] Story ID, title, icon, description
  - [ ] Data columns used (for transparency)
  - [ ] Thresholds that trigger "red flag"
  - [ ] Target page to drill into
  - [ ] Filter keys to pass

---

### Phase 2: Data Analysis Functions

#### 2.1 Create Story Analysis Module
- [ ] Create `dashboard/utils/story_analyzer.py`
- [ ] Implement analysis function for each story:
  - [ ] `analyze_latency_story(calls)` → returns latency issues by operation
  - [ ] `analyze_cache_story(calls)` → returns cache miss opportunities
  - [ ] `analyze_cost_story(calls)` → returns cost concentration data
  - [ ] `analyze_system_prompt_story(calls)` → returns prompt redundancy data
  - [ ] `analyze_token_imbalance_story(calls)` → returns prompt/completion ratios
  - [ ] `analyze_routing_story(calls)` → returns routing opportunities
  - [ ] `analyze_quality_story(calls)` → returns quality/error issues
- [ ] Each function returns:
  - [ ] Summary metrics (for story card)
  - [ ] Red flags (issues found)
  - [ ] Detailed data (for drill-down table)
  - [ ] Top offending operations (for quick action)

#### 2.2 Create Code Change Generator
- [ ] Create `dashboard/utils/code_generator.py`
- [ ] Implement code snippet generators:
  - [ ] `generate_cache_code(agent, operation, cache_key_pattern, ttl)`
  - [ ] `generate_routing_code(agent, operation, complexity_score)`
  - [ ] `generate_prompt_compression_code(agent, operation, current_tokens)`
  - [ ] `generate_sliding_window_code(agent, operation, max_messages)`
- [ ] Each generator uses actual data from the call to personalize the snippet

---

### Phase 3: New Stories Dashboard Page

#### 3.1 Create Story Insights Page
- [ ] Create `dashboard/pages/story_insights.py`
- [ ] Implement page structure:
  - [ ] Health banner at top (reuse from home.py)
  - [ ] Story cards grid (2x3 or 3x2 layout)
  - [ ] Each card shows: icon, title, key metric, red flag count, "View →" button

#### 3.2 Implement Story Cards
- [ ] Create `dashboard/components/story_card.py`
- [ ] Implement `render_story_card(story_data)`:
  - [ ] Title and icon
  - [ ] Key metric (e.g., "16s avg latency")
  - [ ] Red flag indicator (e.g., "3 operations affected")
  - [ ] Mini data table (top 3 offenders)
  - [ ] "Drill Down →" button

#### 3.3 Implement Story Expansion (Optional - inline detail)
- [ ] Add expandable section when story card clicked
- [ ] Shows full data table for that story
- [ ] "Go to [Page] →" button to navigate with filters

---

### Phase 4: Enhance Existing Pages for Filter Handoff

#### 4.1 Update Session State Navigation
- [ ] Define standard filter keys in `dashboard/config/filter_keys.py`:
  - [ ] `story_filter_agent`
  - [ ] `story_filter_operation`
  - [ ] `story_filter_type` (cache/routing/prompt/etc.)
  - [ ] `story_source` (which story sent user here)

#### 4.2 Update Cache Analyzer
- [ ] Accept filter from Stories page
- [ ] When filtered:
  - [ ] Show banner: "From Story: Zero Cache Hits"
  - [ ] Auto-filter to the specific operation
  - [ ] Show actual duplicate prompts (full text)
  - [ ] Show personalized cache key suggestion
  - [ ] Show code snippet with actual file path from plugin_map
  - [ ] Show expected savings calculation
  - [ ] Add "✓ Done - Measure Impact" button → routes to Optimization Impact

#### 4.3 Update Model Router
- [ ] Accept filter from Stories page
- [ ] When filtered:
  - [ ] Show banner: "From Story: Latency Monster" or "From Story: Model Routing"
  - [ ] Auto-expand the filtered operation
  - [ ] Show actual prompt samples causing latency
  - [ ] Show code snippet with actual file path
  - [ ] Add "✓ Done - Measure Impact" button

#### 4.4 Update Prompt Optimizer
- [ ] Accept filter from Stories page
- [ ] When filtered:
  - [ ] Show banner: "From Story: System Prompt Waste"
  - [ ] Auto-expand the filtered operation
  - [ ] Show actual system prompt text
  - [ ] Show compression suggestions
  - [ ] Show code snippet with actual file path
  - [ ] Add "✓ Done - Measure Impact" button

#### 4.5 Update Cost Estimator
- [ ] Accept filter from Stories page
- [ ] When filtered:
  - [ ] Show banner: "From Story: Cost Breakdown"
  - [ ] Auto-expand to show cost concentration
  - [ ] Link to relevant optimization page (cache/routing/prompt)

#### 4.6 Update LLM Judge
- [ ] Accept filter from Stories page
- [ ] When filtered:
  - [ ] Show banner: "From Story: Quality Issues"
  - [ ] Auto-filter to show failures/hallucinations

---

### Phase 5: Code Location & Change Guidance

#### 5.1 Create Code Location Component
- [ ] Create `dashboard/components/code_location.py`
- [ ] Implement `render_code_location(agent, operation)`:
  - [ ] Shows: "📁 File: `agents/plugins/ResumeMatchingPlugin.py`"
  - [ ] Shows: "🔧 Method: `quick_score_job()`"
  - [ ] Shows: "📍 Line: ~120"
  - [ ] "Copy path" button

#### 5.2 Create Before/After Code Component
- [ ] Create `dashboard/components/code_diff.py`
- [ ] Implement `render_code_change(before_code, after_code, explanation)`:
  - [ ] Side-by-side or stacked view
  - [ ] Syntax highlighted
  - [ ] "Copy code" button
  - [ ] Expected impact metrics

#### 5.3 Integrate into Existing Pages
- [ ] Add code location to Cache Analyzer filtered view
- [ ] Add code location to Model Router filtered view
- [ ] Add code location to Prompt Optimizer filtered view

---

### Phase 6: Connect to Optimization Impact

#### 6.1 Add "Measure Impact" Flow
- [ ] Add "✓ I've made this change" button to each page's filtered view
- [ ] Button routes to Optimization Impact with context:
  - [ ] `optimization_type`: cache/routing/prompt
  - [ ] `optimization_target`: agent.operation
  - [ ] `expected_savings`: calculated estimate

#### 6.2 Update Optimization Impact Page
- [ ] Accept context from other pages
- [ ] Show reminder: "You optimized `quick_score_job` caching. Run your app with `phase='optimized'` to measure."
- [ ] Pre-filter comparison to show relevant operation
- [ ] Highlight if expected savings were achieved

---

### Phase 7: Navigation & UX Polish

#### 7.1 Update Sidebar Navigation
- [ ] Rename/reorder pages:
  - [ ] 📊 Stories (main - story_insights.py)
  - [ ] 💾 Cache Analyzer
  - [ ] 🔀 Model Router
  - [ ] ✨ Prompt Optimizer
  - [ ] 💰 Cost Estimator
  - [ ] ⚖️ LLM Judge
  - [ ] 📡 Activity Monitor
  - [ ] 📈 Optimization Impact
- [ ] Set Stories as default landing page

#### 7.2 Add Breadcrumb Navigation
- [ ] Create `dashboard/components/breadcrumb.py`
- [ ] Show: "Stories → Cache Story → quick_score_job"
- [ ] Clickable to go back

#### 7.3 Add "Back to Stories" Button
- [ ] Add to each page when user came from Stories
- [ ] Preserves context for easy navigation

---

### Phase 8: Testing & Validation

#### 8.1 Test Each Story Flow End-to-End
- [ ] Latency Story → Model Router → Code Change → Optimization Impact
- [ ] Cache Story → Cache Analyzer → Code Change → Optimization Impact
- [ ] Cost Story → Cost Estimator → (routes to appropriate optimizer)
- [ ] System Prompt Story → Prompt Optimizer → Code Change → Optimization Impact
- [ ] Token Imbalance Story → Prompt Optimizer → Code Change → Optimization Impact
- [ ] Routing Story → Model Router → Code Change → Optimization Impact
- [ ] Quality Story → LLM Judge → (review/fix prompts)

#### 8.2 Test with Real Data
- [ ] Load your observatory_export.xlsx data
- [ ] Verify all stories populate correctly
- [ ] Verify drill-downs show actual prompt content
- [ ] Verify code suggestions reference correct files

---

### Phase 9: Documentation

#### 9.1 Update README
- [ ] Document new Stories dashboard
- [ ] Document the optimization workflow
- [ ] Add screenshots

#### 9.2 Add In-App Help
- [ ] Add "?" tooltips explaining each story
- [ ] Add "How to use this page" collapsed section

---

## 📊 Files Summary

### New Files to Create

| File | Purpose |
|------|---------|
| `dashboard/pages/story_insights.py` | Main stories dashboard |
| `dashboard/config/plugin_map.py` | Agent → file → method mapping |
| `dashboard/config/story_definitions.py` | Story metadata |
| `dashboard/config/filter_keys.py` | Standard filter key names |
| `dashboard/utils/story_analyzer.py` | Story data analysis functions |
| `dashboard/utils/code_generator.py` | Personalized code snippet generators |
| `dashboard/components/story_card.py` | Story card component |
| `dashboard/components/code_location.py` | File/method/line display |
| `dashboard/components/code_diff.py` | Before/after code display |
| `dashboard/components/breadcrumb.py` | Navigation breadcrumb |

### Existing Files to Modify

| File | Changes |
|------|---------|
| `cache_analyzer.py` | Add filtered view with code guidance |
| `model_router.py` | Add filtered view with code guidance |
| `prompt_optimizer.py` | Add filtered view with code guidance |
| `cost_estimator.py` | Add story filter handling |
| `llm_judge.py` | Add story filter handling |
| `optimization_impact.py` | Add context from optimization pages |
| Sidebar/navigation | Reorder, set Stories as default |

---

## ⏱️ Estimated Effort

| Phase | Effort | Priority |
|-------|--------|----------|
| Phase 1: Foundation & Config | 2-3 hours | 🔴 Must have first |
| Phase 2: Data Analysis | 3-4 hours | 🔴 Must have |
| Phase 3: Stories Dashboard | 3-4 hours | 🔴 Must have |
| Phase 4: Enhance Existing Pages | 4-6 hours | 🔴 Must have |
| Phase 5: Code Location Guidance | 2-3 hours | 🟡 High value |
| Phase 6: Optimization Impact Connection | 1-2 hours | 🟡 High value |
| Phase 7: Navigation Polish | 1-2 hours | 🟢 Nice to have |
| Phase 8: Testing | 2-3 hours | 🔴 Must have |
| Phase 9: Documentation | 1-2 hours | 🟢 Nice to have |

**Total: ~20-30 hours**

---

## 🚀 Recommended Build Order

1. **Phase 1** → Plugin map (you'll reference this everywhere)
2. **Phase 2** → Story analyzers (you need data to display)
3. **Phase 3** → Stories page (the new entry point)
4. **Phase 4.2** → Cache Analyzer enhancement (most common optimization)
5. **Phase 5** → Code location component (reusable)
6. **Phase 4.3-4.6** → Other page enhancements
7. **Phase 6** → Optimization Impact connection
8. **Phase 7-9** → Polish and documentation

---

## 📖 Story Definitions Reference

| Story | Title | Key Metric | Target Page | Red Flag Threshold |
|-------|-------|------------|-------------|-------------------|
| 1 | Latency Monster | Avg latency (s) | Model Router | > 5s avg |
| 2 | Zero Cache Hits | Cache miss count | Cache Analyzer | > 50% redundancy |
| 3 | Cost Breakdown | Cost concentration | Cost Estimator | Top 3 ops > 70% |
| 4 | System Prompt Waste | Redundant tokens | Prompt Optimizer | > 30% system tokens |
| 5 | Token Imbalance | Prompt:Completion ratio | Prompt Optimizer | > 10:1 ratio |
| 6 | Model Routing | Complexity mismatch | Model Router | High complexity + cheap model |
| 7 | Quality Issues | Error/hallucination rate | LLM Judge | > 3% rate |

---

## ✅ Success Criteria

The implementation is complete when:

1. **Part 1: Visualize** - Developer can see all 7 stories on the main dashboard with clear metrics and red flags
2. **Part 2: Engage** - Clicking any story drills down to show the specific operations and actual data causing the issue
3. **Part 3: Act** - Each drill-down shows:
   - The exact file path to modify
   - The method name and line number
   - Before/after code examples using their actual data
   - Expected impact metrics
4. **Part 4: Measure** - After making changes, developer can run with `phase='optimized'` and see actual improvement in Optimization Impact page

---

*Document created: December 2024*
*Project: AI Agent Observatory - Career Copilot*