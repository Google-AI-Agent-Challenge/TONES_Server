"""
DashboardRepository — 대시보드 통계 전담 DB 쿼리 레이어
"""
from typing import Optional, List
from datetime import datetime, timedelta
from app.database.mock_data import MOCK_REVIEWS, MOCK_PRODUCTS


class DashboardRepository:
    def __init__(self, db_conn=None):
        self.conn = db_conn

    def fetch_reviews_for_period(self, product_id: Optional[str], start_date: str,
                                 end_date: Optional[str] = None) -> list:
        """특정 기간의 리뷰 통계 데이터 조회 (summary/insights용 간소화 쿼리)"""
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                sql = "SELECT id, product_id, rating, sentiment, ai_summary, score_ingredients, score_formulation, score_container, is_priority_review FROM public.reviews WHERE review_date >= %s"
                params = [start_date]
                if end_date:
                    sql += " AND review_date < %s"
                    params.append(end_date)
                if product_id:
                    sql += " AND product_id = %s"
                    params.append(product_id)
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                cursor.close()
                return [{
                    "id": str(r[0]), "product_id": str(r[1]), "rating": int(r[2]), "sentiment": str(r[3]),
                    "ai_summary": r[4],
                    "score_ingredients": float(r[5]) if r[5] is not None else 0.5,
                    "score_formulation": float(r[6]) if r[6] is not None else 0.5,
                    "score_container": float(r[7]) if r[7] is not None else 0.5,
                    "is_priority_review": bool(r[8]) if r[8] is not None else False
                } for r in rows]
            except Exception as e:
                print(f"[DashboardRepository.fetch_reviews_for_period] DB 조회 실패: {e}")
        return []

    def fetch_reviews_full_for_period(self, product_id: Optional[str], start_date: str,
                                      end_date: Optional[str] = None) -> list:
        """특정 기간의 리뷰 전체 컬럼 조회 (AI 브리핑/통계 통합용)"""
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                sql = """
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
                params = [start_date]
                if end_date:
                    sql += " AND r.review_date < %s"
                    params.append(end_date)
                if product_id:
                    sql += " AND r.product_id = %s"
                    params.append(product_id)
                sql += " GROUP BY r.id"
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                cursor.close()
                return [{
                    "id": str(r[0]), "product_id": str(r[1]), "source": r[2], "reviewer_type": r[3],
                    "review_text": r[4], "rating": int(r[5]), "review_date": str(r[6]), "sentiment": str(r[7]),
                    "sentiment_score": float(r[8]) if r[8] is not None else None,
                    "keywords": list(r[9]) if r[9] is not None else [],
                    "issue_type": r[10], "ai_summary": r[11],
                    "created_at": str(r[12]), "review_id": str(r[13]) if r[13] is not None else None,
                    "score_ingredients": float(r[14]) if r[14] is not None else 0.5,
                    "score_formulation": float(r[15]) if r[15] is not None else 0.5,
                    "score_container": float(r[16]) if r[16] is not None else 0.5
                } for r in rows]
            except Exception as e:
                print(f"[DashboardRepository.fetch_reviews_full_for_period] DB 조회 실패: {e}")
        return []

    def fetch_trending_keywords(self, product_id: Optional[str], start_date: str, limit: int = 5) -> list:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                sql = """
                    SELECT k.keyword, COUNT(rk.review_id) as cnt
                    FROM public.review_keywords rk
                    JOIN public.keywords k ON rk.keyword_id = k.id
                    JOIN public.reviews r ON rk.review_id = r.id
                    WHERE r.review_date >= %s
                """
                params = [start_date]
                if product_id:
                    sql += " AND r.product_id = %s"
                    params.append(product_id)
                sql += f" GROUP BY k.keyword ORDER BY cnt DESC LIMIT {limit}"
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                cursor.close()
                return [{"keyword": r[0], "count": r[1]} for r in rows]
            except Exception as e:
                print(f"[DashboardRepository.fetch_trending_keywords] DB 조회 실패: {e}")
        return []

    def fetch_negative_trend(self, product_id: Optional[str], start_date: str) -> dict:
        """날짜별 부정 리뷰 건수 반환 {date: count}"""
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                sql = "SELECT review_date::text, COUNT(id) FROM public.reviews WHERE review_date >= %s AND sentiment = 'negative'"
                params = [start_date]
                if product_id:
                    sql += " AND product_id = %s"
                    params.append(product_id)
                sql += " GROUP BY review_date ORDER BY review_date ASC"
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                cursor.close()
                return {r[0]: r[1] for r in rows}
            except Exception as e:
                print(f"[DashboardRepository.fetch_negative_trend] DB 조회 실패: {e}")
        return {}

    def fetch_product_name(self, product_id: str) -> Optional[str]:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT product_name FROM public.products WHERE id = %s", [product_id])
                row = cursor.fetchone()
                cursor.close()
                if row:
                    return row[0]
            except Exception:
                pass
        for p in MOCK_PRODUCTS:
            if p["id"] == product_id:
                return p.get("product_name", "")
        return None

    def get_mock_reviews_split(self, product_id: Optional[str], period_days: int):
        """오프라인 환경용 리뷰 기간 분할"""
        today = datetime.now().date()
        start_this = today - timedelta(days=period_days)
        start_last = today - timedelta(days=2 * period_days)
        reviews_this, reviews_last = [], []
        for r in MOCK_REVIEWS:
            if product_id and r.get("product_id") != product_id:
                continue
            r_date_str = r.get("review_date", "")
            try:
                r_date = datetime.fromisoformat(r_date_str).date() if "T" in r_date_str else datetime.strptime(r_date_str, "%Y-%m-%d").date()
            except Exception:
                r_date = today
            if r_date >= start_this:
                reviews_this.append(r)
            elif r_date >= start_last:
                reviews_last.append(r)
        return reviews_this, reviews_last
