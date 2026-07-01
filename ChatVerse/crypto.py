from cryptography.fernet import Fernet, InvalidToken
import config
import pickle
from typing import Any

fernet = Fernet(config.FERNET_KEY)

def encrypt_object(obj: Any) -> bytes:
    """
    Pickle and encrypt a Python object.
    """
    raw = pickle.dumps(obj)
    token = fernet.encrypt(raw)
    return token

def decrypt_object(token: bytes) -> Any:
    """
    Decrypt and unpickle a Python object.
    """
    try:
        raw = fernet.decrypt(token)
        obj = pickle.loads(raw)
        return obj
    except InvalidToken:
        raise ValueError("Invalid encryption token")

def encrypt_bytes(data: bytes) -> bytes:
    return fernet.encrypt(data)

def decrypt_bytes(token: bytes) -> bytes:
    try:
        return fernet.decrypt(token)
    except InvalidToken:
        raise ValueError("Invalid encryption token")
