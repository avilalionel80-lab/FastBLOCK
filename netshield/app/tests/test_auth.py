import pytest
from app.crypto.ed25519 import generate_key_pair, verify_signature, sign_message


class TestAuth:
    def test_generate_key_pair(self):
        private_b64, public_b64 = generate_key_pair()
        assert private_b64
        assert public_b64
        assert len(private_b64) > 0
        assert len(public_b64) > 0

    def test_sign_and_verify(self):
        private_b64, public_b64 = generate_key_pair()
        message = "hello netshield"
        signature = sign_message(private_b64, message)
        assert verify_signature(public_b64, message, signature) is True

    def test_verify_wrong_message(self):
        private_b64, public_b64 = generate_key_pair()
        signature = sign_message(private_b64, "real message")
        assert verify_signature(public_b64, "fake message", signature) is False

    def test_verify_wrong_key(self):
        private_b64, _ = generate_key_pair()
        _, public_b64_2 = generate_key_pair()
        signature = sign_message(private_b64, "test")
        assert verify_signature(public_b64_2, "test", signature) is False

    def test_verify_tampered_signature(self):
        private_b64, public_b64 = generate_key_pair()
        signature = sign_message(private_b64, "test")
        tampered = "A" * len(signature)
        assert verify_signature(public_b64, "test", tampered) is False
