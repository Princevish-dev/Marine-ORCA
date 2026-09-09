'use client';

import type { PFZCandidate } from '@/types';

interface PFZPanelProps {
  candidates: PFZCandidate[];
}

export default function PFZPanel({ candidates }: PFZPanelProps) {
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
        {candidates.map((pfz, i) => {
          const c = pfz.suitability === 'HIGH' ? '#22c55e' : pfz.suitability === 'MODERATE' ? '#eab308' : '#ef4444';
          const width = `${pfz.score}%`;
          return (
            <div
              key={pfz.id}
              className="p-3 rounded-lg border transition-all hover:border-cyan-500/20"
              style={{ borderColor: `${c}20`, background: `${c}06` }}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-slate-200">Zone {i + 1}</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full border"
                  style={{ color: c, borderColor: `${c}40`, background: `${c}10` }}>
                  {pfz.suitability}
                </span>
              </div>
              {/* Score bar */}
              <div className="mb-2">
                <div className="flex justify-between text-[10px] text-slate-500 mb-1">
                  <span>Suitability Score</span>
                  <span style={{ color: c }}>{pfz.score}/100</span>
                </div>
                <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-700" style={{ width, background: c }} />
                </div>
              </div>
              {/* Metadata */}
              <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[10px]">
                <span className="text-slate-500">Distance</span>
                <span className="text-slate-300">{pfz.distance_km} km</span>
                {pfz.sst_celsius !== undefined && (
                  <>
                    <span className="text-slate-500">SST</span>
                    <span className="text-slate-300">{pfz.sst_celsius}°C</span>
                  </>
                )}
                {pfz.chlorophyll_level && (
                  <>
                    <span className="text-slate-500">Chlorophyll</span>
                    <span className="text-slate-300">{pfz.chlorophyll_level}</span>
                  </>
                )}
                <span className="text-slate-500">Coords</span>
                <span className="text-slate-300 font-mono">{pfz.latitude.toFixed(2)}, {pfz.longitude.toFixed(2)}</span>
              </div>
              <p className="text-[10px] text-slate-500 mt-2 leading-relaxed">{pfz.explanation}</p>
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
