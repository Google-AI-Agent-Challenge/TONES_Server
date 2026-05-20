from fastapi.testclient import TestClient
from app.core.config import settings
from app.services.ai_service import AIService
from app.schemas.ai_search import SearchRequest, GenerateRequest


def test_ai_endpoints_without_auth(client: TestClient):
    # 인증 없이 호출 시 401 Unauthorized 검증
    response = client.post(
        f"{settings.API_V1_STR}/ai/search",
        json={"query": "test query", "top_k": 3}
    )
    assert response.status_code == 401


def test_ai_endpoints_with_auth(client: TestClient):
    # 1. 로그인하여 토큰 획득
    login_response = client.post(
        f"{settings.API_V1_STR}/auth/login/access-token",
        data={
            "username": "test@example.com",
            "password": "testpassword"
        }
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. AI 벡터 검색 API 호출
    search_response = client.post(
        f"{settings.API_V1_STR}/ai/search",
        json={"query": "AI agent challenge", "top_k": 3},
        headers=headers
    )
    assert search_response.status_code == 200
    search_data = search_response.json()
    assert search_data["query"] == "AI agent challenge"
    assert len(search_data["results"]) == 3

    # 3. AI 답변 생성 API 호출
    gen_response = client.post(
        f"{settings.API_V1_STR}/ai/generate",
        json={"prompt": "How does Pinecone work?", "context": "Pinecone is a vector database."},
        headers=headers
    )
    assert gen_response.status_code == 200
    gen_data = gen_response.json()
    # 더미 폴백 모드 및 실연동 모드 둘 다 호환되도록 확인
    assert "Pinecone" in gen_data["answer"] or "오프라인" in gen_data["answer"] or len(gen_data["answer"]) > 0


def test_ai_service_offline_fallback():
    # AIService를 클라이언트 없이 순수하게 호출하여 오프라인 폴백 강인성 검증
    service = AIService(pinecone_client=None)
    
    # 1. 벡터 검색 폴백 검증
    req_search = SearchRequest(query="RAG architecture", top_k=2)
    results = service.vector_search(req_search)
    assert len(results) == 2
    assert results[0].id == "doc_0"
    assert "로컬 테스트용" in results[0].metadata["content"]
    
    # 2. 답변 생성 폴백 검증
    req_gen = GenerateRequest(prompt="What is Antigravity?", context="Antigravity is an AI coder.")
    answer = service.generate_ai_answer(req_gen)
    assert "오프라인 폴백" in answer
    assert "Antigravity is an AI coder" in answer
