"""
BlindSight — Cloud WebSocket Server
Lightweight entry point for Render deployment.
No camera, no OpenCV, no ML models.
Only handles WebSocket connections + MCP tool relay.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import websockets

# ── Ensure repo root is on path so mcp_client can find mcp_server ─
repo_root = Path(__file__).parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# ── Load .env if present ─────────────────────────────────────────
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

# ── MCP client (imports only mcp_server tools, no ML) ────────────
from mcp_client import mcp_client

WEBSOCKET_HOST = "0.0.0.0"
WEBSOCKET_PORT = int(os.getenv("PORT", 8765))

clients: set = set()


async def _reverse_geocode_country(lat: float, lng: float, full_name: bool = False) -> str:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=8, headers={"User-Agent": "BlindSight/1.0"}) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": lat, "lon": lng, "format": "json", "zoom": 3},
            )
            resp.raise_for_status()
            data = resp.json()
            addr = data.get("address", {})
            if full_name:
                return addr.get("country", "India")
            return addr.get("country_code", "in").lower()
    except Exception as e:
        print(f"[GEO] Reverse geocode failed: {e}")
        return "in" if not full_name else "India"


async def ws_handler(websocket):
    clients.add(websocket)
    print(f"[WS] Client connected: {websocket.remote_address}")

    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))

            elif msg_type == "location_update":
                pass  # acknowledged, no-op in cloud mode

            elif msg_type == "trigger_phase2":
                await websocket.send(json.dumps({
                    "type": "phase_2",
                    "status": "done",
                    "description": "Scene description is only available when the local server is running with a camera."
                }))

            elif msg_type == "mcp_request":
                tool_name = data.get("tool", "")
                tool_input = data.get("input", "")
                params = {}
                should_call = True

                if tool_name == "navigate":
                    if " to " in tool_input:
                        parts = tool_input.split(" to ", 1)
                        origin = parts[0].strip()
                        if origin.lower().startswith("from "):
                            origin = origin[5:].strip()
                        params["origin"] = origin
                        params["destination"] = parts[1].strip()
                    else:
                        should_call = False
                        await websocket.send(json.dumps({
                            "type": "mcp_response",
                            "tool": tool_name,
                            "result": {"error": "Please provide both origin and destination."},
                            "spoken_summary": "Please provide both starting point and destination."
                        }))

                elif tool_name in ["weather", "forecast"]:
                    params["location"] = tool_input or "London"

                elif tool_name == "headlines":
                    if tool_input and "," in tool_input:
                        parts_ll = tool_input.split(",")
                        try:
                            lat_v, lng_v = float(parts_ll[0].strip()), float(parts_ll[1].strip())
                            params["country"] = await _reverse_geocode_country(lat_v, lng_v)
                        except ValueError:
                            params["country"] = tool_input or "us"
                    else:
                        params["country"] = tool_input or "us"

                elif tool_name == "search_news":
                    params["query"] = tool_input

                elif tool_name == "safety_tips":
                    params["context"] = tool_input or "walking"

                elif tool_name == "emergency":
                    if tool_input and "," in tool_input:
                        parts_ll = tool_input.split(",")
                        try:
                            lat_v, lng_v = float(parts_ll[0].strip()), float(parts_ll[1].strip())
                            params["location"] = await _reverse_geocode_country(lat_v, lng_v, full_name=True)
                        except ValueError:
                            params["location"] = tool_input
                    else:
                        params["location"] = tool_input

                if should_call:
                    result = await mcp_client.call_tool(tool_name, params)
                    await websocket.send(json.dumps({
                        "type": "mcp_response",
                        "tool": tool_name,
                        "result": result,
                        "spoken_summary": result.get("spoken_summary", "")
                    }))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        clients.discard(websocket)
        print(f"[WS] Client disconnected: {websocket.remote_address}")


async def main():
    print("=" * 50)
    print("  BlindSight Cloud WebSocket Server")
    print(f"  Listening on ws://{WEBSOCKET_HOST}:{WEBSOCKET_PORT}")
    print("=" * 50)

    async with websockets.serve(ws_handler, WEBSOCKET_HOST, WEBSOCKET_PORT):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
