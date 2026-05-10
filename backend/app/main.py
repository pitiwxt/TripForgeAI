"""
FastAPI entrypoint — Osaka Travel Agent (Free-Tier Stack).
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api.v1.router import api_v1_router

# ── Logging ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("=" * 60)
    logger.info("✈️  TripForge AI starting up")
    logger.info(f"   Groq AI: {'✅ configured' if settings.groq_api_key else '⚠️  not set'} ({settings.groq_model})")
    logger.info(f"   Supabase: {'✅ configured' if settings.supabase_url else '⚠️  not set (local only)'}")
    logger.info(f"   Nominatim: {settings.nominatim_url}")
    logger.info(f"   OSRM: {settings.osrm_url}")
    logger.info(f"   Frontend URL: {settings.frontend_url}")
    logger.info(f"   Debug: {settings.debug}")
    logger.info("=" * 60)
    yield
    logger.info("TripForge AI shutting down")


app = FastAPI(
    title="TripForge AI",
    description="AI travel planner for any destination — powered by Groq + Leaflet + OSRM",
    version="3.0.0",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────────
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──────────────────────────────────────────────────────────────
app.include_router(api_v1_router, prefix="/api/v1")
