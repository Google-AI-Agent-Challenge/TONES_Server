from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class FindEmailRequest(BaseModel):
    full_name: str


class FindEmailResponse(BaseModel):
    email: str


class FindPasswordRequest(BaseModel):
    email: EmailStr
    full_name: str


class FindPasswordResponse(BaseModel):
    temp_password: str
