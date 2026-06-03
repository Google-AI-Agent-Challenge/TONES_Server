from app.domains.layout.repository import LayoutRepository


class LayoutService:
    def __init__(self, db_conn=None):
        self.repo = LayoutRepository(db_conn)

    def save_layout(self, user_token: str, pinned_widget) -> bool:
        return self.repo.save(user_token, pinned_widget)

    def load_layout(self, user_token: str):
        return self.repo.load(user_token)
