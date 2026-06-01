import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

# Sentry 초기화 (DSN이 존재할 때만 실행)
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

app = FastAPI(
    title="TONES Server",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="TONES B2B AI Review Analytics Dashboard Backend API",
    version="1.0.0"
)

# CORS 설정
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 통합 API 라우터 포함
app.include_router(api_router, prefix=settings.API_V1_STR)

# 프론트엔드 호환용 API 라우터 포함
from app.api.v1.endpoints import frontend_compat
app.include_router(frontend_compat.router, prefix="/api", tags=["frontend-compat"])


@app.get("/health", tags=["health"])
def health_check():
    """
    서버 상태 확인용 헬스체크 API
    """
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": "1.0.0"
    }
