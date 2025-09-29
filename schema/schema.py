
from typing import Optional, Any, Dict, List
from datetime import datetime, date
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator, constr
from pydantic.types import Json
from enum import Enum
import re 

USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,50}$")
INDIA_PHONE_RE = re.compile(r"^(?:\+91|91)?[6-9]\d{9}$")

#----------------Enum----------------#
class service_type_enum(str, Enum):
    stt = "stt"
    tts = "tts"
    llm = "llm"
    avatar_generation = "avatar_generation"
    avatar_training = "avatar_training"

class entity_type_enum(str, Enum):
    user = "user"
    hospital = "hospital"
    consultation = "consultation"
    subscription = "subscription"
    avatar = "avatar"
    role = "role"
    permission = "permission"

class consultation_type_enum(str, Enum):
    hospital = "hospital"
    independent = "independent"

class consultation_status_enum(str, Enum):
    scheduled = "scheduled"
    ongoing = "ongoing"
    completed = "completed"
    cancelled = "cancelled"

class session_type_enum(str, Enum):
    text = "text"
    voice = "voice"
    video = "video"

class session_status_enum(str, Enum):
    active = "active"
    completed = "completed"
    interrupted = "interrupted"

class processing_status_enum(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class purpose_enum(str, Enum):
    avatar_photo = "avatar_photo"
    voice_sample = "voice_sample"
    training_pdf = "training_pdf"
    training_csv = "training_csv"
    other = "other"

class type_enum(str, Enum):
    info = "info"
    success = "success"
    warning = "warning"
    error = "error"

class category_enum(str, Enum):
    avatar_training = "avatar_training"
    consultation = "consultation"
    system = "system"
    billing = "billing"

class specialty_status_enum(str, Enum):
    active = "active"
    inactive = "inactive"
    in_training = "in_training"

# ---------------- Base ----------------
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
class HospitalCreateIn(BaseModel):
    hospital_name: str = Field(..., min_length=3)
    hospital_email: Optional[EmailStr] = None
    admin_contact: Optional[str] = None
    address: Optional[str] = None


class HospitalOut(BaseModel):
    hospital_id: int
    hospital_name: str
    hospital_email: Optional[EmailStr] = None


class HospitalRoleCreateIn(BaseModel):
    role_name: str = Field(..., min_length=2)
    description: Optional[str] = None
    hierarchy_level: Optional[int] = 0


class HospitalRoleOut(BaseModel):
    hospital_role_id: int
    hospital_id: int
    role_name: str
    description: Optional[str]


class AttachPermissionIn(BaseModel):
    permission_id: int


class AssignRoleIn(BaseModel):
    hospital_role_id: int

class RegisterSuperadminIn(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    auto_login: Optional[bool] = True

class RegisterSuperadminOut(BaseModel):
    user_id: int
    username: str
    email: EmailStr
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
# ---------------- Models & CRUD (concrete) ----------------
# RULES: Full CRUD => Create/Update/Delete
# Partial CRUD => Create & Update only
# Read-only (logs, analytics, cache, transcripts) => NO CRUD generated
class UserMeOut(BaseModel):
    user: Dict[str, Any]
    details: Dict[str, Any]
    permissions: list[Dict[str, Any]]

class RegisterPatientIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    hospital_id: Optional[int] = None


class RegisterPatientOut(BaseModel):
    user_id: int
    username: str
    email: EmailStr
    next: Optional[str] = None


class RegisterDoctorIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    specialties: Optional[list[int]] = None
    invite_hospital_id: Optional[int] = None
    invited_hospital_role_id: Optional[int] = None

class HospitalProfileOut(BaseModel):
    hospital_id: int
    hospital_name: str
    hospital_email: Optional[EmailStr] = None
    admin_contact: Optional[str] = None
    address: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class HospitalProfileUpdate(BaseModel):
    hospital_name: Optional[str] = None
    hospital_email: Optional[EmailStr] = None
    admin_contact: Optional[str] = None
    address: Optional[str] = None

# -------------------------
# Speciality schemas
# -------------------------
class SpecialityBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: Optional[specialty_status_enum] = Field(default="active")

class SpecialityCreate(SpecialityBase):
    pass

class SpecialityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[specialty_status_enum] = None

class SpecialityOut(SpecialityBase):
    specialty_id: int
class OnboardHospitalAdminIn(BaseModel):
    hospital_name: str
    hospital_email: Optional[EmailStr] = None
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8)
    admin_username: Optional[str] = None
    admin_first_name: Optional[str] = None
    admin_last_name: Optional[str] = None
    admin_phone: Optional[str] = None
    auto_login: Optional[bool] = True

class OnboardHospitalAdminOut(BaseModel):
    hospital_id: int
    hospital_name: str
    admin_user_id: int
    admin_username: str
    admin_email: EmailStr
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
# -------------------------
# Hospital doctor schemas
# -------------------------
class HospitalDoctorAdd(BaseModel):
    doctor_user_id: int
    hospital_role_id: Optional[int] = None

class HospitalDoctorUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class HospitalDoctorOut(BaseModel):
    user_id: int
    username: str
    email: str
    global_role_id: Optional[int] = None

# -------------------------
# Patient output schema
# -------------------------
class HospitalPatientOut(BaseModel):
    user_id: int
    username: Optional[str] = None
    email: Optional[str] = None
    registered_on: Optional[str] = None

# -------------------------
# Generic responses
# -------------------------
class StatusOut(BaseModel):
    status: str
    hospital_id: Optional[int] = None
    doctor_user_id: Optional[int] = None
    specialty_id: Optional[int] = None
    specialty_count: Optional[int] = None
class RegisterDoctorOut(BaseModel):
    user_id: int
    status: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UpdateMeIn(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    # changes to email/username require separate verification flows
    email: Optional[EmailStr]
# ---------- DashboardMetrics (Full CRUD) ----------
class DashboardMetricsBase(BaseSchema):
    metric_id: Optional[int] = Field(None)
    metric_date: Optional[date] = Field(None, description="Date for the metrics")
    total_hospitals: Optional[int] = Field(0)
    total_doctors: Optional[int] = Field(0)
    total_patients: Optional[int] = Field(0)
    active_avatars: Optional[int] = Field(0)
    total_consultations_today: Optional[int] = Field(0)
    total_consultations_month: Optional[int] = Field(0)
    total_api_calls_today: Optional[int] = Field(0)
    total_tokens_used_today: Optional[int] = Field(0)
    total_revenue_today: Optional[float] = Field(0.0)
    total_revenue_month: Optional[float] = Field(0.0)
    calculated_at: Optional[datetime] = Field(None)

class DashboardMetricsCreate(DashboardMetricsBase):
    # exclude metric_id (autogenerated)
    metric_date: Optional[date] = Field(None)

class DashboardMetricsUpdate(BaseSchema):
    metric_date: Optional[date] = None
    total_hospitals: Optional[int] = None
    total_doctors: Optional[int] = None
    total_patients: Optional[int] = None
    active_avatars: Optional[int] = None
    total_consultations_today: Optional[int] = None
    total_consultations_month: Optional[int] = None
    total_api_calls_today: Optional[int] = None
    total_tokens_used_today: Optional[int] = None
    total_revenue_today: Optional[float] = None
    total_revenue_month: Optional[float] = None
    calculated_at: Optional[datetime] = None

class DashboardMetricsDelete(BaseSchema):
    metric_id: int

class RoleBase(BaseModel):
    role_name: str
    is_global: Optional[int] = Field(default=0)

class RoleRead(RoleBase):
    role_id: int
    hierarchy_level: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
class AssignGlobalRole(BaseModel):
    user_id: int
    role_id: int


class AssignHospitalRole(BaseModel):
    user_id: int
    role_id: int
    hospital_id: int


class AssignIndependentRole(BaseModel):
    user_id: int
    role_id: int
class UserRoleResponse(BaseModel):
    user_id: int
    role_id: int
    role_name: str
    scope: str  # "global" | "hospital" | "independent"
    hospital_id: Optional[int] = None
# ---------- HospitalMaster (Full CRUD) ----------
class HospitalMasterBase(BaseSchema):
    hospital_id: Optional[int] = Field(None)
    hospital_name: Optional[str] = Field(None)
    hospital_email: Optional[EmailStr] = Field(None)
    admin_contact: Optional[str] = Field(None)
    address: Optional[str] = Field(None)
    created_by: Optional[int] = Field(None)
    updated_by: Optional[int] = Field(None)
    created_at: Optional[datetime] = Field(None)
    updated_at: Optional[datetime] = Field(None)

class HospitalMasterCreate(HospitalMasterBase):
    # exclude hospital_id
    hospital_name: str = Field(..., description="Name of the hospital")
    hospital_email: Optional[EmailStr] = Field(None)

class HospitalMasterUpdate(BaseSchema):
    hospital_name: Optional[str] = None
    hospital_email: Optional[EmailStr] = None
    admin_contact: Optional[str] = None
    address: Optional[str] = None
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class HospitalMasterDelete(BaseSchema):
    hospital_id: int

# ---------- PermissionMaster (Full CRUD) ----------
class PermissionMasterBase(BaseSchema):
    permission_id: Optional[int] = Field(None)
    permission_name: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    created_by: Optional[int] = Field(None)
    updated_by: Optional[int] = Field(None)
    created_at: Optional[datetime] = Field(None)
    updated_at: Optional[datetime] = Field(None)

class PermissionMasterCreate(PermissionMasterBase):
    permission_name: str = Field(..., description="Name of the permission")
    description: Optional[str] = Field(None)

class PermissionMasterUpdate(BaseSchema):
    permission_name: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[int] = None
    updated_by: Optional[int] = None

class PermissionMasterDelete(BaseSchema):
    permission_id: int

# ---------- PlanFeatures (Full CRUD) ----------
class PlanFeaturesBase(BaseSchema):
    feature_id: Optional[int] = Field(None)
    plan_id: Optional[int] = Field(None)
    feature_name: Optional[str] = Field(None)
    description: Optional[str] = Field(None)

class PlanFeaturesCreate(PlanFeaturesBase):
    plan_id: int = Field(..., description="Plan id")
    feature_name: str = Field(..., description="Feature name")

class PlanFeaturesUpdate(BaseSchema):
    plan_id: Optional[int] = None
    feature_name: Optional[str] = None
    description: Optional[str] = None

class PlanFeaturesDelete(BaseSchema):
    feature_id: int

# ---------- PlanMaster (Full CRUD) ----------
class PlanMasterBase(BaseSchema):
    plan_id: Optional[int] = Field(None)
    plan_name: Optional[str] = Field(None)
    price_monthly: Optional[float] = Field(0.0)
    max_specialties: Optional[int] = Field(0)
    created_by: Optional[int] = Field(None)
    updated_by: Optional[int] = Field(None)
    created_at: Optional[datetime] = Field(None)
    updated_at: Optional[datetime] = Field(None)

class PlanMasterCreate(PlanMasterBase):
    plan_name: str = Field(...)

class PlanMasterUpdate(BaseSchema):
    plan_name: Optional[str] = None
    price_monthly: Optional[float] = None
    max_specialties: Optional[int] = None
    created_by: Optional[int] = None
    updated_by: Optional[int] = None

class PlanMasterDelete(BaseSchema):
    plan_id: int


class RoleMasterBase(BaseSchema):
    role_id: Optional[int] = Field(None)
    role_name: Optional[str] = Field(None)
    is_global: Optional[int] = Field(0)
    hierarchy_level: Optional[int] = Field(0)
    can_manage_roles: Optional[Json] = Field(None)
    created_at: Optional[datetime] = Field(None)
    updated_at: Optional[datetime] = Field(None)

class RoleMasterCreate(RoleMasterBase):
    role_name: str = Field(...)

class RoleMasterUpdate(BaseSchema):
    role_name: Optional[str] = None
    is_global: Optional[int] = None
    hierarchy_level: Optional[int] = None
    can_manage_roles: Optional[Json] = None

class RoleMasterDelete(BaseSchema):
    role_id: int


class RolePermissionsBase(BaseSchema):
    id: Optional[int] = Field(None)
    role_id: Optional[int] = Field(None)
    permission_id: Optional[int] = Field(None)

class RolePermissionsCreate(RolePermissionsBase):
    role_id: int = Field(...)
    permission_id: int = Field(...)

class RolePermissionsUpdate(BaseSchema):
    role_id: Optional[int] = None
    permission_id: Optional[int] = None

class RolePermissionsDelete(BaseSchema):
    id: int


class SpecialtiesBase(BaseSchema):
    specialty_id: Optional[int] = Field(None)
    name: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    icon_url: Optional[str] = Field(None)
    status: Optional[specialty_status_enum] = Field(None)
    default_training_template: Optional[Json] = Field(None)
    created_by: Optional[int] = Field(None)
    updated_by: Optional[int] = Field(None)
    created_at: Optional[datetime] = Field(None)
    updated_at: Optional[datetime] = Field(None)

class SpecialtiesCreate(SpecialtiesBase):
    name: str = Field(..., description="Name of specialty")
    status: specialty_status_enum = Field(...)

class SpecialtiesUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    status: Optional[specialty_status_enum] = None

class SpecialtiesDelete(BaseSchema):
    specialty_id: int

class SpecialtyFAQsBase(BaseSchema):
    faq_id: Optional[int] = Field(None)
    doctor_id: Optional[int] = Field(None)
    specialty_id: Optional[int] = Field(None)
    question: Optional[str] = Field(None)
    answer: Optional[str] = Field(None)
    is_active: Optional[int] = Field(1)
    created_at: Optional[datetime] = Field(None)
    updated_at: Optional[datetime] = Field(None)

class SpecialtyFAQsCreate(SpecialtyFAQsBase):
    specialty_id: int = Field(...)
    question: str = Field(...)

class SpecialtyFAQsUpdate(BaseSchema):
    doctor_id: Optional[int] = None
    specialty_id: Optional[int] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    is_active: Optional[int] = None

class SpecialtyFAQsDelete(BaseSchema):
    faq_id: int

class SpecialtyTrainingResourcesBase(BaseSchema):
    resource_id: Optional[int] = Field(None)
    doctor_id: Optional[int] = Field(None)
    specialty_id: Optional[int] = Field(None)
    resource_type: Optional[str] = Field(None)
    file_url: Optional[str] = Field(None)
    content_text: Optional[str] = Field(None)
    processing_status: Optional[str] = Field(None)
    error_message: Optional[str] = Field(None)
    created_at: Optional[datetime] = Field(None)
    updated_at: Optional[datetime] = Field(None)

class SpecialtyTrainingResourcesCreate(SpecialtyTrainingResourcesBase):
    specialty_id: int = Field(...)
    resource_type: str = Field(...)

class SpecialtyTrainingResourcesUpdate(BaseSchema):
    doctor_id: Optional[int] = None
    specialty_id: Optional[int] = None
    resource_type: Optional[str] = None
    file_url: Optional[str] = None

class SpecialtyTrainingResourcesDelete(BaseSchema):
    resource_id: int

class UsersBase(BaseSchema):
    username: Optional[str] = Field(default=None)
    email: Optional[EmailStr] = Field(default=None)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if v is None:
            return v
        if not USERNAME_RE.match(v):
            raise ValueError("Username must be 3-50 characters long and can include letters, numbers, dots, underscores, and hyphens.")
        return v.lower()


class UsersCreate(UsersBase):
    password: str = Field(..., min_length=8, description="Plain password; will be hashed server-side")
    global_role_id: Optional[int] = Field(None)

class UserRead(UsersBase):
    user_id: int
    global_role_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserLoginModel(BaseModel):
    email: str = Field(max_length=90)
    password: str = Field(min_length=8, max_length=30)

def normalised_indian_mobile_number(raw: str) -> str:
    """Normalize Indian mobile number to +91 format.
    
    Args:
        raw: Raw phone number string
        
    Returns:
        Normalized phone number with +91 prefix
    """
    # Remove all non-digit characters
    digits = re.sub(r"\D", "", raw or "")
    # Remove leading zero if present
    if digits.startswith("0"):
        digits = digits[1:]
    # Add +91 prefix for 10-digit numbers
    if len(digits) == 10:
        return "+91" + digits
    # Format 12-digit numbers starting with 91
    if len(digits) == 12 and digits.startswith("91"):
        return "+" + digits
    return raw


class UserDetailsBase(BaseSchema):
    user_id: Optional[int] = Field(None)
    first_name: Optional[str] = Field(None)
    last_name: Optional[str] = Field(None)
    dob: Optional[date] = Field(None)
    gender: Optional[str] = Field(None)
    address: Optional[str] = Field(None)
    phone: Optional[str] = Field(None)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError("phone must be a string")
        if not INDIA_PHONE_RE.match(v):
            raise ValueError(
                "Invalid Indian phone number. Accepts 10 digits starting 6-9, or prefixed with 91 or +91."
            )
        return normalised_indian_mobile_number(v)


class UserDetailsCreate(UserDetailsBase):
    user_id: int


class UserDetailsUpdate(UserDetailsBase):
    pass


class UserDetailsRead(UserDetailsBase):
    user_id: int
    
    model_config = ConfigDict(from_attributes=True)




class UserPermissionCacheBase(BaseSchema):
    key: Optional[str] = Field(None)
    permissions: Optional[Json] = Field(None)
    expires_at: Optional[datetime] = Field(None)


class UserSettingsBase(BaseSchema):
    setting_id: Optional[int] = Field(None)
    user_id: Optional[int] = Field(None)
    key: Optional[str] = Field(None)
    value: Optional[Json] = Field(None)

class UserSettingsCreate(UserSettingsBase):
    user_id: int = Field(...)
    key: str = Field(...)

class UserSettingsUpdate(BaseSchema):
    user_id: Optional[int] = None
    key: Optional[str] = None
    value: Optional[Json] = None

class UserSettingsDelete(BaseSchema):
    setting_id: int


class ConsultationBase(BaseSchema):
    consultation_id: Optional[int] = Field(None)
    patient_id: Optional[int] = Field(None)
    doctor_id: Optional[int] = Field(None)
    specialty_id: Optional[int] = Field(None)
    hospital_id: Optional[int] = Field(None)
    consultation_date: Optional[datetime] = Field(None)
    consultation_type: Optional[consultation_type_enum] = Field(None)
    status: Optional[consultation_status_enum] = Field(None)
    total_duration: Optional[int] = Field(0)

class ConsultationCreate(ConsultationBase):
    patient_id: int = Field(..., description="Identifier for the patient")
    doctor_id: int = Field(..., description="Identifier for the doctor")
    specialty_id: int = Field(..., description="Identifier for the specialty")
    consultation_type: consultation_type_enum = Field(..., description="Type of consultation")

class ConsultationUpdate(BaseSchema):
    consultation_date: Optional[datetime] = None
    status: Optional[consultation_status_enum] = None
    total_duration: Optional[int] = None


class ConsultationFeedbackBase(BaseSchema):
    feedback_id: Optional[int] = Field(None)
    consultation_id: Optional[int] = Field(None)
    patient_id: Optional[int] = Field(None)
    doctor_id: Optional[int] = Field(None)
    rating: Optional[int] = Field(None, ge=1, le=5)
    feedback_text: Optional[str] = Field(None)
    avatar_performance_rating: Optional[int] = Field(None, ge=1, le=5)
    would_recommend: Optional[bool] = Field(None)
    created_at: Optional[datetime] = Field(None)

class ConsultationFeedbackCreate(ConsultationFeedbackBase):
    consultation_id: int = Field(...)
    patient_id: int = Field(...)
    doctor_id: int = Field(...)
    rating: int = Field(..., ge=1, le=5)
    avatar_performance_rating: int = Field(..., ge=1, le=5)

class ConsultationFeedbackUpdate(BaseSchema):
    rating: Optional[int] = None
    feedback_text: Optional[str] = None
    avatar_performance_rating: Optional[int] = None
    would_recommend: Optional[bool] = None


class ConsultationSessionBase(BaseSchema):
    session_id: Optional[int] = Field(None)
    consultation_id: Optional[int] = Field(None)
    session_start: Optional[datetime] = Field(None)
    session_end: Optional[datetime] = Field(None)
    total_tokens_used: Optional[int] = Field(0)
    total_api_calls: Optional[int] = Field(0)
    session_type: Optional[session_type_enum] = Field(None)
    session_status: Optional[session_status_enum] = Field(None)

class ConsultationSessionCreate(ConsultationSessionBase):
    consultation_id: int = Field(...)

class ConsultationSessionUpdate(BaseSchema):
    session_end: Optional[datetime] = None
    total_tokens_used: Optional[int] = None
    total_api_calls: Optional[int] = None
    session_status: Optional[session_status_enum] = None


class ConsultationTranscriptBase(BaseSchema):
    transcript_id: Optional[int] = Field(None)
    consultation_id: Optional[int] = Field(None)
    transcript_text: Optional[str] = Field(None)
    file_url: Optional[str] = Field(None)
    created_at: Optional[datetime] = Field(None)

class DoctorAvatarsBase(BaseSchema):
    avatar_id: Optional[int] = Field(None)
    doctor_id: Optional[int] = Field(None)
    avatar_name: Optional[str] = Field(None)
    photo_url: Optional[str] = Field(None)
    voice_sample_url: Optional[str] = Field(None)
    avatar_video_url: Optional[str] = Field(None)
    config_data: Optional[Json] = Field(None)
    status: Optional[str] = Field(None)
    training_progress: Optional[int] = Field(0)
    is_active: Optional[int] = Field(1)
    created_at: Optional[datetime] = Field(None)
    updated_at: Optional[datetime] = Field(None)

class DoctorAvatarsCreate(DoctorAvatarsBase):
    doctor_id: int = Field(...)

class DoctorAvatarsUpdate(BaseSchema):
    doctor_id: Optional[int] = None
    avatar_name: Optional[str] = None
    photo_url: Optional[str] = None
    is_active: Optional[int] = None

class DoctorAvatarsDelete(BaseSchema):
    avatar_id: int


class DoctorHospitalsBase(BaseSchema):
    user_id: Optional[int] = Field(None)
    hospital_id: Optional[int] = Field(None)
    joined_on: Optional[datetime] = Field(None)
    is_active: Optional[int] = Field(1)

class DoctorHospitalsCreate(DoctorHospitalsBase):
    user_id: int = Field(...)
    hospital_id: int = Field(...)

class DoctorHospitalsUpdate(BaseSchema):
    joined_on: Optional[datetime] = None
    is_active: Optional[int] = None

class DoctorHospitalsDelete(BaseSchema):
    user_id: int
    hospital_id: int


class DoctorSpecialtiesBase(BaseSchema):
    doctor_specialty_id: Optional[int] = Field(None)
    user_id: Optional[int] = Field(None)
    specialty_id: Optional[int] = Field(None)
    certified_date: Optional[date] = Field(None)

class DoctorSpecialtiesCreate(DoctorSpecialtiesBase):
    user_id: int = Field(...)
    specialty_id: int = Field(...)

class DoctorSpecialtiesUpdate(BaseSchema):
    user_id: Optional[int] = None
    specialty_id: Optional[int] = None
    certified_date: Optional[date] = None

class DoctorSpecialtiesDelete(BaseSchema):
    doctor_specialty_id: int


class FileUploadsBase(BaseSchema):
    file_id: Optional[int] = Field(None)
    uploaded_by: Optional[int] = Field(None)
    file_name: Optional[str] = Field(None)
    file_path: Optional[str] = Field(None)
    purpose: Optional[purpose_enum] = Field(None)
    file_type: Optional[str] = Field(None)
    file_size: Optional[int] = Field(0)
    processing_status: Optional[processing_status_enum] = Field(None)
    error_message: Optional[str] = Field(None)
    created_at: Optional[datetime] = Field(None)
    updated_at: Optional[datetime] = Field(None)

class FileUploadsCreate(FileUploadsBase):
    uploaded_by: int = Field(...)
    file_name: str = Field(...)
    file_path: str = Field(...)
    purpose: purpose_enum = Field(...)

class FileUploadsUpdate(BaseSchema):
    file_id: Optional[int] = None
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    processing_status: Optional[processing_status_enum] = None
    error_message: Optional[str] = None

class HospitalAnalyticsBase(BaseSchema):
    analytics_id: Optional[int] = Field(None)
    hospital_id: Optional[int] = Field(None)
    analytics_date: Optional[date] = Field(None)
    total_doctors: Optional[int] = Field(0)
    active_avatars: Optional[int] = Field(0)
    total_patients: Optional[int] = Field(0)
    total_consultations: Optional[int] = Field(0)
    avg_consultation_rating: Optional[float] = Field(0.0)
    total_api_usage_cost: Optional[float] = Field(0.0)
    calculated_at: Optional[datetime] = Field(None)

class HospitalSettingsBase(BaseSchema):
    hospital_id: Optional[int] = Field(None)
    show_doctor_list: Optional[int] = Field(1)
    show_subscription_details: Optional[int] = Field(1)

class HospitalSettingsCreate(HospitalSettingsBase):
    hospital_id: int = Field(...)

class HospitalSettingsUpdate(BaseSchema):
    show_doctor_list: Optional[int] = None
    show_subscription_details: Optional[int] = None

class HospitalSettingsDelete(BaseSchema):
    hospital_id: int


class HospitalSubscriptionBase(BaseSchema):
    hospital_subscription_id: Optional[int] = Field(None)
    hospital_id: Optional[int] = Field(None)
    plan_id: Optional[int] = Field(None)
    subscription_start_date: Optional[datetime] = Field(None)
    subscription_end_date: Optional[datetime] = Field(None)
    is_active: Optional[int] = Field(1)
    created_by: Optional[int] = Field(None)
    updated_by: Optional[int] = Field(None)
    created_at: Optional[datetime] = Field(None)
    updated_at: Optional[datetime] = Field(None)

class HospitalSubscriptionCreate(HospitalSubscriptionBase):
    hospital_id: int = Field(...)
    plan_id: int = Field(...)

class HospitalSubscriptionUpdate(BaseSchema):
    plan_id: Optional[int] = None
    subscription_end_date: Optional[datetime] = None
    is_active: Optional[int] = None

class HospitalSubscriptionDelete(BaseSchema):
    hospital_subscription_id: int


class HospitalUserRolesBase(BaseSchema):
    hospital_id: Optional[int] = Field(None)
    user_id: Optional[int] = Field(None)
    role_id: Optional[int] = Field(None)
    assigned_on: Optional[datetime] = Field(None)
    is_active: Optional[int] = Field(1)

class HospitalUserRolesCreate(HospitalUserRolesBase):
    hospital_id: int = Field(...)
    user_id: int = Field(...)
    role_id: int = Field(...)

class HospitalUserRolesUpdate(BaseSchema):
    assigned_on: Optional[datetime] = None
    is_active: Optional[int] = None

class HospitalUserRolesDelete(BaseSchema):
    hospital_id: int
    user_id: int
    role_id: int


class IndependentUserRolesBase(BaseSchema):
    user_id: Optional[int] = Field(None)
    role_id: Optional[int] = Field(None)
    assigned_on: Optional[datetime] = Field(None)
    is_active: Optional[int] = Field(1)

class IndependentUserRolesCreate(IndependentUserRolesBase):
    user_id: int = Field(...)
    role_id: int = Field(...)

class IndependentUserRolesUpdate(BaseSchema):
    assigned_on: Optional[datetime] = None
    is_active: Optional[int] = None

class IndependentUserRolesDelete(BaseSchema):
    user_id: int
    role_id: int


class NotificationsBase(BaseSchema):
    notification_id: Optional[int] = Field(None)
    user_id: Optional[int] = Field(None)
    title: Optional[str] = Field(None)
    message: Optional[str] = Field(None)
    is_read: Optional[bool] = Field(False)
    action_url: Optional[str] = Field(None)
    created_at: Optional[datetime] = Field(None)
    type: Optional[type_enum] = Field(None)
    category: Optional[category_enum] = Field(None)

class NotificationsCreate(NotificationsBase):
    user_id: int = Field(...)
    title: Optional[str] = Field(None)
    message: Optional[str] = Field(None)
    type: type_enum = Field(...)

class NotificationsUpdate(BaseSchema):
    notification_id: Optional[int] = None
    is_read: Optional[bool] = None
    title: Optional[str] = None
    message: Optional[str] = None

class PatientHospitalsBase(BaseSchema):
    user_id: Optional[int] = Field(None)
    hospital_id: Optional[int] = Field(None)
    registered_on: Optional[date] = Field(None)
    is_active: Optional[int] = Field(1)

class PatientHospitalsCreate(PatientHospitalsBase):
    user_id: int = Field(...)
    hospital_id: int = Field(...)

class PatientHospitalsUpdate(BaseSchema):
    registered_on: Optional[date] = None
    is_active: Optional[int] = None

class PatientHospitalsDelete(BaseSchema):
    user_id: int
    hospital_id: int

class SpecialtyFaqsBase(BaseSchema):
    faq_id: Optional[int] = Field(None)
    doctor_id: Optional[int] = Field(None)
    specialty_id: Optional[int] = Field(None)
    question: Optional[str] = Field(None)
    answer: Optional[str] = Field(None)
    is_active: Optional[int] = Field(1)
    created_at: Optional[datetime] = Field(None)
    updated_at: Optional[datetime] = Field(None)

class SpecialtyFaqsCreate(SpecialtyFaqsBase):
    specialty_id: int = Field(...)
    question: str = Field(...)

class SpecialtyFaqsUpdate(BaseSchema):
    doctor_id: Optional[int] = None
    question: Optional[str] = None
    answer: Optional[str] = None

class SpecialtyFaqsDelete(BaseSchema):
    faq_id: int

# ---------- SpecialtyTrainingResources (Full CRUD) ----------
# (Already defined above as SpecialtyTrainingResources*, kept for completeness)
# ---------- ConsultationFeedback/Transcript/Session/ApiUsageLogs/ConsultationMessages ----------
# ConsultationFeedback, ConsultationSession, FileUploads, Notifications, ConsultationMessages = PARTIAL handled above

# ---------- ApiUsageLogs (READ-ONLY) ----------
class ApiUsageLogsBase(BaseSchema):
    usage_id: Optional[int] = Field(None)
    hospital_id: Optional[int] = Field(None)
    doctor_id: Optional[int] = Field(None)
    patient_id: Optional[int] = Field(None)
    session_id: Optional[int] = Field(None)
    service_type: Optional[service_type_enum] = Field(None)
    tokens_used: Optional[int] = Field(0)
    api_calls: Optional[int] = Field(0)
    response_time_ms: Optional[int] = Field(0)
    status: Optional[str] = Field(None)
    cost: Optional[float] = Field(0.0)
    timestamp: Optional[datetime] = Field(None)
# No CRUD per rules

# ---------- AuditLogs (READ-ONLY) ----------
class AuditLogsBase(BaseSchema):
    audit_id: Optional[int] = Field(None)
    event_type: Optional[str] = Field(None)
    entity_type: Optional[entity_type_enum] = Field(None)
    entity_id: Optional[int] = Field(None)
    user_actor: Optional[int] = Field(None)
    event_time: Optional[datetime] = Field(None)
    old_values: Optional[Json] = Field(None)
    new_values: Optional[Json] = Field(None)
    user_agent: Optional[str] = Field(None)
# No CRUD per rules

# ---------- ConsultationMessages (PARTIAL) ----------
class ConsultationMessagesBase(BaseSchema):
    message_id: Optional[int] = Field(None)
    consultation_id: Optional[int] = Field(None)
    sender_id: Optional[int] = Field(None)
    content: Optional[str] = Field(None)
    created_at: Optional[datetime] = Field(None)

class ConsultationMessagesCreate(ConsultationMessagesBase):
    consultation_id: int = Field(...)
    sender_id: int = Field(...)
    content: str = Field(...)

class ConsultationMessagesUpdate(BaseSchema):
    message_id: Optional[int] = None
    content: Optional[str] = None


class BaseRegisterIn(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: str = None
    last_name: str = None
    phone: int = None
    

class RegisterPatientIn(BaseRegisterIn):
    hospital_id: Optional[int] = Field(default=None, ge=0)

class RegisterDoctorIn(BaseRegisterIn):
    specialty_ids: Optional[List[int]] = Field(default=None)
    hospital_ids: Optional[List[int]] = Field(default=None)

class RegisterOut(BaseModel):
    user_id: int
    username: str
    email: EmailStr




class CreateUserRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class GoogleUser(BaseModel):
    sub: int
    email: str
    name: str
    picture: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str