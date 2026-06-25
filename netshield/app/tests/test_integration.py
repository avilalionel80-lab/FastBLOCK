import pytest
from app.crypto.ed25519 import generate_key_pair, sign_message
from app.crypto.aes import generate_aes_key, encrypt_data, decrypt_data
from app.crypto.shamir import split_secret, reconstruct_secret
from app.blockchain.committee import BlockchainCommittee
from app.blockchain.ledger import MockLedger


@pytest.mark.asyncio
async def test_full_encrypt_decrypt_flow():
    committee = BlockchainCommittee()
    assert committee.mock_mode is True

    data = b'{"alumno_id": "A001", "fecha": "2024-03-15", "presente": true}'
    aes_key = generate_aes_key()
    ciphertext, iv = encrypt_data(data, aes_key)
    shares = split_secret(aes_key, num_shares=3, threshold=3)

    record_id = "test_record_001"
    fragment_ids = []
    for i, share in enumerate(shares):
        fid = f"{record_id}_fragment_{i}"
        fhash = await committee.store_fragment(i, fid, share)
        fragment_ids.append(fhash)

    recovered_shares = []
    for i in range(3):
        fid = f"{record_id}_fragment_{i}"
        share = await committee.get_fragment(i, fid)
        assert share is not None
        recovered_shares.append(share)

    recovered_key = reconstruct_secret(recovered_shares)
    plaintext = decrypt_data(ciphertext, recovered_key, iv)
    assert plaintext == data


@pytest.mark.asyncio
async def test_blockchain_committee_health():
    committee = BlockchainCommittee()
    statuses = await committee.health_check()
    assert statuses["node1"] == "healthy"
    assert statuses["node2"] == "healthy"
    assert statuses["node3"] == "healthy"


@pytest.mark.asyncio
async def test_transaction_and_ledger():
    committee = BlockchainCommittee()
    block_data = {
        "action": "asistencia_marcar",
        "user": "alumno_test",
        "data_hash": "abc123",
        "signature": "test_sig",
    }
    result = await committee.transact(block_data)
    assert result["index"] == 1
    assert result["action"] == "asistencia_marcar"
    assert result["user"] == "alumno_test"

    chain = await committee.get_ledger()
    assert len(chain) == 2

    verify = await committee.verify_ledger()
    assert verify["valid"] is True


@pytest.mark.asyncio
async def test_reset_committee():
    committee = BlockchainCommittee()
    before = len(await committee.get_ledger())
    block_data = {
        "action": "test",
        "user": "u",
        "data_hash": "h",
        "signature": "s",
    }
    await committee.transact(block_data)
    assert len(await committee.get_ledger()) == before + 1
    await committee.reset()
    assert len(await committee.get_ledger()) == 1


@pytest.mark.asyncio
async def test_full_integration():
    private_b64, public_b64 = generate_key_pair()
    message = "netshield_integration_test"
    signature = sign_message(private_b64, message)

    from app.crypto.ed25519 import verify_signature
    assert verify_signature(public_b64, message, signature) is True

    committee = BlockchainCommittee()
    attendance = b'{"alumno_id": "I001", "fecha": "2024-03-15", "presente": true}'
    aes_key = generate_aes_key()
    ciphertext, iv = encrypt_data(attendance, aes_key)
    shares = split_secret(aes_key, 3, 3)

    import hashlib
    data_hash = hashlib.sha256(attendance).hexdigest()
    record_id = "integration_test"

    for i, share in enumerate(shares):
        await committee.store_fragment(i, f"{record_id}_fragment_{i}", share)

    block = await committee.transact({
        "action": "asistencia_marcar",
        "user": "I001",
        "data_hash": data_hash,
        "signature": signature,
    })
    assert block["index"] >= 1

    recovered_shares = []
    for i in range(3):
        s = await committee.get_fragment(i, f"{record_id}_fragment_{i}")
        recovered_shares.append(s)
    recovered_key = reconstruct_secret(recovered_shares)
    decrypted = decrypt_data(ciphertext, recovered_key, iv)
    assert decrypted == attendance

    ledger_verify = await committee.verify_ledger()
    assert ledger_verify["valid"] is True
