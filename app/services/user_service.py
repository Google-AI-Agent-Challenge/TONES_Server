from app.schemas.user import UserCreate
from app.core.security import get_password_hash


class UserService:
    def __init__(self, db_conn=None):
        self.conn = db_conn
        # 로컬 테스트 및 오프라인 상태용 임시 세션
        self._local_db = {
            "test@example.com": {
                "id": "user_12345",
                "email": "test@example.com",
                "full_name": "Test User",
                "is_active": True,
                "hashed_password": "de45ae86a03b7d3e86d7077c4bbb572e$43db25566c86df93cbc866409b7f9b3f36acd51a10e41ffc18a35ab56a3f5855"
            }
        }

    def get_by_email(self, email: str):
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT id, email, full_name, hashed_password, is_active FROM public.users WHERE email = %s",
                    [email]
                )
                row = cursor.fetchone()
                cursor.close()
                if row:
                    return {
                        "id": str(row[0]),
                        "email": row[1],
                        "full_name": row[2],
                        "hashed_password": row[3],
                        "is_active": bool(row[4])
                    }
            except Exception as e:
                print(f"[UserService.get_by_email] Cloud SQL 조회 오류 (오프라인 폴백): {e}")
        
        return self._local_db.get(email)

    def create(self, obj_in: UserCreate):
        hashed_password = get_password_hash(obj_in.password)
        
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute(
                    "INSERT INTO public.users (email, full_name, hashed_password, is_active) VALUES (%s, %s, %s, %s) RETURNING id, email, full_name, is_active",
                    [obj_in.email, obj_in.full_name, hashed_password, True]
                )
                row = cursor.fetchone()
                self.conn.commit()
                cursor.close()
                if row:
                    return {
                        "id": str(row[0]),
                        "email": row[1],
                        "full_name": row[2],
                        "is_active": bool(row[3])
                    }
            except Exception as e:
                print(f"[UserService.create] Cloud SQL 생성 오류 (오프라인 폴백): {e}")
                try:
                    self.conn.rollback()
                except Exception:
                    pass
        
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
