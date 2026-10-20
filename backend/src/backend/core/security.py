from pwdlib import PasswordHash

ph = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return ph.verify(hashed_password, plain_password)
