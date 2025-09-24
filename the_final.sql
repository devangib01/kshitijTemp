
CREATE DATABASE avatar_doctor_managementprofile_V4
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
USE avatar_doctor_managementprofile_V4;

-- =========================================================
-- Core RBAC & tenant tables
-- =========================================================

-- Global/system-wide roles
CREATE TABLE role_master (
    role_id INT PRIMARY KEY AUTO_INCREMENT,
    role_name VARCHAR(100) NOT NULL UNIQUE,
    role_scope VARCHAR(50) NOT NULL DEFAULT 'platform', -- 'platform' or 'tenant'
    parent_role_id INT NULL, -- supports hierarchy / inheritance
    description VARCHAR(500),
    can_manage_roles JSON NULL, -- optional advanced config
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_role_id) REFERENCES role_master(role_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- Global permission definitions
CREATE TABLE permission_master (
    permission_id INT PRIMARY KEY AUTO_INCREMENT,
    permission_name VARCHAR(150) NOT NULL UNIQUE,
    description VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Role ↔ permission mapping
CREATE TABLE role_permission (
    role_id INT NOT NULL,
    permission_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES role_master(role_id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permission_master(permission_id) ON DELETE CASCADE,
    INDEX idx_rp_permission (permission_id)
) ENGINE=InnoDB;

-- Tenants (Hospitals)
CREATE TABLE hospital_master (
    hospital_id INT PRIMARY KEY AUTO_INCREMENT,
    hospital_name VARCHAR(255) NOT NULL UNIQUE,
    hospital_email VARCHAR(255),
    admin_contact VARCHAR(255),
    address VARCHAR(1024),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Hospital-specific roles (tenant scoped)
CREATE TABLE hospital_role (
    hospital_role_id INT PRIMARY KEY AUTO_INCREMENT,
    hospital_id INT NOT NULL,
    role_name VARCHAR(150) NOT NULL,
    description VARCHAR(500),
    parent_hospital_role_id INT NULL, -- for tenant role hierarchy
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (hospital_id) REFERENCES hospital_master(hospital_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_hospital_role_id) REFERENCES hospital_role(hospital_role_id) ON DELETE SET NULL,
    UNIQUE KEY uq_hospital_role (hospital_id, role_name),
    INDEX idx_hr_hospital (hospital_id)
) ENGINE=InnoDB;

-- Hospital role ↔ permission mapping
CREATE TABLE hospital_role_permission (
    hospital_role_id INT NOT NULL,
    permission_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (hospital_role_id, permission_id),
    FOREIGN KEY (hospital_role_id) REFERENCES hospital_role(hospital_role_id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permission_master(permission_id) ON DELETE CASCADE,
    INDEX idx_hrp_permission (permission_id)
) ENGINE=InnoDB;

-- =========================================================
-- Users & profile
-- =========================================================

CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(150) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NULL,
    global_role_id INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (global_role_id) REFERENCES role_master(role_id) ON DELETE SET NULL,
    INDEX idx_users_globalrole (global_role_id)
) ENGINE=InnoDB;

CREATE TABLE user_details (
    user_id INT PRIMARY KEY,
    first_name VARCHAR(120),
    last_name VARCHAR(120),
    dob DATE,
    gender VARCHAR(32),
    phone VARCHAR(50),
    address TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Tenant user assignments
CREATE TABLE hospital_user_roles (
    hospital_id INT NOT NULL,
    user_id INT NOT NULL,
    hospital_role_id INT NOT NULL,
    assigned_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (hospital_id, user_id, hospital_role_id),
    FOREIGN KEY (hospital_id) REFERENCES hospital_master(hospital_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (hospital_role_id) REFERENCES hospital_role(hospital_role_id) ON DELETE CASCADE,
    INDEX idx_hur_user (user_id),
    INDEX idx_hur_role (hospital_role_id)
) ENGINE=InnoDB;

-- Optional patient registration
CREATE TABLE patient_hospitals (
    user_id INT NOT NULL,
    hospital_id INT NOT NULL,
    registered_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (user_id, hospital_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (hospital_id) REFERENCES hospital_master(hospital_id) ON DELETE CASCADE,
    INDEX idx_ph_hosp (hospital_id)
) ENGINE=InnoDB;

-- =========================================================
-- Specialties / doctor mapping
-- =========================================================

CREATE TABLE specialties (
    specialty_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active', -- replaces ENUM
    default_training_template JSON DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE doctor_specialties (
    doctor_specialty_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    specialty_id INT NOT NULL,
    certified_date DATE,
    UNIQUE KEY uq_ds_user_spec (user_id, specialty_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (specialty_id) REFERENCES specialties(specialty_id) ON DELETE CASCADE,
    INDEX idx_ds_spec (specialty_id)
) ENGINE=InnoDB;

CREATE TABLE doctor_hospitals (
    user_id INT NOT NULL,
    hospital_id INT NOT NULL,
    PRIMARY KEY (user_id, hospital_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (hospital_id) REFERENCES hospital_master(hospital_id) ON DELETE CASCADE,
    INDEX idx_dh_hosp (hospital_id)
) ENGINE=InnoDB;

-- Doctor avatars and training metadata
CREATE TABLE doctor_avatars (
    avatar_id INT PRIMARY KEY AUTO_INCREMENT,
    doctor_id INT NOT NULL,
    avatar_name VARCHAR(255),
    photo_url TEXT,
    voice_sample_url TEXT,
    avatar_video_url TEXT,
    config_data JSON,
    status VARCHAR(50), 
    training_progress INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (doctor_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_da_doctor (doctor_id)
) ENGINE=InnoDB;

-- File storage
CREATE TABLE file_uploads (
    file_id INT PRIMARY KEY AUTO_INCREMENT,
    uploaded_by INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_url TEXT NOT NULL,
    file_type VARCHAR(100),
    file_size BIGINT,
    processing_status VARCHAR(50) DEFAULT 'uploaded', -- replaces ENUM
    purpose VARCHAR(100) NOT NULL, -- replaces ENUM
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (uploaded_by) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_fu_user (uploaded_by)
) ENGINE=InnoDB;

-- =========================================================
-- Consultations & interactions
-- =========================================================

CREATE TABLE consultation (
    consultation_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    hospital_id INT NULL,
    specialty_id INT NOT NULL,
    consultation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    consultation_type VARCHAR(50) DEFAULT 'hospital', -- replaces ENUM
    status VARCHAR(50) DEFAULT 'scheduled', -- replaces ENUM
    total_duration INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (hospital_id) REFERENCES hospital_master(hospital_id) ON DELETE SET NULL,
    FOREIGN KEY (specialty_id) REFERENCES specialties(specialty_id) ON DELETE CASCADE,
    INDEX idx_consult_doctor_date (doctor_id, consultation_date),
    INDEX idx_consult_patient_date (patient_id, consultation_date)
) ENGINE=InnoDB;

CREATE TABLE consultation_sessions (
    session_id INT PRIMARY KEY AUTO_INCREMENT,
    consultation_id INT NOT NULL,
    session_start DATETIME DEFAULT CURRENT_TIMESTAMP,
    session_end DATETIME NULL,
    session_type VARCHAR(50) DEFAULT 'text', -- replaces ENUM
    total_tokens_used INT DEFAULT 0,
    total_api_calls INT DEFAULT 0,
    session_status VARCHAR(50) DEFAULT 'active', -- replaces ENUM
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (consultation_id) REFERENCES consultation(consultation_id) ON DELETE CASCADE,
    INDEX idx_cs_consultation (consultation_id)
) ENGINE=InnoDB;

CREATE TABLE consultation_messages (
    message_id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT NOT NULL,
    sender_type VARCHAR(50) NOT NULL, -- replaces ENUM
    message_text LONGTEXT,
    audio_url TEXT,
    processing_time_ms INT DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES consultation_sessions(session_id) ON DELETE CASCADE,
    INDEX idx_cm_session (session_id)
) ENGINE=InnoDB;

CREATE TABLE consultation_transcripts (
    transcript_id INT PRIMARY KEY AUTO_INCREMENT,
    consultation_id INT NOT NULL,
    transcript_text LONGTEXT,
    file_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (consultation_id) REFERENCES consultation(consultation_id) ON DELETE CASCADE
) ENGINE=InnoDB;


CREATE TABLE api_usage_logs (
    usage_id INT PRIMARY KEY AUTO_INCREMENT,
    hospital_id INT NULL,
    doctor_id INT NULL,
    patient_id INT NULL,
    session_id INT NULL,
    service_type VARCHAR(100) NOT NULL, -- replaces ENUM
    tokens_used INT DEFAULT 0,
    api_calls INT DEFAULT 1,
    cost DECIMAL(10,4) DEFAULT 0,
    response_time_ms INT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'success', -- replaces ENUM
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (hospital_id) REFERENCES hospital_master(hospital_id) ON DELETE SET NULL,
    FOREIGN KEY (doctor_id) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (patient_id) REFERENCES users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (session_id) REFERENCES consultation_sessions(session_id) ON DELETE SET NULL,
    INDEX idx_timestamp (timestamp),
    INDEX idx_hospital_usage (hospital_id, timestamp),
    INDEX idx_doctor_usage (doctor_id, timestamp)
) ENGINE=InnoDB;

CREATE TABLE notifications (
    notification_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) DEFAULT 'info', -- replaces ENUM
    category VARCHAR(100) DEFAULT 'system', -- replaces ENUM
    is_read BOOLEAN DEFAULT FALSE,
    action_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_notifications (user_id, is_read, created_at)
) ENGINE=InnoDB;

CREATE TABLE user_settings (
    user_id INT PRIMARY KEY,
    notification_email BOOLEAN DEFAULT TRUE,
    notification_sms BOOLEAN DEFAULT FALSE,
    language_preference VARCHAR(10) DEFAULT 'en',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE audit_logs (
    audit_id INT PRIMARY KEY AUTO_INCREMENT,
    event_type VARCHAR(255),
    entity_type VARCHAR(50), -- replaces ENUM
    entity_id INT,
    user_actor INT NULL, -- who caused event
    event_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    old_values JSON,
    new_values JSON,
    user_agent TEXT,
    FOREIGN KEY (user_actor) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_user_actor (user_actor),
    INDEX idx_event_time (event_time)
) ENGINE=InnoDB;

-- =========================================================
-- User Permissions (materialized)
-- =========================================================

CREATE TABLE user_permissions (
    user_permission_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    permission_id INT NOT NULL,
    permission_name VARCHAR(150) NOT NULL,
    scope VARCHAR(50) NOT NULL, -- 'platform' or 'tenant'
    hospital_id INT NULL,
    hospital_id_coalesced INT AS (COALESCE(hospital_id, 0)) STORED,
    granted_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_perm (user_id, permission_id, hospital_id_coalesced, scope),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permission_master(permission_id) ON DELETE CASCADE,
    INDEX idx_up_user (user_id),
    INDEX idx_up_permission (permission_id),
    INDEX idx_up_hospital (hospital_id)
) ENGINE=InnoDB;
INSERT INTO role_master (role_id, role_name, role_scope, description, created_at)
VALUES
  (1, 'superadmin',     'platform', 'Global super administrator with full access', NOW()),
  (2, 'hospital_admin', 'tenant',   'Administrator for a hospital tenant', NOW()),
  (3, 'doctor',         'tenant',   'Doctor role tied to a hospital tenant', NOW()),
  (4, 'patient',        'tenant',   'Patient role tied to a hospital tenant', NOW())
ON DUPLICATE KEY UPDATE role_name = VALUES(role_name); 
INSERT INTO permission_master (permission_name, description, created_at)
VALUES
  ('auth.register.patient', 'Patient registration', NOW()),
  ('auth.register.doctor', 'Doctor registration', NOW()),
  ('auth.logout', 'User logout', NOW()),
  ('auth.refresh', 'Refresh JWT token', NOW()),
  ('patient.profile.view', 'View patient profile', NOW()),
  ('patient.profile.update', 'Update patient profile', NOW()),
  ('patient.profile.avatar.upload', 'Upload patient profile avatar', NOW()),
  ('specialty.list', 'List specialties', NOW()),
  ('doctor.search', 'Search doctors', NOW()),
  ('doctor.view', 'View doctor details', NOW()),
  ('patient.consultation.list', 'List patient consultations', NOW()),
  ('doctor.profile.view', 'View doctor profile', NOW()),
  ('doctor.profile.update', 'Update doctor profile', NOW()),
  ('doctor.patients.list', 'List patients for a doctor', NOW()),
  ('doctor.patient.view', 'View patient details for doctor', NOW()),
  ('doctor.patient.consultations.list', 'List patient consultations for doctor', NOW()),
  ('doctor.analytics.patients', 'Doctor patient analytics', NOW()),
  ('doctor.consultations.monthly', 'Monthly doctor consultations', NOW()),
  ('hospital.profile.view', 'View hospital profile', NOW()),
  ('hospital.profile.update', 'Update hospital profile', NOW()),
  ('hospital.specialities.list', 'List hospital specialities', NOW()),
  ('hospital.speciality.create', 'Create hospital speciality', NOW()),
  ('hospital.speciality.update', 'Update hospital speciality', NOW()),
  ('hospital.speciality.delete', 'Delete hospital speciality', NOW()),
  ('hospital.doctors.list', 'List hospital doctors', NOW()),
  ('hospital.doctor.create', 'Create doctor in hospital', NOW()),
  ('hospital.doctor.update', 'Update doctor in hospital', NOW()),
  ('hospital.doctor.delete', 'Delete doctor in hospital', NOW()),
  ('hospital.doctor.performance.view', 'View doctor performance metrics', NOW()),
  ('hospital.patients.list', 'List hospital patients', NOW()),
  ('search.doctors', 'Search doctors public', NOW()),
  ('search.hospitals', 'Search hospitals public', NOW()),
  ('search.specialties', 'Search specialties public', NOW()),
  ('upload.profile_image', 'Upload profile images', NOW()),
  ('upload.profile_audio', 'Upload profile audio', NOW())
ON DUPLICATE KEY UPDATE permission_name = VALUES(permission_name); 



INSERT INTO role_permission (role_id, permission_id, created_at)
SELECT rm.role_id, pm.permission_id, NOW()
FROM role_master rm
CROSS JOIN permission_master pm
WHERE rm.role_name = 'superadmin'
  AND (rm.role_id, pm.permission_id) NOT IN (SELECT role_id, permission_id FROM role_permission);
  
INSERT INTO hospital_role_permission (hospital_role_id, permission_id, created_at)
SELECT hr.hospital_role_id, pm.permission_id, NOW()
FROM hospital_role hr
JOIN permission_master pm ON pm.permission_name IN (
  'hospital.profile.view','hospital.profile.update',
  'hospital.specialities.list','hospital.speciality.create','hospital.speciality.update','hospital.speciality.delete',
  'hospital.doctors.list','hospital.doctor.create','hospital.doctor.update','hospital.doctor.delete','hospital.doctor.performance.view',
  'hospital.patients.list',
  'doctor.view','doctor.profile.view','doctor.profile.update',
  'patient.profile.view','patient.profile.update',
  'patient.profile.avatar.upload',
  'patient.consultation.list',
  'upload.profile_image','upload.profile_audio'
)
WHERE hr.role_name = 'hospital_admin'
  AND (hr.hospital_role_id, pm.permission_id) NOT IN (SELECT hospital_role_id, permission_id FROM hospital_role_permission);

INSERT INTO hospital_role_permission (hospital_role_id, permission_id, created_at)
SELECT hr.hospital_role_id, pm.permission_id, NOW()
FROM hospital_role hr
JOIN permission_master pm ON pm.permission_name IN (
  'doctor.view','doctor.profile.view','doctor.profile.update',
  'doctor.patients.list','doctor.patient.view','doctor.patient.consultations.list',
  'patient.consultation.list','doctor.analytics.patients','doctor.consultations.monthly',
  'upload.profile_image','upload.profile_audio','appointment.create','consultation.start'
)
WHERE hr.role_name = 'doctor'
  AND (hr.hospital_role_id, pm.permission_id) NOT IN (SELECT hospital_role_id, permission_id FROM hospital_role_permission);


INSERT INTO hospital_role_permission (hospital_role_id, permission_id, created_at)
SELECT hr.hospital_role_id, pm.permission_id, NOW()
FROM hospital_role hr
JOIN permission_master pm ON pm.permission_name IN (
  'patient.profile.view','patient.profile.update','patient.profile.avatar.upload',
  'patient.consultation.list','appointment.create','upload.profile_image'
)
WHERE hr.role_name = 'patient'
  AND (hr.hospital_role_id, pm.permission_id) NOT IN (SELECT hospital_role_id, permission_id FROM hospital_role_permission);
