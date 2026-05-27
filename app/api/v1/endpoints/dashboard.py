from typing import List
from fastapi import APIRouter, Depends, Query
from app.api import deps
from app.schemas.dashboard import ProductSchema, ReviewSchema, ReviewCreate
from app.services.dashboard_service import DashboardService
from app.services.ai_service import AIService

router = APIRouter()

@router.get("/products", response_model=List[ProductSchema])
def get_products(
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service)
):
    """
    전체 제품 목록 조회 API (대시보드 패드 라인업용)
    """
    return dashboard_service.fetch_products()

@router.get("/reviews/latest", response_model=List[ReviewSchema])
def get_latest_reviews(
    limit: int = Query(20, description="조회할 최신 리뷰 수"),
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service)
):
    """
    최신 부정/일반 리뷰 목록 조회 API
    """
    return dashboard_service.fetch_latest_reviews(limit)

@router.get("/reviews/search", response_model=List[ReviewSchema])
def search_reviews_by_keywords(
    keywords: List[str] = Query(None, alias="keywords", description="검색 키워드 목록"),
    limit: int = Query(20, description="조회할 리뷰 수"),
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service)
):
    """
    키워드 기반 리뷰 필터링/검색 API
    """
    # FastAPI Query alias can bind list params like ?keywords=트러블&keywords=자극
    # Or comma separated strings. Handle both.
    final_keywords = []
    if keywords:
        for kw in keywords:
            # Handle comma separation within a query parameter (e.g. ?keywords=트러블,자극)
            if "," in kw:
                final_keywords.extend([k.strip() for k in kw.split(",") if k.strip()])
            else:
                final_keywords.append(kw.strip())
                
    return dashboard_service.fetch_reviews_by_keywords(final_keywords, limit)

@router.get("/reviews/product/{product_id}", response_model=List[ReviewSchema])
def get_reviews_by_product(
    product_id: str,
    limit: int = Query(20, description="조회할 리뷰 수"),
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service)
):
    """
    특정 제품 리뷰 상세 목록 조회 API
    """
    return dashboard_service.fetch_reviews_by_product(product_id, limit)

@router.post("/reviews/bulk", status_code=201)
async def bulk_upload_reviews(
    reviews: List[ReviewCreate],
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service),
    ai_service: AIService = Depends(deps.get_ai_service)
):
    """
    크롤링된 리뷰 대량 업로드 및 AI 파이프라인 처리 API (인증 미적용)
    """
    result = await dashboard_service.process_and_save_reviews(reviews, ai_service)
    return result
