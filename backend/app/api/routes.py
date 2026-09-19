"""
FastAPI Router for Trip Planning, Real-time Streaming, and Revisions.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.schemas.trip import TripRequest
from app.schemas.itinerary import Itinerary
from app.agent.graph import plan_trip, astream_trip
from app.agent.nodes import _get_model
from app.agent.guardrails import verify_guardrails

logger = logging.getLogger(__name__)

router = APIRouter()


class RevisionRequest(BaseModel):
    """Payload for conversational itinerary revisions."""
    current_itinerary: Itinerary
    instruction: str = Field(..., min_length=3, max_length=500)


@router.get("/health", tags=["System"])
async def health_check():
    """System health and readiness check."""
    settings = get_settings()
    return {
        "status": "healthy",
        "llm_provider": settings.llm_provider,
        "model_name": settings.model_name,
    }


@router.post("/trips/plan", response_model=Itinerary, tags=["Trips"])
async def create_trip_plan(request: TripRequest):
    """
    Synchronous trip planning endpoint.
    Executes the complete LangGraph workflow and returns the final verified Itinerary.
    """
    try:
        result = await plan_trip(request)
        itinerary = result.get("itinerary")
        if not itinerary:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Agent failed to produce an itinerary.",
            )
        return itinerary
    except HTTPException:
        raise
    except ValueError as exc:
        logger.warning("Invalid input during trip planning: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Failed to plan trip: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Planning error: {str(exc)}",
        )


@router.post("/trips/plan/stream", tags=["Trips"])
async def create_trip_plan_stream(request: TripRequest):
    """
    Server-Sent Events (SSE) streaming endpoint.
    Yields real-time events for node transitions, guardrail evaluations, and the final itinerary.
    """
    return StreamingResponse(
        astream_trip(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/trips/revise", response_model=Itinerary, tags=["Trips"])
async def revise_trip(payload: RevisionRequest):
    """
    Revises an existing itinerary according to user instruction.
    Applies deterministic guardrails to ensure the revision remains within budget.
    """
    try:
        model = _get_model()
        structured_llm = model.with_structured_output(Itinerary)

        prompt = (
            f"You are revising an existing itinerary for {payload.current_itinerary.destination}.\n"
            f"Current Itinerary:\n{payload.current_itinerary.model_dump_json(indent=2)}\n\n"
            f"User Revision Instruction: {payload.instruction}\n"
            f"Budget Limit: {payload.current_itinerary.budget} {payload.current_itinerary.currency}\n\n"
            "Apply the requested modification while ensuring realistic activity pacing and budget compliance."
        )

        revised_itinerary: Itinerary = await structured_llm.ainvoke(prompt)
        verify_guardrails(
            itinerary=revised_itinerary,
            budget=payload.current_itinerary.budget,
            weather=[],
        )
        return revised_itinerary
    except Exception as exc:
        logger.error("Revision failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Revision failed: {str(exc)}",
        )
