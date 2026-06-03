from fastapi import APIRouter, Depends, Query, HTTPException

from app.core.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.domains.layout.schemas import LayoutSaveRequest
from app.domains.layout.service import LayoutService

router = APIRouter()


def get_layout_service(db_conn=Depends(get_db_connection)) -> LayoutService:
    return LayoutService(db_conn)


@router.get("")
def get_layout(
    token: str = Query(..., description="사용자 식별 토큰"),
    layout_service: LayoutService = Depends(get_layout_service),
    current_user: dict = Depends(get_current_user)
):
    """공통 - 위젯 고정 레이아웃 조회 API (인증 필요)"""
    pinned = layout_service.load_layout(token)
    return {"pinned_widget": pinned}


@router.put("")
def save_layout_put(
    payload: LayoutSaveRequest,
    layout_service: LayoutService = Depends(get_layout_service),
    current_user: dict = Depends(get_current_user)
):
    """공통 - 위젯 고정 레이아웃 저장/변경 API (PUT, 인증 필요)"""
    success = layout_service.save_layout(payload.token, payload.pinned_widget)
    if not success:
        raise HTTPException(status_code=500, detail="레이아웃 저장에 실패했습니다.")
    return {"success": True}


@router.post("")
def save_layout_post(
    payload: LayoutSaveRequest,
    layout_service: LayoutService = Depends(get_layout_service),
    current_user: dict = Depends(get_current_user)
):
    """공통 - 위젯 고정 레이아웃 저장/변경 API (POST 호환성 지원, 인증 필요)"""
    success = layout_service.save_layout(payload.token, payload.pinned_widget)
    if not success:
        raise HTTPException(status_code=500, detail="레이아웃 저장에 실패했습니다.")
    return {"success": True}
