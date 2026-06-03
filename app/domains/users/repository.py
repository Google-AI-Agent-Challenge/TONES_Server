"""
UserRepository — users 테이블 전담 DB 쿼리 레이어
auth / users / admin 도메인이 공통으로 사용한다.
"""
import secrets
import string
from app.domains.users.schemas import UserCreate
from app.core.security import get_password_hash

_LOCAL_DB = {
    "test@example.com": {
        "id": "user_12345",
        "email": "test@example.com",
        "full_name": "Test User",
        "is_active": True,
        "role": "super_admin",
        "last_login_at": None,
        "hashed_password": "de45ae86a03b7d3e86d7077c4bbb572e$43db25566c86df93cbc866409b7f9b3f36acd51a10e41ffc18a35ab56a3f5855"
    }
}


class UserRepository:
    def __init__(self, db_conn=None):
        self.conn = db_conn

    def get_by_email(self, email: str) -> dict | None:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT id, email, full_name, hashed_password, is_active, role::text, last_login_at FROM public.users WHERE email = %s",
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
                        "is_active": bool(row[4]),
                        "role": row[5] if row[5] else "manager",
                        "last_login_at": str(row[6]) if row[6] is not None else None
                    }
            except Exception as e:
                print(f"[UserRepository.get_by_email] Cloud SQL 조회 오류 (오프라인 폴백): {e}")
        return _LOCAL_DB.get(email)

    def create(self, obj_in: UserCreate) -> dict:
        hashed_password = get_password_hash(obj_in.password)
        role_val = obj_in.role or "manager"

        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute(
                    "INSERT INTO public.users (email, full_name, hashed_password, is_active, role) VALUES (%s, %s, %s, %s, %s::role_type) RETURNING id, email, full_name, is_active, role::text, last_login_at",
                    [obj_in.email, obj_in.full_name, hashed_password, True, role_val]
                )
                row = cursor.fetchone()
                self.conn.commit()
                cursor.close()
                if row:
                    return {
                        "id": str(row[0]),
                        "email": row[1],
                        "full_name": row[2],
                        "is_active": bool(row[3]),
                        "role": row[4],
                        "last_login_at": str(row[5]) if row[5] is not None else None
                    }
            except Exception as e:
                print(f"[UserRepository.create] Cloud SQL 생성 오류 (오프라인 폴백): {e}")
                try:
                    self.conn.rollback()
                except Exception:
                    pass

        new_user = {
            "id": f"user_local_{hash(obj_in.email) & 0xffffff}",
            "email": obj_in.email,
            "full_name": obj_in.full_name,
            "is_active": True,
            "role": role_val,
            "last_login_at": None,
            "hashed_password": hashed_password
        }
        _LOCAL_DB[obj_in.email] = new_user
        return new_user

    def update_last_login(self, email: str) -> None:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute(
                    "UPDATE public.users SET last_login_at = timezone('utc'::text, now()) WHERE email = %s",
                    [email]
                )
                self.conn.commit()
                cursor.close()
                return
            except Exception as e:
                print(f"[UserRepository.update_last_login] Cloud SQL 업데이트 오류: {e}")
                try:
                    self.conn.rollback()
                except Exception:
                    pass
        user = _LOCAL_DB.get(email)
        if user:
            from datetime import datetime
            user["last_login_at"] = datetime.now().isoformat()

    def get_all(self) -> list:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT id, email, full_name, is_active, role::text, last_login_at FROM public.users ORDER BY created_at DESC"
                )
                rows = cursor.fetchall()
                cursor.close()
                return [{
                    "id": str(r[0]),
                    "email": r[1],
                    "full_name": r[2],
                    "is_active": bool(r[3]),
                    "role": r[4] if r[4] else "manager",
                    "last_login_at": str(r[5]) if r[5] is not None else None
                } for r in rows]
            except Exception as e:
                print(f"[UserRepository.get_all] Cloud SQL 전체 조회 오류: {e}")
        return list(_LOCAL_DB.values())

    def update_user(self, user_id: str, fields: dict) -> dict | None:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                set_clauses = []
                params = []
                for k, v in fields.items():
                    if k == "role":
                        set_clauses.append("role = %s::role_type")
                    elif k == "password":
                        set_clauses.append("hashed_password = %s")
                        v = get_password_hash(v)
                    else:
                        set_clauses.append(f"{k} = %s")
                    params.append(v)
                params.append(user_id)
                sql = f"UPDATE public.users SET {', '.join(set_clauses)}, updated_at = timezone('utc'::text, now()) WHERE id = %s::uuid RETURNING id, email, full_name, is_active, role::text, last_login_at"
                cursor.execute(sql, params)
                row = cursor.fetchone()
                self.conn.commit()
                cursor.close()
                if row:
                    return {
                        "id": str(row[0]),
                        "email": row[1],
                        "full_name": row[2],
                        "is_active": bool(row[3]),
                        "role": row[4],
                        "last_login_at": str(row[5]) if row[5] is not None else None
                    }
            except Exception as e:
                print(f"[UserRepository.update_user] Cloud SQL 업데이트 오류: {e}")
                try:
                    self.conn.rollback()
                except Exception:
                    pass
        for user in _LOCAL_DB.values():
            if user.get("id") == user_id:
                for k, v in fields.items():
                    if k == "password":
                        user["hashed_password"] = get_password_hash(v)
                    else:
                        user[k] = v
                return user
        return None

    def delete_user(self, user_id: str) -> bool:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM public.users WHERE id = %s::uuid", [user_id])
                self.conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"[UserRepository.delete_user] Cloud SQL 삭제 오류: {e}")
                try:
                    self.conn.rollback()
                except Exception:
                    pass
                return False
        email_to_delete = None
        for email, user in _LOCAL_DB.items():
            if user.get("id") == user_id:
                email_to_delete = email
                break
        if email_to_delete:
            del _LOCAL_DB[email_to_delete]
            return True
        return False

    def find_email_by_name(self, full_name: str) -> str | None:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT email FROM public.users WHERE full_name = %s",
                    [full_name]
                )
                row = cursor.fetchone()
                cursor.close()
                if row:
                    return row[0]
            except Exception as e:
                print(f"[UserRepository.find_email_by_name] Cloud SQL 조회 오류 (오프라인 폴백): {e}")
        for user in _LOCAL_DB.values():
            if user.get("full_name") == full_name:
                return user["email"]
        return None

    def reset_password_temp(self, email: str, full_name: str) -> str | None:
        alphabet = string.ascii_letters + string.digits
        temp_password = ''.join(secrets.choice(alphabet) for _ in range(8))
        hashed_password = get_password_hash(temp_password)

        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT id FROM public.users WHERE email = %s AND full_name = %s",
                    [email, full_name]
                )
                exists = cursor.fetchone()
                if not exists:
                    cursor.close()
                    return None
                cursor.execute(
                    "UPDATE public.users SET hashed_password = %s WHERE email = %s AND full_name = %s",
                    [hashed_password, email, full_name]
                )
                self.conn.commit()
                cursor.close()
                return temp_password
            except Exception as e:
                print(f"[UserRepository.reset_password_temp] Cloud SQL 업데이트 오류 (오프라인 폴백): {e}")
                try:
                    self.conn.rollback()
                except Exception:
                    pass

        user = _LOCAL_DB.get(email)
        if user and user.get("full_name") == full_name:
            user["hashed_password"] = hashed_password
            return temp_password
        return None
