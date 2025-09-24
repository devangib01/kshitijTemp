# hospitals_service.py
from typing import Optional, List, Dict, Any
from sqlalchemy import select, delete, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from models import (
    HospitalMaster, HospitalUserRoles, t_doctor_hospitals,
    Users, UserDetails, Specialties, PatientHospitals
)
from centralisedErrorHandling.ErrorHandling import ValidationError, DatabaseError, UserNotFoundError, AuthorizationError
from utils.validators import validate_name, validate_email, validate_phone

# Helper: find hospital_id associated with caller
async def _resolve_hospital_id_for_user(db: AsyncSession, caller: Dict[str, Any]) -> Optional[int]:
    """
    Try to resolve hospital_id for a caller in this order:
    - If caller token contains 'hospital_id' at top level, use it.
    - Else, find an active HospitalUserRoles mapping for caller.user_id and return the hospital_id of the first mapping.
    - Return None if not found.
    """
    if not caller or not isinstance(caller, dict):
        return None
    # token may embed hospital_id directly
    hid = caller.get("hospital_id")
    if isinstance(hid, int) and hid > 0:
        return hid
    # otherwise lookup in hospital_user_roles
    user_id = caller.get("user_id")
    if not user_id:
        return None
    try:
        q = select(HospitalUserRoles).where(HospitalUserRoles.user_id == int(user_id), HospitalUserRoles.is_active == 1)
        res = await db.execute(q)
        row = res.scalars().first()
        if row:
            return int(row.hospital_id)
        return None
    except Exception as e:
        # bubble up as DatabaseError
        raise DatabaseError("Failed resolving hospital for user", operation="select", table="hospital_user_roles", original_error=e)


# ----------------------------
# Hospital profile
# ----------------------------
async def get_hospital_profile(db: AsyncSession, hospital_id: int) -> Dict[str, Any]:
    try:
        hospital = await db.get(HospitalMaster, int(hospital_id))
        if not hospital:
            raise UserNotFoundError("Hospital not found", user_id=hospital_id)
        return {
            "hospital_id": int(hospital.hospital_id),
            "hospital_name": hospital.hospital_name,
            "hospital_email": hospital.hospital_email,
            "admin_contact": hospital.admin_contact,
            "address": hospital.address,
            "created_at": hospital.created_at.isoformat() if hospital.created_at else None,
            "updated_at": hospital.updated_at.isoformat() if hospital.updated_at else None
        }
    except UserNotFoundError:
        raise
    except Exception as e:
        raise DatabaseError("Failed to fetch hospital profile", operation="select", table="hospital_master", original_error=e)


async def update_hospital_profile(db: AsyncSession, hospital_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update hospital profile fields: hospital_name, hospital_email, admin_contact, address
    """
    # validation helpers with safe fallbacks
    try:
        hospital = await db.get(HospitalMaster, int(hospital_id))
        if not hospital:
            raise UserNotFoundError("Hospital not found", user_id=hospital_id)
    except UserNotFoundError:
        raise
    except Exception as e:
        raise DatabaseError("Failed to fetch hospital for update", operation="select", table="hospital_master", original_error=e)

    try:
        if "hospital_name" in payload and payload["hospital_name"] is not None:
            hospital.hospital_name = validate_name(payload["hospital_name"], field_name="hospital_name") if "validate_name" in globals() else str(payload["hospital_name"]).strip()
        if "hospital_email" in payload and payload["hospital_email"] is not None:
            hospital.hospital_email = validate_email(payload["hospital_email"]) if "validate_email" in globals() else str(payload["hospital_email"]).strip()
        if "admin_contact" in payload and payload["admin_contact"] is not None:
            hospital.admin_contact = validate_phone(payload["admin_contact"], required=False) if "validate_phone" in globals() else str(payload["admin_contact"]).strip()
        if "address" in payload and payload["address"] is not None:
            hospital.address = str(payload["address"]).strip()

        db.add(hospital)
        await db.commit()
        await db.refresh(hospital)
        return {"status": "updated", "hospital_id": int(hospital.hospital_id)}
    except ValidationError:
        raise
    except Exception as e:
        await db.rollback()
        raise DatabaseError("Failed to update hospital profile", operation="update", table="hospital_master", original_error=e)


# ----------------------------
# Hospital specialties (treat as global specialties table)
# ----------------------------
async def list_specialities(db: AsyncSession, active_only: bool = True) -> List[Dict[str, Any]]:
    try:
        q = select(Specialties)
        if active_only:
            q = q.where(Specialties.status == "active")
        q = q.order_by(Specialties.name)
        res = await db.execute(q)
        rows = res.scalars().all()
        return [
            {
                "specialty_id": int(r.specialty_id),
                "name": r.name,
                "description": r.description,
                "status": r.status
            }
            for r in rows
        ]
    except Exception as e:
        raise DatabaseError("Failed to list specialties", operation="select", table="specialties", original_error=e)


async def create_speciality(db: AsyncSession, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a specialty row. Hospital admins can create global specialties.
    Required: name
    Optional: description, status
    """
    name = payload.get("name")
    if not name or not str(name).strip():
        raise ValidationError("Specialty 'name' is required")
    name = str(name).strip()

    description = payload.get("description")
    status = payload.get("status", "active")

    try:
        # ensure uniqueness
        q = select(Specialties).where(Specialties.name == name)
        res = await db.execute(q)
        if res.scalars().first():
            raise ValidationError("Specialty with that name already exists")

        spec = Specialties(name=name, description=description, status=status)
        db.add(spec)
        await db.commit()
        await db.refresh(spec)
        return {"specialty_id": int(spec.specialty_id), "name": spec.name}
    except ValidationError:
        raise
    except IntegrityError as ie:
        await db.rollback()
        raise ValidationError("Specialty could not be created (integrity error)", context={"detail": str(ie)})
    except Exception as e:
        await db.rollback()
        raise DatabaseError("Failed to create specialty", operation="insert", table="specialties", original_error=e)


async def update_speciality(db: AsyncSession, specialty_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        spec = await db.get(Specialties, int(specialty_id))
        if not spec:
            raise UserNotFoundError("Specialty not found", user_id=specialty_id)

        if "name" in payload and payload["name"] is not None:
            new_name = str(payload["name"]).strip()
            if new_name and new_name != spec.name:
                # ensure unique
                q = select(Specialties).where(Specialties.name == new_name, Specialties.specialty_id != int(specialty_id))
                res = await db.execute(q)
                if res.scalars().first():
                    raise ValidationError("Another specialty with that name already exists")
                spec.name = new_name
        if "description" in payload:
            spec.description = payload.get("description")
        if "status" in payload:
            spec.status = payload.get("status")

        db.add(spec)
        await db.commit()
        await db.refresh(spec)
        return {"status": "updated", "specialty_id": int(spec.specialty_id)}
    except ValidationError:
        raise
    except UserNotFoundError:
        raise
    except IntegrityError as ie:
        await db.rollback()
        raise ValidationError("Failed to update specialty (integrity)", context={"detail": str(ie)})
    except Exception as e:
        await db.rollback()
        raise DatabaseError("Failed to update specialty", operation="update", table="specialties", original_error=e)


async def delete_speciality(db: AsyncSession, specialty_id: int) -> Dict[str, Any]:
    try:
        spec = await db.get(Specialties, int(specialty_id))
        if not spec:
            raise UserNotFoundError("Specialty not found", user_id=specialty_id)
        # safe delete
        await db.delete(spec)
        await db.commit()
        return {"status": "deleted", "specialty_id": int(specialty_id)}
    except UserNotFoundError:
        raise
    except Exception as e:
        await db.rollback()
        raise DatabaseError("Failed to delete specialty", operation="delete", table="specialties", original_error=e)


# ----------------------------
# Hospital doctors (assignment + listing + removal)
# ----------------------------
async def list_hospital_doctors(db: AsyncSession, hospital_id: int, limit: int = 500) -> List[Dict[str, Any]]:
    try:
        # join t_doctor_hospitals table to Users
        q = select(Users).join(t_doctor_hospitals, t_doctor_hospitals.c.user_id == Users.user_id).where(t_doctor_hospitals.c.hospital_id == int(hospital_id)).limit(limit)
        res = await db.execute(q)
        users = res.scalars().all()
        out = []
        for u in users:
            out.append({
                "user_id": int(u.user_id),
                "username": u.username,
                "email": u.email,
                "global_role_id": u.global_role_id
            })
        return out
    except Exception as e:
        raise DatabaseError("Failed to list hospital doctors", operation="select", table="doctor_hospitals", original_error=e)


async def add_doctor_to_hospital(db: AsyncSession, hospital_id: int, doctor_user_id: int, assign_hospital_role_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Assign an existing doctor user to a hospital (creates t_doctor_hospitals mapping, and hospital_user_roles mapping).
    assign_hospital_role_id: optional hospital_role_id to use for hospital_user_roles (if None, will not create hospital_user_roles row)
    """
    try:
        user = await db.get(Users, int(doctor_user_id))
        if not user:
            raise UserNotFoundError("Doctor user not found", user_id=doctor_user_id)

        # Insert into doctor_hospitals mapping (t_doctor_hospitals) safely if not exists
        q = select(t_doctor_hospitals).where(t_doctor_hospitals.c.user_id == int(doctor_user_id), t_doctor_hospitals.c.hospital_id == int(hospital_id))
        res = await db.execute(q)
        if not res.first():
            await db.execute(insert(t_doctor_hospitals).values({"user_id": int(doctor_user_id), "hospital_id": int(hospital_id)}))

        # Optionally create hospital_user_roles mapping with hospital_role (tenant role)
        if assign_hospital_role_id:
            # create mapping if not already present
            q2 = select(HospitalUserRoles).where(HospitalUserRoles.user_id == int(doctor_user_id), HospitalUserRoles.hospital_id == int(hospital_id), HospitalUserRoles.hospital_role_id == int(assign_hospital_role_id))
            res2 = await db.execute(q2)
            if not res2.scalars().first():
                hur = HospitalUserRoles(hospital_id=int(hospital_id), user_id=int(doctor_user_id), hospital_role_id=int(assign_hospital_role_id))
                db.add(hur)

        await db.commit()
        return {"status": "assigned", "hospital_id": int(hospital_id), "doctor_user_id": int(doctor_user_id)}
    except UserNotFoundError:
        raise
    except IntegrityError as ie:
        await db.rollback()
        raise ValidationError("Failed to assign doctor to hospital (integrity)", context={"detail": str(ie)})
    except Exception as e:
        await db.rollback()
        raise DatabaseError("Failed to add doctor to hospital", operation="insert", table="doctor_hospitals/hospital_user_roles", original_error=e)


async def update_hospital_doctor(db: AsyncSession, hospital_id: int, doctor_user_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update doctor-specific fields stored in Users or UserDetails (email, username, details).
    This will NOT change permissions or roles here.
    """
    try:
        user = await db.get(Users, int(doctor_user_id))
        if not user:
            raise UserNotFoundError("Doctor not found", user_id=doctor_user_id)
        # ensure mapping exists
        q = select(t_doctor_hospitals).where(t_doctor_hospitals.c.user_id == int(doctor_user_id), t_doctor_hospitals.c.hospital_id == int(hospital_id))
        res = await db.execute(q)
        if not res.first():
            raise AuthorizationError("Doctor is not assigned to this hospital")

        # update Users fields
        if "username" in payload and payload["username"]:
            user.username = str(payload["username"]).strip()
        if "email" in payload and payload["email"]:
            user.email = validate_email(payload["email"]) if "validate_email" in globals() else str(payload["email"]).strip()

        # update details
        details = await db.get(UserDetails, int(doctor_user_id))
        if not details:
            # create if missing
            details = UserDetails(user_id=int(doctor_user_id))
            db.add(details)
            await db.flush()

        if "first_name" in payload:
            details.first_name = payload.get("first_name")
        if "last_name" in payload:
            details.last_name = payload.get("last_name")
        if "phone" in payload:
            details.phone = validate_phone(payload.get("phone"), required=False) if "validate_phone" in globals() else payload.get("phone")
        if "address" in payload:
            details.address = payload.get("address")

        db.add(user)
        db.add(details)
        await db.commit()
        await db.refresh(user)
        return {"status": "updated", "doctor_user_id": int(doctor_user_id)}
    except ValidationError:
        raise
    except AuthorizationError:
        raise
    except UserNotFoundError:
        raise
    except IntegrityError as ie:
        await db.rollback()
        raise ValidationError("Failed to update doctor (integrity)", context={"detail": str(ie)})
    except Exception as e:
        await db.rollback()
        raise DatabaseError("Failed to update doctor", operation="update", table="users/user_details", original_error=e)


async def remove_doctor_from_hospital(db: AsyncSession, hospital_id: int, doctor_user_id: int) -> Dict[str, Any]:
    """
    Remove doctor mapping from hospital (both t_doctor_hospitals and hospital_user_roles entries)
    """
    try:
        # delete doctor_hospitals mapping
        await db.execute(delete(t_doctor_hospitals).where(t_doctor_hospitals.c.user_id == int(doctor_user_id), t_doctor_hospitals.c.hospital_id == int(hospital_id)))
        # delete hospital_user_roles mappings for that hospital & user
        await db.execute(delete(HospitalUserRoles).where(HospitalUserRoles.user_id == int(doctor_user_id), HospitalUserRoles.hospital_id == int(hospital_id)))
        await db.commit()
        return {"status": "removed", "hospital_id": int(hospital_id), "doctor_user_id": int(doctor_user_id)}
    except Exception as e:
        await db.rollback()
        raise DatabaseError("Failed to remove doctor from hospital", operation="delete", table="doctor_hospitals/hospital_user_roles", original_error=e)


# ----------------------------
# Hospital patients
# ----------------------------
async def list_hospital_patients(db: AsyncSession, hospital_id: int, limit: int = 500) -> List[Dict[str, Any]]:
    try:
        q = select(PatientHospitals, Users).join(Users, PatientHospitals.user_id == Users.user_id).where(PatientHospitals.hospital_id == int(hospital_id)).limit(limit)
        res = await db.execute(q)
        out = []
        for ph, u in res.all():
            out.append({
                "user_id": int(u.user_id),
                "username": u.username,
                "email": u.email,
                "registered_on": ph.registered_on.isoformat() if ph.registered_on else None
            })
        return out
    except Exception as e:
        raise DatabaseError("Failed to list hospital patients", operation="select", table="patient_hospitals", original_error=e)
