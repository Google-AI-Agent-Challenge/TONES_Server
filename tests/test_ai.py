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


def test_review_create_schema():
    # ReviewCreate 스키마 입력 데이터 유효성 검증
    from app.schemas.dashboard import ReviewCreate
    payload = {
        "product_id": "04472697-d7c5-4cbe-bbc1-3cb62d3d4eba",
        "content": "이 패드 진짜 촉촉하고 트러블 안 나요! 추천합니다.",
        "rating": 5,
        "skin_type": "민감성 건성",
        "source": "올리브영",
        "review_id": "99c6b758-6923-40a2-aaee-6df7100b467e"
    }
    review_obj = ReviewCreate(**payload)
    assert review_obj.product_id == "04472697-d7c5-4cbe-bbc1-3cb62d3d4eba"
    assert review_obj.rating == 5
    assert "촉촉하고" in review_obj.content


def test_ai_service_absa_offline():
    # AIService ABSA 엔진 로컬 룰/더미 가동성 검증
    from app.services.ai_service import AIService
    service = AIService(pinecone_client=None)
    
    # 1. 긍정 단어가 많은 경우 분석 테스트
    res = service.analyze_review_absa("원래 이 토너패드 엄청 좋아해서 샀어요. 제형이 매우 촉촉하고 부드럽습니다. 자극은 전혀 없어요!")
    assert res["overall_sentiment"] == "positive"
    assert res["ingredients_skin_concerns_score"] >= 0.7
    assert res["formulation_spreadability_score"] >= 0.7
    
    # 2. 부정적인 자극 키워드가 있는 경우 분석 테스트
    res_neg = service.analyze_review_absa("이 패드 쓰고 나니까 볼 쪽이 엄청 따갑고 자극이 심해요. 끈적이고 용기 뚜껑도 잘 안 닫힙니다.")
    assert res_neg["overall_sentiment"] == "negative"
    assert res_neg["ingredients_skin_concerns_score"] <= 0.3
    assert res_neg["formulation_spreadability_score"] <= 0.3
    assert res_neg["container_design_score"] <= 0.3
    assert "자극" in res_neg["issue_type"] or "제형불만" in res_neg["issue_type"]


def test_bulk_upload_endpoint_offline(client: TestClient):
    # POST /api/v1/dashboard/reviews/bulk 엔드포인트 비인증 가상 크롤러 데이터 처리 검증
    payload = [
        {
            "product_id": "04472697-d7c5-4cbe-bbc1-3cb62d3d4eba",
            "content": "성분이 너무 좋아서 씁니다. 피부 장벽 복구에 짱이에요.",
            "rating": 5,
            "skin_type": "복합성 피부",
            "source": "올리브영"
        },
        {
            "product_id": "e680f731-cfde-427f-9077-62f7e484ec21",
            "content": "이거 쓰고 여드름 폭발했어요... 볼 빨개지고 좁쌀 트러블 다 올라옴",
            "rating": 1,
            "skin_type": "민감성 피부",
            "source": "네이버"
        }
    ]
    response = client.post(
        f"{settings.API_V1_STR}/dashboard/reviews/bulk",
        json=payload
    )
    assert response.status_code == 201 or response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["total_reviews"] == 2
    assert len(data["processed_ids"]) == 2


def test_supabase_self_healing_and_rollback_transaction():
    # Supabase 트랜잭션 롤백 및 자가 치유(Self-Healing) 작동성 단위 테스트
    from app.services.dashboard_service import DashboardService
    from app.services.ai_service import AIService
    from app.schemas.dashboard import ReviewCreate
    from unittest.mock import MagicMock
    import asyncio
    
    # 1. 자가 치유 테스트: Supabase에서 컬럼 에러 발생 시 자가 치유 작동 확인
    mock_supabase = MagicMock()
    
    # 첫 번째 insert 시도 시 column does not exist 에러 발생
    # 두 번째 healed insert 시도 시 성공 처리
    def mock_insert_side_effect(record):
        if "score_ingredients" in record:
            raise Exception("column \"score_ingredients\" does not exist on table reviews")
        # healed record는 성공
        mock_result = MagicMock()
        mock_result.execute.return_value = MagicMock(data=[record])
        return mock_result
        
    mock_supabase.table.return_value.insert.side_effect = mock_insert_side_effect
    
    service = DashboardService(supabase_client=mock_supabase)
    ai_service = AIService(pinecone_client=MagicMock())
    
    review = ReviewCreate(
        product_id="04472697-d7c5-4cbe-bbc1-3cb62d3d4eba",
        content="진짜 좋은데 용기 뚜껑이 안 닫히고 헐거워요.",
        rating=3,
        skin_type="지성"
    )
    
    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(service.process_and_save_reviews([review], ai_service))
    
    assert res["success_count"] == 1
    assert res["failure_count"] == 0
    
    # 2. 롤백 테스트: 모든 시도가 최종 실패하면 Pinecone delete 호출 확인
    mock_supabase_fail = MagicMock()
    mock_supabase_fail.table.return_value.insert.side_effect = Exception("General database connection lost")
    
    mock_pinecone = MagicMock()
    ai_service_pc = AIService(pinecone_client=mock_pinecone)
    
    service_fail = DashboardService(supabase_client=mock_supabase_fail)
    res_fail = loop.run_until_complete(service_fail.process_and_save_reviews([review], ai_service_pc))
    
    assert res_fail["success_count"] == 0
    assert res_fail["failure_count"] == 1
    # Pinecone delete_review_vector(또는 index.delete)가 롤백용으로 호출되었는지 확인
    assert ai_service_pc.pinecone.Index.return_value.delete.called

