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
