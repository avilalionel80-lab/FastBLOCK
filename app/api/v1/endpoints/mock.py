import hashlib
import json
import time
from typing import Any, Dict, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter()

MOCK_NODOS: Dict[str, Dict[str, Any]] = {"nodo1": {}, "nodo2": {}, "nodo3": {}}
MOCK_LEDGER: Dict[str, Dict[str, Any]] = {}


class MockFragmentoPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    record_id: str = Field(min_length=1, max_length=64)
    fragmento: str = Field(min_length=1, max_length=512)
    hash_dato: str = Field(min_length=64, max_length=64)
    nonce: str = Field(min_length=24, max_length=24)


@router.post("/{nodo_id}/fragmento")
async def mock_guardar_fragmento(
    nodo_id: Literal["nodo1", "nodo2", "nodo3"], payload: MockFragmentoPayload
) -> Dict[str, str]:
    MOCK_NODOS[nodo_id][payload.record_id] = payload.model_dump()
    return {"status": "ok"}


@router.get("/{nodo_id}/fragmento/{record_id}")
async def mock_obtener_fragmento(
    nodo_id: Literal["nodo1", "nodo2", "nodo3"], record_id: str
) -> Dict[str, Any]:
    data = MOCK_NODOS[nodo_id].get(record_id)
    if not data:
        raise HTTPException(status_code=404, detail="Fragmento no encontrado")
    return data


@router.post("/ledger/tx")
async def mock_ledger_tx(tx: Dict[str, Any]) -> Dict[str, str]:
    block_hash = hashlib.sha256(
        json.dumps(tx, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    MOCK_LEDGER[block_hash] = {"block_hash": block_hash, "tx": tx, "timestamp": int(time.time())}
    return {"status": "ok", "block_hash": block_hash}


@router.get("/ledger/block/{block_id}")
async def mock_ledger_block(block_id: str) -> Dict[str, Any]:
    block = MOCK_LEDGER.get(block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Bloque no encontrado")
    return block
