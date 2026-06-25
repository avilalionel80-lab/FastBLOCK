from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware


class SignatureMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and "/auth/" not in request.url.path:
            if request.url.path not in ("/auth/register",):
                x_sig = request.headers.get("X-Signature")
                if not x_sig:
                    raise HTTPException(
                        status_code=401,
                        detail="X-Signature header is required for POST requests",
                    )
        return await call_next(request)
