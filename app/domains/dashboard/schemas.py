from typing import Optional
from pydantic import BaseModel


class DocsExportRequest(BaseModel):
    title: str
    period: Optional[int] = 7
    product_id: Optional[str] = None
    report_markdown: Optional[str] = None


class DocsExportResponse(BaseModel):
    success: bool
    message: str
    document_id: Optional[str] = None
    document_url: Optional[str] = None
    report_markdown: Optional[str] = None
