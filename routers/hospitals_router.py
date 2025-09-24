# routers/hospitals_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_db
from dependencies.dependencies import require_permissions
from service.hospital_service import (
    _resolve_hospital_id_for_user,
    get_hospital_profile, update_hospital_profile,
    list_specialities, create_speciality, update_speciality, delete_speciality,
    list_hospital_doctors, add_doctor_to_hospital, update_hospital_doctor, remove_doctor_from_hospital,
    list_hospital_patients
)
from centralisedErrorHandling.ErrorHandling import ValidationError, DatabaseError, UserNotFoundError, AuthorizationError
from schema.schema import (
    HospitalProfileOut, HospitalProfileUpdate,
    SpecialityCreate, SpecialityUpdate, SpecialityOut,
    HospitalDoctorAdd, HospitalDoctorUpdate, HospitalDoctorOut,
    HospitalPatientOut, StatusOut
)

router = APIRouter(tags=["hospitals"])


# ---- Hospital profile ----
@router.get("/hospitals/profile", response_model=HospitalProfileOut)
async def api_get_hospital_profile(
    caller: Dict[str, Any] = Depends(require_permissions(["hospital.profile.view"])),
    db: AsyncSession = Depends(get_db)
):
    hid = await _resolve_hospital_id_for_user(db=db, caller=caller)
    if not hid:
        raise HTTPException(status_code=404, detail="No hospital associated with user")
    try:
        return await get_hospital_profile(db=db, hospital_id=hid)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Hospital not found")
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to fetch hospital profile")


@router.put("/hospitals/profile", response_model=StatusOut)
async def api_update_hospital_profile(
    payload: HospitalProfileUpdate,
    caller: Dict[str, Any] = Depends(require_permissions(["hospital.profile.update"])),
    db: AsyncSession = Depends(get_db)
):
    hid = await _resolve_hospital_id_for_user(db=db, caller=caller)
    if not hid:
        raise HTTPException(status_code=404, detail="No hospital associated with user")
    try:
        result = await update_hospital_profile(db=db, hospital_id=hid, payload=payload.dict(exclude_unset=True))
        return StatusOut(status=result.get("status", "updated"), hospital_id=result.get("hospital_id"))
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Hospital not found")
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to update hospital profile")


# ---- Specialities ----
@router.get("/hospitals/specialities", response_model=List[SpecialityOut])
async def api_list_specialities(
    db: AsyncSession = Depends(get_db),
    active_only: bool = Query(True)
):
    try:
        items = await list_specialities(db=db, active_only=active_only)
        return [SpecialityOut(**i) for i in items]
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to fetch specialities")


@router.post("/hospitals/specialities", response_model=SpecialityOut, status_code=status.HTTP_201_CREATED)
async def api_create_speciality(
    payload: SpecialityCreate,
    caller: Dict[str, Any] = Depends(require_permissions(["hospital.speciality.create"])),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await create_speciality(db=db, payload=payload.dict())
        return SpecialityOut(**result)
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to create speciality")


@router.put("/hospitals/specialities/{speciality_id}", response_model=StatusOut)
async def api_update_speciality(
    speciality_id: int = Path(..., gt=0),
    payload: SpecialityUpdate = None,
    caller: Dict[str, Any] = Depends(require_permissions(["hospital.speciality.update"])),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await update_speciality(db=db, specialty_id=speciality_id, payload=(payload.dict(exclude_unset=True) if payload else {}))
        return StatusOut(status=result.get("status", "updated"), specialty_id=result.get("specialty_id"))
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Speciality not found")
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to update speciality")


@router.delete("/hospitals/specialities/{speciality_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_speciality(
    speciality_id: int = Path(..., gt=0),
    caller: Dict[str, Any] = Depends(require_permissions(["hospital.speciality.delete"])),
    db: AsyncSession = Depends(get_db)
):
    try:
        await delete_speciality(db=db, specialty_id=speciality_id)
        return {"status": "deleted"}
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Speciality not found")
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to delete speciality")


# ---- Hospital doctors ----
@router.get("/hospitals/doctors", response_model=List[HospitalDoctorOut])
async def api_list_hospital_doctors(
    caller: Dict[str, Any] = Depends(require_permissions(["hospital.doctors.list"])),
    db: AsyncSession = Depends(get_db)
):
    hid = await _resolve_hospital_id_for_user(db=db, caller=caller)
    if not hid:
        raise HTTPException(status_code=404, detail="No hospital associated with user")
    try:
        rows = await list_hospital_doctors(db=db, hospital_id=hid)
        return [HospitalDoctorOut(**r) for r in rows]
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to list hospital doctors")


@router.post("/hospitals/doctors", response_model=StatusOut, status_code=status.HTTP_201_CREATED)
async def api_add_hospital_doctor(
    payload: HospitalDoctorAdd,
    caller: Dict[str, Any] = Depends(require_permissions(["hospital.doctor.create"])),
    db: AsyncSession = Depends(get_db)
):
    hid = await _resolve_hospital_id_for_user(db=db, caller=caller)
    if not hid:
        raise HTTPException(status_code=404, detail="No hospital associated with user")
    try:
        res = await add_doctor_to_hospital(db=db, hospital_id=hid, doctor_user_id=payload.doctor_user_id, assign_hospital_role_id=payload.hospital_role_id)
        return StatusOut(status=res.get("status", "assigned"), hospital_id=res.get("hospital_id"), doctor_user_id=res.get("doctor_user_id"))
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Doctor user not found")
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to add doctor")


@router.put("/hospitals/doctors/{doctor_id}", response_model=StatusOut)
async def api_update_hospital_doctor(
    doctor_id: int = Path(..., gt=0),
    payload: HospitalDoctorUpdate = None,
    caller: Dict[str, Any] = Depends(require_permissions(["hospital.doctor.update"])),
    db: AsyncSession = Depends(get_db)
):
    hid = await _resolve_hospital_id_for_user(db=db, caller=caller)
    if not hid:
        raise HTTPException(status_code=404, detail="No hospital associated with user")
    try:
        res = await update_hospital_doctor(db=db, hospital_id=hid, doctor_user_id=doctor_id, payload=(payload.dict(exclude_unset=True) if payload else {}))
        return StatusOut(status=res.get("status", "updated"), doctor_user_id=res.get("doctor_user_id"))
    except AuthorizationError:
        raise HTTPException(status_code=403, detail="Doctor not assigned to this hospital")
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="Doctor not found")
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to update doctor")


@router.delete("/hospitals/doctors/{doctor_id}", response_model=StatusOut)
async def api_delete_hospital_doctor(
    doctor_id: int = Path(..., gt=0),
    caller: Dict[str, Any] = Depends(require_permissions(["hospital.doctor.delete"])),
    db: AsyncSession = Depends(get_db)
):
    hid = await _resolve_hospital_id_for_user(db=db, caller=caller)
    if not hid:
        raise HTTPException(status_code=404, detail="No hospital associated with user")
    try:
        res = await remove_doctor_from_hospital(db=db, hospital_id=hid, doctor_user_id=doctor_id)
        return StatusOut(status=res.get("status", "removed"), hospital_id=res.get("hospital_id"), doctor_user_id=res.get("doctor_user_id"))
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to remove doctor")


# ---- Hospital patients ----
@router.get("/hospitals/patients", response_model=List[HospitalPatientOut])
async def api_list_hospital_patients(
    caller: Dict[str, Any] = Depends(require_permissions(["hospital.patients.list"])),
    db: AsyncSession = Depends(get_db)
):
    hid = await _resolve_hospital_id_for_user(db=db, caller=caller)
    if not hid:
        raise HTTPException(status_code=404, detail="No hospital associated with user")
    try:
        rows = await list_hospital_patients(db=db, hospital_id=hid)
        return [HospitalPatientOut(**r) for r in rows]
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to list patients")
