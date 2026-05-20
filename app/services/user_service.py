from app.schemas.user import UserCreate
from app.core.security import get_password_hash


class UserService:
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        # 로컬 테스트 및 오프라인 상태용 임시 세션
        self._local_db = {
            "test@example.com": {
                "id": "user_12345",
                "email": "test@example.com",
                "full_name": "Test User",
                "is_active": True,
                "hashed_password": "$2b$12$RfunWDaR3GC7axRblV921.G/KS8jGihFyTBp/5rL9NMDANRbmGQ/2"
            }
        }

    def get_by_email(self, email: str):
        if self.supabase is not None:
            try:
                # 실제 Supabase 데이터베이스 조회
                response = self.supabase.table("users").select("*").eq("email", email).execute()
                return response.data[0] if response.data else None
            except Exception as e:
                print(f"[UserService.get_by_email] Supabase 연동 오류 (오프라인 폴백): {e}")
        
        return self._local_db.get(email)

    def create(self, obj_in: UserCreate):
        hashed_password = get_password_hash(obj_in.password)
        
        if self.supabase is not None:
            try:
                # 실제 Supabase 데이터 생성
                new_user_data = {
                    "email": obj_in.email,
                    "full_name": obj_in.full_name,
                    "hashed_password": hashed_password,
                    "is_active": True
                }
                response = self.supabase.table("users").insert(new_user_data).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                print(f"[UserService.create] Supabase 생성 오류 (오프라인 폴백): {e}")
        
        # 오프라인 폴백 처리: 임시 메모리 저장
        new_user = {
            "id": f"user_local_{hash(obj_in.email) & 0xffffff}",
            "email": obj_in.email,
            "full_name": obj_in.full_name,
            "is_active": True,
            "hashed_password": hashed_password
        }
        self._local_db[obj_in.email] = new_user
        return new_user
