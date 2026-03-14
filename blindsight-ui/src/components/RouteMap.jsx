import React, { useEffect, useRef } from 'react';
import './RouteMap.css';

// Leaflet is loaded via CDN in index.html to avoid CRA bundling issues
// We access it via window.L

export default function RouteMap({ origin, destination, steps, geometry }) {
  const mapRef    = useRef(null);
  const leafletRef = useRef(null);

  useEffect(() => {
    const L = window.L;
    if (!L || !origin || !destination) return;

    // Destroy previous map instance if re-rendering
    if (leafletRef.current) {
      leafletRef.current.remove();
      leafletRef.current = null;
    }

    const map = L.map(mapRef.current, { zoomControl: true, attributionControl: false });
    leafletRef.current = map;

    // Dark-style OSM tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
    }).addTo(map);

    // Markers
    const originIcon = L.divIcon({
      className: '',
      html: '<div class="map-marker origin">📍</div>',
      iconSize: [28, 28], iconAnchor: [14, 28],
    });
    const destIcon = L.divIcon({
      className: '',
      html: '<div class="map-marker dest">🏁</div>',
      iconSize: [28, 28], iconAnchor: [14, 28],
    });

    const orgLatLng  = [origin.lat,      origin.lng];
    const dstLatLng  = [destination.lat, destination.lng];

    L.marker(orgLatLng, { icon: originIcon }).addTo(map)
      .bindPopup(`<b>Start</b><br>${origin.label}`);
    L.marker(dstLatLng, { icon: destIcon }).addTo(map)
      .bindPopup(`<b>Destination</b><br>${destination.label}`);

    // Draw route — use actual geometry if available, else straight line
    const routePoints = (geometry && geometry.length > 1) ? geometry : [orgLatLng, dstLatLng];
    L.polyline(routePoints, {
      color: '#00e5cc',
      weight: 4,
      opacity: 0.85,
      dashArray: null,
    }).addTo(map);

    // Fit map to show both markers
    map.fitBounds([orgLatLng, dstLatLng], { padding: [32, 32] });

    return () => {
      if (leafletRef.current) {
        leafletRef.current.remove();
        leafletRef.current = null;
      }
    };
  }, [origin, destination]);

  return <div ref={mapRef} className="route-map" />;
}
