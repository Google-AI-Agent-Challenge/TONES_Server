"""
AIRepository — pgvector 시맨틱 검색 전담 DB 쿼리 레이어
"""
from app.domains.ai_search.schemas import SearchRequest, SearchResultItem


class AIRepository:
    def __init__(self, db_conn=None):
        self.conn = db_conn

    def vector_search(self, request: SearchRequest, query_vector: list) -> list[SearchResultItem]:
        """pgvector 코사인 거리 기반 시맨틱 검색"""
        if self.conn is None or query_vector is None:
            return []
        try:
            cursor = self.conn.cursor()
            vector_str = f"[{','.join(map(str, query_vector))}]"
            where_clauses = ["embedding IS NOT NULL"]
            params = [vector_str]
            if request.filter and "product_id" in request.filter:
                where_clauses.append("product_id = %s")
                params.append(request.filter["product_id"])
            where_str = f"WHERE {' AND '.join(where_clauses)}"
            sql = f"""
                SELECT id, review_text, rating, review_date, sentiment, issue_type, ai_summary,
                       (1 - (embedding <=> %s::vector)) AS similarity
                FROM public.reviews
                {where_str}
                ORDER BY embedding <=> %s::vector ASC
                LIMIT %s
            """
            params.extend([vector_str, request.top_k])
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            cursor.close()
            results = []
            for row in rows:
                results.append(SearchResultItem(
                    id=str(row[0]),
                    score=float(row[7] or 0.0),
                    metadata={
                        "review_text": row[1],
                        "rating": row[2],
                        "review_date": str(row[3]),
                        "sentiment": str(row[4]),
                        "issue_type": row[5] or "",
                        "ai_summary": row[6] or ""
                    }
                ))
            print(f"[AIRepository] pgvector 시맨틱 검색 성공: {len(results)}개 결과 반환")
            return results
        except Exception as e:
            print(f"[AIRepository] pgvector 시맨틱 검색 실패: {e}")
            return []
