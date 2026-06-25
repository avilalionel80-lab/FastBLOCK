import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.config import get_settings


def generate_aes_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def encrypt_data(data: bytes, key: bytes) -> tuple:
    aesgcm = AESGCM(key)
    iv = os.urandom(12)
    ciphertext = aesgcm.encrypt(iv, data, None)
    return ciphertext, iv


def decrypt_data(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(iv, ciphertext, None)
    return plaintext
