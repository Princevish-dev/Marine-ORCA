'use client';

import { useState } from 'react';
import type { FleetCongestionZone, CongestionClass, FleetRecommendation } from '@/types';

interface ZoneDensityPanelProps {
  zones: FleetCongestionZone[];
  pressure_warning: boolean;
}

const class_color: Record<CongestionClass, string> = {
  LOW: 'text-emerald-400',
  MODERATE: 'text-amber-400',
  HIGH: 'text-red-400',
};

const class_bg: Record<CongestionClass, string> = {
  LOW: 'bg-emerald-500/10 border-emerald-500/20',
  MODERATE: 'bg-amber-500/10 border-amber-500/20',
  HIGH: 'bg-red-500/10 border-red-500/20',
};

const rec_badge: Record<FleetRecommendation, { bg: string; text: string; label: string }> = {
  GO: { bg: 'bg-emerald-500/15 border-emerald-500/30', text: 'text-emerald-400', label: '✓ GO' },
  CAUTION: { bg: 'bg-amber-500/15 border-amber-500/30', text: 'text-amber-400', label: '⚠ CAUTION' },
  AVOID: { bg: 'bg-red-500/15 border-red-500/30', text: 'text-red-400', label: '✗ AVOID' },
};

const bar_color: Record<CongestionClass, string> = {
  LOW: 'bg-emerald-500',
  MODERATE: 'bg-amber-500',
  HIGH: 'bg-red-500',
};

export default function ZoneDensityPanel({ zones, pressure_warning }: ZoneDensityPanelProps) {
  const [selected_zone, set_selected_zone] = useState<string | null>(null);

  if (!zones.length) {
    return (
      <div className="glass-card p-4">
        <h3 className="text-xs font-semibold tracking-widest text-slate-400 uppercase mb-2">
          🚢 Fleet Congestion
        </h3>
        <p className="text-xs text-slate-600">No fleet data available. Ask ORCA about fishing zones to see congestion analysis.</p>
      </div>
    );
  }

  const selected = zones.find((z) => z.zone_id === selected_zone);

  return (
    <div className="glass-card p-3 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold tracking-widest text-slate-400 uppercase">
          🚢 Fleet Congestion
        </h3>
        {pressure_warning && (
          <span className="text-[10px] font-bold text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-full animate-pulse">
            HIGH PRESSURE
          </span>
        )}
      </div>

      <div className="space-y-1.5">
        {zones.map((zone) => {
          const rec = rec_badge[zone.recommendation || 'GO'];
          const fill_pct = Math.min(100, zone.vessel_count * 3);
          return (
            <button
              key={zone.zone_id}
              onClick={() => set_selected_zone(selected_zone === zone.zone_id ? null : zone.zone_id)}
              className={`w-full text-left p-2 rounded-lg border transition-all ${class_bg[zone.congestion_class]} ${
                selected_zone === zone.zone_id ? 'ring-1 ring-cyan-500/40' : ''
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className={`text-xs font-bold ${class_color[zone.congestion_class]}`}>
                  {zone.zone_id}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-slate-400">
                    FCR {zone.fcr_score}
                  </span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${rec.bg} ${rec.text}`}>
                    {rec.label}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 rounded-full bg-slate-800/50 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${bar_color[zone.congestion_class]}`}
                    style={{ width: `${fill_pct}%` }}
                  />
                </div>
                <span className="text-[10px] text-slate-400 w-8 text-right">
                  {zone.vessel_count}🚤
                </span>
              </div>
            </button>
          );
        })}
      </div>

      {selected && (
        <div className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-700/30 space-y-1.5">
          <p className="text-xs font-bold text-cyan-400">{selected.zone_id} — Details</p>
          <div className="grid grid-cols-2 gap-1">
            <div className="text-[10px] text-slate-500">Vessels</div>
            <div className="text-[10px] text-slate-300 text-right">{selected.vessel_count}</div>
            <div className="text-[10px] text-slate-500">FCR Score</div>
            <div className={`text-[10px] text-right font-semibold ${class_color[selected.congestion_class]}`}>{selected.fcr_score}</div>
            <div className="text-[10px] text-slate-500">Congestion</div>
            <div className={`text-[10px] text-right font-semibold ${class_color[selected.congestion_class]}`}>{selected.congestion_class}</div>
            <div className="text-[10px] text-slate-500">Recommendation</div>
            <div className={`text-[10px] text-right font-bold ${rec_badge[selected.recommendation || 'GO'].text}`}>{selected.recommendation}</div>
          </div>
          {selected.congestion_class === 'HIGH' && (
            <p className="text-[10px] text-red-400/80 mt-1 italic">
              Individually optimal but collectively unsafe due to high vessel density.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
