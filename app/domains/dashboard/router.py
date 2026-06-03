from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Response, Body

from app.core.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.domains.dashboard.service import DashboardService
from app.domains.ai_search.service import AIService
from app.domains.dashboard.schemas import DocsExportRequest, DocsExportResponse

router = APIRouter()


def get_dashboard_service(db_conn=Depends(get_db_connection)) -> DashboardService:
    return DashboardService(db_conn)


def get_ai_service(db_conn=Depends(get_db_connection)) -> AIService:
    return AIService(db_conn)


@router.get("/summary")
def get_dashboard_summary(
    response: Response,
    product_id: Optional[str] = Query(None, description="특정 제품 필터 ID"),
    period: int = Query(7, description="조회할 기간 범위 (일 수, 기본 7일)"),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    current_user: dict = Depends(get_current_user)
):
    """홈 대시보드 - 전체 리뷰, 평균 별점, 부정 리뷰 비율 및 WoW 변동량, 우선 확인 요약 반환 API (인증 필요)"""
    response.headers["Cache-Control"] = "private, max-age=300, stale-while-revalidate=60"
    return dashboard_service.fetch_dashboard_summary(product_id, period)


@router.get("/trending-keywords")
def get_trending_keywords(
    response: Response,
    product_id: Optional[str] = Query(None),
    period: int = Query(7),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    current_user: dict = Depends(get_current_user)
):
    """홈 대시보드 - Top 5 급상승 및 최다 언급 키워드 집계 API (인증 필요)"""
    response.headers["Cache-Control"] = "private, max-age=300, stale-while-revalidate=60"
    return dashboard_service.fetch_trending_keywords(product_id, period)


@router.get("/negative-trend")
def get_negative_trend(
    response: Response,
    product_id: Optional[str] = Query(None),
    period: int = Query(7),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    current_user: dict = Depends(get_current_user)
):
    """홈 대시보드 - 부정 리뷰 시계열 분포 집계 API (인증 필요)"""
    response.headers["Cache-Control"] = "private, max-age=300, stale-while-revalidate=60"
    return dashboard_service.fetch_negative_trend(product_id, period)


@router.get("/insights")
def get_insights(
    response: Response,
    product_id: Optional[str] = Query(None),
    period: int = Query(7),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    current_user: dict = Depends(get_current_user)
):
    """홈 대시보드 - 주요 분석 리스트 (성분/제형/용기 속성 점수 변동치 감지) API (인증 필요)"""
    response.headers["Cache-Control"] = "private, max-age=300, stale-while-revalidate=60"
    return dashboard_service.fetch_insights(product_id, period)


@router.get("/ai-briefing")
async def get_ai_briefing(
    response: Response,
    product_id: Optional[str] = Query(None),
    period: int = Query(7),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    ai_service: AIService = Depends(get_ai_service),
    current_user: dict = Depends(get_current_user)
):
    """홈 대시보드 - AI 트렌드 및 핵심 긴급 시그널 브리핑 API (인증 필요)"""
    response.headers["Cache-Control"] = "private, max-age=1800, stale-while-revalidate=120"
    stats = await dashboard_service.get_dashboard_statistics(product_id, period, ai_service)
    return {"ai_briefing": stats.get("ai_briefing", "")}


@router.post("/report")
def create_report(
    product_id: Optional[str] = Query(None),
    period: int = Query(7),
    report_type: str = Query("general"),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    current_user: dict = Depends(get_current_user)
):
    """홈 대시보드 - 정기 분석 및 성과 대시보드 요약 보고서 파일 생성 API (인증 필요)"""
    return dashboard_service.create_dashboard_report(product_id, period, report_type)


@router.post("/export/docs", response_model=DocsExportResponse,
             summary="Google Docs 문서 생성")
async def export_docs(
    body: DocsExportRequest = Body(...),
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    ai_service: AIService = Depends(get_ai_service),
    current_user: dict = Depends(get_current_user),
):
    """홈 대시보드 - 리포트 마크다운 데이터 반환 API (인증 필요)"""
    report_markdown = body.report_markdown
    is_empty_request = not report_markdown

    if is_empty_request:
        if body.product_id and body.product_id.strip():
            product_id = body.product_id if body.product_id != "all" else None
            period = body.period or 7
            product_str = "전체 제품"
            if product_id:
                products = dashboard_service.fetch_products()
                matched = next((p for p in products if p["id"] == product_id), None)
                if matched:
                    product_str = f"{matched.get('brand_name', '')} {matched.get('product_name', '')}".strip()
                else:
                    product_str = f"알 수 없는 제품 (ID: {product_id})"
            summary = dashboard_service.fetch_dashboard_summary(product_id, period)
            insights = dashboard_service.fetch_insights(product_id, period)
            keywords = dashboard_service.fetch_trending_keywords(product_id, period)
            briefing_data = await dashboard_service.get_dashboard_statistics(product_id, period, ai_service)
            ai_briefing = briefing_data.get("ai_briefing", "실시간 트렌드 분석 정보가 존재하지 않습니다.")
            keywords_table = ""
            for idx, kw in enumerate(keywords[:5], 1):
                keywords_table += f"| {idx} | {kw.get('keyword', '')} | {kw.get('count', 0)}회 |\n"
            if not keywords_table:
                keywords_table = "| - | 언급된 키워드 없음 | - |\n"
            report_markdown = (
                f"# {body.title or f'{product_str} VOC AI 분석 보고서'}\n\n"
                f"- **생성시점**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"- **분석기간**: 최근 {period}일\n"
                f"- **대상 제품**: {product_str}\n\n---\n\n"
                f"## 📊 분석 요약\n\n"
                f"- **총 수집 리뷰**: {summary.get('total_reviews', 0)}건 (전기 대비 {summary.get('total_reviews_diff', 0):+d}건)\n"
                f"- **평균 만족 별점**: {summary.get('average_rating', 0.0)}점 (전기 대비 {summary.get('average_rating_diff', 0.0):+.2f}점)\n"
                f"- **부정 리뷰 비율**: {summary.get('negative_reviews_rate', 0.0)}% (전기 대비 {summary.get('negative_reviews_rate_diff', 0.0):+.1f}%p)\n\n"
                f"### 💡 실시간 AI 분석 브리핑\n{ai_briefing}\n\n"
                f"## 📝 기타 내용\n\n"
                f"### 🔑 언급 빈도 최다 핵심 키워드\n"
                f"| 순위 | 키워드 | 언급 횟수 |\n| :---: | :--- | :---: |\n{keywords_table}\n"
                f"### 🔍 3대 품질 속성 분석 (성분/제형/용기)\n"
                f"- **성분 및 피부 진정** (만족도: {insights.get('ingredients', {}).get('score', 0.0)}%)\n"
                f"  - *인사이트*: {insights.get('ingredients', {}).get('insight_text', '정보 없음')}\n"
                f"- **제형 및 발림성** (만족도: {insights.get('formulation', {}).get('score', 0.0)}%)\n"
                f"  - *인사이트*: {insights.get('formulation', {}).get('insight_text', '정보 없음')}\n"
                f"- **용기 및 편의성** (만족도: {insights.get('container', {}).get('score', 0.0)}%)\n"
                f"  - *인사이트*: {insights.get('container', {}).get('insight_text', '정보 없음')}\n"
            )
        else:
            report_markdown = (
                f"# {body.title or '[제목] 예시 AI 분석 보고서'}\n\n"
                f"- **생성시점**: [생성시점]\n- **분석기간**: [분석기간]\n- **대상 제품**: [대상 제품]\n\n---\n\n"
                f"## 📊 분석 요약\n\n[이곳에 분석 요약 내용을 작성하십시오.]\n\n"
                f"## 📝 기타 내용\n\n- **주요 속성 만족도**: [성분/제형/용기 분석 데이터 없음]\n"
                f"- **핵심 키워드**: [급상승 키워드 분석 데이터 없음]\n"
            )

    return DocsExportResponse(
        success=True,
        message="리포트 마크다운이 성공적으로 생성되었습니다.",
        document_id=None,
        document_url=None,
        report_markdown=report_markdown,
    )
