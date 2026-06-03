from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.domains.settings.schemas import SettingsUpdatePayload
from app.domains.settings.service import SettingsService

router = APIRouter()


def get_settings_service(db_conn=Depends(get_db_connection)) -> SettingsService:
    return SettingsService(db_conn)


@router.get("")
def get_system_settings(
    settings_service: SettingsService = Depends(get_settings_service),
    current_user: dict = Depends(get_current_user)
):
    """제어센터 - 알림 및 시스템 환경 설정 조회 API (인증 필요)"""
    return settings_service.get_settings()


@router.put("")
def update_system_settings(
    payload: SettingsUpdatePayload,
    settings_service: SettingsService = Depends(get_settings_service),
    current_user: dict = Depends(get_current_user)
):
    """제어센터 - 알림 및 시스템 환경 설정 수정 API (인증 필요)"""
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        return {"success": True, "message": "변경할 항목이 없습니다."}
    try:
        settings_service.update_settings(update_data)
        return {"success": True, "message": "설정이 성공적으로 저장되었습니다."}
    except Exception:
        raise HTTPException(status_code=500, detail="설정 저장 중 데이터베이스 오류가 발생했습니다.")


@router.post("/reset")
def reset_system_settings(
    settings_service: SettingsService = Depends(get_settings_service),
    current_user: dict = Depends(get_current_user)
):
    """제어센터 - 알림 및 환경 설정 기본값 초기화 API (인증 필요)"""
    try:
        settings_service.reset_settings()
        return {"success": True, "message": "모든 시스템 환경 설정이 기본값으로 초기화되었습니다."}
    except Exception:
        raise HTTPException(status_code=500, detail="설정 초기화 중 데이터베이스 오류가 발생했습니다.")
