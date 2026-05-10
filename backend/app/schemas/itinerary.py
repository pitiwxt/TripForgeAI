"""
Pydantic schemas for the structured itinerary output.
Adapted for open-source stack: Nominatim + OSRM + Leaflet.
"""

from pydantic import BaseModel, Field


class GeocodedPlace(BaseModel):
    """A geocoded point of interest with coordinates."""
    name: str = Field(..., description="Place display name")
    lat: float = Field(..., description="Latitude (WGS84)")
    lng: float = Field(..., description="Longitude (WGS84)")
    address: str = Field(default="", description="Formatted street address")
    district: str = Field(default="", description="Region/area name (e.g. city, district, or state)")


class RouteSegment(BaseModel):
    """A single leg of the journey between two consecutive points."""
    from_place: GeocodedPlace
    to_place: GeocodedPlace
    distance_meters: int = Field(..., description="Route distance in meters")
    duration_seconds: int = Field(..., description="Estimated travel time in seconds")
    route_geometry: list[list[float]] = Field(
        default_factory=list,
        description="GeoJSON-style coordinate pairs [[lng, lat], ...] from OSRM",
    )
    google_maps_url: str = Field(
        ...,
        description="Google Maps Directions deep link for real navigation",
    )


class DayPlan(BaseModel):
    """A complete plan for one day of travel."""
    day_number: int = Field(..., ge=1, description="1-indexed day number")
    color: str = Field(..., description="Hex color code for map visualization")
    district_name: str = Field(default="", description="Primary district for this day")
    places: list[GeocodedPlace] = Field(
        ..., description="Ordered list of POIs to visit this day"
    )
    route_segments: list[RouteSegment] = Field(
        ..., description="Route legs connecting places in sequence"
    )
    total_distance_meters: int = Field(
        default=0, description="Sum of all segment distances"
    )
    total_duration_seconds: int = Field(
        default=0, description="Sum of all segment durations"
    )


class ItineraryResponse(BaseModel):
    """Complete multi-day optimized itinerary."""
    trip_id: str = Field(default="", description="Supabase trip ID for persistence")
    hotel: GeocodedPlace = Field(..., description="Base accommodation (TSP depot)")
    days: list[DayPlan] = Field(
        ..., description="Day-by-day ordered plans"
    )
    ai_explanation: str = Field(
        default="",
        description="LLM-generated natural language explanation of routing logic",
    )
