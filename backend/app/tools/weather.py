"""
Weather tool using Open-Meteo API.
Retrieves multi-day weather forecasts with temperature and rain probability.
"""

import logging
from typing import List, Dict, Any
import httpx

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# WMO Weather interpretation codes
WMO_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Heavy rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
}


async def get_weather_forecast(lat: float, lon: float, days: int = 3) -> List[Dict[str, Any]]:
    """
    Fetches daily forecast from Open-Meteo for the specified coordinates.
    Raises RuntimeError if external weather service fails or is unreachable.
    """
    forecast_days = max(1, min(days, 14))
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max",
            "weather_code",
        ],
        "timezone": "auto",
        "forecast_days": forecast_days,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            daily = data.get("daily", {})
            dates = daily.get("time", [])
            max_temps = daily.get("temperature_2m_max", [])
            min_temps = daily.get("temperature_2m_min", [])
            rain_probs = daily.get("precipitation_probability_max", [])
            weather_codes = daily.get("weather_code", [])

            forecasts = []
            for i in range(len(dates)):
                code = weather_codes[i] if i < len(weather_codes) else 0
                condition = WMO_DESCRIPTIONS.get(code, "Clear")
                rain_chance = int(rain_probs[i]) if i < len(rain_probs) and rain_probs[i] is not None else 0
                is_rainy = rain_chance >= 40 or code in (51, 53, 55, 61, 63, 65, 80, 81, 82, 95)

                forecasts.append({
                    "day_number": i + 1,
                    "date": dates[i],
                    "max_temp": float(max_temps[i]) if i < len(max_temps) else 22.0,
                    "min_temp": float(min_temps[i]) if i < len(min_temps) else 15.0,
                    "rain_chance": rain_chance,
                    "is_rainy": is_rainy,
                    "condition": condition,
                })

            logger.info("Retrieved %d days forecast for (lat: %f, lon: %f)", len(forecasts), lat, lon)
            return forecasts

    except Exception as exc:
        logger.error("Weather service failed for (lat: %f, lon: %f): %s", lat, lon, exc)
        raise RuntimeError(f"Live weather service unavailable for coordinates ({lat}, {lon}): {exc}")
