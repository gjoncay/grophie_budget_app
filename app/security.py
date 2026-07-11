from pathlib import Path

from cryptography.fernet import Fernet

from app import config

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _persist_key(key: str) -> None:
    if _ENV_PATH.exists() and "TOKEN_ENCRYPTION_KEY=" in _ENV_PATH.read_text():
        lines = [
            f"TOKEN_ENCRYPTION_KEY={key}" if line.startswith("TOKEN_ENCRYPTION_KEY=") else line
            for line in _ENV_PATH.read_text().splitlines()
        ]
        _ENV_PATH.write_text("\n".join(lines) + "\n")
    else:
        with _ENV_PATH.open("a") as f:
            f.write(f"\nTOKEN_ENCRYPTION_KEY={key}\n")


def _get_key() -> bytes:
    key = config.TOKEN_ENCRYPTION_KEY
    if not key:
        key = Fernet.generate_key().decode()
        _persist_key(key)
        config.TOKEN_ENCRYPTION_KEY = key
    return key.encode()


def encrypt(value: str) -> str:
    return Fernet(_get_key()).encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    return Fernet(_get_key()).decrypt(token.encode()).decode()
