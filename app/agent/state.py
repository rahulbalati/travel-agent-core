"""
LangGraph Agent State Definition.
Lean TypedDict managing state across tool execution, LLM synthesis,
guardrail verification, and self-correction.
"""

from typing import TypedDict, Optional, List, Dict, Any
from app.schemas.trip import TripRequest
from app.schemas.itinerary import Itinerary


class AgentState(TypedDict, total=False):
    """Clean state container for the travel planner orchestrator."""

    trip_request: TripRequest
    geo: Dict[str, Any]
    weather: List[Dict[str, Any]]
    itinerary: Optional[Itinerary]
    guardrail_errors: List[str]
    guardrail_feedback: List[str]
    retry_count: int
    status: str
    error: Optional[str]
