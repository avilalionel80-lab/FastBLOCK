"""Integration test - starts server, runs all endpoints, kills server"""
import subprocess
import sys
import time
import os

os.environ["MOCK_BLOCKCHAIN"] = "true"
os.environ["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import json
from app.crypto.ed25519 import sign_message

BASE = "http://127.0.0.1:8000"


def test(step, status_code, data):
    ok = "[OK]" if 200 <= status_code < 300 else "[ERR]"
    print(f"{ok} {step} ({status_code})")
    text = json.dumps(data, indent=2, ensure_ascii=False) if isinstance(data, (dict, list)) else str(data)
    for line in text[:300].split("\n"):
        print(f"   {line}")
    return 200 <= status_code < 300


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env = os.environ.copy()
    env["MOCK_BLOCKCHAIN"] = "true"
    env["PYTHONPATH"] = project_root
    env["PYTHONIOENCODING"] = "utf-8"
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    time.sleep(4)

    if server.poll() is not None:
        stdout, stderr = server.communicate()
        print(f"Server failed to start:\n{stderr.decode()}")
        return

    try:
        client = httpx.Client(base_url=BASE, timeout=10.0)

        # 1. Register
        r = client.post("/auth/register", json={"username": "demo", "role": "alumno"})
        if r.status_code != 200:
            r = client.post("/auth/register", json={"username": "demo1", "role": "alumno"})
        test(1, r.status_code, r.json())
        user = r.json()
        priv = user["private_key"]

        # 2. Sign & verify
        msg = '{"alumno_id":"A001","fecha":"2026-06-02","presente":true}'
        sig = sign_message(priv, msg)
        r2 = client.post("/auth/verify", json={"username": user["username"], "message": msg, "signature": sig})
        test(2, r2.status_code, r2.json())

        # 3. Marcar asistencia
        r3 = client.post("/asistencia/marcar", content=msg,
            headers={"X-Signature": sig, "X-Username": user["username"], "Content-Type": "application/json"})
        test(3, r3.status_code, r3.json())

        # 4. Consultar
        sig4 = sign_message(priv, "{}")
        r4 = client.get("/asistencia/consultar/A001",
            headers={"X-Signature": sig4, "X-Username": user["username"]})
        test(4, r4.status_code, r4.json())

        # 5. Ledger blocks
        r5 = client.get("/ledger/blocks",
            headers={"X-Signature": sig4, "X-Username": user["username"]})
        test(5, r5.status_code, r5.json())

        # 6. Ledger verify
        r6 = client.get("/ledger/verify",
            headers={"X-Signature": sig4, "X-Username": user["username"]})
        test(6, r6.status_code, r6.json())

        # 7. Encrypt/decrypt
        sig7 = sign_message(priv, json.dumps({"data": {"mensaje": "secreto"}, "owner": user["username"]}))
        r7 = client.post("/data/encrypt",
            json={"data": {"mensaje": "secreto"}, "owner": user["username"]},
            headers={"X-Signature": sig7, "X-Username": user["username"]})
        test(7, r7.status_code, r7.json())
        if r7.status_code == 200:
            rid = r7.json()["record_id"]
            sig7d = sign_message(priv, "{}")
            r7d = client.get(f"/data/decrypt/{rid}",
                headers={"X-Signature": sig7d, "X-Username": user["username"]})
            test("7d", r7d.status_code, r7d.json())

        # 8. Captive portal
        r8 = client.post("/captive/login", json={"username": "waybi", "password": "060618Xx"})
        test(8, r8.status_code, r8.json())

        # 9. Register admin + health
        r9 = client.post("/auth/register", json={"username": "admin", "role": "admin"})
        admin = r9.json()
        sig9 = sign_message(admin["private_key"], "{}")
        r9b = client.post("/admin/health", content="{}",
            headers={"X-Signature": sig9, "X-Username": "admin", "Content-Type": "application/json"})
        test(9, r9b.status_code, r9b.json())

        # 10. Metrics
        r10 = client.get("/admin/metrics",
            headers={"X-Signature": sig9, "X-Username": "admin"})
        test(10, r10.status_code, r10.json())

        # 11. Reset
        r11 = client.post("/admin/reset_simulation", content="{}",
            headers={"X-Signature": sig9, "X-Username": "admin", "Content-Type": "application/json"})
        test(11, r11.status_code, r11.json())

        # 12. Verify reset
        r12 = client.get("/ledger/blocks",
            headers={"X-Signature": sig4, "X-Username": user["username"]})
        test(12, r12.status_code, r12.json())

    finally:
        if server.poll() is None:
            server.terminate()
            server.wait(timeout=5)


if __name__ == "__main__":
    main()
