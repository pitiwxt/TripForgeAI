/**
 * ChatInput — Message input bar with send button.
 * Handles Enter to send, Shift+Enter for newline.
 */

"use client";

import { useState, useRef, useCallback } from "react";
import { Send, Loader2 } from "lucide-react";
import { useTravelStore } from "@/providers/TravelStoreProvider";

export default function ChatInput() {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const sendMessage = useTravelStore((s) => s.sendMessage);
  const isLoading = useTravelStore((s) => s.isLoading);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    sendMessage(trimmed);
    setInput("");

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [input, isLoading, sendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-resize textarea
    const ta = e.target;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 120)}px`;
  };

  return (
    <div className="chat-input-container">
      <div className="chat-input-wrapper">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Tell me about your trip... (hotel, places, days)"
          className="chat-input-textarea"
          rows={1}
          disabled={isLoading}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          className="chat-send-btn"
          title="Send message"
        >
          {isLoading ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
            <Send size={18} />
          )}
        </button>
      </div>
      <p className="chat-input-hint">
        Try: &quot;I&apos;m staying at Hotel Nikko Osaka. I want to visit Osaka Castle,
        Dotonbori, Kaiyukan, Umeda Sky Building, and Shinsekai. 2 days.&quot;
      </p>
    </div>
  );
}
