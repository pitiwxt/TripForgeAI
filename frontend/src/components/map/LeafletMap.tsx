/**
 * LeafletMap — Main map component using Leaflet.js + OpenStreetMap tiles.
 * Renders markers, route polylines, and popups synced with Zustand state.
 */

"use client";

import { useEffect, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import { useTravelStore } from "@/providers/TravelStoreProvider";
import {
  OSAKA_CENTER,
  DEFAULT_ZOOM,
  HOTEL_COLOR,
  getDayColor,
  formatDuration,
  formatDistance,
  DISTRICT_EMOJI,
} from "@/lib/constants";
import type { GeocodedPlace, DayPlan } from "@/types";

// ── Custom marker icons ────────────────────────────────────────────────
function createNumberedIcon(number: number, color: string, isHotel = false): L.DivIcon {
  const label = isHotel ? "🏨" : `${number}`;
  const size = isHotel ? 36 : 30;
  const bg = isHotel ? HOTEL_COLOR : color;

  return L.divIcon({
    className: "custom-marker",
    html: `<div style="
      width:${size}px;height:${size}px;
      border-radius:50%;
      background:${bg};
      color:#fff;
      display:flex;align-items:center;justify-content:center;
      font-weight:700;font-size:${isHotel ? 18 : 13}px;
      border:3px solid rgba(255,255,255,0.9);
      box-shadow:0 2px 8px rgba(0,0,0,0.4);
      cursor:pointer;
    ">${label}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

// ── Auto-fit bounds component ──────────────────────────────────────────
function FitBounds({ places, hotel }: { places: GeocodedPlace[]; hotel?: GeocodedPlace }) {
  const map = useMap();

  useEffect(() => {
    const points: L.LatLngExpression[] = [];
    if (hotel) points.push([hotel.lat, hotel.lng]);
    places.forEach((p) => points.push([p.lat, p.lng]));

    if (points.length >= 2) {
      const bounds = L.latLngBounds(points);
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15, animate: true });
    } else if (points.length === 1) {
      map.setView(points[0], 14, { animate: true });
    }
  }, [map, places, hotel]);

  return null;
}

// ── Resize handler — fixes tiles when chat panel collapses ─────────────
function ResizeHandler() {
  const map = useMap();

  useEffect(() => {
    const observer = new ResizeObserver(() => {
      setTimeout(() => map.invalidateSize(), 100);
    });

    const container = map.getContainer();
    if (container.parentElement) {
      observer.observe(container.parentElement);
    }

    return () => observer.disconnect();
  }, [map]);

  return null;
}

// ── Main component ─────────────────────────────────────────────────────
export default function LeafletMap() {
  const itinerary = useTravelStore((s) => s.itinerary);
  const selectedDay = useTravelStore((s) => s.selectedDay);

  const visibleDays =
    itinerary?.days.filter(
      (day) => selectedDay === null || day.day_number === selectedDay
    ) || [];

  const allVisiblePlaces = visibleDays.flatMap((d) => d.places);

  return (
    <div className="map-container">
      <MapContainer
        center={[OSAKA_CENTER.lat, OSAKA_CENTER.lng]}
        zoom={DEFAULT_ZOOM}
        style={{ width: "100%", height: "100%" }}
        zoomControl={false}
      >
        {/* CartoDB Voyager tiles — clean, English labels */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
          subdomains="abcd"
          maxZoom={20}
        />

        {/* Handle container resize (chat panel toggle) */}
        <ResizeHandler />

        {/* Auto-fit bounds */}
        {itinerary && (
          <FitBounds places={allVisiblePlaces} hotel={itinerary.hotel} />
        )}

        {/* Hotel marker */}
        {itinerary && (
          <Marker
            position={[itinerary.hotel.lat, itinerary.hotel.lng]}
            icon={createNumberedIcon(0, HOTEL_COLOR, true)}
          >
            <Popup className="custom-popup">
              <div className="popup-content">
                <h3>🏨 {itinerary.hotel.name}</h3>
                <p className="popup-address">{itinerary.hotel.address}</p>
                <p className="popup-district">
                  {DISTRICT_EMOJI[itinerary.hotel.district] || "📍"}{" "}
                  {itinerary.hotel.district}
                </p>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Day markers */}
        {visibleDays.map((day) =>
          day.places.map((place, idx) => (
            <Marker
              key={`marker-${day.day_number}-${idx}`}
              position={[place.lat, place.lng]}
              icon={createNumberedIcon(idx + 1, day.color)}
            >
              <Popup className="custom-popup">
                <div className="popup-content">
                  <h3>
                    <span
                      className="popup-day-badge"
                      style={{ background: day.color }}
                    >
                      Day {day.day_number}
                    </span>
                    {place.name}
                  </h3>
                  <p className="popup-address">{place.address}</p>
                  <p className="popup-district">
                    {DISTRICT_EMOJI[place.district] || "📍"} {place.district}
                  </p>
                </div>
              </Popup>
            </Marker>
          ))
        )}

        {/* Route polylines */}
        {visibleDays.map((day) =>
          day.route_segments.map((seg, idx) => {
            // Convert [lng, lat] to [lat, lng] for Leaflet
            const positions: [number, number][] = seg.route_geometry.map(
              ([lng, lat]) => [lat, lng]
            );

            if (positions.length < 2) return null;

            // Midpoint for distance label
            const midIdx = Math.floor(positions.length / 2);
            const midPos = positions[midIdx];

            return (
              <div key={`route-${day.day_number}-${idx}`}>
                {/* Glow effect (wider, transparent) */}
                <Polyline
                  positions={positions}
                  pathOptions={{
                    color: day.color,
                    weight: 8,
                    opacity: 0.25,
                  }}
                />
                {/* Main line */}
                <Polyline
                  positions={positions}
                  pathOptions={{
                    color: day.color,
                    weight: 4,
                    opacity: 0.85,
                    dashArray: "8 4",
                  }}
                />
                {/* Distance overlay at midpoint */}
                {midPos && (
                  <Marker
                    position={midPos}
                    icon={L.divIcon({
                      className: "distance-overlay",
                      html: `<div class="distance-pill" style="border-color:${day.color}">
                        ${formatDistance(seg.distance_meters)} · ${formatDuration(seg.duration_seconds)}
                      </div>`,
                      iconSize: [120, 24],
                      iconAnchor: [60, 12],
                    })}
                    interactive={false}
                  />
                )}
              </div>
            );
          })
        )}
      </MapContainer>
    </div>
  );
}
