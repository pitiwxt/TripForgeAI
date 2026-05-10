"""
Google Maps deep link URL generator.
Produces universal directions URLs that open in Google Maps
for real-time navigation handoff.
"""


def generate_directions_url(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    travel_mode: str = "transit",
) -> str:
    """
    Generate a Google Maps Directions deep link.
    
    Args:
        origin_lat: Origin latitude (WGS84)
        origin_lng: Origin longitude (WGS84)
        dest_lat: Destination latitude (WGS84)
        dest_lng: Destination longitude (WGS84)
        travel_mode: One of 'transit', 'driving', 'walking', 'bicycling'
    
    Returns:
        A URL that opens Google Maps with directions pre-filled.
        Works on mobile (opens app) and desktop (opens web).
    """
    return (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={origin_lat},{origin_lng}"
        f"&destination={dest_lat},{dest_lng}"
        f"&travelmode={travel_mode}"
    )


def generate_place_url(lat: float, lng: float, name: str = "") -> str:
    """
    Generate a Google Maps place link for a single location.
    
    Args:
        lat: Place latitude
        lng: Place longitude
        name: Optional place name for the pin label
    
    Returns:
        A URL that opens Google Maps centered on this location.
    """
    import urllib.parse
    query = urllib.parse.quote(name) if name else f"{lat},{lng}"
    return f"https://www.google.com/maps/search/?api=1&query={query}"
