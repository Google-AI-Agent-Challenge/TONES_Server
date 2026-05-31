import uuid
import re
from typing import List, Optional
from datetime import datetime, timedelta
from supabase import Client
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
    def __init__(self, supabase_client: Client | None):
        self.supabase = supabase_client
        self._stats_cache = {}  # TTL 캐시 보관소: {(product_id, period_days): (timestamp, stats_data)}

    def fetch_products(self) -> List[dict]:
        if self.supabase is not None:
            try:
                response = self.supabase.table("products").select("id, brand_name, product_name, category, target_skin, created_at").order("product_name", desc=False).execute()
                if response.data:
                    return response.data
            except Exception as e:
                print(f"[DashboardService.fetch_products] Supabase fetch 실패, 로컬 Mock 데이터로 폴백: {e}")
        return MOCK_PRODUCTS

    def fetch_latest_reviews(self, limit: int = 20) -> List[dict]:
        if self.supabase is not None:
            try:
                response = self.supabase.table("reviews").select(
                    "id, product_id, source, reviewer_type, review_text, rating, review_date, sentiment, sentiment_score, keywords, issue_type, ai_summary, created_at, review_id, products(id, brand_name, product_name, category, target_skin)"
                ).order("review_date", desc=True).limit(limit).execute()
                if response.data:
                    return response.data
            except Exception as e:
                print(f"[DashboardService.fetch_latest_reviews] Supabase fetch 실패, 로컬 Mock 데이터로 폴백: {e}")
        return MOCK_REVIEWS[:limit]

    def fetch_reviews_by_keywords(self, keywords: List[str], limit: int = 20) -> List[dict]:
        if not keywords:
            return self.fetch_latest_reviews(limit)

        if self.supabase is not None:
            try:
                or_filter = ",".join([f"review_text.ilike.%{kw}%" for kw in keywords])
                response = self.supabase.table("reviews").select(
                    "id, product_id, source, reviewer_type, review_text, rating, review_date, sentiment, sentiment_score, keywords, issue_type, ai_summary, created_at, review_id, products(id, brand_name, product_name, category, target_skin)"
                ).or_(or_filter).order("review_date", desc=True).limit(limit).execute()
                if response.data:
                    return response.data
            except Exception as e:
                print(f"[DashboardService.fetch_reviews_by_keywords] Supabase fetch 실패, 로컬 Mock 데이터로 폴백: {e}")

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
        if self.supabase is not None:
            try:
                response = self.supabase.table("reviews").select(
                    "id, product_id, source, reviewer_type, review_text, rating, review_date, sentiment, sentiment_score, keywords, issue_type, ai_summary, created_at, review_id, products(id, brand_name, product_name, category, target_skin)"
                ).eq("product_id", product_id).order("review_date", desc=True).limit(limit).execute()
                if response.data:
                    return response.data
            except Exception as e:
                print(f"[DashboardService.fetch_reviews_by_product] Supabase fetch 실패, 로컬 Mock 데이터로 폴백: {e}")

        # Local mock filter
        filtered = [r for r in MOCK_REVIEWS if r["product_id"] == product_id]
        return filtered[:limit] if filtered else MOCK_REVIEWS[:limit]

    async def process_and_save_reviews(self, reviews: List[ReviewCreate], ai_service: AIService) -> dict:
        """
        크롤링 리뷰 AI 분석 파이프라인 통합 적재 트랜잭션 메서드
        1. 원시 리뷰에 대해 ABSA 엔진 구동
        2. Pinecone 벡터 임베딩 생성 및 upsert
        3. Supabase DB 적재 (자가 치유 및 롤백 정책 적용)
        """
        success_count = 0
        failure_count = 0
        processed_ids = []

        for review in reviews:
            # 1. 고유 ID 생성 (UUID 검증 포함)
            try:
                review_id_val = str(uuid.UUID(review.review_id)) if review.review_id else str(uuid.uuid4())
            except Exception:
                review_id_val = str(uuid.uuid5(uuid.NAMESPACE_URL, str(review.review_id)))

            row_uuid = str(uuid.uuid4())

            try:
                # 2. Gemini ABSA 엔진 실행
                absa_res = ai_service.analyze_review_absa(review.content)

                # 3. Pinecone 벡터 DB 적재용 메타데이터 빌드 및 업로드
                metadata = {
                    "product_id": review.product_id,
                    "source": review.source,
                    "rating": review.rating,
                    "review_date": review.review_date or datetime.now().date().isoformat(),
                    "sentiment": absa_res["overall_sentiment"],
                    "issue_type": absa_res["issue_type"],
                    "ai_summary": absa_res["ai_summary"]
                }
                
                # Pinecone upsert 수행
                upsert_ok = ai_service.upsert_review_vector(row_uuid, review.content, metadata)
                if not upsert_ok:
                    print(f"[DashboardService] Pinecone 벡터 적재 오류 발생 (건너뜀 또는 에러 처리): {row_uuid}")

                # 4. Supabase DB 적재 레코드 빌드
                supabase_record = {
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
                    "score_ingredients": absa_res["ingredients_skin_concerns_score"],
                    "score_formulation": absa_res["formulation_spreadability_score"],
                    "score_container": absa_res["container_design_score"]
                }

                # 5. Supabase 트랜잭션 수행 (자가 치유 및 롤백 패턴 적용)
                if self.supabase is not None:
                    try:
                        # [시도 1] 개별 컬럼(score_ingredients 등)을 포함하여 인서트 시도
                        self.supabase.table("reviews").insert(supabase_record).execute()
                        print(f"[DashboardService] Supabase 적재 성공 (개별 컬럼 포함): {row_uuid}")
                    except Exception as e:
                        # [시도 2] 자가 치유(Self-Healing) 작동: 컬럼 누락 시 구조화 패키징
                        error_str = str(e)
                        if "column" in error_str or "does not exist" in error_str or "404" in error_str:
                            print(f"[DashboardService] 개별 감성 점수 컬럼 누락 감지, 자가 치유(Self-Healing) 실행: {e}")
                            scores_formatted = (
                                f"[성분/고민]: {absa_res['ingredients_skin_concerns_score']:.2f} | "
                                f"[제형/발림]: {absa_res['formulation_spreadability_score']:.2f} | "
                                f"[용기/디자인]: {absa_res['container_design_score']:.2f}"
                            )
                            healed_record = supabase_record.copy()
                            healed_record["ai_summary"] = f"{scores_formatted} \n요약: {absa_res['ai_summary']}"
                            
                            # 오류 방지용 속성 점수 필드들 제외
                            healed_record.pop("score_ingredients", None)
                            healed_record.pop("score_formulation", None)
                            healed_record.pop("score_container", None)
                            
                            try:
                                self.supabase.table("reviews").insert(healed_record).execute()
                                print(f"[DashboardService] 자가 치유된 레코드 Supabase 적재 성공: {row_uuid}")
                            except Exception as final_err:
                                print(f"[DashboardService] 자가 치유 후 최종 DB 적재 실패로 Pinecone 롤백 실행: {final_err}")
                                ai_service.delete_review_vector(row_uuid)
                                raise final_err
                        else:
                            print(f"[DashboardService] Supabase 기타 DB 오류 발생으로 Pinecone 롤백 실행: {e}")
                            ai_service.delete_review_vector(row_uuid)
                            raise e
                else:
                    # 오프라인 및 로컬 테스트 환경 시뮬레이션
                    print(f"[DashboardService] Supabase 미설정 상태, 가상 메모리 적재 처리: {row_uuid}")
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
                
                # 평점별 기본 감성 점수 매핑 (화장품 만족도 특성에 맞춘 차별화된 베이스라인 배정)
                # 용기/디자인은 일반적으로 Tweezers(집게) 유실/액샘 불만이 많으므로 상대적으로 낮게 시작
                ing_base = 0.50
                form_base = 0.50
                cont_base = 0.50

                if rating == 5:
                    ing_base = 0.88
                    form_base = 0.94  # 제형/발림성은 5점 리뷰에서 극찬 비율이 매우 높음
                    cont_base = 0.74  # 5점이어도 용기에 대한 불만은 잠재되어 있는 편
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

                # 확장된 긍정/부정 키워드 사전 (한국어 화장품 VOC 특화)
                ing_pos = ["순해", "순하고", "자극 없", "자극없", "진정", "트러블 안", "여드름 안", "붉은기", "완화", "개선", "피부결", "진정에", "안심", "트러블성"]
                ing_neg = ["트러블", "뒤집", "자극", "여드름", "간지러", "따가", "붉어", "좁쌀", "붉어지", "가렵", "간지", "좁쌀여드름", "피부 뒤집", "뒤집어", "화끈", "자극감"]
                
                form_pos = ["촉촉", "발림", "제형", "두께", "밀착", "보습", "에센스 많", "충분", "부드러", "닦토", "흡수", "수분감", "밀착력", "두툼", "패드 부드", "닦기 편", "닦토", "부드러운"]
                form_neg = ["끈적", "밀려", "두껍", "거칠", "건조", "보풀", "찢어", "얇아", "흡수 안", "푸석", "끈적", "밀림", "보풀", "찢어짐", "거칠", "에센스 부족", "말라"]

                cont_pos = ["용기", "디자인", "집게", "위생", "뚜껑", "패키지", "예뻐", "편리"]
                cont_neg = ["불편", "새요", "샘", "집게 불편", "뚜껑 불편", "새고", "흐르고", "위생적이지", "집게 분실", "뚜껑 잘 안"]

                # 성분/고민 점수 미세조정 (가중치 상향하여 변동폭 확대)
                if any(k in text for k in ing_pos):
                    ing_score = min(0.96, ing_score + 0.12)
                if any(k in text for k in ing_neg):
                    ing_score = max(0.04, ing_score - 0.22)

                # 제형/발림 점수 미세조정
                if any(k in text for k in form_pos):
                    form_score = min(0.96, form_score + 0.12)
                if any(k in text for k in form_neg):
                    form_score = max(0.04, form_score - 0.22)

                # 용기/디자인 점수 미세조정
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
        # WoW 이전 비교 기간
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
        import time
        
        # 1. 인메모리 TTL 캐시 확인 (60초 만료 시간 적용)
        cache_key = (product_id, period_days)
        if cache_key in self._stats_cache:
            cached_time, cached_data = self._stats_cache[cache_key]
            if time.time() - cached_time < 60:
                print(f"[DashboardService] 캐시 히트 (TTL 60s): {cache_key}")
                return cached_data

        # 2. Supabase에서 해당 제품의 리뷰 기간별 조회
        reviews_this = []
        reviews_last = []
        
        if self.supabase is not None:
            try:
                today = datetime.now().date()
                start_date_this_week = (today - timedelta(days=period_days)).isoformat()
                start_date_last_week = (today - timedelta(days=2 * period_days)).isoformat()

                # 이번 기간
                query_this = self.supabase.table("reviews").select("*").gte("review_date", start_date_this_week)
                if product_id:
                    query_this = query_this.eq("product_id", product_id)
                res_this = query_this.execute()
                reviews_this = res_this.data if res_this.data else []

                # 지난 기간 (WoW)
                query_last = self.supabase.table("reviews").select("*")\
                    .gte("review_date", start_date_last_week)\
                    .lt("review_date", start_date_this_week)
                if product_id:
                    query_last = query_last.eq("product_id", product_id)
                res_last = query_last.execute()
                reviews_last = res_last.data if res_last.data else []
            except Exception as e:
                print(f"[DashboardService] Supabase 통계 데이터 fetch 실패, 로컬 Mock 데이터 전환: {e}")
                reviews_this, reviews_last = self._get_mock_reviews_split(product_id, period_days)
        else:
            reviews_this, reviews_last = self._get_mock_reviews_split(product_id, period_days)

        # 3. 통계 집계 연산 수행 (자가 치유 파싱 적용)
        this_stats = self._aggregate_reviews(reviews_this)
        last_stats = self._aggregate_reviews(reviews_last)

        # 4. 상품명 탐색
        product_name = "전체 제품 합산"
        if product_id:
            if self.supabase is not None:
                try:
                    p_res = self.supabase.table("products").select("name").eq("id", product_id).execute()
                    if p_res.data:
                        product_name = p_res.data[0]["name"]
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

    def save_layout(self, user_token: str, pinned_widget: str | None) -> bool:
        if self.supabase is not None:
            try:
                response = self.supabase.table("user_layouts").upsert(
                    {"user_token": user_token, "pinned_widget": pinned_widget, "updated_at": datetime.now().isoformat()},
                    on_conflict="user_token"
                ).execute()
                return True
            except Exception as e:
                print(f"[DashboardService.save_layout] Supabase upsert 실패: {e}")
                return False
        return True

    def load_layout(self, user_token: str) -> str | None:
        if self.supabase is not None:
            try:
                response = self.supabase.table("user_layouts").select("pinned_widget").eq("user_token", user_token).execute()
                if response.data:
                    return response.data[0].get("pinned_widget")
            except Exception as e:
                print(f"[DashboardService.load_layout] Supabase fetch 실패: {e}")
                return None
        return None

    def fetch_reviews_by_ids(self, ids: List[str]) -> List[dict]:
        if not ids:
            return []
        if self.supabase is not None:
            try:
                response = self.supabase.table("reviews").select(
                    "id, product_id, source, reviewer_type, review_text, rating, review_date, sentiment, sentiment_score, keywords, issue_type, ai_summary, created_at, review_id, products(id, brand_name, product_name, category, target_skin)"
                ).in_("id", ids).order("review_date", desc=True).execute()
                if response.data:
                    return response.data
            except Exception as e:
                print(f"[DashboardService.fetch_reviews_by_ids] Supabase fetch 실패: {e}")
        # 오프라인 폴백
        filtered = [r for r in MOCK_REVIEWS if r["id"] in ids]
        return filtered


