"""
Redis Client for Caching and Session Management
"""
import redis
import json
import logging
from typing import Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Create Redis client
redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5
)


def cache_api_response(key: str, data: Any, expiry: int = 300) -> bool:
    """
    Cache API response in Redis

    Args:
        key: Cache key
        data: Data to cache (will be JSON serialized)
        expiry: Expiry time in seconds (default 5 minutes)

    Returns:
        True if successful, False otherwise
    """
    try:
        serialized = json.dumps(data)
        redis_client.setex(key, expiry, serialized)
        logger.debug(f"Cached data with key: {key} (expires in {expiry}s)")
        return True
    except Exception as e:
        logger.error(f"Failed to cache data: {e}")
        return False


def get_api_response(key: str) -> Optional[Any]:
    """
    Get cached API response from Redis

    Args:
        key: Cache key

    Returns:
        Cached data if found, None otherwise
    """
    try:
        cached = redis_client.get(key)
        if cached:
            logger.debug(f"Cache hit for key: {key}")
            return json.loads(cached)
        logger.debug(f"Cache miss for key: {key}")
        return None
    except Exception as e:
        logger.error(f"Failed to get cached data: {e}")
        return None


def invalidate_cache(pattern: str) -> int:
    """
    Invalidate cache entries matching a pattern

    Args:
        pattern: Redis key pattern (e.g., "api:images:user:1:*")

    Returns:
        Number of keys deleted
    """
    try:
        keys = redis_client.keys(pattern)
        if keys:
            deleted = redis_client.delete(*keys)
            logger.info(f"Invalidated {deleted} cache entries matching: {pattern}")
            return deleted
        return 0
    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}")
        return 0


def invalidate_user_cache(user_id: int) -> int:
    """
    Invalidate all cache entries for a specific user

    Args:
        user_id: User ID

    Returns:
        Number of keys deleted
    """
    pattern = f"api:*:user:{user_id}:*"
    return invalidate_cache(pattern)


def check_redis_connection() -> bool:
    """
    Check if Redis is available

    Returns:
        True if connected, False otherwise
    """
    try:
        redis_client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return False


def get_task_status(task_id: str) -> Optional[dict]:
    """
    Get Celery task status from Redis

    Args:
        task_id: Celery task ID

    Returns:
        Task status dict or None
    """
    try:
        key = f"celery-task-meta-{task_id}"
        status = redis_client.get(key)
        if status:
            return json.loads(status)
        return None
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        return None
