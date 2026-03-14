"""
EcoSight MCP Tool — Navigation
Turn-by-turn walking navigation using:
  - Nominatim (OpenStreetMap) for geocoding  — free, no key
  - OSRM public API for routing             — free, no key
"""

from __future__ import annotations

import httpx
from typing import Any

# OSRM public demo server (walking profile)
OSRM_BASE = "https://router.project-osrm.org"
NOMINATIM_BASE = "https://nominatim.openstreetmap.org"

# OSRM step maneuver type → human instruction prefix
_MANEUVER = {
    "turn":           "Turn",
    "new name":       "Continue onto",
    "depart":         "Head",
    "arrive":         "Arrive at",
    "merge":          "Merge onto",
    "on ramp":        "Take the ramp onto",
    "off ramp":       "Take the exit onto",
    "fork":           "Keep",
    "end of road":    "Turn",
    "roundabout":     "Enter the roundabout",
    "rotary":         "Enter the rotary",
    "roundabout turn":"Turn at the roundabout onto",
    "notification":   "Note:",
    "use lane":       "Use the lane",
}

_MODIFIER = {
    "uturn":        "and make a U-turn",
    "sharp right":  "sharp right",
    "right":        "right",
    "slight right": "slightly right",
    "straight":     "straight",
    "slight left":  "slightly left",
    "left":         "left",
    "sharp left":   "sharp left",
}


def _format_distance(m: float) -> str:
    if m < 1000:
        return f"{int(m)} metres"
    return f"{m / 1000:.1f} km"


def _format_duration(sec: float) -> str:
    mins = int(sec // 60)
    if mins < 1:
        return "less than a minute"
    if mins == 1:
        return "1 minute"
    if mins < 60:
        return f"{mins} minutes"
    h, m = divmod(mins, 60)
    return f"{h} hr {m} min"


def _build_instruction(step: dict) -> str:
    maneuver = step.get("maneuver", {})
    mtype    = maneuver.get("type", "")
    modifier = maneuver.get("modifier", "")
    name     = step.get("name", "").strip()

    prefix = _MANEUVER.get(mtype, "Continue")
    mod    = _MODIFIER.get(modifier, modifier)

    if mtype == "depart":
        return f"Head {mod} on {name}" if name else f"Head {mod}"
    if mtype == "arrive":
        return "You have arrived at your destination"
    if mtype in ("roundabout", "rotary"):
        exit_num = maneuver.get("exit", "")
        return f"Enter the roundabout and take exit {exit_num}" if exit_num else "Enter the roundabout"
    if mod and name:
        return f"{prefix} {mod} onto {name}"
    if mod:
        return f"{prefix} {mod}"
    if name:
        return f"{prefix} onto {name}"
    return prefix


# ─── Geocoding via Nominatim ─────────────────────────────────────

async def _geocode(place: str, country_bias: str = "IN") -> dict:
    """Resolve place name → {lat, lng, label}. Accepts 'lat,lng' directly."""
    parts = place.strip().split(",")
    if len(parts) == 2:
        try:
            lat, lng = float(parts[0].strip()), float(parts[1].strip())
            print(f"[NAV] Direct coords: lat={lat:.5f}, lng={lng:.5f}")
            return {"lat": lat, "lng": lng, "label": f"{lat:.5f},{lng:.5f}"}
        except ValueError:
            pass

    print(f"[NAV] Geocoding '{place}'")
    headers = {"User-Agent": "BlindSight-Navigation/1.0"}

    async with httpx.AsyncClient(timeout=15, headers=headers) as client:
        # Try with country bias first
        resp = await client.get(f"{NOMINATIM_BASE}/search", params={
            "q": place, "format": "json", "limit": 1,
            "countrycodes": country_bias.lower(),
        })
        resp.raise_for_status()
        results = resp.json()

        # Retry globally if not found in country
        if not results:
            resp2 = await client.get(f"{NOMINATIM_BASE}/search", params={
                "q": place, "format": "json", "limit": 1,
            })
            resp2.raise_for_status()
            results = resp2.json()

    if not results:
        raise ValueError(f"Could not find location: '{place}'. Try a more specific name.")

    r = results[0]
    lat, lng = float(r["lat"]), float(r["lon"])
    label = r.get("display_name", place).split(",")[0]
    print(f"[NAV] Geocoded '{place}' → {lat:.4f},{lng:.4f} ({label})")
    return {"lat": lat, "lng": lng, "label": label}


# ─── Routing via OSRM ────────────────────────────────────────────

async def navigate_to_destination(
    origin: str,
    destination: str,
    profile: str | None = None,
) -> dict[str, Any]:
    """
    Get step-by-step walking directions from origin to destination.
    Uses OSRM (free, no API key) with foot profile.
    """
    org = await _geocode(origin)
    dst = await _geocode(destination)

    # OSRM route endpoint — coordinates as lng,lat
    coords = f"{org['lng']},{org['lat']};{dst['lng']},{dst['lat']}"
    url = f"{OSRM_BASE}/route/v1/foot/{coords}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params={
            "steps": "true",
            "geometries": "geojson",
            "overview": "simplified",
            "annotations": "false",
        })
        if not resp.is_success:
            raise ValueError(f"Routing failed ({resp.status_code}): {resp.text[:200]}")
        data = resp.json()

    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError(f"No route found: {data.get('message', 'unknown error')}")

    route    = data["routes"][0]
    legs     = route.get("legs", [])
    total_m  = route.get("distance", 0)
    total_s  = route.get("duration", 0)

    # Extract route geometry coordinates for map rendering
    geometry_coords = []
    raw_geom = route.get("geometry", {})
    if isinstance(raw_geom, dict):
        # GeoJSON format: [[lng,lat], ...]  → convert to [[lat,lng]]
        geometry_coords = [[c[1], c[0]] for c in raw_geom.get("coordinates", [])]

    steps: list[dict] = []
    for leg in legs:
        for step in leg.get("steps", []):
            dist = step.get("distance", 0)
            dur  = step.get("duration", 0)
            if dist < 1 and step.get("maneuver", {}).get("type") not in ("depart", "arrive"):
                continue  # skip zero-distance noise steps
            maneuver_loc = step.get("maneuver", {}).get("location", [])  # [lng, lat]
            steps.append({
                "instruction": _build_instruction(step),
                "distance":    _format_distance(dist),
                "distance_m":  dist,
                "duration":    _format_duration(dur),
                "name":        step.get("name", ""),
                # waypoint = end of this step = where user must reach before next instruction
                "waypoint":    {"lat": maneuver_loc[1], "lng": maneuver_loc[0]} if len(maneuver_loc) == 2 else None,
            })

    overview = (
        f"Walk from {org['label']} to {dst['label']}. "
        f"Total distance: {_format_distance(total_m)}. "
        f"Estimated time: {_format_duration(total_s)}."
    )

    return {
        "summary":        overview,
        "steps":          steps,
        "total_distance": _format_distance(total_m),
        "total_duration": _format_duration(total_s),
        "origin":         org,
        "destination":    dst,
        "geometry":       geometry_coords,   # [[lat,lng], ...] for map polyline
    }
