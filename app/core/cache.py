from typing import Any, Optional
import json

import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


class CacheService:
    def __init__(self, client: redis.Redis):
        self.client = client

    async def get(self, key: str) -> Optional[Any]:
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error("cache_get_error", key=key, error=str(e))
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        try:
            serialized = json.dumps(value, default=str)
            await self.client.set(key, serialized, ex=ttl)
            return True
        except Exception as e:
            logger.error("cache_set_error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error("cache_delete_error", key=key, error=str(e))
            return False

    async def exists(self, key: str) -> bool:
        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.error("cache_exists_error", key=key, error=str(e))
            return False

    async def incr(self, key: str, ttl: Optional[int] = None) -> int:
        try:
            count = await self.client.incr(key)
            if ttl and count == 1:
                await self.client.expire(key, ttl)
            return count
        except Exception as e:
            logger.error("cache_incr_error", key=key, error=str(e))
            return 0

    async def add_to_blacklist(self, token: str, ttl: int) -> None:
        await self.client.set(f"blacklist:{token}", "1", ex=ttl)

    async def is_blacklisted(self, token: str) -> bool:
        return await self.exists(f"blacklist:{token}")


async def get_cache_service() -> CacheService:
    client = await get_redis()
    return CacheService(client)
