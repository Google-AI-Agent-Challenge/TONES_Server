from typing import List, Optional
from pydantic import BaseModel
from app.domains.products.schemas import ProductSchema


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
    is_priority_review: Optional[bool] = None   # DB 신규 컬럼: 우선 확인 리뷰 여부
    analysis_status: Optional[str] = None       # DB 신규 컬럼: 분석 처리 상태
    products: Optional[ProductSchema] = None

    model_config = {"from_attributes": True}


class ReviewCreate(BaseModel):
    product_id: str
    content: str
    rating: int
    skin_type: Optional[str] = None
    reviewer_type: Optional[str] = None
    source: str = "올리브영"
    review_date: Optional[str] = None
    review_id: Optional[str] = None

    model_config = {"from_attributes": True}
