"""
Data contract for trip planning requests.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class TripRequest(BaseModel):
    """Clean, user-facing trip planning request."""

    destination: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Target destination city or region (e.g. 'Paris', 'Tokyo')",
    )
    duration_days: int = Field(
        default=3,
        ge=1,
        le=14,
        description="Trip duration in days (1-14)",
    )
    budget: float = Field(
        default=1000.0,
        gt=0,
        description="Total spending budget in the requested currency",
    )
    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        description="3-letter currency code (e.g. USD, EUR, JPY)",
    )
    interests: List[str] = Field(
        default_factory=lambda: ["culture", "sightseeing"],
        description="Traveler interests or preferred styles",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional traveler notes or dietary/mobility constraints",
    )

    @model_validator(mode="before")
    @classmethod
    def handle_aliases(cls, data: any):
        if isinstance(data, dict):
            # Support max_budget as alias for budget
            if "max_budget" in data and "budget" not in data:
                data["budget"] = data["max_budget"]
            # Support travel_style as alias for interests
            if "travel_style" in data and "interests" not in data:
                data["interests"] = data["travel_style"]
        return data

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("destination")
    @classmethod
    def clean_destination(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Destination cannot be empty")
        return cleaned
