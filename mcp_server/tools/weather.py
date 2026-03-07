"""
EcoSight MCP Tool — Weather
Current weather and short forecast, with blind-friendly natural language output.

Uses OpenWeatherMap API.
"""

from __future__ import annotations

import httpx
from typing import Any

from mcp_server.config import OWM_API_KEY, OWM_BASE_URL


def _comfort_description(temp: float, humidity: int, wind_speed: float) -> str:
    """Generate a comfort-level sentence for TTS."""
    parts = []
    if temp < 0:
        parts.append("It is freezing cold")
    elif temp < 10:
        parts.append("It is quite cold")
    elif temp < 20:
        parts.append("The temperature is cool and pleasant")
    elif temp < 30:
        parts.append("It is warm")
    else:
        parts.append("It is very hot")

    if humidity > 80:
        parts.append("and very humid")
    elif humidity > 60:
        parts.append("with moderate humidity")

    if wind_speed > 10:
        parts.append("with strong winds — hold onto your hat")
    elif wind_speed > 5:
        parts.append("with a noticeable breeze")

    return ". ".join(parts) + "."


def _rain_warning(weather_list: list[dict]) -> str | None:
    """Check if rain or snow is in the condition list."""
    for w in weather_list:
        main_lower = w.get("main", "").lower()
        if "rain" in main_lower:
            return "Rain is expected — consider carrying an umbrella."
        if "snow" in main_lower:
            return "Snow is expected — paths may be slippery."
        if "thunderstorm" in main_lower:
            return "Thunderstorms are expected — it may be safest to stay indoors."
    return None


async def get_current_weather(
    location: str,
    units: str = "metric",
) -> dict[str, Any]:
    """
    Get current weather conditions for a location.

    Args:
        location: City name, "City,Country" or "lat,lng".
        units:    "metric" (°C, m/s) or "imperial" (°F, mph).

    Returns dict with:
        spoken_summary  – natural-language description ready for TTS
        temperature     – current temp
        feels_like      – what it feels like
        humidity        – %
        wind_speed      – speed
        condition       – short label ("Clear", "Clouds", etc.)
        rain_warning    – optional rain/snow alert
        raw             – full API payload
    """
    params: dict[str, Any] = {
        "appid": OWM_API_KEY,
        "units": units,
        "q": location,
    }

    # Allow "lat,lng" input
    if "," in location:
        parts = location.split(",")
        try:
            lat, lng = float(parts[0].strip()), float(parts[1].strip())
            params.pop("q")
            params["lat"] = lat
            params["lon"] = lng
        except ValueError:
            pass  # keep as city query

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{OWM_BASE_URL}/weather", params=params)
        resp.raise_for_status()
        data = resp.json()

    temp = data["main"]["temp"]
    feels = data["main"]["feels_like"]
    humidity = data["main"]["humidity"]
    wind = data["wind"]["speed"]
    condition = data["weather"][0]["main"]
    description = data["weather"][0]["description"]
    city = data.get("name", location)
    unit_label = "°C" if units == "metric" else "°F"
    speed_label = "metres per second" if units == "metric" else "miles per hour"

    rain = _rain_warning(data.get("weather", []))
    comfort = _comfort_description(temp, humidity, wind)

    spoken = (
        f"Current weather in {city}: {description}. "
        f"Temperature is {temp:.0f}{unit_label}, feels like {feels:.0f}{unit_label}. "
        f"Humidity {humidity}%. Wind speed {wind:.1f} {speed_label}. "
        f"{comfort}"
    )
    if rain:
        spoken += f" {rain}"

    return {
        "spoken_summary": spoken,
        "temperature": f"{temp:.1f}{unit_label}",
        "feels_like": f"{feels:.1f}{unit_label}",
        "humidity": f"{humidity}%",
        "wind_speed": f"{wind:.1f} {speed_label}",
        "condition": condition,
        "description": description,
        "rain_warning": rain,
        "city": city,
    }


async def get_weather_forecast(
    location: str,
    hours: int = 12,
    units: str = "metric",
) -> dict[str, Any]:
    """
    Get a short weather forecast (3-hour intervals) for upcoming hours.

    Args:
        location: City name or "lat,lng".
        hours:    How many hours ahead to forecast (max 120, step 3).
        units:    "metric" or "imperial".

    Returns:
        spoken_summary – overview ready for TTS
        periods        – list of 3-hour forecast blocks
    """
    params: dict[str, Any] = {
        "appid": OWM_API_KEY,
        "units": units,
        "q": location,
        "cnt": max(1, hours // 3),
    }
    if "," in location:
        parts = location.split(",")
        try:
            lat, lng = float(parts[0].strip()), float(parts[1].strip())
            params.pop("q")
            params["lat"] = lat
            params["lon"] = lng
        except ValueError:
            pass

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{OWM_BASE_URL}/forecast", params=params)
        resp.raise_for_status()
        data = resp.json()

    unit_label = "°C" if units == "metric" else "°F"
    periods: list[dict] = []
    rain_seen = False
    for item in data.get("list", []):
        dt_txt = item.get("dt_txt", "")
        temp = item["main"]["temp"]
        desc = item["weather"][0]["description"]
        wind = item["wind"]["speed"]
        rain = _rain_warning(item.get("weather", []))
        if rain:
            rain_seen = True
        periods.append({
            "time": dt_txt,
            "temperature": f"{temp:.0f}{unit_label}",
            "description": desc,
            "wind_speed": f"{wind:.1f}",
            "rain_warning": rain,
        })

    city = data.get("city", {}).get("name", location)
    spoken = f"Forecast for {city} over the next {hours} hours: "
    if periods:
        first, last = periods[0], periods[-1]
        spoken += (
            f"Starting at {first['temperature']} with {first['description']}, "
            f"moving to {last['temperature']} with {last['description']}."
        )
    if rain_seen:
        spoken += " Rain is expected in some periods — plan accordingly."

    return {
        "spoken_summary": spoken,
        "city": city,
        "periods": periods,
    }
