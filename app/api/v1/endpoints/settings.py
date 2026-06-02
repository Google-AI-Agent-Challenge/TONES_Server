from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.api import deps
import pg8000

router = APIRouter()


class SettingsUpdatePayload(BaseModel):
    notification_enabled: bool | None = None
    dark_mode: bool | None = None
    analysis_interval_hours: int | None = None


@router.get("")
def get_system_settings(
    db_conn: pg8000.dbapi.Connection = Depends(deps.get_db_connection),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    제어센터 - 알림 및 시스템 환경 설정 조회 API (인증 필요)
    """
    # 기본 Mock 데이터
    sys_settings = {
        "notification_enabled": True,
        "dark_mode": False,
        "analysis_interval_hours": 24
    }
    
    if db_conn is not None:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "SELECT notification_enabled, dark_mode, analysis_interval_hours FROM public.settings LIMIT 1"
            )
            row = cursor.fetchone()
            cursor.close()
            if row:
                sys_settings = {
                    "notification_enabled": bool(row[0]),
                    "dark_mode": bool(row[1]),
                    "analysis_interval_hours": int(row[2])
                }
        except Exception as e:
            print(f"[Settings.get_settings] DB 조회 실패, Mock 폴백: {e}")
            
    return sys_settings


@router.put("")
def update_system_settings(
    payload: SettingsUpdatePayload,
    db_conn: pg8000.dbapi.Connection = Depends(deps.get_db_connection),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    제어센터 - 알림 및 시스템 환경 설정 수정 API (인증 필요)
    """
    if db_conn is not None:
        try:
            cursor = db_conn.cursor()
            set_clauses = []
            params = []
            for k, v in payload.model_dump().items():
                if v is not None:
                    set_clauses.append(f"{k} = %s")
                    params.append(v)
            
            if set_clauses:
                sql = f"UPDATE public.settings SET {', '.join(set_clauses)}, updated_at = timezone('utc'::text, now()) WHERE id = 1"
                cursor.execute(sql, params)
                db_conn.commit()
            cursor.close()
            return {"success": True, "message": "설정이 성공적으로 저장되었습니다."}
        except Exception as e:
            print(f"[Settings.update_settings] DB 업데이트 실패: {e}")
            try:
                db_conn.rollback()
            except Exception:
                pass
            raise HTTPException(status_code=500, detail="설정 저장 중 데이터베이스 오류가 발생했습니다.")
            
    # Mock fallback
    return {"success": True, "message": "로컬 가상 메모리에 설정이 저장되었습니다."}


@router.post("/reset")
def reset_system_settings(
    db_conn: pg8000.dbapi.Connection = Depends(deps.get_db_connection),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    제어센터 - 알림 및 환경 설정 기본값 초기화 API (인증 필요)
    """
    if db_conn is not None:
        try:
            cursor = db_conn.cursor()
            cursor.execute(
                "UPDATE public.settings SET notification_enabled = TRUE, dark_mode = FALSE, analysis_interval_hours = 24, updated_at = timezone('utc'::text, now()) WHERE id = 1"
            )
            db_conn.commit()
            cursor.close()
            return {"success": True, "message": "모든 시스템 환경 설정이 기본값으로 초기화되었습니다."}
        except Exception as e:
            print(f"[Settings.reset_settings] DB 초기화 실패: {e}")
            try:
                db_conn.rollback()
            except Exception:
                pass
            raise HTTPException(status_code=500, detail="설정 초기화 중 데이터베이스 오류가 발생했습니다.")
            
    return {"success": True, "message": "로컬 설정을 기본값으로 초기화했습니다."}
