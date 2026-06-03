from app.domains.users.repository import UserRepository
from app.domains.users.schemas import UserCreate
from app.core.security import get_password_hash, verify_password


class AuthService:
    def __init__(self, db_conn=None):
        self.repo = UserRepository(db_conn)

    def authenticate(self, email: str, password: str) -> dict | None:
        """이메일 + 비밀번호 검증 후 사용자 dict 반환. 실패 시 None."""
        user = self.repo.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user["hashed_password"]):
            return None
        return user

    def register(self, user_in: UserCreate) -> dict:
        """신규 사용자 등록"""
        return self.repo.create(user_in)

    def update_last_login(self, email: str) -> None:
        self.repo.update_last_login(email)

    def find_email_by_name(self, full_name: str) -> str | None:
        return self.repo.find_email_by_name(full_name)

    def reset_password_temp(self, email: str, full_name: str) -> str | None:
        return self.repo.reset_password_temp(email, full_name)

    def get_by_email(self, email: str) -> dict | None:
        return self.repo.get_by_email(email)
