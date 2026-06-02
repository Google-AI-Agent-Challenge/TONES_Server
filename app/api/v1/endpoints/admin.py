from typing import List, Optional
from fastapi import APIRouter, Depends, Path, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.api import deps
from app.schemas.user import User, UserCreate
from app.services.user_service import UserService

router = APIRouter()


class AdminUserCreatePayload(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "manager"


class AdminUserUpdatePayload(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


@router.get("/users", response_model=List[User])
def get_admin_users(
    user_service: UserService = Depends(deps.get_user_service),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    제어센터 - 전체 관리자 계정 목록 조회 API (인증 필요, super_admin 이상 권한 추천)
    """
    if current_user.get("role") != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 작업을 수행할 권한이 없습니다. 슈퍼 관리자 전용 권한입니다."
        )
    return user_service.get_all()


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
def create_admin_user(
    payload: AdminUserCreatePayload,
    user_service: UserService = Depends(deps.get_user_service),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    제어센터 - 신규 관리자 계정 추가 API (인증 필요, super_admin 권한 필요)
    """
    if current_user.get("role") != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="슈퍼 관리자 권한이 필요합니다."
        )
        
    existing = user_service.get_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일 주소입니다.")
        
    user_in = UserCreate(
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
        role=payload.role
    )
    return user_service.create(user_in)


@router.patch("/users/{id}", response_model=User)
def update_admin_user(
    id: str = Path(..., description="수정할 사용자 UUID"),
    payload: AdminUserUpdatePayload = None,
    user_service: UserService = Depends(deps.get_user_service),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    제어센터 - 관리자 계정 정보 수정 API (인증 필요, super_admin 권한 필요)
    """
    if current_user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="슈퍼 관리자 권한이 필요합니다.")
        
    if not payload:
        raise HTTPException(status_code=400, detail="수정 필드 정보가 누락되었습니다.")
        
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="최소 1개 이상의 수정 항목을 입력해야 합니다.")
        
    updated = user_service.update_user(user_id=id, fields=update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="존재하지 않는 사용자 계정입니다.")
    return updated


@router.delete("/users/{id}")
def delete_admin_user(
    id: str = Path(..., description="삭제할 사용자 UUID"),
    user_service: UserService = Depends(deps.get_user_service),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    제어센터 - 관리자 계정 삭제 API (인증 필요, super_admin 권한 필요)
    """
    if current_user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="슈퍼 관리자 권한이 필요합니다.")
        
    success = user_service.delete_user(user_id=id)
    if not success:
        raise HTTPException(status_code=404, detail="계정 삭제 실패 또는 대상을 찾을 수 없습니다.")
    return {"success": True, "message": "계정이 정상적으로 영구 삭제되었습니다."}
