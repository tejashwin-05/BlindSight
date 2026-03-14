"""
Detailed Navigation Feature Test with Full Output
Shows all navigation data including distance, duration, and step-by-step instructions
"""
import asyncio
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.tools.navigation import navigate_to_destination


async def test_navigation_detailed():
    print("=" * 80)
    print("BLINDSIGHT NAVIGATION - DETAILED TEST")
    print("=" * 80)
    
    # Test: Times Square to Central Park
    print("\n📍 NAVIGATION REQUEST")
    print("-" * 80)
    print("From: Times Square, New York")
    print("To: Central Park, New York")
    print("Mode: Walking")
    print("\n⏳ Calculating route...\n")
    
    try:
        result = await navigate_to_destination(
            origin="Times Square, New York",
            destination="Central Park, New York",
            profile="foot-walking"
        )
        
        print("✅ ROUTE CALCULATED SUCCESSFULLY!\n")
        print("=" * 80)
        
        # Summary
        print("📊 ROUTE SUMMARY")
        print("-" * 80)
        print(f"{result.get('summary', 'N/A')}\n")
        
        # Details
        print("📏 ROUTE DETAILS")
        print("-" * 80)
        print(f"Total Distance: {result.get('total_distance', 'N/A')}")
        print(f"Total Duration: {result.get('total_duration', 'N/A')}")
        print(f"Total Steps: {len(result.get('steps', []))}")
        
        # Origin and Destination
        origin = result.get('origin', {})
        destination = result.get('destination', {})
        print(f"\nOrigin: {origin.get('label', 'N/A')}")
        print(f"  Coordinates: {origin.get('lat', 'N/A')}, {origin.get('lng', 'N/A')}")
        print(f"\nDestination: {destination.get('label', 'N/A')}")
        print(f"  Coordinates: {destination.get('lat', 'N/A')}, {destination.get('lng', 'N/A')}")
        
        # Turn-by-turn instructions
        steps = result.get('steps', [])
        if steps:
            print(f"\n🧭 TURN-BY-TURN NAVIGATION ({len(steps)} steps)")
            print("=" * 80)
            
            # Show first 10 steps
            print("\n📍 FIRST 10 STEPS:")
            print("-" * 80)
            for i, step in enumerate(steps[:10], 1):
                print(f"\n{i}. {step.get('instruction', 'N/A')}")
                print(f"   Distance: {step.get('distance', 'N/A')}")
                print(f"   Duration: {step.get('duration', 'N/A')}")
                if step.get('name'):
                    print(f"   Street: {step.get('name')}")
            
            # Show middle section summary
            if len(steps) > 20:
                print(f"\n... ({len(steps) - 20} more steps) ...")
            
            # Show last 5 steps
            if len(steps) > 10:
                print("\n📍 LAST 5 STEPS:")
                print("-" * 80)
                for i, step in enumerate(steps[-5:], len(steps) - 4):
                    print(f"\n{i}. {step.get('instruction', 'N/A')}")
                    print(f"   Distance: {step.get('distance', 'N/A')}")
                    print(f"   Duration: {step.get('duration', 'N/A')}")
                    if step.get('name'):
                        print(f"   Street: {step.get('name')}")
        
        # Bounding box
        bbox = result.get('bbox')
        if bbox:
            print(f"\n🗺️ MAP BOUNDING BOX")
            print("-" * 80)
            print(f"West: {bbox[0]}, South: {bbox[1]}")
            print(f"East: {bbox[2]}, North: {bbox[3]}")
        
        print("\n" + "=" * 80)
        print("✅ NAVIGATION TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        
        # Save full result to JSON file
        with open('navigation_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        print("\n💾 Full result saved to: navigation_result.json")
        
    except Exception as e:
        print(f"\n❌ NAVIGATION FAILED!")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_navigation_detailed())
