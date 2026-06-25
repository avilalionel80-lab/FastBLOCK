import pytest
from app.crypto.aes import generate_aes_key, encrypt_data, decrypt_data
from app.crypto.shamir import split_secret, reconstruct_secret


class TestAES:
    def test_generate_key(self):
        key = generate_aes_key()
        assert len(key) == 32

    def test_encrypt_decrypt(self):
        key = generate_aes_key()
        data = b"Hello NetShield! This is sensitive data."
        ciphertext, iv = encrypt_data(data, key)
        assert ciphertext != data
        assert len(iv) == 12

        decrypted = decrypt_data(ciphertext, key, iv)
        assert decrypted == data

    def test_wrong_key_fails(self):
        key1 = generate_aes_key()
        key2 = generate_aes_key()
        data = b"secret data"
        ciphertext, iv = encrypt_data(data, key1)
        with pytest.raises(Exception):
            decrypt_data(ciphertext, key2, iv)


class TestShamir:
    def test_split_and_reconstruct(self):
        secret = b"hello" * 10
        shares = split_secret(secret, num_shares=3, threshold=3)
        assert len(shares) == 3
        for share in shares:
            assert len(share) == len(secret) * 2

        recovered = reconstruct_secret(shares)
        assert recovered == secret

    def test_not_enough_shares_fails(self):
        secret = b"test secret"
        shares = split_secret(secret, num_shares=3, threshold=3)
        with pytest.raises(ValueError, match="exactly 3 shares"):
            reconstruct_secret(shares[:2])

    def test_different_length_shares_fails(self):
        shares = [b"\x00\x01\x00\x02", b"\x00\x01\x00\x02\x00\x03", b"\x00\x01\x00\x02"]
        with pytest.raises(ValueError, match="same length"):
            reconstruct_secret(shares)

    def test_full_roundtrip(self):
        original = b"A" * 256
        aes_key = generate_aes_key()
        data = original
        ciphertext, iv = encrypt_data(data, aes_key)
        shares = split_secret(aes_key, num_shares=3, threshold=3)
        recovered_key = reconstruct_secret(shares)
        decrypted = decrypt_data(ciphertext, recovered_key, iv)
        assert decrypted == original
