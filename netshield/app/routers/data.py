import json
import hashlib
import uuid
from fastapi import APIRouter, HTTPException, Depends
from loguru import logger
from app.database import get_connection
from app.crypto.aes import generate_aes_key, encrypt_data, decrypt_data
from app.crypto.shamir import split_secret, reconstruct_secret
from app.blockchain.committee import BlockchainCommittee
from app.models import EncryptRequest, EncryptResponse, DecryptResponse
from app.dependencies import auth_required

router = APIRouter(prefix="/data", tags=["data"])


@router.post("/encrypt", response_model=EncryptResponse)
async def encrypt_data_endpoint(req: EncryptRequest, _=Depends(auth_required)):
    committee = BlockchainCommittee()
    data_bytes = json.dumps(req.data, ensure_ascii=False).encode("utf-8")
    aes_key = generate_aes_key()
    ciphertext, iv = encrypt_data(data_bytes, aes_key)
    shares = split_secret(aes_key, num_shares=3, threshold=3)

    record_id = str(uuid.uuid4())
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
                req.owner,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    logger.info(f"Data encrypted and stored: {record_id}")
    return EncryptResponse(record_id=record_id, fragment_hashes=fragment_hashes)


@router.get("/decrypt/{record_id}", response_model=DecryptResponse)
async def decrypt_data_endpoint(record_id: str, _=Depends(auth_required)):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM data_records WHERE id = ?", (record_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Record not found")
    finally:
        conn.close()

    committee = BlockchainCommittee()
    shares = []
    fragment_ids = [
        f"{record_id}_fragment_0",
        f"{record_id}_fragment_1",
        f"{record_id}_fragment_2",
    ]
    for i, fid in enumerate(fragment_ids):
        share = await committee.get_fragment(i, fid)
        if share is None:
            raise HTTPException(
                status_code=503,
                detail=f"Fragment {i} not available from node {i + 1}",
            )
        shares.append(share)

    aes_key = reconstruct_secret(shares)
    ciphertext = bytes.fromhex(row["encrypted_data"])
    iv = bytes.fromhex(row["iv"])
    plaintext = decrypt_data(ciphertext, aes_key, iv)
    data = json.loads(plaintext.decode("utf-8"))

    logger.info(f"Data decrypted: {record_id}")
    return DecryptResponse(record_id=record_id, data=data)
