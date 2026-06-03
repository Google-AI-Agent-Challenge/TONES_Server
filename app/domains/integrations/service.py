from app.domains.integrations.repository import IntegrationsRepository


class IntegrationsService:
    def __init__(self, db_conn=None):
        self.repo = IntegrationsRepository(db_conn)

    def get_status(self) -> list:
        return self.repo.get_status()
