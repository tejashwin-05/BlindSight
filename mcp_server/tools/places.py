"""
EcoSight MCP Tool — Places / Points of Interest
Find nearby accessible places (hospitals, pharmacies, bus stops, etc.)
using OpenStreetMap Overpass API — no API key needed.

Ideal for blind users asking "What's nearby?" or "Find the nearest bus stop."
"""

from __future__ import annotations

import httpx
import math
from typing import Any

from mcp_server.config import OVERPASS_URL
from mcp_server.tools.navigation import _geocode


# Common POI categories mapped to OSM tags
POI_PRESETS: dict[str, str] = {
    "hospital":    '[amenity=hospital]',
    "pharmacy":    '[amenity=pharmacy]',
    "bus_stop":    '[highway=bus_stop]',
    "train_station": '[railway=station]',
    "restaurant":  '[amenity=restaurant]',
    "cafe":        '[amenity=cafe]',
    "bank":        '[amenity=bank]',
    "atm":         '[amenity=atm]',
    "toilet":      '[amenity=toilets]',
    "police":      '[amenity=police]',
    "fire_station": '[amenity=fire_station]',
    "supermarket": '[shop=supermarket]',
    "park":        '[leisure=park]',
    "bench":       '[amenity=bench]',
    "crossing":    '[highway=crossing]',
    "traffic_signal": '[highway=traffic_signals]',
    "taxi":        '[amenity=taxi]',
    "shelter":     '[amenity=shelter]',
}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance between two lat/lng points in metres."""
    R = 6371000
    p = math.pi / 180
    a = (
        0.5 - math.cos((lat2 - lat1) * p) / 2
        + math.cos(lat1 * p) * math.cos(lat2 * p)
        * (1 - math.cos((lon2 - lon1) * p)) / 2
    )
    return 2 * R * math.asin(math.sqrt(a))


async def find_nearby_places(
    location: str,
    category: str = "bus_stop",
    radius_m: int = 500,
    limit: int = 5,
) -> dict[str, Any]:
    """
    Find points of interest near a location.

    Args:
        location:  Address, place name, or "lat,lng".
        category:  One of: hospital, pharmacy, bus_stop, train_station,
                   restaurant, cafe, bank, atm, toilet, police,
                   fire_station, supermarket, park, bench, crossing,
                   traffic_signal, taxi, shelter.
        radius_m:  Search radius in metres (default 500).
        limit:     Max results (default 5).

    Returns:
        spoken_summary – TTS description
        places         – list of place dicts with name & distance
    """
    # Resolve location
    geo = await _geocode(location)
    lat, lng = geo["lat"], geo["lng"]

    tag = POI_PRESETS.get(category.lower())
    if not tag:
        available = ", ".join(sorted(POI_PRESETS.keys()))
        return {
            "spoken_summary": f"Unknown category '{category}'. Available: {available}",
            "places": [],
        }

    query = f"""
    [out:json][timeout:15];
    (
      node{tag}(around:{radius_m},{lat},{lng});
      way{tag}(around:{radius_m},{lat},{lng});
    );
    out center {limit};
    """

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(OVERPASS_URL, data={"data": query})
        resp.raise_for_status()
        data = resp.json()

    elements = data.get("elements", [])
    places: list[dict] = []
    for elem in elements:
        elat = elem.get("lat") or elem.get("center", {}).get("lat")
        elng = elem.get("lon") or elem.get("center", {}).get("lon")
        if elat is None or elng is None:
            continue
        dist = _haversine(lat, lng, elat, elng)
        name = elem.get("tags", {}).get("name", f"Unnamed {category}")
        wheelchair = elem.get("tags", {}).get("wheelchair", "unknown")
        places.append({
            "name": name,
            "distance_m": int(dist),
            "distance_spoken": f"{int(dist)} metres away",
            "wheelchair_accessible": wheelchair,
            "lat": elat,
            "lng": elng,
        })

    places.sort(key=lambda p: p["distance_m"])
    places = places[:limit]

    if not places:
        spoken = f"No {category.replace('_', ' ')} found within {radius_m} metres of {geo['label']}."
    else:
        parts = [f"{p['name']}, {p['distance_spoken']}" for p in places]
        spoken = (
            f"Found {len(places)} {category.replace('_', ' ')}(s) near {geo['label']}: "
            + "; ".join(parts) + "."
        )

    return {
        "spoken_summary": spoken,
        "places": places,
        "search_location": geo,
    }
