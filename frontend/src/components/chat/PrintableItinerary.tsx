import React from "react";
import type { ItineraryResponse } from "@/types";
import { formatDuration, formatDistance } from "@/lib/constants";

export default function PrintableItinerary({ itinerary }: { itinerary: ItineraryResponse }) {
  if (!itinerary) return null;

  return (
    <div
      id="printable-itinerary-container"
      style={{
        position: "fixed",
        top: "-9999px",
        left: "-9999px",
        width: "800px",
        backgroundColor: "white",
        color: "black",
        fontFamily: "Arial, sans-serif",
        padding: "0",
        margin: "0",
        zIndex: -1000,
      }}
    >
      {/* ── HEADER BLOCK ── */}
      <div id="print-block-header" style={{ padding: "40px 40px 20px 40px", backgroundColor: "white" }}>
        <div style={{ borderBottom: "3px solid black", paddingBottom: "10px", marginBottom: "20px" }}>
          <h1 style={{ fontSize: "32px", fontWeight: "bold", margin: 0, textTransform: "uppercase", letterSpacing: "1px", color: "black" }}>
            Official Travel Itinerary
          </h1>
          <p style={{ fontSize: "14px", color: "#555", margin: "5px 0 0 0" }}>
            Generated on {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
          </p>
        </div>

        <div style={{ border: "1px solid #ccc", padding: "15px", backgroundColor: "#fafafa" }}>
          <h2 style={{ fontSize: "12px", textTransform: "uppercase", color: "#666", margin: "0 0 8px 0" }}>
            Primary Accommodation
          </h2>
          <p style={{ fontSize: "18px", fontWeight: "bold", margin: "0 0 4px 0", color: "black" }}>
            {itinerary.hotel.name}
          </p>
          <p style={{ fontSize: "12px", color: "#333", margin: 0 }}>
            {itinerary.hotel.address}
          </p>
        </div>
      </div>

      {/* ── DAY BLOCKS ── */}
      {itinerary.days.map((day) => (
        <div
          key={day.day_number}
          id={`print-block-day-${day.day_number}`}
          className="print-block-day"
          style={{ padding: "20px 40px", backgroundColor: "white" }}
        >
          <div style={{ backgroundColor: "#222", color: "white", padding: "10px 15px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ fontSize: "16px", margin: 0, fontWeight: "bold", color: "white" }}>
              DAY {day.day_number} - {day.district_name.toUpperCase()}
            </h3>
            <span style={{ fontSize: "12px", color: "white" }}>
              Total: {formatDistance(day.total_distance_meters)} | {formatDuration(day.total_duration_seconds)}
            </span>
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "15px" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #ccc" }}>
                <th style={{ textAlign: "left", padding: "8px", width: "10%", fontSize: "12px", color: "#666" }}>#</th>
                <th style={{ textAlign: "left", padding: "8px", width: "40%", fontSize: "12px", color: "#666" }}>DESTINATION</th>
                <th style={{ textAlign: "left", padding: "8px", width: "50%", fontSize: "12px", color: "#666" }}>ADDRESS / NOTES</th>
              </tr>
            </thead>
            <tbody>
              {day.places.map((place, idx) => (
                <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: "12px 8px", fontSize: "14px", fontWeight: "bold", verticalAlign: "top", color: "black" }}>
                    {idx + 1}
                  </td>
                  <td style={{ padding: "12px 8px", fontSize: "14px", fontWeight: "bold", verticalAlign: "top", color: "black" }}>
                    {place.name}
                  </td>
                  <td style={{ padding: "12px 8px", fontSize: "12px", color: "#444", verticalAlign: "top" }}>
                    {place.address}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {day.route_segments.length > 0 && (
            <div style={{ marginTop: "15px", padding: "10px", backgroundColor: "#f9f9f9", borderLeft: "3px solid #ccc" }}>
              <h4 style={{ fontSize: "11px", textTransform: "uppercase", color: "#666", margin: "0 0 5px 0" }}>Navigation Route</h4>
              <p style={{ fontSize: "11px", color: "#444", margin: 0, lineHeight: 1.5 }}>
                {day.route_segments.map((seg, idx) => (
                  <span key={idx}>
                    <strong>{seg.from_place.name}</strong> → <em>({formatDistance(seg.distance_meters)}, {formatDuration(seg.duration_seconds)})</em> → {idx === day.route_segments.length - 1 ? <strong>{seg.to_place.name}</strong> : ""}
                  </span>
                ))}
              </p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
