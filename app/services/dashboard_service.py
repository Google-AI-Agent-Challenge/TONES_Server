import uuid
import re
import time
from typing import List, Optional
from datetime import datetime, timedelta
from app.schemas.dashboard import ReviewCreate
from app.services.ai_service import AIService

# 오프라인 상태 또는 DB 미연동 시 제공할 고품질의 화장품 패드 분석 목업 데이터
MOCK_PRODUCTS = [
    {
        "id": "e680f731-cfde-427f-9077-62f7e484ec21",
        "brand_name": "라운드랩",
        "product_name": "1025 독도 패드",
        "category": "pad",
        "target_skin": "민감성",
        "created_at": (datetime.now() - timedelta(days=60)).isoformat()
    },
    {
        "id": "04472697-d7c5-4cbe-bbc1-3cb62d3d4eba",
        "brand_name": "스킨푸드",
        "product_name": "캐롯 카로틴 카밍 워터 패드 (당근 패드)",
        "category": "pad",
        "target_skin": "민감성 및 자극성",
        "created_at": (datetime.now() - timedelta(days=45)).isoformat()
    },
    {
        "id": "63d4efec-06f6-43d2-93b4-11b26b88c9e3",
        "brand_name": "메디힐",
        "product_name": "티트리 트러블 패드",
        "category": "pad",
        "target_skin": "지성 및 여드름성",
        "created_at": (datetime.now() - timedelta(days=30)).isoformat()
    },
    {
        "id": "cda7adcd-30e5-4610-8dd6-d1b48a3e018a",
        "brand_name": "넘버즈인",
        "product_name": "5번 글루타치온 필름 패드",
        "category": "pad",
        "target_skin": "칙칙한 피부",
        "created_at": (datetime.now() - timedelta(days=20)).isoformat()
    }
]

MOCK_REVIEWS = [
    {
        "id": "rev_1",
        "product_id": "04472697-d7c5-4cbe-bbc1-3cb62d3d4eba",
        "source": "올리브영",
        "reviewer_type": "민감성 피부",
        "review_text": "원래 당근패드 엄청 좋아해서 샀는데 이번 리뉴얼된 패드는 저한테 살짝 자극적이에요ㅠㅠ 쓰고 나서 볼 쪽이 붉어지고 좁쌀 트러블이 올라왔어요. 제형은 여전히 촉촉한데 성분이 바뀐 걸까요? 아쉬워요.",
        "rating": 2,
        "review_date": (datetime.now() - timedelta(days=1)).isoformat(),
        "sentiment": "negative",
        "sentiment_score": 0.15,
        "keywords": ["당근패드", "자극", "붉어짐", "좁쌀 트러블", "성분"],
        "issue_type": "트러블, 자극, 성분",
        "ai_summary": "리뉴얼된 패드 사용 후 볼이 붉어지고 좁쌀 트러블이 생겨 성분 변화나 자극성에 대한 아쉬움을 호소함.",
        "created_at": datetime.now().isoformat(),
        "review_id": "rev_external_1001",
        "products": MOCK_PRODUCTS[1]
    },
    {
        "id": "rev_2",
        "product_id": "e680f731-cfde-427f-9077-62f7e484ec21",
        "source": "네이버 스토어",
        "reviewer_type": "건성 피부",
        "review_text": "독도패드 순하다고 해서 샀는데 이상하게 저는 이거만 쓰면 피부가 엄청 따가워요. 각질 제거용 엠보싱면이 자극이 되는 건지 볼 부분이 아프고 따가움이 오래 가네요. 민감성분들은 조심해야 할 듯..",
        "rating": 2,
        "review_date": (datetime.now() - timedelta(days=2)).isoformat(),
        "sentiment": "negative",
        "sentiment_score": 0.18,
        "keywords": ["독도패드", "따가움", "자극", "볼 부분", "민감성"],
        "issue_type": "자극, 따가움",
        "ai_summary": "순하다고 알려진 제품임에도 사용 후 볼 부분이 따갑고 자극을 느껴 민감성 피부 주의를 당부함.",
        "created_at": datetime.now().isoformat(),
        "review_id": "rev_external_1002",
        "products": MOCK_PRODUCTS[0]
    },
    {
        "id": "rev_3",
        "product_id": "63d4efec-06f6-43d2-93b4-11b26b88c9e3",
        "source": "화해",
        "reviewer_type": "복합성 여드름 피부",
        "review_text": "트러블 진정 효과 보려고 메디힐 티트리 패드 샀는데 진정은커녕 트러블이 더 심해졌어요. 화농성 여드름이 이마랑 턱 쪽에 다다닥 올라와서 피부과 다녀왔습니다. 저한테 티트리가 안 맞는 건지 성분에 맞지 않는 게 있는 듯.",
        "rating": 1,
        "review_date": (datetime.now() - timedelta(days=3)).isoformat(),
        "sentiment": "negative",
        "sentiment_score": 0.05,
        "keywords": ["메디힐", "티트리", "트러블 악화", "여드름", "성분"],
        "issue_type": "트러블, 성분",
        "ai_summary": "진정 효과를 기대하고 사용했으나 이마와 턱에 화농성 여드름 등 트러블이 악화되어 피부과 치료를 받음.",
        "created_at": datetime.now().isoformat(),
        "review_id": "rev_external_1003",
        "products": MOCK_PRODUCTS[2]
    },
    {
        "id": "rev_4",
        "product_id": "04472697-d7c5-4cbe-bbc1-3cb62d3d4eba",
        "source": "올리브영",
        "reviewer_type": "지성 피부",
        "review_text": "수분 충전엔 좋은데 너무 끈적여요. 여름철에는 도저히 못 쓸 제형입니다. 흡수가 잘 안 되고 피부 겉에 겉돌면서 화장이 다 밀려요. 끈적임이랑 밀림이 심해서 아침에는 절대 못 쓰고 저녁에만 대충 씁니다.",
        "rating": 2,
        "review_date": (datetime.now() - timedelta(days=4)).isoformat(),
        "sentiment": "negative",
        "sentiment_score": 0.22,
        "keywords": ["수분", "끈적임", "밀림", "제형", "흡수"],
        "issue_type": "제형, 발림성",
        "ai_summary": "끈적이고 흡수가 안 되는 제형 탓에 아침 사용 시 화장이 밀려 저녁용으로 제한 사용하고 있음.",
        "created_at": datetime.now().isoformat(),
        "review_id": "rev_external_1004",
        "products": MOCK_PRODUCTS[1]
    },
    {
        "id": "rev_5",
        "product_id": "cda7adcd-30e5-4610-8dd6-d1b48a3e018a",
        "source": "네이버 스토어",
        "reviewer_type": "민감성 피부",
        "review_text": "제품 자체는 무난한 것 같은데 용기가 너무 불편해요!! 뚜껑 닫을 때 자꾸 안 맞물려서 헛돌고, 안에 집게 꽂아두는 캡 부분이 자꾸 헐거워져서 아래로 빠집니다. 용기 개선이 시급합니다.",
        "rating": 2,
        "review_date": (datetime.now() - timedelta(days=5)).isoformat(),
        "sentiment": "negative",
        "sentiment_score": 0.25,
        "keywords": ["용기 불편", "뚜껑 불량", "집게 캡", "디자인"],
        "issue_type": "용기불량, 용기, 디자인",
        "ai_summary": "제품 내용은 무난하나 뚜껑이 헛돌고 내부 집게 캡이 헐거워져 빠지는 등 용기 개선 필요성을 강력 어필함.",
        "created_at": datetime.now().isoformat(),
        "review_id": "rev_external_1005",
        "products": MOCK_PRODUCTS[3]
    }
]


class DashboardService:
    def __init__(self, db_conn=None):
        self.conn = db_conn
        self._stats_cache = {}  # TTL 캐시 보관소: {(product_id, period_days): (timestamp, stats_data)}

    def _parse_db_row_to_review(self, row) -> dict:
        """
        SQL Query 결과 Tuple 데이터를 Schema에 맞는 딕셔너리로 안전하게 포맷팅
        (데이터베이스에 score_ingredients 등 분석 컬럼이 누락되어 있어도 자동 감지하여 자가 치유 복구 수행!)
        """
        # p.id 가 존재하는지 체크하여 products 매핑 (보통 r 컬럼들 뒤에 붙으므로 row[-5] ~ row[-1])
        prod_obj = None
        if len(row) >= 19:
            p_idx = len(row) - 5
            if row[p_idx] is not None:
                prod_obj = {
                    "id": str(row[p_idx]),
                    "brand_name": row[p_idx+1],
                    "product_name": row[p_idx+2],
                    "category": row[p_idx+3],
                    "target_skin": row[p_idx+4]
                }

        review_dict = {
            "id": str(row[0]),
            "product_id": str(row[1]),
            "source": row[2],
            "reviewer_type": row[3],
            "review_text": row[4],
            "rating": int(row[5]),
            "review_date": str(row[6]),
            "sentiment": str(row[7]),
            "sentiment_score": float(row[8]) if row[8] is not None else None,
            "keywords": list(row[9]) if row[9] is not None else [],
            "issue_type": row[10],
            "ai_summary": row[11],
            "created_at": str(row[12]) if row[12] is not None else None,
            "review_id": str(row[13]) if row[13] is not None else None,
            "products": prod_obj
        }

        # score_ingredients 컬럼 존재 여부 체크 (튜플 길이를 통해 유연하게 확인)
        has_score_columns = False
        if len(row) >= 22:
            has_score_columns = True
            
        if has_score_columns:
            review_dict["score_ingredients"] = float(row[14]) if row[14] is not None else 0.5
            review_dict["score_formulation"] = float(row[15]) if row[15] is not None else 0.5
            review_dict["score_container"] = float(row[16]) if row[16] is not None else 0.5
        else:
            # 컬럼 누락 시 summary 및 평점 기반 자가 치유(Self-Healing) 기동!
            parsed = self._extract_scores_from_summary(review_dict.get("ai_summary", ""), review_dict=review_dict)
            review_dict["score_ingredients"] = parsed["ingredients_skin_concerns_score"]
            review_dict["score_formulation"] = parsed["formulation_spreadability_score"]
            review_dict["score_container"] = parsed["container_design_score"]

        return review_dict

    def fetch_products(self) -> List[dict]:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT p.id, b.name AS brand_name, p.product_name, c.name AS category, s.name AS target_skin, p.created_at 
                    FROM public.products p
                    JOIN public.brands b ON p.brand_id = b.id
                    JOIN public.categories c ON p.category_id = c.id
                    JOIN public.skin_types s ON p.skin_type_id = s.id
                    ORDER BY p.product_name ASC
                """)
                rows = cursor.fetchall()
                cursor.close()
                return [{
                    "id": str(r[0]),
                    "brand_name": r[1],
                    "product_name": r[2],
                    "category": r[3],
                    "target_skin": r[4],
                    "created_at": str(r[5]) if r[5] is not None else None
                } for r in rows]
            except Exception as e:
                print(f"[DashboardService.fetch_products] Cloud SQL fetch 실패, 로컬 Mock 데이터로 폴백: {e}")
        return MOCK_PRODUCTS

    def fetch_latest_reviews(self, limit: int = 20) -> List[dict]:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                sql = """
                    SELECT r.id, r.product_id, r.source::text, r.reviewer_type::text, r.review_text, r.rating, 
                           r.review_date::text, r.sentiment::text, r.sentiment_score, 
                           COALESCE(array_agg(k.keyword) FILTER (WHERE k.keyword IS NOT NULL), '{}') AS keywords,
                           r.issue_type::text, r.ai_summary, r.created_at, r.review_id,
                           r.score_ingredients, r.score_formulation, r.score_container,
                           p.id, b.name AS brand_name, p.product_name, c.name AS category, s.name AS target_skin
                    FROM public.reviews r
                    LEFT JOIN public.products p ON r.product_id = p.id
                    LEFT JOIN public.brands b ON p.brand_id = b.id
                    LEFT JOIN public.categories c ON p.category_id = c.id
                    LEFT JOIN public.skin_types s ON p.skin_type_id = s.id
                    LEFT JOIN public.review_keywords rk ON r.id = rk.review_id
                    LEFT JOIN public.keywords k ON rk.keyword_id = k.id
                    GROUP BY r.id, p.id, b.name, c.name, s.name
                    ORDER BY r.review_date DESC, r.created_at DESC
                    LIMIT %s
                """
                cursor.execute(sql, [limit])
                rows = cursor.fetchall()
                cursor.close()
                return [self._parse_db_row_to_review(r) for r in rows]
            except Exception as e:
                print(f"[DashboardService.fetch_latest_reviews] Cloud SQL fetch 실패, 로컬 Mock 데이터로 폴백: {e}")
        return MOCK_REVIEWS[:limit]

    def fetch_reviews_by_keywords(self, keywords: List[str], limit: int = 20) -> List[dict]:
        if not keywords:
            return self.fetch_latest_reviews(limit)

        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                
                # 동적 LIKE 검색 조건 수립
                where_clauses = []
                params = []
                for kw in keywords:
                    where_clauses.append("r.review_text ILIKE %s")
                    params.append(f"%{kw}%")
                
                where_str = f"WHERE {' OR '.join(where_clauses)}"
                sql = f"""
                    SELECT r.id, r.product_id, r.source::text, r.reviewer_type::text, r.review_text, r.rating, 
                           r.review_date::text, r.sentiment::text, r.sentiment_score, 
                           COALESCE(array_agg(k.keyword) FILTER (WHERE k.keyword IS NOT NULL), '{}') AS keywords,
                           r.issue_type::text, r.ai_summary, r.created_at, r.review_id,
                           r.score_ingredients, r.score_formulation, r.score_container,
                           p.id, b.name AS brand_name, p.product_name, c.name AS category, s.name AS target_skin
                    FROM public.reviews r
                    LEFT JOIN public.products p ON r.product_id = p.id
                    LEFT JOIN public.brands b ON p.brand_id = b.id
                    LEFT JOIN public.categories c ON p.category_id = c.id
                    LEFT JOIN public.skin_types s ON p.skin_type_id = s.id
                    LEFT JOIN public.review_keywords rk ON r.id = rk.review_id
                    LEFT JOIN public.keywords k ON rk.keyword_id = k.id
                    {where_str}
                    GROUP BY r.id, p.id, b.name, c.name, s.name
                    ORDER BY r.review_date DESC, r.created_at DESC
                    LIMIT %s
                """
                params.append(limit)
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                cursor.close()
                return [self._parse_db_row_to_review(r) for r in rows]
            except Exception as e:
                print(f"[DashboardService.fetch_reviews_by_keywords] Cloud SQL fetch 실패, 로컬 Mock 데이터로 폴백: {e}")

        # Local mock filter
        filtered = []
        for r in MOCK_REVIEWS:
            match = False
            for kw in keywords:
                if kw.lower() in r["review_text"].lower():
                    match = True
                    break
            if match:
                filtered.append(r)
        return filtered[:limit] if filtered else MOCK_REVIEWS[:limit]

    def fetch_reviews_by_product(self, product_id: str, limit: int = 20) -> List[dict]:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                sql = """
                    SELECT r.id, r.product_id, r.source::text, r.reviewer_type::text, r.review_text, r.rating, 
                           r.review_date::text, r.sentiment::text, r.sentiment_score, 
                           COALESCE(array_agg(k.keyword) FILTER (WHERE k.keyword IS NOT NULL), '{}') AS keywords,
                           r.issue_type::text, r.ai_summary, r.created_at, r.review_id,
                           r.score_ingredients, r.score_formulation, r.score_container,
                           p.id, b.name AS brand_name, p.product_name, c.name AS category, s.name AS target_skin
                    FROM public.reviews r
                    LEFT JOIN public.products p ON r.product_id = p.id
                    LEFT JOIN public.brands b ON p.brand_id = b.id
                    LEFT JOIN public.categories c ON p.category_id = c.id
                    LEFT JOIN public.skin_types s ON p.skin_type_id = s.id
                    LEFT JOIN public.review_keywords rk ON r.id = rk.review_id
                    LEFT JOIN public.keywords k ON rk.keyword_id = k.id
                    WHERE r.product_id = %s
                    GROUP BY r.id, p.id, b.name, c.name, s.name
                    ORDER BY r.review_date DESC, r.created_at DESC
                    LIMIT %s
                """
                cursor.execute(sql, [product_id, limit])
                rows = cursor.fetchall()
                cursor.close()
                return [self._parse_db_row_to_review(r) for r in rows]
            except Exception as e:
                print(f"[DashboardService.fetch_reviews_by_product] Cloud SQL fetch 실패, 로컬 Mock 데이터로 폴백: {e}")

        # Local mock filter
        filtered = [r for r in MOCK_REVIEWS if r["product_id"] == product_id]
        return filtered[:limit] if filtered else MOCK_REVIEWS[:limit]

    def fetch_reviews_by_ids(self, ids: List[str]) -> List[dict]:
        if not ids:
            return []
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                # PostgreSQL ANY 구문 또는 동적 플레이스홀더를 활용한 ID 리스트 매칭
                placeholders = ",".join(["%s"] * len(ids))
                sql = f"""
                    SELECT r.id, r.product_id, r.source::text, r.reviewer_type::text, r.review_text, r.rating, 
                           r.review_date::text, r.sentiment::text, r.sentiment_score, 
                           COALESCE(array_agg(k.keyword) FILTER (WHERE k.keyword IS NOT NULL), '{}') AS keywords,
                           r.issue_type::text, r.ai_summary, r.created_at, r.review_id,
                           r.score_ingredients, r.score_formulation, r.score_container,
                           p.id, b.name AS brand_name, p.product_name, c.name AS category, s.name AS target_skin
                    FROM public.reviews r
                    LEFT JOIN public.products p ON r.product_id = p.id
                    LEFT JOIN public.brands b ON p.brand_id = b.id
                    LEFT JOIN public.categories c ON p.category_id = c.id
                    LEFT JOIN public.skin_types s ON p.skin_type_id = s.id
                    LEFT JOIN public.review_keywords rk ON r.id = rk.review_id
                    LEFT JOIN public.keywords k ON rk.keyword_id = k.id
                    WHERE r.id IN ({placeholders})
                    GROUP BY r.id, p.id, b.name, c.name, s.name
                    ORDER BY r.review_date DESC, r.created_at DESC
                """
                cursor.execute(sql, ids)
                rows = cursor.fetchall()
                cursor.close()
                return [self._parse_db_row_to_review(r) for r in rows]
            except Exception as e:
                print(f"[DashboardService.fetch_reviews_by_ids] Cloud SQL fetch 실패: {e}")
        # 오프라인 폴백
        filtered = [r for r in MOCK_REVIEWS if r["id"] in ids]
        return filtered

    def save_layout(self, user_token: str, pinned_widget: str | None) -> bool:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                sql = """
                    INSERT INTO public.user_layouts (user_token, pinned_widget, updated_at)
                    VALUES (%s, %s, timezone('utc'::text, now()))
                    ON CONFLICT (user_token) 
                    DO UPDATE SET pinned_widget = EXCLUDED.pinned_widget, updated_at = timezone('utc'::text, now())
                """
                cursor.execute(sql, [user_token, pinned_widget])
                self.conn.commit()
                cursor.close()
                return True
            except Exception as e:
                print(f"[DashboardService.save_layout] Cloud SQL upsert 실패: {e}")
                try:
                    self.conn.rollback()
                except Exception:
                    pass
                return False
        return True

    def load_layout(self, user_token: str) -> str | None:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT pinned_widget FROM public.user_layouts WHERE user_token = %s",
                    [user_token]
                )
                row = cursor.fetchone()
                cursor.close()
                if row:
                    return row[0]
            except Exception as e:
                print(f"[DashboardService.load_layout] Cloud SQL fetch 실패: {e}")
                return None
        return None

    async def process_and_save_reviews(self, reviews: List[ReviewCreate], ai_service: AIService) -> dict:
        """
        크롤링 리뷰 AI 분석 및 GCP Cloud SQL + pgvector 통합 적재 트랜잭션 메서드 (원자적 성공 보장)
        1. 원시 리뷰에 대해 ABSA 엔진 구동
        2. Gemini Embedding API를 통해 텍스트 벡터 추출
        3. Cloud SQL PostgreSQL에 단일 트랜잭션으로 RDBMS 데이터와 벡터를 동시에 완벽히 밀어넣음!
           (Supabase 적재 실패 시 Pinecone을 수동 롤백하던 구식 분산 복잡성은 이제 RDBMS rollback() 한 줄로 해결!)
        """
        success_count = 0
        failure_count = 0
        processed_ids = []

        for review in reviews:
            # 고유 ID 생성 (UUID 검증 및 deterministic UUID5 지원)
            try:
                review_id_val = str(uuid.UUID(review.review_id)) if review.review_id else str(uuid.uuid4())
            except Exception:
                review_id_val = str(uuid.uuid5(uuid.NAMESPACE_URL, str(review.review_id)))

            row_uuid = str(uuid.uuid4())

            try:
                # 1. Gemini ABSA 감성 분석 엔진 실행
                absa_res = ai_service.analyze_review_absa(review.content)

                # 2. RAG 적재를 위한 Gemini 768차원 임베딩 추출
                query_vector = ai_service._get_gemini_embedding(review.content)
                if query_vector is None:
                    # 임베딩 에러 상황 시 768차원 임시 더미 벡터 주입 (로컬 / 오프라인 가용성 보장)
                    query_vector = [0.01] * 768
                
                # pgvector 직렬화 텍스트 포맷 빌드 (예: "[0.12, 0.34, ...]")
                vector_str = f"[{','.join(map(str, query_vector))}]"

                # 3. Cloud SQL DB 적재용 Record 빌드
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

                # 4. 단일 DB 트랜잭션 수행 (자가 치유(Self-Healing) 및 완벽한 동시 롤백 내장)
                if self.conn is not None:
                    try:
                        cursor = self.conn.cursor()
                        # [시도 1] 개별 감성 점수 컬럼 및 임베딩 벡터를 모두 포함하여 단일 인서트 시도
                        sql = """
                            INSERT INTO public.reviews (
                                id, product_id, source, reviewer_type, review_text, rating, review_date, 
                                sentiment, sentiment_score, issue_type, ai_summary, review_id, 
                                embedding, score_ingredients, score_formulation, score_container
                            ) VALUES (
                                %s::uuid, %s::uuid, 
                                CASE 
                                    WHEN LOWER(TRIM(%s)) IN ('youtube', 'blog', 'naver_store', 'olive_young', 'mock') THEN LOWER(TRIM(%s))::source_type
                                    ELSE 'other'::source_type
                                END,
                                CASE 
                                    WHEN LOWER(TRIM(%s)) IN ('general', 'influencer', 'expert') THEN LOWER(TRIM(%s))::reviewer_type
                                    ELSE 'general'::reviewer_type
                                END,
                                %s, %s, %s::date, %s::sentiment_type, %s, 
                                CASE 
                                    WHEN LOWER(TRIM(%s)) IN ('ingredients', 'formulation', 'container', 'scent', 'irritation', 'none') THEN LOWER(TRIM(%s))::issue_type
                                    ELSE 'other'::issue_type
                                END,
                                %s, %s, %s::vector, %s, %s, %s
                            )
                        """
                        cursor.execute(sql, [
                            sql_record["id"], sql_record["product_id"], 
                            sql_record["source"], sql_record["source"],
                            sql_record["reviewer_type"], sql_record["reviewer_type"],
                            sql_record["review_text"], sql_record["rating"], sql_record["review_date"],
                            sql_record["sentiment"], sql_record["sentiment_score"], 
                            sql_record["issue_type"], sql_record["issue_type"],
                            sql_record["ai_summary"], sql_record["review_id"],
                            sql_record["embedding"], sql_record["score_ingredients"],
                            sql_record["score_formulation"], sql_record["score_container"]
                        ])
                        
                        # 다대다 키워드 적재 (트랜잭션 세션 내에서 함께 원자적으로 수행)
                        if sql_record["keywords"]:
                            for kw in sql_record["keywords"]:
                                if kw and kw.strip():
                                    clean_kw = kw.strip()
                                    cursor.execute("INSERT INTO public.keywords (keyword) VALUES (%s) ON CONFLICT (keyword) DO NOTHING", [clean_kw])
                                    cursor.execute("SELECT id FROM public.keywords WHERE keyword = %s", [clean_kw])
                                    kw_id_row = cursor.fetchone()
                                    if kw_id_row:
                                        cursor.execute("INSERT INTO public.review_keywords (review_id, keyword_id) VALUES (%s::uuid, %s) ON CONFLICT DO NOTHING", [sql_record["id"], kw_id_row[0]])

                        self.conn.commit()
                        cursor.close()
                        print(f"[DashboardService] Cloud SQL pgvector 원자적 적재 성공: {row_uuid}")
                    except Exception as e:
                        try:
                            self.conn.rollback()
                        except Exception:
                            pass
                        
                        error_str = str(e)
                        # [시도 2] 자가 치유(Self-Healing) 작동: 컬럼 누락 혹은 pgvector 미설치 시 텍스트 전용 패키징 폴백 시도
                        if "column" in error_str or "does not exist" in error_str or "404" in error_str or "vector" in error_str:
                            print(f"[DashboardService] 감성 점수 또는 벡터 컬럼 누락 감지, Self-Healing 실행: {e}")
                            scores_formatted = (
                                f"[성분/고민]: {absa_res['ingredients_skin_concerns_score']:.2f} | "
                                f"[제형/발림]: {absa_res['formulation_spreadability_score']:.2f} | "
                                f"[용기/디자인]: {absa_res['container_design_score']:.2f}"
                            )
                            healed_summary = f"{scores_formatted} \n요약: {absa_res['ai_summary']}"
                            
                            try:
                                cursor = self.conn.cursor()
                                # 임베딩 및 보완 점수 필드를 제외하고 핵심 텍스트 컬럼만으로 DB 저장 시도
                                fallback_sql = """
                                    INSERT INTO public.reviews (
                                        id, product_id, source, reviewer_type, review_text, rating, review_date, 
                                        sentiment, sentiment_score, issue_type, ai_summary, review_id
                                    ) VALUES (
                                        %s::uuid, %s::uuid, 
                                        CASE 
                                            WHEN LOWER(TRIM(%s)) IN ('youtube', 'blog', 'naver_store', 'olive_young', 'mock') THEN LOWER(TRIM(%s))::source_type
                                            ELSE 'other'::source_type
                                        END,
                                        CASE 
                                            WHEN LOWER(TRIM(%s)) IN ('general', 'influencer', 'expert') THEN LOWER(TRIM(%s))::reviewer_type
                                            ELSE 'general'::reviewer_type
                                        END,
                                        %s, %s, %s::date, %s::sentiment_type, %s, 
                                        CASE 
                                            WHEN LOWER(TRIM(%s)) IN ('ingredients', 'formulation', 'container', 'scent', 'irritation', 'none') THEN LOWER(TRIM(%s))::issue_type
                                            ELSE 'other'::issue_type
                                        END,
                                        %s, %s
                                    )
                                """
                                cursor.execute(fallback_sql, [
                                    sql_record["id"], sql_record["product_id"], 
                                    sql_record["source"], sql_record["source"],
                                    sql_record["reviewer_type"], sql_record["reviewer_type"],
                                    sql_record["review_text"], sql_record["rating"], sql_record["review_date"],
                                    sql_record["sentiment"], sql_record["sentiment_score"], 
                                    sql_record["issue_type"], sql_record["issue_type"],
                                    healed_summary, sql_record["review_id"]
                                ])
                                
                                # 다대다 키워드 적재 (자가 치유 시에도 동일하게 적재)
                                if sql_record["keywords"]:
                                    for kw in sql_record["keywords"]:
                                        if kw and kw.strip():
                                            clean_kw = kw.strip()
                                            cursor.execute("INSERT INTO public.keywords (keyword) VALUES (%s) ON CONFLICT (keyword) DO NOTHING", [clean_kw])
                                            cursor.execute("SELECT id FROM public.keywords WHERE keyword = %s", [clean_kw])
                                            kw_id_row = cursor.fetchone()
                                            if kw_id_row:
                                                cursor.execute("INSERT INTO public.review_keywords (review_id, keyword_id) VALUES (%s::uuid, %s) ON CONFLICT DO NOTHING", [sql_record["id"], kw_id_row[0]])

                                self.conn.commit()
                                cursor.close()
                                print(f"[DashboardService] 자가 치유된 레코드 Cloud SQL 적재 성공: {row_uuid}")
                            except Exception as final_err:
                                try:
                                    self.conn.rollback()
                                except Exception:
                                    pass
                                print(f"[DashboardService] 자가 치유 최종 DB 적재 실패 (건너뜀): {final_err}")
                                raise final_err
                        else:
                            print(f"[DashboardService] Cloud SQL 기타 데이터베이스 트랜잭션 오류 발생: {e}")
                            raise e
                else:
                    # 오프라인 및 로컬 테스트 환경 시뮬레이션
                    print(f"[DashboardService] Cloud SQL 미설정 상태, 가상 메모리 적재 처리: {row_uuid}")
                    mock_record = {
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
                        "ai_summary": f"[성분/고민]: {absa_res['ingredients_skin_concerns_score']:.2f} | [제형/발림]: {absa_res['formulation_spreadability_score']:.2f} | [용기/디자인]: {absa_res['container_design_score']:.2f} \n요약: {absa_res['ai_summary']}",
                        "review_id": review_id_val,
                        "created_at": datetime.now().isoformat()
                    }
                    MOCK_REVIEWS.append(mock_record)

                success_count += 1
                processed_ids.append(row_uuid)

            except Exception as e:
                print(f"[DashboardService] 리뷰 처리 중 예외 발생 (건너뜀 및 실패 카운트 증가): {e}")
                failure_count += 1

        return {
            "status": "completed",
            "total_reviews": len(reviews),
            "success_count": success_count,
            "failure_count": failure_count,
            "processed_ids": processed_ids
        }

    def _extract_scores_from_summary(self, ai_summary: str, review_dict: dict = None) -> dict:
        """
        ai_summary 문자열에서 정규표현식을 이용하여 [성분/고민], [제형/발림], [용기/디자인] 점수를 파싱 및 복원.
        만약 파싱에 실패하거나 누락된 경우, review_dict(평점 및 리뷰 텍스트)를 기반으로 감성 점수를 휴리스틱하게 추정.
        """
        scores = {
            "ingredients_skin_concerns_score": 0.5,
            "formulation_spreadability_score": 0.5,
            "container_design_score": 0.5
        }
        
        parsed_ok = False
        if ai_summary:
            try:
                m_ing = re.search(r"\[성분/고민\]:\s*([0-9.]+)", ai_summary)
                m_form = re.search(r"\[제형/발림\]:\s*([0-9.]+)", ai_summary)
                m_cont = re.search(r"\[용기/디자인\]:\s*([0-9.]+)", ai_summary)

                if m_ing:
                    scores["ingredients_skin_concerns_score"] = float(m_ing.group(1))
                    parsed_ok = True
                if m_form:
                    scores["formulation_spreadability_score"] = float(m_form.group(1))
                    parsed_ok = True
                if m_cont:
                    scores["container_design_score"] = float(m_cont.group(1))
                    parsed_ok = True
            except Exception as e:
                print(f"[DashboardService] 감성 점수 파싱 중 오류: {e}")

        # 정규식 파싱이 안 되었거나 누락된 경우, review_dict가 있다면 평점 및 키워드 기반 휴리스틱 추정 실행
        if not parsed_ok and review_dict:
            try:
                rating = review_dict.get("rating", 3)
                text = review_dict.get("review_text") or review_dict.get("content") or ""
                
                ing_base = 0.50
                form_base = 0.50
                cont_base = 0.50

                if rating == 5:
                    ing_base = 0.88
                    form_base = 0.94
                    cont_base = 0.74
                elif rating == 4:
                    ing_base = 0.72
                    form_base = 0.80
                    cont_base = 0.60
                elif rating == 3:
                    ing_base = 0.52
                    form_base = 0.56
                    cont_base = 0.40
                elif rating == 2:
                    ing_base = 0.30
                    form_base = 0.36
                    cont_base = 0.22
                elif rating == 1:
                    ing_base = 0.12
                    form_base = 0.14
                    cont_base = 0.08

                ing_score = ing_base
                form_score = form_base
                cont_score = cont_base

                ing_pos = ["순해", "순하고", "자극 없", "자극없", "진정", "트러블 안", "여드름 안", "붉은기", "완화", "개선", "피부결", "진정에", "안심", "트러블성"]
                ing_neg = ["트러블", "뒤집", "자극", "여드름", "간지러", "따가", "붉", "좁쌀", "붉어지", "가렵", "간지", "좁쌀여드름", "피부 뒤집", "뒤집어", "화끈", "자극감"]
                
                form_pos = ["촉촉", "발림", "제형", "두께", "밀착", "보습", "에센스 많", "충분", "부드러", "닦토", "흡수", "수분감", "밀착력", "두툼", "패드 부드", "닦기 편", "부드러운"]
                form_neg = ["끈적", "밀려", "두껍", "거칠", "건조", "보풀", "찢어", "얇아", "흡수 안", "푸석", "밀림", "보풀", "찢어짐", "에센스 부족", "말라"]

                cont_pos = ["용기", "디자인", "집게", "위생", "뚜껑", "패키지", "예뻐", "편리"]
                cont_neg = ["불편", "새요", "샘", "집게 불편", "뚜껑 불편", "새고", "흐르고", "위생적이지", "집게 분실", "뚜껑 잘 안"]

                if any(k in text for k in ing_pos):
                    ing_score = min(0.96, ing_score + 0.12)
                if any(k in text for k in ing_neg):
                    ing_score = max(0.04, ing_score - 0.22)

                if any(k in text for k in form_pos):
                    form_score = min(0.96, form_score + 0.12)
                if any(k in text for k in form_neg):
                    form_score = max(0.04, form_score - 0.22)

                if any(k in text for k in cont_pos):
                    cont_score = min(0.96, cont_score + 0.12)
                if any(k in text for k in cont_neg):
                    cont_score = max(0.04, cont_score - 0.22)

                scores["ingredients_skin_concerns_score"] = round(ing_score, 2)
                scores["formulation_spreadability_score"] = round(form_score, 2)
                scores["container_design_score"] = round(cont_score, 2)
            except Exception as e:
                print(f"[DashboardService] 휴리스틱 감성 분석 실패: {e}")

        return scores

    def _aggregate_reviews(self, reviews: list[dict]) -> dict:
        """
        개별 리뷰 목록에 대한 통계 애그리게이션 계산 (자가 치유 파싱 및 휴리스틱 감성 점수 추정 지원)
        """
        total = len(reviews)
        if total == 0:
            return {
                "total_reviews": 0,
                "average_rating": 0.0,
                "sentiment_breakdown": {"positive": 0, "neutral": 0, "negative": 0},
                "attribute_scores": {
                    "ingredients": 0.5,
                    "formulation": 0.5,
                    "container": 0.5
                }
            }

        ratings_sum = 0
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        
        sum_ing = 0.0
        sum_form = 0.0
        sum_cont = 0.0

        for r in reviews:
            ratings_sum += r.get("rating", 0)
            
            # 감성 카운팅
            sent = r.get("sentiment")
            if sent in sentiment_counts:
                sentiment_counts[sent] += 1
            else:
                sentiment_counts["neutral"] += 1

            # 속성별 점수 추출 (컬럼 우선, 없을 경우 ai_summary 및 휴리스틱 자가 치유 파싱)
            ing_val = r.get("score_ingredients")
            form_val = r.get("score_formulation")
            cont_val = r.get("score_container")

            if ing_val is not None and form_val is not None and cont_val is not None:
                sum_ing += float(ing_val)
                sum_form += float(form_val)
                sum_cont += float(cont_val)
            else:
                parsed = self._extract_scores_from_summary(r.get("ai_summary", ""), review_dict=r)
                sum_ing += parsed["ingredients_skin_concerns_score"]
                sum_form += parsed["formulation_spreadability_score"]
                sum_cont += parsed["container_design_score"]

        return {
            "total_reviews": total,
            "average_rating": round(ratings_sum / total, 2),
            "sentiment_breakdown": sentiment_counts,
            "attribute_scores": {
                "ingredients": round(sum_ing / total, 4),
                "formulation": round(sum_form / total, 4),
                "container": round(sum_cont / total, 4)
            }
        }

    def _get_mock_reviews_split(self, product_id: str | None, period_days: int) -> tuple[list[dict], list[dict]]:
        """
        오프라인 환경용 리뷰 분할 집계
        """
        today = datetime.now().date()
        start_date_this_week = today - timedelta(days=period_days)
        start_date_last_week = today - timedelta(days=2 * period_days)

        reviews_this = []
        reviews_last = []

        for r in MOCK_REVIEWS:
            if product_id and r.get("product_id") != product_id:
                continue

            r_date_str = r.get("review_date")
            try:
                if "T" in r_date_str:
                    r_date = datetime.fromisoformat(r_date_str).date()
                else:
                    r_date = datetime.strptime(r_date_str, "%Y-%m-%d").date()
            except Exception:
                r_date = today

            if r_date >= start_date_this_week:
                reviews_this.append(r)
            elif r_date >= start_date_last_week:
                reviews_last.append(r)

        return reviews_this, reviews_last

    async def get_dashboard_statistics(self, product_id: str | None, period_days: int, ai_service: AIService) -> dict:
        """
        통합 통계 서빙 및 캐싱 서비스 레이어 메서드 (주간 대비 WoW 감지 및 Gemini 요약 포함)
        """
        # 1. 인메모리 TTL 캐시 확인 (60초 만료 시간 적용)
        cache_key = (product_id, period_days)
        if cache_key in self._stats_cache:
            cached_time, cached_data = self._stats_cache[cache_key]
            if time.time() - cached_time < 60:
                print(f"[DashboardService] 캐시 히트 (TTL 60s): {cache_key}")
                return cached_data

        # 2. Cloud SQL에서 해당 제품의 리뷰 기간별 조회
        reviews_this = []
        reviews_last = []
        
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                today = datetime.now().date()
                start_date_this_week = (today - timedelta(days=period_days)).isoformat()
                start_date_last_week = (today - timedelta(days=2 * period_days)).isoformat()

                # 이번 기간 리뷰 로드
                sql_this = """
                    SELECT r.id, r.product_id, r.source::text, r.reviewer_type::text, r.review_text, r.rating, 
                           r.review_date::text, r.sentiment::text, r.sentiment_score, 
                           COALESCE(array_agg(k.keyword) FILTER (WHERE k.keyword IS NOT NULL), '{}') AS keywords,
                           r.issue_type::text, r.ai_summary, r.created_at, r.review_id,
                           r.score_ingredients, r.score_formulation, r.score_container
                    FROM public.reviews r
                    LEFT JOIN public.review_keywords rk ON r.id = rk.review_id
                    LEFT JOIN public.keywords k ON rk.keyword_id = k.id
                    WHERE r.review_date >= %s
                """
                params_this = [start_date_this_week]
                if product_id:
                    sql_this += " AND r.product_id = %s"
                    params_this.append(product_id)
                sql_this += " GROUP BY r.id"
                cursor.execute(sql_this, params_this)
                rows_this = cursor.fetchall()
                reviews_this = [{
                    "id": str(r[0]), "product_id": str(r[1]), "source": r[2], "reviewer_type": r[3],
                    "review_text": r[4], "rating": int(r[5]), "review_date": str(r[6]), "sentiment": str(r[7]),
                    "sentiment_score": float(r[8]) if r[8] is not None else None, "keywords": list(r[9]) if r[9] is not None else [],
                    "issue_type": r[10], "ai_summary": r[11], "created_at": str(r[12]), "review_id": str(r[13]) if r[13] is not None else None,
                    "score_ingredients": float(r[14]) if r[14] is not None else 0.5,
                    "score_formulation": float(r[15]) if r[15] is not None else 0.5,
                    "score_container": float(r[16]) if r[16] is not None else 0.5
                } for r in rows_this]

                # 지난 기간 리뷰 로드 (WoW)
                sql_last = """
                    SELECT r.id, r.product_id, r.source::text, r.reviewer_type::text, r.review_text, r.rating, 
                           r.review_date::text, r.sentiment::text, r.sentiment_score, 
                           COALESCE(array_agg(k.keyword) FILTER (WHERE k.keyword IS NOT NULL), '{}') AS keywords,
                           r.issue_type::text, r.ai_summary, r.created_at, r.review_id,
                           r.score_ingredients, r.score_formulation, r.score_container
                    FROM public.reviews r
                    LEFT JOIN public.review_keywords rk ON r.id = rk.review_id
                    LEFT JOIN public.keywords k ON rk.keyword_id = k.id
                    WHERE r.review_date >= %s AND r.review_date < %s
                """
                params_last = [start_date_last_week, start_date_this_week]
                if product_id:
                    sql_last += " AND r.product_id = %s"
                    params_last.append(product_id)
                sql_last += " GROUP BY r.id"
                cursor.execute(sql_last, params_last)
                rows_last = cursor.fetchall()
                cursor.close()
                reviews_last = [{
                    "id": str(r[0]), "product_id": str(r[1]), "source": r[2], "reviewer_type": r[3],
                    "review_text": r[4], "rating": int(r[5]), "review_date": str(r[6]), "sentiment": str(r[7]),
                    "sentiment_score": float(r[8]) if r[8] is not None else None, "keywords": list(r[9]) if r[9] is not None else [],
                    "issue_type": r[10], "ai_summary": r[11], "created_at": str(r[12]), "review_id": str(r[13]) if r[13] is not None else None,
                    "score_ingredients": float(r[14]) if r[14] is not None else 0.5,
                    "score_formulation": float(r[15]) if r[15] is not None else 0.5,
                    "score_container": float(r[16]) if r[16] is not None else 0.5
                } for r in rows_last]

            except Exception as e:
                print(f"[DashboardService] Cloud SQL 통계 데이터 fetch 실패, 로컬 Mock 데이터 전환: {e}")
                reviews_this, reviews_last = self._get_mock_reviews_split(product_id, period_days)
        else:
            reviews_this, reviews_last = self._get_mock_reviews_split(product_id, period_days)

        # 3. 통계 집계 연산 수행 (자가 치유 파싱 적용)
        this_stats = self._aggregate_reviews(reviews_this)
        last_stats = self._aggregate_reviews(reviews_last)

        # 4. 상품명 탐색
        product_name = "전체 제품 합산"
        if product_id:
            if self.conn is not None:
                try:
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT product_name FROM public.products WHERE id = %s", [product_id])
                    row = cursor.fetchone()
                    cursor.close()
                    if row:
                        product_name = row[0]
                except Exception:
                    pass
            
            if product_name == "전체 제품 합산":
                for p in MOCK_PRODUCTS:
                    if p["id"] == product_id:
                        product_name = p.get("product_name", p.get("brand_name", "") + " " + p.get("product_name", ""))
                        break

        # 5. Gemini 2.0-flash / Rule-based 실시간 브리핑 요약 획득
        briefing = ai_service.generate_trend_briefing(this_stats, last_stats, product_name)

        # 6. 최종 통계 JSON 데이터 조립
        statistics_response = {
            "product_id": product_id,
            "period": period_days,
            "total_reviews": this_stats["total_reviews"],
            "average_rating": this_stats["average_rating"],
            "sentiment_breakdown": this_stats["sentiment_breakdown"],
            "attribute_scores": this_stats["attribute_scores"],
            "ai_briefing": briefing
        }

        # 7. 인메모리 캐시 갱신
        self._stats_cache[cache_key] = (time.time(), statistics_response)
        print(f"[DashboardService] 신규 캐시 저장 완료: {cache_key}")
        
        return statistics_response
