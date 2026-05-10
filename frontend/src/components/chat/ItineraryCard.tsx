/**
 * ItineraryCard — Rich day-by-day itinerary display with Osaka district labels,
 * route timeline, Google Maps navigate buttons, and premium PDF export.
 */

"use client";

import { useState } from "react";
import { useTravelStore } from "@/providers/TravelStoreProvider";
import {
  getDayColor,
  formatDuration,
  formatDistance,
  DISTRICT_EMOJI,
} from "@/lib/constants";
import { Navigation, MapPin, Download } from "lucide-react";
import type { DayPlan, ItineraryResponse } from "@/types";

export default function ItineraryCard() {
  const itinerary = useTravelStore((s) => s.itinerary);
  const selectedDay = useTravelStore((s) => s.selectedDay);
  const setSelectedDay = useTravelStore((s) => s.setSelectedDay);
  const [exporting, setExporting] = useState(false);

  if (!itinerary) return null;

  const handleExportPDF = async () => {
    setExporting(true);
    try {
      const { default: jsPDF } = await import("jspdf");
      await generatePremiumPDF(jsPDF, itinerary);
    } catch (err) {
      console.error("PDF export failed:", err);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="itinerary-card" id="itinerary-card">
      {/* Day filter tabs */}
      <div className="itinerary-tabs">
        <button
          className={`itinerary-tab ${selectedDay === null ? "active" : ""}`}
          onClick={() => setSelectedDay(null)}
        >
          All Days
        </button>
        {itinerary.days.map((day) => (
          <button
            key={day.day_number}
            className={`itinerary-tab ${selectedDay === day.day_number ? "active" : ""}`}
            style={{
              borderColor:
                selectedDay === day.day_number ? day.color : "transparent",
            }}
            onClick={() => setSelectedDay(day.day_number)}
          >
            <span
              className="tab-dot"
              style={{ background: day.color }}
            />
            Day {day.day_number}
          </button>
        ))}

        {/* PDF Export Button */}
        <button
          className="pdf-export-btn"
          onClick={handleExportPDF}
          disabled={exporting}
          title="Download PDF"
        >
          <Download size={14} />
          {exporting ? "..." : "PDF"}
        </button>
      </div>

      {/* Day plans */}
      {itinerary.days
        .filter((d) => selectedDay === null || d.day_number === selectedDay)
        .map((day) => (
          <DayPlanView key={day.day_number} day={day} />
        ))}
    </div>
  );
}

function DayPlanView({ day }: { day: DayPlan }) {
  const emoji = DISTRICT_EMOJI[day.district_name] || "";

  return (
    <div className="day-plan">
      <div className="day-header" style={{ borderLeftColor: day.color }}>
        <h3>
          <span className="day-number" style={{ background: day.color }}>
            Day {day.day_number}
          </span>
          <span className="day-district">
            {emoji} {day.district_name}
          </span>
        </h3>
        <span className="day-stats">
          {formatDistance(day.total_distance_meters)} ·{" "}
          {formatDuration(day.total_duration_seconds)}
        </span>
      </div>

      <div className="route-timeline">
        {day.route_segments.map((seg, idx) => (
          <div key={idx} className="route-segment">
            <div className="segment-from">
              <MapPin size={14} style={{ color: day.color }} />
              <span>{seg.from_place.name}</span>
            </div>

            <div className="segment-line" style={{ borderColor: day.color }}>
              <span className="segment-stats">
                {formatDistance(seg.distance_meters)} ·{" "}
                {formatDuration(seg.duration_seconds)}
              </span>
              <a
                href={seg.google_maps_url}
                target="_blank"
                rel="noopener noreferrer"
                className="navigate-btn"
                style={{ background: day.color }}
              >
                <Navigation size={12} />
                Navigate
              </a>
            </div>

            {idx === day.route_segments.length - 1 && (
              <div className="segment-from">
                <MapPin size={14} style={{ color: day.color }} />
                <span>{seg.to_place.name}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}


// ── Premium PDF Generator ──────────────────────────────────────────────

function hexToRgb(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return [r, g, b];
}

async function generatePremiumPDF(
  jsPDF: typeof import("jspdf").default,
  itinerary: ItineraryResponse
) {
  const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
  const pageW = 210;
  const margin = 18;
  const contentW = pageW - margin * 2;

  // ── Page 1: Title + Hotel ─────────────────────────────────────────
  // Header accent bar
  doc.setFillColor(59, 130, 246);
  doc.rect(0, 0, pageW, 3, "F");

  // Title
  doc.setFontSize(28);
  doc.setFont("helvetica", "bold");
  doc.setTextColor(30, 30, 30);
  doc.text("Osaka Travel Itinerary", pageW / 2, 28, { align: "center" });

  // Subtitle line
  doc.setDrawColor(200, 200, 200);
  doc.line(margin, 34, pageW - margin, 34);

  // Hotel info box
  doc.setFillColor(248, 250, 252);
  doc.roundedRect(margin, 40, contentW, 22, 3, 3, "F");
  doc.setFontSize(10);
  doc.setFont("helvetica", "bold");
  doc.setTextColor(80, 80, 80);
  doc.text("ACCOMMODATION", margin + 5, 48);
  doc.setFontSize(13);
  doc.setTextColor(30, 30, 30);
  doc.setFont("helvetica", "bold");
  doc.text(itinerary.hotel.name, margin + 5, 55);
  doc.setFontSize(9);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(120, 120, 120);
  doc.text(itinerary.hotel.address, margin + 5, 60);

  let y = 72;

  // ── Day Plans ─────────────────────────────────────────────────────
  for (const day of itinerary.days) {
    if (y > 240) {
      doc.addPage();
      doc.setFillColor(59, 130, 246);
      doc.rect(0, 0, pageW, 3, "F");
      y = 15;
    }

    const [r, g, b] = hexToRgb(day.color);

    // Day header with colored bar
    doc.setFillColor(r, g, b);
    doc.roundedRect(margin, y, contentW, 12, 2, 2, "F");
    doc.setFontSize(13);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(255, 255, 255);
    doc.text(`Day ${day.day_number}  --  ${day.district_name}`, margin + 5, y + 8);

    // Stats right-aligned
    const statsText = `${formatDistance(day.total_distance_meters)}  |  ${formatDuration(day.total_duration_seconds)}`;
    doc.setFontSize(9);
    doc.text(statsText, pageW - margin - 5, y + 8, { align: "right" });

    y += 17;

    // Places list
    for (let i = 0; i < day.places.length; i++) {
      if (y > 270) {
        doc.addPage();
        doc.setFillColor(59, 130, 246);
        doc.rect(0, 0, pageW, 3, "F");
        y = 15;
      }

      const place = day.places[i];

      // Number circle
      doc.setFillColor(r, g, b);
      doc.circle(margin + 4, y + 1, 3, "F");
      doc.setFontSize(8);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(255, 255, 255);
      doc.text(`${i + 1}`, margin + 4, y + 2.2, { align: "center" });

      // Place name
      doc.setFontSize(11);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(30, 30, 30);
      doc.text(place.name, margin + 12, y + 2);

      // Address
      doc.setFontSize(8);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(140, 140, 140);
      doc.text(place.address, margin + 12, y + 6);

      // Connector line (dashed)
      if (i < day.places.length - 1) {
        doc.setDrawColor(r, g, b);
        doc.setLineDashPattern([1, 1], 0);
        doc.line(margin + 4, y + 5, margin + 4, y + 12);
        doc.setLineDashPattern([], 0);
      }

      y += 13;
    }

    y += 5;
  }

  // ── Navigation Links Section ──────────────────────────────────────
  if (y > 240) {
    doc.addPage();
    doc.setFillColor(59, 130, 246);
    doc.rect(0, 0, pageW, 3, "F");
    y = 15;
  }

  // Section header
  doc.setDrawColor(200, 200, 200);
  doc.line(margin, y, pageW - margin, y);
  y += 8;

  doc.setFontSize(14);
  doc.setFont("helvetica", "bold");
  doc.setTextColor(30, 30, 30);
  doc.text("Google Maps Navigation Links", margin, y);
  y += 8;

  doc.setFontSize(7.5);

  for (const day of itinerary.days) {
    const [r, g, b] = hexToRgb(day.color);

    for (const seg of day.route_segments) {
      if (y > 278) {
        doc.addPage();
        doc.setFillColor(59, 130, 246);
        doc.rect(0, 0, pageW, 3, "F");
        y = 15;
      }

      // Route label
      doc.setFont("helvetica", "bold");
      doc.setTextColor(r, g, b);
      doc.text(`Day ${day.day_number}`, margin, y);
      doc.setTextColor(60, 60, 60);
      doc.text(`  ${seg.from_place.name}  ->  ${seg.to_place.name}`, margin + 12, y);
      y += 4;

      // URL
      doc.setFont("helvetica", "normal");
      doc.setTextColor(30, 80, 180);
      doc.textWithLink(seg.google_maps_url, margin + 3, y, {
        url: seg.google_maps_url,
      });
      doc.setTextColor(0);
      y += 7;
    }
  }

  // Footer
  doc.setFontSize(7);
  doc.setTextColor(180, 180, 180);
  doc.text(
    `Generated by TripForge  |  ${new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}`,
    pageW / 2,
    290,
    { align: "center" }
  );

  doc.save("osaka-itinerary.pdf");
}
