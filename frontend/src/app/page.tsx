'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import dynamic from 'next/dynamic';
import Header from '@/components/Header';
import ChatPanel from '@/components/ChatPanel';
import SafetyGauge from '@/components/SafetyGauge';
import EvidencePanel from '@/components/EvidencePanel';
import PFZPanel from '@/components/PFZPanel';
import RouteComparison from '@/components/RouteComparison';
import { AlertStack, GeofenceAlertCard } from '@/components/AlertComponents';
import { createSSEConnection, triggerTestAlert, fetchHealth } from '@/lib/api';
import type { ChatResponse, AlertEvent, SafetyAssessment, EvidenceItem, MapData, PFZCandidate, RouteResult } from '@/types';

// Dynamic map import (Leaflet needs browser)
const MarineMap = dynamic(() => import('@/components/MarineMap'), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center bg-slate-900/50 rounded-xl">
      <div className="flex items-center gap-3">
        <div className="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-slate-400">Loading Marine Map...</span>
      </div>
    </div>
  ),
});

export default function DashboardPage() {
  // Guardian state
  const [guardianStatus, setGuardianStatus] = useState<'ACTIVE' | 'DEGRADED' | 'OFFLINE'>('OFFLINE');
  const [lastScan, setLastScan] = useState<string>('');
  const [demoMode, setDemoMode] = useState(false);
  const sseRef = useRef<EventSource | null>(null);

  // Alerts
  const [activeAlerts, setActiveAlerts] = useState<AlertEvent[]>([]);
  const dismissAlert = (id: string) => setActiveAlerts((prev) => prev.filter((a) => a.id !== id));

  // Last response state
  const [safety, setSafety] = useState<SafetyAssessment | undefined>();
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [mapData, setMapData] = useState<MapData | undefined>();
  const [pfzCandidates, setPfzCandidates] = useState<PFZCandidate[]>([]);
  const [route, setRoute] = useState<RouteResult | undefined>();

  // Active right panel tab
  const [rightTab, setRightTab] = useState<'safety' | 'pfz' | 'route' | 'evidence'>('safety');

  // Handle new chat response
  const handleResponse = useCallback((resp: ChatResponse) => {
    if (resp.safety) setSafety(resp.safety);
    if (resp.evidence.length) setEvidence(resp.evidence);
    if (resp.map_data) setMapData(resp.map_data);
    if (resp.pfz_candidates.length) {
      setPfzCandidates(resp.pfz_candidates);
      setRightTab('pfz');
    }
    if (resp.route) {
      setRoute(resp.route);
      setRightTab('route');
    }
    if (resp.is_demo) setDemoMode(true);
  }, []);

  // Health check
  useEffect(() => {
    fetchHealth()
      .then((h) => {
        if (h.status === 'ok') {
          setGuardianStatus(h.guardian?.status === 'ACTIVE' ? 'ACTIVE' : 'DEGRADED');
          setDemoMode(h.demo_mode ?? false);
          if (h.guardian?.last_scan) {
            setLastScan(new Date(h.guardian.last_scan).toLocaleTimeString());
          }
        } else {
          setGuardianStatus('DEGRADED');
        }
      })
      .catch(() => setGuardianStatus('OFFLINE'));
  }, []);

  // SSE connection
  useEffect(() => {
    const es = createSSEConnection(
      (alert) => {
        setActiveAlerts((prev) => {
          const exists = prev.find((a) => a.id === alert.id);
          if (exists) return prev.map((a) => (a.id === alert.id ? alert : a));
          return [alert, ...prev].slice(0, 5); // max 5 visible
        });
      },
      () => setGuardianStatus('ACTIVE'),
      () => setGuardianStatus('DEGRADED')
    );
    sseRef.current = es;
    return () => { es.close(); };
  }, []);

  // Geofence status from last map data
  const geoStatus = mapData ? undefined : undefined; // Will extract from safety factors

  // Boundary alert from safety factors
  const boundaryFactor = safety?.factors?.find((f) => f.name === 'Boundary');
  const boundaryStatus = boundaryFactor
    ? (boundaryFactor.status === 'CRITICAL' ? 'RED' :
       boundaryFactor.status === 'WARNING' ? 'ORANGE' :
       boundaryFactor.status === 'CAUTION' ? 'YELLOW' : 'NORMAL') as 'NORMAL' | 'YELLOW' | 'ORANGE' | 'RED'
    : 'NORMAL';

  const RIGHT_TABS = [
    { id: 'safety', label: '🛡 Safety' },
    { id: 'pfz', label: '🐟 PFZ' },
    { id: 'route', label: '🗺 Route' },
    { id: 'evidence', label: '📎 Evidence' },
  ] as const;

  return (
    <div className="h-screen flex flex-col overflow-hidden" style={{ background: 'var(--navy-950)' }}>
      {/* Header */}
      <Header
        guardianStatus={guardianStatus}
        lastScan={lastScan || undefined}
        demoMode={demoMode}
      />

      {/* Main content */}
      <div className="flex-1 flex gap-3 p-3 min-h-0 overflow-hidden">

        {/* ── LEFT: Chat panel ─────────────────────────────────────────────── */}
        <div className="w-[400px] flex-shrink-0 glass-card flex flex-col min-h-0 overflow-hidden">
          <ChatPanel
            onResponse={handleResponse}
            defaultLat={13.0827}
            defaultLon={80.2707}
          />
        </div>

        {/* ── CENTRE: Map ───────────────────────────────────────────────────── */}
        <div className="flex-1 glass-card flex flex-col min-h-0 overflow-hidden">
          {/* Map header */}
          <div className="px-4 py-2.5 border-b border-slate-800/50 flex items-center justify-between flex-shrink-0">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
              🗺 Marine Chart — Bay of Bengal
            </span>
            <div className="flex items-center gap-2">
              {demoMode && (
                <span className="text-[10px] text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded">
                  DEMO DATA
                </span>
              )}
              {/* Dev: trigger test alert */}
              <button
                onClick={() => triggerTestAlert()}
                className="text-[10px] text-slate-600 hover:text-amber-400 border border-slate-700/30 hover:border-amber-500/30 px-2 py-1 rounded transition-colors"
                title="Trigger test Guardian alert (DEV)"
              >
                ⚡ Test Alert
              </button>
            </div>
          </div>

          {/* Boundary alert (inside map area) */}
          {boundaryStatus !== 'NORMAL' && (
            <div className="px-3 pt-2 flex-shrink-0">
              <GeofenceAlertCard
                status={boundaryStatus}
                distanceKm={parseFloat(boundaryFactor?.value?.match(/[\d.]+/)?.[0] ?? '50')}
                zoneName="IMBL Demonstration Zone"
              />
            </div>
          )}

          <div className="flex-1 min-h-0">
            <MarineMap
              mapData={mapData}
              geofenceGeoJSON={mapData?.geofence_geojson}
            />
          </div>
        </div>

        {/* ── RIGHT: Data panels ────────────────────────────────────────────── */}
        <div className="w-80 flex-shrink-0 flex flex-col gap-2 min-h-0 overflow-hidden">
          {/* Tab selector */}
          <div className="glass-card p-1 flex gap-1 flex-shrink-0">
            {RIGHT_TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setRightTab(tab.id)}
                className={`flex-1 py-1.5 rounded-lg text-[11px] font-medium transition-all ${
                  rightTab === tab.id
                    ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/25'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Panel content */}
          <div className="flex-1 overflow-y-auto space-y-2">
            {rightTab === 'safety' && (
              <>
                <SafetyGauge safety={safety} />
                {activeAlerts.length > 0 && (
                  <div className="glass-card p-3">
                    <h3 className="text-xs font-semibold tracking-widest text-slate-400 uppercase mb-2">
                      Active Alerts ({activeAlerts.length})
                    </h3>
                    <div className="space-y-1.5">
                      {activeAlerts.map((a) => (
                        <div
                          key={a.id}
                          className="text-xs p-2 rounded-lg border"
                          style={{
                            borderColor: a.severity === 'RED' ? '#ef444440' : a.severity === 'ORANGE' ? '#f9731640' : '#eab30840',
                            background: a.severity === 'RED' ? '#ef444408' : '#f9731608',
                          }}
                        >
                          <p className="font-semibold text-slate-200">{a.title}</p>
                          <p className="text-[10px] text-slate-500 mt-0.5">{a.source}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {rightTab === 'pfz' && <PFZPanel candidates={pfzCandidates} />}

            {rightTab === 'route' && (
              route ? <RouteComparison route={route} /> : (
                <div className="glass-card p-4">
                  <h3 className="text-xs font-semibold tracking-widest text-slate-400 uppercase mb-2">Route Optimisation</h3>
                  <p className="text-xs text-slate-600">Ask ORCA &quot;Find a fishing zone and show me the route&quot; to see route comparison.</p>
                </div>
              )
            )}

            {rightTab === 'evidence' && <EvidencePanel evidence={evidence} />}
          </div>

          {/* Agent status footer */}
          <div className="glass-card p-3 flex-shrink-0">
            <div className="grid grid-cols-2 gap-y-1.5 gap-x-3">
              {[
                { name: 'Guardian', status: guardianStatus === 'ACTIVE' ? 'ACTIVE' : guardianStatus, active: guardianStatus === 'ACTIVE' },
                { name: 'SSE', status: guardianStatus !== 'OFFLINE' ? '✓' : '✗', active: guardianStatus !== 'OFFLINE' },
                { name: 'Safety Eng.', status: '✓', active: true },
                { name: 'Geo Engine', status: '✓', active: true },
              ].map((agent) => (
                <div key={agent.name} className="flex items-center justify-between">
                  <span className="text-[10px] text-slate-500">{agent.name}</span>
                  <span className={`text-[10px] font-semibold ${agent.active ? 'text-emerald-400' : 'text-red-400'}`}>
                    {agent.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Floating SSE alert toasts */}
      <AlertStack alerts={activeAlerts} onDismiss={dismissAlert} />
    </div>
  );
}
