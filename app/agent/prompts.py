"""
System and user prompts for itinerary synthesis and guardrail self-correction.
"""

from typing import List, Dict, Any

SYSTEM_PROMPT = """You are an expert AI Travel Planner. Your goal is to synthesize a realistic, immersive, and well-paced travel itinerary based strictly on the provided destination, duration, budget, and live weather forecast.

CRITICAL RULES:
1. Strict Budget Compliance: The sum of costs across all activities must NOT exceed {budget} {currency}. Provide realistic cost estimates for paid attractions and dining. If budget is tight, include free attractions (parks, temples, scenic viewpoints, walking tours).
2. Weather Adaptation: Observe the live weather forecast provided. For days marked as rainy, you MUST schedule indoor activities (e.g. museums, galleries, covered markets, indoor dining) with is_indoor=true.
3. Realistic Pacing: Plan 3 activities per day (Morning, Afternoon, Evening) with actionable descriptions and specific locations.
"""

USER_PROMPT_TEMPLATE = """Plan a {duration_days}-day trip to {destination} ({display_name}).

Trip Parameters:
- Total Budget Limit: {budget} {currency}
- Traveler Interests: {interests}
- Additional Notes: {notes}

Live Weather Forecast:
{weather_summary}

Generate the complete structured itinerary adhering strictly to the budget and weather conditions."""

CORRECTION_PROMPT_TEMPLATE = """Your previous itinerary draft failed deterministic validation with the following guardrail violations:

{violations}

Actionable Feedback:
{feedback}

Please revise the itinerary to resolve ALL violations:
- If over budget, replace expensive activities with lower cost or free alternatives.
- If outdoor activities were scheduled on rainy days, replace them with indoor venues (setting is_indoor=true).
Ensure all activities have valid time slots, locations, and realistic costs."""


def format_weather(forecasts: List[Dict[str, Any]]) -> str:
    """Formats weather forecast list into a readable string for the LLM prompt."""
    if not forecasts:
        return "No weather data available; assume mild, pleasant conditions."

    lines = []
    for f in forecasts:
        rain_text = f"🌧️ Rain likely ({f.get('rain_chance', 0)}% chance)" if f.get("is_rainy") else "☀️ No rain expected"
        lines.append(
            f"- Day {f.get('day_number')}: {f.get('condition')} ({f.get('min_temp')}°C - {f.get('max_temp')}°C), {rain_text}"
        )
    return "\n".join(lines)
