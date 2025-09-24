from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import (
    Users,
    RoleMaster,
    HospitalUserRoles,
    HospitalRole,
    UserPermissions,
    RolePermission,
    PermissionMaster,
    HospitalRolePermission,
)
from collections import defaultdict

async def get_global_role_for_user(db: AsyncSession, user: Users) -> Optional[Dict[str, Any]]:
    """Return {role_id, role_name} for user's global_role_id (if present)."""
    if not user or not user.global_role_id:
        return None
    rm = await db.get(RoleMaster, int(user.global_role_id))
    if not rm:
        return None
    return {"role_id": int(rm.role_id), "role_name": rm.role_name}

async def get_hospital_roles_for_user(db: AsyncSession, user_id: int) -> List[Dict[str, Any]]:
    """Return list like [{'hospital_id':7,'hospital_role_id':101,'role_name':'doctor'}, ...]"""
    out = []
    q = select(HospitalUserRoles).where(HospitalUserRoles.user_id == user_id)
    res = await db.execute(q)
    for hur in res.scalars().all():
        # fetch role name
        hr = await db.get(HospitalRole, int(hur.hospital_role_id))
        role_name = hr.role_name if hr else None
        out.append({
            "hospital_id": int(hur.hospital_id),
            "hospital_role_id": int(hur.hospital_role_id),
            "role_name": role_name,
        })
    return out

async def build_permissions_snapshot(db: AsyncSession, user: Users) -> List[Dict[str, Any]]:
    """
    Build the grouped 'permissions' token claim:
    [
      {"scope":"tenant","hospital_id":7,"permissions":[... ]},
      {"scope":"platform","hospital_id":None,"permissions":[... ]}
    ]
    """
    platform_perms = set()
    tenant_map = defaultdict(set)  # hospital_id -> set(perms)

    user_id = int(user.user_id)

    # 1) direct user_permissions
    try:
        q = select(UserPermissions).where(UserPermissions.user_id == user_id)
        res = await db.execute(q)
        for up in res.scalars().all():
            pname = (up.permission_name or "").strip()
            if not pname:
                continue
            p_scope = (up.scope or "").strip().lower()
            if p_scope == "tenant":
                if up.hospital_id is not None:
                    tenant_map[int(up.hospital_id)].add(pname)
            else:
                platform_perms.add(pname)
    except Exception:
        # swallow here; token snapshot is best-effort
        pass

    # 2) global role permissions (role_permission -> permission_master)
    if user.global_role_id:
        try:
            role_id = int(user.global_role_id)
            rp_q = (
                select(PermissionMaster.permission_name)
                .join(RolePermission, RolePermission.permission_id == PermissionMaster.permission_id)
                .where(RolePermission.role_id == role_id)
            )
            rp_res = await db.execute(rp_q)
            for perm_name in rp_res.scalars().all():
                if perm_name:
                    platform_perms.add(perm_name.strip())
        except Exception:
            pass

    # 3) hospital role permissions (find hospital roles and then gather their permissions)
    try:
        # first get hospital roles mapping (token may not exist yet)
        q = select(HospitalUserRoles).where(HospitalUserRoles.user_id == user_id)
        res = await db.execute(q)
        hospital_roles = res.scalars().all()
        for hur in hospital_roles:
            hid = int(hur.hospital_id)
            hrole_id = int(hur.hospital_role_id)
            hrp_q = (
                select(PermissionMaster.permission_name)
                .join(HospitalRolePermission, HospitalRolePermission.permission_id == PermissionMaster.permission_id)
                .where(HospitalRolePermission.hospital_role_id == hrole_id)
            )
            hrp_res = await db.execute(hrp_q)
            for perm_name in hrp_res.scalars().all():
                if perm_name:
                    tenant_map[hid].add(perm_name.strip())
    except Exception:
        pass

    # Build result list
    out: List[Dict[str, Any]] = []
    if platform_perms:
        out.append({"scope": "platform", "hospital_id": None, "permissions": sorted(platform_perms)})
    for hid, perms in tenant_map.items():
        out.append({"scope": "tenant", "hospital_id": int(hid), "permissions": sorted(perms)})

    return out


async def build_token_user_payload(db: AsyncSession, user: Users) -> Dict[str, Any]:
    """
    Compose the inner 'user' claim for JWT:
    { user_id, username, global_role, hospital_roles, permissions }
    """
    global_role = await get_global_role_for_user(db, user)
    hospital_roles = await get_hospital_roles_for_user(db, user.user_id)
    permissions_snapshot = await build_permissions_snapshot(db, user)

    return {
        "user_id": int(user.user_id),
        "username": user.username,
        "global_role": global_role,
        "hospital_roles": hospital_roles,
        "permissions": permissions_snapshot,
    }