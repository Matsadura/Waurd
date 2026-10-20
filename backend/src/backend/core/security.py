import secrets


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return secrets.compare_digest(plain_password, hashed_password)
