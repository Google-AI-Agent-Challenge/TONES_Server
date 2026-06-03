"""
SettingsRepository — settings 테이블 전담 DB 쿼리 레이어
"""


_DEFAULTS = {"notification_enabled": True, "dark_mode": False, "analysis_interval_hours": 24}


class SettingsRepository:
    def __init__(self, db_conn=None):
        self.conn = db_conn

    def get(self) -> dict:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT notification_enabled, dark_mode, analysis_interval_hours FROM public.settings LIMIT 1")
                row = cursor.fetchone()
                cursor.close()
                if row:
                    return {
                        "notification_enabled": bool(row[0]),
                        "dark_mode": bool(row[1]),
                        "analysis_interval_hours": int(row[2])
                    }
            except Exception as e:
                print(f"[SettingsRepository.get] DB 조회 실패, Mock 폴백: {e}")
        return dict(_DEFAULTS)

    def update(self, fields: dict) -> bool:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                set_clauses = [f"{k} = %s" for k in fields]
                params = list(fields.values())
                sql = f"UPDATE public.settings SET {', '.join(set_clauses)}, updated_at = timezone('utc'::text, now()) WHERE id = 1"
                cursor.execute(sql, params)
                self.conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"[SettingsRepository.update] DB 업데이트 실패: {e}")
                try:
                    self.conn.rollback()
                except Exception:
                    pass
                raise e
        return True

    def reset(self) -> bool:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute(
                    "UPDATE public.settings SET notification_enabled = TRUE, dark_mode = FALSE, analysis_interval_hours = 24, updated_at = timezone('utc'::text, now()) WHERE id = 1"
                )
                self.conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"[SettingsRepository.reset] DB 초기화 실패: {e}")
                try:
                    self.conn.rollback()
                except Exception:
                    pass
                raise e
        return True
