from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status

from app.core.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.domains.products.schemas import ProductSchema, ProductCreatePayload, ProductUpdatePayload
from app.domains.products.service import ProductService

router = APIRouter()


def get_product_service(db_conn=Depends(get_db_connection)) -> ProductService:
    return ProductService(db_conn)


@router.get("/stats")
def get_products_stats(
    product_service: ProductService = Depends(get_product_service),
    current_user: dict = Depends(get_current_user)
):
    """제품 관리 - 등록 상품·분석 활성·누적 리뷰 수 종합 통계 반환 API (인증 필요)"""
    return product_service.fetch_products_stats()


@router.get("")
def get_products_paged(
    q: Optional[str] = Query(None, description="검색어 (브랜드명 또는 제품명)"),
    sort: Optional[str] = Query("name", description="정렬 조건 (name, newest, oldest 등)"),
    page: int = Query(1, description="페이지 번호"),
    limit: int = Query(10, description="한 페이지당 노출 상품 수"),
    product_service: ProductService = Depends(get_product_service),
    current_user: dict = Depends(get_current_user)
):
    """제품 관리 - 정렬, 검색 및 페이징이 가미된 상품 목록 조회 API (인증 필요)"""
    return product_service.fetch_products_paged(q=q, sort=sort, page=page, limit=limit)


@router.get("/list", response_model=List[ProductSchema])
def get_products_dropdown(
    product_service: ProductService = Depends(get_product_service)
):
    """공통 - 제품 드롭다운 필터링 리스트 반환용 단순 API (전체 반환)"""
    return product_service.fetch_products()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_new_product(
    payload: ProductCreatePayload,
    product_service: ProductService = Depends(get_product_service),
    current_user: dict = Depends(get_current_user)
):
    """제품 관리 - 신규 화장품 상품 등록 API (인증 필요)"""
    return product_service.create_product(
        brand_name=payload.brand_name,
        product_name=payload.product_name,
        description=payload.description,
        price=payload.price,
        category_name=payload.category,
        skin_type_name=payload.target_skin
    )


@router.patch("/{id}")
def update_product(
    id: str = Path(..., description="수정할 제품 UUID"),
    payload: ProductUpdatePayload = None,
    product_service: ProductService = Depends(get_product_service),
    current_user: dict = Depends(get_current_user)
):
    """제품 관리 - 분석 활성 상태 토글 및 제품 정보 일부 수정 API (인증 필요)"""
    if not payload:
        raise HTTPException(status_code=400, detail="수정할 필드 바디 정보가 누락되었습니다.")
    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="최소 1개 이상의 수정 필드를 입력해야 합니다.")
    result = product_service.update_product_partial(product_id=id, fields=update_data)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message", "Product not found"))
    return result


@router.post("/sync")
def trigger_sync(
    product_service: ProductService = Depends(get_product_service),
    current_user: dict = Depends(get_current_user)
):
    """제품 관리 - 수집 동기화 파이프라인 수동 트리거 및 이력 로그 저장 API (인증 필요)"""
    return product_service.trigger_sync_crawler()
