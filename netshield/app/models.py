from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
import uuid


class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    role: str = Field(default="alumno", pattern="^(alumno|admin)$")


class UserRegisterResponse(BaseModel):
    username: str
    public_key: str
    private_key: str
    role: str
    message: str = "Save the private key securely. It will not be shown again."


class UserPublicKeyResponse(BaseModel):
    username: str
    public_key: str
    role: str


class VerifySignatureRequest(BaseModel):
    username: str
    message: str
    signature: str


class VerifySignatureResponse(BaseModel):
    valid: bool


class EncryptRequest(BaseModel):
    data: Any
    owner: str = "anonymous"


class EncryptResponse(BaseModel):
    record_id: str
    fragment_hashes: List[str]


class DecryptResponse(BaseModel):
    record_id: str
    data: Any


class BlockModel(BaseModel):
    index: int
    timestamp: str
    action: str
    user: str
    data_hash: str
    previous_hash: str
    signature: str
    hash: str


class LedgerVerifyResponse(BaseModel):
    valid: bool
    blocks_count: int
    errors: List[str] = []


class TransactionRequest(BaseModel):
    action: str
    user: str
    data_hash: str
    signature: str


class TransactionResponse(BaseModel):
    block: BlockModel
    message: str = "Transaction committed to ledger."


class CaptiveLoginRequest(BaseModel):
    username: str
    password: str


class CaptiveLoginResponse(BaseModel):
    token: str
    role: str
    vlan: int
    expires_in_hours: int


class CaptiveSessionResponse(BaseModel):
    username: str
    role: str
    vlan: int
    valid: bool


class MarcarAsistenciaRequest(BaseModel):
    alumno_id: str = Field(..., min_length=1)
    fecha: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    presente: bool = True


class ConsultarAsistenciaResponse(BaseModel):
    alumno_id: str
    registros: List[dict]


class HealthResponse(BaseModel):
    node1: str
    node2: str
    node3: str
    overall: str


class MetricsResponse(BaseModel):
    total_transactions: int
    average_latency_ms: float
    memory_usage_mb: float


class ResetResponse(BaseModel):
    message: str
    status: str = "ok"


class ErrorResponse(BaseModel):
    detail: str
    error_code: str
