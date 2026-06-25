from fastapi import APIRouter, HTTPException, Header
from app.database import get_connection
from app.crypto.ed25519 import generate_key_pair, verify_signature, sign_message
from app.models import (
    UserRegisterRequest,
    UserRegisterResponse,
    UserPublicKeyResponse,
    VerifySignatureRequest,
    VerifySignatureResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRegisterResponse)
def register(req: UserRegisterRequest):
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (req.username,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")

        private_b64, public_b64 = generate_key_pair()

        conn.execute(
            "INSERT INTO users (username, public_key, role) VALUES (?, ?, ?)",
            (req.username, public_b64, req.role),
        )
        conn.commit()

        return UserRegisterResponse(
            username=req.username,
            public_key=public_b64,
            private_key=private_b64,
            role=req.role,
        )
    finally:
        conn.close()


@router.get("/public-key/{username}", response_model=UserPublicKeyResponse)
def get_public_key(username: str):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT username, public_key, role FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return UserPublicKeyResponse(
            username=row["username"],
            public_key=row["public_key"],
            role=row["role"],
        )
    finally:
        conn.close()


@router.post("/verify", response_model=VerifySignatureResponse)
def verify(req: VerifySignatureRequest):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT public_key FROM users WHERE username = ?", (req.username,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        valid = verify_signature(row["public_key"], req.message, req.signature)
        return VerifySignatureResponse(valid=valid)
    finally:
        conn.close()
