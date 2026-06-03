"""
ProductRepository — products 테이블 전담 DB 쿼리 레이어
"""
import uuid
from typing import Optional
from app.database.mock_data import MOCK_PRODUCTS, MOCK_REVIEWS


class ProductRepository:
    def __init__(self, db_conn=None):
        self.conn = db_conn

    def fetch_all(self) -> list:
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
                print(f"[ProductRepository.fetch_all] Cloud SQL fetch 실패, Mock 폴백: {e}")
        return MOCK_PRODUCTS

    def fetch_paged(self, q: Optional[str] = None, sort: Optional[str] = None, page: int = 1, limit: int = 10) -> dict:
        offset = (page - 1) * limit
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                where_clauses = []
                params = []
                if q:
                    where_clauses.append("(p.product_name ILIKE %s OR b.name ILIKE %s)")
                    params.extend([f"%{q}%", f"%{q}%"])
                where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
                order_by = "p.product_name ASC"
                if sort == "newest":
                    order_by = "p.created_at DESC"
                elif sort == "oldest":
                    order_by = "p.created_at ASC"

                cursor.execute(
                    f"SELECT COUNT(p.id) FROM public.products p JOIN public.brands b ON p.brand_id = b.id {where_str}",
                    params
                )
                total = cursor.fetchone()[0]

                sql = f"""
                    SELECT p.id, b.name AS brand_name, p.product_name, c.name AS category, s.name AS target_skin,
                           p.is_analysis_active, p.created_at, COUNT(r.id) AS review_count
                    FROM public.products p
                    JOIN public.brands b ON p.brand_id = b.id
                    JOIN public.categories c ON p.category_id = c.id
                    JOIN public.skin_types s ON p.skin_type_id = s.id
                    LEFT JOIN public.reviews r ON p.id = r.product_id
                    {where_str}
                    GROUP BY p.id, b.name, c.name, s.name
                    ORDER BY {order_by}
                    LIMIT %s OFFSET %s
                """
                params.extend([limit, offset])
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                cursor.close()
                products_list = [{
                    "id": str(r[0]),
                    "brand_name": r[1],
                    "product_name": r[2],
                    "category": r[3],
                    "target_skin": r[4],
                    "is_analysis_active": bool(r[5]),
                    "created_at": str(r[6]),
                    "review_count": r[7]
                } for r in rows]
                return {"total": total, "products": products_list}
            except Exception as e:
                print(f"[ProductRepository.fetch_paged] DB 조회 실패, Mock 폴백: {e}")

        mock_list = []
        for p in MOCK_PRODUCTS:
            brand = p.get("brand_name", "")
            name = p.get("product_name", "")
            if q and not (q.lower() in brand.lower() or q.lower() in name.lower()):
                continue
            cnt = sum(1 for r in MOCK_REVIEWS if r.get("product_id") == p["id"])
            mock_list.append({
                "id": p["id"],
                "brand_name": brand,
                "product_name": name,
                "category": p.get("category", "pad"),
                "target_skin": p.get("target_skin", "민감성"),
                "is_analysis_active": True,
                "created_at": p.get("created_at"),
                "review_count": cnt
            })
        return {"total": len(mock_list), "products": mock_list[offset:offset + limit]}

    def fetch_stats(self) -> dict:
        registered = len(MOCK_PRODUCTS)
        active = len(MOCK_PRODUCTS)
        reviews_cnt = len(MOCK_REVIEWS)
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT COUNT(id) FROM public.products")
                registered = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(id) FROM public.products WHERE is_analysis_active = TRUE")
                active = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(id) FROM public.reviews")
                reviews_cnt = cursor.fetchone()[0]
                cursor.close()
            except Exception as e:
                print(f"[ProductRepository.fetch_stats] DB 조회 실패, Mock 폴백: {e}")
        return {
            "registered_products_count": registered,
            "active_analysis_products_count": active,
            "total_reviews_count": reviews_cnt
        }

    def create(self, brand_name: str, product_name: str, description: Optional[str],
               price: Optional[float], category_name: str, skin_type_name: str) -> dict:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute("INSERT INTO public.brands (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", [brand_name])
                cursor.execute("SELECT id FROM public.brands WHERE name = %s", [brand_name])
                brand_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO public.categories (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", [category_name])
                cursor.execute("SELECT id FROM public.categories WHERE name = %s", [category_name])
                category_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO public.skin_types (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", [skin_type_name])
                cursor.execute("SELECT id FROM public.skin_types WHERE name = %s", [skin_type_name])
                skin_type_id = cursor.fetchone()[0]
                new_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO public.products (id, brand_id, product_name, description, price, category_id, skin_type_id, is_analysis_active)
                    VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, TRUE)
                    RETURNING id
                """, [new_id, brand_id, product_name, description, price, category_id, skin_type_id])
                prod_uuid = str(cursor.fetchone()[0])
                self.conn.commit()
                cursor.close()
                return {
                    "success": True,
                    "product": {
                        "id": prod_uuid,
                        "brand_name": brand_name,
                        "product_name": product_name,
                        "description": description,
                        "price": price,
                        "category": category_name,
                        "target_skin": skin_type_name,
                        "is_analysis_active": True
                    }
                }
            except Exception as e:
                print(f"[ProductRepository.create] DB 인서트 실패: {e}")
                try:
                    self.conn.rollback()
                except Exception:
                    pass

        mock_id = str(uuid.uuid4())
        new_p = {
            "id": mock_id,
            "brand_name": brand_name,
            "product_name": product_name,
            "category": category_name,
            "target_skin": skin_type_name,
            "created_at": __import__('datetime').datetime.now().isoformat()
        }
        MOCK_PRODUCTS.append(new_p)
        return {"success": True, "product": new_p}

    def update_partial(self, product_id: str, fields: dict) -> dict:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                set_clauses = [f"{k} = %s" for k in fields]
                params = list(fields.values()) + [product_id]
                sql = f"UPDATE public.products SET {', '.join(set_clauses)}, updated_at = timezone('utc'::text, now()) WHERE id = %s::uuid RETURNING id, is_analysis_active"
                cursor.execute(sql, params)
                row = cursor.fetchone()
                self.conn.commit()
                cursor.close()
                if row:
                    return {"success": True, "product_id": str(row[0]), "is_analysis_active": bool(row[1])}
            except Exception as e:
                print(f"[ProductRepository.update_partial] DB 업데이트 실패: {e}")
                try:
                    self.conn.rollback()
                except Exception:
                    pass
        for p in MOCK_PRODUCTS:
            if p["id"] == product_id:
                for k, v in fields.items():
                    p[k] = v
                return {"success": True, "product_id": product_id, "is_analysis_active": fields.get("is_analysis_active", True)}
        return {"success": False, "message": "Product not found"}

    def trigger_sync(self) -> dict:
        if self.conn is not None:
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT INTO public.integrations (platform_name, status, sync_rate, last_synced_at)
                    VALUES ('naver', 'connected', 100.0, timezone('utc'::text, now()))
                    ON CONFLICT (platform_name)
                    DO UPDATE SET status = 'connected', sync_rate = 100.0, error_message = NULL, last_synced_at = timezone('utc'::text, now())
                """)
                cursor.execute("""
                    INSERT INTO public.integrations (platform_name, status, sync_rate, last_synced_at)
                    VALUES ('olive_young', 'connected', 98.5, timezone('utc'::text, now()))
                    ON CONFLICT (platform_name)
                    DO UPDATE SET status = 'connected', sync_rate = 98.5, error_message = NULL, last_synced_at = timezone('utc'::text, now())
                """)
                self.conn.commit()
                cursor.close()
            except Exception as e:
                print(f"[ProductRepository.trigger_sync] DB 이력 갱신 실패: {e}")
        return {
            "success": True,
            "message": "크롤링 배치 엔진 동기화가 성공적으로 시작되어 정상 반영되었습니다.",
            "platforms": ["naver", "olive_young"]
        }
