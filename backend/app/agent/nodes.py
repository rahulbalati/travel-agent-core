"""
LangGraph Execution Nodes.
Encapsulates individual state transitions:
1. gather_tools: OpenStreetMap geocoding + Open-Meteo live weather forecast.
2. synthesize: Direct LLM structured output via ChatGoogleGenerativeAI / ChatOpenAI.
3. validate_guardrails: Deterministic mathematical budget and weather checks.
4. self_correct: Formulates feedback and triggers self-correction loop.
"""

import logging
from typing import Dict, Any

from langchain_core.runnables import RunnableConfig
from app.config import get_settings
from app.schemas.itinerary import Itinerary
from app.tools.geocoding import get_coordinates
from app.tools.weather import get_weather_forecast
from app.agent.state import AgentState
from app.agent.prompts import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    CORRECTION_PROMPT_TEMPLATE,
    format_weather,
)
from app.agent.guardrails import verify_guardrails

logger = logging.getLogger(__name__)


def _get_model():
    """Initializes the configured LLM provider directly."""
    settings = get_settings()
    if settings.llm_provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.model_name,
            google_api_key=settings.google_api_key,
            temperature=settings.temperature,
        )
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openai_api_key,
            temperature=settings.temperature,
        )


async def node_gather_tools(state: AgentState, config: RunnableConfig = None) -> Dict[str, Any]:
    """
    Node 1: Resolves destination coordinates and fetches multi-day forecast concurrently.
    """
    req = state["trip_request"]
    logger.info("Gathering tools for destination: %s", req.destination)

    geo = await get_coordinates(req.destination)
    weather = await get_weather_forecast(
        lat=geo["lat"],
        lon=geo["lon"],
        days=req.duration_days,
    )

    return {
        "geo": geo,
        "weather": weather,
        "retry_count": state.get("retry_count", 0),
        "status": f"Acquired coordinates and {len(weather)}-day forecast for {geo['display_name']}.",
    }


async def node_synthesize(state: AgentState, config: RunnableConfig = None) -> Dict[str, Any]:
    """
    Node 2: Prompts the LLM with structured output to synthesize an itinerary.
    Includes guardrail feedback if in a self-correction loop.
    Passes RunnableConfig to nest LLM generation directly inside this trace node.
    """
    req = state["trip_request"]
    geo = state["geo"]
    weather = state["weather"]
    feedback = state.get("guardrail_feedback", [])
    errors = state.get("guardrail_errors", [])

    model = _get_model()
    structured_llm = model.with_structured_output(Itinerary)

    system_msg = SYSTEM_PROMPT.format(
        budget=req.budget,
        currency=req.currency,
    )
    user_msg = USER_PROMPT_TEMPLATE.format(
        destination=req.destination,
        display_name=geo.get("display_name", req.destination),
        duration_days=req.duration_days,
        budget=req.budget,
        currency=req.currency,
        interests=", ".join(req.interests),
        notes=req.notes or "None provided",
        weather_summary=format_weather(weather),
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    # In case of self-correction cycle, append the feedback prompt
    if feedback:
        correction_msg = CORRECTION_PROMPT_TEMPLATE.format(
            violations="\n".join(f"- {e}" for e in errors),
            feedback="\n".join(f"- {f}" for f in feedback),
        )
        messages.append({"role": "user", "content": correction_msg})
        logger.info("Synthesizing revised itinerary with self-correction feedback...")
    else:
        logger.info("Synthesizing initial itinerary draft via LLM...")

    itinerary: Itinerary = await structured_llm.ainvoke(messages, config=config)

    # Ensure trip basics are aligned
    itinerary.destination = req.destination
    itinerary.duration_days = req.duration_days
    itinerary.currency = req.currency

    return {
        "itinerary": itinerary,
        "status": "Synthesized structured itinerary via LLM.",
    }


async def node_validate_guardrails(state: AgentState, config: RunnableConfig = None) -> Dict[str, Any]:
    """
    Node 3: Deterministic guardrail check for strict budget arithmetic and rain feasibility.
    """
    itinerary = state["itinerary"]
    req = state["trip_request"]
    weather = state["weather"]

    is_valid, errors, feedback = verify_guardrails(
        itinerary=itinerary,
        budget=req.budget,
        weather=weather,
    )

    return {
        "itinerary": itinerary,
        "guardrail_errors": errors,
        "guardrail_feedback": feedback,
        "status": f"Guardrails checked: {'Valid' if is_valid else f'{len(errors)} violations detected'}.",
    }


async def node_self_correct(state: AgentState, config: RunnableConfig = None) -> Dict[str, Any]:
    """
    Node 4: Prepares state for self-correction by incrementing retry count.
    """
    next_retry = state.get("retry_count", 0) + 1
    logger.info("Entering self-correction loop (attempt %d)...", next_retry)
    return {
        "retry_count": next_retry,
        "status": f"Self-correcting guardrail violations (attempt {next_retry})...",
    }
