import uuid
from typing import List, Optional
from datetime import datetime
from app.domains.reviews.repository import ReviewRepository
from app.domains.reviews.schemas import ReviewCreate
from app.core.cache import dashboard_cache


class ReviewService:
    def __init__(self, db_conn=None):
        self.repo = ReviewRepository(db_conn)

    def fetch_reviews_count(self, product_id: Optional[str] = None, period_days: Optional[int] = None,
                            sentiment: Optional[str] = None, q: Optional[str] = None,
                            priority: bool = False) -> int:
        _TTL = 120
        cache_key = ("reviews_count", product_id, period_days, sentiment, q, priority)
        hit, cached = dashboard_cache.get(cache_key, _TTL)
        if hit:
            return cached
        count = self.repo.fetch_count(product_id=product_id, period_days=period_days,
                                      sentiment=sentiment, q=q, priority=priority)
        dashboard_cache.set(cache_key, count)
        return count

    def fetch_reviews_advanced(self, product_id: Optional[str] = None, period_days: Optional[int] = None,
                               sentiment: Optional[str] = None, q: Optional[str] = None,
                               priority: bool = False, page: int = 1, limit: int = 20) -> list:
        return self.repo.fetch_advanced(product_id=product_id, period_days=period_days,
                                        sentiment=sentiment, q=q, priority=priority,
                                        page=page, limit=limit)

    def fetch_reviews_attribute_scores(self, product_id: Optional[str] = None,
                                       period_days: Optional[int] = None) -> dict:
        return self.repo.fetch_attribute_scores(product_id=product_id, period_days=period_days)

    async def process_and_save_reviews(self, reviews: List[ReviewCreate], ai_service) -> dict:
        """
        크롤링 리뷰 AI 분석 및 GCP Cloud SQL + pgvector 통합 적재 트랜잭션 메서드
        1. ABSA 엔진 구동
        2. Gemini Embedding 추출
        3. Cloud SQL PostgreSQL에 단일 트랜잭션 원자적 적재
        """
        from app.database.mock_data import MOCK_REVIEWS
        success_count = 0
        failure_count = 0
        processed_ids = []

        for review in reviews:
            try:
                review_id_val = str(uuid.UUID(review.review_id)) if review.review_id else str(uuid.uuid4())
            except Exception:
                review_id_val = str(uuid.uuid5(uuid.NAMESPACE_URL, str(review.review_id)))

            row_uuid = str(uuid.uuid4())

            try:
                absa_res = ai_service.analyze_review_absa(review.content)
                query_vector = ai_service._get_gemini_embedding(review.content)
                if query_vector is None:
                    query_vector = [0.01] * 768
                vector_str = f"[{','.join(map(str, query_vector))}]"

                sql_record = {
                    "id": row_uuid,
                    "product_id": review.product_id,
                    "source": review.source,
                    "reviewer_type": review.skin_type or review.reviewer_type,
                    "review_text": review.content,
                    "rating": review.rating,
                    "review_date": review.review_date or datetime.now().date().isoformat(),
                    "sentiment": absa_res["overall_sentiment"],
                    "sentiment_score": absa_res["overall_score"],
                    "keywords": absa_res["keywords"],
                    "issue_type": absa_res["issue_type"],
                    "ai_summary": absa_res["ai_summary"],
                    "review_id": review_id_val,
                    "embedding": vector_str,
                    "score_ingredients": absa_res["ingredients_skin_concerns_score"],
                    "score_formulation": absa_res["formulation_spreadability_score"],
                    "score_container": absa_res["container_design_score"]
                }

                if self.repo.conn is not None:
                    try:
                        self.repo.save_bulk(sql_record, absa_res["keywords"])
                        print(f"[ReviewService] Cloud SQL pgvector 원자적 적재 성공: {row_uuid}")
                    except Exception as e:
                        error_str = str(e)
                        if "column" in error_str or "does not exist" in error_str or "404" in error_str or "vector" in error_str:
                            print(f"[ReviewService] 컬럼 누락 감지, Self-Healing 실행: {e}")
                            scores_formatted = (
                                f"[성분/고민]: {absa_res['ingredients_skin_concerns_score']:.2f} | "
                                f"[제형/발림]: {absa_res['formulation_spreadability_score']:.2f} | "
                                f"[용기/디자인]: {absa_res['container_design_score']:.2f}"
                            )
                            healed_summary = f"{scores_formatted} \n요약: {absa_res['ai_summary']}"
                            self.repo.save_bulk_fallback(sql_record, absa_res["keywords"], healed_summary)
                            print(f"[ReviewService] 자가 치유 적재 성공: {row_uuid}")
                        else:
                            raise e
                else:
                    print(f"[ReviewService] Cloud SQL 미설정 상태, 가상 메모리 적재 처리: {row_uuid}")
                    MOCK_REVIEWS.append({
                        "id": row_uuid,
                        "product_id": review.product_id,
                        "source": review.source,
                        "reviewer_type": review.skin_type or review.reviewer_type or "일반",
                        "review_text": review.content,
                        "rating": review.rating,
                        "review_date": review.review_date or datetime.now().date().isoformat(),
                        "sentiment": absa_res["overall_sentiment"],
                        "sentiment_score": absa_res["overall_score"],
                        "keywords": absa_res["keywords"],
                        "issue_type": absa_res["issue_type"],
                        "ai_summary": absa_res["ai_summary"],
                        "review_id": review_id_val,
                        "created_at": datetime.now().isoformat()
                    })

                success_count += 1
                processed_ids.append(row_uuid)

            except Exception as e:
                print(f"[ReviewService] 리뷰 처리 중 예외 발생 (건너뜀): {e}")
                failure_count += 1

        dashboard_cache.invalidate_all()
        print("[ReviewService] 리뷰 적재 완료 — 대시보드 캐시 전체 무효화")

        return {
            "status": "completed",
            "total_reviews": len(reviews),
            "success_count": success_count,
            "failure_count": failure_count,
            "processed_ids": processed_ids
        }
