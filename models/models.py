from typing import Optional
import datetime
import decimal

from sqlalchemy import BigInteger, Column, Computed, DECIMAL, Date, DateTime, ForeignKeyConstraint, Index, Integer, JSON, String, Table, Text, text
from sqlalchemy.dialects.mysql import LONGTEXT, TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.database import Base


class HospitalMaster(Base):
    __tablename__ = 'hospital_master'
    __table_args__ = (
        Index('hospital_name', 'hospital_name', unique=True),
    )

    hospital_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hospital_name: Mapped[str] = mapped_column(String(255, 'utf8mb4_unicode_ci'), nullable=False)
    hospital_email: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_unicode_ci'))
    admin_contact: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_unicode_ci'))
    address: Mapped[Optional[str]] = mapped_column(String(1024, 'utf8mb4_unicode_ci'))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    user: Mapped[list['Users']] = relationship('Users', secondary='doctor_hospitals', back_populates='hospital')
    hospital_role: Mapped[list['HospitalRole']] = relationship('HospitalRole', back_populates='hospital')
    consultation: Mapped[list['Consultation']] = relationship('Consultation', back_populates='hospital')
    hospital_user_roles: Mapped[list['HospitalUserRoles']] = relationship('HospitalUserRoles', back_populates='hospital')
    patient_hospitals: Mapped[list['PatientHospitals']] = relationship('PatientHospitals', back_populates='hospital')
    api_usage_logs: Mapped[list['ApiUsageLogs']] = relationship('ApiUsageLogs', back_populates='hospital')


class PermissionMaster(Base):
    __tablename__ = 'permission_master'
    __table_args__ = (
        Index('permission_name', 'permission_name', unique=True),
    )

    permission_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    permission_name: Mapped[str] = mapped_column(String(150, 'utf8mb4_unicode_ci'), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500, 'utf8mb4_unicode_ci'))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    role_permission: Mapped[list['RolePermission']] = relationship('RolePermission', back_populates='permission')
    hospital_role_permission: Mapped[list['HospitalRolePermission']] = relationship('HospitalRolePermission', back_populates='permission')
    user_permissions: Mapped[list['UserPermissions']] = relationship('UserPermissions', back_populates='permission')
    user_direct_permissions: Mapped[list['UserDirectPermissions']] = relationship('UserDirectPermissions', back_populates='permission')

class RoleMaster(Base):
    __tablename__ = 'role_master'
    __table_args__ = (
        ForeignKeyConstraint(['parent_role_id'], ['role_master.role_id'], ondelete='SET NULL', name='role_master_ibfk_1'),
        Index('parent_role_id', 'parent_role_id'),
        Index('role_name', 'role_name', unique=True)
    )

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_name: Mapped[str] = mapped_column(String(100, 'utf8mb4_unicode_ci'), nullable=False)
    role_scope: Mapped[str] = mapped_column(String(50, 'utf8mb4_unicode_ci'), nullable=False, server_default=text("'platform'"))
    parent_role_id: Mapped[Optional[int]] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(String(500, 'utf8mb4_unicode_ci'))
    can_manage_roles: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    parent_role: Mapped[Optional['RoleMaster']] = relationship('RoleMaster', remote_side=[role_id], back_populates='parent_role_reverse')
    parent_role_reverse: Mapped[list['RoleMaster']] = relationship('RoleMaster', remote_side=[parent_role_id], back_populates='parent_role')
    role_permission: Mapped[list['RolePermission']] = relationship('RolePermission', back_populates='role')
    users: Mapped[list['Users']] = relationship('Users', back_populates='global_role')


class Specialties(Base):
    __tablename__ = 'specialties'
    __table_args__ = (
        Index('name', 'name', unique=True),
    )

    specialty_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200, 'utf8mb4_unicode_ci'), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text(collation='utf8mb4_unicode_ci'))
    status: Mapped[Optional[str]] = mapped_column(String(50, 'utf8mb4_unicode_ci'), server_default=text("'active'"))
    default_training_template: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    consultation: Mapped[list['Consultation']] = relationship('Consultation', back_populates='specialty')
    doctor_specialties: Mapped[list['DoctorSpecialties']] = relationship('DoctorSpecialties', back_populates='specialty')


class HospitalRole(Base):
    __tablename__ = 'hospital_role'
    __table_args__ = (
        ForeignKeyConstraint(['hospital_id'], ['hospital_master.hospital_id'], ondelete='CASCADE', name='hospital_role_ibfk_1'),
        ForeignKeyConstraint(['parent_hospital_role_id'], ['hospital_role.hospital_role_id'], ondelete='SET NULL', name='hospital_role_ibfk_2'),
        Index('idx_hr_hospital', 'hospital_id'),
        Index('parent_hospital_role_id', 'parent_hospital_role_id'),
        Index('uq_hospital_role', 'hospital_id', 'role_name', unique=True)
    )

    hospital_role_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hospital_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role_name: Mapped[str] = mapped_column(String(150, 'utf8mb4_unicode_ci'), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500, 'utf8mb4_unicode_ci'))
    parent_hospital_role_id: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    hospital: Mapped['HospitalMaster'] = relationship('HospitalMaster', back_populates='hospital_role')
    parent_hospital_role: Mapped[Optional['HospitalRole']] = relationship('HospitalRole', remote_side=[hospital_role_id], back_populates='parent_hospital_role_reverse')
    parent_hospital_role_reverse: Mapped[list['HospitalRole']] = relationship('HospitalRole', remote_side=[parent_hospital_role_id], back_populates='parent_hospital_role')
    hospital_role_permission: Mapped[list['HospitalRolePermission']] = relationship('HospitalRolePermission', back_populates='hospital_role')
    hospital_user_roles: Mapped[list['HospitalUserRoles']] = relationship('HospitalUserRoles', back_populates='hospital_role')


class RolePermission(Base):
    __tablename__ = 'role_permission'
    __table_args__ = (
        ForeignKeyConstraint(['permission_id'], ['permission_master.permission_id'], ondelete='CASCADE', name='role_permission_ibfk_2'),
        ForeignKeyConstraint(['role_id'], ['role_master.role_id'], ondelete='CASCADE', name='role_permission_ibfk_1'),
        Index('idx_rp_permission', 'permission_id')
    )

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    permission_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    permission: Mapped['PermissionMaster'] = relationship('PermissionMaster', back_populates='role_permission')
    role: Mapped['RoleMaster'] = relationship('RoleMaster', back_populates='role_permission')


class Users(Base):
    __tablename__ = 'users'
    __table_args__ = (
        ForeignKeyConstraint(['global_role_id'], ['role_master.role_id'], ondelete='SET NULL', name='users_ibfk_1'),
        Index('email', 'email', unique=True),
        Index('idx_users_globalrole', 'global_role_id'),
        Index('username', 'username', unique=True)
    )

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(150, 'utf8mb4_unicode_ci'), nullable=False)
    email: Mapped[str] = mapped_column(String(255, 'utf8mb4_unicode_ci'), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_unicode_ci'))
    global_role_id: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    hospital: Mapped[list['HospitalMaster']] = relationship('HospitalMaster', secondary='doctor_hospitals', back_populates='user')
    global_role: Mapped[Optional['RoleMaster']] = relationship('RoleMaster', back_populates='users')
    audit_logs: Mapped[list['AuditLogs']] = relationship('AuditLogs', back_populates='users')
    consultation: Mapped[list['Consultation']] = relationship('Consultation', foreign_keys='[Consultation.doctor_id]', back_populates='doctor')
    consultation_: Mapped[list['Consultation']] = relationship('Consultation', foreign_keys='[Consultation.patient_id]', back_populates='patient')
    doctor_avatars: Mapped[list['DoctorAvatars']] = relationship('DoctorAvatars', back_populates='doctor')
    doctor_specialties: Mapped[list['DoctorSpecialties']] = relationship('DoctorSpecialties', back_populates='user')
    file_uploads: Mapped[list['FileUploads']] = relationship('FileUploads', back_populates='users')
    hospital_user_roles: Mapped[list['HospitalUserRoles']] = relationship('HospitalUserRoles', back_populates='user')
    notifications: Mapped[list['Notifications']] = relationship('Notifications', back_populates='user')
    patient_hospitals: Mapped[list['PatientHospitals']] = relationship('PatientHospitals', back_populates='user')
    user_permissions: Mapped[list['UserPermissions']] = relationship('UserPermissions', back_populates='user')
    api_usage_logs: Mapped[list['ApiUsageLogs']] = relationship('ApiUsageLogs', foreign_keys='[ApiUsageLogs.doctor_id]', back_populates='doctor')
    api_usage_logs_: Mapped[list['ApiUsageLogs']] = relationship('ApiUsageLogs', foreign_keys='[ApiUsageLogs.patient_id]', back_populates='patient')


class AuditLogs(Base):
    __tablename__ = 'audit_logs'
    __table_args__ = (
        ForeignKeyConstraint(['user_actor'], ['users.user_id'], ondelete='SET NULL', name='audit_logs_ibfk_1'),
        Index('idx_entity', 'entity_type', 'entity_id'),
        Index('idx_event_time', 'event_time'),
        Index('idx_user_actor', 'user_actor')
    )

    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_unicode_ci'))
    entity_type: Mapped[Optional[str]] = mapped_column(String(50, 'utf8mb4_unicode_ci'))
    entity_id: Mapped[Optional[int]] = mapped_column(Integer)
    user_actor: Mapped[Optional[int]] = mapped_column(Integer)
    event_time: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    old_values: Mapped[Optional[dict]] = mapped_column(JSON)
    new_values: Mapped[Optional[dict]] = mapped_column(JSON)
    user_agent: Mapped[Optional[str]] = mapped_column(Text(collation='utf8mb4_unicode_ci'))

    users: Mapped[Optional['Users']] = relationship('Users', back_populates='audit_logs')


class Consultation(Base):
    __tablename__ = 'consultation'
    __table_args__ = (
        ForeignKeyConstraint(['doctor_id'], ['users.user_id'], ondelete='CASCADE', name='consultation_ibfk_2'),
        ForeignKeyConstraint(['hospital_id'], ['hospital_master.hospital_id'], ondelete='SET NULL', name='consultation_ibfk_3'),
        ForeignKeyConstraint(['patient_id'], ['users.user_id'], ondelete='CASCADE', name='consultation_ibfk_1'),
        ForeignKeyConstraint(['specialty_id'], ['specialties.specialty_id'], ondelete='CASCADE', name='consultation_ibfk_4'),
        Index('hospital_id', 'hospital_id'),
        Index('idx_consult_doctor_date', 'doctor_id', 'consultation_date'),
        Index('idx_consult_patient_date', 'patient_id', 'consultation_date'),
        Index('specialty_id', 'specialty_id')
    )

    consultation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(Integer, nullable=False)
    doctor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    specialty_id: Mapped[int] = mapped_column(Integer, nullable=False)
    hospital_id: Mapped[Optional[int]] = mapped_column(Integer)
    consultation_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    consultation_type: Mapped[Optional[str]] = mapped_column(String(50, 'utf8mb4_unicode_ci'), server_default=text("'hospital'"))
    status: Mapped[Optional[str]] = mapped_column(String(50, 'utf8mb4_unicode_ci'), server_default=text("'scheduled'"))
    total_duration: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    doctor: Mapped['Users'] = relationship('Users', foreign_keys=[doctor_id], back_populates='consultation')
    hospital: Mapped[Optional['HospitalMaster']] = relationship('HospitalMaster', back_populates='consultation')
    patient: Mapped['Users'] = relationship('Users', foreign_keys=[patient_id], back_populates='consultation_')
    specialty: Mapped['Specialties'] = relationship('Specialties', back_populates='consultation')
    consultation_sessions: Mapped[list['ConsultationSessions']] = relationship('ConsultationSessions', back_populates='consultation')
    consultation_transcripts: Mapped[list['ConsultationTranscripts']] = relationship('ConsultationTranscripts', back_populates='consultation')


class DoctorAvatars(Base):
    __tablename__ = 'doctor_avatars'
    __table_args__ = (
        ForeignKeyConstraint(['doctor_id'], ['users.user_id'], ondelete='CASCADE', name='doctor_avatars_ibfk_1'),
        Index('idx_da_doctor', 'doctor_id')
    )

    avatar_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    avatar_name: Mapped[Optional[str]] = mapped_column(String(255, 'utf8mb4_unicode_ci'))
    photo_url: Mapped[Optional[str]] = mapped_column(Text(collation='utf8mb4_unicode_ci'))
    voice_sample_url: Mapped[Optional[str]] = mapped_column(Text(collation='utf8mb4_unicode_ci'))
    avatar_video_url: Mapped[Optional[str]] = mapped_column(Text(collation='utf8mb4_unicode_ci'))
    config_data: Mapped[Optional[dict]] = mapped_column(JSON)
    status: Mapped[Optional[str]] = mapped_column(String(50, 'utf8mb4_unicode_ci'))
    training_progress: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    is_active: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    doctor: Mapped['Users'] = relationship('Users', back_populates='doctor_avatars')


t_doctor_hospitals = Table(
    'doctor_hospitals', Base.metadata,
    Column('user_id', Integer, primary_key=True),
    Column('hospital_id', Integer, primary_key=True),
    ForeignKeyConstraint(['hospital_id'], ['hospital_master.hospital_id'], ondelete='CASCADE', name='doctor_hospitals_ibfk_2'),
    ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE', name='doctor_hospitals_ibfk_1'),
    Index('idx_dh_hosp', 'hospital_id')
)
# class DoctorHospital(Base):
#     __tablename__ = "doctor_hospitals"
#     user_id = Column(Integer, ForeignKeyConstraint("users.user_id", ondelete="CASCADE"), primary_key=True)
#     hospital_id = Column(Integer, ForeignKeyConstraint("hospital_master.hospital_id", ondelete="CASCADE"), primary_key=True)
#     role = Column(String(50), nullable=True)          
#     joined_at = Column(DateTime, default=datetime.datetime)
#     user = relationship("User", back_populates="doctor_hospitals")
#     hospital = relationship("Hospital", back_populates="doctor_hospitals")



class DoctorSpecialties(Base):
    __tablename__ = 'doctor_specialties'
    __table_args__ = (
        ForeignKeyConstraint(['specialty_id'], ['specialties.specialty_id'], ondelete='CASCADE', name='doctor_specialties_ibfk_2'),
        ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE', name='doctor_specialties_ibfk_1'),
        Index('idx_ds_spec', 'specialty_id'),
        Index('uq_ds_user_spec', 'user_id', 'specialty_id', unique=True)
    )

    doctor_specialty_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    specialty_id: Mapped[int] = mapped_column(Integer, nullable=False)
    certified_date: Mapped[Optional[datetime.date]] = mapped_column(Date)

    specialty: Mapped['Specialties'] = relationship('Specialties', back_populates='doctor_specialties')
    user: Mapped['Users'] = relationship('Users', back_populates='doctor_specialties')


class FileUploads(Base):
    __tablename__ = 'file_uploads'
    __table_args__ = (
        ForeignKeyConstraint(['uploaded_by'], ['users.user_id'], ondelete='CASCADE', name='file_uploads_ibfk_1'),
        Index('idx_fu_user', 'uploaded_by')
    )

    file_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uploaded_by: Mapped[int] = mapped_column(Integer, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255, 'utf8mb4_unicode_ci'), nullable=False)
    file_url: Mapped[str] = mapped_column(Text(collation='utf8mb4_unicode_ci'), nullable=False)
    purpose: Mapped[str] = mapped_column(String(100, 'utf8mb4_unicode_ci'), nullable=False)
    file_type: Mapped[Optional[str]] = mapped_column(String(100, 'utf8mb4_unicode_ci'))
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger)
    processing_status: Mapped[Optional[str]] = mapped_column(String(50, 'utf8mb4_unicode_ci'), server_default=text("'uploaded'"))
    error_message: Mapped[Optional[str]] = mapped_column(Text(collation='utf8mb4_unicode_ci'))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    users: Mapped['Users'] = relationship('Users', back_populates='file_uploads')


class HospitalRolePermission(Base):
    __tablename__ = 'hospital_role_permission'
    __table_args__ = (
        ForeignKeyConstraint(['hospital_role_id'], ['hospital_role.hospital_role_id'], ondelete='CASCADE', name='hospital_role_permission_ibfk_1'),
        ForeignKeyConstraint(['permission_id'], ['permission_master.permission_id'], ondelete='CASCADE', name='hospital_role_permission_ibfk_2'),
        Index('idx_hrp_permission', 'permission_id')
    )

    hospital_role_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    permission_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    hospital_role: Mapped['HospitalRole'] = relationship('HospitalRole', back_populates='hospital_role_permission')
    permission: Mapped['PermissionMaster'] = relationship('PermissionMaster', back_populates='hospital_role_permission')


class HospitalUserRoles(Base):
    __tablename__ = 'hospital_user_roles'
    __table_args__ = (
        ForeignKeyConstraint(['hospital_id'], ['hospital_master.hospital_id'], ondelete='CASCADE', name='hospital_user_roles_ibfk_1'),
        ForeignKeyConstraint(['hospital_role_id'], ['hospital_role.hospital_role_id'], ondelete='CASCADE', name='hospital_user_roles_ibfk_3'),
        ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE', name='hospital_user_roles_ibfk_2'),
        Index('idx_hur_role', 'hospital_role_id'),
        Index('idx_hur_user', 'user_id')
    )

    hospital_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hospital_role_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assigned_on: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    is_active: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))

    hospital: Mapped['HospitalMaster'] = relationship('HospitalMaster', back_populates='hospital_user_roles')
    hospital_role: Mapped['HospitalRole'] = relationship('HospitalRole', back_populates='hospital_user_roles')
    user: Mapped['Users'] = relationship('Users', back_populates='hospital_user_roles')


class Notifications(Base):
    __tablename__ = 'notifications'
    __table_args__ = (
        ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE', name='notifications_ibfk_1'),
        Index('idx_user_notifications', 'user_id', 'is_read', 'created_at')
    )

    notification_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255, 'utf8mb4_unicode_ci'), nullable=False)
    message: Mapped[str] = mapped_column(Text(collation='utf8mb4_unicode_ci'), nullable=False)
    type: Mapped[Optional[str]] = mapped_column(String(50, 'utf8mb4_unicode_ci'), server_default=text("'info'"))
    category: Mapped[Optional[str]] = mapped_column(String(100, 'utf8mb4_unicode_ci'), server_default=text("'system'"))
    is_read: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    action_url: Mapped[Optional[str]] = mapped_column(Text(collation='utf8mb4_unicode_ci'))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    user: Mapped['Users'] = relationship('Users', back_populates='notifications')


class PatientHospitals(Base):
    __tablename__ = 'patient_hospitals'
    __table_args__ = (
        ForeignKeyConstraint(['hospital_id'], ['hospital_master.hospital_id'], ondelete='CASCADE', name='patient_hospitals_ibfk_2'),
        ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE', name='patient_hospitals_ibfk_1'),
        Index('idx_ph_hosp', 'hospital_id')
    )

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hospital_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    registered_on: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    is_active: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))

    hospital: Mapped['HospitalMaster'] = relationship('HospitalMaster', back_populates='patient_hospitals')
    user: Mapped['Users'] = relationship('Users', back_populates='patient_hospitals')


class UserDetails(Base):
    __tablename__ = 'user_details'
    __table_args__ = (
        ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE', name='user_details_ibfk_1'),
    )

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(120, 'utf8mb4_unicode_ci'))
    last_name: Mapped[Optional[str]] = mapped_column(String(120, 'utf8mb4_unicode_ci'))
    dob: Mapped[Optional[datetime.date]] = mapped_column(Date)
    gender: Mapped[Optional[str]] = mapped_column(String(32, 'utf8mb4_unicode_ci'))
    phone: Mapped[Optional[str]] = mapped_column(String(50, 'utf8mb4_unicode_ci'))
    address: Mapped[Optional[str]] = mapped_column(Text(collation='utf8mb4_unicode_ci'))


class UserPermissions(Base):
    __tablename__ = 'user_permissions'
    __table_args__ = (
        ForeignKeyConstraint(['permission_id'], ['permission_master.permission_id'], ondelete='CASCADE', name='user_permissions_ibfk_2'),
        ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE', name='user_permissions_ibfk_1'),
        Index('idx_up_hospital', 'hospital_id'),
        Index('idx_up_permission', 'permission_id'),
        Index('idx_up_user', 'user_id'),
        Index('uq_user_perm', 'user_id', 'permission_id', 'hospital_id_coalesced', 'scope', unique=True)
    )

    user_permission_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    permission_id: Mapped[int] = mapped_column(Integer, nullable=False)
    permission_name: Mapped[str] = mapped_column(String(150, 'utf8mb4_unicode_ci'), nullable=False)
    scope: Mapped[str] = mapped_column(String(50, 'utf8mb4_unicode_ci'), nullable=False)
    hospital_id: Mapped[Optional[int]] = mapped_column(Integer)
    hospital_id_coalesced: Mapped[Optional[int]] = mapped_column(Integer, Computed('(coalesce(`hospital_id`,0))', persisted=True))
    granted_on: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    permission: Mapped['PermissionMaster'] = relationship('PermissionMaster', back_populates='user_permissions')
    user: Mapped['Users'] = relationship('Users', back_populates='user_permissions')


class UserSettings(Base):
    __tablename__ = 'user_settings'
    __table_args__ = (
        ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE', name='user_settings_ibfk_1'),
    )

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notification_email: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))
    notification_sms: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))
    language_preference: Mapped[Optional[str]] = mapped_column(String(10, 'utf8mb4_unicode_ci'), server_default=text("'en'"))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column('settings_created_at', DateTime, server_default=text('CURRENT_TIMESTAMP'))


class ConsultationSessions(Base):
    __tablename__ = 'consultation_sessions'
    __table_args__ = (
        ForeignKeyConstraint(['consultation_id'], ['consultation.consultation_id'], ondelete='CASCADE', name='consultation_sessions_ibfk_1'),
        Index('idx_cs_consultation', 'consultation_id')
    )

    session_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    consultation_id: Mapped[int] = mapped_column(Integer, nullable=False)
    session_start: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    session_end: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    session_type: Mapped[Optional[str]] = mapped_column(String(50, 'utf8mb4_unicode_ci'), server_default=text("'text'"))
    total_tokens_used: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    total_api_calls: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    session_status: Mapped[Optional[str]] = mapped_column(String(50, 'utf8mb4_unicode_ci'), server_default=text("'active'"))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    consultation: Mapped['Consultation'] = relationship('Consultation', back_populates='consultation_sessions')
    api_usage_logs: Mapped[list['ApiUsageLogs']] = relationship('ApiUsageLogs', back_populates='session')
    consultation_messages: Mapped[list['ConsultationMessages']] = relationship('ConsultationMessages', back_populates='session')


class ConsultationTranscripts(Base):
    __tablename__ = 'consultation_transcripts'
    __table_args__ = (
        ForeignKeyConstraint(['consultation_id'], ['consultation.consultation_id'], ondelete='CASCADE', name='consultation_transcripts_ibfk_1'),
        Index('consultation_id', 'consultation_id')
    )

    transcript_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    consultation_id: Mapped[int] = mapped_column(Integer, nullable=False)
    transcript_text: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    file_url: Mapped[Optional[str]] = mapped_column(Text(collation='utf8mb4_unicode_ci'))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    consultation: Mapped['Consultation'] = relationship('Consultation', back_populates='consultation_transcripts')


class ApiUsageLogs(Base):
    __tablename__ = 'api_usage_logs'
    __table_args__ = (
        ForeignKeyConstraint(['doctor_id'], ['users.user_id'], ondelete='SET NULL', name='api_usage_logs_ibfk_2'),
        ForeignKeyConstraint(['hospital_id'], ['hospital_master.hospital_id'], ondelete='SET NULL', name='api_usage_logs_ibfk_1'),
        ForeignKeyConstraint(['patient_id'], ['users.user_id'], ondelete='SET NULL', name='api_usage_logs_ibfk_3'),
        ForeignKeyConstraint(['session_id'], ['consultation_sessions.session_id'], ondelete='SET NULL', name='api_usage_logs_ibfk_4'),
        Index('idx_doctor_usage', 'doctor_id', 'timestamp'),
        Index('idx_hospital_usage', 'hospital_id', 'timestamp'),
        Index('idx_timestamp', 'timestamp'),
        Index('patient_id', 'patient_id'),
        Index('session_id', 'session_id')
    )

    usage_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_type: Mapped[str] = mapped_column(String(100, 'utf8mb4_unicode_ci'), nullable=False)
    hospital_id: Mapped[Optional[int]] = mapped_column(Integer)
    doctor_id: Mapped[Optional[int]] = mapped_column(Integer)
    patient_id: Mapped[Optional[int]] = mapped_column(Integer)
    session_id: Mapped[Optional[int]] = mapped_column(Integer)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    api_calls: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'1'"))
    cost: Mapped[Optional[decimal.Decimal]] = mapped_column(DECIMAL(10, 4), server_default=text("'0.0000'"))
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    status: Mapped[Optional[str]] = mapped_column(String(50, 'utf8mb4_unicode_ci'), server_default=text("'success'"))
    timestamp: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    doctor: Mapped[Optional['Users']] = relationship('Users', foreign_keys=[doctor_id], back_populates='api_usage_logs')
    hospital: Mapped[Optional['HospitalMaster']] = relationship('HospitalMaster', back_populates='api_usage_logs')
    patient: Mapped[Optional['Users']] = relationship('Users', foreign_keys=[patient_id], back_populates='api_usage_logs_')
    session: Mapped[Optional['ConsultationSessions']] = relationship('ConsultationSessions', back_populates='api_usage_logs')


class ConsultationMessages(Base):
    __tablename__ = 'consultation_messages'
    __table_args__ = (
        ForeignKeyConstraint(['session_id'], ['consultation_sessions.session_id'], ondelete='CASCADE', name='consultation_messages_ibfk_1'),
        Index('idx_cm_session', 'session_id')
    )

    message_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sender_type: Mapped[str] = mapped_column(String(50, 'utf8mb4_unicode_ci'), nullable=False)
    message_text: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    audio_url: Mapped[Optional[str]] = mapped_column(Text(collation='utf8mb4_unicode_ci'))
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    timestamp: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    session: Mapped['ConsultationSessions'] = relationship('ConsultationSessions', back_populates='consultation_messages')

class UserDirectPermissions(Base):
    __tablename__ = 'user_direct_permissions'
    __table_args__ = (
        ForeignKeyConstraint(['permission_id'], ['permission_master.permission_id'], name='user_direct_permissions_ibfk_1'),
        Index('permission_id', 'permission_id'),
        Index('uq_udp', 'user_id', 'permission_id', 'hospital_id', 'scope', unique=True)
    )

    udp_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    permission_id: Mapped[int] = mapped_column(Integer, nullable=False)
    scope: Mapped[str] = mapped_column(String(50, 'utf8mb4_unicode_ci'), nullable=False)
    hospital_id: Mapped[Optional[int]] = mapped_column(Integer)
    granted_by: Mapped[Optional[int]] = mapped_column(Integer)
    granted_on: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    permission: Mapped['PermissionMaster'] = relationship('PermissionMaster', back_populates='user_direct_permissions') 




