import asyncio
import os
from typing import Any, Dict, List

import httpx


class ComiteClient:
    def __init__(self) -> None:
        self.nodos = [
            os.getenv("COMITE_NODO1_URL", "http://127.0.0.1:8000/mock/nodo1"),
            os.getenv("COMITE_NODO2_URL", "http://127.0.0.1:8000/mock/nodo2"),
            os.getenv("COMITE_NODO3_URL", "http://127.0.0.1:8000/mock/nodo3"),
        ]
        self.ledger_url = os.getenv("COMITE_LEDGER_URL", "http://127.0.0.1:8000/mock/ledger")
        timeout = float(os.getenv("COMITE_TIMEOUT_SECONDS", "10"))
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def enviar_fragmento(
        self, nodo_id: int, record_id: str, fragmento: str, hash_dato: str, nonce: str
    ) -> Dict[str, Any]:
        base_url = self.nodos[nodo_id - 1]
        payload = {
            "record_id": record_id,
            "fragmento": fragmento,
            "hash_dato": hash_dato,
            "nonce": nonce,
        }
        response = await self._client.post(f"{base_url}/fragmento", json=payload)
        response.raise_for_status()
        return response.json()

    async def solicitar_fragmento(self, nodo_id: int, record_id: str) -> Dict[str, Any]:
        base_url = self.nodos[nodo_id - 1]
        response = await self._client.get(f"{base_url}/fragmento/{record_id}")
        response.raise_for_status()
        return response.json()

    async def enviar_transaccion(self, transaccion: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._client.post(f"{self.ledger_url}/tx", json=transaccion)
        response.raise_for_status()
        return response.json()

    async def consultar_bloque(self, block_id: str) -> Dict[str, Any]:
        response = await self._client.get(f"{self.ledger_url}/block/{block_id}")
        response.raise_for_status()
        return response.json()

    async def reconstruir_clave(self, record_id: str) -> List[str]:
        resultados = await asyncio.gather(
            *[self.solicitar_fragmento(nodo_id, record_id) for nodo_id in range(1, len(self.nodos) + 1)]
        )
        return [r["fragmento"] for r in resultados]
