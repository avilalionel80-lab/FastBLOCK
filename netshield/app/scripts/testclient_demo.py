"""Test completa via TestClient (sin servidor externo)"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Eliminar BD previa para empezar limpio
db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "netshield.db")
for ext in ("", "-wal", "-shm"):
    p = db_path + ext
    if os.path.exists(p):
        os.remove(p)

os.environ["MOCK_BLOCKCHAIN"] = "true"

from app.main import app
from app.database import init_db
from app.crypto.ed25519 import sign_message
from starlette.testclient import TestClient

init_db()
client = TestClient(app)

def t(step, r):
    ok = "OK" if r.status_code == 200 else f"ERR ({r.status_code})"
    print(f"[{ok}] {step}")
    try:
        data = r.json()
        print(f"      {json.dumps(data, indent=2, ensure_ascii=False)[:300]}")
    except:
        print(f"      {r.text[:200]}")
    print()

# 1. Register
r = client.post("/auth/register", json={"username": "demo", "role": "alumno"})
t("1. Registrar usuario", r)
user = r.json()

# 2. Sign & verify
msg = '{"alumno_id":"A001","fecha":"2026-06-02","presente":true}'
sig = sign_message(user["private_key"], msg)
r2 = client.post("/auth/verify", json={"username": user["username"], "message": msg, "signature": sig})
t("2. Verificar firma", r2)

# 3. Marcar asistencia (sign the actual body)
body_marcar = json.dumps({"alumno_id": "A001", "fecha": "2026-06-02", "presente": True})
sig3 = sign_message(user["private_key"], body_marcar)
r3 = client.post("/asistencia/marcar", content=body_marcar,
    headers={"X-Signature": sig3, "X-Username": user["username"], "Content-Type": "application/json"})
t("3. Marcar asistencia", r3)

# 4. Consultar (GET - sign empty body)
sig4 = sign_message(user["private_key"], "")
r4 = client.get("/asistencia/consultar/A001",
    headers={"X-Signature": sig4, "X-Username": user["username"]})
t("4. Consultar asistencia", r4)

# 5. Ledger blocks
r5 = client.get("/ledger/blocks",
    headers={"X-Signature": sig4, "X-Username": user["username"]})
t("5. Ledger bloques", r5)

# 6. Verify ledger
r6 = client.get("/ledger/verify",
    headers={"X-Signature": sig4, "X-Username": user["username"]})
t("6. Verificar ledger", r6)

# 7. Encrypt data (POST with body)
body_enc = json.dumps({"data": {"mensaje": "secreto"}, "owner": user["username"]})
sig7 = sign_message(user["private_key"], body_enc)
r7 = client.post("/data/encrypt", content=body_enc,
    headers={"X-Signature": sig7, "X-Username": user["username"], "Content-Type": "application/json"})
t("7. Cifrar datos", r7)
if r7.status_code == 200:
    rid = r7.json()["record_id"]
    sig7d = sign_message(user["private_key"], "")
    r7d = client.get(f"/data/decrypt/{rid}",
        headers={"X-Signature": sig7d, "X-Username": user["username"]})
    t("7d. Descifrar datos", r7d)

# 8. Captive portal (no auth needed)
r8 = client.post("/captive/login", json={"username": "waybi", "password": "060618Xx"})
t("8. Portal cautivo", r8)

# 9. Register admin + health
r9 = client.post("/auth/register", json={"username": "admin", "role": "admin"})
admin = r9.json()
sig9 = sign_message(admin["private_key"], "")
r9b = client.post("/admin/health", content="",
    headers={"X-Signature": sig9, "X-Username": "admin", "Content-Type": "application/json"})
t("9. Health check", r9b)

# 10. Metrics
r10 = client.get("/admin/metrics",
    headers={"X-Signature": sig9, "X-Username": "admin"})
t("10. Metricas", r10)

# 11. Reset
r11 = client.post("/admin/reset_simulation", content="",
    headers={"X-Signature": sig9, "X-Username": "admin", "Content-Type": "application/json"})
t("11. Reset simulacion", r11)

# 12. Ledger after reset
r12 = client.get("/ledger/blocks",
    headers={"X-Signature": sig4, "X-Username": user["username"]})
t("12. Ledger post-reset (solo genesis)", r12)

print("=" * 50)
print("SIMULACION COMPLETA")
