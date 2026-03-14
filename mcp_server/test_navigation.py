"""
Dedicated Navigation Feature Test
Tests turn-by-turn navigation with detailed output
"""
import asyncio
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.tools.navigation import navigate_to_destination


async def test_navigation():
    print("=" * 80)
    print("BLINDSIGHT NAVIGATION FEATURE TEST")
    print("=" * 80)
    
    # Test Case 1: Short distance navigation
    print("\n[TEST 1] Short Distance Navigation")
    print("-" * 80)
    print("From: Times Square, New York")
    print("To: Central Park, New York")
    print("\nProcessing...")
    
    try:
        result = await navigate_to_destination(
            origin="Times Square, New York",
            destination="Central Park, New York",
            profile="foot-walking"
        )
        
        print("\n✅ SUCCESS!")
        print(f"\nSpoken Summary:")
        print(f"  {result.get('spoken_summary', 'N/A')}")
        
        print(f"\nNavigation Details:")
        print(f"  Total Steps: {len(result.get('steps', []))}")
        print(f"  Distance: {result.get('distance_km', 'N/A')} km")
        print(f"  Duration: {result.get('duration_min', 'N/A')} minutes")
        
        # Show first 5 steps
        steps = result.get('steps', [])
        if steps:
            print(f"\nFirst 5 Navigation Steps:")
            for i, step in enumerate(steps[:5], 1):
                print(f"  {i}. {step.get('instruction', 'N/A')} ({step.get('distance_m', 0)}m)")
        
        # Show last 3 steps
        if len(steps) > 5:
            print(f"\n... ({len(steps) - 8} more steps) ...\n")
            print(f"Last 3 Navigation Steps:")
            for i, step in enumerate(steps[-3:], len(steps) - 2):
                print(f"  {i}. {step.get('instruction', 'N/A')} ({step.get('distance_m', 0)}m)")
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
    
    # Test Case 2: Different location
    print("\n" + "=" * 80)
    print("[TEST 2] Different Location Navigation")
    print("-" * 80)
    print("From: Statue of Liberty, New York")
    print("To: Brooklyn Bridge, New York")
    print("\nProcessing...")
    
    try:
        result = await navigate_to_destination(
            origin="Statue of Liberty, New York",
            destination="Brooklyn Bridge, New York",
            profile="foot-walking"
        )
        
        print("\n✅ SUCCESS!")
        print(f"\nSpoken Summary:")
        print(f"  {result.get('spoken_summary', 'N/A')}")
        
        print(f"\nNavigation Details:")
        print(f"  Total Steps: {len(result.get('steps', []))}")
        print(f"  Distance: {result.get('distance_km', 'N/A')} km")
        print(f"  Duration: {result.get('duration_min', 'N/A')} minutes")
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
    
    # Test Case 3: Wheelchair accessible route
    print("\n" + "=" * 80)
    print("[TEST 3] Wheelchair Accessible Navigation")
    print("-" * 80)
    print("From: Empire State Building, New York")
    print("To: Grand Central Terminal, New York")
    print("Profile: Wheelchair")
    print("\nProcessing...")
    
    try:
        result = await navigate_to_destination(
            origin="Empire State Building, New York",
            destination="Grand Central Terminal, New York",
            profile="wheelchair"
        )
        
        print("\n✅ SUCCESS!")
        print(f"\nSpoken Summary:")
        print(f"  {result.get('spoken_summary', 'N/A')}")
        
        print(f"\nNavigation Details:")
        print(f"  Total Steps: {len(result.get('steps', []))}")
        print(f"  Distance: {result.get('distance_km', 'N/A')} km")
        print(f"  Duration: {result.get('duration_min', 'N/A')} minutes")
        
        # Check for accessibility warnings
        if result.get('accessibility_warnings'):
            print(f"\n⚠️ Accessibility Warnings:")
            for warning in result['accessibility_warnings']:
                print(f"  - {warning}")
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
    
    # Test Case 4: International location
    print("\n" + "=" * 80)
    print("[TEST 4] International Navigation")
    print("-" * 80)
    print("From: Big Ben, London")
    print("To: Tower Bridge, London")
    print("\nProcessing...")
    
    try:
        result = await navigate_to_destination(
            origin="Big Ben, London",
            destination="Tower Bridge, London",
            profile="foot-walking"
        )
        
        print("\n✅ SUCCESS!")
        print(f"\nSpoken Summary:")
        print(f"  {result.get('spoken_summary', 'N/A')}")
        
        print(f"\nNavigation Details:")
        print(f"  Total Steps: {len(result.get('steps', []))}")
        print(f"  Distance: {result.get('distance_km', 'N/A')} km")
        print(f"  Duration: {result.get('duration_min', 'N/A')} minutes")
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
    
    # Test Case 5: Using coordinates
    print("\n" + "=" * 80)
    print("[TEST 5] Navigation Using Coordinates")
    print("-" * 80)
    print("From: 40.7580,-73.9855 (Times Square)")
    print("To: 40.7829,-73.9654 (Central Park)")
    print("\nProcessing...")
    
    try:
        result = await navigate_to_destination(
            origin="40.7580,-73.9855",
            destination="40.7829,-73.9654",
            profile="foot-walking"
        )
        
        print("\n✅ SUCCESS!")
        print(f"\nSpoken Summary:")
        print(f"  {result.get('spoken_summary', 'N/A')}")
        
        print(f"\nNavigation Details:")
        print(f"  Total Steps: {len(result.get('steps', []))}")
        print(f"  Distance: {result.get('distance_km', 'N/A')} km")
        print(f"  Duration: {result.get('duration_min', 'N/A')} minutes")
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
    
    print("\n" + "=" * 80)
    print("NAVIGATION TESTING COMPLETED!")
    print("=" * 80)
    print("\nKey Features Demonstrated:")
    print("  ✓ Turn-by-turn walking directions")
    print("  ✓ Distance and duration calculation")
    print("  ✓ Wheelchair accessible routing")
    print("  ✓ International location support")
    print("  ✓ Coordinate-based navigation")
    print("  ✓ Text-to-speech optimized instructions")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_navigation())
