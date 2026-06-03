from typing import Optional
from app.domains.products.repository import ProductRepository


class ProductService:
    def __init__(self, db_conn=None):
        self.repo = ProductRepository(db_conn)

    def fetch_products(self) -> list:
        return self.repo.fetch_all()

    def fetch_products_paged(self, q: Optional[str] = None, sort: Optional[str] = None,
                             page: int = 1, limit: int = 10) -> dict:
        return self.repo.fetch_paged(q=q, sort=sort, page=page, limit=limit)

    def fetch_products_stats(self) -> dict:
        return self.repo.fetch_stats()

    def create_product(self, brand_name: str, product_name: str, description: Optional[str],
                       price: Optional[float], category_name: str, skin_type_name: str) -> dict:
        return self.repo.create(
            brand_name=brand_name,
            product_name=product_name,
            description=description,
            price=price,
            category_name=category_name,
            skin_type_name=skin_type_name
        )

    def update_product_partial(self, product_id: str, fields: dict) -> dict:
        return self.repo.update_partial(product_id, fields)

    def trigger_sync_crawler(self) -> dict:
        return self.repo.trigger_sync()
