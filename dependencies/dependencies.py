from fastapi.security import HTTPBearer
from fastapi import Request, status, Depends, HTTPException
from typing import Callable, Iterable, Optional, Any, Dict, Sequence, Set, List
from database.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, union_all
from utils.utils import decode_token
from database.redis import token_in_blocklist
import json
import logging
from database.redis import _redis_client
from models.models import (
    Users,
    RoleMaster,
    RolePermission,
    PermissionMaster,
    HospitalUserRoles,
    HospitalRolePermission,
    UserPermissions,
    HospitalMaster,
    Specialties,
    HospitalRole
)
CACHE_TTL = 120 

logger = logging.getLogger(__name__)

def _normalize_perm(p: str) -> str:
    return p.strip().lower()

def is_super_admin(user: Dict[str, Any]) -> bool:
    if not user or not isinstance(user, dict):
        return False
    global_role = user.get("global_role")
    if not isinstance(global_role, dict):
        return False
    rname = global_role.get("role_name")
    return isinstance(rname, str) and rname.strip().lower() == "superadmin"

class TokenBearer(HTTPBearer):
    async def __call__(self, request: Request) -> Dict[str, Any] | None:
        creds = await super().__call__(request)
        token = creds.credentials if creds else None
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token")
        if not isinstance(token, str) or not token.strip():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format")
        token_data = decode_token(token)
        if token_data is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error": "Invalid or expired token", "resolution": "Please authenticate again"})
        jti = token_data.get("jti")
        if jti and await token_in_blocklist(jti):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error": "Token has been revoked", "resolution": "Please authenticate again"})
        self.verify_token_data(token_data)
        user_data = token_data.get("user")
        user_id = user_data.get("user_id") if isinstance(user_data, dict) else None
        if not isinstance(user_id, int) or user_id <= 0:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user identifier in token")
        return token_data

    def token_valid(self, token: str) -> bool:
        token_data = decode_token(token)
        return token_data is not None

    def verify_token_data(self, token_data):
        raise NotImplementedError

class AccessTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data and token_data.get("refresh"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token required, refresh provided")

class RefreshTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict) -> None:
        if token_data and not token_data.get("refresh"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required, access token provided")


async def get_current_user(token_details: dict = Depends(AccessTokenBearer())) -> Dict[str, Any]:
    if not token_details:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No valid token provided")
    user_payload = token_details.get("user")
    if not user_payload or not isinstance(user_payload, dict):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user data in token")
    user_id = user_payload.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user identifier")
    return user_payload


def require_global_roles(role_names: Optional[Iterable[str]] = None, role_ids: Optional[Iterable[int]] = None, allow_super_admin: bool = True) -> Callable:
    role_names_set: Set[str] = set(n.strip().lower() for n in (role_names or []) if isinstance(n, str) and n.strip())
    role_ids_set: Set[int] = set(r for r in (role_ids or []) if isinstance(r, int) and r > 0)

    async def dependency(user: Dict[str, Any] = Depends(get_current_user)):
        if allow_super_admin and is_super_admin(user):
            logger.info(f"Superadmin bypass (role check) for user {user.get('user_id')}")
            return user
        if not role_names_set and not role_ids_set:
            return user
        user_role = user.get("global_role")
        if not isinstance(user_role, dict):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no global role assigned")
        if role_ids_set:
            rid = user_role.get("role_id")
            if isinstance(rid, int) and rid in role_ids_set:
                return user
        if role_names_set:
            rname = user_role.get("role_name")
            if isinstance(rname, str) and rname.strip().lower() in role_names_set:
                return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role privileges")
    return dependency


async def get_user_permissions(
        user_id: int, 
        db: AsyncSession, 
        hospital_id: Optional[int] = None) -> Set[str]:
    cache_chabbhi = f"user:{user_id}:hospital:{hospital_id or 'global'}:perms"  

    cached = await _redis_client.get(cache_chabbhi)
    if cached:
        return set(json.loads(cached))
    
    direct_q = (
        select(UserPermissions.permission_name).where(UserPermissions.user_id == user_id)
    )
    global_q = (select(PermissionMaster.permission_name).join(RolePermission, RolePermission.permission_id == PermissionMaster.permission_id)
        .join(RoleMaster, RoleMaster.role_id == RolePermission.role_id)
        .where(RoleMaster.role_id == Users.global_role_id))
    
    hospital_q = (select(PermissionMaster.permission_name).join(HospitalRolePermission, HospitalRolePermission.permission_id == PermissionMaster.permission_id)
     .join(HospitalUserRoles, HospitalUserRoles.hospital_role_id == HospitalRolePermission.hospital_role_id)
     .where(HospitalUserRoles.user_id == user_id))
    
    if hospital_id:
        hospital_q = hospital_q.where(HospitalUserRoles.hospital_id == hospital_id)
    final_q = union_all(direct_q, global_q, hospital_q)

    execution = await db.execute(final_q)
    perms = set(p.strip().lower() for p in execution.scalars().all() if p)

    await _redis_client.set(cache_chabbhi, json.dumps(list(perms)), ex=CACHE_TTL)
    return perms

def require_permissions(permissions: Sequence[str], scope: Optional[str] = None, hospital_id_param: str = "hospital_id", allow_super_admin: bool = True) -> Callable:
    required = {_normalize_perm(p) for p in permissions}

    async def dependency(request: Request, user: Dict[str, Any] = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        if allow_super_admin and is_super_admin(user):
            return user
        
        user_id = user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user")


        hospital_id = None
        if hospital_id_param in request.path_params:
            hospital_id = int(request.path_params[hospital_id_param])

        cache_key = f"permcheck:user:{user_id}:hospital:{hospital_id or 'global'}:{','.join(sorted(required))}"
        cached = await _redis_client.get(cache_key)
        if cached:
            result = json.loads(cached)
            if result["allowed"]:
                return user
            raise HTTPException(status_code=403, detail=f"Missing permissions: {sorted(result['missing'])}")

        
        found = await get_user_permissions(user_id, db, hospital_id=hospital_id)

        
        missing = required - found
        "cache miss bhai"
        if missing:
            await _redis_client.set(cache_key, json.dumps({"allowed": False, "missing": list(missing)}), ex=CACHE_TTL)
            raise HTTPException(status_code=403, detail=f"Missing permissions: {sorted(missing)}")
        "cache success bhai"
        await _redis_client.set(cache_key, json.dumps({"allowed": True}), ex=CACHE_TTL)
        logger.info(f"Permission check passed for user {user_id}")
        return user
    return dependency

"""
STALE PERMISSION INVALIDATION
"""
async def invalidate_user_permission_from_cache(user_id: int, hospital_id: Optional[int]= None):
    hospital_key = hospital_id or "global"
    perms_key = f"user:{user_id}:hospital:{hospital_key}:perms"
    await _redis_client.delete(perms_key)
    logger.info(f"Permission cache invalidated for user {user_id} and hospital {hospital_id}")
    pattern_for_permcheck = f"permcheck:user:{user_id}:hospital:{hospital_key}:*"
    async for key in _redis_client.scan_iter(match=pattern_for_permcheck):
        await _redis_client.delete(key)

"""
bulk wala invalidation agar saarey invalidate hojaye toh 
"""
async def invalidate_hospital_role_cache(hospital_role_id: int, hospital_id: int, db: AsyncSession):
    q = select(HospitalUserRoles.user_id).where(HospitalUserRoles.hospital_role_id == hospital_role_id)
    res = await db.execute(q)
    for (user_id,) in res.all():
        await invalidate_user_permission_from_cache(user_id, hospital_id=hospital_id)


"""

ye helper function use karna hai consistency match.

"""
async def ensure_hospital_exists(hospital_id: int, db: AsyncSession = Depends(get_db))-> int:
    if not hospital_id or int(hospital_id) <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid hai id")
    try:
        row = await db.get(HospitalMaster, hospital_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Hospital {hospital_id} not found")
        return int(hospital_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching hospital {hospital_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

async def ensure_specialties_exist(specialty_ids: Iterable[int], db: AsyncSession = Depends(get_db)) -> List[int]:
    ids = [int(x) for x in specialty_ids if x is not None]
    if not ids:
        return []
    try:
        q = select(Specialties.specialty_id).where(Specialties.specialty_id.in_(ids))
        res = await db.execute(q)
        found = set(res.scalars().all() or [])
        missing = sorted([i for i in ids if i not in found])
        if missing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "Missing specialties", "missing_ids": missing}
            )
        return list(found)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking specialties: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


async def ensure_user_exists(user_id: int, db: AsyncSession = Depends(get_db)) -> int:
    if not user_id or int(user_id) <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid user id")
    try:
        row = await db.get(Users, user_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")
        return int(user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

async def ensure_hospital_role_belongs_to_hospital(
        hospital_id: int,
        role_id:int,
        db: AsyncSession = Depends(get_db)
):
    q = await db.execute(select(HospitalRole).where(HospitalRole.hospital_role_id == role_id,
                                                     HospitalRole.hospital_id == hospital_id,
                                                     HospitalRole.is_active == True)) 
    hr = q.scalar_one_or_none()
    if not hr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Hospital role {role_id} not found in hospital {hospital_id}")
    return hr



async def ensure_user_belongs_to_hospital(user_id: int, hospital_id:int, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(HospitalUserRoles).where(HospitalUserRoles.user_id == user_id,
                                                         HospitalUserRoles.hospital_id == hospital_id,
                                                         HospitalUserRoles.is_active == True))
           
    hru = q.scalar_one_or_none()
    if not hru:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found in hospital {hospital_id}")
    return hru 









































































































# def require_permissions(permissions: Sequence[str], scope: Optional[str] = None, hospital_id_param: str = "hospital_id", allow_super_admin: bool = True) -> Callable:
#     if not permissions:
#         raise ValueError("At least one permission must be specified")
#     required: Set[str] = set(_normalize_perm(p) for p in permissions if isinstance(p, str) and p.strip())
#     if not required:
#         raise ValueError("No valid permissions provided")
#     if scope is not None and scope.lower() not in {"platform", "tenant"}:
#         raise ValueError("scope must be 'platform' or 'tenant' if provided")

#     async def dependency(request: Request, user: Dict[str, Any] = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
#         try:
#             if not user or not isinstance(user, dict):
#                 raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user data")
#             user_id = user.get("user_id")
#             if not isinstance(user_id, int) or user_id <= 0:
#                 raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user identifier")

#             if allow_super_admin and is_super_admin(user):
#                 logger.info(f"Superadmin bypass (permission check) for user {user_id}")
#                 return user

            
#             hospital_id: Optional[int] = None
#             if hospital_id_param:
#                 if hospital_id_param in request.path_params:
#                     try:
#                         hospital_id = int(request.path_params[hospital_id_param])
#                         if hospital_id <= 0:
#                             hospital_id = None
#                     except (TypeError, ValueError):
#                         hospital_id = None
#                 elif hospital_id_param in request.query_params:
#                     try:
#                         hospital_id = int(request.query_params[hospital_id_param])
#                         if hospital_id <= 0:
#                             hospital_id = None
#                     except (TypeError, ValueError):
#                         hospital_id = None

#             found_perms: Set[str] = set()

            
#             try:
#                 q = select(UserPermissions).where(UserPermissions.user_id == user_id)
#                 res = await db.execute(q)
#                 ups = res.scalars().all()
#                 for up in ups:
#                     pname = (up.permission_name or "").strip().lower()
#                     if not pname:
#                         continue
#                     p_scope = (up.scope or "").strip().lower()
#                     if scope and p_scope != scope.lower():
#                         continue
#                     if hospital_id is not None and up.hospital_id is not None and int(up.hospital_id) != hospital_id:
#                         continue
#                     found_perms.add(pname)
#             except Exception:
#                 logger.exception("Failed to fetch user permissions for user %s", user_id)

            
#             global_role = user.get("global_role")
#             if isinstance(global_role, dict):
#                 try:
#                     role_id = global_role.get("role_id")
#                     if isinstance(role_id, int) and role_id > 0:
#                         # IMPORTANT: use an ORM join instead of __table__.join
#                         rp_q = (
#                             select(PermissionMaster.permission_name)
#                             .join(RolePermission, RolePermission.permission_id == PermissionMaster.permission_id)
#                             .where(RolePermission.role_id == role_id)
#                         )
#                         rp_res = await db.execute(rp_q)
#                         for perm_name in rp_res.scalars().all():
#                             if not perm_name:
#                                 continue
#                             pname = perm_name.strip().lower()
#                             if not pname:
#                                 continue
#                             if scope and scope.lower() == "tenant":
#                                 continue
#                             found_perms.add(pname)
#                 except Exception:
#                     logger.exception("Failed to fetch role permissions for role_id=%s", global_role)

           
#             try:
#                 hospital_roles = []
#                 token_hospital_roles = user.get("hospital_roles")
#                 if isinstance(token_hospital_roles, list):
#                     for hr in token_hospital_roles:
#                         if isinstance(hr, dict):
#                             hid = hr.get("hospital_id")
#                             hrole = hr.get("hospital_role_id")
#                             if isinstance(hid, int) and hid > 0 and isinstance(hrole, int) and hrole > 0:
#                                 hospital_roles.append({"hospital_id": hid, "hospital_role_id": hrole})
#                 else:
#                     hur_q = select(HospitalUserRoles).where(HospitalUserRoles.user_id == user_id)
#                     hur_res = await db.execute(hur_q)
#                     for hur in hur_res.scalars().all():
#                         if hur.hospital_id and hur.hospital_role_id:
#                             if int(hur.hospital_id) > 0 and int(hur.hospital_role_id) > 0:
#                                 hospital_roles.append({"hospital_id": int(hur.hospital_id), "hospital_role_id": int(hur.hospital_role_id)})

#                 for hr in hospital_roles:
#                     hr_hid = hr["hospital_id"]
#                     hr_rid = hr["hospital_role_id"]
#                     if hospital_id is not None and hr_hid != hospital_id:
#                         continue
#                     hrp_q = (
#                         select(PermissionMaster.permission_name)
#                         .join(HospitalRolePermission, HospitalRolePermission.permission_id == PermissionMaster.permission_id)
#                         .where(HospitalRolePermission.hospital_role_id == hr_rid)
#                     )
#                     hrp_res = await db.execute(hrp_q)
#                     for perm_name in hrp_res.scalars().all():
#                         if not perm_name:
#                             continue
#                         pname = perm_name.strip().lower()
#                         if not pname:
#                             continue
#                         if scope and scope.lower() == "platform":
#                             continue
#                         found_perms.add(pname)
#             except Exception:
#                 logger.exception("Failed to fetch hospital role permissions for user %s", user_id)

#             missing = required - found_perms
#             if missing:
#                 logger.warning("User %s missing permissions %s (required %s, found %s)", user_id, missing, required, found_perms)
#                 raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Insufficient permissions: missing {sorted(missing)}")

#             return user

#         except HTTPException:
#             raise
#         except Exception:
#             logger.exception("Unexpected error during permission check for user %s", user.get("user_id") if user else None)
#             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Permission check failed")

#     return dependency
