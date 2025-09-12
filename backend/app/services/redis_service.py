"""
Redis service for caching and session management
Supports both local Redis and Upstash Redis
"""

import redis
import json
from typing import Optional, Dict, Any
from app.config.base import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RedisService:
    def __init__(self):
        # Check if Upstash Redis is configured
        if settings.UPSTASH_REDIS_REST_URL and settings.UPSTASH_REDIS_REST_TOKEN:
            try:
                from upstash_redis import Redis
                self.redis_client = Redis(
                    url=settings.UPSTASH_REDIS_REST_URL,
                    token=settings.UPSTASH_REDIS_REST_TOKEN
                )
                self.is_upstash = True
                logger.info("Using Upstash Redis")
            except ImportError:
                logger.warning("upstash-redis not installed, falling back to local Redis")
                self._init_local_redis()
        else:
            self._init_local_redis()
    
    def _init_local_redis(self):
        """Initialize local Redis connection"""
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        self.is_upstash = False
        logger.info("Using local Redis")

    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        try:
            if self.is_upstash:
                # Upstash Redis returns bytes, convert to string if needed
                result = self.redis_client.get(key)
                return result.decode('utf-8') if isinstance(result, bytes) else result
            else:
                return self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Redis GET failed for key {key}: {str(e)}")
            return None

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set key-value pair with optional expiration"""
        try:
            if self.is_upstash:
                if expire:
                    return bool(self.redis_client.setex(key, expire, value))
                else:
                    return bool(self.redis_client.set(key, value))
            else:
                return self.redis_client.set(key, value, ex=expire)
        except Exception as e:
            logger.error(f"Redis SET failed for key {key}: {str(e)}")
            return False

    async def get_json(self, key: str) -> Optional[Dict]:
        """Get JSON object by key"""
        try:
            if self.is_upstash:
                value = self.redis_client.get(key)
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
            else:
                value = self.redis_client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Redis GET JSON failed for key {key}: {str(e)}")
            return None

    async def set_json(self, key: str, value: Dict, expire: Optional[int] = None) -> bool:
        """Set JSON object with optional expiration"""
        try:
            json_value = json.dumps(value)
            if self.is_upstash:
                if expire:
                    return bool(self.redis_client.setex(key, expire, json_value))
                else:
                    return bool(self.redis_client.set(key, json_value))
            else:
                return self.redis_client.set(key, json_value, ex=expire)
        except Exception as e:
            logger.error(f"Redis SET JSON failed for key {key}: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key"""
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Redis DELETE failed for key {key}: {str(e)}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS failed for key {key}: {str(e)}")
            return False

    async def cache_analysis_result(self, analysis_id: str, result: Dict, expire: int = 3600) -> bool:
        """Cache analysis result"""
        cache_key = f"analysis:{analysis_id}"
        return await self.set_json(cache_key, result, expire)

    async def get_cached_analysis(self, analysis_id: str) -> Optional[Dict]:
        """Get cached analysis result"""
        cache_key = f"analysis:{analysis_id}"
        return await self.get_json(cache_key)


redis_service = RedisService()
