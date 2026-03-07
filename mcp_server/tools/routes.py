"""
EcoSight MCP Tool — Route Fetching
Retrieve multiple route alternatives between two points,
with accessibility metadata (surface type, elevation, wheelchair suitability).

Uses OpenRouteService Directions API.
"""

from __future__ import annotations

import httpx
from typing import Any

from mcp_server.config import (
    ORS_API_KEY,
    ORS_BASE_URL,
    DEFAULT_WALKING_PROFILE,
    MAX_ROUTE_ALTERNATIVES,
)

# Re-use geocode & formatting helpers from navigation module
from mcp_server.tools.navigation import (
    _geocode,
    _format_distance,
    _format_duration,
    _simplify_instruction,
)


async def fetch_available_routes(
    origin: str,
    destination: str,
    profile: str | None = None,
    alternatives: int | None = None,
    avoid_steps: bool = False,
) -> dict[str, Any]:
    """
    Fetch up to N route alternatives between origin and destination.

    Args:
        origin:       Starting location (address or "lat,lng").
        destination:  End location (address or "lat,lng").
        profile:      "foot-walking" (default) or "wheelchair".
        alternatives: Number of alternatives to request (max 3).
        avoid_steps:  If True, request routes that avoid steps/stairs.

    Returns:
        routes: list of route dicts, each containing summary, steps, warnings.
    """
    profile = profile or DEFAULT_WALKING_PROFILE
    n_alt = min(alternatives or MAX_ROUTE_ALTERNATIVES, MAX_ROUTE_ALTERNATIVES)

    org = await _geocode(origin)
    dst = await _geocode(destination)

    url = f"{ORS_BASE_URL}/v2/directions/{profile}/geojson"
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
    body: dict[str, Any] = {
        "coordinates": [[org["lng"], org["lat"]], [dst["lng"], dst["lat"]]],
        "instructions": True,
        "alternative_routes": {"target_count": n_alt, "share_factor": 0.6, "weight_factor": 1.4},
        "language": "en",
        "units": "m",
        "elevation": True,
    }

    if avoid_steps:
        body["options"] = {"avoid_features": ["steps"]}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()

    routes: list[dict] = []
    for i, feature in enumerate(data.get("features", [])):
        props = feature["properties"]
        summary = props["summary"]
        segments = props.get("segments", [])

        steps: list[dict] = []
        warnings: list[str] = []

        for seg in segments:
            for step in seg.get("steps", []):
                steps.append({
                    "instruction": _simplify_instruction(step.get("instruction", "")),
                    "distance": _format_distance(step.get("distance", 0)),
                    "duration": _format_duration(step.get("duration", 0)),
                    "name": step.get("name", ""),
                })

        # Surface / accessibility warnings from extras
        extras = props.get("extras", {})
        if "surface" in extras:
            for info in extras["surface"].get("summary", []):
                val = info.get("value")
                pct = info.get("amount", 0)
                if val in (0, 1) and pct > 10:  # unknown / paved
                    pass
                elif pct > 20:
                    warnings.append(f"{pct:.0f}% of route has surface type {val}")
        if "waytypes" in extras:
            for info in extras["waytypes"].get("summary", []):
                if info.get("value") == 3 and info.get("amount", 0) > 5:  # steps
                    warnings.append(f"Route includes stairs for {info['amount']:.0f}% of distance")

        elevation_gain = summary.get("ascent", 0)
        elevation_loss = summary.get("descent", 0)

        routes.append({
            "route_number": i + 1,
            "summary": (
                f"Route {i + 1}: {_format_distance(summary['distance'])} — "
                f"{_format_duration(summary['duration'])}"
            ),
            "distance": _format_distance(summary["distance"]),
            "duration": _format_duration(summary["duration"]),
            "elevation_gain": f"{elevation_gain:.0f} metres up",
            "elevation_loss": f"{elevation_loss:.0f} metres down",
            "steps": steps,
            "warnings": warnings if warnings else ["No accessibility warnings"],
        })

    label = f"Found {len(routes)} route(s) from {org['label']} to {dst['label']}."
    return {
        "overview": label,
        "routes": routes,
        "origin": org,
        "destination": dst,
    }
