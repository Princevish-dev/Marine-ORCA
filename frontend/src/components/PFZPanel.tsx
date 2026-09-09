'use client';

import type { PFZCandidate } from '@/types';

interface Pfzpanelprops {
  candidates: PFZCandidate[];
}

export default function PFZPanel({ candidates }: Pfzpanelprops) {
  if (!candidates || candidates.length === 0) {
    return (
      <div className="glass-card p-4">
        <h3 className="text-xs font-semibold tracking-widest text-slate-400 uppercase mb-2">
          Potential Fishing Zones
        </h3>
        <p className="text-xs text-slate-600">Ask ORCA to &quot;find a fishing zone&quot; to see PFZ analysis.</p>
      </div>
    );
  }

  return (
    <div className="glass-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold tracking-widest text-slate-400 uppercase">
          Potential Fishing Zones
        </h3>
        <span className="text-[10px] text-slate-500">EO-derived</span>
      </div>

      <div className="space-y-2">
        {candidates.map((Pfz, I) => {
          const C = Pfz.suitability === 'HIGH' ? '#22c55e' : Pfz.suitability === 'MODERATE' ? '#eab308' : '#ef4444';
          const Width = `${Pfz.score}%`;
          return (
            <div
              key={Pfz.id}
              className="p-3 rounded-lg border transition-all hover:border-cyan-500/20"
              style={{ borderColor: `${C}20`, background: `${C}06` }}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-slate-200">Zone {I + 1}</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full border"
                  style={{ color: C, borderColor: `${C}40`, background: `${C}10` }}>
                  {Pfz.suitability}
                </span>
              </div>
              <div className="mb-2">
                <div className="flex justify-between text-[10px] text-slate-500 mb-1">
                  <span>Suitability Score</span>
                  <span style={{ color: C }}>{Pfz.score}/100</span>
                </div>
                <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-700" style={{ width: Width, background: C }} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[10px]">
                <span className="text-slate-500">Distance</span>
                <span className="text-slate-300">{Pfz.distance_km} km</span>
                {Pfz.sst_celsius !== undefined && (
                  <>
                    <span className="text-slate-500">SST</span>
                    <span className="text-slate-300">{Pfz.sst_celsius}°C</span>
                  </>
                )}
                {Pfz.chlorophyll_level && (
                  <>
                    <span className="text-slate-500">Chlorophyll</span>
                    <span className="text-slate-300">{Pfz.chlorophyll_level}</span>
                  </>
                )}
                <span className="text-slate-500">Coords</span>
                <span className="text-slate-300 font-mono">{Pfz.latitude.toFixed(2)}, {Pfz.longitude.toFixed(2)}</span>
              </div>
              <p className="text-[10px] text-slate-500 mt-2 leading-relaxed">{Pfz.explanation}</p>
            </div>
          );
        })}
      </div>

      <p className="mt-3 text-[10px] text-slate-600 leading-relaxed">
        "Potentially suitable" — not a guarantee of fish presence. Based on EO-derived indicators.
      </p>
    </div>
  );
}
