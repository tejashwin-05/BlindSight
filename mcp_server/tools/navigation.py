"""
EcoSight MCP Tool — Navigation
Turn-by-turn walking navigation between two locations,
optimised for blind / visually-impaired users.

Uses OpenRouteService Directions API with the foot-walking profile.
"""

from __future__ import annotations

import httpx
from typing import Any

from mcp_server.config import ORS_API_KEY, ORS_BASE_URL, DEFAULT_WALKING_PROFILE


# ─── Internal helpers ────────────────────────────────────────────

async def _geocode(place: str) -> dict[str, float]:
    """Geocode a place name → {lng, lat} via ORS Pelias search."""
    url = f"{ORS_BASE_URL}/geocode/search"
    params = {"api_key": ORS_API_KEY, "text": place, "size": 1}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        features = resp.json().get("features", [])
        if not features:
            raise ValueError(f"Could not geocode '{place}'")
        coords = features[0]["geometry"]["coordinates"]  # [lng, lat]
        label = features[0]["properties"].get("label", place)
        return {"lng": coords[0], "lat": coords[1], "label": label}


def _bearing_word(bearing: float) -> str:
    """Convert 0-360 bearing to compass word."""
    dirs = [
        "north", "north-east", "east", "south-east",
        "south", "south-west", "west", "north-west",
    ]
    idx = int((bearing + 22.5) % 360 // 45)
    return dirs[idx]


def _simplify_instruction(raw: str) -> str:
    """Make ORS HTML instruction friendlier for TTS."""
    import re
    clean = re.sub(r"<[^>]+>", "", raw)
    clean = clean.replace("&nbsp;", " ").strip()
    return clean


def _format_distance(m: float) -> str:
    if m < 1000:
        return f"{int(m)} metres"
    return f"{m / 1000:.1f} kilometres"


def _format_duration(sec: float) -> str:
    mins = int(sec // 60)
    if mins < 1:
        return "less than a minute"
    if mins == 1:
        return "1 minute"
    if mins < 60:
        return f"{mins} minutes"
    h, m = divmod(mins, 60)
    return f"{h} hour{'s' if h > 1 else ''} {m} minutes"


# ─── Public tool functions ───────────────────────────────────────

async def navigate_to_destination(
    origin: str,
    destination: str,
    profile: str | None = None,
) -> dict[str, Any]:
    """
    Get step-by-step walking directions from *origin* to *destination*.

    Args:
        origin:      Starting address or place name (or "lat,lng").
        destination: Target address or place name (or "lat,lng").
        profile:     ORS profile — "foot-walking" (default) or "wheelchair".

    Returns a dict with:
        summary   – human-readable overview (distance + time)
        steps     – list of turn-by-turn instructions with distance/duration
        bbox      – bounding box [west, south, east, north]
        raw       – full ORS response for advanced use
    """
    profile = profile or DEFAULT_WALKING_PROFILE

    # Resolve coordinates
    org = await _geocode(origin)
    dst = await _geocode(destination)

    url = f"{ORS_BASE_URL}/v2/directions/{profile}/geojson"
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
    body = {
        "coordinates": [[org["lng"], org["lat"]], [dst["lng"], dst["lat"]]],
        "instructions": True,
        "language": "en",
        "units": "m",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()

    feature = data["features"][0]
    props = feature["properties"]
    summary = props["summary"]
    segments = props.get("segments", [])

    steps: list[dict] = []
    for seg in segments:
        for step in seg.get("steps", []):
            steps.append({
                "instruction": _simplify_instruction(step.get("instruction", "")),
                "distance": _format_distance(step.get("distance", 0)),
                "duration": _format_duration(step.get("duration", 0)),
                "type": step.get("type"),
                "name": step.get("name", ""),
            })

    overview = (
        f"Walk from {org['label']} to {dst['label']}. "
        f"Total distance: {_format_distance(summary['distance'])}. "
        f"Estimated time: {_format_duration(summary['duration'])}."
    )

    return {
        "summary": overview,
        "steps": steps,
        "total_distance": _format_distance(summary["distance"]),
        "total_duration": _format_duration(summary["duration"]),
        "bbox": feature.get("bbox"),
        "origin": org,
        "destination": dst,
    }
