from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "TONES Server"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = "super-secret-key-change-this-in-production-12345"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # GCP & Cloud SQL Config
    GCP_PROJECT_ID: Optional[str] = None
    GCP_REGION: str = "us-central1"
    CLOUD_SQL_CONNECTION_NAME: Optional[str] = None
    DB_USER: str = "postgres"
    DB_PASS: Optional[str] = None
    DB_NAME: str = "postgres"
    DB_HOST: Optional[str] = None
    DB_PORT: int = 5432

    # Sentry Config
    SENTRY_DSN: Optional[str] = None

    # Google Gemini Config
    GEMINI_API_KEY: Optional[str] = None

    # Google Docs API Config
    # 방법 1 (운영/Cloud Run): JSON 키 내용 전체를 한 줄 문자열로 직접 주입
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None
    # 방법 2 (로컬 개발): JSON 키 파일 경로 지정 (GOOGLE_SERVICE_ACCOUNT_JSON 없을 때 fallback)
    GOOGLE_SERVICE_ACCOUNT_KEY_FILE: Optional[str] = None
    
    # CORS Config
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
