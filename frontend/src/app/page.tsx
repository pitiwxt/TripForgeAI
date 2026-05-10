/**
 * Main page — Chat panel overlays the map.
 * Loads shared sessions from ?session=ID URL param.
 */

"use client";

import { useState, useEffect } from "react";
import Header from "@/components/layout/Header";
import ChatPanel from "@/components/chat/ChatPanel";
import DynamicLeaflet from "@/components/map/DynamicLeaflet";
import { MessageSquare } from "lucide-react";
import { useTravelStore } from "@/providers/TravelStoreProvider";

export default function HomePage() {
  const [chatOpen, setChatOpen] = useState(true);
  const loadSharedSession = useTravelStore((s) => s.loadSharedSession);

  // Load shared session from URL on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get("session");
    if (sessionId) {
      loadSharedSession(sessionId);
    }
  }, [loadSharedSession]);

  return (
    <div className="app-layout">
      <Header chatOpen={chatOpen} onToggleChat={() => setChatOpen(!chatOpen)} />
      <main className="app-main-overlay">
        <div className="map-full">
          <DynamicLeaflet />
        </div>

        <div className={`chat-overlay ${chatOpen ? "chat-overlay-open" : "chat-overlay-closed"}`}>
          <ChatPanel />
        </div>

        {!chatOpen && (
          <button
            className="chat-toggle-float"
            onClick={() => setChatOpen(true)}
            title="Open chat"
          >
            <MessageSquare size={20} />
          </button>
        )}
      </main>
    </div>
  );
}
