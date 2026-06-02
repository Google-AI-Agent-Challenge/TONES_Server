import sys
import jwt
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
import pg8000
from app.core.config import settings
from app.services.user_service import UserService
from app.services.ai_service import AIService
from app.services.dashboard_service import DashboardService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

_connector = None

def get_db_connection():
    """GCP Cloud SQL PostgreSQL 연결 반환. 설정이 없을 경우 None 반환"""
    global _connector
    db_name = getattr(settings, "DB_NAME", None)
    db_user = getattr(settings, "DB_USER", "postgres")
    db_pass = getattr(settings, "DB_PASS", None)
    db_host = getattr(settings, "DB_HOST", None)
    db_port = getattr(settings, "DB_PORT", 5432)
    cloud_sql_conn = getattr(settings, "CLOUD_SQL_CONNECTION_NAME", None)
    
    if not db_name or db_name.startswith("your-"):
        print("[deps] GCP 데이터베이스 연결 변수가 설정되지 않음 (오프라인 모드)")
        return None

    # 1단계: UNIX 소켓 연결 시도 (리눅스 기반 Cloud Run & Cloud SQL 인스턴스 연동 환경)
    if sys.platform != "win32" and cloud_sql_conn and not cloud_sql_conn.startswith("your-"):
        sock_path = f"/cloudsql/{cloud_sql_conn}/.s.PGSQL.5432"
        print(f"[deps] UNIX 소켓 방식으로 연결 시도 중... (경로: {sock_path}, 계정: {db_user}, DB: {db_name})")
        try:
            conn = pg8000.dbapi.connect(
                unix_sock=sock_path,
                user=db_user,
                password=db_pass,
                database=db_name,
            )
            print("[deps] UNIX 소켓 연결 성공!")
            return conn
        except Exception as e:
            print(f"[deps] UNIX 소켓 연결 실패: {e}. TCP/IP 방식으로 폴백 시도합니다.")

    # 2단계: TCP/IP 연결 시도 (로컬 개발 환경 및 TCP 폴백)
    if db_host and not db_host.startswith("your-"):
        print(f"[deps] TCP/IP 방식으로 연결 시도 중... (호스트: {db_host}:{db_port}, 계정: {db_user}, DB: {db_name})")
        try:
            conn = pg8000.dbapi.connect(
                host=db_host,
                port=int(db_port),
                user=db_user,
                password=db_pass,
                database=db_name,
            )
            print("[deps] TCP/IP 연결 성공!")
            return conn
        except Exception as e:
            print(f"[deps] TCP/IP 연결 실패: {e}")
            
    print("[deps] 모든 데이터베이스 연결 시도가 실패하였습니다. 오프라인 모드로 폴백합니다.")
    return None

def get_user_service(db_conn: pg8000.dbapi.Connection = Depends(get_db_connection)) -> UserService:
    return UserService(db_conn)

def get_ai_service(db_conn: pg8000.dbapi.Connection = Depends(get_db_connection)) -> AIService:
    return AIService(db_conn)

def get_dashboard_service(db_conn: pg8000.dbapi.Connection = Depends(get_db_connection)) -> DashboardService:
    return DashboardService(db_conn)

def get_current_user(
    authorization: str | None = Header(None),
    user_service: UserService = Depends(get_user_service)
) -> dict:
    # [Prototype Mode] 데모 시연을 위해 모든 토큰 검증 및 헤더 장벽을 완전히 100% 비활성화함
    # 어떠한 헤더가 들어오든, 혹은 들어오지 않든 즉시 최고 관리자 권한 세션으로 통과 처리
    return {
        "id": "user_12345", 
        "email": "test@example.com", 
        "full_name": "Test User", 
        "is_active": True,
        "role": "super_admin",
        "last_login_at": "2026-06-02T15:20:16Z"
    }
