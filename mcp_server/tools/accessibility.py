"""
EcoSight MCP Tool — Accessibility & Safety Helpers
Emergency contacts, time/date awareness, and general blind-user utilities.
"""

from __future__ import annotations

import datetime
from typing import Any

from mcp_server.config import EMERGENCY_NUMBER


async def get_current_time_and_date() -> dict[str, Any]:
    """
    Returns the current date, time, and day of week in a TTS-friendly format.
    Helpful for blind users to stay oriented.
    """
    now = datetime.datetime.now()
    day_name = now.strftime("%A")
    date_str = now.strftime("%B %d, %Y")
    time_str = now.strftime("%I:%M %p")
    hour = now.hour

    if 5 <= hour < 12:
        greeting = "Good morning"
    elif 12 <= hour < 17:
        greeting = "Good afternoon"
    elif 17 <= hour < 21:
        greeting = "Good evening"
    else:
        greeting = "It's night time"

    # Daylight safety hint
    if hour < 6 or hour > 20:
        safety = "It is currently dark outside. Take extra care when walking."
    elif hour < 7 or hour > 19:
        safety = "Light is low — dusk or dawn conditions. Be cautious near roads."
    else:
        safety = "There is daylight outside."

    spoken = f"{greeting}. It is {time_str} on {day_name}, {date_str}. {safety}"

    return {
        "spoken_summary": spoken,
        "time": time_str,
        "date": date_str,
        "day": day_name,
        "safety_note": safety,
    }


async def get_emergency_info(
    location: str | None = None,
) -> dict[str, Any]:
    """
    Provide emergency contact information and guidance.

    Args:
        location: Optional — user's country or city for localised numbers.

    Returns:
        spoken_summary – TTS-ready emergency guidance
        contacts       – list of emergency contacts
    """
    contacts = [
        {"service": "General Emergency", "number": EMERGENCY_NUMBER},
        {"service": "Police", "number": EMERGENCY_NUMBER},
        {"service": "Ambulance", "number": EMERGENCY_NUMBER},
        {"service": "Fire", "number": EMERGENCY_NUMBER},
    ]

    # Localised overrides
    loc_lower = (location or "").lower()
    if "india" in loc_lower or loc_lower in ("in",):
        contacts = [
            {"service": "General Emergency", "number": "112"},
            {"service": "Police", "number": "100"},
            {"service": "Ambulance", "number": "108"},
            {"service": "Fire", "number": "101"},
            {"service": "Women Helpline", "number": "1091"},
        ]
    elif "us" in loc_lower or "united states" in loc_lower:
        contacts = [
            {"service": "Emergency (Police/Fire/Ambulance)", "number": "911"},
            {"service": "Poison Control", "number": "1-800-222-1222"},
        ]
    elif "uk" in loc_lower or "united kingdom" in loc_lower or "britain" in loc_lower:
        contacts = [
            {"service": "Emergency", "number": "999"},
            {"service": "Non-urgent", "number": "111"},
        ]

    numbers_spoken = ". ".join(
        f"{c['service']}: {c['number']}" for c in contacts
    )
    spoken = f"Emergency contacts: {numbers_spoken}. Stay calm and describe your location clearly when calling."

    return {
        "spoken_summary": spoken,
        "contacts": contacts,
        "tip": "If you are in danger, try to move to a safe location and call for help immediately.",
    }


async def describe_surroundings_prompt() -> dict[str, Any]:
    """
    Returns a structured prompt inviting the EcoSight vision system
    to describe the user's surroundings.  This bridges the MCP agent
    with the existing Phase 2 scene-description pipeline.
    """
    return {
        "spoken_summary": "I will now describe your surroundings. Please hold your phone steady.",
        "action": "trigger_phase2",
        "instruction": (
            "Send a 'trigger_phase2' message to the EcoSight WebSocket server "
            "to capture a frame and generate a scene description."
        ),
    }


async def get_safety_tips(context: str = "walking") -> dict[str, Any]:
    """
    Provide safety tips based on activity context.

    Args:
        context: "walking", "crossing", "public_transport", "indoor", "night".
    """
    tips_map: dict[str, list[str]] = {
        "walking": [
            "Stay on the sidewalk whenever possible.",
            "Use your white cane or guide dog to detect obstacles.",
            "Listen for traffic sounds before stepping off the curb.",
            "Keep your phone accessible in case you need to call for help.",
            "Walk facing traffic when there is no sidewalk.",
        ],
        "crossing": [
            "Listen for the pedestrian signal before crossing.",
            "Cross at marked crosswalks or intersections.",
            "Walk straight across — don't cross diagonally.",
            "Be extra cautious of turning vehicles.",
            "Ask a nearby person for help if you are unsure.",
        ],
        "public_transport": [
            "Arrive at the stop a few minutes early.",
            "Ask the driver to announce your stop.",
            "Hold handrails when moving on a bus or train.",
            "Keep your belongings close to your body.",
            "Use tactile paving to locate platform edges.",
        ],
        "indoor": [
            "Let your hand trail along the wall for orientation.",
            "Count doorways to find your destination.",
            "Listen for echoes to gauge room size.",
            "Ask staff for assistance in unfamiliar buildings.",
        ],
        "night": [
            "Wear reflective clothing or accessories.",
            "Carry a bright flashlight or wear a headlamp.",
            "Avoid poorly lit areas if possible.",
            "Stay on familiar routes.",
            "Let someone know your route and expected arrival time.",
        ],
    }

    ctx = context.lower()
    tips = tips_map.get(ctx, tips_map["walking"])
    spoken = f"Safety tips for {ctx}: " + " ".join(
        f"{i}. {t}" for i, t in enumerate(tips, 1)
    )

    return {
        "spoken_summary": spoken,
        "context": ctx,
        "tips": tips,
    }
