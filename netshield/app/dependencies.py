import base64
import hashlib
import json
from typing import Optional
from fastapi import Header, HTTPException, Request, Depends
from jose import JWTError, jwt
from app.config import get_settings
from app.crypto.ed25519 import verify_signature
from app.database import get_connection


class AuthDependency:
    async def __call__(
        self,
        request: Request,
        x_signature: Optional[str] = Header(None),
        x_username: Optional[str] = Header(None),
        authorization: Optional[str] = Header(None),
    ):
        if x_signature is None or x_username is None:
            raise HTTPException(status_code=401, detail="Missing X-Signature or X-Username header")

        body = await request.body()
        message = body.decode("utf-8") if body else ""

        is_admin = False
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]
            try:
                settings = get_settings()
                payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
                if payload.get("role") == "admin":
                    is_admin = True
            except JWTError:
                pass

        conn = get_connection()
        try:
            cursor = conn.execute("SELECT public_key, role FROM users WHERE username = ?", (x_username,))
            row = cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=401, detail="User not found")

            public_key = row["public_key"]
            role = row["role"]

            if not is_admin and role != "admin":
                valid = verify_signature(public_key, message, x_signature)
                if not valid:
                    raise HTTPException(status_code=401, detail="Invalid signature")

            request.state.username = x_username
            request.state.role = role
            request.state.is_admin = is_admin or role == "admin"
            return request.state
        finally:
            conn.close()


auth_required = AuthDependency()


async def get_current_user(request: Request):
    return getattr(request.state, "username", None)


async def require_admin(request: Request):
    if not getattr(request.state, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
