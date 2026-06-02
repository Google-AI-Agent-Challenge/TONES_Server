from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from app.api import deps
from app.services.dashboard_service import DashboardService
from app.services.ai_service import AIService

router = APIRouter()


@router.get("/summary")
def get_dashboard_summary(
    response: Response,
    product_id: Optional[str] = Query(None, description="특정 제품 필터 ID (미지정 시 전체 상품 합산)"),
    period: int = Query(7, description="조회할 기간 범위 (일 수, 기본 7일)"),
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    홈 대시보드 - 전체 리뷰, 평균 별점, 부정 리뷰 비율 및 WoW 변동량, 우선 확인 요약 반환 API (인증 필요)
    """
    response.headers["Cache-Control"] = "private, max-age=300, stale-while-revalidate=60"
    return dashboard_service.fetch_dashboard_summary(product_id, period)


@router.get("/trending-keywords")
def get_trending_keywords(
    response: Response,
    product_id: Optional[str] = Query(None, description="특정 제품 필터 ID"),
    period: int = Query(7, description="조회할 기간 범위"),
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    홈 대시보드 - Top 5 급상승 및 최다 언급 키워드 집계 API (인증 필요)
    """
    response.headers["Cache-Control"] = "private, max-age=300, stale-while-revalidate=60"
    return dashboard_service.fetch_trending_keywords(product_id, period)


@router.get("/negative-trend")
def get_negative_trend(
    response: Response,
    product_id: Optional[str] = Query(None, description="특정 제품 필터 ID"),
    period: int = Query(7, description="조회할 기간 범위"),
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    홈 대시보드 - 부정 리뷰 시계열 분포 집계 API (인증 필요)
    """
    response.headers["Cache-Control"] = "private, max-age=300, stale-while-revalidate=60"
    return dashboard_service.fetch_negative_trend(product_id, period)


@router.get("/insights")
def get_insights(
    response: Response,
    product_id: Optional[str] = Query(None, description="특정 제품 필터 ID"),
    period: int = Query(7, description="조회할 기간 범위"),
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    홈 대시보드 - 주요 분석 리스트 (성분/제형/용기 속성 점수 변동치 감지) API (인증 필요)
    """
    response.headers["Cache-Control"] = "private, max-age=300, stale-while-revalidate=60"
    return dashboard_service.fetch_insights(product_id, period)


@router.get("/ai-briefing")
async def get_ai_briefing(
    response: Response,
    product_id: Optional[str] = Query(None, description="특정 제품 필터 ID"),
    period: int = Query(7, description="조회할 기간 범위"),
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service),
    ai_service: AIService = Depends(deps.get_ai_service),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    홈 대시보드 - AI 트렌드 및 핵심 긴급 시그널 브리핑 API (인증 필요)
    """
    response.headers["Cache-Control"] = "private, max-age=1800, stale-while-revalidate=120"
    stats = await dashboard_service.get_dashboard_statistics(product_id, period, ai_service)
    return {"ai_briefing": stats.get("ai_briefing", "")}


@router.post("/report")
def create_report(
    product_id: Optional[str] = Query(None, description="특정 제품 필터 ID"),
    period: int = Query(7, description="조회할 기간 범위"),
    report_type: str = Query("general", description="리포트 타입 (general 등)"),
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service),
    current_user: dict = Depends(deps.get_current_user)
):
    """
    홈 대시보드 - 정기 분석 및 성과 대시보드 요약 보고서 파일 생성 API (인증 필요)
    """
    return dashboard_service.create_dashboard_report(product_id, period, report_type)

