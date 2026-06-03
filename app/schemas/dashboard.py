from typing import List, Optional
from pydantic import BaseModel

class ProductSchema(BaseModel):
    id: str
    brand_name: str
    product_name: str
    category: str
    target_skin: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

class ReviewSchema(BaseModel):
    id: str
    product_id: str
    source: str
    reviewer_type: Optional[str] = None
    review_text: str
    rating: int
    review_date: str
    sentiment: str
    sentiment_score: Optional[float] = None
    keywords: List[str] = []
    issue_type: Optional[str] = None
    ai_summary: Optional[str] = None
    created_at: Optional[str] = None
    review_id: Optional[str] = None
    products: Optional[ProductSchema] = None

    model_config = {
        "from_attributes": True
    }

class ReviewCreate(BaseModel):
    product_id: str
    content: str
    rating: int
    skin_type: Optional[str] = None
    reviewer_type: Optional[str] = None
    source: str = "올리브영"
    review_date: Optional[str] = None
    review_id: Optional[str] = None

    model_config = {
        "from_attributes": True
    }

class LayoutSaveRequest(BaseModel):
    token: str
    pinned_widget: Optional[str] = None

class LayoutResponse(BaseModel):
    pinned_widget: Optional[str] = None

class ReviewsByIdsRequest(BaseModel):
    ids: List[str]


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

