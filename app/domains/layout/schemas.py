from typing import Optional
from pydantic import BaseModel


class LayoutSaveRequest(BaseModel):
    token: str
    pinned_widget: Optional[str] = None


class LayoutResponse(BaseModel):
    pinned_widget: Optional[str] = None
