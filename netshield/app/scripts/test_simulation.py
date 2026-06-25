"""Script para probar la simulacion NetShield"""
import json
import httpx

BASE = "http://127.0.0.1:8000"

def main():
    client = httpx.Client(base_url=BASE)

    # 1. Registrar usuario
    r = client.post("/auth/register", json={"username": "demo", "role": "alumno"})
    data = r.json()
    priv_key = data["private_key"]
    pub_key = data["public_key"]
    print(f"1. Registro OK -> private_key: {priv_key[:32]}...")
    print(f"   public_key:  {pub_key[:32]}...\n")

    # 2. Firmar con Ed25519 via endpoint /auth/verify
    mensaje = '{"alumno_id": "A001", "fecha": "2026-06-02", "presente": true}'

    from app.crypto.ed25519 import sign_message
    sig = sign_message(priv_key, mensaje)
    print(f"2. Firma generada (longitud: {len(sig)})")

    r2 = client.post("/auth/verify", json={"username": "demo", "message": mensaje, "signature": sig})
    print(f"   Verificacion: {r2.json()}\n")

    # 3. Marcar asistencia (flujo completo: cifrar + fragmentar + comité + ledger)
    r3 = client.post(
        "/asistencia/marcar",
        content=mensaje,
        headers={"X-Signature": sig, "X-Username": "demo", "Content-Type": "application/json"},
    )
    print(f"3. Marcar asistencia: {r3.status_code}")
    print(f"   Respuesta: {json.dumps(r3.json(), indent=2)}\n")

    # 4. Consultar asistencia
    from app.crypto.ed25519 import sign_message as sm2
    sig_consulta = sm2(priv_key, "{}")
    r4 = client.get(
        "/asistencia/consultar/A001",
        headers={"X-Signature": sig_consulta, "X-Username": "demo"},
    )
    print(f"4. Consultar asistencia: {r4.status_code}")
    print(f"   Registros: {json.dumps(r4.json(), indent=2)}\n")

    # 5. Ver ledger
    sig_ledger = sm2(priv_key, "{}")
    r5 = client.get(
        "/ledger/blocks",
        headers={"X-Signature": sig_ledger, "X-Username": "demo"},
    )
    print(f"5. Ledger: {r5.status_code} - {len(r5.json())} bloques\n")

    # 6. Portal cautivo
    r6 = client.post("/captive/login", json={"username": "waybi", "password": "060618Xx"})
    print(f"6. Captive login: {r6.status_code} -> VLAN={r6.json()['vlan']}, role={r6.json()['role']}\n")

    # 7. Health check (requiere admin)
    # Registrar admin
    r7 = client.post("/auth/register", json={"username": "admin_demo", "role": "admin"})
    admin = r7.json()
    sig_admin = sm2(admin["private_key"], "{}")
    r7b = client.post(
        "/admin/health",
        content="{}",
        headers={"X-Signature": sig_admin, "X-Username": "admin_demo", "Content-Type": "application/json"},
    )
    print(f"7. Health check: {r7b.status_code} -> {json.dumps(r7b.json(), indent=2)}")

if __name__ == "__main__":
    main()
