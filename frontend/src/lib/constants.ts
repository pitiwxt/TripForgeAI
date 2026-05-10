/**
 * Constants — Osaka-themed design tokens and utility functions.
 */

export const OSAKA_CENTER = { lat: 34.6937, lng: 135.5023 };
export const DEFAULT_ZOOM = 12;

export const DAY_COLORS = [
  "#3B82F6", // Blue
  "#10B981", // Emerald
  "#F59E0B", // Amber
  "#F43F5E", // Rose
  "#8B5CF6", // Violet
  "#06B6D4", // Cyan
  "#EC4899", // Pink
];

export const HOTEL_COLOR = "#FBBF24";

export function getDayColor(dayNumber: number): string {
  return DAY_COLORS[(dayNumber - 1) % DAY_COLORS.length];
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.round(seconds / 60);
  if (mins < 60) return `${mins} min`;
  const hours = Math.floor(mins / 60);
  const rem = mins % 60;
  return rem > 0 ? `${hours}h ${rem}m` : `${hours}h`;
}

export function formatDistance(meters: number): string {
  if (meters < 1000) return `${meters}m`;
  return `${(meters / 1000).toFixed(1)} km`;
}

export const DISTRICT_EMOJI: Record<string, string> = {
  Kita: "🏙️",
  Minami: "🌃",
  Castle: "🏯",
  Tennoji: "🗼",
  "Bay Area": "🌊",
  Nakanoshima: "🌹",
  Sumiyoshi: "⛩️",
  Suita: "🌿",
};
