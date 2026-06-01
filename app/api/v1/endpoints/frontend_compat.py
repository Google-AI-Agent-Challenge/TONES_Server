from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from app.api import deps
from app.schemas.dashboard import ProductSchema, ReviewSchema
from app.services.dashboard_service import DashboardService

router = APIRouter()

@router.get("/products", response_model=List[ProductSchema])
def get_products(
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service)
):
    """
    프론트엔드 호환용 전체 제품 목록 조회 API
    """
    return dashboard_service.fetch_products()

@router.get("/reviews", response_model=List[ReviewSchema])
def get_reviews(
    limit: int = Query(20, description="조회할 리뷰 수"),
    product_id: Optional[str] = Query(None, description="특정 상품 필터 ID"),
    keywords: Optional[str] = Query(None, description="쉼표 구분 키워드"),
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service)
):
    """
    프론트엔드 호환용 리뷰 조회 API (조건에 따라 분기 처리)
    """
    if product_id:
        return dashboard_service.fetch_reviews_by_product(product_id, limit)
    elif keywords:
        final_keywords = [k.strip() for k in keywords.split(",") if k.strip()]
        return dashboard_service.fetch_reviews_by_keywords(final_keywords, limit)
    else:
        return dashboard_service.fetch_latest_reviews(limit)

@router.get("/reviews/batch", response_model=List[ReviewSchema])
def get_reviews_batch(
    ids: str = Query(..., description="쉼표 구분 ID 목록"),
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service)
):
    """
    프론트엔드 호환용 ID 기반 리뷰 조회 API
    """
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    return dashboard_service.fetch_reviews_by_ids(id_list)
