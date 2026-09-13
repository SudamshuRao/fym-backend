"""
Overpass API (OpenStreetMap) client: finds real-world locations of
known restaurant chains near the user, within a radius. Free, no API
key, no signup - matching this app's cost-discipline principle.

We only need location lookup here, not menu data - nutrition data is
already scraped per chain (not per individual store location), so this
just answers "which of the chains I have data for actually have a
location near this user."

The HTTP call is injected as a parameter, same pattern as the Ollama
client and recipe generation - lets this be tested without a live
network call.
"""

from __future__ import annotations

import requests

from app.core.geo import haversine_distance_km

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Overpass API's usage policy asks clients to identify themselves, and
# in practice blocks requests using Python's unmodified default
# User-Agent (many abusive scripts use it as-is) with a 406 error.
HEADERS = {"User-Agent": "FYM-FitYourMacros/0.1 (personal nutrition app; contact: none)"}


class OverpassError(Exception):
    pass


def _default_query_fn(lat: float, lon: float, radius_km: float) -> dict:
    radius_m = int(radius_km * 1000)
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"~"^(restaurant|fast_food|cafe)$"](around:{radius_m},{lat},{lon});
    );
    out center;
    """
    try:
        resp = requests.get(OVERPASS_URL, params={"data": query}, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise OverpassError(f"Overpass API request failed: {e}") from e

    return resp.json()


def find_nearby_chains(
    lat: float,
    lon: float,
    radius_km: float,
    known_chains: list[tuple[str, str]],  # (restaurant_id, display_name) pairs
    query_fn=_default_query_fn,
) -> list[dict]:
    """
    Returns a list of {restaurant_id, name, distance_km} for every known
    chain with at least one real-world location within the given radius.
    If a chain has multiple nearby locations, only the closest one is
    returned. Sorted by distance, closest first.
    """
    data = query_fn(lat, lon, radius_km)
    elements = data.get("elements", [])

    # Normalize known chain names for case-insensitive matching
    chain_lookup = {display_name.strip().lower(): restaurant_id for restaurant_id, display_name in known_chains}

    best_by_chain: dict[str, dict] = {}

    for element in elements:
        tags = element.get("tags", {})
        osm_name = tags.get("name", "").strip().lower()
        if not osm_name:
            continue

        # Match if the OSM name matches a known chain, or contains it
        # (handles cases like "McDonald's - Main St")
        matched_restaurant_id = None
        for chain_name_lower, restaurant_id in chain_lookup.items():
            if chain_name_lower == osm_name or chain_name_lower in osm_name:
                matched_restaurant_id = restaurant_id
                break

        if matched_restaurant_id is None:
            continue

        elem_lat = element.get("lat")
        elem_lon = element.get("lon")
        if elem_lat is None or elem_lon is None:
            continue  # ways/relations without a computed center - skip rather than guess

        distance = haversine_distance_km(lat, lon, elem_lat, elem_lon)

        existing = best_by_chain.get(matched_restaurant_id)
        if existing is None or distance < existing["distance_km"]:
            best_by_chain[matched_restaurant_id] = {
                "restaurant_id": matched_restaurant_id,
                "name": tags.get("name"),
                "distance_km": round(distance, 2),
            }

    return sorted(best_by_chain.values(), key=lambda r: r["distance_km"])