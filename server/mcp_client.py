"""
EcoSight — MCP Client Bridge
Connects the main WebSocket server to the MCP server tools
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory and mcp_server to path
parent_dir = Path(__file__).parent.parent
mcp_path = parent_dir / 'mcp_server'
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(mcp_path))

# Now import from mcp_server
from tools.navigation import navigate_to_destination
from tools.weather import get_current_weather, get_weather_forecast
from tools.news import get_top_headlines, search_news
from tools.accessibility import (
    get_current_time_and_date,
    get_emergency_info,
    get_safety_tips,
)


class MCPClient:
    """Client to call MCP tools from the main server"""
    
    def __init__(self):
        self.tools = {
            'time': self._get_time,
            'weather': self._get_weather,
            'forecast': self._get_forecast,
            'headlines': self._get_headlines,
            'search_news': self._search_news,
            'navigate': self._navigate,
            'emergency': self._get_emergency,
            'safety_tips': self._get_safety_tips,
        }
    
    async def call_tool(self, tool_name: str, params: dict) -> dict:
        """Call an MCP tool and return the result"""
        handler = self.tools.get(tool_name)
        if not handler:
            return {
                'error': f'Unknown tool: {tool_name}',
                'spoken_summary': f'Sorry, {tool_name} is not available.'
            }
        
        try:
            result = await handler(params)
            return result
        except Exception as e:
            print(f"[MCP] Error calling {tool_name}: {e}")
            return {
                'error': str(e),
                'spoken_summary': f'Sorry, there was an error: {str(e)}'
            }
    
    async def _get_time(self, params: dict) -> dict:
        """Get current time and date"""
        return await get_current_time_and_date()
    
    async def _get_weather(self, params: dict) -> dict:
        """Get current weather"""
        location = params.get('location', 'London')
        units = params.get('units', 'metric')
        return await get_current_weather(location=location, units=units)
    
    async def _get_forecast(self, params: dict) -> dict:
        """Get weather forecast"""
        location = params.get('location', 'London')
        hours = params.get('hours', 12)
        units = params.get('units', 'metric')
        return await get_weather_forecast(location=location, hours=hours, units=units)
    
    async def _get_headlines(self, params: dict) -> dict:
        """Get top news headlines"""
        country = params.get('country', 'us')
        category = params.get('category')
        count = params.get('count', 5)
        return await get_top_headlines(country=country, category=category, count=count)
    
    async def _search_news(self, params: dict) -> dict:
        """Search news articles"""
        query = params.get('query', '')
        count = params.get('count', 5)
        return await search_news(query=query, count=count)
    
    async def _navigate(self, params: dict) -> dict:
        """Get navigation directions"""
        origin = params.get('origin', '')
        destination = params.get('destination', '')
        profile = params.get('profile', 'foot-walking')
        
        if not origin or not destination:
            return {
                'error': 'Origin and destination are required',
                'spoken_summary': 'Please provide both origin and destination.'
            }
        
        result = await navigate_to_destination(
            origin=origin,
            destination=destination,
            profile=profile
        )

        # Build spoken summary from steps
        steps_text = ". ".join(
            f"Step {i+1}: {s['instruction']}, {s['distance']}"
            for i, s in enumerate(result.get('steps', [])[:5])  # first 5 steps for TTS
        )
        result['spoken_summary'] = f"{result.get('summary', '')}. {steps_text}"
        return result
    
    async def _get_emergency(self, params: dict) -> dict:
        """Get emergency information"""
        location = params.get('location', '')
        return await get_emergency_info(location=location)
    
    async def _get_safety_tips(self, params: dict) -> dict:
        """Get safety tips"""
        context = params.get('context', 'walking')
        return await get_safety_tips(context=context)


# Global instance
mcp_client = MCPClient()
