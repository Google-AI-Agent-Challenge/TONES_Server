from typing import Optional
from pydantic import BaseModel, EmailStr


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
