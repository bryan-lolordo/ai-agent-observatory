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

Choose ONE of these installation methods:

OPTION A: Global Installation (Recommended - Install Once)
-----------------------------------------------------------
Install Observatory globally so ALL projects can use it:

1. Open terminal/command prompt (NOT in any venv)
2. Navigate to Observatory:
   cd path/to/ai-agent-observatory
   
3. Install globally:
   pip install -e .
   
4. Verify:
   python -c "from observatory import Observatory; print('✓ Installed!')"

Now every project can import Observatory without reinstalling.


OPTION B: Per-Project Installation (Install in Each Project's Venv)
--------------------------------------------------------------------
Install Observatory separately in each project's virtual environment:

1. Activate your project's venv:
   cd path/to/your-project
   .venv\Scripts\activate       # Windows
   source .venv/bin/activate    # Mac/Linux
   
2. Install Observatory from local path:
   pip install -e ../ai-agent-observatory
   
3. Repeat for each project

RECOMMENDATION: Use Option A (Global) for simplicity.


USAGE IN YOUR CODE:
===================
from observatory_config import obs, start_tracking_session, end_tracking_session, track_llm_call


SETUP STEPS:
============
1. Install Observatory (see above)
2. Copy this file to your project root
3. Change PROJECT_NAME below
4. Import and use in your code
"""

import os
from observatory import Observatory, ModelProvider, AgentRole

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
    return obs.start_session(
        operation_type=operation_type,
        metadata=metadata or {}
    )


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
    obs.end_session(session, success=success, error=error)


def track_llm_call(
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
    agent_name: str = None,
    operation: str = None,
    metadata: dict = None,
    provider: ModelProvider = ModelProvider.OPENAI  # Default to OpenAI, change if needed
):
    """
    Record an LLM call in Observatory.
    
    Args:
        model_name: Name of the model (e.g., "gpt-4", "claude-sonnet-3-5")
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
        latency_ms: Time taken in milliseconds
        agent_name: Name of the agent making the call (optional)
        operation: Type of operation (optional)
        metadata: Additional metadata (optional)
        provider: LLM provider (default: OpenAI, change to ANTHROPIC, AZURE_OPENAI, etc.)
    
    Example:
        track_llm_call(
            model_name="gpt-4",
            prompt_tokens=1500,
            completion_tokens=800,
            latency_ms=2300,
            agent_name="CodeReviewer",
            operation="code_analysis"
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
        metadata=metadata or {}
    )


# ============================================================================
# AGENT ROLE MAPPING (Optional - Customize for your agents)
# ============================================================================

# Map your agent/plugin names to Observatory agent roles
# This helps categorize agents in the dashboard
# Available roles: ANALYST, REVIEWER, FIXER, ORCHESTRATOR, CUSTOM
AGENT_ROLE_MAP = {
    # Example mappings - customize for your project
    "YourAgent1": AgentRole.ANALYST,      # Analyzes data
    "YourAgent2": AgentRole.REVIEWER,     # Reviews outputs
    "YourAgent3": AgentRole.FIXER,        # Fixes/improves content
    "YourAgent4": AgentRole.ORCHESTRATOR, # Coordinates other agents
    # Add your agents here...
}


def get_agent_role(agent_name: str) -> AgentRole:
    """
    Get the appropriate AgentRole for an agent.
    
    Args:
        agent_name: Name of your agent
    
    Returns:
        AgentRole enum value (defaults to ANALYST if not found)
    """
    return AGENT_ROLE_MAP.get(agent_name, AgentRole.ANALYST)


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
EXAMPLE 1: Track a simple operation
-----------------------------------
from observatory_config import start_tracking_session, end_tracking_session

session = start_tracking_session("user_query")
try:
    # Your code here
    result = process_user_query()
    end_tracking_session(session, success=True)
except Exception as e:
    end_tracking_session(session, success=False, error=str(e))


EXAMPLE 2: Track an LLM call
----------------------------
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


EXAMPLE 3: Track a complex workflow
-----------------------------------
from observatory_config import start_tracking_session, end_tracking_session, track_llm_call

session = start_tracking_session("multi_step_workflow", {"steps": 3})

try:
    # Step 1: LLM call
    start = time.time()
    result1 = llm_call_1()
    track_llm_call("gpt-4", 100, 50, (time.time() - start) * 1000, operation="step1")
    
    # Step 2: LLM call
    start = time.time()
    result2 = llm_call_2()
    track_llm_call("gpt-4", 200, 100, (time.time() - start) * 1000, operation="step2")
    
    # Step 3: LLM call
    start = time.time()
    result3 = llm_call_3()
    track_llm_call("gpt-3.5-turbo", 150, 75, (time.time() - start) * 1000, operation="step3")
    
    end_tracking_session(session, success=True)
    
except Exception as e:
    end_tracking_session(session, success=False, error=str(e))
    raise
"""