'use client';

import { useState } from 'react';
import type { CollectiveImpactResult } from '@/types';

interface DiversificationBannerProps {
  collective_impact: CollectiveImpactResult | undefined;
  on_dismiss: () => void;
}

export default function DiversificationBanner({ collective_impact, on_dismiss }: DiversificationBannerProps) {
  if (!collective_impact?.collective_pressure_warning) return null;

  return (
    <div className="mx-3 mt-2 relative overflow-hidden rounded-xl border border-amber-500/30 bg-gradient-to-r from-amber-500/10 via-orange-500/10 to-red-500/10 backdrop-blur-sm">
      <div className="absolute inset-0 bg-gradient-to-r from-amber-500/5 to-transparent animate-pulse" />
      <div className="relative flex items-start gap-3 p-3">
        <span className="text-lg flex-shrink-0 mt-0.5">⚠️</span>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-bold text-amber-300 tracking-wide uppercase">
            Recommendation Diversified
          </p>
          <p className="text-[11px] text-slate-300 mt-1 leading-relaxed">
            {collective_impact.redistribution_note}
          </p>
          <div className="flex flex-wrap gap-2 mt-2">
            {collective_impact.diversified_zones.map((z) => (
              <span
                key={z}
                className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/25"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                {z} — GO
              </span>
            ))}
            {collective_impact.avoided_zones.map((z) => (
              <span
                key={z}
                className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/25"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                {z} — AVOID
              </span>
            ))}
          </div>
        </div>
        <button
          onClick={on_dismiss}
          className="flex-shrink-0 text-slate-500 hover:text-slate-300 transition-colors text-lg leading-none"
        >
          ×
        </button>
      </div>
    </div>
  );
}
