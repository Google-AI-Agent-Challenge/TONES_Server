"""
ReviewRepository — reviews 테이블 전담 DB 쿼리 레이어
"""
import uuid
from typing import List, Optional
from datetime import datetime, timedelta
from app.database.mock_data import MOCK_REVIEWS, MOCK_PRODUCTS


class ReviewRepository:
    def __init__(self, db_conn=None):
        self.conn = db_conn

    def _parse_db_row_to_review(self, row) -> dict:
        """
        SQL Query 결과 Tuple을 ReviewSchema 호환 딕셔너리로 변환.

        컬럼 레이아웃 (_REVIEW_SELECT_SQL 기준, 24열):
          0-13  : 기본 리뷰 필드
          14    : is_priority_review  ← DB 신규 컬럼
          15    : analysis_status     ← DB 신규 컬럼
          16-18 : score_ingredients, score_formulation, score_container
          19-23 : p.id, brand_name, product_name, category, target_skin

        폴백 쿼리(_REVIEW_SELECT_FALLBACK_SQL, 21열)는 score 컬럼(16-18)이 없고
        product 컬럼이 16-20에 위치한다. p_idx = len(row) - 5 로 공통 처리.
        """
        # 제품 정보 파싱 (두 쿼리 모두 마지막 5열이 p.id ~ target_skin)
        prod_obj = None
        if len(row) >= 21:
            p_idx = len(row) - 5
            if row[p_idx] is not None:
                prod_obj = {
                    "id": str(row[p_idx]),
                    "brand_name": row[p_idx + 1],
                    "product_name": row[p_idx + 2],
                    "category": row[p_idx + 3],
                    "target_skin": row[p_idx + 4]
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
            # DB 신규 컬럼 (idx 14, 15) — 두 쿼리 모두 동일 위치
            "is_priority_review": bool(row[14]) if row[14] is not None else False,
            "analysis_status": str(row[15]) if row[15] is not None else None,
            "products": prod_obj
        }

        # score 컬럼은 전체 쿼리(24열)에만 존재 (idx 16-18)
        if len(row) >= 24:
            review_dict["score_ingredients"] = float(row[16]) if row[16] is not None else 0.5
            review_dict["score_formulation"] = float(row[17]) if row[17] is not None else 0.5
            review_dict["score_container"] = float(row[18]) if row[18] is not None else 0.5
        else:
            review_dict["score_ingredients"] = 0.5
            review_dict["score_formulation"] = 0.5
            review_dict["score_container"] = 0.5

        return review_dict

    # 컬럼 레이아웃 (전체 쿼리, 24열)
    # idx 0-13 : 기본 리뷰 필드
    # idx 14   : r.is_priority_review
    # idx 15   : r.analysis_status
    # idx 16-18: r.score_ingredients, r.score_formulation, r.score_container
    # idx 19-23: p.id, b.name, p.product_name, c.name, s.name
    _REVIEW_SELECT_SQL = """
        SELECT r.id, r.product_id, r.source::text, r.reviewer_type::text, r.review_text, r.rating,
               r.review_date::text, r.sentiment::text, r.sentiment_score,
               COALESCE(array_agg(k.keyword) FILTER (WHERE k.keyword IS NOT NULL), '{}') AS keywords,
               r.issue_type::text, r.ai_summary, r.created_at, r.review_id,
               r.is_priority_review, r.analysis_status,
               r.score_ingredients, r.score_formulation, r.score_container,
               p.id, b.name AS brand_name, p.product_name, c.name AS category, s.name AS target_skin
        FROM public.reviews r
        LEFT JOIN public.products p ON r.product_id = p.id
        LEFT JOIN public.brands b ON p.brand_id = b.id
        LEFT JOIN public.categories c ON p.category_id = c.id
        LEFT JOIN public.skin_types s ON p.skin_type_id = s.id
        LEFT JOIN public.review_keywords rk ON r.id = rk.review_id
        LEFT JOIN public.keywords k ON rk.keyword_id = k.id
    """

    # score_* 컬럼이 DB에 없는 경우 폴백용 SELECT (21열)
    # idx 0-13 : 기본 리뷰 필드
    # idx 14   : r.is_priority_review
    # idx 15   : r.analysis_status
    # idx 16-20: p.id, b.name, p.product_name, c.name, s.name
    # → _parse_db_row_to_review: len(row) < 24 이면 score 를 0.5 기본값으로 처리
    _REVIEW_SELECT_FALLBACK_SQL = """
        SELECT r.id, r.product_id, r.source::text, r.reviewer_type::text, r.review_text, r.rating,
               r.review_date::text, r.sentiment::text, r.sentiment_score,
               COALESCE(array_agg(k.keyword) FILTER (WHERE k.keyword IS NOT NULL), '{}') AS keywords,
               r.issue_type::text, r.ai_summary, r.created_at, r.review_id,
               r.is_priority_review, r.analysis_status,
               p.id, b.name AS brand_name, p.product_name, c.name AS category, s.name AS target_skin
        FROM public.reviews r
        LEFT JOIN public.products p ON r.product_id = p.id
        LEFT JOIN public.brands b ON p.brand_id = b.id
        LEFT JOIN public.categories c ON p.category_id = c.id
        LEFT JOIN public.skin_types s ON p.skin_type_id = s.id
        LEFT JOIN public.review_keywords rk ON r.id = rk.review_id
        LEFT JOIN public.keywords k ON rk.keyword_id = k.id
    """

    def _build_where(self, product_id, period_days, sentiment, q, priority, alias=""):
        """
        공통 WHERE 절 빌더.
        - sentiment 조건은 ::sentiment_type enum 캐스팅 없이 ::text 비교로 처리
          → 실제 DB 컬럼이 enum이든 text든 동일하게 동작
        - alias: 테이블 별칭 (예: "r" → "r.sentiment"). 빈 문자열이면 그대로 사용.
        """
        prefix = f"{alias}." if alias else ""
        where_clauses = []
        params = []
        if product_id:
            where_clauses.append(f"{prefix}product_id = %s::uuid")
            params.append(product_id)
        if period_days:
            start_date = (datetime.now().date() - timedelta(days=period_days)).isoformat()
            where_clauses.append(f"{prefix}review_date >= %s::date")
            params.append(start_date)
        if priority:
            # DB 신규 컬럼 is_priority_review 로 우선 확인 리뷰 여부 판단
            where_clauses.append(f"{prefix}is_priority_review = true")
        elif sentiment:
            where_clauses.append(f"{prefix}sentiment::text = %s")
            params.append(sentiment)
        if q:
            where_clauses.append(f"{prefix}review_text ILIKE %s")
            params.append(f"%{q}%")
        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        return where_str, params

    def fetch_count(self, product_id: Optional[str] = None, period_days: Optional[int] = None,
                    sentiment: Optional[str] = None, q: Optional[str] = None, priority: bool = False) -> int:
        if self.conn is not None:
            try:
                where_str, params = self._build_where(product_id, period_days, sentiment, q, priority)
                cursor = self.conn.cursor()
                cursor.execute(f"SELECT COUNT(id) FROM public.reviews {where_str}", params)
                count = int(cursor.fetchone()[0])
                cursor.close()
                return count
            except Exception as e:
                print(f"[ReviewRepository.fetch_count] DB 조회 실패, Mock 건수 반환: {e}")
        reviews = MOCK_REVIEWS
        if priority:
            reviews = [r for r in reviews if r.get("is_priority_review") is True]
        elif sentiment:
            reviews = [r for r in reviews if r.get("sentiment") == sentiment]
        return len(reviews)

    def fetch_advanced(self, product_id: Optional[str] = None, period_days: Optional[int] = None,
                       sentiment: Optional[str] = None, q: Optional[str] = None,
                       priority: bool = False, page: int = 1, limit: int = 20) -> list:
        offset = (page - 1) * limit
        if self.conn is not None:
            where_str, where_params = self._build_where(product_id, period_days, sentiment, q, priority, alias="r")
            group_order = "GROUP BY r.id, p.id, b.name, c.name, s.name ORDER BY r.review_date DESC, r.created_at DESC LIMIT %s OFFSET %s"
            full_params = where_params + [limit, offset]

            # 1차 시도: score_* 컬럼 포함 전체 쿼리
            try:
                cursor = self.conn.cursor()
                sql = f"{self._REVIEW_SELECT_SQL} {where_str} {group_order}"
                cursor.execute(sql, full_params)
                rows = cursor.fetchall()
                cursor.close()
                return [self._parse_db_row_to_review(r) for r in rows]
            except Exception as e:
                print(f"[ReviewRepository.fetch_advanced] 전체 쿼리 실패: {e}")

            # 2차 시도: score_* 컬럼 제외 폴백 쿼리 (WHERE 조건·필터는 동일하게 유지)
            try:
                cursor = self.conn.cursor()
                sql_fallback = f"{self._REVIEW_SELECT_FALLBACK_SQL} {where_str} {group_order}"
                cursor.execute(sql_fallback, full_params)
                rows = cursor.fetchall()
                cursor.close()
                print("[ReviewRepository.fetch_advanced] score 컬럼 제외 폴백 쿼리로 조회 성공")
                return [self._parse_db_row_to_review(r) for r in rows]
            except Exception as e2:
                print(f"[ReviewRepository.fetch_advanced] 폴백 쿼리도 실패, Mock 데이터 반환: {e2}")

        # Mock 폴백 (필터 조건 동일하게 적용)
        filtered = list(MOCK_REVIEWS)
        if product_id:
            filtered = [r for r in filtered if r.get("product_id") == product_id]
        if priority:
            filtered = [r for r in filtered if r.get("is_priority_review") is True]
        elif sentiment:
            filtered = [r for r in filtered if r.get("sentiment") == sentiment]
        if q:
            filtered = [r for r in filtered if q.lower() in r.get("review_text", "").lower()]
        return filtered[offset:offset + limit]

    def fetch_attribute_scores(self, product_id: Optional[str] = None, period_days: Optional[int] = None) -> dict:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                where_clauses = []
                params = []
                if product_id:
                    where_clauses.append("product_id = %s::uuid")
                    params.append(product_id)
                if period_days:
                    start_date = (datetime.now().date() - timedelta(days=period_days)).isoformat()
                    where_clauses.append("review_date >= %s::date")
                    params.append(start_date)
                where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
                cursor.execute(
                    f"SELECT AVG(score_ingredients), AVG(score_formulation), AVG(score_container) FROM public.reviews {where_str}",
                    params
                )
                row = cursor.fetchone()
                cursor.close()
                if row:
                    return {
                        "score_ingredients": round(float(row[0]), 3) if row[0] else 0.5,
                        "score_formulation": round(float(row[1]), 3) if row[1] else 0.5,
                        "score_container": round(float(row[2]), 3) if row[2] else 0.5,
                    }
            except Exception as e:
                print(f"[ReviewRepository.fetch_attribute_scores] DB 조회 실패, Mock 폴백: {e}")
        filtered = MOCK_REVIEWS
        if product_id:
            filtered = [r for r in filtered if r.get("product_id") == product_id]
        if not filtered:
            return {"score_ingredients": 0.5, "score_formulation": 0.5, "score_container": 0.5}
        return {
            "score_ingredients": round(sum(r.get("score_ingredients", 0.5) for r in filtered) / len(filtered), 3),
            "score_formulation": round(sum(r.get("score_formulation", 0.5) for r in filtered) / len(filtered), 3),
            "score_container": round(sum(r.get("score_container", 0.5) for r in filtered) / len(filtered), 3),
        }

    def fetch_by_ids(self, ids: List[str]) -> list:
        if not ids:
            return []
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                placeholders = ",".join(["%s"] * len(ids))
                sql = f"{self._REVIEW_SELECT_SQL} WHERE r.id IN ({placeholders}) GROUP BY r.id, p.id, b.name, c.name, s.name ORDER BY r.review_date DESC, r.created_at DESC"
                cursor.execute(sql, ids)
                rows = cursor.fetchall()
                cursor.close()
                return [self._parse_db_row_to_review(r) for r in rows]
            except Exception as e:
                print(f"[ReviewRepository.fetch_by_ids] Cloud SQL fetch 실패: {e}")
        return [r for r in MOCK_REVIEWS if r["id"] in ids]

    def save_bulk(self, sql_record: dict, keywords: list) -> None:
        """단일 리뷰를 DB에 원자적으로 적재 (pgvector + keywords)"""
        if self.conn is None:
            return
        try:
            cursor = self.conn.cursor()
            sql = """
                INSERT INTO public.reviews (
                    id, product_id, source, reviewer_type, review_text, rating, review_date,
                    sentiment, sentiment_score, issue_type, ai_summary, review_id,
                    embedding, score_ingredients, score_formulation, score_container
                ) VALUES (
                    %s::uuid, %s::uuid,
                    CASE WHEN LOWER(TRIM(%s)) IN ('youtube', 'blog', 'naver_store', 'olive_young', 'mock') THEN LOWER(TRIM(%s))::source_type ELSE 'other'::source_type END,
                    CASE WHEN LOWER(TRIM(%s)) IN ('general', 'influencer', 'expert') THEN LOWER(TRIM(%s))::reviewer_type ELSE 'general'::reviewer_type END,
                    %s, %s, %s::date, %s::sentiment_type, %s,
                    CASE WHEN LOWER(TRIM(%s)) IN ('ingredients', 'formulation', 'container', 'scent', 'irritation', 'none') THEN LOWER(TRIM(%s))::issue_type ELSE 'other'::issue_type END,
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
                sql_record["embedding"],
                sql_record["score_ingredients"], sql_record["score_formulation"], sql_record["score_container"]
            ])
            if keywords:
                for kw in keywords:
                    if kw and kw.strip():
                        clean_kw = kw.strip()
                        cursor.execute("INSERT INTO public.keywords (keyword) VALUES (%s) ON CONFLICT (keyword) DO NOTHING", [clean_kw])
                        cursor.execute("SELECT id FROM public.keywords WHERE keyword = %s", [clean_kw])
                        kw_id_row = cursor.fetchone()
                        if kw_id_row:
                            cursor.execute("INSERT INTO public.review_keywords (review_id, keyword_id) VALUES (%s::uuid, %s) ON CONFLICT DO NOTHING", [sql_record["id"], kw_id_row[0]])
            self.conn.commit()
            cursor.close()
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            raise e

    def save_bulk_fallback(self, sql_record: dict, keywords: list, healed_summary: str) -> None:
        """벡터/스코어 컬럼 누락 시 핵심 텍스트 컬럼만으로 자가 치유(Self-Healing) 적재"""
        if self.conn is None:
            return
        try:
            cursor = self.conn.cursor()
            fallback_sql = """
                INSERT INTO public.reviews (
                    id, product_id, source, reviewer_type, review_text, rating, review_date,
                    sentiment, sentiment_score, issue_type, ai_summary, review_id
                ) VALUES (
                    %s::uuid, %s::uuid,
                    CASE WHEN LOWER(TRIM(%s)) IN ('youtube', 'blog', 'naver_store', 'olive_young', 'mock') THEN LOWER(TRIM(%s))::source_type ELSE 'other'::source_type END,
                    CASE WHEN LOWER(TRIM(%s)) IN ('general', 'influencer', 'expert') THEN LOWER(TRIM(%s))::reviewer_type ELSE 'general'::reviewer_type END,
                    %s, %s, %s::date, %s::sentiment_type, %s,
                    CASE WHEN LOWER(TRIM(%s)) IN ('ingredients', 'formulation', 'container', 'scent', 'irritation', 'none') THEN LOWER(TRIM(%s))::issue_type ELSE 'other'::issue_type END,
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
            if keywords:
                for kw in keywords:
                    if kw and kw.strip():
                        clean_kw = kw.strip()
                        cursor.execute("INSERT INTO public.keywords (keyword) VALUES (%s) ON CONFLICT (keyword) DO NOTHING", [clean_kw])
                        cursor.execute("SELECT id FROM public.keywords WHERE keyword = %s", [clean_kw])
                        kw_id_row = cursor.fetchone()
                        if kw_id_row:
                            cursor.execute("INSERT INTO public.review_keywords (review_id, keyword_id) VALUES (%s::uuid, %s) ON CONFLICT DO NOTHING", [sql_record["id"], kw_id_row[0]])
            self.conn.commit()
            cursor.close()
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            raise e
