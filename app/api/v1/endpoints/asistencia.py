import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, Literal

import bleach
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.crypto_service import NetShieldCrypto
from app.services.comite_client import ComiteClient

router = APIRouter()
logger = logging.getLogger("netshield.api")

crypto = NetShieldCrypto()
comite_client = ComiteClient()

ASISTENCIAS_CIFRADAS: Dict[str, Dict[str, str]] = {}
METRICAS: Dict[str, int] = {
    "asistencia_marcar_ok": 0,
    "asistencia_consultar_ok": 0,
    "auth_verify_ok": 0,
    "errores": 0,
}

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "netshield-admin-token")
PUBLIC_KEYS: Dict[str, str] = {
    # Debe poblarse desde BD/almacén seguro en producción.
    "alumno-demo": os.getenv("ALUMNO_DEMO_PUBLIC_KEY_B64", ""),
}


class AsistenciaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    alumno_id: str = Field(min_length=1, max_length=64)
    fecha: str = Field(min_length=10, max_length=10)
    presente: bool
    firma: str = Field(min_length=32)

    @field_validator("alumno_id", "fecha")
    @classmethod
    def sanitize_text(cls, value: str) -> str:
        cleaned = bleach.clean(value, tags=[], strip=True)
        if cleaned != value:
            raise ValueError("Input contiene caracteres no permitidos")
        return cleaned


class AdminModificarRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    accion: str = Field(min_length=1, max_length=120)
    admin_id: str = Field(min_length=1, max_length=64)
    admin_token: str = Field(min_length=8)

    @field_validator("accion", "admin_id")
    @classmethod
    def sanitize_text(cls, value: str) -> str:
        cleaned = bleach.clean(value, tags=[], strip=True)
        if cleaned != value:
            raise ValueError("Input contiene caracteres no permitidos")
        return cleaned


class AuthVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    usuario_id: str = Field(min_length=1, max_length=64)
    payload: Dict[str, Any]
    firma: str = Field(min_length=32, max_length=256)


def _payload_para_firma(alumno_id: str, fecha: str, presente: bool) -> bytes:
    msg = {"alumno_id": alumno_id, "fecha": fecha, "presente": presente}
    return json.dumps(msg, sort_keys=True, separators=(",", ":")).encode("utf-8")


@router.post("/asistencia/marcar")
async def marcar_asistencia(req: AsistenciaRequest) -> Dict[str, str]:
    public_key_b64 = PUBLIC_KEYS.get(req.alumno_id)
    if not public_key_b64:
        METRICAS["errores"] += 1
        raise HTTPException(status_code=401, detail="Usuario sin clave pública registrada")

    mensaje = _payload_para_firma(req.alumno_id, req.fecha, req.presente)
    if not crypto.verificar_firma_ed25519(public_key_b64, mensaje, req.firma):
        METRICAS["errores"] += 1
        raise HTTPException(status_code=401, detail="Firma inválida")

    record_id = str(uuid.uuid4())
    timestamp = int(time.time())
    nonce = crypto.generar_nonce()
    nonce_hex = nonce.hex()

    payload = {
        "alumno_id": req.alumno_id,
        "fecha": req.fecha,
        "presente": req.presente,
        "timestamp": timestamp,
        "record_id": record_id,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    clave = crypto.generar_clave_aes()
    payload_cifrado = crypto.cifrar(payload_bytes, clave, nonce)
    hash_dato = hashlib.sha256(payload_cifrado).hexdigest()

    fragmentos = crypto.fragmentar_clave(clave, 3, 3)
    await asyncio.gather(*(
        comite_client.enviar_fragmento(idx, record_id, frag, hash_dato, nonce_hex)
        for idx, frag in enumerate(fragmentos, start=1)
    ))

    ASISTENCIAS_CIFRADAS[record_id] = {
        "ciphertext_hex": payload_cifrado.hex(),
        "nonce": nonce_hex,
        "hash_dato": hash_dato,
    }

    tx = {
        "accion": "asistencia",
        "usuario": req.alumno_id,
        "record_id": record_id,
        "hash_dato": hash_dato,
        "timestamp": timestamp,
        "nonce": nonce_hex,
        "firma_usuario": req.firma,
    }
    tx_response = await comite_client.enviar_transaccion(tx)
    METRICAS["asistencia_marcar_ok"] += 1
    logger.info("Asistencia marcada: alumno=%s record_id=%s", req.alumno_id, record_id)
    return {"status": "ok", "block_hash": tx_response["block_hash"], "record_id": record_id}


@router.get("/asistencia/consultar/{record_id}")
async def consultar_asistencia(record_id: str) -> Dict[str, Any]:
    registro = ASISTENCIAS_CIFRADAS.get(record_id)
    if not registro:
        METRICAS["errores"] += 1
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    fragmentos = await comite_client.reconstruir_clave(record_id)
    clave = crypto.reconstruir_clave(fragmentos)
    plaintext = crypto.descifrar(
        bytes.fromhex(registro["ciphertext_hex"]),
        clave,
        bytes.fromhex(registro["nonce"]),
    )
    METRICAS["asistencia_consultar_ok"] += 1
    return {"status": "ok", "record_id": record_id, "data": json.loads(plaintext.decode("utf-8"))}


@router.post("/admin/modificar")
async def admin_modificar(req: AdminModificarRequest) -> Dict[str, str]:
    if not hmac.compare_digest(req.admin_token, ADMIN_TOKEN):
        METRICAS["errores"] += 1
        raise HTTPException(status_code=403, detail="Token administrativo inválido")

    tx = {
        "accion": "admin_modificar",
        "admin_id": req.admin_id,
        "detalle": req.accion,
        "timestamp": int(time.time()),
    }
    tx_response = await comite_client.enviar_transaccion(tx)
    logger.warning("Acción admin ejecutada por %s", req.admin_id)
    return {"status": "ok", "block_hash": tx_response["block_hash"]}


@router.get("/ledger/ver/{block_id}")
async def ver_ledger(block_id: str) -> Dict[str, Any]:
    return await comite_client.consultar_bloque(block_id)


@router.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "netshield-fastapi",
        "metrics": METRICAS,
        "nodes": len(comite_client.nodos),
    }


@router.post("/auth/verificar")
async def verificar_firma(req: AuthVerifyRequest) -> Dict[str, Literal["ok"]]:
    public_key_b64 = PUBLIC_KEYS.get(req.usuario_id)
    if not public_key_b64:
        METRICAS["errores"] += 1
        raise HTTPException(status_code=404, detail="Usuario sin clave pública")

    message = json.dumps(req.payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if not crypto.verificar_firma_ed25519(public_key_b64, message, req.firma):
        METRICAS["errores"] += 1
        raise HTTPException(status_code=401, detail="Firma inválida")

    METRICAS["auth_verify_ok"] += 1
    return {"status": "ok"}
