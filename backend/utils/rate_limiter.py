# -*- coding: utf-8 -*-
"""Rate Limiter with User-Agent Rotation"""
import random
from datetime import datetime, timedelta
from fake_useragent import UserAgent

class RateLimiter:
    """Rate limiter for API requests"""
    
    def __init__(self, max_requests=10, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
    
    async def wait_if_needed(self):
        """Wait if rate limit reached"""
        import asyncio
        now = datetime.now()
        self.requests = [t for t in self.requests if now - t < timedelta(seconds=self.window_seconds)]
        
        if len(self.requests) >= self.max_requests:
            wait_time = self.window_seconds - (now - self.requests[0]).total_seconds()
            if wait_time > 0:
                print(f"Rate limit: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                self.requests = []
        
        self.requests.append(datetime.now())
    
    def get_random_delay(self, min_sec=1, max_sec=3):
        """Get random delay"""
        return random.uniform(min_sec, max_sec)

class UserAgentRotator:
    """User-Agent rotation"""
    
    def __init__(self):
        try:
            self.ua = UserAgent()
        except Exception:
            self.ua = None
    
    def get_random_ua(self):
        """Get random User-Agent"""
        try:
            if self.ua:
                return self.ua.random
        except Exception:
            pass
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    def get_headers(self):
        """Get headers with random UA"""
        return {
            "User-Agent": self.get_random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }

rate_limiter = RateLimiter()
ua_rotator = UserAgentRotator()
