"""
Distance Matrix service — OSRM Table endpoint (free) with haversine fallback.
"""

import math
import logging
import httpx
from app.schemas.itinerary import GeocodedPlace
from app.utils.cache import distance_matrix_cache

logger = logging.getLogger(__name__)

OSRM_BASE = "http://router.project-osrm.org"


def _haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _estimate_duration(distance_meters: float) -> int:
    """Estimate walking duration (~5km/h) as transit proxy for urban Osaka."""
    return max(60, int(distance_meters / (5_000 / 3600)))


async def get_distance_matrix(
    places: list[GeocodedPlace],
) -> tuple[list[list[int]], list[list[int]]]:
    """
    Build NxN duration/distance matrices using OSRM Table API.
    Falls back to haversine if OSRM is unavailable.
    """
    n = len(places)
    duration_matrix = [[0] * n for _ in range(n)]
    distance_matrix_result = [[0] * n for _ in range(n)]

    # ── Try OSRM Table endpoint ─────────────────────────────────────
    try:
        coords_str = ";".join(f"{p.lng},{p.lat}" for p in places)
        url = f"{OSRM_BASE}/table/v1/driving/{coords_str}?annotations=duration,distance"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15.0)
            response.raise_for_status()
            data = response.json()

        if data.get("code") == "Ok":
            durations = data["durations"]
            distances = data["distances"]

            for i in range(n):
                for j in range(n):
                    dur = durations[i][j]
                    dist = distances[i][j]
                    duration_matrix[i][j] = int(dur) if dur is not None else 0
                    distance_matrix_result[i][j] = int(dist) if dist is not None else 0

            logger.info(f"OSRM distance matrix built: {n}×{n}")
            return duration_matrix, distance_matrix_result

    except Exception as e:
        logger.warning(f"OSRM Table error: {e} — falling back to haversine")

    # ── Haversine fallback ──────────────────────────────────────────
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            dist = _haversine_meters(places[i].lat, places[i].lng, places[j].lat, places[j].lng)
            distance_matrix_result[i][j] = int(dist)
            duration_matrix[i][j] = _estimate_duration(dist)

    logger.info(f"Distance matrix built via haversine fallback: {n}×{n}")
    return duration_matrix, distance_matrix_result
