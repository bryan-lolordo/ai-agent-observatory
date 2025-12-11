"""
Cache Manager - Caching with Observatory Tracking
Location: observatory/cache.py

Provides caching for LLM responses with automatic Observatory metadata tracking.
Applications configure which operations to cache and TTL settings.
"""

import hashlib
import re
import time
from typing import Optional, Dict, Any, Tuple, TYPE_CHECKING
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from observatory.models import CacheMetadata

if TYPE_CHECKING:
    from observatory.collector import Observatory


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
        cache = CacheManager(
            observatory=obs,
            operations={
                "find_jobs": {"ttl": 3600, "normalize": True},
                "query_database": {"ttl": 300},
            }
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
        """
        self.observatory = observatory
        self.operations = operations or {}
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self.normalize_prompts = normalize_prompts
        
        # In-memory cache storage
        self._cache: Dict[str, CacheEntry] = {}
        
        # Statistics
        self._total_hits = 0
        self._total_misses = 0
        self._total_evictions = 0
        
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
        """Compute hash of content for deduplication."""
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
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
        
        Args:
            operation: Operation name
            key_data: Dict of values that form the cache key
            prompt: Optional prompt text for similarity tracking
        
        Returns:
            Tuple of (cached_value or None, CacheMetadata)
        """
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
        
        # Cache hit!
        self._total_hits += 1
        entry.hit_count += 1
        
        metadata = self._create_metadata(
            cache_hit=True,
            cache_key=cache_key,
            cache_cluster_id=cluster_id,
            content_hash=self._compute_content_hash(entry.value),
            ttl_seconds=config.get('ttl', self.default_ttl),
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
        
        Args:
            operation: Operation name
            key_data: Dict of values that form the cache key
            value: Value to cache
            ttl: Override TTL for this entry
            metadata: Additional metadata to store
        
        Returns:
            CacheMetadata for the operation
        """
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
        
        # Count by operation
        by_operation = {}
        for entry in self._cache.values():
            op = entry.operation
            if op not in by_operation:
                by_operation[op] = {"count": 0, "total_hits": 0}
            by_operation[op]["count"] += 1
            by_operation[op]["total_hits"] += entry.hit_count
        
        return {
            "total_entries": len(self._cache),
            "max_entries": self.max_entries,
            "total_hits": self._total_hits,
            "total_misses": self._total_misses,
            "total_evictions": self._total_evictions,
            "hit_rate": round(hit_rate, 3),
            "by_operation": by_operation,
            "configured_operations": list(self.operations.keys()),
        }
    
    def reset_stats(self):
        """Reset statistics (does not clear cache)."""
        self._total_hits = 0
        self._total_misses = 0
        self._total_evictions = 0
        for entry in self._cache.values():
            entry.hit_count = 0


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