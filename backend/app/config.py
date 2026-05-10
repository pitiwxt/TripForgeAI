"""
Configuration — Groq (Llama 4 Scout) + Nominatim + OSRM.
All secrets come from environment variables.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── AI (Groq) ──────────────────────────────────────────────────────
    groq_api_key: str = ""
    groq_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # ── Supabase (optional) ────────────────────────────────────────────
    supabase_url: str = ""
    supabase_key: str = ""

    # ── Application ────────────────────────────────────────────────────
    app_name: str = "TripForge AI"
    debug: bool = False
    default_travel_mode: str = "driving"

    # ── External APIs (free, no key) ───────────────────────────────────
    nominatim_url: str = "https://nominatim.openstreetmap.org"
    osrm_url: str = "http://router.project-osrm.org"
    nominatim_user_agent: str = "TripForgeAI/3.0"

    # ── CORS ───────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:3000"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — created once per process."""
    return Settings()
