"""
IntegrationsRepository — integrations 테이블 전담 DB 쿼리 레이어
"""

_MOCK_STATUS = [
    {"platform_name": "naver", "status": "connected", "sync_rate": 98.0, "error_message": None, "last_synced_at": "2026-06-02T15:20:16Z"},
    {"platform_name": "olive_young", "status": "error", "sync_rate": 40.0, "error_message": "408 Request Timeout", "last_synced_at": "2026-06-02T10:15:30Z"}
]


class IntegrationsRepository:
    def __init__(self, db_conn=None):
        self.conn = db_conn

    def get_status(self) -> list:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT platform_name, status, sync_rate, error_message, last_synced_at::text FROM public.integrations"
                )
                rows = cursor.fetchall()
                cursor.close()
                if rows:
                    return [{
                        "platform_name": r[0],
                        "status": r[1],
                        "sync_rate": float(r[2]),
                        "error_message": r[3],
                        "last_synced_at": r[4]
                    } for r in rows]
            except Exception as e:
                print(f"[IntegrationsRepository.get_status] DB 조회 실패, Mock 폴백: {e}")
        return list(_MOCK_STATUS)
