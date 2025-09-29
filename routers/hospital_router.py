# routers/hospitals_router.py
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_db
from dependencies.dependencies import require_global_roles
from schema.schema import OnboardHospitalAdminIn, OnboardHospitalAdminOut
from service.hospital_service import create_hospital_with_admin
from centralisedErrorHandling.ErrorHandling import ValidationError, DatabaseError
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["hospitals"])

@router.post(
    "/hospitals/onboard",
    response_model=OnboardHospitalAdminOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_global_roles(role_names=["superadmin"]))]
)
async def onboard_hospital(payload: OnboardHospitalAdminIn, db: AsyncSession = Depends(get_db)):
    """
    Superadmin can create a hospital AND its hospital_admin user (email + password) in one atomic operation.
    The created hospital_admin receives tenant-scoped hospital_admin role for that hospital.
    """
    try:
        res = await create_hospital_with_admin(
            db=db,
            hospital_name=payload.hospital_name,
            hospital_email=payload.hospital_email,
            admin_email=payload.admin_email,
            admin_password=payload.admin_password,
            admin_username=payload.admin_username,
            admin_first_name=payload.admin_first_name,
            admin_last_name=payload.admin_last_name,
            admin_phone=payload.admin_phone,
            auto_login=payload.auto_login if payload.auto_login is not None else True
        )
        return OnboardHospitalAdminOut(**res)
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except DatabaseError as de:
        logger.exception("Database error during hospital onboarding")
        raise HTTPException(status_code=500, detail=str(de))
    except Exception as e:
        logger.exception("Unexpected error during hospital onboarding")
        raise HTTPException(status_code=500, detail="Failed to onboard hospital")
