from fastapi import APIRouter
from app.domains.auth import router as auth
from app.domains.users import router as users
from app.domains.ai_search import router as ai_search
from app.domains.dashboard import router as dashboard
from app.domains.reviews import router as reviews
from app.domains.products import router as products
from app.domains.layout import router as layout
from app.domains.admin import router as admin
from app.domains.settings import router as settings
from app.domains.integrations import router as integrations

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
