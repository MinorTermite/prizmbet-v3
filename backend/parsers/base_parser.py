# -*- coding: utf-8 -*-
"""Base Parser Class"""
import asyncio
import aiohttp
from datetime import datetime
from backend.utils.rate_limiter import rate_limiter, ua_rotator
from backend.utils.telegram import telegram
from backend.db.supabase_client import db
from backend.utils.redis_client import cache
from backend.utils.team_mapping import team_normalizer

class BaseParser:
    """Base class for all parsers"""
    
    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url
        self.session = None
        self.matches = []
        self.proxy = None  # will be set from proxy_manager or config
    
    @staticmethod
    def _normalize_proxy_url(raw: str) -> str:
        """Normalize proxy URL to scheme://user:pass@host:port format.

        Accepts:
          socks5://user:pass@host:port  → unchanged
          http://user:pass@host:port    → unchanged
          host:port:user:pass           → socks5://user:pass@host:port
          host:port                     → socks5://host:port
        """
        if not raw:
            return raw
        if raw.startswith(('socks', 'http')):
            return raw
        parts = raw.split(':')
        if len(parts) == 4:  # host:port:user:pass
            return f"socks5://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
        if len(parts) == 2:  # host:port
            return f"socks5://{parts[0]}:{parts[1]}"
        return raw

    async def init_session(self):
        """Initialize HTTP session with optional proxy support."""
        if self.session is None:
            from backend.utils.proxy_manager import proxy_manager
            from backend.config import config
            proxy_url = None
            if config.PROXY_ENABLED and config.PROXY_URL:
                proxy_url = self._normalize_proxy_url(config.PROXY_URL)
            elif config.PROXY_ENABLED:
                await proxy_manager.refresh_if_needed()
                proxy_url = proxy_manager.get_proxy()

            if proxy_url:
                masked = proxy_url.split('@')[-1] if '@' in proxy_url else proxy_url
                print(f"[{self.name}] Using proxy: {proxy_url.split('://')[0]}://***@{masked}")

            self.proxy = proxy_url

            connector = None
            if proxy_url and proxy_url.startswith('socks'):
                try:
                    from aiohttp_socks import ProxyConnector
                    connector = ProxyConnector.from_url(proxy_url)
                    self.proxy = None  # SOCKS handled by connector, not per-request
                except ImportError:
                    print(f"[{self.name}] aiohttp-socks not installed, skipping SOCKS proxy")
                    proxy_url = None
                    self.proxy = None

            # ✅ OPTIMIZATION: Connection pooling and DNS caching (if not SOCKS)
            if connector is None:
                connector = aiohttp.TCPConnector(
                    limit=50,             # Overall connection pool limit
                    limit_per_host=10,    # Per-host limit
                    use_dns_cache=True,   # Cache IP addresses of bookmakers
                    ttl_dns_cache=300     # For 5 minutes
                )

            # ✅ OPTIMIZATION: Added compression support (gzip, deflate, br)
            headers = {**ua_rotator.get_headers(), "Accept-Encoding": "gzip, deflate, br"}

            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
                connector=connector,
            )
    
    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def fetch(self, url: str, retries=3):
        """Fetch URL with retries"""
        await self.init_session()
        
        for attempt in range(retries):
            try:
                await rate_limiter.wait_if_needed()
                await asyncio.sleep(rate_limiter.get_random_delay())
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
            except Exception as e:
                print(f"Fetch error (attempt {attempt+1}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        return None
    
    async def parse(self):
        """Parse matches - override in subclass"""
        raise NotImplementedError("Subclasses must implement parse()")
    
    async def save_matches(self):
        """Save matches to database with Redis pipeline and deduplication"""
        if not self.matches:
            return 0
        
        # 1. Normalization and preparation
        matches_to_check = []
        cache_keys = []
        for match in self.matches:
            # Using team_normalizer as in original code
            home = team_normalizer.normalize(match.get("home_team", ""))
            away = team_normalizer.normalize(match.get("away_team", ""))
            match["home_team"] = home
            match["away_team"] = away
            
            date_str = str(match.get('match_time') or '')[:10]
            cache_key = f"match:{self.name}:{date_str}:{home}:{away}"
            
            matches_to_check.append(match)
            cache_keys.append(cache_key)
            
        # 2. Bulk cache check (using optimized get_many)
        try:
            cached_results = await cache.get_many(cache_keys)
        except Exception as e:
            print(f"Bulk cache check failed: {e}")
            cached_results = [False] * len(cache_keys)

        matches_to_insert = []
        cache_to_set = {}
        
        # 3. Filter duplicates
        for match, cache_key, is_cached in zip(matches_to_check, cache_keys, cached_results):
            if not is_cached:
                match["bookmaker"] = self.name
                match["parsed_at"] = datetime.utcnow().isoformat()
                matches_to_insert.append(match)
                cache_to_set[cache_key] = "1"
        
        # 4. Save to DB and bulk cache update
        saved = 0
        if matches_to_insert and db.initialized:
            # Note: insert_match is still per-item, but bulk insert could be a future step
            for match in matches_to_insert:
                try:
                    result = await db.insert_match(match)
                    if result is not None:
                        saved += 1
                    else:
                        print(f"DB skipped {match.get('home_team')} vs {match.get('away_team')}")
                except Exception as e:
                    print(f"DB Error for {match.get('home_team')}: {e}")
            
            if cache_to_set:
                await cache.set_many(cache_to_set, expire=3600)
        
        return saved
    
    async def run(self):
        """Run parser"""
        print(f"Starting {self.name} parser...")
        start_time = datetime.now()
        
        try:
            self.matches = await self.parse()
            saved_count = await self.save_matches()
            
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"{self.name} completed in {elapsed:.1f}s - {saved_count} matches")
            
            await telegram.send_parser_report(self.name, saved_count, "success")
            return saved_count
            
        except Exception as e:
            print(f"{self.name} failed: {e}")
            await telegram.send_alert_throttled(
                f"Parser Error: {self.name}", str(e),
                cooldown_key=f"parser_error:{self.name}",
                cooldown_seconds=1800
            )
            return 0
        
        finally:
            await self.close_session()
