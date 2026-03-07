"""
EcoSight MCP Server — Main Entry Point
Model Context Protocol server exposing agentic tool-calling capabilities
to help blind / visually-impaired users navigate, get weather, news,
find nearby places, and stay safe.

Run:
    python -m mcp_server.server          (stdio transport — default)
    python -m mcp_server.server --sse    (SSE transport for web clients)

Requires env vars (or edit config.py):
    ORS_API_KEY   — OpenRouteService  (free tier: openrouteservice.org)
    OWM_API_KEY   — OpenWeatherMap    (free tier: openweathermap.org)
    NEWS_API_KEY  — NewsAPI           (free tier: newsapi.org)
"""

from __future__ import annotations

import argparse
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent

from mcp_server.config import SERVER_NAME, SERVER_VERSION

# ─── Tool implementations ────────────────────────────────────────
from mcp_server.tools.navigation import navigate_to_destination
from mcp_server.tools.routes import fetch_available_routes
from mcp_server.tools.weather import get_current_weather, get_weather_forecast
from mcp_server.tools.news import get_top_headlines, search_news
from mcp_server.tools.places import find_nearby_places
from mcp_server.tools.accessibility import (
    get_current_time_and_date,
    get_emergency_info,
    describe_surroundings_prompt,
    get_safety_tips,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(SERVER_NAME)

# ─── MCP Server instance ─────────────────────────────────────────
app = Server(SERVER_NAME)


# ─── Tool Catalogue ──────────────────────────────────────────────
TOOLS: list[Tool] = [
    # 1. Navigation
    Tool(
        name="navigate_to_destination",
        description=(
            "Get step-by-step walking directions from an origin to a destination. "
            "Returns turn-by-turn instructions optimised for a blind user."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Starting address, place name, or 'lat,lng'.",
                },
                "destination": {
                    "type": "string",
                    "description": "Target address, place name, or 'lat,lng'.",
                },
                "profile": {
                    "type": "string",
                    "enum": ["foot-walking", "wheelchair"],
                    "description": "Routing profile. Default: foot-walking.",
                },
            },
            "required": ["origin", "destination"],
        },
    ),
    # 2. Routes
    Tool(
        name="fetch_available_routes",
        description=(
            "Fetch multiple route alternatives between two locations with "
            "accessibility info (elevation, surface, stairs warnings)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "origin": {"type": "string", "description": "Starting location."},
                "destination": {"type": "string", "description": "End location."},
                "profile": {
                    "type": "string",
                    "enum": ["foot-walking", "wheelchair"],
                },
                "alternatives": {
                    "type": "integer",
                    "description": "Number of route alternatives (max 3).",
                },
                "avoid_steps": {
                    "type": "boolean",
                    "description": "Avoid stairs/steps in route if true.",
                },
            },
            "required": ["origin", "destination"],
        },
    ),
    # 3. Weather — current
    Tool(
        name="get_current_weather",
        description=(
            "Get current weather conditions for a location. Returns a natural-language "
            "summary suitable for text-to-speech, including rain/snow warnings."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name, 'City,Country', or 'lat,lng'.",
                },
                "units": {
                    "type": "string",
                    "enum": ["metric", "imperial"],
                    "description": "Temperature units. Default: metric.",
                },
            },
            "required": ["location"],
        },
    ),
    # 4. Weather — forecast
    Tool(
        name="get_weather_forecast",
        description=(
            "Get a short weather forecast (3-hour intervals). "
            "Warns about upcoming rain or temperature changes."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City or 'lat,lng'."},
                "hours": {
                    "type": "integer",
                    "description": "Hours ahead to forecast (max 120). Default 12.",
                },
                "units": {"type": "string", "enum": ["metric", "imperial"]},
            },
            "required": ["location"],
        },
    ),
    # 5. News — headlines
    Tool(
        name="get_top_headlines",
        description=(
            "Fetch today's top news headlines by country and optional category. "
            "Returns TTS-friendly summaries."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "country": {
                    "type": "string",
                    "description": "ISO country code, e.g. 'us', 'in', 'gb'. Default: us.",
                },
                "category": {
                    "type": "string",
                    "enum": [
                        "business", "entertainment", "general",
                        "health", "science", "sports", "technology",
                    ],
                    "description": "News category filter.",
                },
                "count": {
                    "type": "integer",
                    "description": "Number of articles (max 10). Default 5.",
                },
            },
            "required": [],
        },
    ),
    # 6. News — search
    Tool(
        name="search_news",
        description="Search news articles by keyword. Returns TTS-friendly summaries.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keywords."},
                "count": {"type": "integer", "description": "Max results (max 10)."},
                "sort_by": {
                    "type": "string",
                    "enum": ["relevancy", "popularity", "publishedAt"],
                },
            },
            "required": ["query"],
        },
    ),
    # 7. Nearby places
    Tool(
        name="find_nearby_places",
        description=(
            "Find nearby points of interest (bus stops, hospitals, pharmacies, etc.) "
            "with distance and wheelchair accessibility info."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "Address or 'lat,lng'."},
                "category": {
                    "type": "string",
                    "enum": [
                        "hospital", "pharmacy", "bus_stop", "train_station",
                        "restaurant", "cafe", "bank", "atm", "toilet",
                        "police", "fire_station", "supermarket", "park",
                        "bench", "crossing", "traffic_signal", "taxi", "shelter",
                    ],
                    "description": "POI category to search.",
                },
                "radius_m": {
                    "type": "integer",
                    "description": "Search radius in metres. Default 500.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results. Default 5.",
                },
            },
            "required": ["location", "category"],
        },
    ),
    # 8. Time & Date
    Tool(
        name="get_current_time_and_date",
        description=(
            "Get current time, date, day of week, and daylight/safety info. "
            "Useful for orientation."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    # 9. Emergency info
    Tool(
        name="get_emergency_info",
        description=(
            "Get emergency phone numbers and safety guidance, "
            "localised by country if provided."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Country or city for localised numbers.",
                },
            },
            "required": [],
        },
    ),
    # 10. Describe surroundings (bridge to EcoSight Phase 2)
    Tool(
        name="describe_surroundings",
        description=(
            "Trigger the EcoSight camera to describe the user's surroundings "
            "using the Phase 2 scene-description pipeline."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    # 11. Safety tips
    Tool(
        name="get_safety_tips",
        description=(
            "Get context-specific safety tips for blind users. "
            "Contexts: walking, crossing, public_transport, indoor, night."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "context": {
                    "type": "string",
                    "enum": ["walking", "crossing", "public_transport", "indoor", "night"],
                    "description": "Activity context. Default: walking.",
                },
            },
            "required": [],
        },
    ),
]


# ─── Handler dispatch map ────────────────────────────────────────
DISPATCH: dict[str, Any] = {
    "navigate_to_destination": navigate_to_destination,
    "fetch_available_routes": fetch_available_routes,
    "get_current_weather": get_current_weather,
    "get_weather_forecast": get_weather_forecast,
    "get_top_headlines": get_top_headlines,
    "search_news": search_news,
    "find_nearby_places": find_nearby_places,
    "get_current_time_and_date": get_current_time_and_date,
    "get_emergency_info": get_emergency_info,
    "describe_surroundings": describe_surroundings_prompt,
    "get_safety_tips": get_safety_tips,
}


# ─── MCP Protocol Handlers ───────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Return the catalogue of available tools."""
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Dispatch a tool call to the correct handler."""
    handler = DISPATCH.get(name)
    if handler is None:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    try:
        result = await handler(**arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
    except Exception as exc:
        logger.exception("Tool %s failed", name)
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": str(exc),
                "spoken_summary": f"Sorry, {name.replace('_', ' ')} failed. {exc}",
            }),
        )]


# ─── Entry-point ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="EcoSight MCP Server")
    parser.add_argument("--sse", action="store_true", help="Use SSE transport instead of stdio")
    parser.add_argument("--port", type=int, default=8100, help="Port for SSE transport (default 8100)")
    args = parser.parse_args()

    if args.sse:
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount
        import uvicorn

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                await app.run(streams[0], streams[1], app.create_initialization_options())

        starlette_app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )
        logger.info("Starting EcoSight MCP Server (SSE) on port %d", args.port)
        uvicorn.run(starlette_app, host="0.0.0.0", port=args.port)
    else:
        import asyncio
        from mcp.server.stdio import stdio_server

        async def run_stdio():
            async with stdio_server() as streams:
                logger.info("Starting EcoSight MCP Server (stdio)")
                await app.run(streams[0], streams[1], app.create_initialization_options())

        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
