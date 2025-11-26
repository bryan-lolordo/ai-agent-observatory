"""
OBSERVATORY INTEGRATION PATTERNS
=================================

Quick-reference code snippets for common integration patterns.
Copy these into your project as needed.

For full template, see: observatory_config.py
"""

# ============================================================================
# PATTERN 1: BASIC TRACKING (Minimum Required)
# ============================================================================
"""
Enables: Cost Estimator, basic metrics
Dashboard pages: Home, Cost Estimator (basic mode)
"""

from observatory_config import track_llm_call
import time

def basic_tracking_example():
    # Your LLM call
    start = time.time()
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello"}]
    )
    latency_ms = (time.time() - start) * 1000
    
    # TRACK IT
    track_llm_call(
        model_name="gpt-4",
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        latency_ms=latency_ms,
        agent_name="Chatbot",              # Optional but recommended
        operation="greeting"                # Optional but recommended
    )


# ============================================================================
# PATTERN 2: WITH PROMPT/RESPONSE (Enables Cache Analysis)
# ============================================================================
"""
Enables: Cache Analyzer (semantic clustering)
Dashboard pages: Home, Cost Estimator, Cache Analyzer
"""

from observatory_config import track_llm_call
import time

def cache_analysis_example():
    prompt = "Summarize this resume for a software engineer"
    
    # Your LLM call
    start = time.time()
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    latency_ms = (time.time() - start) * 1000
    response_text = response.choices[0].message.content
    
    # TRACK IT WITH PROMPT/RESPONSE
    track_llm_call(
        model_name="gpt-4",
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        latency_ms=latency_ms,
        agent_name="ResumeAnalyzer",
        operation="summarization",
        prompt=prompt,                      # ← Enables cache analysis
        response_text=response_text         # ← Enables quality evaluation
    )


# ============================================================================
# PATTERN 3: FULL-FEATURED (All Dashboard Features)
# ============================================================================
"""
Enables: ALL dashboard pages with full functionality
Dashboard pages: All 8 pages with complete features
"""

from observatory_config import (
    track_llm_call,
    create_routing_decision,
    create_cache_metadata,
    create_quality_evaluation
)
import time
import hashlib

def full_featured_example():
    prompt = "Analyze this code for security vulnerabilities"
    
    # 1. ROUTING LOGIC (your implementation)
    complexity = analyze_prompt_complexity(prompt)
    if complexity > 0.7:
        model = "gpt-4"
        routing = create_routing_decision(
            chosen_model="gpt-4",
            alternative_models=["gpt-4o-mini", "claude-sonnet-4"],
            reasoning="High complexity requires premium model"
        )
    else:
        model = "gpt-4o-mini"
        routing = create_routing_decision(
            chosen_model="gpt-4o-mini",
            alternative_models=["gpt-4"],
            reasoning="Simple task - using cheap model"
        )
    
    # 2. CACHE CHECK (your implementation)
    cache_key = hashlib.md5(prompt.encode()).hexdigest()
    cached_response = your_cache.get(cache_key)
    
    if cached_response:
        # CACHE HIT
        cache_meta = create_cache_metadata(
            cache_hit=True,
            cache_key=cache_key,
            cache_cluster_id="code_analysis"
        )
        
        track_llm_call(
            model_name=model,
            prompt_tokens=0,                # No tokens used
            completion_tokens=0,
            latency_ms=5,                   # Very fast
            agent_name="CodeAnalyzer",
            operation="security_analysis",
            prompt=prompt,
            response_text=cached_response,
            routing_decision=routing,
            cache_metadata=cache_meta       # ← Tracks cache hit
        )
        
        return cached_response
    
    # 3. CACHE MISS - MAKE LLM CALL
    start = time.time()
    response = openai.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    latency_ms = (time.time() - start) * 1000
    response_text = response.choices[0].message.content
    
    # Cache it for next time
    your_cache.set(cache_key, response_text)
    
    cache_meta = create_cache_metadata(
        cache_hit=False,
        cache_key=cache_key,
        cache_cluster_id="code_analysis"
    )
    
    # 4. QUALITY EVALUATION (optional - sample 10% to save cost)
    quality = None
    if should_evaluate():  # e.g., random.random() < 0.1
        judge_result = evaluate_with_llm_judge(prompt, response_text)
        quality = create_quality_evaluation(
            judge_score=judge_result['score'],
            reasoning=judge_result['reasoning'],
            hallucination_flag=judge_result.get('hallucination', False),
            confidence=0.85
        )
    
    # 5. TRACK EVERYTHING
    track_llm_call(
        model_name=model,
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        latency_ms=latency_ms,
        agent_name="CodeAnalyzer",
        operation="security_analysis",
        prompt=prompt,                      # For cache clustering
        response_text=response_text,        # For quality analysis
        routing_decision=routing,           # ← Enables Model Router page
        cache_metadata=cache_meta,          # ← Enables Cache Analyzer page
        quality_evaluation=quality          # ← Enables LLM Judge page
    )
    
    return response_text


# ============================================================================
# PATTERN 4: SESSION TRACKING (Multi-Step Workflows)
# ============================================================================
"""
Track entire workflows with multiple LLM calls
"""

from observatory_config import start_tracking_session, end_tracking_session, track_llm_call

def session_tracking_example():
    # Start session
    session = start_tracking_session(
        operation_type="code_review_workflow",
        metadata={"file": "app.py", "user": "bryan"}
    )
    
    try:
        # Step 1: Analyze
        result1 = llm_call_step_1()
        track_llm_call(...)  # Track this call
        
        # Step 2: Review
        result2 = llm_call_step_2()
        track_llm_call(...)  # Track this call
        
        # Step 3: Fix
        result3 = llm_call_step_3()
        track_llm_call(...)  # Track this call
        
        # End session (success)
        end_tracking_session(session, success=True)
        return result3
        
    except Exception as e:
        # End session (failure)
        end_tracking_session(session, success=False, error=str(e))
        raise


# ============================================================================
# PATTERN 5: MULTI-AGENT TRACKING (Different Agents)
# ============================================================================
"""
Track multiple agents in same workflow
"""

def multi_agent_example():
    session = start_tracking_session(operation_type="multi_agent_workflow")
    
    try:
        # Agent 1: Classifier
        track_llm_call(
            model_name="gpt-4o-mini",
            ...,
            agent_name="QueryClassifier",
            operation="classify"
        )
        
        # Agent 2: Analyzer
        track_llm_call(
            model_name="gpt-4",
            ...,
            agent_name="DeepAnalyzer",
            operation="analyze"
        )
        
        # Agent 3: Generator
        track_llm_call(
            model_name="claude-sonnet-4",
            ...,
            agent_name="ResponseGenerator",
            operation="generate"
        )
        
        end_tracking_session(session, success=True)
        
    except Exception as e:
        end_tracking_session(session, success=False, error=str(e))
        raise


# ============================================================================
# HELPER FUNCTIONS (Utility Examples)
# ============================================================================

def analyze_prompt_complexity(prompt: str) -> float:
    """Example: Analyze prompt complexity for routing"""
    # Your logic here
    word_count = len(prompt.split())
    if word_count > 100:
        return 0.8
    elif word_count > 50:
        return 0.5
    else:
        return 0.2

def should_evaluate() -> bool:
    """Example: Decide whether to run expensive quality eval"""
    import random
    return random.random() < 0.1  # 10% sampling

def evaluate_with_llm_judge(prompt: str, response: str) -> dict:
    """Example: Run LLM-as-a-judge evaluation"""
    # Your judge implementation
    judge_prompt = f"""
    Evaluate this response on a scale of 0-10:
    
    Prompt: {prompt}
    Response: {response}
    
    Check for: accuracy, relevance, hallucinations
    """
    
    # Call judge model
    judge_response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": judge_prompt}]
    )
    
    # Parse judge response (your parsing logic)
    return {
        'score': 8.5,
        'reasoning': "Good response with minor issues",
        'hallucination': False
    }


# ============================================================================
# DASHBOARD FEATURES ENABLED BY EACH PATTERN
# ============================================================================

"""
PATTERN 1 (Basic):
  ✓ Home page (basic KPIs)
  ✓ Cost Estimator (historical costs)
  ✓ Live Demo (basic monitoring)
  ✗ Cache Analyzer (needs prompt)
  ✗ Model Router (needs routing_decision)
  ✗ LLM Judge (needs quality_evaluation)

PATTERN 2 (+ Prompt/Response):
  ✓ Home page (full KPIs)
  ✓ Cost Estimator (full features)
  ✓ Live Demo (full monitoring)
  ✓ Cache Analyzer (semantic clustering) ← NEW
  ✗ Model Router (needs routing_decision)
  ✗ LLM Judge (needs quality_evaluation)

PATTERN 3 (Full-Featured):
  ✓ All 8 dashboard pages with complete functionality
  ✓ Home page
  ✓ Live Demo
  ✓ Cost Estimator
  ✓ Model Router ← NEW
  ✓ Cache Analyzer
  ✓ LLM Judge ← NEW
  ✓ Prompt Optimizer
  ✓ Settings
"""


# ============================================================================
# QUICK START RECOMMENDATION
# ============================================================================

"""
START HERE:
1. Use Pattern 1 (basic) to get started quickly
2. Add Pattern 2 (prompt/response) when you want cache insights
3. Upgrade to Pattern 3 (full) when you want all features

Most projects should aim for Pattern 3 eventually, but Pattern 2 
gives you 80% of the value with minimal effort.
"""
