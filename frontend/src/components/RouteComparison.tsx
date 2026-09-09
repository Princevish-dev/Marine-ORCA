'use client';

import type { RouteResult } from '@/types';

interface RouteComparisonProps {
  route: RouteResult;
}

export default function RouteComparison({ route }: RouteComparisonProps) {
  const distDelta = route.orca_distance_km - route.direct_distance_km;

  return (
    <div className="glass-card p-4">
      <h3 className="text-xs font-semibold tracking-widest text-slate-400 uppercase mb-3">Route Comparison</h3>

      <div className="grid grid-cols-2 gap-3">
        {/* Direct route */}
        <div className="rounded-lg p-3 border border-slate-600/30 bg-slate-800/30">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-4 h-0.5 bg-slate-400" style={{ borderTop: '2px dashed #94a3b8' }} />
            <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Direct Route</span>
          </div>
          <p className="text-lg font-bold text-white">{route.direct_distance_km} km</p>
          <div className="mt-2 space-y-1">
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-500">Risk</span>
              <span className="text-orange-400 font-medium">{(route.direct_risk * 100).toFixed(0)}%</span>
            </div>
          </div>
        </div>

        {/* ORCA route */}
        <div className="rounded-lg p-3 border border-cyan-500/30 bg-cyan-500/5">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-4 h-0.5 bg-cyan-400" />
            <span className="text-[10px] text-cyan-400 font-semibold uppercase tracking-wider">ORCA Route</span>
          </div>
          <p className="text-lg font-bold text-white">{route.orca_distance_km} km</p>
          <div className="mt-2 space-y-1">
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-500">Risk</span>
              <span className="text-emerald-400 font-medium">{(route.orca_risk * 100).toFixed(0)}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Savings summary */}
      <div className="mt-3 grid grid-cols-3 gap-2">
        <div className="text-center p-2 rounded-lg bg-slate-800/40 border border-slate-700/30">
          <p className="text-[10px] text-slate-500 mb-1">Distance</p>
          <p className={`text-xs font-bold ${distDelta > 0 ? 'text-orange-400' : 'text-emerald-400'}`}>
            +{distDelta.toFixed(1)} km
          </p>
        </div>
        <div className="text-center p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
          <p className="text-[10px] text-slate-500 mb-1">Fuel (modelled)</p>
          <p className="text-xs font-bold text-emerald-400">-{route.fuel_reduction_pct}%</p>
        </div>
        <div className="text-center p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
          <p className="text-[10px] text-slate-500 mb-1">Risk (modelled)</p>
          <p className="text-xs font-bold text-emerald-400">-{route.risk_reduction_pct}%</p>
        </div>
      </div>

      {route.current_benefit && (
        <div className="mt-2 flex items-center gap-2 text-[11px] text-cyan-400/70">
          <span>〜</span>
          <span>Favorable current leveraged along ORCA route</span>
        </div>
      )}

      <p className="mt-3 text-[10px] text-slate-600 leading-relaxed">
        MODELLED ESTIMATE — not verified vessel fuel measurements. {route.explanation.split('MODELLED')[0]}
      </p>
    </div>
  );
}
