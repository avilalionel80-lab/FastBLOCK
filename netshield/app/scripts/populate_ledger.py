"""
Script para cargar bloques de ejemplo en el ledger simulado.
Útil para testear la integridad de la cadena y los endpoints de consulta.
"""
import asyncio
import json
import sys
import httpx

BASE_URL = "http://localhost:8000"

SAMPLE_BLOCKS = [
    {"action": "asistencia_marcar", "user": "A001", "data_hash": "a" * 64, "signature": "sig_001"},
    {"action": "asistencia_marcar", "user": "A002", "data_hash": "b" * 64, "signature": "sig_002"},
    {"action": "asistencia_marcar", "user": "A003", "data_hash": "c" * 64, "signature": "sig_003"},
    {"action": "asistencia_marcar", "user": "A004", "data_hash": "d" * 64, "signature": "sig_004"},
    {"action": "asistencia_editar", "user": "A001", "data_hash": "e" * 64, "signature": "sig_005"},
    {"action": "asistencia_marcar", "user": "A005", "data_hash": "f" * 64, "signature": "sig_006"},
    {"action": "asistencia_marcar", "user": "A006", "data_hash": "g" * 64, "signature": "sig_007"},
    {"action": "admin_update", "user": "admin", "data_hash": "h" * 64, "signature": "sig_admin_001"},
    {"action": "asistencia_marcar", "user": "A007", "data_hash": "i" * 64, "signature": "sig_008"},
    {"action": "asistencia_marcar", "user": "A008", "data_hash": "j" * 64, "signature": "sig_009"},
]


async def register_admin() -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/auth/register",
            json={"username": "admin_user", "role": "admin"},
        )
        resp.raise_for_status()
        return resp.json()


async def populate():
    print("Registrando usuario admin...")
    admin = await register_admin()
    username = admin["username"]
    private_key = admin["private_key"]
    print(f"Admin registrado: {username}")

    from app.crypto.ed25519 import sign_message

    async with httpx.AsyncClient(timeout=10.0) as client:
        for i, block_data in enumerate(SAMPLE_BLOCKS):
            payload = json.dumps(block_data)
            signature = sign_message(private_key, payload)

            resp = await client.post(
                f"{BASE_URL}/ledger/transact",
                content=payload,
                headers={
                    "X-Signature": signature,
                    "X-Username": username,
                    "Content-Type": "application/json",
                },
            )

            if resp.status_code == 200:
                result = resp.json()
                print(f"Bloque #{i + 1}: índice={result['block']['index']} hash={result['block']['hash'][:16]}...")
            else:
                print(f"Error bloque #{i + 1}: {resp.status_code} {resp.text}")

    print("\nVerificando ledger...")
    async with httpx.AsyncClient() as client:
        empty = "{}"
        sig = sign_message(private_key, empty)
        resp = await client.get(
            f"{BASE_URL}/ledger/verify",
            headers={
                "X-Signature": sig,
                "X-Username": username,
            },
        )
        if resp.status_code == 200:
            v = resp.json()
            print(f"Ledger válido: {v['valid']}, bloques: {v['blocks_count']}")
        else:
            print(f"Error al verificar: {resp.status_code}")

    print("\nBloques en ledger:")
    async with httpx.AsyncClient() as client:
        empty = "{}"
        sig = sign_message(private_key, empty)
        resp = await client.get(
            f"{BASE_URL}/ledger/blocks",
            headers={
                "X-Signature": sig,
                "X-Username": username,
            },
        )
        if resp.status_code == 200:
            blocks = resp.json()
            for b in blocks:
                print(f"  #{b['index']} {b['action']:25s} {b['user']:12s} {b['hash'][:16]}...")


if __name__ == "__main__":
    asyncio.run(populate())
