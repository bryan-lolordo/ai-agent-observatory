"""
Cache Layer for LLM Calls

Detects duplicate calls and returns cached responses to save costs.
Tracks cache hit rates and provides analytics.
"""

import hashlib
import json
import time
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


class CacheEntry:
    """Represents a cached LLM response."""
    
    def __init__(
        self,
        response: str,
        prompt_tokens: int,
        completion_tokens: int,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.response = response
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.hit_count = 0
        self.last_accessed = datetime.utcnow()
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if cache entry has expired."""
        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age > ttl_seconds
    
    def record_hit(self):
        """Record a cache hit."""
        self.hit_count += 1
        self.last_accessed = datetime.utcnow()


class CacheLayer:
    """
    In-memory cache for LLM responses.
    
    Features:
    - Content-based hashing (same prompt + model = same hash)
    - TTL (time-to-live) expiration
    - Hit rate tracking
    - Cost savings calculation
    """
    
    def __init__(
        self,
        enabled: bool = True,
        ttl_seconds: int = 3600,  # 1 hour default
        max_entries: int = 1000,
    ):
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        
        # Storage
        self._cache: Dict[str, CacheEntry] = {}
        
        # Metrics
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_tokens_saved = 0
        self.total_cost_saved = 0.0
    
    def _generate_cache_key(
        self,
        model: str,
        messages: list,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a unique cache key based on request parameters.
        
        Note: Only deterministic calls (temperature=0) should be cached.
        """
        # Create a deterministic representation
        cache_input = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        # Hash it
        cache_json = json.dumps(cache_input, sort_keys=True)
        cache_hash = hashlib.sha256(cache_json.encode()).hexdigest()
        
        return cache_hash
    
    def get(
        self,
        model: str,
        messages: list,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> Optional[CacheEntry]:
        """
        Try to get a cached response.
        
        Returns None if not found or expired.
        """
        if not self.enabled:
            return None
        
        # Don't cache non-deterministic calls
        if temperature > 0:
            return None
        
        self.total_requests += 1
        
        cache_key = self._generate_cache_key(model, messages, temperature, max_tokens)
        
        # Check if in cache
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            
            # Check if expired
            if entry.is_expired(self.ttl_seconds):
                del self._cache[cache_key]
                self.cache_misses += 1
                return None
            
            # Cache hit!
            entry.record_hit()
            self.cache_hits += 1
            
            # Track savings
            self.total_tokens_saved += entry.prompt_tokens + entry.completion_tokens
            
            return entry
        
        # Cache miss
        self.cache_misses += 1
        return None
    
    def set(
        self,
        model: str,
        messages: list,
        response: str,
        prompt_tokens: int,
        completion_tokens: int,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Store a response in the cache."""
        if not self.enabled:
            return
        
        # Don't cache non-deterministic calls
        if temperature > 0:
            return
        
        cache_key = self._generate_cache_key(model, messages, temperature, max_tokens)
        
        # Evict oldest if at capacity
        if len(self._cache) >= self.max_entries:
            self._evict_oldest()
        
        # Store entry
        entry = CacheEntry(
            response=response,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            metadata=metadata,
        )
        
        self._cache[cache_key] = entry
    
    def _evict_oldest(self):
        """Remove the least recently used entry."""
        if not self._cache:
            return
        
        # Find oldest entry
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        
        del self._cache[oldest_key]
    
    def clear(self):
        """Clear all cached entries."""
        self._cache.clear()
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_tokens_saved = 0
        self.total_cost_saved = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        hit_rate = self.cache_hits / self.total_requests if self.total_requests > 0 else 0
        
        return {
            "enabled": self.enabled,
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": hit_rate,
            "cached_entries": len(self._cache),
            "max_entries": self.max_entries,
            "ttl_seconds": self.ttl_seconds,
            "total_tokens_saved": self.total_tokens_saved,
            "total_cost_saved": self.total_cost_saved,
        }
    
    def estimate_cost_savings(self, cost_per_token: float = 0.00003) -> float:
        """
        Estimate cost savings from caching.
        
        Args:
            cost_per_token: Average cost per token (default: ~GPT-4 pricing)
        """
        self.total_cost_saved = self.total_tokens_saved * cost_per_token
        return self.total_cost_saved