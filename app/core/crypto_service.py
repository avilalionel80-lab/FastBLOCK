import base64
import os
from typing import List

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from secretsharing import PlaintextToHexSecretSharer

_NONCE_SIZE = 12  # AES-GCM standard nonce size in bytes


class NetShieldCrypto:
    def fragmentar_clave(self, clave_bytes: bytes, minimo: int = 3, total: int = 3) -> List[str]:
        return PlaintextToHexSecretSharer.split_secret(clave_bytes.hex(), minimo, total)

    def reconstruir_clave(self, fragmentos: List[str]) -> bytes:
        return bytes.fromhex(PlaintextToHexSecretSharer.recover_secret(fragmentos))

    def generar_clave_aes(self) -> bytes:
        return AESGCM.generate_key(bit_length=256)

    def cifrar(self, payload: bytes, clave: bytes, nonce: bytes) -> bytes:
        return AESGCM(clave).encrypt(nonce, payload, None)

    def descifrar(self, payload_cifrado: bytes, clave: bytes, nonce: bytes) -> bytes:
        return AESGCM(clave).decrypt(nonce, payload_cifrado, None)

    def generar_nonce(self) -> bytes:
        return os.urandom(_NONCE_SIZE)

    def verificar_firma_ed25519(self, public_key_b64: str, mensaje: bytes, firma_b64: str) -> bool:
        try:
            verify_key = VerifyKey(base64.b64decode(public_key_b64))
            verify_key.verify(mensaje, base64.b64decode(firma_b64))
            return True
        except (BadSignatureError, ValueError, Exception):
            return False
