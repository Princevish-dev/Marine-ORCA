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
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';

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

const playEmergencyBeep = () => {
  try {
    const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
    const oscillator = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioCtx.destination);
    
    oscillator.type = 'square';
    oscillator.frequency.setValueAtTime(800, audioCtx.currentTime);
    
    gainNode.gain.setValueAtTime(1, audioCtx.currentTime);
    gainNode.gain.setValueAtTime(0, audioCtx.currentTime + 0.2);
    gainNode.gain.setValueAtTime(1, audioCtx.currentTime + 0.4);
    gainNode.gain.setValueAtTime(0, audioCtx.currentTime + 0.6);
    gainNode.gain.setValueAtTime(1, audioCtx.currentTime + 0.8);
    gainNode.gain.setValueAtTime(0, audioCtx.currentTime + 1.0);
    
    oscillator.start();
    oscillator.stop(audioCtx.currentTime + 1.2);
  } catch (e) {
    console.error("Audio beep failed", e);
  }
};

export default function DashboardPage() {
  const [Guardianstatus, Setguardianstatus] = useState<'ACTIVE' | 'DEGRADED' | 'OFFLINE'>('OFFLINE');
  const [Lastscan, Setlastscan] = useState<string>('');
  const [Demomode, Setdemomode] = useState(false);
  const SseRef = useRef<EventSource | null>(null);
  const Router = useRouter();
  const [Usr, Setusr] = useState<any>(null);

  const [Activealerts, Setactivealerts] = useState<AlertEvent[]>([]);
  const Dismissalert = (id: string) => Setactivealerts((prev) => prev.filter((a) => a.id !== id));

  const [Safety, Setsafety] = useState<SafetyAssessment | undefined>();
  const [Evidence, Setevidence] = useState<EvidenceItem[]>([]);
  const [Mapdata, Setmapdata] = useState<MapData | undefined>();
  const [Pfzcandidates, Setpfzcandidates] = useState<PFZCandidate[]>([]);
  const [Route, Setroute] = useState<RouteResult | undefined>();
  const [Righttab, Setrighttab] = useState<'safety' | 'pfz' | 'route' | 'evidence'>('safety');

  const [Userlat, Setuserlat] = useState<number>(13.0827);
  const [Userlon, Setuserlon] = useState<number>(80.2707);
  const [Emergencyquery, Setemergencyquery] = useState<{ ts: number, text: string } | undefined>();

  const [Mounted, Setmounted] = useState(false);
  useEffect(() => Setmounted(true), []);

  const Handleresponse = useCallback((resp: ChatResponse) => {
    if (resp.safety) Setsafety(resp.safety);
    if (resp.evidence.length) Setevidence(resp.evidence);
    if (resp.map_data) Setmapdata(resp.map_data);
    if (resp.pfz_candidates.length) {
      Setpfzcandidates(resp.pfz_candidates);
      Setrighttab('pfz');
    }
    if (resp.route) {
      Setroute(resp.route);
      Setrighttab('route');
    }
    if (resp.is_demo) Setdemomode(true);
  }, []);

  useEffect(() => {
    Setusr({ email: 'demo@orca.com', user_metadata: { full_name: 'Demo User' } });
  }, []);

  useEffect(() => {
    fetchHealth()
      .then((h) => {
        if (h.status === 'ok') {
          Setguardianstatus(h.guardian?.status === 'ACTIVE' ? 'ACTIVE' : 'DEGRADED');
          Setdemomode(h.demo_mode ?? false);
          if (h.guardian?.last_scan) {
            Setlastscan(new Date(h.guardian.last_scan).toLocaleTimeString());
          }
        } else {
          Setguardianstatus('DEGRADED');
        }
      })
      .catch(() => Setguardianstatus('OFFLINE'));
  }, []);

  useEffect(() => {
    const Es = createSSEConnection(
      (alert) => {
        Setactivealerts((prev) => {
          const Exists = prev.find((a) => a.id === alert.id);
          if (!Exists && alert.severity === 'RED') {
            playEmergencyBeep();
            if (navigator.geolocation) {
              navigator.geolocation.getCurrentPosition(
                (pos) => {
                  Setuserlat(pos.coords.latitude);
                  Setuserlon(pos.coords.longitude);
                  Setemergencyquery({
                    ts: Date.now(),
                    text: `CRITICAL DANGER: ${alert.title}! My current location is Lat: ${pos.coords.latitude.toFixed(4)}, Lon: ${pos.coords.longitude.toFixed(4)}. Find the nearest safe port and calculate an escape route immediately!`
                  });
                },
                (err) => {
                  console.error("Geolocation error:", err);
                  Setemergencyquery({
                    ts: Date.now(),
                    text: `CRITICAL DANGER: ${alert.title}! My location tracking failed. Use my last known coordinates and find the nearest safe port with an escape route immediately!`
                  });
                },
                { enableHighAccuracy: true }
              );
            }
          }
          if (Exists) return prev.map((a) => (a.id === alert.id ? alert : a));
          return [alert, ...prev].slice(0, 5);
        });
      },
      () => Setguardianstatus('ACTIVE'),
      () => Setguardianstatus('DEGRADED')
    );
    SseRef.current = Es;
    return () => { Es.close(); };
  }, []);

  const Geostatus = Mapdata ? undefined : undefined;

  const Boundaryfactor = Safety?.factors?.find((f) => f.name === 'Boundary');
  const Boundarystatus = Boundaryfactor
    ? (Boundaryfactor.status === 'CRITICAL' ? 'RED' :
       Boundaryfactor.status === 'WARNING' ? 'ORANGE' :
       Boundaryfactor.status === 'CAUTION' ? 'YELLOW' : 'NORMAL') as 'NORMAL' | 'YELLOW' | 'ORANGE' | 'RED'
    : 'NORMAL';

  const RIGHT_TABS = [
    { id: 'safety', label: '🛡 Safety' },
    { id: 'pfz', label: '🐟 PFZ' },
    { id: 'route', label: '🗺 Route' },
    { id: 'evidence', label: '📎 Evidence' },
  ] as const;

  if (!Mounted) return null;

  return (
    <div className="h-screen flex flex-col overflow-hidden" style={{ background: 'var(--navy-950)' }}>
      <Header
        Guardianstatus={Guardianstatus}
        Lastscan={Lastscan || undefined}
        Demomode={Demomode}
        Usr={Usr}
        Onlogout={async () => {
          await supabase.auth.signOut();
        }}
      />

      <div className="flex-1 flex gap-3 p-3 min-h-0 overflow-hidden">

        <div className="w-[400px] flex-shrink-0 glass-card flex flex-col min-h-0 overflow-hidden">
          <ChatPanel
            onResponse={Handleresponse}
            defaultLat={Userlat}
            defaultLon={Userlon}
            emergencyQuery={Emergencyquery}
          />
        </div>

        <div className="flex-1 glass-card flex flex-col min-h-0 overflow-hidden">
          <div className="px-4 py-2.5 border-b border-slate-800/50 flex items-center justify-between flex-shrink-0">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
              🗺 Marine Chart — Bay of Bengal
            </span>
            <div className="flex items-center gap-2">
              {Demomode && (
                <span className="text-[10px] text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded">
                  DEMO DATA
                </span>
              )}
              {Demomode && (
                <button
                  onClick={() => triggerTestAlert()}
                  className="text-[10px] text-slate-600 hover:text-amber-400 border border-slate-700/30 hover:border-amber-500/30 px-2 py-1 rounded transition-colors"
                  title="Trigger test Guardian alert (demo only)"
                >
                  ⚡ Test Alert
                </button>
              )}
            </div>
          </div>

          {Boundarystatus !== 'NORMAL' && (
            <div className="px-3 pt-2 flex-shrink-0">
              <GeofenceAlertCard
                status={Boundarystatus}
                distanceKm={parseFloat(Boundaryfactor?.value?.match(/[\d.]+/)?.[0] ?? '50')}
                zoneName="IMBL Demonstration Zone"
              />
            </div>
          )}

          <div className="flex-1 min-h-0">
            <MarineMap
              mapData={Mapdata}
              geofenceGeoJSON={Mapdata?.geofence_geojson}
            />
          </div>
        </div>

        <div className="w-80 flex-shrink-0 flex flex-col gap-2 min-h-0 overflow-hidden">
          <div className="glass-card p-1 flex gap-1 flex-shrink-0">
            {RIGHT_TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => Setrighttab(tab.id as any)}
                className={`flex-1 py-1.5 rounded-lg text-[11px] font-medium transition-all ${
                  Righttab === tab.id
                    ? 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/25'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto space-y-2">
            {Righttab === 'safety' && (
              <>
                <SafetyGauge safety={Safety} />
                {Activealerts.length > 0 && (
                  <div className="glass-card p-3">
                    <h3 className="text-xs font-semibold tracking-widest text-slate-400 uppercase mb-2">
                      Active Alerts ({Activealerts.length})
                    </h3>
                    <div className="space-y-1.5">
                      {Activealerts.map((a) => (
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

            {Righttab === 'pfz' && <PFZPanel candidates={Pfzcandidates} />}

            {Righttab === 'route' && (
              Route ? <RouteComparison route={Route} /> : (
                <div className="glass-card p-4">
                  <h3 className="text-xs font-semibold tracking-widest text-slate-400 uppercase mb-2">Route Optimisation</h3>
                  <p className="text-xs text-slate-600">Ask ORCA &quot;Find a fishing zone and show me the route&quot; to see route comparison.</p>
                </div>
              )
            )}

            {Righttab === 'evidence' && <EvidencePanel evidence={Evidence} />}
          </div>

          <div className="glass-card p-3 flex-shrink-0">
            <div className="grid grid-cols-2 gap-y-1.5 gap-x-3">
              {[
                { name: 'Guardian', status: Guardianstatus === 'ACTIVE' ? 'ACTIVE' : Guardianstatus, active: Guardianstatus === 'ACTIVE' },
                { name: 'SSE', status: Guardianstatus !== 'OFFLINE' ? '✓' : '✗', active: Guardianstatus !== 'OFFLINE' },
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

      <AlertStack alerts={Activealerts} onDismiss={Dismissalert} />
    </div>
  );
}
