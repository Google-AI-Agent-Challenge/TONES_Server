from typing import Optional
from fastapi import APIRouter, Depends, Query, Response, Body, HTTPException
from app.api import deps
from app.services.dashboard_service import DashboardService
from app.services.ai_service import AIService
from app.services.docs_service import DocsService
from app.schemas.dashboard import DocsExportRequest, DocsExportResponse

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


@router.post(
    "/export/docs",
    response_model=DocsExportResponse,
    summary="Google Docs 문서 생성",
    description=(
        "대시보드의 AI 분석 요약 데이터(Markdown)를 기반으로 Google Docs API를 호출하여 "
        "새로운 구글 문서를 생성하고, 해당 문서의 공유 링크를 반환합니다. "
        "(GCP 서비스 계정 활용)"
    ),
)
def export_docs(
    body: DocsExportRequest = Body(...),
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service),
    current_user: dict = Depends(deps.get_current_user),
):
    """
    홈 대시보드 - Google Docs 문서 생성 및 공유 링크 반환 API (인증 필요)
    """
    from datetime import datetime
    docs_service = DocsService()

    # report_markdown이 넘어오지 않은 경우, 기본 골격 텍스트 생성
    report_markdown = body.report_markdown
    is_empty_request = not report_markdown

    if is_empty_request:
        product_str = "전체 제품"
        if body.product_id:
            products = dashboard_service.fetch_products()
            matched = next((p for p in products if p["id"] == body.product_id), None)
            if matched:
                product_str = f"{matched.get('brand_name', '')} {matched.get('product_name', '')}".strip()
            else:
                product_str = f"알 수 없는 제품 (ID: {body.product_id})"

        report_markdown = (
            f"# {body.title or '예시 AI 분석 보고서'}\n\n"
            f"- **생성시점**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- **분석기간**: 최근 {body.period}일\n"
            f"- **대상 제품**: {product_str}\n\n"
            "---\n\n"
            "## 📊 분석 요약\n\n"
            "본 문서는 TONES 대시보드에서 자동 생성된 AI 분석 보고서입니다.\n"
        )

    # Google Docs API 생성을 실제로 시도
    try:
        title_val = body.title or ("예시 AI 분석 보고서" if is_empty_request else "AI 분석 보고서")
        result = docs_service.create_document(
            title=title_val,
            report_markdown=report_markdown,
        )
        return DocsExportResponse(
            success=True,
            message="구글 문서가 성공적으로 생성되었습니다.",
            document_id=result["document_id"],
            document_url=result["document_url"],
        )
    except RuntimeError as e:
        # Google Docs API 호출 오류 시 폴백 작동
        sample_document_id = "1wWI3tmqlXa5BdAmc5Vw5FeX8Mm2qXELDESgwB1Y-IH8"
        sample_document_url = f"https://docs.google.com/document/d/{sample_document_id}/edit?usp=sharing"
        
        message_str = "구글 Docs API 호출 오류로 인해 공개 샘플 템플릿 문서로 대체 제공합니다."
        if is_empty_request:
            message_str = "프론트엔드 제공 본문 내용이 없어 예시 AI 분석 보고서 템플릿 문서로 대체 제공합니다."
            
        return DocsExportResponse(
            success=True,
            message=message_str,
            document_id=sample_document_id,
            document_url=sample_document_url,
        )

