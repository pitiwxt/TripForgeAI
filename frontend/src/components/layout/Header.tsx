/**
 * Header — Branding + chat toggle + share + new trip.
 */

"use client";

import { useState } from "react";
import { useTravelStore } from "@/providers/TravelStoreProvider";
import { MapPin, RotateCcw, PanelLeftClose, PanelLeft, Share2, Check, History } from "lucide-react";

interface HeaderProps {
  chatOpen: boolean;
  onToggleChat: () => void;
}

export default function Header({ chatOpen, onToggleChat }: HeaderProps) {
  const resetTrip = useTravelStore((s) => s.resetTrip);
  const saveSession = useTravelStore((s) => s.saveCurrentSession);
  const sessionId = useTravelStore((s) => s.sessionId);
  const messages = useTravelStore((s) => s.messages);
  const [copied, setCopied] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  const handleShare = async () => {
    const id = sessionId || (await saveSession());
    if (id) {
      const url = `${window.location.origin}?session=${id}`;
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <header className="app-header">
      <div className="header-brand">
        <button
          className="header-toggle-btn"
          onClick={onToggleChat}
          title={chatOpen ? "Close chat" : "Open chat"}
        >
          {chatOpen ? <PanelLeftClose size={18} /> : <PanelLeft size={18} />}
        </button>
        <div className="header-logo">
          <MapPin size={22} />
        </div>
        <h1>TripForge</h1>
        <span className="header-badge">🏯 Osaka</span>
      </div>

      <div className="header-actions">
        {messages.length > 0 && (
          <button
            className="header-btn header-share-btn"
            onClick={handleShare}
            title="Copy share link"
          >
            {copied ? <Check size={16} /> : <Share2 size={16} />}
            {copied ? "Copied!" : "Share"}
          </button>
        )}
        <button className="header-btn" onClick={resetTrip}>
          <RotateCcw size={16} />
          New Trip
        </button>
      </div>
    </header>
  );
}
