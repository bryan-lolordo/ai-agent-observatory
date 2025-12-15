"""
Models Package - Complete Exports
Location: api/models/__init__.py

Exports from all 15 model files for easy importing.
"""

# =============================================================================
# BASE MODELS
# =============================================================================

from .base import (
    BaseResponse,
    ErrorDetail,
    ErrorResponse,
    PaginationMeta,
    PaginatedResponse,
    HealthResponse,
    SuccessResponse,
    CreatedResponse,
    DeletedResponse,
)

# =============================================================================
# LLM CALL MODELS
# =============================================================================

from .llm_call import (
    PromptBreakdown,
    RoutingDecision,
    CacheMetadata,
    QualityEvaluation,
    LLMCallResponse,
    LLMCallSummary,
    LLMCallListResponse,
    CallsByOperationResponse,
)

# =============================================================================
# FILTER MODELS
# =============================================================================

from .filters import (
    DateRangeFilter,
    CallFilters,
    StoryFilters,
    OperationFilters,
    TimeSeriesFilters,
    ComparisonFilters,
    ExportFilters,
)

# =============================================================================
# METADATA MODELS
# =============================================================================

from .metadata import (
    ProjectMetadata,
    ModelMetadata,
    AgentMetadata,
    OperationMetadata,
    ProjectsResponse,
    ModelsResponse,
    AgentsResponse,
    OperationsResponse,
    DatabaseStats,
    OverviewStats,
)

# =============================================================================
# STORY RESPONSE MODELS (Your existing responses.py)
# =============================================================================

from .responses import (
    TopOffender,
    Recommendation,
    ChartDataPoint,
    StoryResponse,
    LatencySummary,
    CacheSummary,
    CostSummary,
    SystemPromptSummary,
    TokenImbalanceSummary,
    RoutingSummary,
    QualitySummary,
    LatencyStoryResponse,
    CacheStoryResponse,
    CostStoryResponse,
    SystemPromptStoryResponse,
    TokenImbalanceStoryResponse,
    RoutingStoryResponse,
    QualityStoryResponse,
    AllStoriesResponse,
)

# =============================================================================
# OPTIMIZATION MODELS (Story 8)
# =============================================================================

from .optimization import (
    OptimizationRecord,
    BeforeAfterMetrics,
    OptimizationImpact,
    OptimizationListResponse,
    OptimizationDetailResponse,
    OptimizationSummaryResponse,
    CreateOptimizationRequest,
    UpdateOptimizationRequest,
)

# =============================================================================
# ANALYTICS MODELS
# =============================================================================

from .analytics import (
    TimeSeriesDataPoint,
    TimeSeriesResponse,
    MultiSeriesResponse,
    TrendAnalysis,
    MultiTrendResponse,
    PeriodMetrics,
    ComparisonMetrics,
    DistributionBucket,
    DistributionAnalysis,
    CorrelationPair,
    CorrelationMatrix,
)

# =============================================================================
# ALERTS MODELS
# =============================================================================

from .alerts import (
    AlertRule,
    Alert,
    AlertsResponse,
    AlertRulesResponse,
    CreateAlertRuleRequest,
    AcknowledgeAlertRequest,
)

# =============================================================================
# EXPERIMENT MODELS
# =============================================================================

from .experiment import (
    ExperimentConfig,
    ExperimentResults,
    ExperimentListResponse,
)

# =============================================================================
# DASHBOARD MODELS
# =============================================================================

from .dashboard import (
    WidgetConfig,
    DashboardLayout,
    DashboardResponse,
    DashboardListResponse,
)

# =============================================================================
# CODE LOCATION MODELS
# =============================================================================

from .code_location import (
    CodeLocation,
    CodeExample,
    OptimizationTemplate,
    OptimizationGuidance,
    CodeLocationResponse,
)

# =============================================================================
# BATCH MODELS
# =============================================================================

from .batch import (
    BatchExportRequest,
    BatchAnalysisRequest,
    BatchOperationResponse,
    ExportResponse,
)

# =============================================================================
# CONVERSATION MODELS
# =============================================================================

from .conversation import (
    ConversationTurn,
    ConversationDetail,
    ConversationSummary,
    ConversationListResponse,
    ConversationMetrics,
)

# =============================================================================
# USER PREFERENCES MODELS
# =============================================================================

from .user_preferences import (
    UserPreferences,
    TeamSettings,
    UserPreferencesResponse,
    UpdateUserPreferencesRequest,
)

# =============================================================================
# WEBHOOKS MODELS
# =============================================================================

from .webhooks import (
    WebhookConfig,
    WebhookDelivery,
    WebhookEvent,
    WebhookListResponse,
    WebhookDeliveryListResponse,
    CreateWebhookRequest,
    TestWebhookResponse,
)


# =============================================================================
# CONVENIENCE GROUPS (for easier importing)
# =============================================================================

# Core models (use now)
CORE_MODELS = [
    "BaseResponse", "ErrorResponse", "HealthResponse",
    "LLMCallResponse", "CallFilters", "ProjectsResponse",
]

# Story models (use now)
STORY_MODELS = [
    "LatencyStoryResponse", "CacheStoryResponse", "CostStoryResponse",
    "SystemPromptStoryResponse", "TokenImbalanceStoryResponse",
    "RoutingStoryResponse", "QualityStoryResponse", "AllStoriesResponse",
]

# Future models (use later)
FUTURE_MODELS = [
    "OptimizationRecord", "ExperimentConfig", "AlertRule",
    "DashboardLayout", "WebhookConfig",
]


__all__ = [
    # Base
    "BaseResponse",
    "ErrorDetail",
    "ErrorResponse",
    "PaginationMeta",
    "PaginatedResponse",
    "HealthResponse",
    "SuccessResponse",
    "CreatedResponse",
    "DeletedResponse",
    
    # LLM Calls
    "PromptBreakdown",
    "RoutingDecision",
    "CacheMetadata",
    "QualityEvaluation",
    "LLMCallResponse",
    "LLMCallSummary",
    "LLMCallListResponse",
    "CallsByOperationResponse",
    
    # Filters
    "DateRangeFilter",
    "CallFilters",
    "StoryFilters",
    "OperationFilters",
    "TimeSeriesFilters",
    "ComparisonFilters",
    "ExportFilters",
    
    # Metadata
    "ProjectMetadata",
    "ModelMetadata",
    "AgentMetadata",
    "OperationMetadata",
    "ProjectsResponse",
    "ModelsResponse",
    "AgentsResponse",
    "OperationsResponse",
    "DatabaseStats",
    "OverviewStats",
    
    # Story Responses
    "TopOffender",
    "Recommendation",
    "ChartDataPoint",
    "StoryResponse",
    "LatencySummary",
    "CacheSummary",
    "CostSummary",
    "SystemPromptSummary",
    "TokenImbalanceSummary",
    "RoutingSummary",
    "QualitySummary",
    "LatencyStoryResponse",
    "CacheStoryResponse",
    "CostStoryResponse",
    "SystemPromptStoryResponse",
    "TokenImbalanceStoryResponse",
    "RoutingStoryResponse",
    "QualityStoryResponse",
    "AllStoriesResponse",
    
    # Optimization
    "OptimizationRecord",
    "BeforeAfterMetrics",
    "OptimizationImpact",
    "OptimizationListResponse",
    "OptimizationDetailResponse",
    "OptimizationSummaryResponse",
    "CreateOptimizationRequest",
    "UpdateOptimizationRequest",
    
    # Analytics
    "TimeSeriesDataPoint",
    "TimeSeriesResponse",
    "MultiSeriesResponse",
    "TrendAnalysis",
    "MultiTrendResponse",
    "PeriodMetrics",
    "ComparisonMetrics",
    "DistributionBucket",
    "DistributionAnalysis",
    "CorrelationPair",
    "CorrelationMatrix",
    
    # Alerts
    "AlertRule",
    "Alert",
    "AlertsResponse",
    "AlertRulesResponse",
    "CreateAlertRuleRequest",
    "AcknowledgeAlertRequest",
    
    # Experiments
    "ExperimentConfig",
    "ExperimentResults",
    "ExperimentListResponse",
    
    # Dashboard
    "WidgetConfig",
    "DashboardLayout",
    "DashboardResponse",
    "DashboardListResponse",
    
    # Code Location
    "CodeLocation",
    "CodeExample",
    "OptimizationTemplate",
    "OptimizationGuidance",
    "CodeLocationResponse",
    
    # Batch
    "BatchExportRequest",
    "BatchAnalysisRequest",
    "BatchOperationResponse",
    "ExportResponse",
    
    # Conversation
    "ConversationTurn",
    "ConversationDetail",
    "ConversationSummary",
    "ConversationListResponse",
    "ConversationMetrics",
    
    # User Preferences
    "UserPreferences",
    "TeamSettings",
    "UserPreferencesResponse",
    "UpdateUserPreferencesRequest",
    
    # Webhooks
    "WebhookConfig",
    "WebhookDelivery",
    "WebhookEvent",
    "WebhookListResponse",
    "WebhookDeliveryListResponse",
    "CreateWebhookRequest",
    "TestWebhookResponse",
    
    # Convenience groups
    "CORE_MODELS",
    "STORY_MODELS",
    "FUTURE_MODELS",
]