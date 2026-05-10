/**
 * TypeScript interfaces matching backend Pydantic schemas.
 * Adapted for open-source stack: GeoJSON geometry, districts, trip persistence.
 */

export interface GeocodedPlace {
  name: string;
  lat: number;
  lng: number;
  address: string;
  district: string;
}

export interface RouteSegment {
  from_place: GeocodedPlace;
  to_place: GeocodedPlace;
  distance_meters: number;
  duration_seconds: number;
  route_geometry: [number, number][]; // [[lng, lat], ...]
  google_maps_url: string;
}

export interface DayPlan {
  day_number: number;
  color: string;
  district_name: string;
  places: GeocodedPlace[];
  route_segments: RouteSegment[];
  total_distance_meters: number;
  total_duration_seconds: number;
}

export interface ItineraryResponse {
  trip_id: string;
  hotel: GeocodedPlace;
  days: DayPlan[];
  ai_explanation: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  message: string;
  conversation_history: ChatMessage[];
}

export interface ChatResponse {
  assistant_message: string;
  itinerary: ItineraryResponse | null;
}
