# EcoSight: Send Google Maps Link with Coordinates

import webbrowser

latitude = 17.537459740503298
longitude = 78.3854384918926

maps_url = f"https://maps.google.com/?q={latitude},{longitude}"

print(f"Google Maps link: {maps_url}")

# Open the link in the default browser (uncomment to auto-open)
# webbrowser.open(maps_url)
