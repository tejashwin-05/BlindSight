"""
Comprehensive test script for all 11 MCP server tools
"""
import asyncio
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

async def test_all_tools():
    print("=" * 70)
    print("TESTING ALL 11 ECOSIGHT MCP SERVER TOOLS")
    print("=" * 70)
    
    # Test 1: Time and Date
    print("\n[1/11] Testing get_current_time_and_date...")
    try:
        result = await get_current_time_and_date()
        print(f"✅ SUCCESS: {result['spoken_summary']}")
    except Exception as e:
        print(f"❌ FAILED: {e}")
    
    # Test 2: Safety Tips
    print("\n[2/11] Testing get_safety_tips...")
    try:
        result = await get_safety_tips(context="crossing")
        print(f"✅ SUCCESS: {len(result['tips'])} tips provided")
        print(f"   Sample: {result['tips'][0]}")
    except Exception as e:
        print(f"❌ FAILED: {e}")
    
    # Test 3: Emergency Info
    print("\n[3/11] Testing get_emergency_info...")
    try:
        result = await get_emergency_info(location="United States")
        print(f"✅ SUCCESS: {result['spoken_summary'][:80]}...")
    except Exception as e:
        print(f"❌ FAILED: {e}")
    
    # Test 4: Describe Surroundings
    print("\n[4/11] Testing describe_surroundings...")
    try:
        result = await describe_surroundings_prompt()
        print(f"✅ SUCCESS: {result['spoken_summary']}")
    except Exception as e:
        print(f"❌ FAILED: {e}")
    
    # Test 5: Current Weather
    print("\n[5/11] Testing get_current_weather...")
    try:
        result = await get_current_weather(location="New York", units="metric")
        print(f"✅ SUCCESS: {result['spoken_summary'][:80]}...")
    except Exception as e:
        print(f"❌ FAILED: {e}")
    
    # Test 6: Weather Forecast
    print("\n[6/11] Testing get_weather_forecast...")
    try:
        result = await get_weather_forecast(location="London", hours=12, units="metric")
        print(f"✅ SUCCESS: {result['spoken_summary'][:80]}...")
    except Exception as e:
        print(f"❌ FAILED: {e}")
    
    # Test 7: Top Headlines
    print("\n[7/11] Testing get_top_headlines...")
    try:
        result = await get_top_headlines(country="us", count=3)
        print(f"✅ SUCCESS: {len(result.get('articles', []))} headlines retrieved")
        if result.get('articles'):
            print(f"   Sample: {result['articles'][0]['title'][:60]}...")
    except Exception as e:
        print(f"❌ FAILED: {e}")
    
    # Test 8: Search News
    print("\n[8/11] Testing search_news...")
    try:
        result = await search_news(query="technology", count=3)
        print(f"✅ SUCCESS: {len(result.get('articles', []))} articles found")
        if result.get('articles'):
            print(f"   Sample: {result['articles'][0]['title'][:60]}...")
    except Exception as e:
        print(f"❌ FAILED: {e}")
    
    # Test 9: Find Nearby Places
    print("\n[9/11] Testing find_nearby_places...")
    try:
        result = await find_nearby_places(
            location="Times Square, New York",
            category="restaurant",
            radius_m=500,
            limit=3
        )
        print(f"✅ SUCCESS: {len(result.get('places', []))} places found")
        if result.get('places'):
            print(f"   Sample: {result['places'][0]['name']}")
    except Exception as e:
        print(f"❌ FAILED: {e}")
    
    # Test 10: Navigate to Destination
    print("\n[10/11] Testing navigate_to_destination...")
    try:
        result = await navigate_to_destination(
            origin="Times Square, New York",
            destination="Central Park, New York",
            profile="foot-walking"
        )
        print(f"✅ SUCCESS: {len(result.get('steps', []))} navigation steps")
        print(f"   Distance: {result.get('distance_km', 'N/A')} km")
    except Exception as e:
        print(f"❌ FAILED: {e}")
    
    # Test 11: Fetch Available Routes
    print("\n[11/11] Testing fetch_available_routes...")
    try:
        result = await fetch_available_routes(
            origin="Times Square, New York",
            destination="Central Park, New York",
            profile="foot-walking",
            alternatives=2
        )
        print(f"✅ SUCCESS: {len(result.get('routes', []))} routes found")
        if result.get('routes'):
            print(f"   Route 1: {result['routes'][0].get('distance_km', 'N/A')} km")
    except Exception as e:
        print(f"❌ FAILED: {e}")
    
    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_all_tools())
