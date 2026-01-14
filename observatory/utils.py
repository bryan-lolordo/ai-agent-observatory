"""
Shared utility functions for Observatory SDK
Location: observatory/utils.py

Consolidated utility functions used across the observatory package:
- Token estimation (tiktoken-based)
- Content hashing (MD5-based)
- Prompt normalization
- Cost calculation
- Client type detection
"""

import os
import re
import hashlib
from typing import Any, Tuple


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


def generate_content_hash(text: str, length: int = 8) -> str:
    """
    Generate deterministic hash from text prefix.

    Alias for compute_content_hash with default length of 8.
    Kept for backwards compatibility.

    Args:
        text: Text to hash
        length: Length of hash to return (default 8 characters)

    Returns:
        Hex string hash
    """
    if not text:
        return ""
    return hashlib.md5(text[:500].encode()).hexdigest()[:length]


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
