import re
import time
from typing import Optional, List
from datetime import datetime, timedelta
from app.domains.dashboard.repository import DashboardRepository
from app.core.cache import dashboard_cache

_TTL_SUMMARY = 300
_TTL_KEYWORDS = 300
_TTL_TREND = 300
_TTL_INSIGHTS = 300
_TTL_AI_BRIEFING = 1800

_CATEGORY_KEYWORD_MAP = {
    "ingredients": [
        "성분", "자극", "트러블", "진정", "피부결", "여드름", "붉", "순해", "순하", "민감",
        "피부 고민", "자극성", "피부진정", "저자극", "보습", "재구매", "산뜻", "피부결 만족",
        "효과", "효능", "피부 개선", "피부 변화", "각질", "피부톤", "미백", "수분감", "모공",
        "피부 진정", "트러블케어", "진정효과", "보습력", "리뷰", "만족", "추천", "개선", "실망", "별로",
    ],
    "formulation": [
        "제형", "흡수", "끈적", "발림", "촉촉", "수분", "밀림", "밀려", "발리", "보풀",
        "찢", "두께", "밀착", "에센스", "닦토", "부드러", "사용감", "질감", "겉돔", "번들",
        "발라", "바르", "발림성", "텍스처", "피부 흡수", "흡수력",
    ],
    "container": [
        "용기", "뚜껑", "집게", "패키지", "디자인", "포장", "캡", "불편", "편리",
        "용기불량", "파손", "누액", "펌프", "새는", "불량", "도포구", "용기 디자인",
    ],
}

_NEGATIVE_SIGNAL_KWS = [
    "자극", "트러블", "여드름", "붉", "불편", "끈적", "밀림", "밀려", "보풀", "찢",
    "뚜껑 불편", "집게 불편", "따가", "뒤집", "파손", "누액", "새는", "불량", "실망", "별로",
]


class DashboardService:
    def __init__(self, db_conn=None):
        self.repo = DashboardRepository(db_conn)

    # ── 내부 유틸리티 ────────────────────────────────────────────────────────

    def _extract_scores_from_summary(self, ai_summary: str, review_dict: dict = None) -> dict:
        scores = {"ingredients_skin_concerns_score": 0.5, "formulation_spreadability_score": 0.5, "container_design_score": 0.5}
        parsed_ok = False
        if ai_summary:
            try:
                m_ing = re.search(r"\[성분/고민\]:\s*([0-9.]+)", ai_summary)
                m_form = re.search(r"\[제형/발림\]:\s*([0-9.]+)", ai_summary)
                m_cont = re.search(r"\[용기/디자인\]:\s*([0-9.]+)", ai_summary)
                if m_ing:
                    scores["ingredients_skin_concerns_score"] = float(m_ing.group(1)); parsed_ok = True
                if m_form:
                    scores["formulation_spreadability_score"] = float(m_form.group(1)); parsed_ok = True
                if m_cont:
                    scores["container_design_score"] = float(m_cont.group(1)); parsed_ok = True
            except Exception as e:
                print(f"[DashboardService] 감성 점수 파싱 오류: {e}")
        if not parsed_ok and review_dict:
            rating = review_dict.get("rating", 3)
            text = review_dict.get("review_text") or review_dict.get("content") or ""
            bases = {5: (0.88, 0.94, 0.74), 4: (0.72, 0.80, 0.60), 3: (0.52, 0.56, 0.40), 2: (0.30, 0.36, 0.22), 1: (0.12, 0.14, 0.08)}
            ing_base, form_base, cont_base = bases.get(rating, (0.50, 0.50, 0.50))
            ing_pos = ["순해", "순하고", "자극 없", "진정", "트러블 안", "여드름 안", "붉은기", "완화", "개선", "안심"]
            ing_neg = ["트러블", "뒤집", "자극", "여드름", "간지러", "따가", "붉", "좁쌀", "화끈", "자극감"]
            form_pos = ["촉촉", "발림", "제형", "밀착", "보습", "부드러", "닦토", "흡수", "수분감"]
            form_neg = ["끈적", "밀려", "두껍", "거칠", "건조", "보풀", "찢어", "흡수 안", "푸석", "밀림"]
            cont_pos = ["용기", "디자인", "집게", "위생", "뚜껑", "패키지", "예뻐", "편리"]
            cont_neg = ["불편", "새요", "샘", "새고", "흐르고", "집게 분실", "뚜껑 잘 안"]
            ing_score = min(0.96, ing_base + 0.12) if any(k in text for k in ing_pos) else (max(0.04, ing_base - 0.22) if any(k in text for k in ing_neg) else ing_base)
            form_score = min(0.96, form_base + 0.12) if any(k in text for k in form_pos) else (max(0.04, form_base - 0.22) if any(k in text for k in form_neg) else form_base)
            cont_score = min(0.96, cont_base + 0.12) if any(k in text for k in cont_pos) else (max(0.04, cont_base - 0.22) if any(k in text for k in cont_neg) else cont_base)
            scores["ingredients_skin_concerns_score"] = round(ing_score, 2)
            scores["formulation_spreadability_score"] = round(form_score, 2)
            scores["container_design_score"] = round(cont_score, 2)
        return scores

    def _aggregate_reviews(self, reviews: list) -> dict:
        total = len(reviews)
        if total == 0:
            return {"total_reviews": 0, "average_rating": 0.0,
                    "sentiment_breakdown": {"positive": 0, "neutral": 0, "negative": 0},
                    "attribute_scores": {"ingredients": 0.5, "formulation": 0.5, "container": 0.5}}
        ratings_sum = 0
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
        sum_ing = sum_form = sum_cont = 0.0
        for r in reviews:
            ratings_sum += r.get("rating", 0)
            sent = r.get("sentiment")
            if sent in sentiment_counts:
                sentiment_counts[sent] += 1
            else:
                sentiment_counts["neutral"] += 1
            ing_val = r.get("score_ingredients")
            form_val = r.get("score_formulation")
            cont_val = r.get("score_container")
            if ing_val is not None and form_val is not None and cont_val is not None:
                sum_ing += float(ing_val); sum_form += float(form_val); sum_cont += float(cont_val)
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

    def _categorize_keyword(self, keyword: str) -> str:
        for category, kws in _CATEGORY_KEYWORD_MAP.items():
            for kw in kws:
                if kw in keyword or keyword in kw:
                    return category
        return "unknown"

    def _is_negative_keyword(self, keyword: str) -> bool:
        return any(neg in keyword for neg in _NEGATIVE_SIGNAL_KWS)

    def _build_insight_text(self, category: str, related_keywords: list, change: float, score: float, keyword_counts: dict = None) -> str:
        def _fmt_kw(k):
            return f"'{k}'({keyword_counts[k]}회)" if keyword_counts and k in keyword_counts else f"'{k}'"
        label = {"ingredients": "성분·피부 진정", "formulation": "제형·발림성", "container": "용기·편의성"}.get(category, category)
        if not related_keywords:
            return f"{label} 관련 만족도가 전기 대비 {change:+.1f}%p {'개선' if change > 0 else '하락' if change < 0 else '변화 없음'}되었습니다."
        neg_kws = [k for k in related_keywords if self._is_negative_keyword(k)]
        pos_kws = [k for k in related_keywords if not self._is_negative_keyword(k)]
        if change == 0.0:
            kws_str = neg_kws or pos_kws or related_keywords
            kwl = ", ".join(_fmt_kw(k) for k in kws_str)
            return f"급상승 키워드 {kwl} 관련 {label} 만족도는 전기 대비 큰 변동 없이 안정적으로 유지되었습니다."
        if neg_kws and change < 0:
            return f"급상승 키워드 {', '.join(_fmt_kw(k) for k in neg_kws)}가 {label} 관련 불만 반응과 연관됩니다. 만족도 {change:+.1f}%p 하락했습니다."
        if neg_kws and change >= 0:
            return f"급상승 키워드 {', '.join(_fmt_kw(k) for k in neg_kws)} 언급이 늘었으나, {label} 점수는 유지되거나 소폭 개선되었습니다. (+{change:.1f}%p)"
        if pos_kws and change > 0:
            return f"급상승 키워드 {', '.join(_fmt_kw(k) for k in pos_kws)}가 {label} 만족도 개선을 뒷받침합니다. (만족도 {change:+.1f}%p)"
        if pos_kws and change < 0:
            return f"급상승 키워드 {', '.join(_fmt_kw(k) for k in pos_kws)} 언급이 있었으나 {label} 전반적 만족도는 하락했습니다. ({change:+.1f}%p)"
        kws_str = ", ".join(_fmt_kw(k) for k in related_keywords)
        return f"급상승 키워드 {kws_str}가 {label} 관련 이슈와 연관되며 전기 대비 {change:+.1f}%p 변동을 기록했습니다."

    # ── 공개 메서드 ──────────────────────────────────────────────────────────

    def fetch_dashboard_summary(self, product_id: Optional[str], period_days: int) -> dict:
        cache_key = ("summary", product_id, period_days)
        hit, cached = dashboard_cache.get(cache_key, _TTL_SUMMARY)
        if hit:
            return cached

        today = datetime.now().date()
        start_this = (today - timedelta(days=period_days)).isoformat()
        start_last = (today - timedelta(days=2 * period_days)).isoformat()

        reviews_this = self.repo.fetch_reviews_for_period(product_id, start_this)
        reviews_last = self.repo.fetch_reviews_for_period(product_id, start_last, start_this)
        if not reviews_this and not reviews_last:
            reviews_this, reviews_last = self.repo.get_mock_reviews_split(product_id, period_days)

        this_agg = self._aggregate_reviews(reviews_this)
        last_agg = self._aggregate_reviews(reviews_last)
        review_diff = this_agg["total_reviews"] - last_agg["total_reviews"]
        rating_diff = round(this_agg["average_rating"] - last_agg["average_rating"], 2)
        neg_count_this = this_agg["sentiment_breakdown"].get("negative", 0)
        neg_count_last = last_agg["sentiment_breakdown"].get("negative", 0)
        neg_rate_this = round(neg_count_this / this_agg["total_reviews"] * 100, 1) if this_agg["total_reviews"] > 0 else 0.0
        neg_rate_last = round(neg_count_last / last_agg["total_reviews"] * 100, 1) if last_agg["total_reviews"] > 0 else 0.0
        neg_diff = round(neg_rate_this - neg_rate_last, 1)

        urgent_reviews = [r for r in reviews_this if r.get("is_priority_review") is True]
        urgent_summary = [{"id": r.get("id"), "summary": (r.get("ai_summary", "") or "")[:60] + "...", "rating": r.get("rating")} for r in urgent_reviews[:3]]

        result = {
            "total_reviews": this_agg["total_reviews"],
            "total_reviews_diff": review_diff,
            "average_rating": this_agg["average_rating"],
            "average_rating_diff": rating_diff,
            "negative_reviews_count": neg_count_this,
            "negative_reviews_rate": neg_rate_this,
            "negative_reviews_rate_diff": neg_diff,
            "priority_reviews_count": len(urgent_reviews),
            "urgent_reviews_summary": urgent_summary
        }
        dashboard_cache.set(cache_key, result)
        return result

    def fetch_trending_keywords(self, product_id: Optional[str], period_days: int) -> List[dict]:
        cache_key = ("trending_keywords", product_id, period_days)
        hit, cached = dashboard_cache.get(cache_key, _TTL_KEYWORDS)
        if hit:
            return cached
        today = datetime.now().date()
        start_this = (today - timedelta(days=period_days)).isoformat()
        result = self.repo.fetch_trending_keywords(product_id, start_this)
        if result:
            dashboard_cache.set(cache_key, result)
            return result
        # Mock 폴백
        reviews_this, _ = self.repo.get_mock_reviews_split(product_id, period_days)
        keywords_count = {}
        for r in reviews_this:
            for kw in r.get("keywords", []):
                keywords_count[kw] = keywords_count.get(kw, 0) + 1
        result = [{"keyword": k, "count": v} for k, v in sorted(keywords_count.items(), key=lambda x: x[1], reverse=True)[:5]]
        dashboard_cache.set(cache_key, result)
        return result

    def fetch_negative_trend(self, product_id: Optional[str], period_days: int) -> List[dict]:
        cache_key = ("negative_trend", product_id, period_days)
        hit, cached = dashboard_cache.get(cache_key, _TTL_TREND)
        if hit:
            return cached
        today = datetime.now().date()
        trend_dict = {(today - timedelta(days=i)).isoformat(): 0 for i in range(period_days + 1)}
        start_this = (today - timedelta(days=period_days)).isoformat()
        db_data = self.repo.fetch_negative_trend(product_id, start_this)
        for date_str, count in db_data.items():
            if date_str in trend_dict:
                trend_dict[date_str] = count
        if sum(trend_dict.values()) == 0:
            reviews_this, _ = self.repo.get_mock_reviews_split(product_id, period_days)
            for r in reviews_this:
                if r.get("sentiment") == "negative":
                    r_date = r.get("review_date", "")[:10]
                    if r_date in trend_dict:
                        trend_dict[r_date] += 1
        result = [{"date": k, "count": v} for k, v in sorted(trend_dict.items())]
        dashboard_cache.set(cache_key, result)
        return result

    def fetch_insights(self, product_id: Optional[str], period_days: int) -> dict:
        cache_key = ("insights", product_id, period_days)
        hit, cached = dashboard_cache.get(cache_key, _TTL_INSIGHTS)
        if hit:
            return cached
        today = datetime.now().date()
        start_this = (today - timedelta(days=period_days)).isoformat()
        start_last = (today - timedelta(days=2 * period_days)).isoformat()

        reviews_this_raw = self.repo.fetch_reviews_for_period(product_id, start_this)
        reviews_last_raw = self.repo.fetch_reviews_for_period(product_id, start_last, start_this)
        if not reviews_this_raw and not reviews_last_raw:
            reviews_this_raw, reviews_last_raw = self.repo.get_mock_reviews_split(product_id, period_days)

        this_agg = self._aggregate_reviews(reviews_this_raw)
        last_agg = self._aggregate_reviews(reviews_last_raw)
        t_attr = this_agg["attribute_scores"]
        l_attr = last_agg["attribute_scores"]

        trending = self.fetch_trending_keywords(product_id, period_days)
        category_keywords: dict = {"ingredients": [], "formulation": [], "container": []}
        keyword_counts: dict = {}
        for item in trending:
            keyword_counts[item["keyword"]] = item["count"]
            cat = self._categorize_keyword(item["keyword"])
            if cat in category_keywords:
                category_keywords[cat].append(item["keyword"])

        _LABELS = {"ingredients": "성분 및 피부 진정", "formulation": "제형 흡수력 및 발림성", "container": "용기 불량 및 편리성"}

        def _build_entry(category: str, this_score: float, last_score: float) -> dict:
            score = round(this_score * 100, 1)
            change = round((this_score - last_score) * 100, 1)
            related_strs = category_keywords.get(category, [])
            related = [{"keyword": kw, "count": keyword_counts.get(kw, 0)} for kw in related_strs]
            if change > 0:
                sentiment = "positive"; change_description = f"+{change:.1f}%p 개선"
            elif change < 0:
                sentiment = "negative"; change_description = f"{change:.1f}%p 하락"
            else:
                sentiment = "neutral"; change_description = "큰 변화 없음"
            return {
                "label": _LABELS.get(category, category),
                "score": score,
                "change": change,
                "change_description": change_description,
                "sentiment": sentiment,
                "related_keywords": related,
                "insight_text": self._build_insight_text(category, related_strs, change, score, keyword_counts),
            }

        result = {
            "ingredients": _build_entry("ingredients", t_attr["ingredients"], l_attr["ingredients"]),
            "formulation": _build_entry("formulation", t_attr["formulation"], l_attr["formulation"]),
            "container": _build_entry("container", t_attr["container"], l_attr["container"]),
        }
        dashboard_cache.set(cache_key, result)
        return result

    async def get_dashboard_statistics(self, product_id: Optional[str], period_days: int, ai_service) -> dict:
        cache_key = ("ai_briefing", product_id, period_days)
        hit, cached = dashboard_cache.get(cache_key, _TTL_AI_BRIEFING)
        if hit:
            return cached

        today = datetime.now().date()
        start_this = (today - timedelta(days=period_days)).isoformat()
        start_last = (today - timedelta(days=2 * period_days)).isoformat()

        reviews_this = self.repo.fetch_reviews_full_for_period(product_id, start_this)
        reviews_last = self.repo.fetch_reviews_full_for_period(product_id, start_last, start_this)
        if not reviews_this and not reviews_last:
            reviews_this, reviews_last = self.repo.get_mock_reviews_split(product_id, period_days)

        this_stats = self._aggregate_reviews(reviews_this)
        last_stats = self._aggregate_reviews(reviews_last)

        product_name = "전체 제품 합산"
        if product_id:
            product_name = self.repo.fetch_product_name(product_id) or product_name

        briefing = ai_service.generate_trend_briefing(this_stats, last_stats, product_name)

        statistics_response = {
            "product_id": product_id,
            "period": period_days,
            "total_reviews": this_stats["total_reviews"],
            "average_rating": this_stats["average_rating"],
            "sentiment_breakdown": this_stats["sentiment_breakdown"],
            "attribute_scores": this_stats["attribute_scores"],
            "ai_briefing": briefing
        }
        dashboard_cache.set(cache_key, statistics_response)
        return statistics_response

    def create_dashboard_report(self, product_id: Optional[str], period_days: int, report_type: str = "general") -> dict:
        summary = self.fetch_dashboard_summary(product_id, period_days)
        insights = self.fetch_insights(product_id, period_days)
        keywords = self.fetch_trending_keywords(product_id, period_days)

        def _fmt(item: dict) -> str:
            change_val = item['change']
            if round(abs(change_val), 1) == 0.0:
                return "품질 이슈 없이 견고하고 안정적인 만족도를 유지하고 있습니다."
            return f"{item['score']:.1f}% (전기 대비 {change_val:+.1f}%p)"

        report_markdown = f"""# TONES AI 분석 보고서

- **생성시점**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **분석기간**: 최근 {period_days}일
- **조회대상**: {product_id if product_id else "전체 상품 합산"}

## 1. 대시보드 성과 요약
- **전체 리뷰 수**: {summary['total_reviews']}건 (WoW 대비 {summary['total_reviews_diff']:+d}건 변동)
- **평균 만족도 별점**: {summary['average_rating']}/5.0 (WoW 대비 {summary['average_rating_diff']:+.2f}점 변동)
- **부정 리뷰 수**: {summary['negative_reviews_count']}건 (비율: {summary['negative_reviews_rate']}%)

## 2. 3대 핵심 품질 속성 만족도
- **성분 및 피부진정 효과 만족도**: {_fmt(insights['ingredients'])}
- **제형 흡수력 및 발림성 만족도**: {_fmt(insights['formulation'])}
- **용기 불량 및 편리성 만족도**: {_fmt(insights['container'])}

## 3. 핵심 유의어 및 급상승 키워드 Top 5
"""
        for i, kw in enumerate(keywords):
            report_markdown += f"{i+1}. **{kw['keyword']}** ({kw['count']}회 언급)\n"

        return {
            "success": True,
            "report_id": f"rep_{int(time.time())}",
            "report_markdown": report_markdown,
            "raw_data": {"summary": summary, "insights": insights, "keywords": keywords}
        }

    # DashboardService 하위 호환용 — products/layout 도메인이 아직 DashboardService를 참조하는 경우를 위한 위임 메서드
    def fetch_products(self) -> list:
        from app.domains.products.service import ProductService
        return ProductService(self.repo.conn).fetch_products()

    def save_layout(self, user_token: str, pinned_widget) -> bool:
        from app.domains.layout.service import LayoutService
        return LayoutService(self.repo.conn).save_layout(user_token, pinned_widget)

    def load_layout(self, user_token: str):
        from app.domains.layout.service import LayoutService
        return LayoutService(self.repo.conn).load_layout(user_token)
