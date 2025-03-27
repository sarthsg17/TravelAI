import { useState, useEffect } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || '';

export default function MapComponent({ route }: { route: any }) {
  const [map, setMap] = useState<mapboxgl.Map | null>(null);
  const mapContainer = useState<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!mapContainer.current || map) return;

    const newMap = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/streets-v11',
      center: [77.1025, 32.2432], // Manali coordinates
      zoom: 12
    });

    if (route) {
      newMap.on('load', () => {
        newMap.addLayer({
          id: 'route',
          type: 'line',
          source: {
            type: 'geojson',
            data: {
              type: 'Feature',
              properties: {},
              geometry: {
                type: 'LineString',
                coordinates: route.geometry.coordinates
              }
            }
          },
          layout: {
            'line-join': 'round',
            'line-cap': 'round'
          },
          paint: {
            'line-color': '#3b82f6',
            'line-width': 4
          }
        });
      });
    }

    setMap(newMap);

    return () => newMap