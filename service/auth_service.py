
from typing import Tuple, Dict, Any
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.redis import add_jti_to_blocklist
from utils.utils import create_access_token, verify_password
from centralisedErrorHandling.ErrorHandling import AuthenticationError, DatabaseError, UserNotFoundError
from models.models import Users, RoleMaster
from config.config import Config

ACCESS_EXPIRE = getattr(Config, "ACCESS_TOKEN_EXPIRY_SECONDS", 4000)
REFRESH_EXPIRE = getattr(Config, "JTI_EXPIRY_SECONDS", 3600)


async def revoke_jti(jti: str) -> None:
    if not jti:
        return
    try:
        await add_jti_to_blocklist(jti)
    except Exception as e:
        # bubble up as domain error so central handler can decide
        raise DatabaseError("Failed to revoke token", operation="redis.set", table="jti_blocklist", original_error=e)


async def refresh_token_pair(db: AsyncSession, refresh_token_data: Dict[str, Any]) -> Tuple[str, str, int]:

    if not refresh_token_data or not isinstance(refresh_token_data, dict):
        raise AuthenticationError("Invalid refresh token payload")

    jti_old = refresh_token_data.get("jti")
    user_payload = refresh_token_data.get("user")
    if not user_payload or not isinstance(user_payload, dict):
        raise AuthenticationError("Invalid refresh token (no user payload)")

    user_id = user_payload.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise AuthenticationError("Invalid user id in refresh token")

    # Optional: verify user exists
    try:
        user = await db.get(Users, int(user_id))
    except Exception as e:
        raise DatabaseError("DB error while verifying user during token refresh", operation="select", table="users", original_error=e)
    if not user:
        raise UserNotFoundError("User not found for refresh", user_id=user_id)

    # Revoke old refresh token jti (best-effort)
    if jti_old:
        try:
            await revoke_jti(jti_old)
        except DatabaseError:
            pass

    access_exp = int(getattr(Config, "ACCESS_TOKEN_EXPIRY_SECONDS", ACCESS_EXPIRE))

    new_user_claim = user_payload

    new_access = create_access_token(new_user_claim, expiry=timedelta(seconds=access_exp), refresh=False)
    refresh_exp = int(getattr(Config, "JTI_EXPIRY_SECONDS", REFRESH_EXPIRE))
    new_refresh = create_access_token(new_user_claim, expiry=timedelta(seconds=refresh_exp), refresh=True)

    return new_access, new_refresh, access_exp


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Tuple[str, str, int]:


    q = select(Users).where(Users.email == email)
    result = await db.execute(q)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid email or password")

    user_payload = {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email
    }
    

    if user.global_role_id:
        role_q = select(RoleMaster).where(RoleMaster.role_id == user.global_role_id)
        role_result = await db.execute(role_q)
        role = role_result.scalar_one_or_none()
        if role:
            user_payload["global_role"] = {
                "role_id": role.role_id,
                "role_name": role.role_name
            }
    

    access_exp = int(getattr(Config, "ACCESS_TOKEN_EXPIRY_SECONDS", ACCESS_EXPIRE))
    refresh_exp = int(getattr(Config, "JTI_EXPIRY_SECONDS", REFRESH_EXPIRE))
    
    access_token = create_access_token(user_payload, expiry=timedelta(seconds=access_exp), refresh=False)
    refresh_token = create_access_token(user_payload, expiry=timedelta(seconds=refresh_exp), refresh=True)
    
    return access_token, refresh_token, access_exp
