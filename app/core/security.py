from datetime import datetime, timedelta, timezone
from typing import Any, Union
import hashlib
import os
import jwt  # PyJWT 사용
from app.core.config import settings

ALGORITHM = "HS256"


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # PBKDF2 순수 파이썬 해싱 검증 (salt$hash 형태 구조 분해)
        if "$" not in hashed_password:
            return False
        salt, key = hashed_password.split("$", 1)
        new_key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            bytes.fromhex(salt),
            100000
        ).hex()
        return new_key == key
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    # 암호화용 난수 Salt 추출 (os.urandom)
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100000
    ).hex()
    return f"{salt.hex()}${key}"

