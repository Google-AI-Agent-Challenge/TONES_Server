import time
from typing import Any


class TTLCache:
    """요청 간 공유되는 인메모리 TTL 캐시. 프로세스 수명 동안 유지된다."""

    def __init__(self) -> None:
        self._store: dict[tuple, tuple[float, Any]] = {}

    def get(self, key: tuple, ttl: int) -> tuple[bool, Any]:
        entry = self._store.get(key)
        if entry is not None:
            timestamp, data = entry
            if time.time() - timestamp < ttl:
                return True, data
            del self._store[key]
        return False, None

    def set(self, key: tuple, value: Any) -> None:
        self._store[key] = (time.time(), value)

    def invalidate(self, key: tuple) -> None:
        self._store.pop(key, None)

    def invalidate_all(self) -> None:
        self._store.clear()


# 모듈 레벨 싱글톤 — DashboardService 인스턴스가 매 요청마다 재생성돼도 캐시는 유지됨
dashboard_cache = TTLCache()
