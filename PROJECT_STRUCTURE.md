# AI Agent Observatory - Complete Project Architecture

---

## 📋 Project Overview

The Observatory is a comprehensive LLM observability platform with:
- **Backend:** FastAPI + SQLite (28 files, 8 story services)
- **Frontend:** React + Vite + Tailwind + shadcn/ui
- **Core Library:** Python tracking SDK (observatory/)
- **Database:** SQLite with 85-column schema

---

## 🗂️ Complete File Structure

```
ai-agent-observatory/
│
├── .env                                # Environment variables (DB URL, API keys)
├── .git/                               # Git repository
├── .gitignore                          # Git ignore patterns
├── .pytest_cache/                      # pytest cache (auto-generated)
├── .venv/                              # Python virtual environment
├── ai_agent_observatory.egg-info/      # Python package metadata (auto-generated)
├── excel.py                            # Utility: Export database to Excel
├── LICENSE                             # Project license
├── observatory.db                      # SQLite database (85 columns, production data)
├── pyproject.toml                      # Python project configuration
├── pytest.ini                          # pytest configuration
├── README.md                           # Main project documentation
├── requirements.txt                    # Python dependencies
├── setup.py                            # Python package setup
├── x.py                                # Utility: Database schema verification
│
├── api/                                # 🚀 FastAPI Backend (28 files)
│   ├── __init__.py                         # Package marker
│   ├── dependencies.py                     # Dependency injection (get_storage, etc.)
│   ├── main.py                             # FastAPI app entry point + router registration
│   │
│   ├── config/                             # ⚙️ Configuration
│   │   ├── __init__.py
│   │   ├── plugin_map.py                       # Agent → file → method mapping
│   │   ├── settings.py                         # Environment settings (DB URL, API keys)
│   │   └── story_definitions.py                # Story metadata & thresholds
│   │
│   ├── models/                             # 📦 Pydantic Response Models (16 files)
│   │   ├── __init__.py                         # Comprehensive exports for all models (~95 models)
│   │   ├── alerts.py                           # AlertRule, Alert, threshold monitoring
│   │   ├── analytics.py                        # TimeSeriesResponse, TrendAnalysis, CorrelationMatrix
│   │   ├── base.py                             # BaseResponse, ErrorResponse, pagination
│   │   ├── batch.py                            # Batch exports: BatchExportRequest, ExportResponse
│   │   ├── code_location.py                    # Code guidance: CodeLocation, OptimizationTemplate
│   │   ├── conversation.py                     # Multi-turn analysis: ConversationDetail, ConversationMetrics
│   │   ├── dashboard.py                        # Custom dashboards: WidgetConfig, DashboardLayout
│   │   ├── experiment.py                       # A/B testing: ExperimentConfig, ExperimentResults
│   │   ├── filters.py                          # Query parameter models (CallFilters, DateRangeFilter)
│   │   ├── llm_call.py                         # LLMCallResponse, PromptBreakdown, QualityEvaluation
│   │   ├── metadata.py                         # ProjectsResponse, ModelsResponse, AgentsResponse
│   │   ├── optimization.py                     # Story 8: Before/after metrics, optimization tracking
│   │   ├── responses.py                        # Story response models (7 stories + summaries)
│   │   ├── user_preferences.py                 # UserPreferences, TeamSettings, notification config
│   │   └── webhooks.py                         # WebhookConfig, WebhookDelivery, integration events
│   │
│   ├── routers/                            # 🛤️ API Routes
│   │   ├── __init__.py
│   │   ├── alerts.py                           # ⏳ LATER - GET/POST /api/alerts, /api/alerts/rules
│   │   ├── analytics.py                        # ⏳ LATER - GET /api/analytics/timeseries, /trends
│   │   ├── calls.py                            # ⏳ LATER - Layer 3: GET /api/calls/{id}
│   │   ├── experiments.py                      # ⏳ LATER - GET/POST /api/experiments
│   │   ├── metadata.py                         # ✅ NOW - GET /api/projects, /models, /agents, /operations
│   │   ├── optimizations.py                    # ⏳ LATER - Story 8: GET/POST /api/optimizations
│   │   ├── stories.py                          # ✅ NOW - GET /api/stories, /api/stories/{id}
│   │   └── webhooks.py                         # ⏳ LATER - GET/POST /api/webhooks
│   │
│   ├── services/                           # 💼 Business Logic
│   │   ├── __init__.py
│   │   ├── alert_service.py                    # ⏳ LATER - Threshold monitoring & alert triggering
│   │   ├── analytics_service.py                # ⏳ LATER - Time series, trends, correlations
│   │   ├── batch_service.py                    # ⏳ LATER - Bulk exports (CSV/JSON)
│   │   ├── cache_service.py                    # ✅ NOW - Story 2: Cache opportunities
│   │   ├── call_service.py                     # ⏳ LATER - Layer 3: Individual call detail
│   │   ├── cost_service.py                     # ✅ NOW - Story 7: Cost analysis
│   │   ├── dashboard_service.py                # ⏳ LATER - Custom dashboard configs
│   │   ├── experiment_service.py               # ⏳ LATER - A/B testing logic
│   │   ├── latency_service.py                  # ✅ NOW - Story 1: Latency analysis
│   │   ├── optimization_service.py             # ⏳ LATER - Story 8: Before/after tracking
│   │   ├── prompt_service.py                   # ✅ NOW - Story 6: Prompt composition
│   │   ├── quality_service.py                  # ✅ NOW - Story 4: Quality issues
│   │   ├── routing_service.py                  # ✅ NOW - Story 3: Model routing
│   │   ├── token_service.py                    # ✅ NOW - Story 5: Token efficiency
│   │   └── webhook_service.py                  # ⏳ LATER - Integration events & delivery
│   │
│   └── utils/                              # 🛠️ Utilities
│       ├── __init__.py
│       ├── aggregators.py                      # Data aggregation functions
│       ├── data_fetcher.py                     # Database queries
│       ├── exceptions.py                       # Custom exceptions
│       └── formatters.py                       # Display formatting
│
├── frontend/                           # ⚛️ React Frontend (Vite + Tailwind v3 + shadcn/ui)
│   ├── .eslintrc.cjs                       # ESLint configuration (optional)
│   ├── .gitignore                          # Frontend-specific git ignore
│   ├── .prettierrc.cjs                     # Prettier auto-formatting (optional)
│   ├── components.json                     # shadcn/ui configuration (component install paths & aliases)
│   ├── index.html                          # Main HTML template
│   ├── jsconfig.json                       # JavaScript config (path aliases for @/*)
│   ├── node_modules/                       # NPM packages (auto-generated)
│   ├── package-lock.json                   # NPM lockfile
│   ├── package.json                        # NPM dependencies & scripts
│   ├── postcss.config.js                   # PostCSS config (Tailwind, autoprefixer)
│   ├── public/                             # Static assets (served as-is)
│   ├── README.md                           # Frontend documentation
│   ├── tailwind.config.js                  # Tailwind CSS v3 + shadcn config
│   ├── vite.config.js                      # Vite bundler config (proxy, path alias)
│   │
│   └── src/                                # 📂 Source Code
│       ├── App.jsx                             # Main app component (router)
│       ├── main.jsx                            # React entry point
│       │
│       ├── assets/                             # 🎨 Static Assets
│       │   ├── fonts/                              # Web fonts
│       │   └── images/                             # Images
│       │       ├── empty-state.svg                     # Empty state illustration
│       │       └── logo.svg                            # Observatory logo
│       │
│       ├── components/                         # 🧩 Reusable UI Components
│       │   ├── common/                             # Custom Common Components
│       │   │   ├── Button.jsx                          # Custom button (if needed)
│       │   │   ├── Card.jsx                            # Custom card (if needed)
│       │   │   ├── KPICard.jsx                         # KPI metric card
│       │   │   ├── Loading.jsx                         # Loading spinner
│       │   │   └── Table.jsx                           # Custom table (if needed)
│       │   │
│       │   ├── layout/                             # Layout Components
│       │   │   ├── Footer.jsx                          # Footer
│       │   │   ├── Header.jsx                          # Top navigation header
│       │   │   └── Sidebar.jsx                         # Side navigation
│       │   │
│       │   ├── stories/                            # Story-Specific Components
│       │   │   ├── CallDetail.jsx                      # Call detail display
│       │   │   ├── OperationTable.jsx                  # Operation data table
│       │   │   └── StoryCard.jsx                       # Story summary card
│       │   │
│       │   └── ui/                                 # 🎨 shadcn/ui components (installed)
│       │       ├── badge.jsx                           # Badge component (status indicators)
│       │       ├── button.jsx                          # Button component (all variants)
│       │       ├── card.jsx                            # Card component (containers)
│       │       └── table.jsx                           # Table component (data tables)
│       │
│       ├── config/                             # ⚙️ Configuration
│       │   ├── routes.js                           # Route definitions
│       │   └── theme.js                            # Rainbow color scheme & chart config
│       │
│       ├── constants/                          # 📌 Constants
│       │   ├── apiEndpoints.js                     # API endpoint URLs
│       │   └── storyDefinitions.js                 # Story metadata
│       │
│       ├── hooks/                              # 🎣 Custom React Hooks
│       │   ├── useCalls.js                         # Fetch calls data
│       │   ├── useDebounce.js                      # Debounce utility
│       │   └── useStories.js                       # Fetch stories data
│       │
│       ├── lib/                                # 📚 Libraries
│       │   └── utils.js                            # shadcn/ui utility functions (cn helper)
│       │
│       ├── pages/                              # 📄 Page Components
│       │   ├── CallDetail.jsx                      # Call detail page (Layer 3)
│       │   ├── Dashboard.jsx                       # Main dashboard (Layer 1)
│       │   └── stories/                            # Story Pages (Layer 2)
│       │       ├── Cache.jsx                           # Story 2: Caching
│       │       ├── Cost.jsx                            # Story 7: Cost
│       │       ├── Latency.jsx                         # Story 1: Latency
│       │       ├── Optimization.jsx                    # Story 8: Optimization Impact
│       │       ├── Prompt.jsx                          # Story 6: Prompt Composition
│       │       ├── Quality.jsx                         # Story 4: Quality
│       │       ├── Routing.jsx                         # Story 3: Routing
│       │       └── Token.jsx                           # Story 5: Token Efficiency
│       │
│       ├── services/                           # 📡 API Services
│       │   ├── api.js                              # Axios/fetch setup
│       │   └── observatoryApi.js                   # Observatory API client
│       │
│       ├── styles/                             # 🎨 Styles
│       │   ├── index.css                           # Tailwind directives + dark theme CSS variables
│       │   └── variables.css                       # CSS custom properties
│       │
│       └── utils/                              # 🛠️ Utilities
│           ├── formatters.js                       # Format numbers, dates, costs
│           ├── helpers.js                          # General helper functions
│           └── validators.js                       # Input validation
│
├── MD/                                 # 📚 Project Documentation
│   ├── api_endpoint_map.md                 # API endpoint specifications
│   ├── ARCHITECTURE.md                     # Architecture overview
│   ├── data-availability-map.md            # Data field coverage analysis
│   ├── Observatory.md                      # Main Observatory documentation
│   ├── stories.md                          # Story system documentation
│   └── x.md                                # Miscellaneous notes
│
├── observatory/                        # 🔭 Core Tracking Library (Python SDK)
│   ├── __init__.py                         # Package exports
│   ├── __pycache__/                        # Python bytecode (auto-generated)
│   ├── cache.py                            # Caching logic
│   ├── collector.py                        # Session & call tracking
│   ├── judge.py                            # LLM-as-judge quality evaluation
│   ├── models.py                           # Pydantic models (LLMCall, Session, etc.)
│   ├── prompts.py                          # Prompt utilities
│   ├── router.py                           # Model routing logic
│   └── storage.py                          # SQLAlchemy database layer
│
├── templates/                          # 📋 Configuration Templates
│   ├── observatory_config.py               # Template: Observatory configuration
│   └── tracking_template.py                # Template: How to instrument tracking
│
└── tests/                              # 🧪 Test Suite
    ├── __init__.py
    ├── fixtures/                           # Test Data
    │   └── sample_data.json                    # Sample LLM call data
    │
    ├── test_api/                           # API Tests
    │   ├── test_routers.py                     # Test API endpoints
    │   └── test_services.py                    # Test business logic
    │
    └── test_observatory/                   # Observatory SDK Tests
        ├── test_collector.py                   # Test data collection
        └── test_storage.py                     # Test database operations
```


## 🎯 Key Architecture Decisions

### **Backend:**
- **Pattern:** Service Layer (routers → services → utils → storage)
- **Database:** SQLite with SQLAlchemy ORM
- **API Style:** RESTful with 3-layer story architecture
- **Story Services:** One service file per story (8 total)

### **Frontend:**
- **Framework:** React 18 with Vite
- **Styling:** Tailwind CSS v4 + shadcn/ui
- **State:** React hooks (no Redux needed for MVP)
- **Routing:** React Router v6
- **Charts:** Recharts library

### **Core Library:**
- **Models:** Pydantic for validation
- **Storage:** SQLAlchemy with 85-column schema
- **Tracking:** Decorator-based instrumentation

---

## 🔗 Data Flow

```
User Action (Frontend)
    ↓
React Component (pages/)
    ↓
Custom Hook (hooks/useStories)
    ↓
API Service (services/observatoryApi.js)
    ↓
FastAPI Router (api/routers/stories.py)
    ↓
Service Layer (api/services/latency_service.py)
    ↓
Data Fetcher (api/utils/data_fetcher.py)
    ↓
Storage Layer (observatory/storage.py)
    ↓
SQLite Database (observatory.db)
```

---

## 📦 Dependencies

### **Backend (Python):**
```
fastapi
openpyxl
pandas
pydantic
pytest
python-dotenv
sqlalchemy
uvicorn
```

### **Frontend (Node):**
```
@tailwindcss/forms
axios
lucide-react (icons)
react
react-dom
react-router-dom
recharts
shadcn/ui components
tailwindcss
vite
```

---

## 🚀 Running the Project

### **Backend:**
```bash
# Activate virtual environment
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run API server
cd api
uvicorn main:app --reload --port 8000
```

### **Frontend:**
```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

### **Database Export:**
```bash
python excel.py  # Export observatory.db to Excel
```

---

## 🎨 Styling System

### **Color Palette:**
- **Background:** gray-950 (darkest) → gray-800 (cards)
- **Text:** gray-100 (primary) → gray-500 (muted)
- **Accents:** 
  - Blue (#3b82f6) - Info, links
  - Green (#22c55e) - Success, savings
  - Orange (#f97316) - Charts
  - Purple (#8b5cf6) - Agents
  - Red (#ef4444) - Errors, warnings
  - Yellow (#eab308) - Warnings, cost

### **Components:**
- **shadcn/ui:** Card, Button, Table (base components)
- **Custom:** KPICard, StoryCard, OperationTable
- **Charts:** Recharts with dark theme

---

## 📋 API Endpoints (24 Total)

### **Stories (16):**
- `GET /api/stories` - Layer 1: All stories summary
- `GET /api/stories/{story_id}` - Layer 2: Story detail (×8 stories)
- Story-specific Layer 3 endpoints (×7 stories)

### **Calls (6):**
- `GET /api/calls` - List calls with filters
- `GET /api/calls/{call_id}` - Get call detail
- `GET /api/calls/{call_id}/diagnosis` - Get diagnosis
- `GET /api/calls/{call_id}/recommendations` - Get recommendations
- Story-specific call endpoints (×2)

### **Metadata (4):**
- `GET /api/projects` - List projects
- `GET /api/models` - List models
- `GET /api/agents` - List agents
- `GET /api/operations` - List operations
