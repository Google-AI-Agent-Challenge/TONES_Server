from fastapi import APIRouter, Depends, HTTPException
from app.api import deps
import pg8000

router = APIRouter()


@router.get("/status")
def get_integrations_status(
    db_conn: pg8000.dbapi.Connection = Depends(deps.get_db_connection),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    제어센터 - 외부 연동 상태 (네이버, 올리브영 연동 정보 및 동기화 진행율/에러 상태) 반환 API (인증 필요)
    """
    # 기본 Mock 데이터 제공 준비
    integrations_status = [
        {"platform_name": "naver", "status": "connected", "sync_rate": 98.0, "error_message": None, "last_synced_at": "2026-06-02T15:20:16Z"},
        {"platform_name": "olive_young", "status": "error", "sync_rate": 40.0, "error_message": "408 Request Timeout", "last_synced_at": "2026-06-02T10:15:30Z"}
    ]
    
    if db_conn is not None:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "SELECT platform_name, status, sync_rate, error_message, last_synced_at::text FROM public.integrations"
            )
            rows = cursor.fetchall()
            cursor.close()
            if rows:
                integrations_status = [{
                    "platform_name": r[0],
                    "status": r[1],
                    "sync_rate": float(r[2]),
                    "error_message": r[3],
                    "last_synced_at": r[4]
                } for r in rows]
        except Exception as e:
            print(f"[Integrations.get_status] DB 조회 실패, Mock 폴백: {e}")
            
    return integrations_status
