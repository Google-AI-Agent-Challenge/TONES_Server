from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, ai_search

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(ai_search.router, prefix="/ai", tags=["ai"])
