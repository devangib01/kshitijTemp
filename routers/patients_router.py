from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_db
from dependencies.dependencies import require_permissions, get_current_user
from schema.schema import (
    RegisterPatientIn, RegisterPatientOut,
    UserDetailsRead, UserDetailsUpdate
)
from service.patients_service import (
    create_patient, get_patient_profile, update_patient_profile, list_patient_consultations
)
from centralisedErrorHandling.ErrorHandling import ValidationError, DatabaseError, UserNotFoundError, AuthorizationError

router = APIRouter()


@router.post("/auth/register/patient", response_model=RegisterPatientOut, status_code=status.HTTP_201_CREATED)
async def register_patient(
    payload: RegisterPatientIn,
    db: AsyncSession = Depends(get_db),
):
    try:
        new_user = await create_patient(db=db, payload=payload, created_by_user_id=None)
        return RegisterPatientOut(
            user_id=int(new_user.user_id),
            username=new_user.username,
            email=new_user.email,
            next="/login"
        )
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except DatabaseError as de:
        raise HTTPException(status_code=500, detail=f"Database error: {str(de)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create patient: {str(e)}")


@router.get("/patients/profile", response_model=UserDetailsRead)
async def get_profile(
    caller: Dict[str, Any] = Depends(require_permissions(["patient.profile.view"], allow_super_admin=False)),
    db: AsyncSession = Depends(get_db),
):
    # enforce patient role
    global_role = caller.get("global_role") or {}
    role_name = (global_role.get("role_name") or "").strip().lower()
    if role_name != "patient":
        raise HTTPException(status_code=403, detail="Only patients may access their profile")

    user_id = caller.get("user_id")
    try:
        details = await get_patient_profile(db=db, user_id=user_id)
        if not details:
            raise HTTPException(status_code=404, detail="Profile not found")
        return details
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to fetch profile")


@router.put("/patients/profile", response_model=UserDetailsRead)
async def put_profile(
    payload: UserDetailsUpdate,
    caller: Dict[str, Any] = Depends(require_permissions(["patient.profile.update"], allow_super_admin=False)),
    db: AsyncSession = Depends(get_db),
):
    global_role = caller.get("global_role") or {}
    role_name = (global_role.get("role_name") or "").strip().lower()
    if role_name != "patient":
        raise HTTPException(status_code=403, detail="Only patients may update their profile")

    user_id = caller.get("user_id")
    try:
        updated = await update_patient_profile(db=db, user_id=user_id, update_data=payload.model_dump(exclude_none=True))
        return updated
    except UserNotFoundError as unfe:
        raise HTTPException(status_code=404, detail=str(unfe))
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to update profile")

@router.get("/patients/consultations")
async def get_consultations(
    caller: Dict[str, Any] = Depends(require_permissions(["patient.consultation.list"], allow_super_admin=False)),
    db: AsyncSession = Depends(get_db),
):
    global_role = caller.get("global_role") or {}
    role_name = (global_role.get("role_name") or "").strip().lower()
    if role_name != "patient":
        raise HTTPException(status_code=403, detail="Only patients may list their consultations")

    user_id = caller.get("user_id")
    try:
        consultations = await list_patient_consultations(db=db, user_id=user_id, limit=200)
        return {"consultations": consultations}
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to fetch consultations")