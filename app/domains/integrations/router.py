from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.domains.integrations.service import IntegrationsService

router = APIRouter()


def get_integrations_service(db_conn=Depends(get_db_connection)) -> IntegrationsService:
    return IntegrationsService(db_conn)


@router.get("/status")
def get_integrations_status(
    integrations_service: IntegrationsService = Depends(get_integrations_service),
    current_user: dict = Depends(get_current_user)
):
    """제어센터 - 외부 연동 상태 (네이버, 올리브영 연동 정보 및 동기화 진행율/에러 상태) 반환 API (인증 필요)"""
    return integrations_service.get_status()
