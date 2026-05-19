from fastapi.testclient import TestClient
from app.core.config import settings


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
    assert "Pinecone is a vector database" in gen_data["answer"]
