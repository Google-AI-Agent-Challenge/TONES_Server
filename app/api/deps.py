from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from supabase import create_client, Client
from pinecone import Pinecone
from app.core.config import settings
from app.core.security import ALGORITHM
from app.schemas.auth import TokenPayload
from app.services.user_service import UserService
from app.services.ai_service import AIService
from app.services.dashboard_service import DashboardService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token"
)

_supabase_client: Client | None = None
_pinecone_client: Pinecone | None = None


def get_supabase_client() -> Client | None:
    global _supabase_client
    if _supabase_client is None:
        try:
            _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        except Exception as e:
            print(f"Supabase 클라이언트 생성 실패 (더미 설정 모드 활성): {e}")
            _supabase_client = None
    return _supabase_client


def get_pinecone_client() -> Pinecone | None:
    global _pinecone_client
    if _pinecone_client is None:
        try:
            if settings.PINECONE_API_KEY and not settings.PINECONE_API_KEY.startswith("your-"):
                _pinecone_client = Pinecone(api_key=settings.PINECONE_API_KEY)
            else:
                _pinecone_client = None
        except Exception as e:
            print(f"Pinecone 클라이언트 생성 실패 (더미 설정 모드 활성): {e}")
            _pinecone_client = None
    return _pinecone_client


def get_user_service(
    supabase_client: Client | None = Depends(get_supabase_client)
) -> UserService:
    return UserService(supabase_client)


def get_ai_service(
    pinecone_client: Pinecone | None = Depends(get_pinecone_client)
) -> AIService:
    return AIService(pinecone_client)


def get_dashboard_service(
    supabase_client: Client | None = Depends(get_supabase_client)
) -> DashboardService:
    return DashboardService(supabase_client)



def get_current_user() -> dict:
    # 프로토타입 개발을 위한 JWT 인증 비활성화: 항상 테스트 더미 사용자 반환
    return {
        "id": "user_12345",
        "email": "test@example.com",
        "full_name": "Test User",
        "is_active": True
    }
