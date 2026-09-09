'use client';

import { useEffect, useRef, useState } from 'react';
import type { MapData, GeoJSONFeatureCollection } from '@/types';
import { Layers, MapPin, Fish, Route as RouteIcon, Shield } from 'lucide-react';

interface Marinemapprops {
  mapData?: MapData;
  geofenceGeoJSON?: GeoJSONFeatureCollection;
}

const LAYER_DEFS = [
  { id: 'pfz', label: 'PFZ Zones', icon: '🐟' },
  { id: 'route', label: 'Routes', icon: '🗺' },
  { id: 'geofence', label: 'Geofence', icon: '🚧' },
  { id: 'waves', label: 'Wave Indicators', icon: '🌊' },
];

export default function MarineMap({ mapData, geofenceGeoJSON }: Marinemapprops) {
  const MapRef = useRef<HTMLDivElement>(null);
  const LeafletmapRef = useRef<any>(null);
  const LayersRef = useRef<Record<string, any>>({});
  const [Activelayers, Setactivelayers] = useState<Set<string>>(new Set(['geofence']));
  const [Mapready, Setmapready] = useState(false);
  const [Clickinfo, Setclickinfo] = useState<{ lat: number; lng: number } | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined' || LeafletmapRef.current) return;

    import('leaflet').then((L) => {
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
      });

      const Map = L.map(MapRef.current!, {
        center: [13.0827, 80.2707],
        zoom: 7,
        zoomControl: true,
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 18,
      }).addTo(Map);

      const Gridlines: any[] = [];
      for (let Lat = 8; Lat <= 22; Lat += 2) {
        Gridlines.push(
          L.polyline([[Lat, 70], [Lat, 90]], {
            color: 'rgba(6,182,212,0.08)', weight: 1, dashArray: '4,8',
          }).addTo(Map)
        );
      }
      for (let Lon = 70; Lon <= 90; Lon += 2) {
        Gridlines.push(
          L.polyline([[8, Lon], [22, Lon]], {
            color: 'rgba(6,182,212,0.08)', weight: 1, dashArray: '4,8',
          }).addTo(Map)
        );
      }

      Map.on('click', (e: any) => {
        Setclickinfo({ lat: +e.latlng.lat.toFixed(4), lng: +e.latlng.lng.toFixed(4) });
      });

      LeafletmapRef.current = Map;
      (window as any).__leafletMap = Map;
      (window as any).__L = L;
      Setmapready(true);
    });

    return () => {
      if (LeafletmapRef.current) {
        LeafletmapRef.current.remove();
        LeafletmapRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!Mapready || !mapData) return;
    const Map = LeafletmapRef.current;
    const L = (window as any).__L;
    if (!Map || !L) return;

    if (mapData.user_location) {
      if (LayersRef.current['user']) {
        Map.removeLayer(LayersRef.current['user']);
      }
      const Usericon = L.divIcon({
        className: '',
        html: `<div style="width:16px;height:16px;border-radius:50%;background:#06b6d4;border:3px solid white;box-shadow:0 0 12px #06b6d488;"></div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      });
      LayersRef.current['user'] = L.marker(
        [mapData.user_location.lat, mapData.user_location.lng],
        { icon: Usericon }
      )
        .bindPopup('<b style="color:#06b6d4">📍 Your Location</b>')
        .addTo(Map);
      Map.setView([mapData.user_location.lat, mapData.user_location.lng], 8);
    }

    if (mapData.pfz_candidates?.length && Activelayers.has('pfz')) {
      if (LayersRef.current['pfz']) {
        Map.removeLayer(LayersRef.current['pfz']);
      }
      const Group = L.layerGroup();
      mapData.pfz_candidates.forEach((Pfz: any) => {
        const C = Pfz.suitability === 'HIGH' ? '#22c55e' : Pfz.suitability === 'MODERATE' ? '#eab308' : '#ef4444';
        const Icon = L.divIcon({
          className: '',
          html: `<div style="width:22px;height:22px;border-radius:50%;background:${C};opacity:0.85;border:2px solid white;box-shadow:0 0 8px ${C}88;display:flex;align-items:center;justify-content:center;font-size:11px;">🐟</div>`,
          iconSize: [22, 22],
          iconAnchor: [11, 11],
        });
        L.marker([Pfz.lat, Pfz.lng], { icon: Icon })
          .bindPopup(
            `<div style="color:#e2e8f0;font-family:Inter,sans-serif;min-width:160px">
              <b style="color:${C}">PFZ Candidate</b><br/>
              Score: <b>${Pfz.score}/100</b><br/>
              Suitability: ${Pfz.suitability}
            </div>`
          )
          .addTo(Group);
      });
      LayersRef.current['pfz'] = Group.addTo(Map);
    } else if (!Activelayers.has('pfz') && LayersRef.current['pfz']) {
      Map.removeLayer(LayersRef.current['pfz']);
    }

    if (mapData.route_geojson && Activelayers.has('route')) {
      if (LayersRef.current['route']) Map.removeLayer(LayersRef.current['route']);
      const Group = L.layerGroup();
      const Direct = mapData.route_geojson.direct.map((p: any) => [p.lat, p.lng]);
      const Orca = mapData.route_geojson.orca.map((p: any) => [p.lat, p.lng]);
      if (Direct.length > 0)
        L.polyline(Direct, { color: '#94a3b8', weight: 2, dashArray: '6,8', opacity: 0.7 })
          .bindTooltip('Direct Route', { permanent: false })
          .addTo(Group);
      if (Orca.length > 0)
        L.polyline(Orca, { color: '#06b6d4', weight: 3, opacity: 0.9 })
          .bindTooltip('ORCA Optimized Route', { permanent: false })
          .addTo(Group);
      LayersRef.current['route'] = Group.addTo(Map);
    } else if (!Activelayers.has('route') && LayersRef.current['route']) {
      Map.removeLayer(LayersRef.current['route']);
    }

    if (geofenceGeoJSON && Activelayers.has('geofence')) {
      if (LayersRef.current['geofence']) Map.removeLayer(LayersRef.current['geofence']);
      const Group = L.layerGroup();
      geofenceGeoJSON.features.forEach((F: any) => {
        if (F.geometry.type === 'Polygon') {
          const Coords = F.geometry.coordinates[0].map((c: number[]) => [c[1], c[0]]);
          L.polygon(Coords, {
            color: '#f97316',
            weight: 2,
            opacity: 0.8,
            fillColor: '#f97316',
            fillOpacity: 0.05,
            dashArray: '8,6',
          })
            .bindPopup(`<b style="color:#f97316">⚠ ${F.properties.name}</b><br/><span style="color:#94a3b8;font-size:11px">${F.properties.description}</span>`)
            .addTo(Group);
        }
      });
      LayersRef.current['geofence'] = Group.addTo(Map);
    } else if (!Activelayers.has('geofence') && LayersRef.current['geofence']) {
      Map.removeLayer(LayersRef.current['geofence']);
    }
  }, [mapData, geofenceGeoJSON, Mapready, Activelayers]);

  const Togglelayer = (Id: string) => {
    Setactivelayers((prev) => {
      const Next = new Set(prev);
      Next.has(Id) ? Next.delete(Id) : Next.add(Id);
      return Next;
    });
  };

  return (
    <div className="relative w-full h-full flex flex-col">
      <div className="absolute top-3 right-3 z-[1000] flex flex-col gap-1.5">
        <div className="glass-card-dark rounded-xl p-2 border border-cyan-500/15 shadow-xl">
          <div className="flex items-center gap-1.5 mb-2 px-1">
            <Layers className="w-3 h-3 text-slate-500" />
            <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Layers</span>
          </div>
          {LAYER_DEFS.map((Lyr) => (
            <button
              key={Lyr.id}
              className={`layer-btn w-full text-left mb-1 ${Activelayers.has(Lyr.id) ? 'active' : ''}`}
              onClick={() => Togglelayer(Lyr.id)}
            >
              {Lyr.icon} {Lyr.label}
            </button>
          ))}
        </div>
      </div>

      <div ref={MapRef} className="flex-1 w-full rounded-b-xl" style={{ minHeight: 300 }} />

      {Clickinfo && (
        <div className="absolute bottom-3 left-3 z-[1000] glass-card-dark border border-cyan-500/20 p-3 rounded-xl max-w-xs animate-slide-up">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-cyan-400 font-semibold flex items-center gap-1">
              <MapPin className="w-3 h-3" /> Selected Point
            </span>
            <button
              onClick={() => Setclickinfo(null)}
              className="text-slate-500 hover:text-slate-300 text-xs"
            >✕</button>
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
            <span className="text-slate-500">Lat</span>
            <span className="text-slate-200 font-mono">{Clickinfo.lat}°</span>
            <span className="text-slate-500">Lon</span>
            <span className="text-slate-200 font-mono">{Clickinfo.lng}°</span>
            <span className="text-slate-500">Bay of Bengal</span>
            <span className="text-cyan-400">Indian Ocean</span>
          </div>
          <p className="text-[10px] text-slate-600 mt-2">Ask ORCA about this location</p>
        </div>
      )}

      {!Mapready && (
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
