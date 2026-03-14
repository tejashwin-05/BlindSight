"""
EcoSight MCP Server — Configuration
All API keys, endpoints, and tuneable constants live here.
Set environment variables or edit defaults below.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from mcp_server directory
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"[Config] Loaded environment from {env_path}")
else:
    print(f"[Config] No .env file found at {env_path}")

# ─── Server ──────────────────────────────────────────────────────
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8100"))
SERVER_NAME = "ecosight-mcp"
SERVER_VERSION = "1.0.0"

# ─── OpenRouteService (routing / navigation / geocoding) ─────────
ORS_API_KEY = os.getenv("ORS_API_KEY", "")  # https://openrouteservice.org/dev/#/signup
ORS_BASE_URL = "https://api.openrouteservice.org"

# ─── OpenWeatherMap ──────────────────────────────────────────────
OWM_API_KEY = os.getenv("OWM_API_KEY", "")  # https://openweathermap.org/api
OWM_BASE_URL = "https://api.openweathermap.org/data/2.5"

# ─── NewsAPI ─────────────────────────────────────────────────────
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")  # https://newsapi.org
NEWS_BASE_URL = "https://newsapi.org/v2"

# ─── Overpass / OpenStreetMap (POI lookup — no key needed) ───────
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# ─── Accessibility defaults ──────────────────────────────────────
DEFAULT_WALKING_PROFILE = "foot-walking"        # ORS profile
DEFAULT_WHEELCHAIR_PROFILE = "wheelchair"        # ORS profile
DEFAULT_UNITS = "metric"                         # metric | imperial
DEFAULT_LANGUAGE = "en"
MAX_ROUTE_ALTERNATIVES = 3

# ─── Emergency ───────────────────────────────────────────────────
EMERGENCY_NUMBER = os.getenv("EMERGENCY_NUMBER", "112")  # default international
