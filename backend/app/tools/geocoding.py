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
        logger.warning("Primary Nominatim geocoding failed for '%s' (%s), attempting Wikipedia coordinates fallback...", cleaned_dest, exc)
        try:
            wiki_url = "https://en.wikipedia.org/w/api.php"
            wiki_headers = {"User-Agent": USER_AGENT}
            async with httpx.AsyncClient(timeout=8.0) as client:
                # 1. Try exact title with redirects
                wiki_params = {
                    "action": "query",
                    "prop": "coordinates",
                    "titles": cleaned_dest,
                    "format": "json",
                    "redirects": 1,
                }
                w_resp = await client.get(wiki_url, params=wiki_params, headers=wiki_headers)
                if w_resp.status_code == 200:
                    pages = w_resp.json().get("query", {}).get("pages", {})
                    for page in pages.values():
                        if "coordinates" in page and page["coordinates"]:
                            coord = page["coordinates"][0]
                            lat = float(coord["lat"])
                            lon = float(coord["lon"])
                            display_name = page.get("title", cleaned_dest)
                            logger.info("Geocoded '%s' via Wikipedia fallback -> lat: %f, lon: %f (%s)", cleaned_dest, lat, lon, display_name)
                            return {
                                "destination": cleaned_dest,
                                "lat": lat,
                                "lon": lon,
                                "display_name": display_name,
                                "country_code": "",
                            }

                # 2. Try search generator if direct title had no coordinates
                search_params = {
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": cleaned_dest,
                    "gsrlimit": 1,
                    "prop": "coordinates",
                    "format": "json",
                }
                s_resp = await client.get(wiki_url, params=search_params, headers=wiki_headers)
                if s_resp.status_code == 200:
                    pages = s_resp.json().get("query", {}).get("pages", {})
                    for page in pages.values():
                        if "coordinates" in page and page["coordinates"]:
                            coord = page["coordinates"][0]
                            lat = float(coord["lat"])
                            lon = float(coord["lon"])
                            display_name = page.get("title", cleaned_dest)
                            logger.info("Geocoded '%s' via Wikipedia search fallback -> lat: %f, lon: %f (%s)", cleaned_dest, lat, lon, display_name)
                            return {
                                "destination": cleaned_dest,
                                "lat": lat,
                                "lon": lon,
                                "display_name": display_name,
                                "country_code": "",
                            }
        except Exception as fb_exc:
            logger.error("Wikipedia geocoding fallback failed for '%s': %s", cleaned_dest, fb_exc)

        logger.error("Geocoding service error for '%s': %s", cleaned_dest, exc)
        raise RuntimeError(f"Geocoding service unavailable for '{cleaned_dest}': {exc}")
