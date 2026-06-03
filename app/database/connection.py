import sys
import pg8000
from app.core.config import settings


def _safe_print(msg: str) -> None:
    """Windows CP949 환경에서도 안전하게 출력하는 헬퍼 — 인코딩 오류 시 무시"""
    try:
        print(msg)
    except Exception:
        try:
            sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
            sys.stdout.buffer.flush()
        except Exception:
            pass  # 최후의 수단: 출력 실패를 조용히 무시


def get_db_connection():
    """GCP Cloud SQL PostgreSQL 연결 반환. 설정이 없을 경우 None 반환"""
    db_name = getattr(settings, "DB_NAME", None)
    db_user = getattr(settings, "DB_USER", "postgres")
    db_pass = getattr(settings, "DB_PASS", None)
    db_host = getattr(settings, "DB_HOST", None)
    db_port = getattr(settings, "DB_PORT", 5432)
    cloud_sql_conn = getattr(settings, "CLOUD_SQL_CONNECTION_NAME", None)

    if not db_name or db_name.startswith("your-"):
        print("[database] GCP 데이터베이스 연결 변수가 설정되지 않음 (오프라인 모드)")
        return None

    # 1단계: UNIX 소켓 연결 시도 (Cloud Run & Cloud SQL 환경)
    if sys.platform != "win32" and cloud_sql_conn and not cloud_sql_conn.startswith("your-"):
        sock_path = f"/cloudsql/{cloud_sql_conn}/.s.PGSQL.5432"
        _safe_print(f"[database] UNIX 소켓 연결 시도 중... (경로: {sock_path}, 계정: {db_user}, DB: {db_name})")
        try:
            conn = pg8000.dbapi.connect(
                unix_sock=sock_path,
                user=db_user,
                password=db_pass,
                database=db_name,
            )
            _safe_print("[database] UNIX 소켓 연결 성공!")
            return conn
        except Exception as e:
            _safe_print(f"[database] UNIX 소켓 연결 실패: {str(e)[:120]}. TCP/IP 방식으로 폴백 시도합니다.")

    # 2단계: TCP/IP 연결 시도 (로컬 개발 환경 및 TCP 폴백)
    if db_host and not db_host.startswith("your-"):
        _safe_print(f"[database] TCP/IP 연결 시도 중... (호스트: {db_host}:{db_port}, 계정: {db_user}, DB: {db_name})")
        try:
            conn = pg8000.dbapi.connect(
                host=db_host,
                port=int(db_port),
                user=db_user,
                password=db_pass,
                database=db_name,
            )
            _safe_print("[database] TCP/IP 연결 성공!")
            return conn
        except Exception as e:
            _safe_print(f"[database] TCP/IP 연결 실패: {str(e)[:120]}")

    _safe_print("[database] 모든 데이터베이스 연결 시도가 실패하였습니다. 오프라인 모드로 폴백합니다.")
    return None
