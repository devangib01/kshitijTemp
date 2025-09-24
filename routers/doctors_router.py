
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_db
from dependencies.dependencies import require_permissions, get_current_user
from service.doctors_service import (
    create_doctor, get_doctor_profile, update_doctor_profile,
    list_doctor_patients, view_patient_for_doctor, list_doctor_consultations,
    get_all_specialties, get_doctors_list, get_doctor_specialties, update_doctor_specialties,
    get_patient_consultations_for_doctor
)
from centralisedErrorHandling.ErrorHandling import ValidationError, DatabaseError, UserNotFoundError, AuthorizationError
from schema.schema import RegisterDoctorIn, UpdateMeIn

router = APIRouter()


@router.post("/auth/register/doctor", status_code=status.HTTP_201_CREATED)
async def register_doctor_endpoint(
    payload: RegisterDoctorIn,
    caller: Dict[str, Any] = Depends(require_permissions(["auth.register.doctor"])),
    db: AsyncSession = Depends(get_db),
):
    try:
        new_user = await create_doctor(db=db, payload=payload, created_by_user_id=caller.get("user_id"))
        return {"user_id": int(new_user.user_id), "username": new_user.username, "email": new_user.email}
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to create doctor")


@router.get("/doctors/profile")
async def get_profile(
    caller: Dict[str, Any] = Depends(require_permissions(["doctor.profile.view"], allow_super_admin=False)),
    db: AsyncSession = Depends(get_db),
):
    # ensure caller is doctor
    global_role = caller.get("global_role") or {}
    role_name = (global_role.get("role_name") or "").strip().lower()
    if role_name != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors may access this endpoint")
    user_id = caller.get("user_id")
    try:
        profile = await get_doctor_profile(db=db, user_id=user_id)
        return profile
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Doctor not found")
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to fetch doctor profile")


@router.put("/doctors/profile")
async def put_profile(
    payload: UpdateMeIn,
    caller: Dict[str, Any] = Depends(require_permissions(["doctor.profile.update"], allow_super_admin=False)),
    db: AsyncSession = Depends(get_db),
):
    global_role = caller.get("global_role") or {}
    role_name = (global_role.get("role_name") or "").strip().lower()
    if role_name != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors may update their profile")
    user_id = caller.get("user_id")
    try:
        await update_doctor_profile(db=db, user_id=user_id, update_data=payload.model_dump(exclude_unset=True))
        profile = await get_doctor_profile(db=db, user_id=user_id)
        return profile
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Doctor not found")
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to update doctor profile")


@router.get("/doctors/patients")
async def get_patients(
    caller: Dict[str, Any] = Depends(require_permissions(["doctor.patients.list"], allow_super_admin=False)),
    db: AsyncSession = Depends(get_db),
):
    global_role = caller.get("global_role") or {}
    role_name = (global_role.get("role_name") or "").strip().lower()
    if role_name != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors may list their patients")
    user_id = caller.get("user_id")
    try:
        patients = await list_doctor_patients(db=db, doctor_user_id=user_id)
        return {"patients": patients}
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to list patients")


@router.get("/doctors/patients/{patient_user_id}")
async def get_patient(
    patient_user_id: int,
    caller: Dict[str, Any] = Depends(require_permissions(["doctor.patient.view"], allow_super_admin=False)),
    db: AsyncSession = Depends(get_db),
):
    global_role = caller.get("global_role") or {}
    role_name = (global_role.get("role_name") or "").strip().lower()
    if role_name != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors may view patient details")
    user_id = caller.get("user_id")
    try:
        patient = await view_patient_for_doctor(db=db, doctor_user_id=user_id, patient_user_id=patient_user_id)
        return patient
    except AuthorizationError:
        raise HTTPException(status_code=403, detail="Not authorized to view this patient")
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Patient not found")
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to fetch patient details")


@router.get("/doctors/consultations")
async def get_consultations(
    caller: Dict[str, Any] = Depends(require_permissions(["doctor.patient.consultations.list"], allow_super_admin=False)),
    db: AsyncSession = Depends(get_db),
):
    global_role = caller.get("global_role") or {}
    role_name = (global_role.get("role_name") or "").strip().lower()
    if role_name != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors may list consultations")
    user_id = caller.get("user_id")
    try:
        consultations = await list_doctor_consultations(db=db, doctor_user_id=user_id)
        return {"consultations": consultations}
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to list consultations")


@router.get("/specialties")
async def get_specialties(db: AsyncSession = Depends(get_db)):
    """Get all medical specialties - public endpoint."""
    try:
        specialties = await get_all_specialties(db=db)
        return {"specialties": specialties}
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to fetch specialties")


@router.get("/doctors")
async def get_doctors(
    specialty: Optional[int] = Query(None, gt=0),
    db: AsyncSession = Depends(get_db)
):
    """Get doctors with optional specialty filter - public endpoint."""
    try:
        doctors = await get_doctors_list(db=db, specialty_id=specialty)
        return {"doctors": doctors}
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to fetch doctors")


@router.get("/doctors/{doctor_id}")
async def get_doctor_details(
    doctor_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db)
):
    """Get specific doctor details - public endpoint."""
    try:
        profile = await get_doctor_profile(db=db, user_id=doctor_id)
        return profile
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Doctor not found")
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to fetch doctor details")


@router.get("/doctors/specialties")
async def get_my_specialties(
    caller: Dict[str, Any] = Depends(require_permissions(["doctor.specialties.view"], allow_super_admin=False)),
    db: AsyncSession = Depends(get_db)
):
    """Get doctor's specialties."""
    global_role = caller.get("global_role") or {}
    role_name = (global_role.get("role_name") or "").strip().lower()
    if role_name != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors may access this endpoint")
    
    user_id = caller.get("user_id")
    try:
        specialties = await get_doctor_specialties(db=db, user_id=user_id)
        return {"specialties": specialties}
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to fetch specialties")


@router.put("/doctors/specialties")
async def update_my_specialties(
    payload: Dict[str, List[int]],
    caller: Dict[str, Any] = Depends(require_permissions(["doctor.specialties.update"], allow_super_admin=False)),
    db: AsyncSession = Depends(get_db)
):
    """Update doctor's specialties."""
    global_role = caller.get("global_role") or {}
    role_name = (global_role.get("role_name") or "").strip().lower()
    if role_name != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors may update specialties")
    
    user_id = caller.get("user_id")
    specialty_ids = payload.get("specialty_ids", [])
    
    try:
        result = await update_doctor_specialties(db=db, user_id=user_id, specialty_ids=specialty_ids)
        return result
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to update specialties")


@router.get("/doctors/patients/{patient_id}/consultations")
async def get_patient_consultations(
    patient_id: int,
    caller: Dict[str, Any] = Depends(require_permissions(["doctor.patient.consultations.view"], allow_super_admin=False)),
    db: AsyncSession = Depends(get_db)
):
    """Get patient medical consultations for this doctor."""
    global_role = caller.get("global_role") or {}
    role_name = (global_role.get("role_name") or "").strip().lower()
    if role_name != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors may view patient consultations")
    
    doctor_id = caller.get("user_id")
    try:
        consultations = await get_patient_consultations_for_doctor(db=db, doctor_id=doctor_id, patient_id=patient_id)
        return {"consultations": consultations}
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to fetch patient consultations")


@router.get("/doctors/analytics/patients")
async def get_patient_analytics(
    caller: Dict[str, Any] = Depends(require_permissions(["doctor.analytics.view"], allow_super_admin=False)),
    db: AsyncSession = Depends(get_db)
):
    """Patient analytics for doctor."""
    global_role = caller.get("global_role") or {}
    role_name = (global_role.get("role_name") or "").strip().lower()
    if role_name != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors may view analytics")
    
    doctor_id = caller.get("user_id")
    try:
        patients = await list_doctor_patients(db=db, doctor_user_id=doctor_id)
        consultations = await list_doctor_consultations(db=db, doctor_user_id=doctor_id)
        
        return {
            "total_patients": len(patients),
            "total_consultations": len(consultations),
            "patients": patients[:10]  # Top 10 patients
        }
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to fetch analytics")


@router.get("/doctors/consultations/all")
async def get_monthly_consultations(
    caller: Dict[str, Any] = Depends(require_permissions(["doctor.consultations.monthly"], allow_super_admin=False)),
    db: AsyncSession = Depends(get_db)
):
    """All consultations for doctor."""
    global_role = caller.get("global_role") or {}
    role_name = (global_role.get("role_name") or "").strip().lower()
    if role_name != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors may view monthly consultations")
    
    doctor_id = caller.get("user_id")
    try:
        consultations = await list_doctor_consultations(db=db, doctor_user_id=doctor_id)
        return {"consultations": consultations}
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to fetch monthly consultations")
