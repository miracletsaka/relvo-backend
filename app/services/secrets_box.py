"""
Encrypts secrets (like a Retell API key) before they go into the database.
    pip install cryptography
Create the key once and add it to backend/.env (and to Render's environment):
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    SECRETS_ENC_KEY=<the printed value>
"""
import os

from cryptography.fernet import Fernet


def _box() -> Fernet:
    key = os.getenv("SECRETS_ENC_KEY")
    if not key:
        raise RuntimeError("SECRETS_ENC_KEY is not set")
    return Fernet(key.encode())


def encrypt(text: str) -> str:
    return _box().encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    return _box().decrypt(token.encode()).decode()