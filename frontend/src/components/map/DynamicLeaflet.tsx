/**
 * DynamicLeaflet — Client Component wrapper for SSR-safe Leaflet import.
 * Leaflet requires browser APIs (window/document) so must be dynamically imported.
 */

"use client";

import dynamic from "next/dynamic";

const LeafletMap = dynamic(() => import("@/components/map/LeafletMap"), {
  ssr: false,
  loading: () => (
    <div
      className="map-container"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#0a0e1a",
      }}
    >
      <div style={{ textAlign: "center", color: "#5a6480" }}>
        <p style={{ fontSize: "2rem", marginBottom: "8px" }}>🏯</p>
        <p>Loading Osaka map...</p>
      </div>
    </div>
  ),
});

export default function DynamicLeaflet() {
  return <LeafletMap />;
}
