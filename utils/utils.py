from passlib.context import CryptContext
from datetime import timedelta, datetime, timezone
import uuid
import logging
from config.config import Config
import jwt 
logger = logging.getLogger(__name__)
passwd_context = CryptContext(schemes=["bcrypt"])

def generate_passwd_hash(password: str) -> str:
    return passwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return passwd_context.verify(password, hashed)


def create_access_token(user_data: dict, expiry: timedelta | None = None, refresh: bool = False) -> str:
    now = datetime.now(tz=timezone.utc)
    exp = now + (expiry if expiry is not None else timedelta(seconds=getattr(Config, "ACCESS_TOKEN_EXPIRY_SECONDS", 4000)))

    payload = {
        "user": user_data,
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "refresh": bool(refresh),
    }
    token = jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)
    return token

def decode_token(token: str) -> dict | None:
    try:
        token_data = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
        return token_data
    except Exception as e:
        logger.exception("JWT decode failed: %s", e)
        return None

