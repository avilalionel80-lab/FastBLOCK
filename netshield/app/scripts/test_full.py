"""Prueba completa de la simulacion NetShield"""
import httpx
import json
import sys
from app.crypto.ed25519 import sign_message

BASE = "http://127.0.0.1:8000"


def test(step, status_code, data):
    ok = "✅" if status_code == 200 else "❌"
    print(f"{ok} {step} ({status_code})")
    if isinstance(data, dict) or isinstance(data, list):
        print(f"   {json.dumps(data, indent=2, ensure_ascii=False)[:200]}")
    else:
        print(f"   {str(data)[:200]}")
    return status_code == 200


def main():
    client = httpx.Client(base_url=BASE, timeout=10.0)

    # 1. Registrar
    r = client.post("/auth/register", json={"username": "demo2", "role": "alumno"})
    if r.status_code == 400:
        r = client.post("/auth/register", json={"username": "demo3", "role": "alumno"})
    test(1, r.status_code, r.json())
    user = r.json()
    priv_key = user["private_key"]
    pub_key = user["public_key"]

    # 2. Firmar y verificar
    msg = '{"alumno_id": "A001", "fecha": "2026-06-02", "presente": true}'
    sig = sign_message(priv_key, msg)
    r2 = client.post("/auth/verify", json={"username": user["username"], "message": msg, "signature": sig})
    test(2, r2.status_code, r2.json())

    # 3. Marcar asistencia
    r3 = client.post(
        "/asistencia/marcar",
        content=msg,
        headers={"X-Signature": sig, "X-Username": user["username"], "Content-Type": "application/json"},
    )
    test(3, r3.status_code, r3.json())

    # 4. Consultar asistencia
    sig4 = sign_message(priv_key, "{}")
    r4 = client.get(
        "/asistencia/consultar/A001",
        headers={"X-Signature": sig4, "X-Username": user["username"]},
    )
    test(4, r4.status_code, r4.json())

    # 5. Ledger
    sig5 = sign_message(priv_key, "{}")
    r5 = client.get(
        "/ledger/blocks",
        headers={"X-Signature": sig5, "X-Username": user["username"]},
    )
    test(5, r5.status_code, r5.json())

    # 6. Verificar ledger
    r5v = client.get(
        "/ledger/verify",
        headers={"X-Signature": sig5, "X-Username": user["username"]},
    )
    test("5v", r5v.status_code, r5v.json())

    # 7. Cifrar/descifrar datos
    r_enc = client.post(
        "/data/encrypt",
        json={"data": {"mensaje": "secreto", "nivel": "alto"}, "owner": user["username"]},
        headers={"X-Signature": sig5, "X-Username": user["username"]},
    )
    test(7, r_enc.status_code, r_enc.json())
    if r_enc.status_code == 200:
        record_id = r_enc.json()["record_id"]
        r_dec = client.get(
            f"/data/decrypt/{record_id}",
            headers={"X-Signature": sig5, "X-Username": user["username"]},
        )
        test("7d", r_dec.status_code, r_dec.json())

    # 8. Portal cautivo
    r8 = client.post("/captive/login", json={"username": "waybi", "password": "060618Xx"})
    test(8, r8.status_code, r8.json())

    # 9. Registrar admin + health
    r9 = client.post("/auth/register", json={"username": "admin_test", "role": "admin"})
    admin = r9.json()
    sig9 = sign_message(admin["private_key"], "{}")
    r9b = client.post(
        "/admin/health",
        content="{}",
        headers={"X-Signature": sig9, "X-Username": "admin_test", "Content-Type": "application/json"},
    )
    test(9, r9b.status_code, r9b.json())

    # 10. Reset simulacion
    r10 = client.post(
        "/admin/reset_simulation",
        content="{}",
        headers={"X-Signature": sig9, "X-Username": "admin_test", "Content-Type": "application/json"},
    )
    test(10, r10.status_code, r10.json())

    # 11. Ver ledger despues de reset
    r11 = client.get(
        "/ledger/blocks",
        headers={"X-Signature": sig5, "X-Username": user["username"]},
    )
    test(11, r11.status_code, r11.json())

    # 12. Metrics
    r12 = client.get(
        "/admin/metrics",
        headers={"X-Signature": sig9, "X-Username": "admin_test"},
    )
    test(12, r12.status_code, r12.json())

    print(f"\n{'='*40}")
    print("SIMULACION COMPLETA - Todos los endpoints probados")


if __name__ == "__main__":
    main()
