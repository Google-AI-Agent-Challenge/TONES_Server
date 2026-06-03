"""
AdminService — users 도메인 Repository를 통해 관리자 계정 관리
"""
from app.domains.users.repository import UserRepository
from app.domains.users.schemas import UserCreate


class AdminService:
    def __init__(self, db_conn=None):
        self.repo = UserRepository(db_conn)

    def get_all_users(self) -> list:
        return self.repo.get_all()

    def create_user(self, email: str, full_name: str, password: str, role: str = "manager") -> dict:
        user_in = UserCreate(email=email, full_name=full_name, password=password, role=role)
        return self.repo.create(user_in)

    def get_by_email(self, email: str) -> dict | None:
        return self.repo.get_by_email(email)

    def update_user(self, user_id: str, fields: dict) -> dict | None:
        return self.repo.update_user(user_id, fields)

    def delete_user(self, user_id: str) -> bool:
        return self.repo.delete_user(user_id)
