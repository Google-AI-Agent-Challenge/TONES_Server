"""
LayoutRepository — user_layouts 테이블 전담 DB 쿼리 레이어
"""


class LayoutRepository:
    def __init__(self, db_conn=None):
        self.conn = db_conn

    def save(self, user_token: str, pinned_widget) -> bool:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT INTO public.user_layouts (user_token, pinned_widget, updated_at)
                    VALUES (%s, %s, timezone('utc'::text, now()))
                    ON CONFLICT (user_token)
                    DO UPDATE SET pinned_widget = EXCLUDED.pinned_widget, updated_at = timezone('utc'::text, now())
                """, [user_token, pinned_widget])
                self.conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"[LayoutRepository.save] Cloud SQL upsert 실패: {e}")
                try:
                    self.conn.rollback()
                except Exception:
                    pass
                return False
        return True

    def load(self, user_token: str):
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT pinned_widget FROM public.user_layouts WHERE user_token = %s", [user_token])
                row = cursor.fetchone()
                cursor.close()
                if row:
                    return row[0]
            except Exception as e:
                print(f"[LayoutRepository.load] Cloud SQL fetch 실패: {e}")
        return None
