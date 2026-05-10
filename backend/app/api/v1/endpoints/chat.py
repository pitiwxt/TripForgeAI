"""
Chat endpoint — the main AI conversation interface.

POST /api/v1/chat
Accepts user messages + current itinerary context,
routes through LLM, and returns updated itinerary.
"""

import logging
from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_service import process_chat

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    tags=["Chat"],
    summary="Process a travel planning message",
)
async def chat(request: ChatRequest):
    """
    Main chat endpoint. Sends message + itinerary context to AI.
    AI can generate new, modify existing, or just chat.
    """
    try:
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]

        assistant_message, itinerary = await process_chat(
            user_message=request.message,
            conversation_history=history,
            current_itinerary=request.current_itinerary,
        )

        itinerary_dict = itinerary.model_dump() if itinerary else None

        return ChatResponse(
            assistant_message=assistant_message,
            itinerary=itinerary_dict,
        )

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process your message: {str(e)}",
        )
