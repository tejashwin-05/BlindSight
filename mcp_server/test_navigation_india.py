"""
Navigation Test for Indian Locations
Tests if navigation works for major Indian cities and landmarks
"""
import asyncio
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_server.tools.navigation import navigate_to_destination


async def test_indian_navigation():
    print("=" * 80)
    print("BLINDSIGHT NAVIGATION - INDIAN LOCATIONS TEST")
    print("=" * 80)
    
    test_cases = [
        {
            "name": "Delhi - India Gate to Red Fort",
            "origin": "India Gate, New Delhi",
            "destination": "Red Fort, Delhi"
        },
        {
            "name": "Mumbai - Gateway of India to Marine Drive",
            "origin": "Gateway of India, Mumbai",
            "destination": "Marine Drive, Mumbai"
        },
        {
            "name": "Bangalore - MG Road to Cubbon Park",
            "origin": "MG Road, Bangalore",
            "destination": "Cubbon Park, Bangalore"
        },
        {
            "name": "Hyderabad - Charminar to Golconda Fort",
            "origin": "Charminar, Hyderabad",
            "destination": "Golconda Fort, Hyderabad"
        },
        {
            "name": "Chennai - Marina Beach to Kapaleeshwarar Temple",
            "origin": "Marina Beach, Chennai",
            "destination": "Kapaleeshwarar Temple, Chennai"
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n[TEST {i}/5] {test['name']}")
        print("-" * 80)
        print(f"From: {test['origin']}")
        print(f"To: {test['destination']}")
        print("\n⏳ Calculating route...")
        
        try:
            result = await navigate_to_destination(
                origin=test['origin'],
                destination=test['destination'],
                profile="foot-walking"
            )
            
            print("\n✅ SUCCESS!")
            print(f"\n📊 Route Summary:")
            print(f"  {result.get('summary', 'N/A')}")
            
            print(f"\n📏 Details:")
            print(f"  Distance: {result.get('total_distance', 'N/A')}")
            print(f"  Duration: {result.get('total_duration', 'N/A')}")
            print(f"  Steps: {len(result.get('steps', []))}")
            
            # Show first 3 steps
            steps = result.get('steps', [])
            if steps:
                print(f"\n🧭 First 3 Navigation Steps:")
                for j, step in enumerate(steps[:3], 1):
                    print(f"  {j}. {step.get('instruction', 'N/A')}")
                    print(f"     Distance: {step.get('distance', 'N/A')}, Duration: {step.get('duration', 'N/A')}")
            
            results.append({
                'test': test['name'],
                'status': 'SUCCESS',
                'distance': result.get('total_distance'),
                'duration': result.get('total_duration'),
                'steps': len(result.get('steps', []))
            })
            
        except Exception as e:
            print(f"\n❌ FAILED: {e}")
            results.append({
                'test': test['name'],
                'status': 'FAILED',
                'error': str(e)
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
    total_count = len(results)
    
    print(f"\nTotal Tests: {total_count}")
    print(f"Successful: {success_count}")
    print(f"Failed: {total_count - success_count}")
    print(f"Success Rate: {(success_count/total_count)*100:.1f}%")
    
    print("\n📊 Detailed Results:")
    print("-" * 80)
    for r in results:
        status_icon = "✅" if r['status'] == 'SUCCESS' else "❌"
        print(f"\n{status_icon} {r['test']}")
        if r['status'] == 'SUCCESS':
            print(f"   Distance: {r['distance']}")
            print(f"   Duration: {r['duration']}")
            print(f"   Steps: {r['steps']}")
        else:
            print(f"   Error: {r.get('error', 'Unknown')}")
    
    print("\n" + "=" * 80)
    print("CONCLUSION:")
    print("=" * 80)
    if success_count == total_count:
        print("✅ Navigation works perfectly for Indian locations!")
        print("   The system supports all major Indian cities and landmarks.")
    elif success_count > 0:
        print(f"⚠️ Navigation works for {success_count}/{total_count} Indian locations.")
        print("   Some locations may need more specific addresses.")
    else:
        print("❌ Navigation needs configuration for Indian locations.")
    
    print("\n" + "=" * 80)
    
    # Save results
    with open('navigation_india_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\n💾 Results saved to: navigation_india_results.json\n")


if __name__ == "__main__":
    asyncio.run(test_indian_navigation())
