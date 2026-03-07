"""
EcoSight Agentic Orchestrator Server (v1)

Standalone LangChain-based tool-calling server for day-to-day tasks.
This server is isolated from the main pipeline.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@dataclass
class ServerConfig:
    host: str = os.getenv("ECOSIGHT_AGENT_HOST", "0.0.0.0")
    port: int = int(os.getenv("ECOSIGHT_AGENT_PORT", "8091"))
    api_key: str = os.getenv("ECOSIGHT_AGENT_API_KEY", "")
    model: str = os.getenv("ECOSIGHT_AGENT_MODEL", "deepseek-r1:1.5b")
    ollama_base_url: str = os.getenv("ECOSIGHT_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    timeout_sec: int = int(os.getenv("ECOSIGHT_AGENT_TIMEOUT_SEC", "18"))
    gmaps_api_key: str = os.getenv("ECOSIGHT_GMAPS_API_KEY", "AIzaSyA43RpbHXS0rdlegp6XAgmrB-8RzC41uow")


CONFIG = ServerConfig()


def _safe_json_parse(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        return {}

    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    return {}


class AgentEngine:
    def __init__(self) -> None:
        self._langchain_ready = False
        self._init_error: str | None = None
        self._tools = []
        self._tool_map = {}
        self._llm = None
        self._llm_with_tools = None

        self.contact_book = {
            "mom": "tel:+919493312768",
            "mother": "tel:+919493312768",
            "dad": "tel:+918523072687",
            "father": "tel:+918523072687",
            "brother": "tel:+933333333333",
            "sister": "tel:+944444444444",
        }

        self._try_init_langchain()

    def _try_init_langchain(self) -> None:
        try:
            from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
            from langchain_core.tools import tool
            from langchain_ollama import ChatOllama
        except Exception as exc:
            self._init_error = f"LangChain imports unavailable: {exc}"
            return

        self.HumanMessage = HumanMessage
        self.SystemMessage = SystemMessage
        self.ToolMessage = ToolMessage

        @tool
        def get_current_time() -> str:
            """Get current local date-time for the user."""
            return datetime.now().strftime("%A, %d %B %Y %I:%M %p")

        @tool
        def get_weather(latitude: float, longitude: float) -> str:
            """Get current weather using latitude and longitude via Google Weather API."""
            key = CONFIG.gmaps_api_key
            if not key:
                return "No Google Maps API key configured."
            url = (
                "https://weather.googleapis.com/v1/currentConditions:lookup"
                f"?key={key}"
            )
            body = json.dumps({"location": {"latitude": latitude, "longitude": longitude}}).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            temp = data.get("temperature", {}).get("degrees")
            feels = data.get("feelsLikeTemperature", {}).get("degrees")
            humidity = data.get("relativeHumidity")
            wind = data.get("wind", {}).get("speed", {}).get("value")
            desc = data.get("weatherCondition", {}).get("description", {}).get("text", "")
            if not desc:
                desc = data.get("weatherCondition", {}).get("type", "unknown")
            return (
                f"condition={desc}, temperature={temp}C, feels_like={feels}C, "
                f"humidity={humidity}%, wind={wind}km/h"
            )

        @tool
        def call_relative(relative_name: str) -> str:
            """Get dial URL for a relative (mom/dad/brother/sister)."""
            key = (relative_name or "").strip().lower()
            if key not in self.contact_book:
                return "not_found"
            return self.contact_book[key]

        @tool
        def get_location_hint(latitude: float, longitude: float) -> str:
            """Format location coordinates into a user-friendly text."""
            return f"latitude={latitude:.5f}, longitude={longitude:.5f}"

        @tool
        def reverse_geocode(latitude: float, longitude: float) -> str:
            """Convert latitude and longitude to a human-readable address using Google Maps."""
            key = CONFIG.gmaps_api_key
            if not key:
                return f"No Google Maps key. Coordinates: {latitude:.5f}, {longitude:.5f}"
            url = (
                "https://maps.googleapis.com/maps/api/geocode/json?"
                f"latlng={latitude},{longitude}&key={key}"
            )
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])
            if results:
                return results[0].get("formatted_address", "Unknown address")
            return "No address found for these coordinates."

        @tool
        def find_nearby_places(latitude: float, longitude: float, place_type: str, radius_meters: int = 500) -> str:
            """Find nearby places using Google Maps. place_type examples: hospital, restaurant, bus_station, pharmacy, atm, park, police, grocery_or_supermarket."""
            key = CONFIG.gmaps_api_key
            if not key:
                return "No Google Maps key configured."
            url = (
                "https://maps.googleapis.com/maps/api/place/nearbysearch/json?"
                f"location={latitude},{longitude}&radius={radius_meters}"
                f"&type={place_type}&key={key}"
            )
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            places = data.get("results", [])[:5]
            if not places:
                return f"No {place_type} found within {radius_meters} meters."
            lines = []
            for p in places:
                name = p.get("name", "Unknown")
                vicinity = p.get("vicinity", "")
                rating = p.get("rating", "N/A")
                open_now = p.get("opening_hours", {}).get("open_now")
                status = "open" if open_now else ("closed" if open_now is False else "unknown hours")
                lines.append(f"{name} ({vicinity}) rating={rating} status={status}")
            return "; ".join(lines)

        @tool
        def get_walking_directions(origin_lat: float, origin_lng: float, destination: str) -> str:
            """Get walking directions from current location to a destination name or address using Google Maps."""
            key = CONFIG.gmaps_api_key
            if not key:
                return "No Google Maps key configured."
            origin = f"{origin_lat},{origin_lng}"
            dest_encoded = urllib.request.quote(destination)
            url = (
                "https://maps.googleapis.com/maps/api/directions/json?"
                f"origin={origin}&destination={dest_encoded}"
                f"&mode=walking&key={key}"
            )
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            routes = data.get("routes", [])
            if not routes:
                return f"No walking route found to {destination}."
            leg = routes[0].get("legs", [{}])[0]
            distance = leg.get("distance", {}).get("text", "unknown")
            duration = leg.get("duration", {}).get("text", "unknown")
            steps = leg.get("steps", [])
            instructions = []
            for i, step in enumerate(steps[:8], 1):
                text = step.get("html_instructions", "")
                # Strip HTML tags
                import re
                clean = re.sub(r"<[^>]+>", " ", text).strip()
                step_dist = step.get("distance", {}).get("text", "")
                instructions.append(f"Step {i}: {clean} ({step_dist})")
            header = f"Walking to {destination}: {distance}, about {duration}."
            return header + " " + " ".join(instructions)

        self._tools = [
            get_current_time,
            get_weather,
            call_relative,
            get_location_hint,
            reverse_geocode,
            find_nearby_places,
            get_walking_directions,
        ]
        self._tool_map = {tool_obj.name: tool_obj for tool_obj in self._tools}

        self._llm = ChatOllama(
            model=CONFIG.model,
            base_url=CONFIG.ollama_base_url,
            temperature=0.3,
            num_predict=512,
        )
        self._llm_with_tools = self._llm.bind_tools(self._tools)
        self._langchain_ready = True

    def health(self) -> dict:
        return {
            "langchain_ready": self._langchain_ready,
            "langchain_error": self._init_error,
            "provider": "ollama",
            "model": CONFIG.model,
            "ollama_base_url": CONFIG.ollama_base_url,
        }

    def _fallback(self, text: str, context: dict) -> dict:
        t = (text or "").lower()
        if "describe" in t and "scene" in t:
            return {
                "action": "describe_scene",
                "speak_text": "Okay, describing the current scene.",
                "parameters": {},
            }
        if "start" in t and "stream" in t:
            return {
                "action": "start_stream",
                "speak_text": "Starting camera stream.",
                "parameters": {},
            }
        if "stop" in t and "stream" in t:
            return {
                "action": "stop_stream",
                "speak_text": "Stopping camera stream.",
                "parameters": {},
            }
        if "health" in t:
            return {
                "action": "check_health",
                "speak_text": "Checking server health.",
                "parameters": {},
            }
        if "call" in t:
            for rel, tel in self.contact_book.items():
                if rel in t:
                    return {
                        "action": "call_relative",
                        "speak_text": f"Opening dialer to call {rel}.",
                        "parameters": {"relative": rel, "tel": tel},
                    }

        if "where" in t and ("am i" in t or "i am" in t or "location" in t):
            lat = context.get("latitude")
            lng = context.get("longitude")
            if lat is not None and lng is not None:
                try:
                    key = CONFIG.gmaps_api_key
                    url = (
                        "https://maps.googleapis.com/maps/api/geocode/json?"
                        f"latlng={lat},{lng}&key={key}"
                    )
                    with urllib.request.urlopen(url, timeout=10) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                    results = data.get("results", [])
                    addr = results[0].get("formatted_address", "unknown") if results else "unknown"
                    return {
                        "action": "none",
                        "speak_text": f"You are near {addr}.",
                        "parameters": {},
                    }
                except Exception:
                    pass
            return {
                "action": "none",
                "speak_text": f"Your coordinates are {lat}, {lng}.",
                "parameters": {},
            }

        if "weather" in t or "temperature" in t or "hot" in t or "cold" in t or "rain" in t:
            lat = context.get("latitude")
            lng = context.get("longitude")
            if lat is not None and lng is not None:
                try:
                    key = CONFIG.gmaps_api_key
                    url = (
                        "https://weather.googleapis.com/v1/currentConditions:lookup"
                        f"?key={key}"
                    )
                    body = json.dumps({"location": {"latitude": lat, "longitude": lng}}).encode("utf-8")
                    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                    temp = data.get("temperature", {}).get("degrees")
                    feels = data.get("feelsLikeTemperature", {}).get("degrees")
                    humidity = data.get("relativeHumidity")
                    wind_speed = data.get("wind", {}).get("speed", {}).get("value")
                    desc = data.get("weatherCondition", {}).get("description", {}).get("text", "")
                    if not desc:
                        desc = data.get("weatherCondition", {}).get("type", "unknown")
                    return {
                        "action": "none",
                        "speak_text": (
                            f"Current weather: {desc}. "
                            f"Temperature is {temp} degrees, feels like {feels} degrees. "
                            f"Wind speed {wind_speed} kilometers per hour, "
                            f"humidity {humidity} percent."
                        ),
                        "parameters": {},
                    }
                except Exception:
                    pass
            return {
                "action": "none",
                "speak_text": "I could not fetch the weather. GPS may be unavailable.",
                "parameters": {},
            }

        if "nearby" in t or "nearest" in t or "find" in t:
            return {
                "action": "none",
                "speak_text": "Searching for nearby places. Please wait.",
                "parameters": {},
            }

        return {
            "action": "none",
            "speak_text": (
                "I can describe scene, start or stop stream, check health, "
                "call a relative, find your location, search nearby places, "
                "or get walking directions."
            ),
            "parameters": {},
        }

    def execute(self, text: str, context: dict | None = None) -> dict:
        context = context or {}
        if not text.strip():
            return {
                "action": "none",
                "speak_text": "Please say a command.",
                "parameters": {},
            }

        if not self._langchain_ready:
            return self._fallback(text, context)

        system = self.SystemMessage(
            content=(
                "You are EcoSight — a caring, intelligent voice assistant built to help "
                "a visually impaired user navigate their day confidently and independently. "
                "Speak warmly, clearly, and concisely. The user hears your reply via text-to-speech, "
                "so keep sentences short and natural. Never use markdown, bullet points, or symbols.\n\n"

                "YOU HAVE ACCESS TO THESE TOOLS — use them whenever the user's request can benefit:\n"
                "1. get_current_time() → returns the current local date and time.\n"
                "2. get_weather(latitude, longitude) → fetches live weather (temperature, humidity, wind, condition) via Google Weather API.\n"
                "3. reverse_geocode(latitude, longitude) → converts GPS coordinates to a human-readable address.\n"
                "4. find_nearby_places(latitude, longitude, place_type, radius_meters=500) → "
                "searches for nearby places. place_type examples: hospital, pharmacy, bus_station, "
                "restaurant, atm, park, police, grocery_or_supermarket.\n"
                "5. get_walking_directions(origin_lat, origin_lng, destination) → gives step-by-step walking directions.\n"
                "6. call_relative(relative_name) → returns a dial URL for a family member (mom, dad, brother, sister).\n"
                "7. get_location_hint(latitude, longitude) → formats coordinates into readable text.\n\n"

                "HOW TO RESPOND:\n"
                "- Think about what the user needs. If a tool can help, call it first.\n"
                "- After getting tool results, compose a warm, spoken reply summarising the answer.\n"
                "- Return STRICT JSON with these keys: action, speak_text, parameters.\n"
                "- speak_text is what the user will HEAR — make it friendly and complete.\n"
                "- Allowed actions: describe_scene, start_stream, stop_stream, check_health, "
                "call_relative, navigate, none.\n"
                "- For call_relative, put {\"relative\": \"name\", \"tel\": \"tel:+...\"} in parameters.\n"
                "- For navigate, put {\"destination\": \"place name\"} in parameters.\n"
                "- For informational answers (weather, time, location, nearby), use action=\"none\".\n\n"

                "IMPORTANT: The user's current GPS coordinates are provided in the context object. "
                "Use them as latitude/longitude arguments when calling location-based tools — "
                "do NOT ask the user for coordinates.\n\n"

                "Remember: you are this person's eyes and companion. Be helpful, respectful, "
                "and reassuring. If you're unsure, say so honestly and suggest what you can do."
            )
        )
        user = self.HumanMessage(
            content=json.dumps(
                {
                    "user_said": text,
                    "gps": {
                        "latitude": context.get("latitude"),
                        "longitude": context.get("longitude"),
                    },
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                ensure_ascii=False,
            )
        )

        messages = [system, user]

        try:
            first = self._llm_with_tools.invoke(messages)

            tool_messages = []
            tool_trace = []
            for call in (first.tool_calls or []):
                name = call.get("name")
                args = call.get("args", {})
                tool = self._tool_map.get(name)
                if tool is None:
                    continue

                result = tool.invoke(args)
                tool_trace.append({"tool": name, "args": args, "result": str(result)})
                tool_messages.append(
                    self.ToolMessage(
                        content=str(result),
                        tool_call_id=call.get("id", ""),
                    )
                )

            final_msg = (
                self._llm_with_tools.invoke(messages + [first] + tool_messages)
                if tool_messages
                else first
            )

            structured = _safe_json_parse(getattr(final_msg, "content", ""))
            if not structured:
                structured = self._fallback(text, context)

            structured.setdefault("action", "none")
            structured.setdefault("speak_text", "Done")
            structured.setdefault("parameters", {})
            structured["tool_trace"] = tool_trace
            return structured
        except Exception:
            return self._fallback(text, context)


ENGINE = AgentEngine()


class AgenticHandler(BaseHTTPRequestHandler):
    server_version = "EcoSightAgenticV1/1.0"

    def _check_api_key(self) -> bool:
        if not CONFIG.api_key:
            return True
        return self.headers.get("X-API-Key", "") == CONFIG.api_key

    def _write_json(self, code: int, payload: dict):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self._write_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "service": "ecosight-agentic-v1",
                    "agent": ENGINE.health(),
                    "ts": int(time.time() * 1000),
                },
            )
            return

        self._write_json(
            HTTPStatus.NOT_FOUND,
            {
                "ok": False,
                "error": "not_found",
                "message": "Use GET /health or POST /v1/agent/execute, /v1/directions, or /v1/places/autocomplete",
            },
        )

    def _handle_places_autocomplete(self, payload: dict):
        """Google Places Autocomplete proxy — returns place predictions."""
        query = (payload.get("query") or "").strip()
        lat = payload.get("latitude")
        lng = payload.get("longitude")

        if not query:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "validation_error",
                 "message": "query is required"},
            )
            return

        key = CONFIG.gmaps_api_key
        if not key:
            self._write_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": "config_error",
                 "message": "No Google Maps API key configured"},
            )
            return

        params = f"input={urllib.request.quote(query)}&key={key}"
        if lat is not None and lng is not None:
            params += f"&location={lat},{lng}&radius=50000"
        url = f"https://maps.googleapis.com/maps/api/place/autocomplete/json?{params}"

        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            self._write_json(
                HTTPStatus.BAD_GATEWAY,
                {"ok": False, "error": "places_api_error",
                 "message": str(exc)},
            )
            return

        predictions = data.get("predictions", [])
        results = []
        for p in predictions[:8]:
            place_id = p.get("place_id", "")
            description = p.get("description", "")
            main_text = p.get("structured_formatting", {}).get("main_text", "")
            secondary_text = p.get("structured_formatting", {}).get("secondary_text", "")
            results.append({
                "place_id": place_id,
                "description": description,
                "main_text": main_text,
                "secondary_text": secondary_text,
            })

        self._write_json(HTTPStatus.OK, {"ok": True, "predictions": results})

    def _handle_place_details(self, payload: dict):
        """Get lat/lng for a place_id via Google Places Details."""
        place_id = (payload.get("place_id") or "").strip()

        if not place_id:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "validation_error",
                 "message": "place_id is required"},
            )
            return

        key = CONFIG.gmaps_api_key
        if not key:
            self._write_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": "config_error",
                 "message": "No Google Maps API key configured"},
            )
            return

        url = (
            "https://maps.googleapis.com/maps/api/place/details/json?"
            f"place_id={place_id}&fields=geometry,name,formatted_address&key={key}"
        )

        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            self._write_json(
                HTTPStatus.BAD_GATEWAY,
                {"ok": False, "error": "place_details_error",
                 "message": str(exc)},
            )
            return

        result = data.get("result", {})
        location = result.get("geometry", {}).get("location", {})
        self._write_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "name": result.get("name", ""),
                "address": result.get("formatted_address", ""),
                "latitude": location.get("lat"),
                "longitude": location.get("lng"),
            },
        )

    def _handle_directions(self, payload: dict):
        """Return structured walking directions with GPS waypoints for each step."""
        origin_lat = payload.get("origin_lat")
        origin_lng = payload.get("origin_lng")
        destination = payload.get("destination", "")

        if origin_lat is None or origin_lng is None or not destination:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {"ok": False, "error": "validation_error",
                 "message": "origin_lat, origin_lng, and destination are required"},
            )
            return

        key = CONFIG.gmaps_api_key
        if not key:
            self._write_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "error": "config_error",
                 "message": "No Google Maps API key configured"},
            )
            return

        import re as _re
        origin = f"{origin_lat},{origin_lng}"
        dest_encoded = urllib.request.quote(str(destination))
        url = (
            "https://maps.googleapis.com/maps/api/directions/json?"
            f"origin={origin}&destination={dest_encoded}"
            f"&mode=walking&key={key}"
        )

        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            self._write_json(
                HTTPStatus.BAD_GATEWAY,
                {"ok": False, "error": "directions_api_error",
                 "message": str(exc)},
            )
            return

        routes = data.get("routes", [])
        if not routes:
            self._write_json(
                HTTPStatus.OK,
                {"ok": True, "found": False, "destination": destination,
                 "message": f"No walking route found to {destination}."},
            )
            return

        leg = routes[0].get("legs", [{}])[0]
        total_distance = leg.get("distance", {}).get("text", "unknown")
        total_duration = leg.get("duration", {}).get("text", "unknown")
        dest_address = leg.get("end_address", destination)

        steps_raw = leg.get("steps", [])
        steps_out = []
        for i, step in enumerate(steps_raw):
            html = step.get("html_instructions", "")
            clean = _re.sub(r"<[^>]+>", " ", html).strip()
            clean = _re.sub(r"\s+", " ", clean)
            start_loc = step.get("start_location", {})
            end_loc = step.get("end_location", {})
            steps_out.append({
                "index": i + 1,
                "instruction": clean,
                "distance": step.get("distance", {}).get("text", ""),
                "duration": step.get("duration", {}).get("text", ""),
                "start_lat": start_loc.get("lat"),
                "start_lng": start_loc.get("lng"),
                "end_lat": end_loc.get("lat"),
                "end_lng": end_loc.get("lng"),
            })

        dest_loc = leg.get("end_location", {})

        self._write_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "found": True,
                "destination": dest_address,
                "total_distance": total_distance,
                "total_duration": total_duration,
                "dest_lat": dest_loc.get("lat"),
                "dest_lng": dest_loc.get("lng"),
                "steps": steps_out,
            },
        )

    _VALID_POST_PATHS = frozenset({
        "/v1/agent/execute",
        "/v1/directions",
        "/v1/places/autocomplete",
        "/v1/places/details",
    })

    def do_POST(self):
        if self.path not in self._VALID_POST_PATHS:
            self._write_json(
                HTTPStatus.NOT_FOUND,
                {
                    "ok": False,
                    "error": "not_found",
                    "message": "Unknown endpoint",
                },
            )
            return

        if not self._check_api_key():
            self._write_json(
                HTTPStatus.UNAUTHORIZED,
                {
                    "ok": False,
                    "error": "unauthorized",
                    "message": "Missing or invalid X-API-Key",
                },
            )
            return

        try:
            content_len = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_len = 0

        if content_len <= 0:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "ok": False,
                    "error": "bad_request",
                    "message": "Request body is required",
                },
            )
            return

        try:
            raw = self.rfile.read(content_len)
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "ok": False,
                    "error": "bad_json",
                    "message": str(exc),
                },
            )
            return

        # Route to directions endpoint if applicable
        if self.path == "/v1/directions":
            self._handle_directions(payload)
            return

        # Route to places autocomplete
        if self.path == "/v1/places/autocomplete":
            self._handle_places_autocomplete(payload)
            return

        # Route to place details
        if self.path == "/v1/places/details":
            self._handle_place_details(payload)
            return

        text = str(payload.get("text", "")).strip()
        context = payload.get("context", {})
        if context is None:
            context = {}
        if not isinstance(context, dict):
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "ok": False,
                    "error": "validation_error",
                    "message": "context must be an object",
                },
            )
            return

        started = time.perf_counter()
        result = ENGINE.execute(text=text, context=context)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        self._write_json(
            HTTPStatus.OK,
            {
                "ok": True,
                "result": result,
                "latency_ms": elapsed_ms,
                "ts": int(time.time() * 1000),
            },
        )

    def log_message(self, fmt: str, *args):
        print(f"[agent-v1] {self.address_string()} - {fmt % args}")


def run() -> None:
    server = ThreadingHTTPServer((CONFIG.host, CONFIG.port), AgenticHandler)
    print("[agent-v1] Agentic orchestration server started")
    print(f"[agent-v1] Listening on http://{CONFIG.host}:{CONFIG.port}")
    if CONFIG.api_key:
        print("[agent-v1] API key auth enabled (X-API-Key)")
    else:
        print("[agent-v1] API key auth disabled (dev mode)")

    health = ENGINE.health()
    print(
        "[agent-v1] LangChain ready:",
        health["langchain_ready"],
        "| provider:",
        health["provider"],
        "| model:",
        health["model"],
        "| ollama:",
        health["ollama_base_url"],
    )
    if health["langchain_error"]:
        print("[agent-v1] LangChain init warning:", health["langchain_error"])

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("[agent-v1] Server stopped")


if __name__ == "__main__":
    run()
