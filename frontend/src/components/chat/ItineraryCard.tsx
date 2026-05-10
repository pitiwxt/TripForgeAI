/**
 * ItineraryCard — Rich day-by-day itinerary display with Osaka district labels,
 * route timeline, Google Maps navigate buttons, and premium PDF export.
 */

"use client";

import { useState } from "react";
import { useTravelStore } from "@/providers/TravelStoreProvider";
import {
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

async function generatePremiumPDF(
  jsPDF: typeof import("jspdf").default,
  itinerary: ItineraryResponse
) {
  try {
    const { toJpeg } = await import("html-to-image");

    const getImageRatio = (dataUrl: string): Promise<number> => {
      return new Promise((resolve) => {
        const img = new Image();
        img.onload = () => resolve(img.height / img.width);
        img.src = dataUrl;
      });
    };

    // 1. Capture Map
    let mapImgData: string | null = null;
    let mapRatio = 1;
    const mapElement = document.querySelector(".leaflet-container") as HTMLElement;
    if (mapElement) {
      await new Promise(r => setTimeout(r, 200));
      mapImgData = await toJpeg(mapElement, { 
        quality: 0.95, 
        pixelRatio: 2,
        backgroundColor: '#f8fafc'
      });
      mapRatio = await getImageRatio(mapImgData);
    }

    // 2. Capture Itinerary Card
    let cardImgData: string | null = null;
    let cardRatio = 1;
    const cardElement = document.querySelector(".itinerary-card") as HTMLElement;
    if (cardElement) {
      cardImgData = await toJpeg(cardElement, {
        quality: 0.95,
        pixelRatio: 2,
        backgroundColor: '#ffffff',
        filter: (node) => {
          // Exclude tabs from PDF
          if (node instanceof Element && node.classList.contains("itinerary-tabs")) {
            return false;
          }
          return true;
        }
      });
      cardRatio = await getImageRatio(cardImgData);
    }

    // 3. Create PDF
    const pageW = 210;
    const margin = 15;
    const contentW = pageW - margin * 2;

    const titleHeight = 30;
    const mapHeight = mapImgData ? contentW * mapRatio : 0;
    const cardHeight = cardImgData ? contentW * cardRatio : 0;
    const spacing = 10;

    // Single long page format
    const totalHeight = Math.max(297, titleHeight + mapHeight + spacing + cardHeight + spacing + 20);

    const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: [pageW, totalHeight] });

    // Header accent bar
    doc.setFillColor(59, 130, 246);
    doc.rect(0, 0, pageW, 4, "F");

    // Title
    doc.setFontSize(28);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(30, 30, 30);
    doc.text("Travel Itinerary", pageW / 2, 22, { align: "center" });

    // Subtitle line
    doc.setDrawColor(200, 200, 200);
    doc.line(margin, 28, pageW - margin, 28);

    let y = 35;

    // Draw Map
    if (mapImgData && mapHeight > 0) {
      doc.setDrawColor(220, 220, 220);
      doc.setLineWidth(0.5);
      doc.rect(margin - 0.5, y - 0.5, contentW + 1, mapHeight + 1);
      doc.addImage(mapImgData, "JPEG", margin, y, contentW, mapHeight);
      y += mapHeight + spacing;
    }

    // Draw Card
    if (cardImgData && cardHeight > 0) {
      doc.addImage(cardImgData, "JPEG", margin, y, contentW, cardHeight);
      y += cardHeight + spacing;
    }

    // Navigation Links Section
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
      // Very crude hexToRgb just for the links label colors
      const r = parseInt(day.color.slice(1, 3), 16) || 0;
      const g = parseInt(day.color.slice(3, 5), 16) || 0;
      const b = parseInt(day.color.slice(5, 7), 16) || 0;

      for (const seg of day.route_segments) {
        if (y > totalHeight - 20) {
          doc.addPage();
          doc.setFillColor(59, 130, 246);
          doc.rect(0, 0, pageW, 3, "F");
          y = 15;
        }

        doc.setFont("helvetica", "bold");
        doc.setTextColor(r, g, b);
        doc.text(`Day ${day.day_number}`, margin, y);
        doc.setTextColor(60, 60, 60);
        // Fallback ASCII names for the link labels to prevent gibberish
        doc.text(`  Route`, margin + 12, y);
        y += 4;

        doc.setFont("helvetica", "normal");
        doc.setTextColor(30, 80, 180);
        doc.textWithLink(seg.google_maps_url, margin + 3, y, { url: seg.google_maps_url });
        doc.setTextColor(0);
        y += 7;
      }
    }

    // Footer
    doc.setFontSize(8);
    doc.setTextColor(150, 150, 150);
    doc.text(
      `Generated by TripForge AI  |  ${new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}`,
      pageW / 2,
      totalHeight - 10,
      { align: "center" }
    );

    doc.save("TripForge-Itinerary.pdf");
  } catch (err) {
    console.error("Failed to generate PDF", err);
  }
}
