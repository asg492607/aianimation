from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator, EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

    # App
    PROJECT_NAME: str = "AnimateAI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Security
    SECRET_KEY: str = "super_secret_key_change_me"
    REFRESH_SECRET_KEY: str = "super_secret_refresh_key_change_me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 1
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24

    # Database
    POSTGRES_SERVER: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        if isinstance(v, str):
            # SQLAlchemy asyncpg requires postgresql+asyncpg:// instead of postgres://
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
            return v
            
        data = info.data
        if data.get("POSTGRES_USER"):
            return (
                f"postgresql+asyncpg://{data['POSTGRES_USER']}:{data['POSTGRES_PASSWORD']}"
                f"@{data['POSTGRES_SERVER']}:{data['POSTGRES_PORT']}/{data['POSTGRES_DB']}"
            )
        return ""

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    @field_validator("CELERY_BROKER_URL", mode="before")
    @classmethod
    def assemble_celery_broker(cls, v: Optional[str], info) -> str:
        if isinstance(v, str):
            return v
        data = info.data
        redis_pass = data.get("REDIS_PASSWORD")
        if redis_pass:
            return f"redis://:{redis_pass}@{data['REDIS_HOST']}:{data['REDIS_PORT']}/1"
        return f"redis://{data['REDIS_HOST']}:{data['REDIS_PORT']}/1"

    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def assemble_celery_backend(cls, v: Optional[str], info) -> str:
        if isinstance(v, str):
            return v
        data = info.data
        redis_pass = data.get("REDIS_PASSWORD")
        if redis_pass:
            return f"redis://:{redis_pass}@{data['REDIS_HOST']}:{data['REDIS_PORT']}/2"
        return f"redis://{data['REDIS_HOST']}:{data['REDIS_PORT']}/2"

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    ALLOWED_HOSTS: List[str] = ["*"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Storage
    STORAGE_BACKEND: str = "local"  # local, s3, minio
    LOCAL_STORAGE_PATH: str = "/app/media"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: Optional[str] = None
    MINIO_ENDPOINT: Optional[str] = None
    MINIO_ACCESS_KEY: Optional[str] = None
    MINIO_SECRET_KEY: Optional[str] = None
    MINIO_BUCKET: str = "animateai"
    MINIO_SECURE: bool = False

    # Groq AI
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama3-70b-8192"
    GROQ_MAX_TOKENS: int = 4096
    GROQ_TEMPERATURE: float = 0.7

    # Phase 8 Providers
    FAL_API_KEY: Optional[str] = None
    ELEVENLABS_API_KEY: Optional[str] = None

    # Email
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = 587
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[EmailStr] = None
    EMAILS_FROM_NAME: Optional[str] = "AnimateAI"

    # FFmpeg
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"

    # Rate Limiting
    RATE_LIMIT_CALLS: int = 100
    RATE_LIMIT_PERIOD: int = 60

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    ALLOWED_AUDIO_TYPES: List[str] = ["audio/mpeg", "audio/wav", "audio/ogg"]


settings = Settings()
