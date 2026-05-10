"""
API v1 router — aggregates all endpoint routers.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import health, chat, sessions

api_v1_router = APIRouter()

api_v1_router.include_router(health.router)
api_v1_router.include_router(chat.router)
api_v1_router.include_router(sessions.router)
