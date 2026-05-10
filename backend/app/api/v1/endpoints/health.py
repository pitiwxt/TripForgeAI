"""
Health check endpoint — used for monitoring and container orchestration.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check():
    """Returns service health status."""
    return {"status": "healthy", "service": "ai-travel-agent"}
