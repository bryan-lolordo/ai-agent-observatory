# observatory/semantic_cache.py
"""
Semantic Cache - Vector Similarity Caching for LLM Responses
Location: observatory/semantic_cache.py

Provides semantic (meaning-based) caching using vector embeddings.
Unlike CacheManager (exact match), SemanticCache finds similar prompts
even when wording differs.

Comparison:
    CacheManager (exact match):
        "Find Python jobs in NYC" → cached
        "Find Python jobs in NYC" → HIT ✅
        "Search for Python positions in New York" → MISS ❌

    SemanticCache (semantic match):
        "Find Python jobs in NYC" → cached with embedding
        "Search for Python positions in New York" → HIT ✅ (92% similar)
        "Find data scientist roles in Boston" → MISS ❌ (different meaning)

Usage in observatory_config.py:
    from observatory import Observatory, SemanticCache
    
    obs = Observatory(project_name="My App")
    
    semantic_cache = SemanticCache(
        observatory=obs,
        operations={
            "generate_sql": {"ttl": 86400, "threshold": 0.95},
            "quick_score_job": {"ttl": 3600, "threshold": 0.90},
        },
        default_threshold=0.92,
        enabled=True,
    )

Usage in application code:
    from observatory_config import semantic_cache, track_llm_call, create_cache_metadata
    
    # Check cache before LLM call
    result = await semantic_cache.get(prompt, operation="generate_sql")
    
    if result.hit:
        # Use cached response, track as cache hit
        cache_metadata = create_cache_metadata(
            cache_hit=True,
            cache_key=result.cache_key,
            similarity_score=result.similarity,
        )
        return result.response
    
    # Cache miss - call LLM
    response = await llm.complete(prompt)
    
    # Store for future
    await semantic_cache.set(prompt, response, operation="generate_sql")

Installation:
    pip install chromadb
"""

import os
import hashlib
import logging
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from observatory.models import CacheMetadata

if TYPE_CHECKING:
    from observatory.collector import Observatory

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SemanticCacheResult:
    """
    Result from a semantic cache lookup.
    
    Attributes:
        hit: Whether a cache hit occurred
        response: Cached response text (if hit)
        cache_key: Cache entry identifier
        similarity: Similarity score (0.0-1.0)
        stored_at: When the entry was cached
        operation: Operation that created the entry
        metadata: Additional stored metadata
    """
    hit: bool
    response: Optional[str] = None
    cache_key: Optional[str] = None
    similarity: Optional[float] = None
    stored_at: Optional[str] = None
    operation: Optional[str] = None
    original_prompt: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __bool__(self):
        """Allow `if result:` syntax."""
        return self.hit
    
    def to_cache_metadata(self, cluster_id: str = None) -> CacheMetadata:
        """Convert to CacheMetadata for Observatory tracking."""
        return CacheMetadata(
            cache_hit=self.hit,
            cache_key=self.cache_key,
            cache_cluster_id=cluster_id or self.operation,
            similarity_score=self.similarity,
            normalization_strategy="semantic_embedding",
        )


# =============================================================================
# OPERATION CONFIG
# =============================================================================

@dataclass
class SemanticCacheOperationConfig:
    """Configuration for a cached operation."""
    ttl: int = 3600  # Time-to-live in seconds
    threshold: float = 0.92  # Similarity threshold (0.0-1.0)
    cluster_id: Optional[str] = None  # For grouping in analytics
    enabled: bool = True


# =============================================================================
# SEMANTIC CACHE
# =============================================================================

class SemanticCache:
    """
    Semantic cache using vector similarity for LLM response caching.
    
    Uses ChromaDB for vector storage and similarity search. Integrates
    with Observatory for cache hit/miss tracking via CacheMetadata.
    
    Args:
        observatory: Observatory instance for metrics integration
        operations: Dict of operation → config
            Config options: ttl (seconds), threshold (0.0-1.0), cluster_id (str)
        default_ttl: Default time-to-live in seconds (default: 3600)
        default_threshold: Default similarity threshold (default: 0.92)
        db_path: Path to ChromaDB storage (default: derived from project)
        collection_name: ChromaDB collection name (default: derived from project)
        enabled: Whether caching is active (default: True)
    
    Example:
        semantic_cache = SemanticCache(
            observatory=obs,
            operations={
                "generate_sql": {"ttl": 86400, "threshold": 0.95},
                "summarize": {"ttl": 3600, "threshold": 0.85},
            },
        )
        
        # Check cache
        result = await semantic_cache.get(prompt, "generate_sql")
        if result.hit:
            return result.response
        
        # Store after LLM call
        await semantic_cache.set(prompt, response, "generate_sql")
    """
    
    def __init__(
        self,
        observatory: Optional['Observatory'] = None,
        operations: Optional[Dict[str, Dict[str, Any]]] = None,
        default_ttl: int = 3600,
        default_threshold: float = 0.92,
        db_path: Optional[str] = None,
        collection_name: Optional[str] = None,
        enabled: bool = True,
    ):
        self.observatory = observatory
        self.default_ttl = default_ttl
        self.default_threshold = default_threshold
        self.enabled = enabled
        
        # Parse operation configs
        self.operations: Dict[str, SemanticCacheOperationConfig] = {}
        if operations:
            for op_name, config in operations.items():
                self.operations[op_name] = SemanticCacheOperationConfig(
                    ttl=config.get('ttl', default_ttl),
                    threshold=config.get('threshold', default_threshold),
                    cluster_id=config.get('cluster_id', op_name),
                    enabled=config.get('enabled', True),
                )
        
        # Derive paths from observatory
        project_name = "default"
        if observatory and hasattr(observatory, 'project_name'):
            project_name = observatory.project_name.lower().replace(" ", "_")
        
        self.db_path = db_path or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "observatory_cache", project_name)
        )
        self.collection_name = collection_name or f"semantic_cache_{project_name}"
        
        # ChromaDB client (lazy initialization)
        self._client = None
        self._collection = None
        self._initialized = False
        
        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "stores": 0,
            "errors": 0,
            "by_operation": {},
        }
        
        # Initialize if enabled
        if enabled:
            self._initialize()
    
    # =========================================================================
    # INITIALIZATION
    # =========================================================================
    
    def _initialize(self) -> bool:
        """Initialize ChromaDB client and collection."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Ensure directory exists
            os.makedirs(self.db_path, exist_ok=True)
            
            # Create persistent client
            self._client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "description": "Observatory semantic cache",
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
            
            self._initialized = True
            count = self._collection.count()
            logger.info(f"✅ SemanticCache initialized: {count} entries in {self.collection_name}")
            return True
            
        except ImportError:
            logger.warning(
                "⚠️ ChromaDB not installed. SemanticCache disabled. "
                "Install with: pip install chromadb"
            )
            self.enabled = False
            return False
            
        except Exception as e:
            logger.error(f"❌ SemanticCache initialization failed: {e}")
            self.enabled = False
            self._stats["errors"] += 1
            return False
    
    # =========================================================================
    # CONFIGURATION
    # =========================================================================
    
    def configure_operation(
        self,
        operation: str,
        ttl: Optional[int] = None,
        threshold: Optional[float] = None,
        cluster_id: Optional[str] = None,
        enabled: bool = True,
    ) -> 'SemanticCache':
        """
        Configure caching for an operation.
        
        Args:
            operation: Operation name
            ttl: Time-to-live in seconds
            threshold: Similarity threshold (0.0-1.0)
            cluster_id: Cluster identifier for analytics
            enabled: Whether caching is enabled for this operation
        
        Returns:
            Self for chaining
        """
        if operation not in self.operations:
            self.operations[operation] = SemanticCacheOperationConfig()
        
        config = self.operations[operation]
        if ttl is not None:
            config.ttl = ttl
        if threshold is not None:
            config.threshold = threshold
        if cluster_id is not None:
            config.cluster_id = cluster_id
        config.enabled = enabled
        
        return self
    
    def is_cacheable(self, operation: str) -> bool:
        """Check if operation is configured for caching."""
        if operation not in self.operations:
            return False
        return self.operations[operation].enabled
    
    # =========================================================================
    # CACHE KEY GENERATION
    # =========================================================================
    
    def _generate_id(self, prompt: str, operation: str) -> str:
        """Generate a unique ID for a cache entry."""
        content = f"{operation}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    # =========================================================================
    # EXPIRATION CHECK
    # =========================================================================
    
    def _is_expired(self, metadata: dict, operation: str) -> bool:
        """Check if a cache entry has expired."""
        stored_at = metadata.get("stored_at")
        if not stored_at:
            return True
        
        config = self.operations.get(operation, SemanticCacheOperationConfig())
        ttl = config.ttl
        
        try:
            stored_time = datetime.fromisoformat(stored_at)
            return datetime.utcnow() - stored_time > timedelta(seconds=ttl)
        except (ValueError, TypeError):
            return True
    
    # =========================================================================
    # CACHE OPERATIONS
    # =========================================================================
    
    async def get(
        self,
        prompt: str,
        operation: str,
        threshold: Optional[float] = None,
    ) -> SemanticCacheResult:
        """
        Check if a similar prompt exists in cache.
        
        Args:
            prompt: The prompt to search for
            operation: Operation name (e.g., "generate_sql")
            threshold: Override similarity threshold (optional)
        
        Returns:
            SemanticCacheResult with hit status and cached response
        """
        # Check if enabled and initialized
        if not self.enabled or not self._collection:
            return SemanticCacheResult(hit=False)
        
        # Check if operation is cacheable
        if not self.is_cacheable(operation):
            self._update_stats(operation, hit=False)
            return SemanticCacheResult(hit=False, operation=operation)
        
        config = self.operations.get(operation, SemanticCacheOperationConfig())
        threshold = threshold or config.threshold
        
        try:
            # Query for similar prompts
            results = self._collection.query(
                query_texts=[prompt],
                n_results=1,
                where={"operation": operation}
            )
            
            # Check if we got results
            if not results or not results['ids'] or not results['ids'][0]:
                self._update_stats(operation, hit=False)
                return SemanticCacheResult(hit=False, operation=operation)
            
            # Get similarity score
            # ChromaDB returns L2 distances; convert to similarity
            distance = results['distances'][0][0]
            similarity = max(0.0, 1.0 - (distance / 2.0))
            
            # Check threshold
            if similarity < threshold:
                self._update_stats(operation, hit=False)
                logger.debug(
                    f"Cache MISS (similarity {similarity:.3f} < {threshold}): {operation}"
                )
                return SemanticCacheResult(
                    hit=False,
                    operation=operation,
                    similarity=similarity,
                )
            
            # Get metadata and check expiration
            metadata = results['metadatas'][0][0] if results['metadatas'] else {}
            
            if self._is_expired(metadata, operation):
                self._update_stats(operation, hit=False)
                # Delete expired entry
                self._collection.delete(ids=[results['ids'][0][0]])
                logger.debug(f"Cache MISS (expired): {operation}")
                return SemanticCacheResult(hit=False, operation=operation)
            
            # Cache hit!
            self._update_stats(operation, hit=True)
            cache_key = results['ids'][0][0]
            response = metadata.get("response", "")
            original_prompt = results['documents'][0][0] if results['documents'] else None
            
            logger.info(
                f"✅ Cache HIT ({similarity:.1%} similar): {operation} [{cache_key[:8]}]"
            )
            
            return SemanticCacheResult(
                hit=True,
                response=response,
                cache_key=cache_key,
                similarity=similarity,
                stored_at=metadata.get("stored_at"),
                operation=operation,
                original_prompt=original_prompt,
                metadata=metadata,
            )
            
        except Exception as e:
            logger.error(f"SemanticCache get error: {e}")
            self._stats["errors"] += 1
            return SemanticCacheResult(hit=False, operation=operation)
    
    async def set(
        self,
        prompt: str,
        response: str,
        operation: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Store a prompt-response pair in the cache.
        
        Args:
            prompt: The prompt that was sent to the LLM
            response: The LLM's response
            operation: Operation name (e.g., "generate_sql")
            metadata: Additional metadata to store
        
        Returns:
            Cache key (ID) of the stored entry, or None if failed
        """
        if not self.enabled or not self._collection:
            return None
        
        if not self.is_cacheable(operation):
            return None
        
        try:
            cache_id = self._generate_id(prompt, operation)
            config = self.operations.get(operation, SemanticCacheOperationConfig())
            
            # Build metadata
            entry_metadata = {
                "operation": operation,
                "response": response[:50000],  # Limit response size
                "stored_at": datetime.utcnow().isoformat(),
                "prompt_length": len(prompt),
                "response_length": len(response),
                "ttl_seconds": config.ttl,
                "cluster_id": config.cluster_id,
            }
            
            # Add custom metadata (only serializable values)
            if metadata:
                for k, v in metadata.items():
                    if isinstance(v, (str, int, float, bool)):
                        entry_metadata[k] = v
            
            # Upsert (add or update)
            self._collection.upsert(
                ids=[cache_id],
                documents=[prompt],
                metadatas=[entry_metadata]
            )
            
            self._stats["stores"] += 1
            logger.debug(f"Cache STORE: {operation} [{cache_id[:8]}]")
            
            return cache_id
            
        except Exception as e:
            logger.error(f"SemanticCache set error: {e}")
            self._stats["errors"] += 1
            return None
    
    # =========================================================================
    # SYNC VERSIONS (for non-async contexts)
    # =========================================================================
    
    def get_sync(
        self,
        prompt: str,
        operation: str,
        threshold: Optional[float] = None,
    ) -> SemanticCacheResult:
        """Synchronous version of get()."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.get(prompt, operation, threshold))
    
    def set_sync(
        self,
        prompt: str,
        response: str,
        operation: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Synchronous version of set()."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.set(prompt, response, operation, metadata))
    
    # =========================================================================
    # CACHE MANAGEMENT
    # =========================================================================
    
    def invalidate(
        self,
        operation: Optional[str] = None,
        cache_key: Optional[str] = None,
    ) -> int:
        """
        Invalidate cache entries.
        
        Args:
            operation: If provided, invalidate all entries for this operation
            cache_key: If provided, invalidate specific entry
        
        Returns:
            Number of entries invalidated
        """
        if not self._collection:
            return 0
        
        try:
            if cache_key:
                # Delete specific entry
                self._collection.delete(ids=[cache_key])
                return 1
            
            elif operation:
                # Delete all entries for operation
                results = self._collection.get(where={"operation": operation})
                if results and results['ids']:
                    self._collection.delete(ids=results['ids'])
                    count = len(results['ids'])
                    logger.info(f"Invalidated {count} cache entries for {operation}")
                    return count
                return 0
            
            else:
                # Clear entire collection
                count = self._collection.count()
                self._client.delete_collection(self.collection_name)
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"description": "Observatory semantic cache"}
                )
                logger.info(f"Cleared all {count} cache entries")
                return count
                
        except Exception as e:
            logger.error(f"SemanticCache invalidate error: {e}")
            self._stats["errors"] += 1
            return 0
    
    def clear(self, operation: Optional[str] = None) -> int:
        """Alias for invalidate() for consistency with CacheManager."""
        return self.invalidate(operation=operation)
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def _update_stats(self, operation: str, hit: bool):
        """Update cache statistics."""
        if hit:
            self._stats["hits"] += 1
        else:
            self._stats["misses"] += 1
        
        if operation not in self._stats["by_operation"]:
            self._stats["by_operation"][operation] = {"hits": 0, "misses": 0}
        
        if hit:
            self._stats["by_operation"][operation]["hits"] += 1
        else:
            self._stats["by_operation"][operation]["misses"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0.0
        
        # Calculate per-operation hit rates
        by_operation = {}
        for op, stats in self._stats["by_operation"].items():
            op_total = stats["hits"] + stats["misses"]
            by_operation[op] = {
                "hits": stats["hits"],
                "misses": stats["misses"],
                "hit_rate": stats["hits"] / op_total if op_total > 0 else 0.0,
            }
        
        return {
            "enabled": self.enabled,
            "initialized": self._initialized,
            "total_entries": self._collection.count() if self._collection else 0,
            "total_hits": self._stats["hits"],
            "total_misses": self._stats["misses"],
            "total_stores": self._stats["stores"],
            "total_errors": self._stats["errors"],
            "hit_rate": round(hit_rate, 3),
            "hit_rate_pct": f"{hit_rate:.1%}",
            "by_operation": by_operation,
            "configured_operations": list(self.operations.keys()),
            "db_path": self.db_path,
            "collection_name": self.collection_name,
        }
    
    def reset_stats(self):
        """Reset statistics (does not clear cache)."""
        self._stats = {
            "hits": 0,
            "misses": 0,
            "stores": 0,
            "errors": 0,
            "by_operation": {},
        }


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

def create_semantic_cache_metadata(
    result: SemanticCacheResult,
    cluster_id: Optional[str] = None,
) -> CacheMetadata:
    """
    Create CacheMetadata from a SemanticCacheResult.
    
    Args:
        result: SemanticCacheResult from get() call
        cluster_id: Override cluster ID
    
    Returns:
        CacheMetadata for use with track_llm_call()
    """
    return CacheMetadata(
        cache_hit=result.hit,
        cache_key=result.cache_key,
        cache_cluster_id=cluster_id or result.operation,
        similarity_score=result.similarity,
        normalization_strategy="semantic_embedding",
    )