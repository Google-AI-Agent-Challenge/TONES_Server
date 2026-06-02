from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from app.api import deps
from app.services.dashboard_service import DashboardService

router = APIRouter()


class LayoutSaveRequest(BaseModel):
    token: str
    pinned_widget: str | None = None


@router.get("")
def get_layout(
    token: str = Query(..., description="사용자 식별 토큰"),
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    공통 - 위젯 고정 레이아웃 조회 API (인증 필요)
    """
    pinned = dashboard_service.load_layout(token)
    return {"pinned_widget": pinned}


@router.put("")
def save_layout_put(
    payload: LayoutSaveRequest,
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    공통 - 위젯 고정 레이아웃 저장/변경 API (PUT, 인증 필요)
    """
    success = dashboard_service.save_layout(payload.token, payload.pinned_widget)
    if not success:
        raise HTTPException(status_code=500, detail="레이아웃 저장에 실패했습니다.")
    return {"success": True}


@router.post("")
def save_layout_post(
    payload: LayoutSaveRequest,
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    공통 - 위젯 고정 레이아웃 저장/변경 API (POST 호환성 지원, 인증 필요)
    """
    success = dashboard_service.save_layout(payload.token, payload.pinned_widget)
    if not success:
        raise HTTPException(status_code=500, detail="레이아웃 저장에 실패했습니다.")
    return {"success": True}
