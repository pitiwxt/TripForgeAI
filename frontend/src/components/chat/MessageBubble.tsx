/**
 * MessageBubble — Renders a single chat message (user or assistant).
 * Assistant messages may contain markdown-like formatting.
 */

"use client";

import { User, Bot } from "lucide-react";
import type { ChatMessage } from "@/types";

interface Props {
  message: ChatMessage;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`message-bubble ${isUser ? "message-user" : "message-assistant"}`}>
      {/* Avatar */}
      <div className={`message-avatar ${isUser ? "message-avatar-user" : "message-avatar-assistant"}`}>
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      {/* Content */}
      <div className={`message-content ${isUser ? "message-content-user" : "message-content-assistant"}`}>
        {/* Render with basic formatting */}
        {message.content.split("\n").map((line, i) => (
          <p key={i} className="message-line">
            {renderFormattedLine(line)}
          </p>
        ))}
      </div>
    </div>
  );
}

/**
 * Simple markdown-like rendering for bold (**text**) and emoji support.
 */
function renderFormattedLine(line: string): React.ReactNode {
  if (!line.trim()) return <br />;

  // Replace **bold** with <strong>
  const parts = line.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}
