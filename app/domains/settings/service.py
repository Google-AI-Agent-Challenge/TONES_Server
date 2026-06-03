from app.domains.settings.repository import SettingsRepository


class SettingsService:
    def __init__(self, db_conn=None):
        self.repo = SettingsRepository(db_conn)

    def get_settings(self) -> dict:
        return self.repo.get()

    def update_settings(self, fields: dict) -> bool:
        return self.repo.update(fields)

    def reset_settings(self) -> bool:
        return self.repo.reset()
