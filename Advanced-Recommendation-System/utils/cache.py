"""
Simple in-memory cache with TTL support.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from config import CACHE_TTL

logger = logging.getLogger(__name__)


class Cache:
    """
    In-memory cache with time-to-live (TTL) support.
    
    Stores data with expiration timestamps. Used primarily for
    role TF-IDF computations that change infrequently.
    """
    
    def __init__(self):
        """Initialize empty cache."""
        self._cache = {}
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if exists and not expired, None otherwise
        """
        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now() < expiry:
                logger.debug(f"Cache HIT: {key}")
                return value
            else:
                # Expired - remove from cache
                del self._cache[key]
                logger.debug(f"Cache EXPIRED: {key}")
        
        logger.debug(f"Cache MISS: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: int = CACHE_TTL):
        """
        Store value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (default from config)
        """
        expiry = datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = (value, expiry)
        logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
    
    def clear(self):
        """Clear all cached data."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared ({count} entries removed)")
    
    def size(self) -> int:
        """Return number of cached entries."""
        return len(self._cache)


# Global cache instance
cache = Cache()
