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
    current_user: dict = Depends(deps.get_current_user),
):
    """
    홈 대시보드 - Google Docs 문서 생성 및 공유 링크 반환 API (인증 필요)
    """
    docs_service = DocsService()

    # report_markdown이 없으면 제목과 기본 메타데이터로 본문 자동 구성
    markdown_content = body.report_markdown
    if not markdown_content:
        from datetime import datetime
        product_str = body.product_id if body.product_id and body.product_id != "all" else "전체 제품"
        markdown_content = (
            f"# {body.title}\n\n"
            f"- **생성시점**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- **분석기간**: 최근 {body.period}일\n"
            f"- **대상 제품**: {product_str}\n\n"
            "---\n\n"
            "## 📊 분석 요약\n\n"
            "본 문서는 TONES 대시보드에서 자동 생성된 AI 분석 보고서입니다.\n"
        )

    try:
        result = docs_service.create_document(
            title=body.title,
            report_markdown=markdown_content,
        )
        return DocsExportResponse(
            success=True,
            message="구글 문서가 성공적으로 생성되었습니다.",
            document_id=result["document_id"],
            document_url=result["document_url"],
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Google Docs API 호출 중 오류가 발생했습니다. GCP 서비스 계정 권한을 확인해주세요.",
        )
