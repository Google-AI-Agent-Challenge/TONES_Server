from app.schemas.user import UserCreate
from app.core.security import get_password_hash


class UserService:
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client

    def get_by_email(self, email: str):
        # 실제 Supabase 연동 코드 예시:
        # response = self.supabase.table("users").select("*").eq("email", email).execute()
        # return response.data[0] if response.data else None
        
        # DB 연결 전 로컬 테스트용 더미 데이터 반환
        if email == "test@example.com":
            return {
                "id": "user_12345",
                "email": "test@example.com",
                "full_name": "Test User",
                "is_active": True,
                # 암호화된 "testpassword" 비밀번호 해시값
                "hashed_password": "$2b$12$RfunWDaR3GC7axRblV921.G/KS8jGihFyTBp/5rL9NMDANRbmGQ/2"
            }
        return None

    def create(self, obj_in: UserCreate):
        hashed_password = get_password_hash(obj_in.password)
        new_user = {
            "id": "user_new",
            "email": obj_in.email,
            "full_name": obj_in.full_name,
            "is_active": True,
            "hashed_password": hashed_password
        }
        return new_user
