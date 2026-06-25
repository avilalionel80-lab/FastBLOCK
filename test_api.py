import json
import requests
from nacl.signing import SigningKey
import base64
from datetime import date

# ========== CONFIGURACIÓN ==========
PRIVATE_KEY_B64 = "97FZi8XMIfHIqntsRBe0NFRlATSquKhxBhhv02byErI="
ALUMNO_ID = "A123"
PRESENTE = True
FECHA = str(date.today())  # Ejemplo: "2026-04-22"
API_URL = "http://localhost:8000/asistencia/marcar"
# ===================================

# 1. Crear payload sin firma (INCLUYENDO fecha)
payload = {
    "alumno_id": ALUMNO_ID,
    "presente": PRESENTE,
    "fecha": FECHA
}
payload_str = json.dumps(payload, separators=(',', ':')).encode('utf-8')

# 2. Firmar con Ed25519
priv_key = SigningKey(base64.b64decode(PRIVATE_KEY_B64))
firma = priv_key.sign(payload_str).signature
firma_b64 = base64.b64encode(firma).decode()

# 3. Agregar firma al payload completo
payload_con_firma = {**payload, "firma": firma_b64}

# 4. Enviar POST
print("Enviando petición a /asistencia/marcar...")
print("Payload con firma:", json.dumps(payload_con_firma, indent=2))
response = requests.post(API_URL, json=payload_con_firma)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    print(f"Respuesta: {response.json()}")
else:
    print(f"Error: {response.text}")