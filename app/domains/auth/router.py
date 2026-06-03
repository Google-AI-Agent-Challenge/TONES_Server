from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.security import create_access_token
from app.core.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.domains.auth.schemas import (
    Token, UserLogin,
    FindEmailRequest, FindEmailResponse,
    FindPasswordRequest, FindPasswordResponse,
)
from app.domains.users.schemas import User, UserCreate
from app.domains.auth.service import AuthService

router = APIRouter()


def get_auth_service(db_conn=Depends(get_db_connection)) -> AuthService:
    return AuthService(db_conn)


@router.post("/login", response_model=Token)
def login(
    payload: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
) -> Any:
    """JSON 기반 로그인 API (이메일 및 패스워드를 바디로 수신)"""
    user = auth_service.authenticate(payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이메일 또는 비밀번호가 잘못되었습니다."
        )
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비활성화된 사용자 계정입니다."
        )
    auth_service.update_last_login(user["email"])
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(user["email"], expires_delta=access_token_expires),
        "token_type": "bearer",
    }


@router.post("/login/access-token", response_model=Token)
def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
) -> Any:
    """OAuth2 호환 액세스 토큰 획득 로그인 API (폼 데이터 기반)"""
    user = auth_service.authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이메일 또는 비밀번호가 잘못되었습니다."
        )
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비활성화된 사용자 계정입니다."
        )
    auth_service.update_last_login(user["email"])
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(user["email"], expires_delta=access_token_expires),
        "token_type": "bearer",
    }


@router.post("/logout")
def logout() -> Any:
    """사용자 로그아웃 API"""
    return {"success": True, "message": "성공적으로 로그아웃되었습니다."}


@router.post("/signup", response_model=User)
def register_user(
    user_in: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
) -> Any:
    """신규 사용자 회원가입 API"""
    existing = auth_service.get_by_email(user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 이메일입니다."
        )
    return auth_service.register(user_in)


@router.post("/find-email", response_model=FindEmailResponse)
def find_email(
    payload: FindEmailRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> Any:
    """이름(full_name)을 기반으로 가입된 이메일을 조회하는 API"""
    email = auth_service.find_email_by_name(payload.full_name)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 이름으로 등록된 사용자를 찾을 수 없습니다."
        )
    return FindEmailResponse(email=email)


@router.post("/find-password", response_model=FindPasswordResponse)
def find_password(
    payload: FindPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> Any:
    """이메일과 이름을 기반으로 임시 비밀번호를 재설정하여 발급하는 API"""
    temp_password = auth_service.reset_password_temp(payload.email, payload.full_name)
    if not temp_password:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="이메일과 이름이 일치하는 사용자를 찾을 수 없습니다."
        )
    return FindPasswordResponse(temp_password=temp_password)
