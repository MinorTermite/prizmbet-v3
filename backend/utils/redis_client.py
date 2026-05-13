from upstash_redis.asyncio import Redis as UpstashRedis
from backend.config import config

class Cache:
    """Redis cache client (Upstash REST)"""
    
    def __init__(self):
        self.redis = None
        self.initialized = False
    
    async def connect(self):
        """Connect to Redis via REST"""
        if not self.initialized and config.UPSTASH_REDIS_URL:
            try:
                # Upstash-redis uses url and token directly
                self.redis = UpstashRedis(
                    url=config.UPSTASH_REDIS_URL,
                    token=config.UPSTASH_REDIS_TOKEN
                )
                self.initialized = True
                print("Redis (Upstash REST) connected")
            except Exception as e:
                print(f"Redis connection failed: {e}")
                self.initialized = False
    
    async def get(self, key: str):
        """Get value from cache"""
        if not self.initialized:
            return None
        try:
            return await self.redis.get(key)
        except Exception:
            return None
    
    async def set(self, key: str, value, expire: int = 3600):
        """Set value in cache"""
        if not self.initialized:
            return False
        try:
            await self.redis.set(key, value, ex=expire)
            return True
        except Exception:
            return False

    # ✅ Optimized Batch read
    async def get_many(self, keys: list):
        """Get multiple values from cache in one request (REST Pipeline)"""
        if not self.initialized or not keys:
            return []
        try:
            pipe = self.redis.pipeline()
            for key in keys:
                pipe.get(key)
            return await pipe.exec()
        except Exception as e:
            print(f"Redis get_many error: {e}")
            return [None] * len(keys)

    # ✅ Optimized Batch write
    async def set_many(self, data: dict, expire: int = 3600):
        """Set multiple values in cache in one request (REST Pipeline)"""
        if not self.initialized or not data:
            return False
        try:
            pipe = self.redis.pipeline()
            for key, value in data.items():
                pipe.set(key, value, ex=expire)
            await pipe.exec()
            return True
        except Exception as e:
            print(f"Redis set_many error: {e}")
            return False
    
    async def delete(self, key: str):
        """Delete key from cache"""
        if not self.initialized:
            return False
        try:
            await self.redis.delete(key)
            return True
        except Exception:
            return False
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()

cache = Cache()
