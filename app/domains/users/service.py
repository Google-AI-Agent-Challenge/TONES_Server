from app.domains.users.repository import UserRepository
from app.domains.users.schemas import UserCreate


class UserService:
    """users 도메인 서비스 — UserRepository를 통해 사용자 CRUD 처리"""

    def __init__(self, db_conn=None):
        self.repo = UserRepository(db_conn)

    def get_by_email(self, email: str) -> dict | None:
        return self.repo.get_by_email(email)

    def create(self, obj_in: UserCreate) -> dict:
        return self.repo.create(obj_in)

    def update_last_login(self, email: str) -> None:
        self.repo.update_last_login(email)

    def get_all(self) -> list:
        return self.repo.get_all()

    def update_user(self, user_id: str, fields: dict) -> dict | None:
        return self.repo.update_user(user_id, fields)

    def delete_user(self, user_id: str) -> bool:
        return self.repo.delete_user(user_id)

    def find_email_by_name(self, full_name: str) -> str | None:
        return self.repo.find_email_by_name(full_name)

    def reset_password_temp(self, email: str, full_name: str) -> str | None:
        return self.repo.reset_password_temp(email, full_name)
