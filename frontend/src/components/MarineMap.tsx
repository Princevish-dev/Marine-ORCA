'use client';

import { useEffect, useState, useMemo, useCallback } from 'react';
import Map, { NavigationControl, ScaleControl, Popup } from 'react-map-gl/maplibre';
import type { StyleSpecification } from 'maplibre-gl';
import { DeckGL } from '@deck.gl/react';
import { ScatterplotLayer, PathLayer, PolygonLayer, IconLayer } from '@deck.gl/layers';
import type { MapData, GeoJSONFeatureCollection } from '@/types';
import { Layers, MapPin } from 'lucide-react';
import 'maplibre-gl/dist/maplibre-gl.css';

interface Marinemapprops {
  mapData?: MapData;
  geofenceGeoJSON?: GeoJSONFeatureCollection;
}

const LAYER_DEFS = [
  { id: 'pfz', label: 'PFZ Zones', icon: '🐟' },
  { id: 'route', label: 'Routes', icon: '🗺' },
  { id: 'geofence', label: 'Geofence', icon: '🚧' },
];

const INITIAL_VIEW = {
  longitude: 80.2707,
  latitude: 13.0827,
  zoom: 6.5,
  pitch: 0,
  bearing: 0,
};

const MAP_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© OpenStreetMap contributors',
    },
  },
  layers: [
    {
      id: 'osm-tiles',
      type: 'raster',
      source: 'osm',
    },
  ],
};

export default function MarineMap({ mapData, geofenceGeoJSON }: Marinemapprops) {
  const [Viewstate, Setviewstate] = useState(INITIAL_VIEW);
  const [Activelayers, Setactivelayers] = useState<Set<string>>(new Set(['geofence']));
  const [Clickinfo, Setclickinfo] = useState<{ lat: number; lng: number } | null>(null);

  useEffect(() => {
    if (mapData?.user_location) {
      Setviewstate((prev) => ({
        ...prev,
        latitude: mapData.user_location!.lat,
        longitude: mapData.user_location!.lng,
        zoom: 8,
      }));
    }
  }, [mapData?.user_location]);

  const Userlayer = useMemo(() => {
    if (!mapData?.user_location) return null;
    return new ScatterplotLayer({
      id: 'user-location',
      data: [{ position: [mapData.user_location.lng, mapData.user_location.lat] }],
      getPosition: (d: any) => d.position,
      getRadius: 800,
      getFillColor: [6, 182, 212, 200],
      getLineColor: [255, 255, 255, 255],
      getLineWidth: 3,
      lineWidthMinPixels: 2,
      radiusMinPixels: 8,
      radiusMaxPixels: 16,
      stroked: true,
    });
  }, [mapData?.user_location]);

  const Pfzlayer = useMemo(() => {
    if (!mapData?.pfz_candidates?.length || !Activelayers.has('pfz')) return null;
    return new ScatterplotLayer({
      id: 'pfz-markers',
      data: mapData.pfz_candidates.map((P: any) => ({
        position: [P.lng || P.longitude, P.lat || P.latitude],
        suitability: P.suitability,
        score: P.score,
      })),
      getPosition: (d: any) => d.position,
      getRadius: 1200,
      getFillColor: (d: any) => {
        if (d.suitability === 'HIGH') return [34, 197, 94, 200];
        if (d.suitability === 'MODERATE') return [234, 179, 8, 200];
        return [239, 68, 68, 200];
      },
      getLineColor: [255, 255, 255, 255],
      getLineWidth: 2,
      lineWidthMinPixels: 1,
      radiusMinPixels: 10,
      radiusMaxPixels: 20,
      stroked: true,
      pickable: true,
    });
  }, [mapData?.pfz_candidates, Activelayers]);

  const Routelayers = useMemo(() => {
    if (!mapData?.route_geojson || !Activelayers.has('route')) return [];
    const Layers: any[] = [];

    if (mapData.route_geojson.direct?.length > 0) {
      Layers.push(new PathLayer({
        id: 'direct-route',
        data: [{ path: mapData.route_geojson.direct.map((p: any) => [p.lng, p.lat]) }],
        getPath: (d: any) => d.path,
        getColor: [148, 163, 184, 180],
        getWidth: 3,
        widthMinPixels: 2,
        getDashArray: [6, 4],
        dashJustified: true,
        extensions: [],
      }));
    }

    if (mapData.route_geojson.orca?.length > 0) {
      Layers.push(new PathLayer({
        id: 'orca-route',
        data: [{ path: mapData.route_geojson.orca.map((p: any) => [p.lng, p.lat]) }],
        getPath: (d: any) => d.path,
        getColor: [6, 182, 212, 230],
        getWidth: 4,
        widthMinPixels: 3,
      }));
    }

    return Layers;
  }, [mapData?.route_geojson, Activelayers]);

  const Geofencelayer = useMemo(() => {
    if (!geofenceGeoJSON?.features?.length || !Activelayers.has('geofence')) return null;

    const Polygondata = geofenceGeoJSON.features
      .filter((f: any) => f.geometry.type === 'Polygon')
      .map((f: any) => ({
        polygon: f.geometry.coordinates[0].map((c: number[]) => [c[0], c[1]]),
        name: f.properties?.name || 'Restricted Zone',
      }));

    return new PolygonLayer({
      id: 'geofence-zones',
      data: Polygondata,
      getPolygon: (d: any) => d.polygon,
      getFillColor: [249, 115, 22, 12],
      getLineColor: [249, 115, 22, 200],
      getLineWidth: 2,
      lineWidthMinPixels: 2,
      filled: true,
      stroked: true,
      pickable: true,
    });
  }, [geofenceGeoJSON, Activelayers]);

  const Alllayers = useMemo(() => {
    const Result: any[] = [];
    if (Geofencelayer) Result.push(Geofencelayer);
    if (Pfzlayer) Result.push(Pfzlayer);
    Result.push(...Routelayers);
    if (Userlayer) Result.push(Userlayer);
    return Result;
  }, [Geofencelayer, Pfzlayer, Routelayers, Userlayer]);

  const Togglelayer = (Id: string) => {
    Setactivelayers((prev) => {
      const Next = new Set(prev);
      Next.has(Id) ? Next.delete(Id) : Next.add(Id);
      return Next;
    });
  };

  const Handleclick = useCallback((info: any) => {
    if (info.coordinate) {
      Setclickinfo({
        lat: +info.coordinate[1].toFixed(4),
        lng: +info.coordinate[0].toFixed(4),
      });
    }
  }, []);

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

      <div className="flex-1 w-full rounded-b-xl overflow-hidden" style={{ minHeight: 300 }}>
        <DeckGL
          viewState={Viewstate}
          onViewStateChange={({ viewState }: any) => Setviewstate(viewState)}
          controller={true}
          layers={Alllayers}
          onClick={Handleclick}
          getCursor={() => 'crosshair'}
        >
          <Map
            mapStyle={MAP_STYLE}
            attributionControl={false}
          >
            <NavigationControl position="bottom-right" />
            <ScaleControl position="bottom-left" />
          </Map>
        </DeckGL>
      </div>

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
    </div>
  );
}
