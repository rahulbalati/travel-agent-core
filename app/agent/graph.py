"""
LangGraph Orchestrator Graph Definition.
Wires state transitions, deterministic guardrail checks, and cyclical self-correction.
"""

import json
import logging
from typing import AsyncGenerator, Dict, Any

from langgraph.graph import StateGraph, START, END

from app.schemas.trip import TripRequest
from app.agent.state import AgentState
from app.agent.nodes import (
    node_gather_tools,
    node_synthesize,
    node_validate_guardrails,
    node_self_correct,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


def should_continue(state: AgentState) -> str:
    """
    Conditional routing function:
    - If no guardrail errors: finish and route to END.
    - If errors exist and retries < MAX_RETRIES: route to self_correct.
    - If errors exist but max retries exhausted: route to END (deliver best-effort).
    """
    errors = state.get("guardrail_errors", [])
    retries = state.get("retry_count", 0)

    if not errors:
        logger.info("Guardrails passed cleanly. Proceeding to END.")
        return "end"

    if retries >= MAX_RETRIES:
        logger.warning("Max self-correction retries (%d) exhausted. Proceeding to END.", MAX_RETRIES)
        return "end"

    logger.info("Guardrail violations detected (%d errors). Routing to self_correct...", len(errors))
    return "self_correct"


def build_agent_graph():
    """Builds and compiles the LangGraph state machine."""
    builder = StateGraph(AgentState)

    builder.add_node("gather_tools", node_gather_tools)
    builder.add_node("synthesize", node_synthesize)
    builder.add_node("validate_guardrails", node_validate_guardrails)
    builder.add_node("self_correct", node_self_correct)

    # Edge wiring
    builder.add_edge(START, "gather_tools")
    builder.add_edge("gather_tools", "synthesize")
    builder.add_edge("synthesize", "validate_guardrails")

    builder.add_conditional_edges(
        "validate_guardrails",
        should_continue,
        {
            "end": END,
            "self_correct": "self_correct",
        },
    )
    builder.add_edge("self_correct", "synthesize")

    return builder.compile()


# Compiled singleton graph
graph = build_agent_graph()


async def plan_trip(request: TripRequest) -> Dict[str, Any]:
    """Non-streaming runner returning final state."""
    initial_state: AgentState = {
        "trip_request": request,
        "retry_count": 0,
    }
    return await graph.ainvoke(initial_state)


async def astream_trip(request: TripRequest) -> AsyncGenerator[str, None]:
    """
    Streaming runner yielding SSE formatted events at each node transition.
    """
    initial_state: AgentState = {
        "trip_request": request,
        "retry_count": 0,
    }

    try:
        async for event in graph.astream(initial_state, stream_mode="updates"):
            for node_name, state_update in event.items():
                status = state_update.get("status", f"Executed {node_name}")
                payload = {
                    "node": node_name,
                    "status": status,
                    "retry_count": state_update.get("retry_count", 0),
                }

                # If final itinerary or draft is produced
                if "itinerary" in state_update and state_update["itinerary"]:
                    payload["itinerary"] = state_update["itinerary"].model_dump()

                if "guardrail_errors" in state_update:
                    payload["guardrail_errors"] = state_update["guardrail_errors"]

                yield f"data: {json.dumps(payload)}\n\n"

        # Signal completion
        yield "data: {\"done\": true}\n\n"

    except Exception as exc:
        logger.error("Error during agent stream: %s", exc)
        err_payload = {"error": str(exc), "done": True}
        yield f"data: {json.dumps(err_payload)}\n\n"
