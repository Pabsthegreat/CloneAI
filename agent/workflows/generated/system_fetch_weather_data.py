from agent.workflows import register_workflow
from agent.workflows.registry import ParameterSpec, WorkflowContext
from typing import Dict, Any
import requests

@register_workflow(
    namespace="system",
    name="fetch_weather_data",
    summary="Auto-generated workflow for `system:fetch_weather_data`",
    description="Implements the CLI command `system:fetch_weather_data`. Retrieves current weather data for a given city using a weather API.",
    parameters=(
        ParameterSpec(name="city", description="Name of the city to fetch weather for.", type=str, required=True),
    ),
    metadata={
        "category": "GENERAL COMMANDS",
        "usage": "system:fetch_weather_data city:CITY_NAME",
        "examples": ["Example: system:fetch_weather_data city:Bangalore"],
    }
)
def system_fetch_weather_data_handler(ctx: WorkflowContext, params: Dict[str, Any]) -> str:
    city = params.get("city")
    if not city or not isinstance(city, str):
        return "Error: 'city' parameter must be provided as a string."

    # Open-Meteo API for current weather (no API key required)
    # Step 1: Geocode city to get latitude and longitude
    geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
    try:
        geo_resp = requests.get(geocode_url, params={"name": city, "count": 1, "language": "en", "format": "json"}, timeout=10)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        if not geo_data.get("results"):
            return f"Error: City '{city}' not found. Please check the city name and try again."
        location = geo_data["results"][0]
        lat = location["latitude"]
        lon = location["longitude"]
        resolved_city = location.get("name", city)
        country = location.get("country", "")
    except Exception as e:
        return f"Error: Failed to geocode city '{city}'. Details: {str(e)}"

    # Step 2: Fetch current weather
    weather_url = "https://api.open-meteo.com/v1/forecast"
    try:
        weather_resp = requests.get(
            weather_url,
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
                "timezone": "auto"
            },
            timeout=10
        )
        weather_resp.raise_for_status()
        weather_data = weather_resp.json()
        current = weather_data.get("current_weather")
        if not current:
            return f"Error: Weather data not available for '{resolved_city}'."
        temp_c = current.get("temperature")
        wind_kph = current.get("windspeed")
        weather_code = current.get("weathercode")
        # Weather code mapping (Open-Meteo)
        weather_conditions = {
            0: "clear sky",
            1: "mainly clear",
            2: "partly cloudy",
            3: "overcast",
            45: "fog",
            48: "depositing rime fog",
            51: "light drizzle",
            53: "moderate drizzle",
            55: "dense drizzle",
            56: "light freezing drizzle",
            57: "dense freezing drizzle",
            61: "slight rain",
            63: "moderate rain",
            65: "heavy rain",
            66: "light freezing rain",
            67: "heavy freezing rain",
            71: "slight snow fall",
            73: "moderate snow fall",
            75: "heavy snow fall",
            77: "snow grains",
            80: "slight rain showers",
            81: "moderate rain showers",
            82: "violent rain showers",
            85: "slight snow showers",
            86: "heavy snow showers",
            95: "thunderstorm",
            96: "thunderstorm with slight hail",
            99: "thunderstorm with heavy hail"
        }
        condition = weather_conditions.get(weather_code, "unknown conditions")
        # Compose output
        city_display = f"{resolved_city}, {country}" if country else resolved_city
        return f"It is currently {temp_c}°C with {condition} in {city_display}. Wind speed is {wind_kph} km/h."
    except Exception as e:
        return f"Error: Failed to fetch weather data for '{resolved_city}'. Details: {str(e)}"
