/**
 * Zustand store — chat, map, trip state + session persistence & sharing.
 */

import { createStore } from "zustand/vanilla";
import type {
  ChatMessage,
  ItineraryResponse,
  GeocodedPlace,
} from "@/types";
import { sendChatMessage, saveSession, loadSession } from "@/lib/api-client";

export interface TravelState {
  // Chat
  messages: ChatMessage[];
  isLoading: boolean;

  // Itinerary + Map
  itinerary: ItineraryResponse | null;
  selectedDay: number | null;
  activePopup: GeocodedPlace | null;

  // Session
  sessionId: string | null;
  isSaving: boolean;

  // Actions
  sendMessage: (text: string) => Promise<void>;
  setSelectedDay: (day: number | null) => void;
  setActivePopup: (place: GeocodedPlace | null) => void;
  resetTrip: () => void;
  saveCurrentSession: () => Promise<string | null>;
  loadSharedSession: (id: string) => Promise<void>;
}

export const createTravelStore = () =>
  createStore<TravelState>((set, get) => ({
    messages: [],
    isLoading: false,
    itinerary: null,
    selectedDay: null,
    activePopup: null,
    sessionId: null,
    isSaving: false,

    sendMessage: async (text: string) => {
      const userMsg: ChatMessage = { role: "user", content: text };
      set((s) => ({
        messages: [...s.messages, userMsg],
        isLoading: true,
      }));

      try {
        const state = get();
        const response = await sendChatMessage(
          text,
          state.messages,
          state.itinerary,
        );

        const assistantMsg: ChatMessage = {
          role: "assistant",
          content: response.assistant_message,
        };

        set((s) => ({
          messages: [...s.messages, assistantMsg],
          isLoading: false,
          itinerary: response.itinerary || s.itinerary,
          selectedDay: null,
        }));

        // Auto-save session after each message
        const updated = get();
        if (updated.messages.length > 0) {
          try {
            const saved = await saveSession(
              updated.sessionId,
              updated.messages,
              updated.itinerary,
            );
            set({ sessionId: saved.id });
          } catch {
            // Silent fail on auto-save
          }
        }
      } catch (error) {
        set((s) => ({
          messages: [
            ...s.messages,
            { role: "assistant", content: "Something went wrong. Please try again. 🙏" },
          ],
          isLoading: false,
        }));
      }
    },

    saveCurrentSession: async () => {
      const { messages, itinerary, sessionId } = get();
      if (messages.length === 0) return null;
      set({ isSaving: true });
      try {
        const saved = await saveSession(sessionId, messages, itinerary);
        set({ sessionId: saved.id, isSaving: false });
        return saved.id;
      } catch {
        set({ isSaving: false });
        return null;
      }
    },

    loadSharedSession: async (id: string) => {
      try {
        const session = await loadSession(id);
        set({
          sessionId: session.id,
          messages: session.messages || [],
          itinerary: session.itinerary || null,
          selectedDay: null,
          activePopup: null,
        });
      } catch (e) {
        console.error("Failed to load session:", e);
      }
    },

    setSelectedDay: (day) => set({ selectedDay: day }),
    setActivePopup: (place) => set({ activePopup: place }),
    resetTrip: () =>
      set({
        messages: [],
        itinerary: null,
        selectedDay: null,
        activePopup: null,
        isLoading: false,
        sessionId: null,
      }),
  }));
