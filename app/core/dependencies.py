from fastapi import Depends
from app.database.connection import get_db_connection


def get_user_service(db_conn=Depends(get_db_connection)):
    from app.domains.users.service import UserService
    return UserService(db_conn)


def get_ai_service(db_conn=Depends(get_db_connection)):
    from app.domains.ai_search.service import AIService
    return AIService(db_conn)


def get_dashboard_service(db_conn=Depends(get_db_connection)):
    from app.domains.dashboard.service import DashboardService
    return DashboardService(db_conn)


def get_current_user(
    db_conn=Depends(get_db_connection),
) -> dict:
    # [Prototype Mode] 데모 시연을 위해 모든 토큰 검증 및 헤더 장벽을 완전히 비활성화함
    # 어떠한 헤더가 들어오든 즉시 최고 관리자 권한 세션으로 통과 처리
    return {
        "id": "user_12345",
        "email": "test@example.com",
        "full_name": "Test User",
        "is_active": True,
        "role": "super_admin",
        "last_login_at": "2026-06-02T15:20:16Z"
    }
