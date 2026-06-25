from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Header
from jose import jwt, JWTError
from app.config import get_settings
from app.models import CaptiveLoginRequest, CaptiveLoginResponse, CaptiveSessionResponse

router = APIRouter(prefix="/captive", tags=["captive"])

USERS = {
    "waybi": {"password": "060618Xx", "role": "admin", "vlan": 20},
}

VLAN_MAP = {"alumno": 10, "admin": 20}


@router.post("/login", response_model=CaptiveLoginResponse)
def login(req: CaptiveLoginRequest):
    settings = get_settings()

    user_info = USERS.get(req.username)
    if user_info is None:
        if req.username == settings.captive_admin_username:
            user_info = {
                "password": settings.captive_admin_password,
                "role": "admin",
                "vlan": 20,
            }
        else:
            user_info = {"password": "default", "role": "alumno", "vlan": 10}

    if req.password != user_info["password"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": req.username,
        "role": user_info["role"],
        "vlan": user_info["vlan"],
        "exp": expire,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

    return CaptiveLoginResponse(
        token=token,
        role=user_info["role"],
        vlan=user_info["vlan"],
        expires_in_hours=settings.jwt_expire_hours,
    )


@router.get("/session", response_model=CaptiveSessionResponse)
def validate_session(authorization: str = Header(...)):
    settings = get_settings()
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return CaptiveSessionResponse(
            username=payload.get("sub", "unknown"),
            role=payload.get("role", "alumno"),
            vlan=payload.get("vlan", 10),
            valid=True,
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
