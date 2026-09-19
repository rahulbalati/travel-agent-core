"""
Geocoding tool using OpenStreetMap Nominatim API.
Resolves destination queries to geographic coordinates and addresses.
"""

import logging
from typing import Dict, Any
import httpx

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "VoyagerTravelPlanner/1.0"


async def get_coordinates(destination: str) -> Dict[str, Any]:
    """
    Resolves destination string into geographic coordinates and formatted address.
    Raises ValueError if destination cannot be found.
    Raises RuntimeError if external geocoding service fails.
    """
    cleaned_dest = destination.strip()
    if not cleaned_dest:
        raise ValueError("Destination cannot be empty.")

    params = {
        "q": cleaned_dest,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }
    headers = {"User-Agent": USER_AGENT}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(NOMINATIM_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            if not data:
                logger.warning("Nominatim returned no results for '%s'", cleaned_dest)
                raise ValueError(f"Destination '{cleaned_dest}' not found. Please provide a valid city or region name.")

            result = data[0]
            lat = float(result.get("lat", 0.0))
            lon = float(result.get("lon", 0.0))
            display_name = result.get("display_name", cleaned_dest)
            country_code = result.get("address", {}).get("country_code", "").upper()

            logger.info("Geocoded '%s' -> lat: %f, lon: %f (%s)", cleaned_dest, lat, lon, display_name)
            return {
                "destination": cleaned_dest,
                "lat": lat,
                "lon": lon,
                "display_name": display_name,
                "country_code": country_code,
            }
    except ValueError:
        raise
    except Exception as exc:
        logger.error("Geocoding service error for '%s': %s", cleaned_dest, exc)
        raise RuntimeError(f"Geocoding service unavailable for '{cleaned_dest}': {exc}")
