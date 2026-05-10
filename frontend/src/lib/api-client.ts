/**
 * API client — typed fetch wrapper for the FastAPI backend.
 */

import type { ChatMessage, ChatResponse, ItineraryResponse } from "@/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
  timeoutMs: number = 60000,
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  for (let attempt = 0; attempt < 2; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        headers: { "Content-Type": "application/json", ...options.headers },
        signal: controller.signal,
        ...options,
      });
      clearTimeout(timer);

      if (response.status === 429) {
        // Rate limited — wait and retry
        await new Promise((r) => setTimeout(r, 3000));
        continue;
      }
      if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`API Error ${response.status}: ${errorBody}`);
      }
      return response.json() as Promise<T>;
    } catch (e) {
      clearTimeout(timer);
      if (attempt === 0 && (e instanceof DOMException || (e as Error).name === "AbortError")) {
        // Timeout — retry once
        continue;
      }
      throw e;
    }
  }
  throw new Error("Request failed after retries");
}

/** POST /api/v1/chat */
export async function sendChatMessage(
  message: string,
  conversationHistory: ChatMessage[],
  currentItinerary: ItineraryResponse | null,
): Promise<ChatResponse> {
  return apiFetch<ChatResponse>("/api/v1/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      conversation_history: conversationHistory,
      current_itinerary: currentItinerary,
    }),
  });
}

/** POST /api/v1/sessions — save/create session */
export async function saveSession(
  sessionId: string | null,
  messages: ChatMessage[],
  itinerary: ItineraryResponse | null,
): Promise<{ id: string; title: string }> {
  return apiFetch("/api/v1/sessions", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      messages,
      itinerary,
    }),
  });
}

/** GET /api/v1/sessions/:id — load shared session */
export async function loadSession(sessionId: string): Promise<{
  id: string;
  title: string;
  messages: ChatMessage[];
  itinerary: ItineraryResponse | null;
}> {
  return apiFetch(`/api/v1/sessions/${sessionId}`);
}

/** GET /api/v1/sessions — list all sessions */
export async function listSessions(): Promise<Array<{
  id: string;
  title: string;
  message_count: number;
  has_itinerary: boolean;
  updated_at: string;
}>> {
  return apiFetch("/api/v1/sessions");
}

/** DELETE /api/v1/sessions/:id */
export async function deleteSession(sessionId: string): Promise<void> {
  return apiFetch(`/api/v1/sessions/${sessionId}`, { method: "DELETE" });
}
