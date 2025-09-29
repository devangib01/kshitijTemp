from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import timedelta

from models.models import (
    HospitalMaster, HospitalRole, Users, HospitalUserRoles,
    PermissionMaster, HospitalRolePermission
)
from utils.utils import generate_passwd_hash, create_access_token
from utils.validators import validate_email, validate_password, validate_username, sanitize_string, validate_phone
from centralisedErrorHandling.ErrorHandling import ValidationError, DatabaseError
from config.config import Config
ACCESS_EXPIRE = getattr(Config, "ACCESS_TOKEN_EXPIRY_SECONDS", 4000)
REFRESH_EXPIRE = getattr(Config, "JTI_EXPIRY_SECONDS", 3600)

HOSPITAL_ADMIN_PERMISSIONS = [
    'hospital.profile.view', 'hospital.profile.update',
    'hospital.specialities.list', 'hospital.speciality.create', 
    'hospital.speciality.update', 'hospital.speciality.delete',
    'hospital.doctors.list', 'hospital.doctor.create', 
    'hospital.doctor.update', 'hospital.doctor.delete', 
    'hospital.doctor.performance.view',
    'hospital.patients.list',
    'doctor.view', 'doctor.profile.view', 'doctor.profile.update',
    'patient.profile.view', 'patient.profile.update', 
    'patient.profile.avatar.upload',
    'patient.consultation.list', 'upload.profile_image', 'upload.profile_audio',
    'hospital.role.create', 'hospital.role.view', 
    'hospital.role.manage_permissions', 'hospital.user.assign_role', 
    'hospital.role.delete'
]


async def _fetch_permissions_by_names(db: AsyncSession, permission_names: List[str]) -> List[PermissionMaster]:
    """
    Fetch permissions by name and validate all exist.
    Raises ValidationError if any permissions are missing.
    """
    query = select(PermissionMaster).where(
        PermissionMaster.permission_name.in_(permission_names)
    )
    result = await db.execute(query)
    permissions = result.scalars().all()
    
    if len(permissions) != len(permission_names):
        found_names = {p.permission_name for p in permissions}
        missing = set(permission_names) - found_names
        raise ValidationError(
            f"Missing required permissions in database: {', '.join(missing)}"
        )
    
    return list(permissions)


async def _check_hospital_exists(db: AsyncSession, hospital_name: str) -> bool:
    """Check if hospital with given name already exists."""
    query = select(HospitalMaster).where(
        HospitalMaster.hospital_name == hospital_name
    )
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def _check_user_exists(
    db: AsyncSession, 
    email: str, 
    username: str
) -> bool:
    """Check if user with given email or username already exists."""
    query = select(Users).where(
        (Users.email == email) | (Users.username == username)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def create_hospital_with_admin(
    db: AsyncSession,
    *,
    hospital_name: str,
    hospital_email: Optional[str] = None,
    admin_email: str,
    admin_password: str,
    admin_username: Optional[str] = None,
    admin_first_name: Optional[str] = None,
    admin_last_name: Optional[str] = None,
    admin_phone: Optional[str] = None,
    auto_login: bool = True,
    permission_names: Optional[List[str]] = None
) -> Dict[str, Any]:

    try:
        hospital_name = sanitize_string(hospital_name, max_length=255, allow_none=False)
        admin_email = validate_email(admin_email)
        admin_password = validate_password(admin_password)
        

        if hospital_email:
            hospital_email = validate_email(hospital_email)
        

        if admin_username:
            admin_username = validate_username(admin_username)
        else:
            admin_username = admin_email.split("@", 1)[0]
        
        admin_phone = validate_phone(admin_phone, required=False)
        
    except ValidationError:
        raise ValidationError("Lmao Galat data hai")


    perms_to_assign = permission_names or HOSPITAL_ADMIN_PERMISSIONS

    try:

        if await _check_hospital_exists(db, hospital_name):
            raise ValidationError(f"Hospital with name '{hospital_name}' already exists")
        
        if await _check_user_exists(db, admin_email, admin_username):
            raise ValidationError(
                f"User with email '{admin_email}' or username '{admin_username}' already exists"
            )
        
       
        permissions = await _fetch_permissions_by_names(db, perms_to_assign)
        
        async with db.begin():
            # Create hospital
            hospital = HospitalMaster(
                hospital_name=hospital_name,
                hospital_email=hospital_email,
                admin_contact=admin_phone
            )
            db.add(hospital)
            await db.flush()
            
            hospital_id = hospital.hospital_id

            # Create hospital role
            hospital_role = HospitalRole(
                hospital_id=hospital_id,
                role_name="hospital_admin",
                description="Administrator for this hospital (tenant-scoped)",
                is_active=1
            )
            db.add(hospital_role)
            await db.flush()
            
            hospital_role_id = hospital_role.hospital_role_id

            # Create admin user
            admin_user = Users(
                username=admin_username,
                email=admin_email,
                password_hash=generate_passwd_hash(admin_password),
                first_name=admin_first_name,
                last_name=admin_last_name,
                phone=admin_phone
            )
            db.add(admin_user)
            await db.flush()
            
            user_id = admin_user.user_id

            # Assign user to hospital with role
            hospital_user_role = HospitalUserRoles(
                hospital_id=hospital_id,
                user_id=user_id,
                hospital_role_id=hospital_role_id,
                is_active=1
            )
            db.add(hospital_user_role)

            # Batch assign permissions to role
            role_permissions = [
                HospitalRolePermission(
                    hospital_role_id=hospital_role_id,
                    permission_id=perm.permission_id
                )
                for perm in permissions
            ]
            db.add_all(role_permissions)
            
            await db.flush()

        # Transaction commits here
        
    except ValidationError:
        raise
    except IntegrityError as ie:
        raise DatabaseError(
            "Database integrity error during hospital onboarding. "
            "This may indicate a duplicate entry or foreign key violation.",
            operation="insert",
            table="hospital_master/hospital_role/users",
            original_error=ie
        )
    except Exception as e:
        raise DatabaseError(
            "Unexpected error during hospital and admin creation",
            operation="transaction",
            table="hospital_master",
            original_error=e
        )

    # Prepare response
    result: Dict[str, Any] = {
        "hospital_id": hospital_id,
        "hospital_name": hospital.hospital_name,
        "hospital_email": hospital.hospital_email,
        "admin_user_id": user_id,
        "admin_username": admin_user.username,
        "admin_email": admin_user.email,
        "permissions_assigned": len(permissions)
    }

    # Generate tokens if auto_login is enabled
    if auto_login:
        user_payload = {
            "user_id": user_id,
            "username": admin_user.username,
            "email": admin_user.email,
            "hospital_roles": [{
                "hospital_id": hospital_id,
                "hospital_role_id": hospital_role_id,
                "role_name": hospital_role.role_name
            }]
        }
        
        access_token = create_access_token(
            user_payload, 
            expiry=timedelta(seconds=ACCESS_EXPIRE), 
            refresh=False
        )
        refresh_token = create_access_token(
            user_payload, 
            expiry=timedelta(seconds=REFRESH_EXPIRE), 
            refresh=True
        )
        
        result.update({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_EXPIRE
        })

    return result