"""
Geocoding service — Nominatim (free) with popular places cache.
Works for any location worldwide.
Rate-limited to 1 request/second per Nominatim usage policy.
"""

import asyncio
import logging
import httpx
from app.config import get_settings
from app.schemas.itinerary import GeocodedPlace
from app.utils.cache import geocoding_cache

logger = logging.getLogger(__name__)

# ── Rate limiter for Nominatim (1 req/s) ────────────────────────────────
_last_request_time = 0.0
_rate_lock = asyncio.Lock()

# ── Popular places cache — instant lookup, no API call ──────────────────
# Covers major attractions in Japan, Thailand, and popular destinations
PLACES_DB: dict[str, dict] = {
    # ── Osaka ────────────────────────────────────────────────────────
    "umeda sky building": {"lat": 34.7055, "lng": 135.4903, "address": "Kita-ku, Osaka", "region": "Osaka"},
    "hep five": {"lat": 34.7039, "lng": 135.5006, "address": "Kita-ku, Osaka", "region": "Osaka"},
    "grand front osaka": {"lat": 34.7052, "lng": 135.4955, "address": "Kita-ku, Osaka", "region": "Osaka"},
    "dotonbori": {"lat": 34.6687, "lng": 135.5013, "address": "Chuo-ku, Osaka", "region": "Osaka"},
    "shinsaibashi": {"lat": 34.6745, "lng": 135.5008, "address": "Chuo-ku, Osaka", "region": "Osaka"},
    "namba": {"lat": 34.6659, "lng": 135.5010, "address": "Namba, Osaka", "region": "Osaka"},
    "namba parks": {"lat": 34.6630, "lng": 135.5018, "address": "Naniwa-ku, Osaka", "region": "Osaka"},
    "shinsekai": {"lat": 34.6524, "lng": 135.5063, "address": "Naniwa-ku, Osaka", "region": "Osaka"},
    "tsutenkaku": {"lat": 34.6525, "lng": 135.5063, "address": "Naniwa-ku, Osaka", "region": "Osaka"},
    "kuromon market": {"lat": 34.6629, "lng": 135.5069, "address": "Chuo-ku, Osaka", "region": "Osaka"},
    "amerikamura": {"lat": 34.6724, "lng": 135.4977, "address": "Chuo-ku, Osaka", "region": "Osaka"},
    "osaka castle": {"lat": 34.6873, "lng": 135.5262, "address": "Chuo-ku, Osaka", "region": "Osaka"},
    "abeno harukas": {"lat": 34.6462, "lng": 135.5133, "address": "Abeno-ku, Osaka", "region": "Osaka"},
    "shitennoji": {"lat": 34.6535, "lng": 135.5164, "address": "Tennoji-ku, Osaka", "region": "Osaka"},
    "shitennoji temple": {"lat": 34.6535, "lng": 135.5164, "address": "Tennoji-ku, Osaka", "region": "Osaka"},
    "universal studios japan": {"lat": 34.6654, "lng": 135.4323, "address": "Konohana-ku, Osaka", "region": "Osaka"},
    "usj": {"lat": 34.6654, "lng": 135.4323, "address": "Konohana-ku, Osaka", "region": "Osaka"},
    "kaiyukan": {"lat": 34.6545, "lng": 135.4290, "address": "Minato-ku, Osaka", "region": "Osaka"},
    "tempozan": {"lat": 34.6555, "lng": 135.4295, "address": "Minato-ku, Osaka", "region": "Osaka"},
    "sumiyoshi taisha": {"lat": 34.6119, "lng": 135.4928, "address": "Sumiyoshi-ku, Osaka", "region": "Osaka"},
    "hotel nikko osaka": {"lat": 34.6724, "lng": 135.5004, "address": "Chuo-ku, Osaka", "region": "Osaka"},

    # ── Kyoto ────────────────────────────────────────────────────────
    "fushimi inari": {"lat": 34.9671, "lng": 135.7727, "address": "Fushimi-ku, Kyoto", "region": "Kyoto"},
    "fushimi inari taisha": {"lat": 34.9671, "lng": 135.7727, "address": "Fushimi-ku, Kyoto", "region": "Kyoto"},
    "kinkaku-ji": {"lat": 35.0394, "lng": 135.7292, "address": "Kita-ku, Kyoto", "region": "Kyoto"},
    "kinkakuji": {"lat": 35.0394, "lng": 135.7292, "address": "Kita-ku, Kyoto", "region": "Kyoto"},
    "arashiyama": {"lat": 35.0094, "lng": 135.6672, "address": "Ukyo-ku, Kyoto", "region": "Kyoto"},
    "kiyomizu-dera": {"lat": 34.9949, "lng": 135.7850, "address": "Higashiyama-ku, Kyoto", "region": "Kyoto"},
    "kiyomizudera": {"lat": 34.9949, "lng": 135.7850, "address": "Higashiyama-ku, Kyoto", "region": "Kyoto"},
    "nijo castle": {"lat": 35.0142, "lng": 135.7481, "address": "Nakagyo-ku, Kyoto", "region": "Kyoto"},
    "gion": {"lat": 35.0037, "lng": 135.7756, "address": "Higashiyama-ku, Kyoto", "region": "Kyoto"},

    # ── Tokyo ────────────────────────────────────────────────────────
    "senso-ji": {"lat": 35.7148, "lng": 139.7967, "address": "Asakusa, Taito-ku, Tokyo", "region": "Tokyo"},
    "sensoji": {"lat": 35.7148, "lng": 139.7967, "address": "Asakusa, Taito-ku, Tokyo", "region": "Tokyo"},
    "tokyo tower": {"lat": 35.6586, "lng": 139.7454, "address": "Minato-ku, Tokyo", "region": "Tokyo"},
    "tokyo skytree": {"lat": 35.7101, "lng": 139.8107, "address": "Sumida-ku, Tokyo", "region": "Tokyo"},
    "meiji shrine": {"lat": 35.6764, "lng": 139.6993, "address": "Shibuya-ku, Tokyo", "region": "Tokyo"},
    "shibuya crossing": {"lat": 35.6595, "lng": 139.7004, "address": "Shibuya, Tokyo", "region": "Tokyo"},
    "shinjuku": {"lat": 35.6938, "lng": 139.7034, "address": "Shinjuku, Tokyo", "region": "Tokyo"},
    "akihabara": {"lat": 35.7023, "lng": 139.7745, "address": "Chiyoda-ku, Tokyo", "region": "Tokyo"},
    "tsukiji outer market": {"lat": 35.6654, "lng": 139.7707, "address": "Chuo-ku, Tokyo", "region": "Tokyo"},
    "teamlab borderless": {"lat": 35.6256, "lng": 139.7843, "address": "Odaiba, Tokyo", "region": "Tokyo"},
    "imperial palace": {"lat": 35.6852, "lng": 139.7528, "address": "Chiyoda-ku, Tokyo", "region": "Tokyo"},
    "harajuku": {"lat": 35.6702, "lng": 139.7026, "address": "Shibuya-ku, Tokyo", "region": "Tokyo"},
    "ueno park": {"lat": 35.7146, "lng": 139.7714, "address": "Taito-ku, Tokyo", "region": "Tokyo"},
    "odaiba": {"lat": 35.6273, "lng": 139.7750, "address": "Minato-ku, Tokyo", "region": "Tokyo"},
    "ginza": {"lat": 35.6717, "lng": 139.7649, "address": "Chuo-ku, Tokyo", "region": "Tokyo"},
    "roppongi": {"lat": 35.6628, "lng": 139.7315, "address": "Minato-ku, Tokyo", "region": "Tokyo"},
    "hotel gracery shinjuku": {"lat": 35.6942, "lng": 139.7014, "address": "Shinjuku-ku, Tokyo", "region": "Tokyo"},

    # ── Nara ─────────────────────────────────────────────────────────
    "nara park": {"lat": 34.6851, "lng": 135.8430, "address": "Nara", "region": "Nara"},
    "todai-ji": {"lat": 34.6891, "lng": 135.8398, "address": "Nara", "region": "Nara"},
    "todai-ji temple": {"lat": 34.6891, "lng": 135.8398, "address": "Nara", "region": "Nara"},
    "kasuga taisha": {"lat": 34.6812, "lng": 135.8498, "address": "Nara", "region": "Nara"},

    # ── Kobe ─────────────────────────────────────────────────────────
    "kobe harborland": {"lat": 34.6800, "lng": 135.1856, "address": "Chuo-ku, Kobe", "region": "Kobe"},
    "meriken park": {"lat": 34.6830, "lng": 135.1890, "address": "Chuo-ku, Kobe", "region": "Kobe"},
    "kitano ijinkan": {"lat": 34.6988, "lng": 135.1913, "address": "Chuo-ku, Kobe", "region": "Kobe"},

    # ── Hokkaido ─────────────────────────────────────────────────────
    "sapporo clock tower": {"lat": 43.0625, "lng": 141.3536, "address": "Chuo-ku, Sapporo", "region": "Sapporo"},
    "otaru canal": {"lat": 43.1972, "lng": 140.9945, "address": "Otaru, Hokkaido", "region": "Hokkaido"},
    "sapporo beer museum": {"lat": 43.0706, "lng": 141.3634, "address": "Higashi-ku, Sapporo", "region": "Sapporo"},
    "odori park": {"lat": 43.0601, "lng": 141.3563, "address": "Chuo-ku, Sapporo", "region": "Sapporo"},
    "sapporo central wholesale market": {"lat": 43.0639, "lng": 141.3320, "address": "Chuo-ku, Sapporo", "region": "Sapporo"},
    "biei blue pond": {"lat": 43.4292, "lng": 142.6028, "address": "Biei, Hokkaido", "region": "Hokkaido"},
    "mount moiwa": {"lat": 43.0230, "lng": 141.3275, "address": "Minami-ku, Sapporo", "region": "Sapporo"},
    "noboribetsu onsen": {"lat": 42.4865, "lng": 141.1714, "address": "Noboribetsu, Hokkaido", "region": "Hokkaido"},
    "furano lavender fields": {"lat": 43.3412, "lng": 142.3824, "address": "Furano, Hokkaido", "region": "Hokkaido"},

    # ── Hiroshima ────────────────────────────────────────────────────
    "hiroshima peace memorial": {"lat": 34.3955, "lng": 132.4536, "address": "Naka-ku, Hiroshima", "region": "Hiroshima"},
    "itsukushima shrine": {"lat": 34.2961, "lng": 132.3198, "address": "Miyajima, Hiroshima", "region": "Hiroshima"},
    "miyajima": {"lat": 34.2961, "lng": 132.3198, "address": "Hatsukaichi, Hiroshima", "region": "Hiroshima"},

    # ── Bangkok ──────────────────────────────────────────────────────
    "grand palace": {"lat": 13.7500, "lng": 100.4914, "address": "Phra Nakhon, Bangkok", "region": "Bangkok"},
    "wat pho": {"lat": 13.7463, "lng": 100.4928, "address": "Phra Nakhon, Bangkok", "region": "Bangkok"},
    "wat arun": {"lat": 13.7437, "lng": 100.4888, "address": "Bangkok Yai, Bangkok", "region": "Bangkok"},
    "chatuchak market": {"lat": 13.7999, "lng": 100.5506, "address": "Chatuchak, Bangkok", "region": "Bangkok"},
    "khao san road": {"lat": 13.7589, "lng": 100.4974, "address": "Phra Nakhon, Bangkok", "region": "Bangkok"},
    "terminal 21": {"lat": 13.7379, "lng": 100.5600, "address": "Sukhumvit, Bangkok", "region": "Bangkok"},
    "icon siam": {"lat": 13.7262, "lng": 100.5105, "address": "Khlong San, Bangkok", "region": "Bangkok"},
    "jim thompson house": {"lat": 13.7490, "lng": 100.5291, "address": "Pathum Wan, Bangkok", "region": "Bangkok"},
    "centara grand centralworld": {"lat": 13.7468, "lng": 100.5392, "address": "Pathum Wan, Bangkok", "region": "Bangkok"},

    # ── Chiang Mai ───────────────────────────────────────────────────
    "doi suthep": {"lat": 18.8048, "lng": 98.9219, "address": "Chiang Mai", "region": "Chiang Mai"},
    "chiang mai old city": {"lat": 18.7874, "lng": 98.9931, "address": "Chiang Mai", "region": "Chiang Mai"},
    "chiang mai night bazaar": {"lat": 18.7861, "lng": 99.0002, "address": "Chiang Mai", "region": "Chiang Mai"},
    "elephant nature park": {"lat": 19.1544, "lng": 98.7929, "address": "Mae Taeng, Chiang Mai", "region": "Chiang Mai"},

    # ── Phuket ───────────────────────────────────────────────────────
    "patong beach": {"lat": 7.8804, "lng": 98.2920, "address": "Patong, Phuket", "region": "Phuket"},
    "big buddha phuket": {"lat": 7.8276, "lng": 98.3131, "address": "Chalong, Phuket", "region": "Phuket"},
    "old phuket town": {"lat": 7.8847, "lng": 98.3889, "address": "Phuket Town", "region": "Phuket"},
    "phi phi islands": {"lat": 7.7407, "lng": 98.7784, "address": "Krabi/Phuket", "region": "Phuket"},
}


def _normalize_name(name: str) -> str:
    """Normalize a place name for matching."""
    return name.lower().strip().replace("'", "").replace("'", "")


async def geocode_place(place_name: str) -> GeocodedPlace | None:
    """
    Geocode a place name — checks cache first, then Nominatim.
    Works for any location worldwide.
    """
    normalized = _normalize_name(place_name)

    # ── Check places DB first (instant, no rate limit) ──────────────
    for key, data in PLACES_DB.items():
        if key == normalized:
            result = GeocodedPlace(
                name=place_name.title() if place_name.islower() else place_name,
                lat=data["lat"],
                lng=data["lng"],
                address=data["address"],
                district=data["region"],
            )
            logger.info(f"Cache hit: '{place_name}' → ({data['lat']}, {data['lng']}) [{data['region']}]")
            return result

    # ── Check runtime cache ─────────────────────────────────────────
    cached = geocoding_cache.get(normalized)
    if cached:
        logger.debug(f"Runtime cache HIT: {place_name}")
        return cached

    # ── Call Nominatim (global search) ──────────────────────────────
    settings = get_settings()
    try:
        global _last_request_time
        async with _rate_lock:
            now = asyncio.get_event_loop().time()
            wait_time = max(0, 1.0 - (now - _last_request_time))
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            _last_request_time = asyncio.get_event_loop().time()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.nominatim_url}/search",
                params={
                    "q": place_name,
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 1,
                },
                headers={"User-Agent": settings.nominatim_user_agent},
                timeout=10.0,
            )
            response.raise_for_status()
            results = response.json()

        if results:
            r = results[0]
            lat = float(r["lat"])
            lng = float(r["lon"])
            address = r.get("display_name", "")
            
            # Extract region from address details
            addr = r.get("address", {})
            region = (
                addr.get("city")
                or addr.get("town")
                or addr.get("state")
                or addr.get("county")
                or addr.get("country")
                or ""
            )

            place = GeocodedPlace(
                name=place_name,
                lat=lat,
                lng=lng,
                address=address,
                district=region,
            )
            geocoding_cache.set(normalized, place)
            logger.info(f"Nominatim: '{place_name}' → ({lat}, {lng}) [{region}]")
            return place

    except Exception as e:
        logger.error(f"Nominatim error for '{place_name}': {e}")

    logger.warning(f"Could not geocode: '{place_name}'")
    return None
