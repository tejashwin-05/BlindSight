# EcoSight MCP Server

Agentic tool-calling server for **EcoSight** — providing blind and visually-impaired users with intelligent, context-aware assistance beyond real-time hazard detection.

Built on the **Model Context Protocol (MCP)**, this server exposes tools that any MCP-compatible AI agent (Claude, Copilot, custom LLM agents) can invoke on behalf of the user.

---

## Tools Available

| # | Tool | Description |
|---|------|-------------|
| 1 | `navigate_to_destination` | Step-by-step walking directions (turn-by-turn, TTS-ready) |
| 2 | `fetch_available_routes` | Multiple route alternatives with accessibility warnings (stairs, elevation, surface) |
| 3 | `get_current_weather` | Current weather with comfort description and rain/snow alerts |
| 4 | `get_weather_forecast` | 3-hour interval forecast for the next N hours |
| 5 | `get_top_headlines` | Top news headlines by country/category |
| 6 | `search_news` | Keyword search across news articles |
| 7 | `find_nearby_places` | POI search (bus stops, hospitals, pharmacies, crossings, etc.) via OpenStreetMap |
| 8 | `get_current_time_and_date` | Time, date, day of week + daylight safety info |
| 9 | `get_emergency_info` | Localised emergency numbers + safety guidance |
| 10 | `describe_surroundings` | Bridge to EcoSight Phase 2 scene description pipeline |
| 11 | `get_safety_tips` | Context-specific safety tips (walking, crossing, night, transit, indoor) |

Every tool returns a **`spoken_summary`** field — a natural-language string optimised for text-to-speech output.

---

## Setup

### 1. Install dependencies

```bash
cd mcp_server
pip install -r requirements.txt
```

### 2. Set API keys

Create a `.env` file in the project root or export environment variables:

```bash
# OpenRouteService — routing, directions, geocoding (free tier)
# Sign up: https://openrouteservice.org/dev/#/signup
export ORS_API_KEY="your_ors_key"

# OpenWeatherMap — weather data (free tier)
# Sign up: https://openweathermap.org/api
export OWM_API_KEY="your_owm_key"

# NewsAPI — news headlines & search (free tier)
# Sign up: https://newsapi.org
export NEWS_API_KEY="your_news_key"
```

### 3. Run the server

**Stdio transport** (default — for local MCP clients like Claude Desktop):
```bash
python -m mcp_server
```

**SSE transport** (for web/remote clients):
```bash
python -m mcp_server --sse --port 8100
```

---

## MCP Client Configuration

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "ecosight": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "path/to/EcoSight",
      "env": {
        "ORS_API_KEY": "your_key",
        "OWM_API_KEY": "your_key",
        "NEWS_API_KEY": "your_key"
      }
    }
  }
}
```

### VS Code / Copilot (`.vscode/mcp.json`)

```json
{
  "servers": {
    "ecosight": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "${workspaceFolder}",
      "env": {
        "ORS_API_KEY": "your_key",
        "OWM_API_KEY": "your_key",
        "NEWS_API_KEY": "your_key"
      }
    }
  }
}
```

---

## Architecture

```
mcp_server/
├── __init__.py          # Package marker
├── __main__.py          # python -m entry point
├── server.py            # MCP server — tool registry + dispatch
├── config.py            # API keys, endpoints, defaults
├── requirements.txt     # Python dependencies
├── README.md            # This file
└── tools/
    ├── __init__.py
    ├── navigation.py    # Turn-by-turn walking directions
    ├── routes.py        # Multi-route alternatives + accessibility
    ├── weather.py       # Current weather + forecast
    ├── news.py          # Headlines + search
    ├── places.py        # Nearby POI via OpenStreetMap
    └── accessibility.py # Time, emergency, safety tips
```

### External APIs used

| API | Purpose | Free Tier |
|-----|---------|-----------|
| [OpenRouteService](https://openrouteservice.org) | Routing, geocoding, directions | 2,000 req/day |
| [OpenWeatherMap](https://openweathermap.org) | Weather current + forecast | 1,000 req/day |
| [NewsAPI](https://newsapi.org) | News headlines + search | 100 req/day |
| [Overpass / OSM](https://overpass-api.de) | Nearby places (POI) | Unlimited (fair use) |

---

## Integration with EcoSight

This MCP server complements the existing EcoSight pipeline:

- **Phase 1 (Reflex)** — Real-time hazard detection via YOLOv8 + depth estimation (existing `server/`)
- **Phase 2 (Context)** — On-demand scene description via Florence-2 (existing `server/`)
- **MCP Server (Agent)** — Higher-level agentic capabilities: navigation, weather, news, places, safety

The `describe_surroundings` tool bridges the MCP agent back to Phase 2 by triggering a scene capture.

---

## License

Part of the EcoSight project.
