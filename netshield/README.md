# NetShield REST API

API puente entre la aplicación web NetShield y el comité blockchain Hyperledger Besu (3 nodos). Incluye autenticación con firma Ed25519, cifrado AES-256-GCM + Shamir Secret Sharing (3,3), y un ledger inmutable simulado.

## Requisitos

- Python 3.11+
- Docker y Docker Compose (opcional)

## Instalación y ejecución local

```bash
# Clonar e instalar dependencias
pip install -r requirements.txt

# Copiar configuración
cp .env.example .env

# Ejecutar (modo simulación por defecto)
uvicorn app.main:app --reload --port 8000
```

La API estará disponible en `http://localhost:8000`. Swagger UI en `/docs`.

## Modo simulación vs producción

| Variable | Descripción |
|---|---|
| `MOCK_BLOCKCHAIN=true` | Usa comité y ledger simulados en memoria/JSON |
| `MOCK_BLOCKCHAIN=false` | Conecta a nodos Besu reales vía JSON-RPC |

En modo simulación todos los endpoints funcionan sin hardware real.

## Variables de entorno

Ver `.env.example`:

```
MOCK_BLOCKCHAIN=true
NODE1_URL=http://localhost:8545
NODE2_URL=http://localhost:8546
NODE3_URL=http://localhost:8547
DATABASE_URL=sqlite:///./netshield.db
SECRET_KEY=clave-para-jwt
LOG_LEVEL=INFO
RATE_LIMIT_PER_MINUTE=100
```

## Endpoints principales

### Autenticación
- `POST /auth/register` — Registra usuario, devuelve par de claves Ed25519
- `GET /auth/public-key/{username}` — Obtiene clave pública
- `POST /auth/verify` — Verifica una firma

### Datos cifrados
- `POST /data/encrypt` — Cifra datos con AES-256-GCM, fragmenta clave con Shamir (3,3) y almacena fragmentos en los 3 nodos
- `GET /data/decrypt/{id}` — Recupera fragmentos, reconstruye clave y descifra

### Ledger
- `GET /ledger/blocks` — Lista todos los bloques
- `POST /ledger/transact` — Envía transacción al ledger (requiere admin)
- `GET /ledger/verify` — Verifica integridad de la cadena

### Asistencia
- `POST /asistencia/marcar` — Marca asistencia (cifra + fragmenta + ledger)
- `GET /asistencia/consultar/{alumno_id}` — Consulta asistencias

### Portal cautivo
- `POST /captive/login` — Login con `waybi` / `060618Xx`, devuelve JWT y VLAN
- `GET /captive/session` — Valida sesión JWT

### Administración
- `POST /admin/health` — Health check de los 3 nodos
- `GET /admin/metrics` — Métricas (transacciones, latencia, memoria)
- `POST /admin/reset_simulation` — Resetea el estado simulado

## Autenticación de peticiones

Toda petición a endpoints protegidos debe incluir:

```
X-Signature: <firma_ed25519_en_base64_del_body>
X-Username: <nombre_de_usuario>
```

La firma se genera con la clave privada del usuario sobre el body de la petición (en texto plano).

## Ejecución con Docker

```bash
# Solo la API (modo simulación)
docker-compose up netshield-api

# Producción con nodos Besu
docker-compose up netshield-api-production

# Solo los nodos Besu
docker-compose up besu-node1 besu-node2 besu-node3
```

## Ejecutar pruebas

```bash
pytest app/tests/ -v
```

## Scripts de simulación

```bash
# Poblar ledger con datos de ejemplo
python -m app.scripts.populate_ledger

# Simular clientes concurrentes
python -m app.scripts.simulate_clients
```

## Estructura del proyecto

```
netshield/
├── app/
│   ├── main.py              # Punto de entrada FastAPI
│   ├── config.py             # Variables de entorno (Pydantic Settings)
│   ├── database.py           # SQLite (users, data_records)
│   ├── dependencies.py       # Dependencias de autenticación
│   ├── models.py             # Modelos Pydantic
│   ├── crypto/               # Criptografía
│   │   ├── aes.py            # AES-256-GCM
│   │   ├── shamir.py         # Shamir Secret Sharing (3,3)
│   │   └── ed25519.py        # Ed25519 firmas
│   ├── blockchain/           # Blockchain
│   │   ├── committee.py      # Comité de 3 nodos (simulado/real)
│   │   └── ledger.py         # Ledger inmutable
│   ├── routers/              # Endpoints
│   ├── middleware/            # Middleware
│   ├── tests/                # Pruebas unitarias
│   └── scripts/              # Utilidades
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```
