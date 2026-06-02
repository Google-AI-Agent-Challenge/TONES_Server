from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, ai_search, dashboard, reviews, products, layout, admin, settings, integrations

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(ai_search.router, prefix="/ai", tags=["ai"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(layout.router, prefix="/layout", tags=["layout"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])

