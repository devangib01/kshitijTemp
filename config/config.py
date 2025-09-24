from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    JWT_SECRET: str = "dev-secret"
    JWT_ALGORITHM: str = "HS256"
    DATABASE_URL: str = "mysql+asyncmy://root:1234@localhost:3306/avatar_doctor_managementprofile_V4"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    ACCESS_TOKEN_EXPIRY_SECONDS: int = 4000
    JTI_EXPIRY_SECONDS: int = 3600
    ENFORCE_TRUSTED_IPS: bool = False
    SHOW_ERRORS: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


Config = Settings()
