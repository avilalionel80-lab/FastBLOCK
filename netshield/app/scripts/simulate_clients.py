"""
Script que simula múltiples clientes enviando peticiones concurrentes
a la API NetShield para marcar asistencias y consultar el ledger.
"""
import asyncio
import json
import time
import sys
from statistics import mean, stdev
import httpx

BASE_URL = "http://localhost:8000"
NUM_CLIENTS = 10
REQUESTS_PER_CLIENT = 5


async def register_user(client: httpx.AsyncClient, username: str) -> dict:
    resp = await client.post(
        f"{BASE_URL}/auth/register",
        json={"username": username, "role": "alumno"},
    )
    resp.raise_for_status()
    return resp.json()


async def marcar_asistencia(
    client: httpx.AsyncClient, username: str, private_key: str, alumno_id: str, fecha: str
) -> float:
    start = time.time()
    payload = json.dumps({"alumno_id": alumno_id, "fecha": fecha, "presente": True})
    message = payload
    from app.crypto.ed25519 import sign_message
    signature = sign_message(private_key, message)
    resp = await client.post(
        f"{BASE_URL}/asistencia/marcar",
        content=payload,
        headers={
            "X-Signature": signature,
            "X-Username": username,
            "Content-Type": "application/json",
        },
    )
    resp.raise_for_status()
    elapsed = time.time() - start
    return elapsed


async def consultar_asistencia(
    client: httpx.AsyncClient, username: str, private_key: str, alumno_id: str
) -> float:
    start = time.time()
    empty_body = "{}"
    from app.crypto.ed25519 import sign_message
    signature = sign_message(private_key, empty_body)
    resp = await client.get(
        f"{BASE_URL}/asistencia/consultar/{alumno_id}",
        headers={
            "X-Signature": signature,
            "X-Username": username,
        },
    )
    resp.raise_for_status()
    elapsed = time.time() - start
    return elapsed


async def client_worker(
    semaphore: asyncio.Semaphore,
    client_id: int,
    results: list,
):
    async with semaphore:
        async with httpx.AsyncClient(timeout=30.0) as client:
            username = f"sim_client_{client_id}"
            reg = await register_user(client, username)
            private_key = reg["private_key"]

            for req_num in range(REQUESTS_PER_CLIENT):
                alumno_id = f"A{client_id:03d}"
                fecha = f"2024-03-{10 + req_num:02d}"

                lat = await marcar_asistencia(
                    client, username, private_key, alumno_id, fecha
                )
                results.append(("marcar", lat))

                if req_num % 2 == 0:
                    lat2 = await consultar_asistencia(
                        client, username, private_key, alumno_id
                    )
                    results.append(("consultar", lat2))

                await asyncio.sleep(0.05)


async def main():
    print(f"Simulando {NUM_CLIENTS} clientes, {REQUESTS_PER_CLIENT} peticiones cada uno...")
    print(f"Total estimado: {NUM_CLIENTS * (REQUESTS_PER_CLIENT + REQUESTS_PER_CLIENT // 2)} peticiones")
    print("-" * 60)

    semaphore = asyncio.Semaphore(5)
    results = []

    workers = [
        client_worker(semaphore, i, results) for i in range(NUM_CLIENTS)
    ]

    start_time = time.time()
    await asyncio.gather(*workers)
    total_time = time.time() - start_time

    marcar_lats = [r[1] for r in results if r[0] == "marcar"]
    consultar_lats = [r[1] for r in results if r[0] == "consultar"]

    print("-" * 60)
    print(f"Tiempo total: {total_time:.2f}s")
    print(f"Peticiones totales: {len(results)}")
    print(f"Throughput: {len(results) / total_time:.2f} req/s")
    print()

    for name, lats in [("marcar", marcar_lats), ("consultar", consultar_lats)]:
        if lats:
            print(f"[{name}]")
            print(f"  Media: {mean(lats) * 1000:.2f}ms")
            print(f"  Mediana: {sorted(lats)[len(lats) // 2] * 1000:.2f}ms")
            if len(lats) > 1:
                print(f"  Desviación: {stdev(lats) * 1000:.2f}ms")
            print(f"  Mín: {min(lats) * 1000:.2f}ms")
            print(f"  Máx: {max(lats) * 1000:.2f}ms")
            print()

    return results


if __name__ == "__main__":
    asyncio.run(main())
