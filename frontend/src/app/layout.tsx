/**
 * Root layout — wraps the entire application with providers.
 * Sets up Inter font, TravelStore provider, and SEO metadata.
 */

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { TravelStoreProvider } from "@/providers/TravelStoreProvider";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "TripForge AI — Map-Centric Travel Planner",
  description:
    "AI-powered travel itinerary planner with optimized routing, " +
    "interactive maps, and Google Maps navigation deep links.",
  keywords: ["travel planner", "AI itinerary", "TSP routing", "Google Maps", "Tokyo trip"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <TravelStoreProvider>{children}</TravelStoreProvider>
      </body>
    </html>
  );
}
