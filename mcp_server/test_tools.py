"""
Quick test script for MCP server tools
"""
import asyncio
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.tools.accessibility import get_current_time_and_date, get_safety_tips
from mcp_server.tools.weather import get_current_weather

async def test_tools():
    print("=" * 60)
    print("Testing EcoSight MCP Server Tools")
    print("=" * 60)
    
    # Test 1: Time and Date
    print("\n1. Testing get_current_time_and_date...")
    try:
        result = await get_current_time_and_date()
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Safety Tips
    print("\n2. Testing get_safety_tips...")
    try:
        result = await get_safety_tips(context="walking")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Weather (requires API key)
    print("\n3. Testing get_current_weather...")
    try:
        result = await get_current_weather(location="London", units="metric")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_tools())
