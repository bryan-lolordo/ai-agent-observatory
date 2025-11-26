"""
OBSERVATORY CONFIG TEMPLATE (Enhanced)
=======================================

Copy this file to the ROOT of your AI project and customize it.
This provides centralized Observatory configuration with full metrics tracking.

FILE LOCATION: Put this at the root of your project
    your-project/
    ├── observatory_config.py  ← This file
    ├── agents/
    ├── services/
    └── ...

INSTALLATION (ONE-TIME SETUP):
===============================

1. Install Observatory in editable mode:
   
   cd path/to/ai-agent-observatory
   pip install -e .
   
   This allows all your projects to import Observatory.

2. Verify installation:
   
   python -c "from observatory import Observatory; print('✓ Installed!')"

3. Copy this file to your project root

4. Change PROJECT_NAME below

5. Import and use in your code:
   
   from observatory_config import track_llm_call


USAGE IN YOUR CODE:
    from observatory_config import obs, start_tracking_session, end_tracking_session, track_llm_call

SETUP INSTRUCTIONS:
1. Copy this file to your project root
2. Change PROJECT_NAME to your project name
3. Import and use in your code
"""

import os
from observatory import Observatory, ModelProvider, AgentRole
from observatory.models import QualityEvaluation, RoutingDecision, CacheMetadata

# ============================================================================
# CONFIGURATION - CUSTOMIZE THIS
# ============================================================================

# PROJECT NAME - Change this to your project name
PROJECT_NAME = "Your Project Name"  # ← CHANGE THIS (e.g., "Career Copilot", "Code Review Crew")


# ============================================================================
# DATABASE PATH - Automatically points to Observatory (DO NOT CHANGE)
# ============================================================================

# This assumes your project structure is:
#   your-projects/
#   ├── your-project/              (Career Copilot, Code Review Crew, etc.)
#   │   └── observatory_config.py  (this file)
#   └── ai-agent-observatory/      (Observatory project)
#       └── observatory.db         (centralized metrics database)

OBSERVATORY_DB_PATH = os.path.join(
    os.path.dirname(__file__),     # Current project root
    "..",                           # Go up one level
    "ai-agent-observatory",         # Observatory folder name
    "observatory.db"                # Database file
)
OBSERVATORY_DB_PATH = os.path.abspath(OBSERVATORY_DB_PATH)

# Set database URL environment variable
os.environ['DATABASE_URL'] = f"sqlite:///{OBSERVATORY_DB_PATH}"


# ============================================================================
# OBSERVATORY INITIALIZATION
# ============================================================================

obs = Observatory(
    project_name=PROJECT_NAME,
    enabled=True  # Set to False to disable all tracking
)

print(f"✅ Observatory initialized for {PROJECT_NAME}")
print(f"   Database: {OBSERVATORY_DB_PATH}")


# ============================================================================
# HELPER FUNCTIONS - Use these in your code
# ============================================================================

def start_tracking_session(operation_type: str, metadata: dict = None):
    """
    Start a tracking session for an operation.
    
    Args:
        operation_type: Type of operation (e.g., "resume_matching", "chat_message", "code_review")
        metadata: Optional metadata to store with the session
    
    Returns:
        Session object (pass this to end_tracking_session)
    
    Example:
        session = start_tracking_session("chat_message", {"user_id": "123"})
    """
    if metadata:
        return obs.start_session(operation_type, **metadata)
    else:
        return obs.start_session(operation_type)


def end_tracking_session(session, success: bool = True, error: str = None):
    """
    End a tracking session.
    
    Args:
        session: Session object from start_tracking_session
        success: Whether the operation succeeded
        error: Error message if operation failed
    
    Example:
        end_tracking_session(session, success=True)
        # or
        end_tracking_session(session, success=False, error="API timeout")
    """
    # Update session object before ending (Observatory.end_session doesn't accept these params)
    if session:
        if not success:
            session.success = False
        if error:
            session.error = error
    
    obs.end_session(session)


def track_llm_call(
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
    agent_name: str = None,
    operation: str = None,
    prompt: str = None,
    response_text: str = None,
    routing_decision: RoutingDecision = None,
    cache_metadata: CacheMetadata = None,
    quality_evaluation: QualityEvaluation = None,
    metadata: dict = None,
    provider: ModelProvider = ModelProvider.OPENAI
):
    """
    Record an LLM call in Observatory with enhanced metrics.
    
    Args:
        model_name: Name of the model (e.g., "gpt-4", "claude-sonnet-4")
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
        latency_ms: Time taken in milliseconds
        agent_name: Name of the agent making the call (optional)
        operation: Type of operation (optional)
        prompt: The actual prompt text (optional, enables cache analysis)
        response_text: The LLM response (optional, enables quality evaluation)
        routing_decision: Routing decision metadata (optional)
        cache_metadata: Cache performance metadata (optional)
        quality_evaluation: Quality evaluation results (optional)
        metadata: Additional metadata (optional)
        provider: LLM provider (OPENAI, ANTHROPIC, AZURE_OPENAI, etc.)
    
    Example (Basic):
        track_llm_call(
            model_name="gpt-4",
            prompt_tokens=1500,
            completion_tokens=800,
            latency_ms=2300,
            agent_name="CodeReviewer",
            operation="code_analysis"
        )
    
    Example (With Prompt/Response for Cache Analysis):
        track_llm_call(
            model_name="gpt-4",
            prompt_tokens=1500,
            completion_tokens=800,
            latency_ms=2300,
            prompt=original_prompt,
            response_text=llm_response
        )
    
    Example (With Routing Decision):
        routing = RoutingDecision(
            chosen_model="gpt-4",
            alternative_models=["claude-sonnet-4", "mistral-large"],
            reasoning="Complex reasoning task requires premium model"
        )
        track_llm_call(
            model_name="gpt-4",
            ...,
            routing_decision=routing
        )
    
    Example (With Cache):
        cache = CacheMetadata(
            cache_hit=True,
            cache_key="abc123",
            cache_cluster_id="resume_analysis"
        )
        track_llm_call(
            model_name="gpt-4",
            ...,
            cache_metadata=cache
        )
    
    Example (With Quality Evaluation):
        quality = QualityEvaluation(
            judge_score=8.5,
            reasoning="Good response with minor issues",
            hallucination_flag=False,
            confidence=0.85
        )
        track_llm_call(
            model_name="gpt-4",
            ...,
            quality_evaluation=quality
        )
    """
    obs.record_call(
        provider=provider,
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        agent_name=agent_name,
        operation=operation,
        prompt=prompt,
        response_text=response_text,
        routing_decision=routing_decision,
        cache_metadata=cache_metadata,
        quality_evaluation=quality_evaluation,
        metadata=metadata or {}
    )


# ============================================================================
# ADVANCED HELPER FUNCTIONS - For Enhanced Features
# ============================================================================

def create_routing_decision(
    chosen_model: str,
    alternative_models: list = None,
    reasoning: str = None
):
    """
    Create a RoutingDecision object for model routing tracking.
    
    Args:
        chosen_model: The model that was selected
        alternative_models: Other models that were considered
        reasoning: Why this model was chosen
    
    Returns:
        RoutingDecision object
    
    Example:
        routing = create_routing_decision(
            chosen_model="mistral-small",
            alternative_models=["gpt-4", "claude-sonnet-4"],
            reasoning="Simple classification task - using cheap model"
        )
    """
    return RoutingDecision(
        chosen_model=chosen_model,
        alternative_models=alternative_models or [],
        model_scores={},
        reasoning=reasoning or "Direct model selection (no routing logic applied)"
    )


def create_cache_metadata(
    cache_hit: bool,
    cache_key: str = None,
    cache_cluster_id: str = None
):
    """
    Create a CacheMetadata object for cache tracking.
    
    Args:
        cache_hit: Whether this was a cache hit (True) or miss (False)
        cache_key: The cache key used
        cache_cluster_id: Semantic cluster ID for grouping similar prompts
    
    Returns:
        CacheMetadata object
    
    Example:
        cache = create_cache_metadata(
            cache_hit=True,
            cache_key="hash_abc123",
            cache_cluster_id="resume_matching"
        )
    """
    return CacheMetadata(
        cache_hit=cache_hit,
        cache_key=cache_key,
        cache_cluster_id=cache_cluster_id
    )


def create_quality_evaluation(
    judge_score: float,
    reasoning: str = None,
    hallucination_flag: bool = False,
    factual_error: bool = False,
    confidence: float = None,
    error_category: str = None,
    suggestions: list = None
):
    """
    Create a QualityEvaluation object for quality tracking.
    
    Args:
        judge_score: Quality score from 0-10
        reasoning: Explanation of the score
        hallucination_flag: Whether hallucination was detected
        factual_error: Whether factual errors were found
        confidence: Judge confidence (0-1)
        error_category: Category of error if any
        suggestions: List of improvement suggestions
    
    Returns:
        QualityEvaluation object
    
    Example:
        quality = create_quality_evaluation(
            judge_score=8.5,
            reasoning="Good response with accurate information",
            hallucination_flag=False,
            confidence=0.9
        )
    """
    return QualityEvaluation(
        judge_score=judge_score,
        reasoning=reasoning,
        hallucination_flag=hallucination_flag,
        factual_error=factual_error,
        confidence=confidence,
        error_category=error_category,
        suggestions=suggestions or []
    )


# ============================================================================
# USAGE EXAMPLES - Copy and adapt for your code
# ============================================================================

"""
EXAMPLE 1: Basic LLM tracking (minimum required)
------------------------------------------------
import time
from observatory_config import track_llm_call

start_time = time.time()
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)
latency_ms = (time.time() - start_time) * 1000

track_llm_call(
    model_name="gpt-4",
    prompt_tokens=response.usage.prompt_tokens,
    completion_tokens=response.usage.completion_tokens,
    latency_ms=latency_ms,
    agent_name="Chatbot",
    operation="greeting"
)


EXAMPLE 2: With prompt/response (enables cache analysis)
---------------------------------------------------------
from observatory_config import track_llm_call

prompt = "Summarize this resume for a software engineer position"

start_time = time.time()
response = llm_call(prompt)
latency_ms = (time.time() - start_time) * 1000

track_llm_call(
    model_name="gpt-4",
    prompt_tokens=500,
    completion_tokens=200,
    latency_ms=latency_ms,
    agent_name="ResumeAnalyzer",
    operation="summarization",
    prompt=prompt,                    # ← Enables cache analysis
    response_text=response            # ← Enables quality evaluation
)


EXAMPLE 3: With routing decision (enables router analysis)
-----------------------------------------------------------
from observatory_config import track_llm_call, create_routing_decision

# Your routing logic
def route_query(query_complexity):
    if query_complexity < 0.3:
        return "mistral-small", ["gpt-4", "claude-sonnet-4"], "Low complexity"
    else:
        return "gpt-4", ["mistral-small"], "High complexity"

model, alternatives, reason = route_query(complexity_score)

routing = create_routing_decision(
    chosen_model=model,
    alternative_models=alternatives,
    reasoning=reason
)

track_llm_call(
    model_name=model,
    prompt_tokens=500,
    completion_tokens=200,
    latency_ms=1200,
    routing_decision=routing           # ← Enables router analysis
)


EXAMPLE 4: With caching (enables cache analysis)
-------------------------------------------------
from observatory_config import track_llm_call, create_cache_metadata
import hashlib

# Check cache
prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
cached_result = cache.get(prompt_hash)

if cached_result:
    # Cache hit!
    cache = create_cache_metadata(
        cache_hit=True,
        cache_key=prompt_hash,
        cache_cluster_id="resume_matching"
    )
    
    track_llm_call(
        model_name="gpt-4",
        prompt_tokens=0,  # No tokens used
        completion_tokens=0,
        latency_ms=5,     # Very fast
        cache_metadata=cache
    )
else:
    # Cache miss - call LLM
    response = llm_call(prompt)
    cache.set(prompt_hash, response)
    
    cache = create_cache_metadata(
        cache_hit=False,
        cache_key=prompt_hash,
        cache_cluster_id="resume_matching"
    )
    
    track_llm_call(
        model_name="gpt-4",
        prompt_tokens=500,
        completion_tokens=200,
        latency_ms=1200,
        cache_metadata=cache
    )


EXAMPLE 5: With quality evaluation (enables LLM Judge)
-------------------------------------------------------
from observatory_config import track_llm_call, create_quality_evaluation

# Your LLM call
response = llm_call(prompt)

# Optional: Run LLM-as-a-Judge
judge_response = judge_llm_call(f"Evaluate this response: {response}")
judge_data = parse_judge_response(judge_response)

quality = create_quality_evaluation(
    judge_score=judge_data['score'],
    reasoning=judge_data['reasoning'],
    hallucination_flag=judge_data['has_hallucination'],
    confidence=0.85
)

track_llm_call(
    model_name="gpt-4",
    prompt_tokens=500,
    completion_tokens=200,
    latency_ms=1200,
    quality_evaluation=quality        # ← Enables quality tracking
)


EXAMPLE 6: Full-featured tracking (all metrics)
------------------------------------------------
from observatory_config import (
    track_llm_call,
    create_routing_decision,
    create_cache_metadata,
    create_quality_evaluation
)

# 1. Routing decision
routing = create_routing_decision(
    chosen_model="gpt-4",
    alternative_models=["mistral-small", "claude-sonnet-4"],
    reasoning="Complex analysis requires premium model"
)

# 2. Check cache
prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
cached = cache.get(prompt_hash)
cache_meta = create_cache_metadata(
    cache_hit=bool(cached),
    cache_key=prompt_hash,
    cache_cluster_id="analysis_tasks"
)

# 3. LLM call (if not cached)
if not cached:
    response = llm_call(prompt)
    cache.set(prompt_hash, response)
else:
    response = cached

# 4. Quality evaluation (optional - can sample to reduce cost)
if should_evaluate():  # e.g., random.random() < 0.1 for 10% sampling
    judge_data = evaluate_response(prompt, response)
    quality = create_quality_evaluation(
        judge_score=judge_data['score'],
        reasoning=judge_data['reasoning'],
        hallucination_flag=judge_data['hallucination'],
        confidence=0.9
    )
else:
    quality = None

# 5. Track everything
track_llm_call(
    model_name="gpt-4",
    prompt_tokens=500,
    completion_tokens=200,
    latency_ms=1200,
    agent_name="AnalysisAgent",
    operation="deep_analysis",
    prompt=prompt,                    # For cache clustering
    response_text=response,           # For quality analysis
    routing_decision=routing,         # For router insights
    cache_metadata=cache_meta,        # For cache performance
    quality_evaluation=quality        # For quality tracking
)


EXAMPLE 7: Session with multiple LLM calls
-------------------------------------------
from observatory_config import (
    start_tracking_session,
    end_tracking_session,
    track_llm_call
)

session = start_tracking_session("multi_step_workflow", {"user_id": "123"})

try:
    # Step 1: Classification
    result1 = classify_query(query)
    track_llm_call(
        model_name="mistral-small",
        prompt_tokens=100,
        completion_tokens=10,
        latency_ms=300,
        agent_name="Classifier",
        operation="classify"
    )
    
    # Step 2: Analysis
    result2 = analyze_query(query, result1)
    track_llm_call(
        model_name="gpt-4",
        prompt_tokens=500,
        completion_tokens=300,
        latency_ms=2000,
        agent_name="Analyzer",
        operation="analyze"
    )
    
    # Step 3: Response generation
    result3 = generate_response(result2)
    track_llm_call(
        model_name="claude-sonnet-4",
        prompt_tokens=800,
        completion_tokens=400,
        latency_ms=1500,
        agent_name="Generator",
        operation="generate"
    )
    
    end_tracking_session(session, success=True)
    
except Exception as e:
    end_tracking_session(session, success=False, error=str(e))
    raise


# ============================================================================
# IMPLEMENTATION CHECKLIST
# ============================================================================

Minimum (enables basic tracking):
[ ] Import track_llm_call
[ ] Track model, tokens, latency for each LLM call
[ ] Set agent_name and operation

Recommended (enables cache analysis):
[ ] Pass prompt parameter
[ ] Pass response_text parameter

Advanced (enables all dashboard features):
[ ] Create routing decisions with alternatives
[ ] Track cache hits/misses
[ ] Implement quality evaluation (with sampling)
[ ] Use sessions for multi-step workflows

Dashboard Features Enabled By Each:
- Basic params → Cost Estimator, Model Router basics
- prompt + response_text → Cache Analyzer (semantic clustering)
- routing_decision → Model Router (routing effectiveness)
- cache_metadata → Cache Analyzer (hit rates, savings)
- quality_evaluation → LLM Judge (quality trends, hallucinations)


# ============================================================================
# NOTES
# ============================================================================

Performance:
- Minimal overhead: ~1ms per track_llm_call()
- Async writes to SQLite (non-blocking)
- Safe to use in production

Privacy:
- Prompts/responses are optional
- Store only what you need
- Data stays in your local database

Cost:
- Quality evaluation adds cost (~$0.002-0.01 per eval)
- Use sampling (10-20%) to control costs
- Can run judge on scheduled batch processing

Next Steps:
1. Copy this file to your project root
2. Change PROJECT_NAME
3. Add track_llm_call() to your LLM calls
4. Add prompt/response for cache analysis
5. Implement routing and track decisions
6. Add quality evaluation with sampling
7. View insights in Observatory dashboard!
"""