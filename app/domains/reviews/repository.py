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
        """SQL Query 결과 Tuple을 ReviewSchema 호환 딕셔너리로 변환 (자가 치유 복구 포함)"""
        prod_obj = None
        if len(row) >= 19:
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
            "products": prod_obj
        }

        if len(row) >= 22:
            review_dict["score_ingredients"] = float(row[14]) if row[14] is not None else 0.5
            review_dict["score_formulation"] = float(row[15]) if row[15] is not None else 0.5
            review_dict["score_container"] = float(row[16]) if row[16] is not None else 0.5
        else:
            review_dict["score_ingredients"] = 0.5
            review_dict["score_formulation"] = 0.5
            review_dict["score_container"] = 0.5

        return review_dict

    _REVIEW_SELECT_SQL = """
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
    """

    def fetch_count(self, product_id: Optional[str] = None, period_days: Optional[int] = None,
                    sentiment: Optional[str] = None, q: Optional[str] = None, priority: bool = False) -> int:
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
                if priority:
                    where_clauses.append("sentiment = 'negative'::sentiment_type")
                    where_clauses.append("rating <= 2")
                elif sentiment:
                    where_clauses.append("sentiment = %s::sentiment_type")
                    params.append(sentiment)
                if q:
                    where_clauses.append("review_text ILIKE %s")
                    params.append(f"%{q}%")
                where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
                cursor.execute(f"SELECT COUNT(id) FROM public.reviews {where_str}", params)
                count = int(cursor.fetchone()[0])
                cursor.close()
                return count
            except Exception as e:
                print(f"[ReviewRepository.fetch_count] DB 조회 실패, Mock 건수 반환: {e}")
        reviews = MOCK_REVIEWS
        if priority:
            reviews = [r for r in reviews if r.get("sentiment") == "negative" and r.get("rating", 3) <= 2]
        return len(reviews)

    def fetch_advanced(self, product_id: Optional[str] = None, period_days: Optional[int] = None,
                       sentiment: Optional[str] = None, q: Optional[str] = None,
                       priority: bool = False, page: int = 1, limit: int = 20) -> list:
        offset = (page - 1) * limit
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                where_clauses = []
                params = []
                if product_id:
                    where_clauses.append("r.product_id = %s::uuid")
                    params.append(product_id)
                if period_days:
                    start_date = (datetime.now().date() - timedelta(days=period_days)).isoformat()
                    where_clauses.append("r.review_date >= %s::date")
                    params.append(start_date)
                if priority:
                    where_clauses.append("r.sentiment = 'negative'::sentiment_type")
                    where_clauses.append("r.rating <= 2")
                elif sentiment:
                    where_clauses.append("r.sentiment = %s::sentiment_type")
                    params.append(sentiment)
                if q:
                    where_clauses.append("r.review_text ILIKE %s")
                    params.append(f"%{q}%")
                where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
                sql = f"{self._REVIEW_SELECT_SQL} {where_str} GROUP BY r.id, p.id, b.name, c.name, s.name ORDER BY r.review_date DESC, r.created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                cursor.close()
                return [self._parse_db_row_to_review(r) for r in rows]
            except Exception as e:
                print(f"[ReviewRepository.fetch_advanced] DB 조회 실패, Mock 폴백: {e}")
        filtered = MOCK_REVIEWS
        if product_id:
            filtered = [r for r in filtered if r.get("product_id") == product_id]
        if priority:
            filtered = [r for r in filtered if r.get("sentiment") == "negative" and r.get("rating", 3) <= 2]
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

    def _save_keywords(self, cursor, review_id: str, keywords: list) -> None:
        if not keywords:
            return
        clean_kws = [kw.strip() for kw in keywords if kw and kw.strip()]
        if not clean_kws:
            return
        
        # 1) Bulk insert keywords ON CONFLICT DO NOTHING
        placeholders = ",".join(["(%s)"] * len(clean_kws))
        cursor.execute(f"INSERT INTO public.keywords (keyword) VALUES {placeholders} ON CONFLICT (keyword) DO NOTHING", clean_kws)
        
        # 2) Fetch all keyword IDs
        placeholders_select = ",".join(["%s"] * len(clean_kws))
        cursor.execute(f"SELECT id, keyword FROM public.keywords WHERE keyword IN ({placeholders_select})", clean_kws)
        kw_rows = cursor.fetchall()
        
        # 3) Bulk insert review_keywords mapping
        mapping_values = []
        mapping_params = []
        for kw_id, _ in kw_rows:
            mapping_values.append("(%s::uuid, %s)")
            mapping_params.extend([review_id, kw_id])
        
        if mapping_values:
            mapping_sql = f"INSERT INTO public.review_keywords (review_id, keyword_id) VALUES {','.join(mapping_values)} ON CONFLICT DO NOTHING"
            cursor.execute(mapping_sql, mapping_params)

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
            self._save_keywords(cursor, sql_record["id"], keywords)
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
            self._save_keywords(cursor, sql_record["id"], keywords)
            self.conn.commit()
            cursor.close()
        except Exception as e:
            try:
                self.conn.rollback()
            except Exception:
                pass
            raise e
