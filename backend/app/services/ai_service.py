"""
AI Service — Groq (Llama 4 Scout) via OpenAI-compatible API.
Global travel planner — works for any destination worldwide.
"""

import json
import logging
import re
import asyncio
import aiohttp

from app.config import get_settings
from app.schemas.itinerary import GeocodedPlace, ItineraryResponse
from app.services.geocoding_service import geocode_place
from app.services.routing_optimizer import generate_itinerary

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are TripForge AI — a smart, friendly travel planning assistant.
You help plan trips to ANY destination worldwide.

## YOUR TOOLS
1. generate_itinerary — Create a NEW trip plan from scratch
2. modify_itinerary — Change the CURRENT plan
3. search_place — Look up an unknown place

## CRITICAL RULES

### Always provide enough places!
Number of places MUST be >= num_days × 2 (at least 2 per day).
3-day trip → 6-8 places. 5-day trip → 10-12 places. 7-day trip → 14+ places.
Use SPECIFIC attraction names: "Senso-ji Temple" not "temple", "Chatuchak Weekend Market" not "market".
Append the city name to help geocoding: "Grand Palace, Bangkok", "Otaru Canal, Hokkaido".
If the user explicitly specifies what places go on which days (e.g. "Day 1: X, Day 2: Y"), you MUST use the `daily_places` parameter instead of `requested_places` to preserve their exact day assignments.

### Hotel selection — MUST be in the SAME area as attractions!
The hotel MUST be located IN the destination city/region, NOT a random city.
- "trip to Chiang Mai" → hotel in Chiang Mai (e.g. "Le Meridien Chiang Mai")
- "trip to Hokkaido" → hotel in Sapporo (e.g. "JR Tower Hotel Nikko Sapporo")  
- "trip to Phuket" → hotel in Phuket (e.g. "Kata Rocks Resort, Phuket")
- "trip to Tokyo" → hotel in Tokyo (e.g. "Hotel Gracery Shinjuku, Tokyo")
- "trip to Bangkok" → hotel in Bangkok (e.g. "Centara Grand, Bangkok")
- "trip to Osaka" → hotel in Osaka (e.g. "Hotel Nikko Osaka")
NEVER pick a hotel in a different city from the attractions!

### Regenerate (rebuild) the plan:
Use modify_itinerary with action="regenerate" + all_places = full list of ALL desired places.

### For casual chat (greetings, food tips, general questions):
Just respond naturally. NO tool call needed.

## INTELLIGENCE
- Understand what the user WANTS, not just literal commands.
- "plan trip Hokkaido 3 days" → pick Sapporo hotel + Hokkaido attractions
- "ไป เชียงใหม่ 2 วัน" → pick Chiang Mai hotel + Chiang Mai attractions  
- "I want day 2 in Kyoto" → keep other days, add Kyoto attractions for day 2
- "add something fun" → pick an appropriate attraction for the current destination
- "what should I eat?" → give local food recommendations, NO tool call
- Respond in the user's language (Thai/English/Japanese/etc.)
- All place names should be in English for reliable geocoding.

## CURRENT PLAN
Check CURRENT_ITINERARY below for what the user already has."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_itinerary",
            "description": "Generate a new optimized travel itinerary for any destination. Pick a suitable hotel if none specified.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hotel_name": {"type": "string", "description": "Hotel name or 'lat,lng' coordinates"},
                    "requested_places": {"type": "array", "items": {"type": "string"}, "description": "All attractions/places to visit (use specific names)"},
                    "daily_places": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}, "description": "Use this INSTEAD of requested_places if the user explicitly assigns places to specific days (e.g. Day 1: X, Day 2: Y)."},
                    "num_days": {"type": "integer", "description": "Number of days"},
                },
                "required": ["hotel_name", "num_days"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "modify_itinerary",
            "description": "Modify the current plan. For complex changes use action='regenerate' with all_places.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add", "remove", "swap", "change_days", "regenerate"]},
                    "place_name": {"type": "string", "description": "Place to add/remove"},
                    "swap_with": {"type": "string", "description": "Replacement place (for swap)"},
                    "new_num_days": {"type": "integer", "description": "New number of days"},
                    "all_places": {"type": "array", "items": {"type": "string"}, "description": "Full list of ALL desired places (for regenerate). Include existing + new."},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_place",
            "description": "Search for a place anywhere in the world.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Place name + city/country"},
                },
                "required": ["query"],
            },
        },
    },
]


def _build_context(itin: dict | None) -> str:
    if not itin:
        return "\n\nCURRENT_ITINERARY: None (no plan yet)"
    hotel = itin.get("hotel", {})
    days = itin.get("days", [])
    lines = ["\n\nCURRENT_ITINERARY:"]
    lines.append(f"  Hotel: {hotel.get('name', '?')} ({hotel.get('lat', 0):.4f}, {hotel.get('lng', 0):.4f})")
    for d in days:
        names = [p.get("name", "?") for p in d.get("places", [])]
        if names:
            lines.append(f"  Day {d.get('day_number')} [{d.get('district_name', '')}]: {' → '.join(names)}")
    all_names = [p.get("name", "") for d in days for p in d.get("places", [])]
    lines.append(f"  All places: {', '.join(all_names)}")
    return "\n".join(lines)


def _extract_current(itin: dict | None) -> tuple[str | None, list[str], int]:
    if not itin:
        return None, [], 0
    hotel = itin.get("hotel", {})
    lat, lng = hotel.get("lat", 0), hotel.get("lng", 0)
    ref = f"{lat},{lng}" if lat and lng else hotel.get("name", "")
    names = [p["name"] for d in itin.get("days", []) for p in d.get("places", [])]
    return ref, names, len(itin.get("days", []))


async def _call_groq(messages: list[dict], tools: list | None = None) -> dict:
    """Call Groq API with retry for rate limits."""
    settings = get_settings()
    payload = {
        "model": settings.groq_model,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 1024,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    last_error = None
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{settings.groq_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 429:
                        wait = min(2 ** attempt * 2, 10)
                        logger.warning(f"Groq rate limited (attempt {attempt+1}), waiting {wait}s")
                        await asyncio.sleep(wait)
                        last_error = "rate_limit"
                        continue
                    if resp.status != 200:
                        body = await resp.text()
                        raise Exception(f"Groq API {resp.status}: {body[:200]}")
                    return await resp.json()
        except aiohttp.ClientError as e:
            logger.warning(f"Connection error (attempt {attempt+1}): {e}")
            last_error = "connection"
            await asyncio.sleep(2)
            continue
        except Exception as e:
            if last_error == "rate_limit":
                continue
            raise

    raise Exception(f"groq_{last_error}_after_retries")


async def process_chat(
    user_message: str,
    conversation_history: list[dict],
    current_itinerary: dict | None = None,
) -> tuple[str, ItineraryResponse | None]:
    """Process chat message through Groq AI."""
    try:
        context = _build_context(current_itinerary)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in conversation_history[-16:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": f"{user_message}{context}"})

        result = await _call_groq(messages, TOOLS)
        choice = result["choices"][0]
        msg = choice["message"]

        if msg.get("tool_calls"):
            tc = msg["tool_calls"][0]
            fn_name = tc["function"]["name"]
            fn_args = json.loads(tc["function"]["arguments"])
            logger.info(f"Tool call: {fn_name} → {fn_args}")
            return await _handle_tool(fn_name, fn_args, current_itinerary)

        return msg.get("content", "How can I help plan your trip?"), None

    except Exception as e:
        logger.error(f"AI error: {e}", exc_info=True)
        err = str(e).lower()
        if "rate_limit" in err or "429" in err:
            return "I'm getting too many requests right now. Please wait a few seconds and try again! ⏳", None
        if "connection" in err or "timeout" in err:
            return "Having trouble connecting to AI. Please check your internet and try again. 🔄", None
        if "json" in err:
            return "I got a confused response. Could you rephrase that? 🤔", None
        return f"Something went wrong ({type(e).__name__}). Please try again. 🙏", None


async def _handle_tool(name: str, args: dict, current_itinerary: dict | None):
    """Handle tool calls from AI."""
    if name == "generate_itinerary":
        hotel = args.get("hotel_name", "")
        places = list(args.get("requested_places", []))
        daily_places = args.get("daily_places", [])
        days = int(args.get("num_days", len(daily_places) or 2))

        itin = await _build_itinerary(hotel, places, days, daily_places)
        if not itin:
            return "I had trouble finding some places. Try more specific names (e.g. 'Senso-ji Temple, Tokyo').", None
        return _format_summary(itin), itin

    elif name == "modify_itinerary":
        if not current_itinerary:
            return "No plan to modify yet! Tell me where you want to go.", None

        action = args.get("action", "regenerate")
        place = args.get("place_name", "")
        swap_with = args.get("swap_with", "")
        new_days = args.get("new_num_days")
        all_places = args.get("all_places", [])

        ref, places, num_days = _extract_current(current_itinerary)
        if new_days:
            num_days = int(new_days)

        if action == "regenerate" and all_places:
            places = list(all_places)
            desc = "Rebuilt your plan"
        elif action == "add" and place:
            if place.lower() in [p.lower() for p in places]:
                return f"**{place}** is already in your plan!", None
            places.append(place)
            desc = f"Added **{place}**"
        elif action == "remove" and place:
            before = len(places)
            places = [p for p in places if p.lower() != place.lower()]
            if len(places) == before:
                return f"\"{place}\" isn't in your plan. Current places: {', '.join(places)}", None
            desc = f"Removed **{place}**"
        elif action == "swap" and place and swap_with:
            places = [swap_with if p.lower() == place.lower() else p for p in places]
            desc = f"Swapped **{place}** → **{swap_with}**"
        elif action == "change_days" and new_days:
            desc = f"Changed to **{num_days} days**"
        else:
            desc = "Updated"

        if not places:
            return "No places left! What would you like to visit?", None

        itin = await _build_itinerary(ref, places, num_days)
        if not itin:
            failed = place or (all_places[-1] if all_places else "some places")
            return f"Trouble finding \"{failed}\". Try a more specific name?", None

        return f"✅ {desc}!\n\n{_format_summary(itin)}", itin

    elif name == "search_place":
        query = args.get("query", "")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": query, "format": "json", "limit": 3},
                    headers={"User-Agent": "TripForge/2.0"},
                ) as resp:
                    if resp.status == 200:
                        results = await resp.json()
                        if results:
                            r = results[0]
                            name = r.get("display_name", "").split(",")[0]
                            return f"Found **{name}** 📍\n{r.get('display_name', '')}\nCoordinates: {r['lat']}, {r['lon']}\n\nWant me to add it to your plan?", None
        except Exception as e:
            logger.error(f"Search error: {e}")
        return f"Couldn't find \"{query}\". Try a more specific name?", None

    return "I'm not sure how to handle that. Could you rephrase?", None


async def _build_itinerary(hotel_input: str, place_names: list[str], num_days: int, daily_place_names: list[list[str]] = None) -> ItineraryResponse | None:
    """Geocode places and build optimized itinerary — works for any location."""
    coord = re.match(r'^\s*(-?\d+\.?\d*)\s*[,\s]\s*(-?\d+\.?\d*)\s*$', hotel_input)
    if coord:
        lat, lng = float(coord.group(1)), float(coord.group(2))
        hotel = GeocodedPlace(name="Hotel", lat=lat, lng=lng, address=f"{lat}, {lng}", district="")
    else:
        hotel = await geocode_place(hotel_input)
        if not hotel:
            return None

    if daily_place_names:
        daily_clusters = []
        for day_names in daily_place_names:
            cluster = []
            for name in day_names:
                c = re.match(r'^\s*(-?\d+\.?\d*)\s*[,\s]\s*(-?\d+\.?\d*)\s*$', name)
                if c:
                    cluster.append(GeocodedPlace(name=name, lat=float(c.group(1)), lng=float(c.group(2)), address="", district=""))
                else:
                    p = await geocode_place(name)
                    if p:
                        cluster.append(p)
            daily_clusters.append(cluster)
        
        return await generate_itinerary(hotel=hotel, daily_clusters=daily_clusters)

    places = []
    for name in place_names:
        c = re.match(r'^\s*(-?\d+\.?\d*)\s*[,\s]\s*(-?\d+\.?\d*)\s*$', name)
        if c:
            places.append(GeocodedPlace(name=name, lat=float(c.group(1)), lng=float(c.group(2)), address="", district=""))
        else:
            p = await geocode_place(name)
            if p:
                places.append(p)

    if not places:
        return None

    # Ensure num_days doesn't exceed place count
    num_days = max(1, min(num_days, len(places)))
    return await generate_itinerary(hotel=hotel, places=places, num_days=num_days)


def _format_summary(itin: ItineraryResponse) -> str:
    """Format itinerary as readable text."""
    lines = []
    for d in itin.days:
        if not d.places:
            continue
        names = " → ".join([p.name for p in d.places])
        mins = d.total_duration_seconds // 60
        km = d.total_distance_meters / 1000
        area = f" [{d.district_name}]" if d.district_name else ""
        lines.append(f"**Day {d.day_number}{area}:** {names} (~{mins}min, {km:.1f}km)")
    lines.append("\nWant to change anything? Just tell me!")
    return "\n".join(lines)
