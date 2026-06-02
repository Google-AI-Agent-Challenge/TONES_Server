from typing import Any, Optional
from fastapi import APIRouter, Depends, Query
from app.api import deps
from app.schemas.ai_search import (
    SearchRequest,
    SearchResponse,
    GenerateRequest,
    GenerateResponse,
    AIChatRequest,
    AIChatResponse
)
from app.services.ai_service import AIService
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
def search_vectors(
    request: SearchRequest,
    ai_service: AIService = Depends(deps.get_ai_service),
    current_user: dict = Depends(deps.get_current_user)
) -> Any:
    """
    벡터 데이터베이스(pgvector) 시맨틱 검색 API (인증 필요)
    """
    results = ai_service.vector_search(request)
    return SearchResponse(query=request.query, results=results)


@router.post("/generate", response_model=GenerateResponse)
def generate_response(
    request: GenerateRequest,
    ai_service: AIService = Depends(deps.get_ai_service),
    current_user: dict = Depends(deps.get_current_user)
) -> Any:
    """
    컨텍스트 기반 AI 답변 생성 API (인증 필요)
    """
    answer = ai_service.generate_ai_answer(request)
    return GenerateResponse(answer=answer)


@router.post("/chat", response_model=AIChatResponse)
def ai_chat_assistant(
    payload: AIChatRequest,
    ai_service: AIService = Depends(deps.get_ai_service),
    current_user: dict = Depends(deps.get_current_user)
) -> Any:
    """
    리뷰 분석 - AI 어시스턴트 RAG 챗봇 API (인증 필요)
    질문과 매칭되는 실제 고객 리뷰를 pgvector로 자동 검색하고, 그에 기반한 답변을 Gemini로 정교하게 작성하여 제공
    """
    # 1. pgvector 기반 시맨틱 검색 수행 (컨텍스트 리뷰 4개 추출)
    search_filter = {}
    if payload.product_id:
        search_filter["product_id"] = payload.product_id

    search_req = SearchRequest(
        query=payload.message,
        top_k=4,
        filter=search_filter if payload.product_id else None
    )
    search_results = ai_service.vector_search(search_req)

    # 2. 검색된 리뷰 텍스트 조립
    context_items = []
    referenced_reviews = []
    for item in search_results:
        metadata = item.metadata
        text = metadata.get("review_text", "")
        rating = metadata.get("rating", 3)
        sentiment = metadata.get("sentiment", "neutral")
        
        context_items.append(f"[평점: {rating}점 | 감성: {sentiment}] 리뷰 내용: {text}")
        referenced_reviews.append({
            "id": item.id,
            "score": item.score,
            "review_text": text,
            "rating": rating,
            "sentiment": sentiment,
            "ai_summary": metadata.get("ai_summary", "")
        })

    # 3. Gemini RAG 제네레이터 답변 생성
    context_str = "\n".join(context_items)
    gen_req = GenerateRequest(prompt=payload.message, context=context_str)
    answer = ai_service.generate_ai_answer(gen_req)

    return AIChatResponse(
        answer=answer,
        referenced_reviews=referenced_reviews
    )


@router.get("/insight-briefing")
async def get_insight_briefing(
    product_id: Optional[str] = Query(None, description="특정 제품 필터 ID"),
    period: int = Query(7, description="조회 기간 범위 (기본 7일)"),
    dashboard_service: DashboardService = Depends(deps.get_dashboard_service),
    ai_service: AIService = Depends(deps.get_ai_service),
    current_user: dict = Depends(deps.get_current_user)
) -> Any:
    """
    리뷰 분석 - AI Insight Briefing 및 핵심 VOC 요약 지표 제공 API (인증 필요)
    """
    stats = await dashboard_service.get_dashboard_statistics(product_id, period, ai_service)
    return {
        "insight_briefing": stats.get("ai_briefing", ""),
        "total_reviews": stats.get("total_reviews", 0),
        "average_rating": stats.get("average_rating", 0.0),
        "attribute_scores": stats.get("attribute_scores", {})
    }
