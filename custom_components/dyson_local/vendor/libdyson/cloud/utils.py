"""Dyson cloud client utilities."""

import base64
import json

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

DYSON_ENCRYPTION_KEY = (
    b"\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10"
    b"\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f "
)
DYSON_ENCRYPTION_INIT_VECTOR = (
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
)


def _unpad(string: str) -> str:
    """Un-pad string."""
    return string[: -ord(string[len(string) - 1 :])]


def decrypt_password(encrypted_password: str) -> str:
    """Decrypt local credential into MQTT password."""
    cipher = Cipher(
        algorithms.AES(DYSON_ENCRYPTION_KEY),
        modes.CBC(DYSON_ENCRYPTION_INIT_VECTOR),
    )
    decryptor = cipher.decryptor()
    encrypted = base64.b64decode(encrypted_password)
    decrypted = decryptor.update(encrypted) + decryptor.finalize()
    json_password = json.loads(_unpad(decrypted))
    return json_password["apPasswordHash"]
