"""
EcoSight — JSON Schema Definitions
Single source of truth for all WebSocket message formats.
Both the Python server and the Flutter client must follow these schemas.

PHASE 1 — Hazard Alert (server → client)
{
    "type":          "phase_1",
    "hazard":        str | null,       // "person", "chair", "puddle", etc.  null if nothing detected
    "direction":     "left" | "center" | "right" | null,
    "distance":      float | null,     // metres (e.g. 1.5)
    "confidence":    float | null,     // 0.0 – 1.0
    "total_hazards": int               // number of hazards in this frame
}

PHASE 2 — Scene Description (server → client)
{
    "type":          "phase_2",
    "status":        "processing" | "done",
    "description":   str | null        // full scene description text
}

CLIENT → SERVER messages:
{
    "type": "trigger_phase2"           // user double‑tapped — request scene description
}
{
    "type": "ping"                     // connectivity check
}
Server responds with:
{
    "type": "pong"
}
"""


def build_phase1_payload(
    hazard: str | None,
    direction: str | None,
    distance: float | None,
    confidence: float | None,
    total_hazards: int,
) -> dict:
    """Build a validated Phase 1 hazard payload."""
    return {
        "type": "phase_1",
        "hazard": hazard,
        "direction": direction,
        "distance": distance,
        "confidence": confidence,
        "total_hazards": total_hazards,
    }


def build_phase2_payload(
    status: str,
    description: str | None = None,
) -> dict:
    """Build a validated Phase 2 scene description payload."""
    assert status in ("processing", "done"), f"Invalid phase2 status: {status}"
    return {
        "type": "phase_2",
        "status": status,
        "description": description,
    }


def build_pong() -> dict:
    return {"type": "pong"}
