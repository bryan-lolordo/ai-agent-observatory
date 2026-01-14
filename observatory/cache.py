"""
Cache Manager - Caching with Observatory Tracking
Location: observatory/cache.py

Provides caching for LLM responses with automatic Observatory metadata tracking.
Applications configure which operations to cache and TTL settings.

DETECTION_ONLY MODE (Baseline):
    - Checks cache and identifies exact match opportunities
    - Logs "would-be hits" for analysis
    - Does NOT return cached responses (baseline behavior unchanged)
    - Tracks opportunity metrics for reporting

ACTIVE MODE (Optimized):
    - Returns cached responses for exact matches
    - Reduces LLM calls and costs
"""

import hashlib
import re
import time
from typing import Optional, Dict, Any, Tuple, TYPE_CHECKING
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging

from observatory.models import CacheMetadata
from observatory.utils import compute_content_hash, normalize_prompt

if TYPE_CHECKING:
    from observatory.collector import Observatory

logger = logging.getLogger(__name__)


# =============================================================================
# CACHE ENTRY
# =============================================================================

@dataclass
class CacheEntry:
    """Individual cache entry."""
    key: str
    value: str
    created_at: datetime
    expires_at: Optional[datetime]
    operation: str
    hit_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# CACHE MANAGER
# =============================================================================

class CacheManager:
    """
    Caching system with Observatory integration.
    
    Usage:
        # Baseline mode - detect opportunities
        cache = CacheManager(
            observatory=obs,
            operations={"find_jobs": {"ttl": 3600, "normalize": True}},
            enabled=True,
            detection_only=True,  # Track opportunities, don't return cached
        )
        
        # Optimized mode - actually cache
        cache = CacheManager(
            observatory=obs,
            operations={"find_jobs": {"ttl": 3600, "normalize": True}},
            enabled=True,
            detection_only=False,  # Return cached responses
        )
        
        # Check cache before LLM call
        cached, metadata = cache.get(
            operation="find_jobs",
            key_data={"query": "Python developer", "location": "Chicago"}
        )
        
        if cached:
            # Use cached response
            return cached
        
        # Make LLM call...
        response = await llm.complete(...)
        
        # Cache the result
        cache.set(
            operation="find_jobs",
            key_data={"query": "Python developer", "location": "Chicago"},
            value=response
        )
    """
    
    def __init__(
        self,
        observatory: Optional['Observatory'] = None,
        operations: Optional[Dict[str, Dict[str, Any]]] = None,
        default_ttl: int = 3600,
        max_entries: int = 1000,
        normalize_prompts: bool = True,
        enabled: bool = True,  # NEW
        detection_only: bool = False,  # NEW
    ):
        """
        Initialize Cache Manager.
        
        Args:
            observatory: Observatory instance (for potential future tracking)
            operations: Dict of operation → config
                Config options: ttl (seconds), normalize (bool), cluster_id (str)
            default_ttl: Default time-to-live in seconds
            max_entries: Maximum cache entries before eviction
            normalize_prompts: Whether to normalize prompts by default
            enabled: Whether caching is active (NEW)
            detection_only: If True, detect opportunities but don't return cached responses (NEW)
        """
        self.observatory = observatory
        self.operations = operations or {}
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self.normalize_prompts = normalize_prompts
        self.enabled = enabled  # NEW
        self.detection_only = detection_only  # NEW
        
        # In-memory cache storage
        self._cache: Dict[str, CacheEntry] = {}
        
        # Statistics
        self._total_hits = 0
        self._total_misses = 0
        self._total_evictions = 0
        self._total_opportunities = 0  # NEW: Would-be hits in detection_only mode
        
        # Last metadata (for easy retrieval after set())
        self._last_metadata: Optional[CacheMetadata] = None
    
    # =========================================================================
    # CONFIGURATION
    # =========================================================================
    
    def configure_operation(
        self,
        operation: str,
        ttl: Optional[int] = None,
        normalize: Optional[bool] = None,
        cluster_id: Optional[str] = None,
    ) -> 'CacheManager':
        """
        Configure caching for an operation.
        
        Args:
            operation: Operation name
            ttl: Time-to-live in seconds
            normalize: Whether to normalize prompts
            cluster_id: Semantic cluster identifier
        
        Returns:
            Self for chaining
        """
        if operation not in self.operations:
            self.operations[operation] = {}
        
        if ttl is not None:
            self.operations[operation]['ttl'] = ttl
        if normalize is not None:
            self.operations[operation]['normalize'] = normalize
        if cluster_id is not None:
            self.operations[operation]['cluster_id'] = cluster_id
        
        return self
    
    def is_cacheable(self, operation: str) -> bool:
        """Check if operation is configured for caching."""
        return operation in self.operations
    
    # =========================================================================
    # CACHE KEY GENERATION
    # =========================================================================
    
    def _generate_cache_key(
        self,
        operation: str,
        key_data: Dict[str, Any],
        normalize: bool = True,
    ) -> str:
        """
        Generate a cache key from operation and key data.
        
        Args:
            operation: Operation name
            key_data: Dict of values to include in key
            normalize: Whether to normalize values
        
        Returns:
            Cache key string
        """
        # Build key components
        components = [operation]
        
        for k, v in sorted(key_data.items()):
            value_str = str(v)
            if normalize:
                value_str = self._normalize_text(value_str)
            components.append(f"{k}:{value_str}")
        
        # Create hash
        key_str = "|".join(components)
        hash_str = hashlib.md5(key_str.encode()).hexdigest()[:16]
        
        return f"{operation}:{hash_str}"
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for cache key generation.
        
        - Lowercase
        - Remove extra whitespace
        - Remove punctuation
        """
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s]', '', text)
        return text.strip()
    
    def _compute_content_hash(self, content: str) -> str:
        """Compute hash of content for deduplication (internal use)."""
        return compute_content_hash(content)
    
    # =========================================================================
    # CACHE OPERATIONS
    # =========================================================================
    
    def get(
        self,
        operation: str,
        key_data: Dict[str, Any],
        prompt: Optional[str] = None,
    ) -> Tuple[Optional[str], CacheMetadata]:
        """
        Get value from cache.
        
        DETECTION_ONLY MODE (baseline):
            - Checks for cache entry
            - Returns None (doesn't use cache)
            - Logs "💡 CACHE OPPORTUNITY (exact)" if found
            - Tracks opportunity metrics
        
        ACTIVE MODE (optimized):
            - Returns cached response if found
        
        Args:
            operation: Operation name
            key_data: Dict of values that form the cache key
            prompt: Optional prompt text for similarity tracking
        
        Returns:
            Tuple of (cached_value or None, CacheMetadata)
        """
        # Check if enabled
        if not self.enabled:
            metadata = self._create_metadata(
                cache_hit=False,
                cache_key=None,
                reason="Cache disabled"
            )
            return None, metadata
        
        # Check if operation is cacheable
        if not self.is_cacheable(operation):
            metadata = self._create_metadata(
                cache_hit=False,
                cache_key=None,
                reason="Operation not cacheable"
            )
            return None, metadata
        
        # Get operation config
        config = self.operations.get(operation, {})
        normalize = config.get('normalize', self.normalize_prompts)
        cluster_id = config.get('cluster_id', operation)
        
        # Generate cache key
        cache_key = self._generate_cache_key(operation, key_data, normalize)
        
        # Look up in cache
        entry = self._cache.get(cache_key)
        
        if entry is None:
            # Cache miss
            self._total_misses += 1
            metadata = self._create_metadata(
                cache_hit=False,
                cache_key=cache_key,
                cache_cluster_id=cluster_id,
                normalization_strategy="lowercase_strip" if normalize else None,
            )
            self._last_metadata = metadata
            return None, metadata
        
        # Check expiration
        if entry.expires_at and datetime.utcnow() > entry.expires_at:
            # Expired - remove and return miss
            del self._cache[cache_key]
            self._total_misses += 1
            metadata = self._create_metadata(
                cache_hit=False,
                cache_key=cache_key,
                cache_cluster_id=cluster_id,
                eviction_info="Expired",
            )
            self._last_metadata = metadata
            return None, metadata
        
        # Entry found and not expired
        content_hash = self._compute_content_hash(entry.value)
        ttl = config.get('ttl', self.default_ttl)
        
        # ═══════════════════════════════════════════════════════════════
        # NEW: DETECTION_ONLY MODE
        # ═══════════════════════════════════════════════════════════════
        if self.detection_only:
            # Track opportunity but don't return cached response
            self._total_opportunities += 1
            entry.hit_count += 1  # Track would-be hits
            
            logger.info(
                f"💡 CACHE OPPORTUNITY (exact match): {operation} [{cache_key[:8]}]"
            )
            
            metadata = self._create_metadata(
                cache_hit=False,  # Don't actually use cache
                cache_key=cache_key,
                cache_cluster_id=cluster_id,
                content_hash=content_hash,
                ttl_seconds=ttl,
                normalization_strategy="lowercase_strip" if normalize else None,
            )
            self._last_metadata = metadata
            return None, metadata  # Return None, not cached value
        
        # ═══════════════════════════════════════════════════════════════
        # ACTIVE MODE - Return cached response
        # ═══════════════════════════════════════════════════════════════
        self._total_hits += 1
        entry.hit_count += 1
        
        logger.info(
            f"✅ Cache HIT (exact match): {operation} [{cache_key[:8]}]"
        )
        
        metadata = self._create_metadata(
            cache_hit=True,
            cache_key=cache_key,
            cache_cluster_id=cluster_id,
            content_hash=content_hash,
            ttl_seconds=ttl,
        )
        self._last_metadata = metadata
        
        return entry.value, metadata
    
    def set(
        self,
        operation: str,
        key_data: Dict[str, Any],
        value: str,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CacheMetadata:
        """
        Store value in cache.
        
        Works in both detection_only and active modes - we need to store
        entries to detect future opportunities.
        
        Args:
            operation: Operation name
            key_data: Dict of values that form the cache key
            value: Value to cache
            ttl: Override TTL for this entry
            metadata: Additional metadata to store
        
        Returns:
            CacheMetadata for the operation
        """
        # Check if enabled
        if not self.enabled:
            cache_meta = self._create_metadata(
                cache_hit=False,
                reason="Cache disabled"
            )
            self._last_metadata = cache_meta
            return cache_meta
        
        # Check if operation is cacheable
        if not self.is_cacheable(operation):
            cache_meta = self._create_metadata(
                cache_hit=False,
                reason="Operation not cacheable"
            )
            self._last_metadata = cache_meta
            return cache_meta
        
        # Get operation config
        config = self.operations.get(operation, {})
        normalize = config.get('normalize', self.normalize_prompts)
        cluster_id = config.get('cluster_id', operation)
        entry_ttl = ttl or config.get('ttl', self.default_ttl)
        
        # Generate cache key
        cache_key = self._generate_cache_key(operation, key_data, normalize)
        
        # Evict if at capacity
        if len(self._cache) >= self.max_entries:
            self._evict_oldest()
        
        # Create entry
        now = datetime.utcnow()
        entry = CacheEntry(
            key=cache_key,
            value=value,
            created_at=now,
            expires_at=now + timedelta(seconds=entry_ttl) if entry_ttl > 0 else None,
            operation=operation,
            metadata=metadata or {},
        )
        
        self._cache[cache_key] = entry
        
        mode = "[detection]" if self.detection_only else ""
        logger.debug(f"Cache STORE {mode}: {operation} [{cache_key[:8]}]")
        
        cache_meta = self._create_metadata(
            cache_hit=False,  # This was a miss that we're now caching
            cache_key=cache_key,
            cache_cluster_id=cluster_id,
            content_hash=self._compute_content_hash(value),
            ttl_seconds=entry_ttl,
            normalization_strategy="lowercase_strip" if normalize else None,
        )
        self._last_metadata = cache_meta
        
        return cache_meta
    
    def invalidate(
        self,
        operation: Optional[str] = None,
        key_data: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Invalidate cache entries.
        
        Args:
            operation: If provided, invalidate only this operation
            key_data: If provided with operation, invalidate specific key
        
        Returns:
            Number of entries invalidated
        """
        if operation and key_data:
            # Invalidate specific entry
            config = self.operations.get(operation, {})
            normalize = config.get('normalize', self.normalize_prompts)
            cache_key = self._generate_cache_key(operation, key_data, normalize)
            
            if cache_key in self._cache:
                del self._cache[cache_key]
                return 1
            return 0
        
        elif operation:
            # Invalidate all entries for operation
            keys_to_remove = [
                k for k, v in self._cache.items()
                if v.operation == operation
            ]
            for k in keys_to_remove:
                del self._cache[k]
            return len(keys_to_remove)
        
        else:
            # Clear entire cache
            count = len(self._cache)
            self._cache.clear()
            return count
    
    def _evict_oldest(self):
        """Evict oldest entry from cache."""
        if not self._cache:
            return
        
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]
        self._total_evictions += 1
    
    # =========================================================================
    # METADATA CREATION
    # =========================================================================
    
    def _create_metadata(
        self,
        cache_hit: bool,
        cache_key: Optional[str] = None,
        cache_cluster_id: Optional[str] = None,
        similarity_score: Optional[float] = None,
        normalization_strategy: Optional[str] = None,
        eviction_info: Optional[str] = None,
        content_hash: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> CacheMetadata:
        """Create CacheMetadata object."""
        return CacheMetadata(
            cache_hit=cache_hit,
            cache_key=cache_key,
            cache_cluster_id=cache_cluster_id,
            similarity_score=similarity_score,
            normalization_strategy=normalization_strategy,
            eviction_info=eviction_info or reason,
            content_hash=content_hash,
            ttl_seconds=ttl_seconds,
        )
    
    @property
    def last_metadata(self) -> Optional[CacheMetadata]:
        """Get metadata from last get/set operation."""
        return self._last_metadata
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._total_hits + self._total_misses
        hit_rate = self._total_hits / total_requests if total_requests > 0 else 0
        opportunity_rate = self._total_opportunities / total_requests if total_requests > 0 else 0
        
        # Count by operation
        by_operation = {}
        for entry in self._cache.values():
            op = entry.operation
            if op not in by_operation:
                by_operation[op] = {"count": 0, "total_hits": 0}
            by_operation[op]["count"] += 1
            by_operation[op]["total_hits"] += entry.hit_count
        
        return {
            "enabled": self.enabled,
            "detection_only": self.detection_only,
            "total_entries": len(self._cache),
            "max_entries": self.max_entries,
            "total_hits": self._total_hits,
            "total_misses": self._total_misses,
            "total_opportunities": self._total_opportunities,
            "total_evictions": self._total_evictions,
            "hit_rate": round(hit_rate, 3),
            "hit_rate_pct": f"{hit_rate:.1%}",
            "opportunity_rate": round(opportunity_rate, 3),
            "opportunity_rate_pct": f"{opportunity_rate:.1%}",
            "by_operation": by_operation,
            "configured_operations": list(self.operations.keys()),
        }
    
    def reset_stats(self):
        """Reset statistics (does not clear cache)."""
        self._total_hits = 0
        self._total_misses = 0
        self._total_evictions = 0
        self._total_opportunities = 0
        for entry in self._cache.values():
            entry.hit_count = 0

# =============================================================================
# PREFIX CACHE DETECTOR
# =============================================================================

class PrefixCacheDetector:
    """
    Detects Azure/Anthropic prefix caching opportunities.
    
    Prefix caching: Azure and Anthropic cache your prompt prefix and charge
    ~50% less for cached tokens. Perfect for large system prompts.
    
    BASELINE MODE (detection_only=True):
        - Tracks same prompt prefix across calls
        - Calculates potential cost savings (~50% on cached prefix)
        - Logs opportunities
        - Does NOT actually use prefix caching API
    
    OPTIMIZED MODE (detection_only=False):
        - Same detection
        - Application code can use Azure/Anthropic prefix caching API
    
    Usage:
        detector = PrefixCacheDetector(
            observatory=obs,
            prefix_length=500,  # Track first 500 chars as prefix
            min_prefix_tokens=100,  # Minimum tokens to benefit from caching
            detection_only=True,
        )
        
        # Track each call
        detector.track_call(
            operation="quick_score_job",
            system_prompt="Your 11K token system prompt...",
            system_prompt_tokens=1555,
            call_id="call_123",
        )
        
        # Get stats
        stats = detector.get_stats()
    """
    
    def __init__(
        self,
        observatory: Optional['Observatory'] = None,
        prefix_length: int = 500,
        min_prefix_tokens: int = 100,
        enabled: bool = True,
        detection_only: bool = True,
    ):
        """
        Initialize PrefixCacheDetector.
        
        Args:
            observatory: Observatory instance
            prefix_length: Number of characters to consider as prefix
            min_prefix_tokens: Minimum tokens to qualify for prefix caching
            enabled: Whether detection is active
            detection_only: If True, only detect (don't apply caching)
        """
        self.observatory = observatory
        self.prefix_length = prefix_length
        self.min_prefix_tokens = min_prefix_tokens
        self.enabled = enabled
        self.detection_only = detection_only
        
        # Track prefix hashes: hash -> (full_prefix, token_count, call_count)
        self._prefix_registry: Dict[str, Dict[str, Any]] = {}
        
        # Statistics
        self._stats = {
            "unique_prefixes": 0,
            "cacheable_calls": 0,
            "potential_cost_savings": 0.0,
            "potential_cached_tokens": 0,
        }
    
    def track_call(
        self,
        operation: str = None,
        system_prompt: str = None,
        system_prompt_tokens: int = None,
        call_id: str = None,
        model: str = "gpt-4o-mini",
    ):
        """
        Track a call for prefix caching opportunities.
        
        Args:
            operation: Operation name
            system_prompt: System prompt text
            system_prompt_tokens: Token count of system prompt
            call_id: Call identifier
            model: Model name for cost calculation
        """
        if not self.enabled or not system_prompt:
            return
        
        # Check if prompt is large enough to benefit from prefix caching
        if system_prompt_tokens and system_prompt_tokens < self.min_prefix_tokens:
            return
        
        # Extract prefix and generate hash
        prefix = system_prompt[:self.prefix_length]
        prefix_hash = hashlib.md5(prefix.encode()).hexdigest()[:16]
        
        # Track this prefix
        if prefix_hash not in self._prefix_registry:
            self._prefix_registry[prefix_hash] = {
                "prefix": prefix,
                "token_count": system_prompt_tokens or 0,
                "call_count": 0,
                "operations": set(),
            }
            self._stats["unique_prefixes"] += 1
        
        # Increment call count
        self._prefix_registry[prefix_hash]["call_count"] += 1
        if operation:
            self._prefix_registry[prefix_hash]["operations"].add(operation)
        
        # If this is a repeat (call_count > 1), it's a caching opportunity
        if self._prefix_registry[prefix_hash]["call_count"] > 1:
            self._stats["cacheable_calls"] += 1
            
            # Calculate potential savings (~50% cost on cached tokens)
            cached_tokens = system_prompt_tokens or 0
            cost_per_token = self._get_cost_per_token(model)
            savings = cached_tokens * cost_per_token * 0.5  # 50% savings
            
            self._stats["potential_cost_savings"] += savings
            self._stats["potential_cached_tokens"] += cached_tokens
            
            logger.info(
                f"💡 PREFIX CACHE OPPORTUNITY: {operation or 'unknown'} "
                f"[{prefix_hash[:8]}] ({cached_tokens} tokens, ${savings:.4f} savings)"
            )
    
    def _get_cost_per_token(self, model: str) -> float:
        """Get cost per input token for model."""
        # Pricing per 1K tokens
        pricing = {
            "gpt-4o": 0.0025 / 1000,
            "gpt-4o-mini": 0.00015 / 1000,
            "gpt-4": 0.03 / 1000,
            "claude-sonnet-4": 0.003 / 1000,
            "claude-opus-4": 0.015 / 1000,
        }
        
        # Find matching model
        model_lower = model.lower()
        for key, cost in pricing.items():
            if key in model_lower:
                return cost
        
        # Default to gpt-4o-mini pricing
        return 0.00015 / 1000
    
    def get_stats(self) -> Dict[str, Any]:
        """Get prefix caching statistics."""
        total_calls = sum(p["call_count"] for p in self._prefix_registry.values())
        
        # Find most used prefix
        most_used = None
        if self._prefix_registry:
            most_used_hash = max(
                self._prefix_registry.keys(),
                key=lambda h: self._prefix_registry[h]["call_count"]
            )
            most_used = {
                "hash": most_used_hash[:8],
                "call_count": self._prefix_registry[most_used_hash]["call_count"],
                "token_count": self._prefix_registry[most_used_hash]["token_count"],
            }
        
        return {
            "enabled": self.enabled,
            "detection_only": self.detection_only,
            "prefix_length": self.prefix_length,
            "min_prefix_tokens": self.min_prefix_tokens,
            "unique_prefixes": self._stats["unique_prefixes"],
            "total_calls": total_calls,
            "cacheable_calls": self._stats["cacheable_calls"],
            "potential_cost_savings": round(self._stats["potential_cost_savings"], 4),
            "potential_cached_tokens": self._stats["potential_cached_tokens"],
            "most_used_prefix": most_used,
        }

# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def create_cache_metadata(
    cache_hit: bool,
    cache_key: Optional[str] = None,
    cache_cluster_id: Optional[str] = None,
    similarity_score: Optional[float] = None,
    normalization_strategy: Optional[str] = None,
    eviction_info: Optional[str] = None,
    cache_key_candidates: Optional[list] = None,
    dynamic_fields: Optional[list] = None,
    content_hash: Optional[str] = None,
    ttl_seconds: Optional[int] = None,
) -> CacheMetadata:
    """
    Convenience function to create CacheMetadata.
    
    Args:
        cache_hit: Whether this was a cache hit
        cache_key: The cache key used
        cache_cluster_id: Semantic cluster identifier
        similarity_score: Similarity to cached prompt (0-1)
        normalization_strategy: How prompt was normalized
        eviction_info: Why entry was evicted (if applicable)
        cache_key_candidates: Alternative keys considered
        dynamic_fields: Fields excluded from caching
        content_hash: Hash of cacheable content
        ttl_seconds: Time-to-live for cache entry
    
    Returns:
        CacheMetadata object
    """
    return CacheMetadata(
        cache_hit=cache_hit,
        cache_key=cache_key,
        cache_cluster_id=cache_cluster_id,
        similarity_score=similarity_score,
        normalization_strategy=normalization_strategy,
        eviction_info=eviction_info,
        cache_key_candidates=cache_key_candidates,
        dynamic_fields=dynamic_fields,
        content_hash=content_hash,
        ttl_seconds=ttl_seconds,
    )