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
import PrintableItinerary from "./PrintableItinerary";

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
      <PrintableItinerary itinerary={itinerary} />
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

    const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
    const pageW = 210;
    const pageH = 297;
    const margin = 15;
    const contentW = pageW - margin * 2;
    let currentY = margin;

    const addBlock = async (elementId: string) => {
      const el = document.getElementById(elementId);
      if (!el) return;
      
      // Temporarily make sure it's fully rendered by html-to-image
      const dataUrl = await toJpeg(el, { 
        quality: 0.95, 
        pixelRatio: 2, 
        backgroundColor: "white",
      });
      const ratio = await getImageRatio(dataUrl);
      const imgHeight = contentW * ratio;

      if (currentY + imgHeight > pageH - margin) {
        doc.addPage();
        currentY = margin;
      }
      doc.addImage(dataUrl, "JPEG", margin, currentY, contentW, imgHeight);
      currentY += imgHeight;
    };

    // 1. Capture Official Header
    await addBlock("print-block-header");

    // 2. Capture Map (Optional visual)
    const mapElement = document.querySelector(".leaflet-container") as HTMLElement;
    if (mapElement) {
      await new Promise(r => setTimeout(r, 200));
      const mapDataUrl = await toJpeg(mapElement, { 
        quality: 0.95, 
        pixelRatio: 2,
        backgroundColor: '#f8fafc'
      });
      const mapRatio = await getImageRatio(mapDataUrl);
      const mapHeight = contentW * mapRatio;
      
      if (currentY + mapHeight > pageH - margin) {
        doc.addPage();
        currentY = margin;
      }
      doc.setDrawColor(200, 200, 200);
      doc.setLineWidth(0.5);
      doc.rect(margin - 0.5, currentY - 0.5, contentW + 1, mapHeight + 1);
      doc.addImage(mapDataUrl, "JPEG", margin, currentY, contentW, mapHeight);
      currentY += mapHeight + 5; // Add a small gap after map
    }

    // 3. Capture Each Day Block
    for (const day of itinerary.days) {
      await addBlock(`print-block-day-${day.day_number}`);
    }

    // 4. Navigation Links Section on a new page
    doc.addPage();
    let y = margin;
    doc.setFontSize(16);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 0, 0);
    doc.text("Official Navigation Links", margin, y);
    y += 10;

    doc.setFontSize(9);
    for (const day of itinerary.days) {
      for (const seg of day.route_segments) {
        if (y > pageH - margin) {
          doc.addPage();
          y = margin;
        }

        doc.setFont("helvetica", "bold");
        doc.setTextColor(50, 50, 50);
        doc.text(`Day ${day.day_number} Route`, margin, y);
        y += 5;

        doc.setFont("helvetica", "normal");
        doc.setTextColor(30, 80, 180);
        doc.textWithLink(seg.google_maps_url, margin, y, { url: seg.google_maps_url });
        doc.setTextColor(0);
        y += 8;
      }
    }

    doc.save("Official-Itinerary.pdf");
  } catch (err) {
    console.error("Failed to generate PDF", err);
  }
}
