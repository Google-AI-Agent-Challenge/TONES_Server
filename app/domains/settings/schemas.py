from typing import Optional
from pydantic import BaseModel


class SettingsUpdatePayload(BaseModel):
    notification_enabled: bool | None = None
    dark_mode: bool | None = None
    analysis_interval_hours: int | None = None
