from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

ph = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    try:
        return ph.verify(plain_password, hashed_password)
    except UnknownHashError:
        return False
