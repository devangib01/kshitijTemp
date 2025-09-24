from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, delete, insert
from models import Users, UserDetails, DoctorSpecialties, RoleMaster, Consultation, Specialties
from schema.schema import RegisterDoctorIn
from utils.utils import generate_passwd_hash
from utils.validators import validate_username, validate_email, validate_password, validate_phone
from centralisedErrorHandling.ErrorHandling import ValidationError, DatabaseError, UserNotFoundError
from datetime import datetime
from sqlalchemy.exc import IntegrityError


async def create_doctor(db: AsyncSession, payload: RegisterDoctorIn, created_by_user_id: Optional[int] = None) -> Users:
    try:
        username = validate_username(payload.username)
        email = validate_email(payload.email)
        password = validate_password(payload.password)
        phone = validate_phone(payload.phone, required=False)
    except ValidationError as ve:
        raise ve

    # Check duplicates
    q = select(Users).where((Users.email == email) | (Users.username == username))
    try:
        res = await db.execute(q)
        existing = res.scalars().first()
    except Exception as e:
        raise DatabaseError("Failed to query existing users", operation="select", table="users", original_error=e)

    if existing:
        raise ValidationError("A user with that email or username already exists")

    # Get doctor role
    try:
        role_q = select(RoleMaster).where(RoleMaster.role_name == "doctor")
        role_res = await db.execute(role_q)
        doctor_role = role_res.scalar_one_or_none()
    except Exception as e:
        raise DatabaseError("Failed to find doctor role", operation="select", table="role_master", original_error=e)

    # Create user
    user = Users(
        username=username,
        email=email,
        password_hash=generate_passwd_hash(password),
        global_role_id=doctor_role.role_id if doctor_role else None,
    )
    
    try:
        db.add(user)
        await db.flush()
        await db.refresh(user)

        # Create user details
        details = UserDetails(
            user_id=int(user.user_id),
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone=phone,
        )
        db.add(details)

        # Add specialties if provided
        if payload.specialties:
            for specialty_id in payload.specialties:
                if specialty_id > 0:
                    ds = DoctorSpecialties(user_id=int(user.user_id), specialty_id=specialty_id)
                    db.add(ds)

        await db.commit()
        await db.refresh(user)
        return user
    except Exception as e:
        await db.rollback()
        raise DatabaseError("Failed to create doctor", operation="insert", table="users", original_error=e)


async def get_doctor_profile(db: AsyncSession, user_id: int) -> Optional[UserDetails]:
    """Return the UserDetails row for given user_id."""
    try:
        details = await db.get(UserDetails, int(user_id))
        return details
    except Exception as e:
        raise DatabaseError("Failed to fetch doctor details", operation="select", table="user_details", original_error=e)


async def update_doctor_profile(db: AsyncSession, user_id: int, update_data: Dict[str, Any]) -> UserDetails:
    """Update allowed profile fields on user_details."""
    try:
        details = await db.get(UserDetails, int(user_id))
    except Exception as e:
        raise DatabaseError("Failed to fetch profile", operation="select", table="user_details", original_error=e)

    if not details:
        raise UserNotFoundError("Profile not found", user_id=user_id)

    allowed = {"first_name", "last_name", "phone", "dob", "gender", "address"}
    changed = False
    for k, v in update_data.items():
        if k in allowed:
            setattr(details, k, v)
            changed = True

    if not changed:
        return details

    try:
        db.add(details)
        await db.commit()
        await db.refresh(details)
        return details
    except Exception as e:
        await db.rollback()
        raise DatabaseError("Failed to update profile", operation="update", table="user_details", original_error=e)


async def list_doctor_consultations(db: AsyncSession, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch consultations where this user is the doctor."""
    try:
        q = (
            select(Consultation)
            .where(Consultation.doctor_id == int(user_id))
            .order_by(desc(Consultation.consultation_date))
            .limit(int(limit))
        )
        res = await db.execute(q)
        consultations = res.scalars().all()
    except Exception as e:
        raise DatabaseError("Failed to list consultations", operation="select", table="consultation", original_error=e)

    out = []
    for c in consultations:
        out.append({
            "consultation_id": int(c.consultation_id),
            "patient_id": int(c.patient_id) if c.patient_id is not None else None,
            "hospital_id": int(c.hospital_id) if c.hospital_id is not None else None,
            "specialty_id": int(c.specialty_id) if c.specialty_id is not None else None,
            "consultation_date": c.consultation_date.isoformat() if c.consultation_date else None,
            "status": c.status,
            "total_duration": int(c.total_duration or 0),
        })
    return out


async def get_all_specialties(db: AsyncSession) -> List[Dict[str, Any]]:
    """Get all medical specialties."""
    try:
        q = select(Specialties).where(Specialties.status == "active")
        res = await db.execute(q)
        specialties = res.scalars().all()
        return [{"specialty_id": s.specialty_id, "name": s.name, "description": s.description} for s in specialties]
    except Exception as e:
        raise DatabaseError("Failed to fetch specialties", operation="select", table="specialties", original_error=e)


async def get_doctors_list(db: AsyncSession, specialty_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Get doctors with optional specialty filter."""
    try:
        if specialty_id:
            q = (
                select(Users, UserDetails)
                .join(UserDetails, Users.user_id == UserDetails.user_id, isouter=True)
                .join(DoctorSpecialties, Users.user_id == DoctorSpecialties.user_id)
                .join(RoleMaster, Users.global_role_id == RoleMaster.role_id)
                .where(RoleMaster.role_name == "doctor", DoctorSpecialties.specialty_id == specialty_id)
                .limit(limit)
            )
        else:
            q = (
                select(Users, UserDetails)
                .join(UserDetails, Users.user_id == UserDetails.user_id, isouter=True)
                .join(RoleMaster, Users.global_role_id == RoleMaster.role_id)
                .where(RoleMaster.role_name == "doctor")
                .limit(limit)
            )
        
        res = await db.execute(q)
        doctors = []
        for user, details in res.all():
            doctors.append({
                "user_id": Users.user_id,
                "username": Users.username,
                "first_name": UserDetails.first_name if details else None,
                "last_name": UserDetails.last_name if details else None
            })
        return doctors
    except Exception as e:
        raise DatabaseError("Failed to fetch doctors", operation="select", table="users", original_error=e)


async def get_doctor_specialties(db: AsyncSession, user_id: int) -> List[Dict[str, Any]]:
    """Get doctor's specialties."""
    try:
        q = (
            select(Specialties)
            .join(DoctorSpecialties, Specialties.specialty_id == DoctorSpecialties.specialty_id)
            .where(DoctorSpecialties.user_id == user_id)
        )
        res = await db.execute(q)
        specialties = res.scalars().all()
        return [{"specialty_id": s.specialty_id, "name": s.name, "description": s.description} for s in specialties]
    except Exception as e:
        raise DatabaseError("Failed to fetch doctor specialties", operation="select", table="doctor_specialties", original_error=e)


async def update_doctor_specialties(db: AsyncSession, user_id: int, specialty_ids: List[int]) -> Dict[str, Any]:
    """Update doctor's specialties."""
    try:
        # Delete existing specialties
        del_q = delete(DoctorSpecialties).where(DoctorSpecialties.user_id == user_id)
        await db.execute(del_q)
        
        # Add new specialties
        for specialty_id in specialty_ids:
            if specialty_id > 0:
                ds = DoctorSpecialties(user_id=user_id, specialty_id=specialty_id)
                db.add(ds)
        
        await db.commit()
        return {"status": "updated", "specialty_count": len(specialty_ids)}
    except Exception as e:
        await db.rollback()
        raise DatabaseError("Failed to update specialties", operation="update", table="doctor_specialties", original_error=e)


async def list_doctor_patients(db: AsyncSession, doctor_user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """Get patients for this doctor using single JOIN query."""
    try:
        q = (
            select(Users.user_id, Users.username, Users.email)
            .join(Consultation, Users.user_id == Consultation.patient_id)
            .where(Consultation.doctor_id == int(doctor_user_id))
            .group_by(Users.user_id, Users.username, Users.email)
            .limit(int(limit))
        )
        res = await db.execute(q)
        return [{"user_id": int(Users.user_id), "username": Users.username, "email": Users.email}]
    except Exception as e:
        raise DatabaseError("Failed to list doctor patients", operation="select", table="consultation", original_error=e)


async def view_patient_for_doctor(db: AsyncSession, doctor_user_id: int, patient_user_id: int) -> Dict[str, Any]:
    """Get patient details if doctor has treated them."""
    try:
        q = (
            select(Consultation)
            .where(Consultation.doctor_id == int(doctor_user_id), Consultation.patient_id == int(patient_user_id))
            .limit(1)
        )
        res = await db.execute(q)
        consult = res.scalars().first()
        if not consult:
            raise ValidationError("Doctor is not authorized to view this patient")
    except ValidationError:
        raise
    except Exception as e:
        raise DatabaseError("Failed to verify doctor-patient relationship", operation="select", table="consultation", original_error=e)

    try:
        patient = await db.get(Users, int(patient_user_id))
        if not patient:
            raise UserNotFoundError("Patient not found", user_id=patient_user_id)
        details = await db.get(UserDetails, int(patient_user_id))
    except Exception as e:
        raise DatabaseError("Failed to fetch patient details", operation="select", table="users/user_details", original_error=e)

    return {
        "user_id": int(patient.user_id),
        "username": patient.username,
        "email": patient.email,
        "details": {
            "first_name": getattr(details, "first_name", None),
            "last_name": getattr(details, "last_name", None),
            "phone": getattr(details, "phone", None),
            "address": getattr(details, "address", None),
        }
    }


async def get_patient_consultations_for_doctor(db: AsyncSession, doctor_id: int, patient_id: int) -> List[Dict[str, Any]]:
    """Get patient consultations for a specific doctor."""
    try:
        q = (
            select(Consultation)
            .where(Consultation.doctor_id == doctor_id, Consultation.patient_id == patient_id)
            .order_by(desc(Consultation.consultation_date))
        )
        res = await db.execute(q)
        consultations = res.scalars().all()
        
        return [{
            "consultation_id": c.consultation_id,
            "consultation_date": c.consultation_date.isoformat() if c.consultation_date else None,
            "status": c.status,
            "total_duration": c.total_duration or 0
        } for c in consultations]
    except Exception as e:
        raise DatabaseError("Failed to fetch patient consultations", operation="select", table="consultation", original_error=e)