"""
Redis caching configuration and utilities for NexCompli.

This module provides caching functionality to improve API performance by caching
frequently accessed data like evidence statistics, framework information, and
user dashboard data.
"""

import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from config.logging_config import get_logger

logger = get_logger(__name__)


class CacheManager:
    """
    Async Redis cache manager with fallback to in-memory caching.

    Provides caching for:
    - Evidence statistics and dashboard data
    - Framework information
    - User business profiles
    - API response data
    """

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_enabled = True
        self.default_ttl = 300  # 5 minutes default TTL

    async def initialize(self):
        """Initialize Redis connection with fallback to memory cache."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using in-memory cache fallback")
            return

        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)

            # Test connection
            await self.redis_client.ping()
            logger.info("Redis cache initialized successfully")

        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory cache fallback")
            self.redis_client = None

    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate a consistent cache key from prefix and parameters."""
        # Sort kwargs for consistent key generation
        sorted_params = sorted(kwargs.items())
        params_str = "&".join([f"{k}={v}" for k, v in sorted_params])

        # Create hash for long parameter strings
        if len(params_str) > 100:
            params_hash = hashlib.md5(params_str.encode()).hexdigest()
            return f"{prefix}:{params_hash}"

        return f"{prefix}:{params_str}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (Redis or memory fallback)."""
        if not self.cache_enabled:
            return None

        try:
            if self.redis_client:
                # Try Redis first
                value = await self.redis_client.get(key)
                if value:
                    return json.loads(value)
            else:
                # Fallback to memory cache
                cache_entry = self.memory_cache.get(key)
                if cache_entry:
                    # Check if expired
                    if datetime.utcnow() < cache_entry["expires_at"]:
                        return cache_entry["value"]
                    else:
                        # Remove expired entry
                        del self.memory_cache[key]

        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")

        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with TTL."""
        if not self.cache_enabled:
            return False

        ttl = ttl or self.default_ttl

        try:
            if self.redis_client:
                # Use Redis
                serialized_value = json.dumps(value, default=str)
                await self.redis_client.setex(key, ttl, serialized_value)
                return True
            else:
                # Use memory cache
                expires_at = datetime.utcnow() + timedelta(seconds=ttl)
                self.memory_cache[key] = {"value": value, "expires_at": expires_at}
                return True

        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            if self.redis_client:
                await self.redis_client.delete(key)
            else:
                self.memory_cache.pop(key, None)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        try:
            if self.redis_client:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                return len(keys)
            else:
                # Memory cache pattern matching
                keys_to_delete = [k for k in self.memory_cache if pattern.replace("*", "") in k]
                for key in keys_to_delete:
                    del self.memory_cache[key]
                return len(keys_to_delete)
        except Exception as e:
            logger.warning(f"Cache clear pattern error for {pattern}: {e}")
            return 0

    # High-level caching methods for specific data types

    async def get_evidence_statistics(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached evidence statistics for a user."""
        key = self._generate_cache_key("evidence_stats", user_id=user_id)
        return await self.get(key)

    async def set_evidence_statistics(
        self, user_id: str, stats: Dict[str, Any], ttl: int = 600
    ) -> bool:
        """Cache evidence statistics for a user (10 min TTL)."""
        key = self._generate_cache_key("evidence_stats", user_id=user_id)
        return await self.set(key, stats, ttl)

    async def get_evidence_dashboard(
        self, user_id: str, framework_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached evidence dashboard data."""
        key = self._generate_cache_key(
            "evidence_dashboard", user_id=user_id, framework_id=framework_id
        )
        return await self.get(key)

    async def set_evidence_dashboard(
        self, user_id: str, framework_id: str, dashboard_data: Dict[str, Any], ttl: int = 300
    ) -> bool:
        """Cache evidence dashboard data (5 min TTL)."""
        key = self._generate_cache_key(
            "evidence_dashboard", user_id=user_id, framework_id=framework_id
        )
        return await self.set(key, dashboard_data, ttl)

    async def get_framework_info(self, framework_id: str) -> Optional[Dict[str, Any]]:
        """Get cached framework information."""
        key = self._generate_cache_key("framework_info", framework_id=framework_id)
        return await self.get(key)

    async def set_framework_info(
        self, framework_id: str, framework_data: Dict[str, Any], ttl: int = 3600
    ) -> bool:
        """Cache framework information (1 hour TTL)."""
        key = self._generate_cache_key("framework_info", framework_id=framework_id)
        return await self.set(key, framework_data, ttl)

    async def get_business_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached business profile."""
        key = self._generate_cache_key("business_profile", user_id=user_id)
        return await self.get(key)

    async def set_business_profile(
        self, user_id: str, profile_data: Dict[str, Any], ttl: int = 1800
    ) -> bool:
        """Cache business profile (30 min TTL)."""
        key = self._generate_cache_key("business_profile", user_id=user_id)
        return await self.set(key, profile_data, ttl)

    async def invalidate_user_cache(self, user_id: str) -> int:
        """Invalidate all cache entries for a user."""
        patterns = [
            f"evidence_stats:*user_id={user_id}*",
            f"evidence_dashboard:*user_id={user_id}*",
            f"business_profile:*user_id={user_id}*",
        ]

        total_cleared = 0
        for pattern in patterns:
            total_cleared += await self.clear_pattern(pattern)

        logger.info(f"Invalidated {total_cleared} cache entries for user {user_id}")
        return total_cleared

    async def cleanup_expired_memory_cache(self):
        """Clean up expired entries from memory cache."""
        if self.redis_client:
            return  # Redis handles expiration automatically

        now = datetime.utcnow()
        expired_keys = [
            key for key, entry in self.memory_cache.items() if now >= entry["expires_at"]
        ]

        for key in expired_keys:
            del self.memory_cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


# Global cache manager instance
cache_manager = CacheManager()


async def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    if cache_manager.redis_client is None and REDIS_AVAILABLE:
        await cache_manager.initialize()
    return cache_manager


# Decorator for caching function results
def cache_result(ttl: int = 300, key_prefix: str = "func"):
    """
    Decorator to cache function results.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            cache = await get_cache_manager()

            # Generate cache key from function name and arguments
            func_name = f"{func.__module__}.{func.__name__}"
            cache_key = cache._generate_cache_key(
                f"{key_prefix}:{func_name}", args=str(args), kwargs=str(sorted(kwargs.items()))
            )

            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator
