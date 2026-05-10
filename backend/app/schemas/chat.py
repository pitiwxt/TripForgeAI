"""
Pydantic schemas for chat request/response contracts.
"""

from typing import Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in the conversation history."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message text content")


class ChatRequest(BaseModel):
    """Request body for POST /api/v1/chat."""
    message: str = Field(
        ...,
        description="The user's natural language message",
        min_length=1,
        max_length=4000,
    )
    conversation_history: list[ChatMessage] = Field(
        default_factory=list,
        description="Previous messages for context continuity",
    )
    current_itinerary: dict[str, Any] | None = Field(
        default=None,
        description="The current itinerary state (hotel, days, places) for modification context",
    )


class ChatResponse(BaseModel):
    """Response body for POST /api/v1/chat."""
    assistant_message: str = Field(
        ..., description="The AI assistant's text response"
    )
    itinerary: dict | None = Field(
        default=None,
        description="Structured itinerary data if a plan was generated",
    )
