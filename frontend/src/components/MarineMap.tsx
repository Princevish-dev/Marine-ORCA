'use client';

import { useEffect, useRef, useState } from 'react';
import type { MapData, GeoJSONFeatureCollection } from '@/types';
import { Layers, MapPin, Fish, Route as RouteIcon, Shield } from 'lucide-react';

interface MarineMapProps {
  mapData?: MapData;
  geofenceGeoJSON?: GeoJSONFeatureCollection;
}

const LAYER_DEFS = [
  { id: 'pfz', label: 'PFZ Zones', icon: '🐟' },
  { id: 'route', label: 'Routes', icon: '🗺' },
  { id: 'geofence', label: 'Geofence', icon: '🚧' },
  { id: 'waves', label: 'Wave Indicators', icon: '🌊' },
];

export default function MarineMap({ mapData, geofenceGeoJSON }: MarineMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMapRef = useRef<any>(null);
  const layersRef = useRef<Record<string, any>>({});
  const [activeLayers, setActiveLayers] = useState<Set<string>>(new Set(['geofence']));
  const [mapReady, setMapReady] = useState(false);
  const [clickInfo, setClickInfo] = useState<{ lat: number; lng: number } | null>(null);

  // ── Initialize Leaflet ────────────────────────────────────────────────────
  useEffect(() => {
    if (typeof window === 'undefined' || leafletMapRef.current) return;

    // Dynamically import Leaflet
    import('leaflet').then((L) => {
      // Fix default icons
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      });

      const map = L.map(mapRef.current!, {
        center: [13.0827, 80.2707],
        zoom: 7,
        zoomControl: true,
      });

      // Dark ocean-style tiles
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 18,
      }).addTo(map);

      // Grid lines layer (ocean grid)
      const gridLines: any[] = [];
      for (let lat = 8; lat <= 22; lat += 2) {
        gridLines.push(
          L.polyline([[lat, 70], [lat, 90]], {
            color: 'rgba(6,182,212,0.08)', weight: 1, dashArray: '4,8',
          }).addTo(map)
        );
      }
      for (let lon = 70; lon <= 90; lon += 2) {
        gridLines.push(
          L.polyline([[8, lon], [22, lon]], {
            color: 'rgba(6,182,212,0.08)', weight: 1, dashArray: '4,8',
          }).addTo(map)
        );
      }

      // Click handler
      map.on('click', (e: any) => {
        setClickInfo({ lat: +e.latlng.lat.toFixed(4), lng: +e.latlng.lng.toFixed(4) });
      });

      leafletMapRef.current = map;
      (window as any).__leafletMap = map;
      (window as any).__L = L;
      setMapReady(true);
    });

    return () => {
      if (leafletMapRef.current) {
        leafletMapRef.current.remove();
        leafletMapRef.current = null;
      }
    };
  }, []);

  // ── Sync map data ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapReady || !mapData) return;
    const map = leafletMapRef.current;
    const L = (window as any).__L;
    if (!map || !L) return;

    // User location marker
    if (mapData.user_location) {
      if (layersRef.current['user']) {
        map.removeLayer(layersRef.current['user']);
      }
      const userIcon = L.divIcon({
        className: '',
        html: `<div style="width:16px;height:16px;border-radius:50%;background:#06b6d4;border:3px solid white;box-shadow:0 0 12px #06b6d488;"></div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      });
      layersRef.current['user'] = L.marker(
        [mapData.user_location.lat, mapData.user_location.lng],
        { icon: userIcon }
      )
        .bindPopup('<b style="color:#06b6d4">📍 Your Location</b>')
        .addTo(map);
      map.setView([mapData.user_location.lat, mapData.user_location.lng], 8);
    }

    // PFZ markers
    if (mapData.pfz_candidates?.length && activeLayers.has('pfz')) {
      if (layersRef.current['pfz']) {
        map.removeLayer(layersRef.current['pfz']);
      }
      const group = L.layerGroup();
      mapData.pfz_candidates.forEach((pfz: any) => {
        const c = pfz.suitability === 'HIGH' ? '#22c55e' : pfz.suitability === 'MODERATE' ? '#eab308' : '#ef4444';
        const icon = L.divIcon({
          className: '',
          html: `<div style="width:22px;height:22px;border-radius:50%;background:${c};opacity:0.85;border:2px solid white;box-shadow:0 0 8px ${c}88;display:flex;align-items:center;justify-content:center;font-size:11px;">🐟</div>`,
          iconSize: [22, 22],
          iconAnchor: [11, 11],
        });
        L.marker([pfz.lat, pfz.lng], { icon })
          .bindPopup(
            `<div style="color:#e2e8f0;font-family:Inter,sans-serif;min-width:160px">
              <b style="color:${c}">PFZ Candidate</b><br/>
              Score: <b>${pfz.score}/100</b><br/>
              Suitability: ${pfz.suitability}
            </div>`
          )
          .addTo(group);
      });
      layersRef.current['pfz'] = group.addTo(map);
    } else if (!activeLayers.has('pfz') && layersRef.current['pfz']) {
      map.removeLayer(layersRef.current['pfz']);
    }

    // Routes
    if (mapData.route_geojson && activeLayers.has('route')) {
      if (layersRef.current['route']) map.removeLayer(layersRef.current['route']);
      const group = L.layerGroup();
      const direct = mapData.route_geojson.direct.map((p: any) => [p.lat, p.lng]);
      const orca = mapData.route_geojson.orca.map((p: any) => [p.lat, p.lng]);
      if (direct.length > 0)
        L.polyline(direct, { color: '#94a3b8', weight: 2, dashArray: '6,8', opacity: 0.7 })
          .bindTooltip('Direct Route', { permanent: false })
          .addTo(group);
      if (orca.length > 0)
        L.polyline(orca, { color: '#06b6d4', weight: 3, opacity: 0.9 })
          .bindTooltip('ORCA Optimized Route', { permanent: false })
          .addTo(group);
      layersRef.current['route'] = group.addTo(map);
    } else if (!activeLayers.has('route') && layersRef.current['route']) {
      map.removeLayer(layersRef.current['route']);
    }

    // Geofence
    if (geofenceGeoJSON && activeLayers.has('geofence')) {
      if (layersRef.current['geofence']) map.removeLayer(layersRef.current['geofence']);
      const group = L.layerGroup();
      geofenceGeoJSON.features.forEach((f: any) => {
        if (f.geometry.type === 'Polygon') {
          const coords = f.geometry.coordinates[0].map((c: number[]) => [c[1], c[0]]);
          L.polygon(coords, {
            color: '#f97316',
            weight: 2,
            opacity: 0.8,
            fillColor: '#f97316',
            fillOpacity: 0.05,
            dashArray: '8,6',
          })
            .bindPopup(`<b style="color:#f97316">⚠ ${f.properties.name}</b><br/><span style="color:#94a3b8;font-size:11px">${f.properties.description}</span>`)
            .addTo(group);
        }
      });
      layersRef.current['geofence'] = group.addTo(map);
    } else if (!activeLayers.has('geofence') && layersRef.current['geofence']) {
      map.removeLayer(layersRef.current['geofence']);
    }
  }, [mapData, geofenceGeoJSON, mapReady, activeLayers]);

  // Toggle layer
  const toggleLayer = (id: string) => {
    setActiveLayers((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  return (
    <div className="relative w-full h-full flex flex-col">
      {/* Layer control */}
      <div className="absolute top-3 right-3 z-[1000] flex flex-col gap-1.5">
        <div className="glass-card-dark rounded-xl p-2 border border-cyan-500/15 shadow-xl">
          <div className="flex items-center gap-1.5 mb-2 px-1">
            <Layers className="w-3 h-3 text-slate-500" />
            <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Layers</span>
          </div>
          {LAYER_DEFS.map((l) => (
            <button
              key={l.id}
              className={`layer-btn w-full text-left mb-1 ${activeLayers.has(l.id) ? 'active' : ''}`}
              onClick={() => toggleLayer(l.id)}
            >
              {l.icon} {l.label}
            </button>
          ))}
        </div>
      </div>

      {/* Map container */}
      <div ref={mapRef} className="flex-1 w-full rounded-b-xl" style={{ minHeight: 300 }} />

      {/* Click popup */}
      {clickInfo && (
        <div className="absolute bottom-3 left-3 z-[1000] glass-card-dark border border-cyan-500/20 p-3 rounded-xl max-w-xs animate-slide-up">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-cyan-400 font-semibold flex items-center gap-1">
              <MapPin className="w-3 h-3" /> Selected Point
            </span>
            <button
              onClick={() => setClickInfo(null)}
              className="text-slate-500 hover:text-slate-300 text-xs"
            >✕</button>
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
            <span className="text-slate-500">Lat</span>
            <span className="text-slate-200 font-mono">{clickInfo.lat}°</span>
            <span className="text-slate-500">Lon</span>
            <span className="text-slate-200 font-mono">{clickInfo.lng}°</span>
            <span className="text-slate-500">Bay of Bengal</span>
            <span className="text-cyan-400">Indian Ocean</span>
          </div>
          <p className="text-[10px] text-slate-600 mt-2">Ask ORCA about this location</p>
        </div>
      )}

      {!mapReady && (
        <div className="absolute inset-0 flex items-center justify-center bg-navy-900/80 rounded-b-xl z-10">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-slate-400">Loading Marine Map...</span>
          </div>
        </div>
      )}
    </div>
  );
}
