from typing import Any
from fastapi import APIRouter, Depends
from app.api import deps
from app.schemas.ai_search import (
    SearchRequest,
    SearchResponse,
    GenerateRequest,
    GenerateResponse,
)
from app.services.ai_service import AIService

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
def search_vectors(
    request: SearchRequest,
    ai_service: AIService = Depends(deps.get_ai_service),
    current_user: dict = Depends(deps.get_current_user)
) -> Any:
    """
    벡터 데이터베이스(Pinecone) 시맨틱 검색 API (인증 필요)
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
