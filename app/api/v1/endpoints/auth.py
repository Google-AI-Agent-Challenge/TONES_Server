from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.api import deps
from app.schemas.auth import Token
from app.schemas.user import User, UserCreate
from app.services.user_service import UserService

router = APIRouter()


@router.post("/login/access-token", response_model=Token)
def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(deps.get_user_service)
) -> Any:
    """
    OAuth2 호환 액세스 토큰 획득 로그인 API
    """
    user = user_service.get_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이메일 또는 비밀번호가 잘못되었습니다."
        )
    elif not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비활성화된 사용자 계정입니다."
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            user["email"], expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.post("/signup", response_model=User)
def register_user(
    user_in: UserCreate,
    user_service: UserService = Depends(deps.get_user_service)
) -> Any:
    """
    신규 사용자 회원가입 API
    """
    user = user_service.get_by_email(user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 이메일입니다."
        )
    new_user = user_service.create(user_in)
    return new_user
