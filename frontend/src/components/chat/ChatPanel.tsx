/**
 * ChatPanel — The left-side chat interface.
 * Contains message list, itinerary cards, and input bar.
 */

"use client";

import { useEffect, useRef } from "react";
import { MessageSquare, Loader2 } from "lucide-react";
import { useTravelStore } from "@/providers/TravelStoreProvider";
import MessageBubble from "./MessageBubble";
import ItineraryCard from "./ItineraryCard";
import ChatInput from "./ChatInput";

export default function ChatPanel() {
  const messages = useTravelStore((s) => s.messages);
  const isLoading = useTravelStore((s) => s.isLoading);
  const itinerary = useTravelStore((s) => s.itinerary);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  return (
    <div className="chat-panel">
      {/* Messages Area */}
      <div className="chat-messages" ref={scrollRef}>
        {messages.length === 0 ? (
          <WelcomeScreen />
        ) : (
          <>
            {messages.map((msg, idx) => (
              <MessageBubble key={idx} message={msg} />
            ))}

            {/* Itinerary card after messages */}
            {itinerary && (
              <div className="chat-itinerary-wrapper">
                <ItineraryCard />
              </div>
            )}
          </>
        )}

        {/* Typing indicator */}
        {isLoading && (
          <div className="typing-indicator">
            <div className="message-avatar message-avatar-assistant">
              <Loader2 size={16} className="animate-spin" />
            </div>
            <div className="typing-dots">
              <span className="typing-dot" style={{ animationDelay: "0ms" }} />
              <span className="typing-dot" style={{ animationDelay: "150ms" }} />
              <span className="typing-dot" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <ChatInput />
    </div>
  );
}

function WelcomeScreen() {
  return (
    <div className="welcome-screen">
      <div className="welcome-icon">
        <MessageSquare size={40} />
      </div>
      <h2 className="welcome-title">Plan Your Osaka Trip</h2>
      <p className="welcome-subtitle">
        Tell me your hotel, the places you want to visit, and how many days you have.
        I&apos;ll create an optimized itinerary grouped by Osaka districts. 🏯
      </p>
      <div className="welcome-examples">
        <p className="welcome-example-label">TRY SAYING:</p>
        <div className="welcome-example">
          &quot;I&apos;m staying at Hotel Nikko Osaka. I want to visit Osaka Castle,
          Dotonbori, Kaiyukan, Umeda Sky Building, Shinsekai, and Kuromon Market.
          I have 2 days.&quot;
        </div>
      </div>
    </div>
  );
}
