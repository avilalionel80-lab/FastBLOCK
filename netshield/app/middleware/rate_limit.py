import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import get_settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests: dict = defaultdict(list)
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = 60.0
        max_requests = self.settings.rate_limit_per_minute

        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if now - t < window
        ]

        if len(self.requests[client_ip]) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {max_requests} per minute",
            )

        self.requests[client_ip].append(now)
        return await call_next(request)
