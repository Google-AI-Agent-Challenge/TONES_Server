import sys
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import pg8000
from app.core.config import settings
from app.services.user_service import UserService
from app.services.ai_service import AIService
from app.services.dashboard_service import DashboardService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token")

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
    try:
        # UNIX 소켓 연결 (GCP Cloud SQL)
        if sys.platform != "win32" and cloud_sql_conn and not cloud_sql_conn.startswith("your-"):
            conn = pg8000.dbapi.connect(
                unix_sock=f"/cloudsql/{cloud_sql_conn}/.s.PGSQL.5432",
                user=db_user,
                password=db_pass,
                database=db_name,
            )
            return conn
        # TCP/IP 연결 (로컬/원격 PostgreSQL)
        elif db_host and not db_host.startswith("your-"):
            conn = pg8000.dbapi.connect(
                host=db_host,
                port=int(db_port),
                user=db_user,
                password=db_pass,
                database=db_name,
            )
            return conn
    except Exception as e:
        print(f"[deps] 데이터베이스 연결 실패: {e}")
    return None

def get_user_service(db_conn: pg8000.dbapi.Connection = Depends(get_db_connection)) -> UserService:
    return UserService(db_conn)

def get_ai_service(db_conn: pg8000.dbapi.Connection = Depends(get_db_connection)) -> AIService:
    return AIService(db_conn)

def get_dashboard_service(db_conn: pg8000.dbapi.Connection = Depends(get_db_connection)) -> DashboardService:
    return DashboardService(db_conn)

def get_current_user() -> dict:
    return {"id": "user_12345", "email": "test@example.com", "full_name": "Test User", "is_active": True}
