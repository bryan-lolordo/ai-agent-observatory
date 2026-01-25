"""
Shared utility functions for Observatory SDK
Location: observatory/utils.py

Consolidated utility functions used across the observatory package:
- Token estimation (tiktoken-based)
- Content hashing (MD5-based)
- Prompt normalization
- Cost calculation
- Client type detection
- Error classification
- Token breakdown extraction
- Model parameter extraction
"""

import os
import re
import hashlib
from typing import Any, Dict, List, Tuple


# =============================================================================
# TOKEN ESTIMATION
# =============================================================================

def estimate_tokens(text: str, model: str = None) -> int:
    """
    Accurate token estimation using tiktoken.

    Args:
        text: Text to tokenize
        model: Model name (defaults to environment or gpt-4o-mini)

    Returns:
        Token count
    """
    if not text:
        return 0

    if model is None:
        # Check both common environment variables
        model = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

    try:
        import tiktoken
        encoder = tiktoken.encoding_for_model(model)
        return len(encoder.encode(text))
    except Exception:
        # Fallback for unknown models or missing tiktoken
        return len(text) // 4


# =============================================================================
# HASHING FUNCTIONS
# =============================================================================

def compute_content_hash(content: str, length: int = 16) -> str:
    """
    Compute MD5 hash of content for deduplication/caching.

    This is a public utility function for use in observatory_config.py
    and other client code that needs to generate content hashes.

    Args:
        content: Text content to hash
        length: Length of hash to return (default 16 characters)

    Returns:
        Hex string hash of the content

    Example:
        >>> compute_content_hash("Hello, world!")
        '6cd3556deb0da54b'
    """
    if not content:
        return ""
    return hashlib.md5(content.encode()).hexdigest()[:length]


def generate_prompt_hash(prompt: str, prefix_length: int = 500) -> str:
    """
    Generate a short hash from prompt prefix for version detection.

    Useful for detecting prompt drift and version changes without
    storing the full prompt content.

    Args:
        prompt: Full prompt text
        prefix_length: Number of characters to hash (default 500)

    Returns:
        8-character hex hash
    """
    if not prompt:
        return ""
    return hashlib.md5(prompt[:prefix_length].encode()).hexdigest()[:8]


# =============================================================================
# TEXT NORMALIZATION
# =============================================================================

def normalize_prompt(prompt: str) -> str:
    """
    Normalize prompt for semantic matching and cache key generation.

    Normalization:
    - Lowercase
    - Strip leading/trailing whitespace
    - Collapse multiple whitespace to single space
    - Remove punctuation (except essential ones)

    This enables finding similar prompts even with minor differences:
    - "Find Python jobs in NYC" → "find python jobs in nyc"
    - "FIND  Python   jobs in NYC!" → "find python jobs in nyc"

    Args:
        prompt: Raw prompt text

    Returns:
        Normalized prompt string

    Example:
        >>> normalize_prompt("  Find Python JOBS in NYC!  ")
        'find python jobs in nyc'
    """
    if not prompt:
        return ""

    # Lowercase
    normalized = prompt.lower()

    # Strip leading/trailing whitespace
    normalized = normalized.strip()

    # Collapse multiple whitespace to single space
    normalized = re.sub(r'\s+', ' ', normalized)

    # Remove punctuation (keep alphanumeric and spaces)
    normalized = re.sub(r'[^\w\s]', '', normalized)

    return normalized.strip()


# =============================================================================
# COST CALCULATION
# =============================================================================

# Model pricing per token (prompt_price, completion_price)
MODEL_PRICING = {
    "gpt-4": (0.03 / 1000, 0.06 / 1000),
    "gpt-4o": (0.0025 / 1000, 0.01 / 1000),
    "gpt-4o-mini": (0.00015 / 1000, 0.0006 / 1000),
    "gpt-3.5-turbo": (0.0005 / 1000, 0.0015 / 1000),
    "claude-4": (0.015 / 1000, 0.075 / 1000),
    "claude-sonnet-4": (0.003 / 1000, 0.015 / 1000),
    "claude-3-5-sonnet": (0.003 / 1000, 0.015 / 1000),
    "claude-opus-4": (0.015 / 1000, 0.075 / 1000),
    "mistral-small": (0.0002 / 1000, 0.0006 / 1000),
}

DEFAULT_PRICING = (0.001 / 1000, 0.002 / 1000)


def calculate_cost(provider: Any, model_name: str, prompt_tokens: int, completion_tokens: int) -> Tuple[float, float]:
    """
    Calculate cost for LLM call based on model pricing.

    Args:
        provider: ModelProvider enum (not used directly, kept for API compatibility)
        model_name: Name of the model used
        prompt_tokens: Number of prompt/input tokens
        completion_tokens: Number of completion/output tokens

    Returns:
        Tuple of (prompt_cost, completion_cost)

    Example:
        >>> calculate_cost(ModelProvider.OPENAI, "gpt-4o-mini", 1000, 500)
        (0.00015, 0.0003)
    """
    model_lower = model_name.lower()
    prompt_price, completion_price = DEFAULT_PRICING

    for key, prices in MODEL_PRICING.items():
        if key in model_lower:
            prompt_price, completion_price = prices
            break

    prompt_cost = prompt_tokens * prompt_price
    completion_cost = completion_tokens * completion_price

    return prompt_cost, completion_cost


# =============================================================================
# CLIENT TYPE DETECTION
# =============================================================================

class ClientType:
    """Enum for supported LLM client types."""
    OPENAI = "openai"
    SEMANTIC_KERNEL = "semantic_kernel"
    CALLABLE = "callable"
    UNKNOWN = "unknown"


def detect_client_type(client: Any) -> str:
    """
    Detect the type of LLM client.

    Supports:
    - OpenAI / Azure OpenAI clients (has .chat.completions)
    - Semantic Kernel (has .invoke_prompt)
    - Generic callable (function or lambda)

    Args:
        client: The LLM client to detect

    Returns:
        ClientType string constant

    Example:
        >>> from openai import OpenAI
        >>> client = OpenAI()
        >>> detect_client_type(client)
        'openai'
    """
    # OpenAI / Azure OpenAI style (has .chat.completions.create)
    if hasattr(client, 'chat') and hasattr(client.chat, 'completions'):
        return ClientType.OPENAI

    # Semantic Kernel (has .invoke_prompt)
    if hasattr(client, 'invoke_prompt'):
        return ClientType.SEMANTIC_KERNEL

    # Generic callable (function or lambda)
    if callable(client):
        return ClientType.CALLABLE

    return ClientType.UNKNOWN


# =============================================================================
# ERROR CLASSIFICATION
# =============================================================================

def classify_error(error: Exception, operation: str = None) -> Dict[str, str]:
    """
    Classify errors for tracking and analysis.

    Categorizes common LLM API errors into standard types for easier
    debugging and monitoring.

    Args:
        error: The exception to classify
        operation: Optional operation name for context

    Returns:
        Dict with 'error_type' (exception class name) and 'error_code'
        (standardized code like AUTH_ERROR, RATE_LIMIT, etc.)

    Example:
        >>> try:
        ...     raise Exception("rate limit exceeded")
        ... except Exception as e:
        ...     classify_error(e)
        {'error_type': 'Exception', 'error_code': 'RATE_LIMIT'}
    """
    error_str = str(error).lower()
    error_type = type(error).__name__

    if any(x in error_str for x in ["api key", "unauthorized", "401", "authentication"]):
        return {"error_type": error_type, "error_code": "AUTH_ERROR"}
    elif any(x in error_str for x in ["rate limit", "429", "quota", "too many requests"]):
        return {"error_type": error_type, "error_code": "RATE_LIMIT"}
    elif any(x in error_str for x in ["timeout", "connection", "timed out", "connect"]):
        return {"error_type": error_type, "error_code": "TIMEOUT"}
    elif any(x in error_str for x in ["context length", "token limit", "maximum context", "too long"]):
        return {"error_type": error_type, "error_code": "CONTEXT_LENGTH_EXCEEDED"}
    elif any(x in error_str for x in ["content filter", "policy", "blocked", "safety"]):
        return {"error_type": error_type, "error_code": "CONTENT_FILTER"}
    elif any(x in error_str for x in ["invalid", "malformed", "bad request", "400"]):
        return {"error_type": error_type, "error_code": "INVALID_REQUEST"}
    elif any(x in error_str for x in ["not found", "404", "does not exist"]):
        return {"error_type": error_type, "error_code": "NOT_FOUND"}
    elif any(x in error_str for x in ["server error", "500", "502", "503", "504"]):
        return {"error_type": error_type, "error_code": "SERVER_ERROR"}
    else:
        return {"error_type": error_type, "error_code": "UNKNOWN"}


# =============================================================================
# TOKEN BREAKDOWN EXTRACTION
# =============================================================================

def extract_token_breakdown_from_messages(
    messages: List[Dict] = None,
    system_prompt: str = None,
    user_message: str = None,
    model: str = None,
) -> Dict[str, int]:
    """
    Extract token breakdown from messages or prompt components.

    Analyzes the token distribution across different message types
    (system, user, assistant) for cost analysis and optimization.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        system_prompt: System prompt text (used if messages not provided)
        user_message: User message text (used if messages not provided)
        model: Model name for accurate token estimation

    Returns:
        Dict with token counts:
        - system_prompt_tokens: Tokens in system messages
        - user_message_tokens: Tokens in the latest user message
        - chat_history_tokens: Tokens in previous messages
        - chat_history_count: Number of previous user messages
        - conversation_context_tokens: Total context tokens

    Example:
        >>> messages = [
        ...     {"role": "system", "content": "You are helpful."},
        ...     {"role": "user", "content": "Hello"},
        ...     {"role": "assistant", "content": "Hi there!"},
        ...     {"role": "user", "content": "How are you?"}
        ... ]
        >>> extract_token_breakdown_from_messages(messages)
        {'system_prompt_tokens': 4, 'user_message_tokens': 4, ...}
    """
    breakdown = {
        'system_prompt_tokens': 0,
        'user_message_tokens': 0,
        'chat_history_tokens': 0,
        'chat_history_count': 0,
        'conversation_context_tokens': 0,
    }

    if messages:
        user_messages = []
        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')
            tokens = estimate_tokens(content, model) if content else 0

            if role == 'system':
                breakdown['system_prompt_tokens'] += tokens
            elif role == 'user':
                user_messages.append(tokens)
            elif role in ['assistant', 'function', 'tool']:
                breakdown['chat_history_tokens'] += tokens

        if user_messages:
            # Last user message is the current one
            breakdown['user_message_tokens'] = user_messages[-1]
            # Previous user messages are history
            for t in user_messages[:-1]:
                breakdown['chat_history_tokens'] += t
            breakdown['chat_history_count'] = len(user_messages) - 1
    else:
        # Fall back to individual prompt components
        if system_prompt:
            breakdown['system_prompt_tokens'] = estimate_tokens(system_prompt, model)
        if user_message:
            breakdown['user_message_tokens'] = estimate_tokens(user_message, model)

    # Calculate total context
    breakdown['conversation_context_tokens'] = (
        breakdown['system_prompt_tokens'] +
        breakdown['user_message_tokens'] +
        breakdown['chat_history_tokens']
    )

    return breakdown


# =============================================================================
# MODEL PARAMETER EXTRACTION
# =============================================================================

def extract_model_parameters(
    execution_settings: Any = None,
    temperature: float = None,
    max_tokens: int = None,
    top_p: float = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Extract model parameters from various sources.

    Consolidates model configuration from explicit parameters and
    execution settings objects (like Semantic Kernel's).

    Args:
        execution_settings: Settings object with model config attributes
        temperature: Explicit temperature value
        max_tokens: Explicit max tokens value
        top_p: Explicit top_p value
        **kwargs: Additional parameters to include

    Returns:
        Dict with model parameters (temperature, max_tokens, top_p)

    Example:
        >>> extract_model_parameters(temperature=0.7, max_tokens=1000)
        {'temperature': 0.7, 'max_tokens': 1000, 'top_p': None}
    """
    params = {
        'temperature': temperature,
        'max_tokens': max_tokens,
        'top_p': top_p,
    }

    # Try to extract from execution_settings object
    if execution_settings:
        try:
            params['temperature'] = params['temperature'] or getattr(execution_settings, 'temperature', None)
            params['max_tokens'] = params['max_tokens'] or getattr(execution_settings, 'max_tokens', None)
            params['top_p'] = params['top_p'] or getattr(execution_settings, 'top_p', None)
        except Exception:
            pass

    return params
