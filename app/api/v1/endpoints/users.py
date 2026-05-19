from typing import Any
from fastapi import APIRouter, Depends
from app.api import deps
from app.schemas.user import User

router = APIRouter()


@router.get("/me", response_model=User)
def read_user_me(
    current_user: dict = Depends(deps.get_current_user)
) -> Any:
    """
    로그인한 현재 사용자의 정보 조회 API
    """
    return current_user
