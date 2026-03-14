# BlindSight Navigation - User Input Guide

## How to Use Navigation Feature

### In the App:
1. Click **"AI Assistant"** button (🤖)
2. Select **"Navigation"** tab
3. Click **"Navigate"** (🧭)
4. Enter your destination in the input field
5. Click **"Submit"**

---

## Input Format Examples

### ✅ Simple Landmark Names
Just type the landmark name - the system will find it!

**Indian Examples:**
```
India Gate
Red Fort
Gateway of India
Charminar
Marina Beach
Taj Mahal
```

**International Examples:**
```
Eiffel Tower
Times Square
Big Ben
Central Park
```

### ✅ Landmark with City
Add city name for better accuracy:

```
India Gate, Delhi
Gateway of India, Mumbai
Charminar, Hyderabad
MG Road, Bangalore
Marina Beach, Chennai
Cubbon Park, Bangalore
```

### ✅ Full Address
Provide complete address:

```
Connaught Place, New Delhi, India
Marine Drive, Mumbai, Maharashtra
Brigade Road, Bangalore, Karnataka
```

### ✅ Street Names
Just the street name works too:

```
MG Road, Bangalore
Rajpath, Delhi
Park Street, Kolkata
```

### ✅ Popular Places
Restaurants, malls, stations:

```
Phoenix Mall, Mumbai
Bangalore City Railway Station
Kempegowda International Airport
```

---

## What You DON'T Need to Provide

❌ **Starting Point** - The system assumes you're starting from your current location
❌ **Coordinates** - Just use place names (though coordinates work too)
❌ **Exact spelling** - The system is smart enough to find close matches
❌ **Country name** - Usually not needed for well-known places

---

## Input Examples by Use Case

### 🏥 Going to Hospital
```
Apollo Hospital, Delhi
Fortis Hospital, Bangalore
Lilavati Hospital, Mumbai
```

### 🚉 Going to Railway Station
```
New Delhi Railway Station
Mumbai Central
Bangalore City Railway Station
Chennai Central
```

### 🏛️ Visiting Tourist Spots
```
Qutub Minar
Lotus Temple
Hawa Mahal, Jaipur
Victoria Memorial, Kolkata
```

### 🏪 Shopping Areas
```
Sarojini Nagar Market, Delhi
Commercial Street, Bangalore
Linking Road, Mumbai
T Nagar, Chennai
```

### 🍽️ Restaurants/Cafes
```
Indian Coffee House, Delhi
Koshy's, Bangalore
Leopold Cafe, Mumbai
```

### 🏫 Educational Institutions
```
IIT Delhi
IISc Bangalore
IIT Bombay
```

---

## Tips for Best Results

### ✅ DO:
- Use well-known landmark names
- Add city name if the place is common (e.g., "MG Road, Bangalore")
- Use English names
- Keep it simple and clear

### ❌ DON'T:
- Use very specific house numbers (unless it's a famous address)
- Use abbreviations that might be unclear
- Mix multiple languages
- Add unnecessary details

---

## Real User Examples

### Example 1: Tourist in Delhi
**Input:** `Red Fort`
**Result:** Navigation from current location to Red Fort with 50 turn-by-turn steps

### Example 2: Going to Work
**Input:** `Cyber City, Gurgaon`
**Result:** Complete walking directions with distance and time

### Example 3: Meeting Someone
**Input:** `Cafe Coffee Day, Indiranagar, Bangalore`
**Result:** Step-by-step navigation to the cafe

### Example 4: Emergency
**Input:** `Max Hospital, Saket`
**Result:** Fastest walking route with estimated time

---

## What the System Provides

After you submit your destination, you'll get:

✅ **Total Distance** - e.g., "7.3 kilometres"
✅ **Estimated Time** - e.g., "1 hour 27 minutes"
✅ **Turn-by-Turn Steps** - e.g., "Turn left onto MG Road"
✅ **Voice Guidance** - Spoken instructions via text-to-speech
✅ **Visual Display** - On-screen notification with all details

---

## Sample Complete Flow

### User Journey:
1. **User opens app** → Connects to server
2. **Clicks AI Assistant** → Opens feature menu
3. **Selects Navigate** → Input dialog appears
4. **Types:** `India Gate, Delhi`
5. **Clicks Submit** → Processing starts
6. **Receives:**
   - Voice: "Walk from your location to India Gate, Delhi. Total distance: 7.3 kilometres. Estimated time: 1 hour 27 minutes."
   - Screen: Shows 50 navigation steps
   - First step: "Head southwest, 275 metres, 3 minutes"

---

## Advanced: Coordinates (Optional)

If you know exact coordinates, you can use them:

**Format:** `latitude,longitude`

**Example:**
```
28.6129,77.2295
```

But this is **NOT recommended** for regular users - place names are much easier!

---

## Troubleshooting

### "Could not find location"
**Solution:** Try adding city name
- Instead of: `MG Road`
- Try: `MG Road, Bangalore`

### "Navigation failed"
**Solution:** Check internet connection and try again

### "Too many results"
**Solution:** Be more specific
- Instead of: `Park`
- Try: `Cubbon Park, Bangalore`

---

## Quick Reference Card

| What You Want | What To Type |
|---------------|--------------|
| Famous landmark | `Taj Mahal` |
| Local landmark | `India Gate, Delhi` |
| Street | `MG Road, Bangalore` |
| Hospital | `Apollo Hospital, Delhi` |
| Station | `New Delhi Railway Station` |
| Mall | `Phoenix Mall, Mumbai` |
| Restaurant | `Koshy's, Bangalore` |

---

## Summary

**The simplest input is the best!**

Just type the name of where you want to go, and BlindSight will:
1. Find the location
2. Calculate the route
3. Give you turn-by-turn directions
4. Speak the instructions aloud

**Example:** Just type `Red Fort` and you're good to go! 🎯
