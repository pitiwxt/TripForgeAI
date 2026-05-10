"""
Directions service — OSRM Route endpoint (free).
Returns GeoJSON route geometry instead of Google-encoded polylines.
"""

import math
import logging
import httpx
from app.schemas.itinerary import GeocodedPlace
from app.utils.cache import directions_cache

logger = logging.getLogger(__name__)

OSRM_BASE = "http://router.project-osrm.org"


async def get_directions(
    origin: GeocodedPlace,
    destination: GeocodedPlace,
) -> dict:
    """
    Fetch route geometry between two points using OSRM.

    Returns:
        Dict with keys:
        - route_geometry: list of [lng, lat] coordinate pairs (GeoJSON order)
        - distance_meters: int
        - duration_seconds: int
    """
    cache_key = f"{origin.lat},{origin.lng}->{destination.lat},{destination.lng}"
    cached = directions_cache.get(cache_key)
    if cached:
        return cached

    # ── Try OSRM Route ──────────────────────────────────────────────
    try:
        coords = f"{origin.lng},{origin.lat};{destination.lng},{destination.lat}"
        url = f"{OSRM_BASE}/route/v1/driving/{coords}?geometries=geojson&overview=full"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()

        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            geometry = route["geometry"]["coordinates"]  # [[lng, lat], ...]
            distance = int(route["distance"])
            duration = int(route["duration"])

            result = {
                "route_geometry": geometry,
                "distance_meters": distance,
                "duration_seconds": duration,
            }
            directions_cache.set(cache_key, result)
            logger.info(
                f"OSRM route: {origin.name} → {destination.name} "
                f"({distance}m, {duration}s, {len(geometry)} points)"
            )
            return result

    except Exception as e:
        logger.warning(f"OSRM Route error: {e} — falling back to straight line")

    # ── Fallback: straight line ─────────────────────────────────────
    R = 6_371_000
    phi1, phi2 = math.radians(origin.lat), math.radians(destination.lat)
    dphi = math.radians(destination.lat - origin.lat)
    dlambda = math.radians(destination.lng - origin.lng)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    dist = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    result = {
        "route_geometry": [
            [origin.lng, origin.lat],
            [destination.lng, destination.lat],
        ],
        "distance_meters": int(dist),
        "duration_seconds": max(60, int(dist / (5_000 / 3600))),
    }
    directions_cache.set(cache_key, result)
    logger.info(f"Directions (fallback): {origin.name} → {destination.name}")
    return result
