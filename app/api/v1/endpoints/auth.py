from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.api import deps
from app.schemas.auth import Token, FindEmailRequest, FindEmailResponse, FindPasswordRequest, FindPasswordResponse
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


@router.post("/find-email", response_model=FindEmailResponse)
def find_email(
    payload: FindEmailRequest,
    user_service: UserService = Depends(deps.get_user_service)
) -> Any:
    """
    이름(full_name)을 기반으로 가입된 이메일을 조회하는 API
    """
    email = user_service.find_email_by_name(payload.full_name)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 이름으로 등록된 사용자를 찾을 수 없습니다."
        )
    return FindEmailResponse(email=email)


@router.post("/find-password", response_model=FindPasswordResponse)
def find_password(
    payload: FindPasswordRequest,
    user_service: UserService = Depends(deps.get_user_service)
) -> Any:
    """
    이메일과 이름을 기반으로 임시 비밀번호를 재설정하여 발급하는 API
    """
    temp_password = user_service.reset_password_temp(payload.email, payload.full_name)
    if not temp_password:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="이메일과 이름이 일치하는 사용자를 찾을 수 없습니다."
        )
    return FindPasswordResponse(temp_password=temp_password)

