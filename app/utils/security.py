import bcrypt

def hash_password(password: str) -> str:
    """
    Hashes a plain text password using bcrypt.
    
    Args:
    - password (str): Plain text password to hash.

    Returns:
    - str: A bcrypt hashed password.
    """
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes")
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password against a hashed password.

    Args:
    - plain_password (str): Plain text password to verify.
    - hashed_password (str): Bcrypt hashed password to verify against.

    Returns:
    - bool: True if verification is successful, False otherwise.
    """
    if len(plain_password.encode("utf-8")) > 72:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except (ValueError, TypeError):
        return False
