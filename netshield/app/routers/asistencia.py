import json
import hashlib
import uuid
from fastapi import APIRouter, HTTPException, Depends
from loguru import logger
from app.database import get_connection
from app.crypto.aes import generate_aes_key, encrypt_data, decrypt_data
from app.crypto.shamir import split_secret, reconstruct_secret
from app.blockchain.committee import BlockchainCommittee
from app.models import MarcarAsistenciaRequest, ConsultarAsistenciaResponse
from app.dependencies import auth_required

router = APIRouter(prefix="/asistencia", tags=["asistencia"])


@router.post("/marcar")
async def marcar_asistencia(req: MarcarAsistenciaRequest, _=Depends(auth_required)):
    committee = BlockchainCommittee()

    attendance_data = {
        "alumno_id": req.alumno_id,
        "fecha": req.fecha,
        "presente": req.presente,
    }

    data_bytes = json.dumps(attendance_data, ensure_ascii=False).encode("utf-8")
    aes_key = generate_aes_key()
    ciphertext, iv = encrypt_data(data_bytes, aes_key)
    shares = split_secret(aes_key, num_shares=3, threshold=3)

    record_id = str(uuid.uuid4())
    data_hash = hashlib.sha256(data_bytes).hexdigest()
    fragment_hashes = []

    for i, share in enumerate(shares):
        fragment_id = f"{record_id}_fragment_{i}"
        fhash = await committee.store_fragment(i, fragment_id, share)
        fragment_hashes.append(fhash)

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO data_records
               (id, encrypted_data, iv, tag, fragment1_hash, fragment2_hash, fragment3_hash, owner)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record_id,
                ciphertext.hex(),
                iv.hex(),
                "",
                fragment_hashes[0],
                fragment_hashes[1],
                fragment_hashes[2],
                req.alumno_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    block_data = {
        "action": "asistencia_marcar",
        "user": req.alumno_id,
        "data_hash": data_hash,
        "signature": f"sig_{record_id}",
    }

    try:
        block = await committee.transact(block_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    logger.info(f"Attendance marked for {req.alumno_id} on {req.fecha}")
    return {
        "record_id": record_id,
        "block_index": block["index"],
        "block_hash": block["hash"],
        "data_hash": data_hash,
        "fragment_hashes": fragment_hashes,
    }


@router.get("/consultar/{alumno_id}", response_model=ConsultarAsistenciaResponse)
async def consultar_asistencia(alumno_id: str, _=Depends(auth_required)):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM data_records WHERE owner = ? ORDER BY created_at DESC",
            (alumno_id,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return ConsultarAsistenciaResponse(alumno_id=alumno_id, registros=[])

    committee = BlockchainCommittee()
    registros = []

    for row in rows:
        shares = []
        for i in range(3):
            fid = f"{row['id']}_fragment_{i}"
            share = await committee.get_fragment(i, fid)
            if share is None:
                continue
            shares.append(share)

        if len(shares) < 3:
            continue

        try:
            aes_key = reconstruct_secret(shares)
            ciphertext = bytes.fromhex(row["encrypted_data"])
            iv = bytes.fromhex(row["iv"])
            plaintext = decrypt_data(ciphertext, aes_key, iv)
            data = json.loads(plaintext.decode("utf-8"))
            data["record_id"] = row["id"]
            registros.append(data)
        except Exception as exc:
            logger.error(f"Failed to decrypt record {row['id']}: {exc}")
            continue

    return ConsultarAsistenciaResponse(alumno_id=alumno_id, registros=registros)
