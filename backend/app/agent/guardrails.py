"""
Deterministic Guardrails & Verification Engine.
Enforces strict budget arithmetic and weather feasibility over LLM outputs.
"""

import logging
from typing import Tuple, List, Dict, Any
from app.schemas.itinerary import Itinerary

logger = logging.getLogger(__name__)


def verify_guardrails(
    itinerary: Itinerary,
    budget: float,
    weather: List[Dict[str, Any]],
) -> Tuple[bool, List[str], List[str]]:
    """
    Executes deterministic checks on the generated itinerary:
    1. Financial compliance: Exact sum of all activities <= budget limit.
    2. Weather feasibility: No outdoor activities on rainy days.

    Returns:
        (is_valid, errors, feedback)
    """
    errors: List[str] = []
    feedback: List[str] = []

    # 1. Deterministic Budget Verification (Exact arithmetic)
    all_activities = [act for day in itinerary.days for act in day.activities]
    total_cost = round(sum(act.cost for act in all_activities), 2)
    budget = round(budget, 2)

    itinerary.total_cost = total_cost
    itinerary.budget = budget
    itinerary.is_within_budget = total_cost <= budget

    if total_cost > budget:
        overage = round(total_cost - budget, 2)
        errors.append(
            f"Budget exceeded: Total cost (${total_cost:.2f}) exceeds budget (${budget:.2f}) by ${overage:.2f}."
        )
        feedback.append(
            f"Reduce total cost by at least ${overage:.2f}. Swap paid dining or premium tickets for free public parks, "
            f"historic walking routes, or lower-cost dining."
        )

    # 2. Deterministic Weather Feasibility Check
    weather_by_day = {w.get("day_number"): w for w in weather}

    for day in itinerary.days:
        day_weather = weather_by_day.get(day.day_number)
        if day_weather and day_weather.get("is_rainy"):
            for act in day.activities:
                if not act.is_indoor:
                    errors.append(
                        f"Weather conflict on Day {day.day_number}: Rain is forecasted "
                        f"({day_weather.get('condition', 'Rain')}, {day_weather.get('rain_chance', 0)}% chance), "
                        f"but outdoor activity '{act.title}' is scheduled."
                    )
                    feedback.append(
                        f"On Day {day.day_number}, replace outdoor activity '{act.title}' with an indoor venue "
                        f"(museum, covered arcade, exhibition, or gallery) and set is_indoor=True."
                    )

    is_valid = len(errors) == 0
    logger.info(
        "Guardrail verification: valid=%s, errors=%d, total_cost=%.2f, budget=%.2f",
        is_valid,
        len(errors),
        total_cost,
        budget,
    )
    return is_valid, errors, feedback
