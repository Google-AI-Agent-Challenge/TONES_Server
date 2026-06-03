from typing import Optional
from pydantic import BaseModel


class ProductSchema(BaseModel):
    id: str
    brand_name: str
    product_name: str
    category: str
    target_skin: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class ProductCreatePayload(BaseModel):
    brand_name: str
    product_name: str
    description: Optional[str] = None
    price: Optional[float] = None
    category: str = "pad"
    target_skin: str = "민감성"


class ProductUpdatePayload(BaseModel):
    product_name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    is_analysis_active: Optional[bool] = None
