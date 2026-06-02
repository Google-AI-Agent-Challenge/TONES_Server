from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
import io
import csv
from app.api import deps
from app.schemas.dashboard import ReviewSchema, ReviewCreate
from app.services.dashboard_service import DashboardService
from app.services.ai_service import AIService

router = APIRouter()


@router.get("", response_model=List[ReviewSchema])
def get_reviews(
    product: Optional[str] = Query(None, description="특정 제품 필터 ID"),
    period: Optional[int] = Query(None, description="조회 기간 범위 (일 수)"),
    sentiment: Optional[str] = Query(None, description="감성 구분 (positive, neutral, negative)"),
    q: Optional[str] = Query(None, description="검색어"),
    page: int = Query(1, description="페이지 번호"),
    limit: int = Query(20, description="한 페이지당 리뷰 수"),
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    리뷰 분석 - 다중 조건 필터 및 검색이 통합된 리뷰 목록 조회 API (인증 필요)
    """
    return dashboard_service.fetch_reviews_advanced(
        product_id=product,
        period_days=period,
        sentiment=sentiment,
        q=q,
        page=page,
        limit=limit
    )


@router.get("/attribute-scores")
def get_attribute_scores(
    product: Optional[str] = Query(None, description="특정 제품 필터 ID"),
    period: Optional[int] = Query(None, description="조회 기간 범위 (일 수)"),
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    리뷰 분석 - 성분·수분·용기 3대 핵심 품질 속성의 분석 기간 내 평균 점수 반환 API (인증 필요)
    """
    return dashboard_service.fetch_reviews_attribute_scores(product_id=product, period_days=period)


@router.post("/export")
def export_reviews(
    product: Optional[str] = Query(None, description="특정 제품 필터 ID"),
    period: Optional[int] = Query(None, description="조회 기간 범위 (일 수)"),
    sentiment: Optional[str] = Query(None, description="감성 구분"),
    q: Optional[str] = Query(None, description="검색어"),
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    리뷰 분석 - 현재 필터링된 모든 리뷰 데이터를 CSV 파일 스트림으로 다운로드 내보내기 API (인증 필요)
    """
    reviews = dashboard_service.fetch_reviews_advanced(
        product_id=product,
        period_days=period,
        sentiment=sentiment,
        q=q,
        page=1,
        limit=10000  # 추출 시 대량 다운로드 보장
    )
    
    output = io.StringIO()
    writer = csv.writer(output, csv.excel)
    
    # Header 작성
    writer.writerow([
        "리뷰ID", "제품ID", "리뷰출처", "리뷰어타입", "평점", 
        "리뷰날짜", "감성구분", "감성점수", "AI요약", 
        "성분점수", "제형점수", "용기점수", "원문텍스트"
    ])
    
    for r in reviews:
        writer.writerow([
            r.get("id"),
            r.get("product_id"),
            r.get("source"),
            r.get("reviewer_type"),
            r.get("rating"),
            r.get("review_date"),
            r.get("sentiment"),
            r.get("sentiment_score"),
            r.get("ai_summary", ""),
            r.get("score_ingredients", 0.5),
            r.get("score_formulation", 0.5),
            r.get("score_container", 0.5),
            r.get("review_text", "").replace("\n", " ")
        ])
    
    output.seek(0)
    
    # 윈도우 OS 인코딩 호환을 위해 utf-8-sig(BOM 포함) 바이트 변환 적용
    bytes_data = output.getvalue().encode("utf-8-sig")
    
    return StreamingResponse(
        io.BytesIO(bytes_data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tones_reviews_export.csv"}
    )


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_upload_reviews(
    reviews: List[ReviewCreate],
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service),
    ai_service: AIService = Depends(deps.get_ai_service)
):
    """
    리뷰 데이터 대량 적재 - 크롤링된 리뷰 대량 업로드 및 AI 파이프라인 처리 API (인증 미적용)
    """
    result = await dashboard_service.process_and_save_reviews(reviews, ai_service)
    return result
