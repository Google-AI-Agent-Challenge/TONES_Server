import pytest
from unittest.mock import MagicMock, patch
from app.domains.ai_search.service import AIService
from app.domains.dashboard.service import DashboardService
from app.domains.ai_search.schemas import SearchRequest, GenerateRequest
from app.domains.reviews.schemas import ReviewCreate


def test_heuristic_absa_fallback():
    """
    GCP API 장애 또는 로컬 테스트 환경을 대비한 룰 베이스 ABSA 엔진 단위 테스트
    """
    service = AIService(db_conn=None)

    # 1. 트러블/자극 부작용 리뷰 검증
    res_trouble = service._local_heuristic_absa("이거 쓰고 좁쌀 여드름이 이마에 다 뒤집어졌어요 ㅠㅠ 너무 따갑고 자극적입니다.")
    assert res_trouble["ingredients_skin_concerns_score"] == 0.15
    assert "자극" in res_trouble["issue_type"]
    assert res_trouble["overall_sentiment"] == "negative"

    # 2. 발림성 극찬 및 산뜻 수분감 리뷰 검증
    res_form = service._local_heuristic_absa("진짜 대박 촉촉해요!! 발림성도 너무 부드럽고 끈적임 없이 제형이 산뜻합니다.")
    assert res_form["formulation_spreadability_score"] == 0.90
    assert "촉촉" in res_form["keywords"]
    assert res_form["overall_sentiment"] == "positive"


@patch("app.domains.ai_search.service.HAS_VERTEX_SDK", True)
@patch("app.domains.ai_search.service._init_vertex_ai")
@patch("app.domains.ai_search.service.GenerativeModel")
def test_vertex_generative_ai_answer(mock_gen_model, mock_init, client):
    """
    Vertex AI GenerativeModel을 활용해 RAG 답변이 올바르게 생성되는지 연동 모킹 검증
    """
    mock_init.return_value = True

    mock_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "GCP Vertex AI RAG 시스템에 의해 생성된 정교한 실시간 리뷰 분석 답변입니다."
    mock_instance.generate_content.return_value = mock_response
    mock_gen_model.return_value = mock_instance

    ai_service = AIService(db_conn=None)
    req = GenerateRequest(prompt="당근패드 트러블 후기 요약해줘", context="일부 민감성 사용자가 당근패드 리뉴얼 후 자극을 느꼈다는 불만이 있습니다.")

    answer = ai_service.generate_ai_answer(req)
    assert "GCP Vertex AI" in answer
    assert mock_instance.generate_content.called


def test_pgvector_semantic_search_sql():
    """
    GCP Cloud SQL PostgreSQL + pgvector를 활용한 RAG 코사인 유사도 쿼리가 정상 빌드되는지 검증
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_cursor.fetchall.return_value = [
        ("rev-uuid-1", "수분감은 좋은데 용기가 헛돌아요", 4, "2026-05-31", "neutral", "용기불편", "ai-summary", 0.92)
    ]
    mock_conn.cursor.return_value = mock_cursor

    ai_service = AIService(db_conn=mock_conn)
    ai_service._get_gemini_embedding = MagicMock(return_value=[0.01] * 768)

    req = SearchRequest(query="용기 뚜껑 불만 리뷰 찾아줘", top_k=3, filter={"product_id": "product-uuid-1"})

    results = ai_service.vector_search(req)

    assert len(results) == 1
    assert results[0].id == "rev-uuid-1"
    assert results[0].metadata["review_text"] == "수분감은 좋은데 용기가 헛돌아요"
    assert results[0].score == 0.92

    called_sql = mock_cursor.execute.call_args[0][0]
    assert "<=>" in called_sql
    assert "product_id = %s" in called_sql


def test_cloud_sql_atomic_rollback_on_save_failure():
    """
    GCP 통합 DB 아키텍처: 리뷰 및 임베딩 적재 중 RDBMS 오류 발생 시,
    동일 트랜잭션의 connection.rollback()이 작동하여 원자적으로 롤백되는지 검증
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_cursor.execute.side_effect = Exception("Cloud SQL Connection Timeout")
    mock_conn.cursor.return_value = mock_cursor

    from app.domains.reviews.service import ReviewService
    review_service = ReviewService(db_conn=mock_conn)
    ai_service = AIService(db_conn=mock_conn)
    ai_service._get_gemini_embedding = MagicMock(return_value=[0.02] * 768)
    ai_service.analyze_review_absa = MagicMock(return_value={
        "ingredients_skin_concerns_score": 0.8,
        "formulation_spreadability_score": 0.9,
        "container_design_score": 0.7,
        "overall_sentiment": "positive",
        "overall_score": 0.85,
        "keywords": ["촉촉"],
        "issue_type": "없음",
        "ai_summary": "수분 충전 완료"
    })

    review_in = ReviewCreate(
        product_id="product-uuid-123",
        content="이 제품 진짜 순하고 촉촉해서 매일 닦토로 쓰고 있어요.",
        rating=5,
        source="올리브영"
    )

    import asyncio
    res = asyncio.run(review_service.process_and_save_reviews([review_in], ai_service))

    assert res["success_count"] == 0
    assert res["failure_count"] == 1
    assert mock_conn.rollback.called
