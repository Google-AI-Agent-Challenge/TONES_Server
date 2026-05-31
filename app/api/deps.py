from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError as JWTError
import pg8000
from app.core.config import settings
from app.core.security import ALGORITHM
from app.schemas.auth import TokenPayload
from app.services.user_service import UserService
from app.services.ai_service import AIService
from app.services.dashboard_service import DashboardService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token"
)

_connector = None

def get_db_connection():
    """
    GCP Cloud SQL Python Connector 또는 직접 pg8000을 활용해 PostgreSQL 커넥션 반환.
    안전한 릴리즈를 위해 settings에 해당 속성이 없을 경우 getattr 및 기본값 폴백 처리를 적용합니다.
    """
    global _connector

    # 1. 설정 변수 안전 획득 (GCP 및 로컬 연결 설정 대응)
    db_name = getattr(settings, "DB_NAME", None) or getattr(settings, "SUPABASE_URL", "").split("/")[-1].split("?")[0]
    db_user = getattr(settings, "DB_USER", "postgres")
    db_pass = getattr(settings, "DB_PASS", None) or getattr(settings, "SUPABASE_KEY", None)
    db_host = getattr(settings, "DB_HOST", None)
    db_port = getattr(settings, "DB_PORT", 5432)
    cloud_sql_conn = getattr(settings, "CLOUD_SQL_CONNECTION_NAME", None)

    if not db_name or db_name.startswith("your-"):
        print("[deps] GCP 데이터베이스 연결 변수가 설정되지 않았습니다. (오프라인 모킹 활성)")
        return None

    try:
        # A. GCP Cloud SQL UNIX 소켓 직접 연결 시도 (배포 환경 - 무겁고 에러가 잦은 Connector 제거 후 UNIX 소켓 직연결!)
        if cloud_sql_conn and not cloud_sql_conn.startswith("your-"):
            print(f"[deps] GCP Cloud SQL UNIX 소켓 연결 기동: /cloudsql/{cloud_sql_conn}/.s.PGSQL.5432")
            conn = pg8000.dbapi.connect(
                unix_sock=f"/cloudsql/{cloud_sql_conn}/.s.PGSQL.5432",
                user=db_user,
                password=db_pass,
                database=db_name
            )
            return conn

        # B. 로컬 PostgreSQL 및 직접 TCP IP 기반 연결 시도
        elif db_host and not db_host.startswith("your-"):
            print(f"[deps] 로컬/원격 PostgreSQL 직접 연결 시도: {db_host}:{db_port}")
            conn = pg8000.dbapi.connect(
                host=db_host,
                port=int(db_port),
                user=db_user,
                password=db_pass,
                database=db_name
            )
            return conn

        # C. Supabase 연결 URL 파싱을 통한 마이그레이션 과도기 지원 폴백
        elif getattr(settings, "SUPABASE_URL", None) and "supabase.co" in settings.SUPABASE_URL:
            # supabase.co 호스트 파싱
            sb_host = settings.SUPABASE_URL.replace("https://", "").replace("http://", "").split("/")[0]
            sb_db_host = f"db.{sb_host}"
            print(f"[deps] 과도기 Supabase 직접 DB TCP 연결 시도: {sb_db_host}")
            conn = pg8000.dbapi.connect(
                host=sb_db_host,
                port=5432,
                user="postgres",
                password=db_pass,
                database="postgres"
            )
            return conn

    except Exception as e:
        print(f"[deps] 데이터베이스 연결 실패 (오프라인 Mocking 모드 폴백 작동): {e}")

    return None


def get_user_service(
    db_conn = Depends(get_db_connection)
) -> UserService:
    return UserService(db_conn)


def get_ai_service(
    db_conn = Depends(get_db_connection)
) -> AIService:
    return AIService(db_conn)


def get_dashboard_service(
    db_conn = Depends(get_db_connection)
) -> DashboardService:
    return DashboardService(db_conn)


def get_current_user() -> dict:
    # 프로토타입 개발을 위한 JWT 인증 비활성화: 항상 테스트 더미 사용자 반환
    return {
        "id": "user_12345",
        "email": "test@example.com",
        "full_name": "Test User",
        "is_active": True
    }
