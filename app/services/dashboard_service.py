import uuid
from typing import List, Optional
from datetime import datetime, timedelta
from supabase import Client

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

    def fetch_products(self) -> List[dict]:
        if self.supabase is not None:
            try:
                response = self.supabase.table("products").select("id, brand_name, product_name, category, target_skin, created_at").order("product_name", ascending=True).execute()
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
                ).order("review_date", ascending=False).limit(limit).execute()
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
                ).or_(or_filter).order("review_date", ascending=False).limit(limit).execute()
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
                ).eq("product_id", product_id).order("review_date", ascending=False).limit(limit).execute()
                if response.data:
                    return response.data
            except Exception as e:
                print(f"[DashboardService.fetch_reviews_by_product] Supabase fetch 실패, 로컬 Mock 데이터로 폴백: {e}")

        # Local mock filter
        filtered = [r for r in MOCK_REVIEWS if r["product_id"] == product_id]
        return filtered[:limit] if filtered else MOCK_REVIEWS[:limit]
